# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A command of Docker tried again when the mirror of the images does not answer (#4894).

Usage: ``python -m wftools.retried -- <command>…``.

``docker compose up --build`` and ``docker build`` resolve the images of the mirror on ghcr.io
(``ghcr.io/waterfall-project/mirror/``) that the Compose files and the Dockerfiles pin by digest.
Twice, in the merge queue, the registry did not answer from the runner (``dial tcp …: i/o timeout``,
after 60 s) and the job ``service / paths`` failed before any path ran. The command is played on the
streams of the tool; when it fails and what it printed says ghcr.io could not be reached, it is
played again, ATTEMPTS times in all, with a pause that grows.

The command is tried again whole rather than its images pulled beforehand, because BuildKit may ask
the registry for the manifest of a base image though the image is held locally: only the command
itself knows what it resolves, and what it already built, its cache keeps. A failure that is not
the registry's — an image the mirror does not hold, a refusal, an error of the build — is not tried
again: its code is the command's. The failure after the last attempt is the command's own, its
message kept as the last attempt printed it.
"""

import re
import subprocess
import sys
import time
from typing import TYPE_CHECKING

from wftools import registry

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

TOOL = "wftools.retried"
"""The name the tool gives its messages."""

ATTEMPTS = registry.ATTEMPTS
"""The attempts at the command before its failure is the tool's."""

PAUSE = registry.PAUSE
"""The seconds before the second attempt; the n-th pause is n times as long."""

# What a registry that cannot be reached says, in Docker's message or BuildKit's.
UNREACHABLE = re.compile(
    r"dial tcp[^\n]*(?:i/o timeout|connection (?:refused|reset)|no such host)"
    r"|TLS handshake timeout|Client\.Timeout exceeded|unexpected EOF",
    re.IGNORECASE,
)


def unreachable(output: str) -> bool:
    """Say whether what a command printed is a failure to reach ghcr.io, the mirror's registry."""
    return registry.REGISTRY in output and UNREACHABLE.search(output) is not None


def retried(
    command: Sequence[str],
    run: Callable[[Sequence[str]], tuple[int, str]],
    wait: Callable[[float], None] = time.sleep,
) -> int:
    """Play a command until it succeeds or fails otherwise than by a connection; return its code.

    ``run`` plays the command, printing what it says as it goes, and returns its code with what it
    printed. A connection failure is tried again, ATTEMPTS times in all, after a pause of PAUSE
    seconds, then twice as long, and so on.
    """
    code = 1
    for attempt in range(1, ATTEMPTS + 1):
        code, output = run(command)
        if code == 0 or not unreachable(output):
            return code
        if attempt < ATTEMPTS:
            pause = PAUSE * attempt
            print(
                f"{TOOL}: {registry.REGISTRY} did not answer; attempt {attempt + 1} in {pause:g} s",
                file=sys.stderr,
            )
            wait(pause)
    print(f"{TOOL}: {registry.REGISTRY} did not answer, in {ATTEMPTS} attempts", file=sys.stderr)
    return code


def _run(command: Sequence[str]) -> tuple[int, str]:
    # The output goes to the error stream, as it comes, and is kept to be read.
    printed: list[str] = []
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    ) as process:
        for line in process.stdout or ():
            sys.stderr.write(line)
            printed.append(line)
    return process.returncode, "".join(printed)


def main(arguments: Sequence[str]) -> int:
    """Play the command after ``--``; return its code, 2 when it is not given or cannot run."""
    command = list(arguments[1:] if arguments[:1] == ["--"] else arguments)
    if not command:
        print(f"{TOOL}: no command to play", file=sys.stderr)
        return 2
    try:
        return retried(command, _run)
    except OSError as error:
        print(f"{TOOL}: {command[0]} could not run: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
