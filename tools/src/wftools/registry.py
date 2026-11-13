# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tools that read or write a registry share: its answers, and the attempts at it (#2530).

``wftools.e2eimage`` finds the work image of the paths in ghcr.io, or publishes it;
``wftools.mirror`` copies the third-party images of Docker Hub there. Both ask the registry whether
it holds a reference, and both try a request again before they say it failed: the one place the
attempts, the pause and the registry's answers are written (US-1900).
"""

import re
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

ATTEMPTS = 4
"""The attempts at a request to the registry, or at a build, before its failure is said (#2530)."""

PAUSE = 20.0
"""The seconds between two attempts, as curl waited between its own for the package of make."""

REGISTRY = "ghcr.io"
"""The registry the tools publish to and read from, which a failure names."""

# What the registry answers for a tag it does not hold.
UNKNOWN_TAG = re.compile(r"not found|manifest unknown|name unknown", re.IGNORECASE)
# What it answers for a package it does not hold yet, the first time, as for one it refuses to show:
# a refusal — `403 Forbidden`, or `requested access to the resource is denied`. The image is then
# built or copied, and its publication says which it was.
REFUSED = re.compile(r"403 Forbidden|denied", re.IGNORECASE)
# The digest of the index or of the manifest, as `docker buildx imagetools inspect` says it.
DIGEST = re.compile(r"^Digest:\s+(sha256:[0-9a-f]{64})\s*$", re.MULTILINE)


class ImageError(Exception):
    """An image could not be found, built, copied or published: the message says where."""


def held_digest(
    reference: str,
    read: Callable[[list[str]], tuple[int, str]],
    wait: Callable[[float], None] = time.sleep,
    *,
    tool: str,
    registry: str = REGISTRY,
) -> str | None:
    """Return the digest the registry holds for the reference, None if it does not hold it.

    A refusal is taken for a package not yet published: ghcr.io answers so for a name it does not
    hold, before the image is first published, and the publication that follows fails on a true
    refusal. Any other answer — the registry unreachable, a 5xx, a delay — is asked again,
    ATTEMPTS times in all, then is an error that names the registry and what it said last: the
    jobs that pull the image would not reach it either.
    """
    said = "nothing"
    for attempt in range(1, ATTEMPTS + 1):
        code, answer = read(["docker", "buildx", "imagetools", "inspect", reference])
        said = (answer.strip().splitlines() or ["nothing"])[-1]
        if code == 0:
            if found := DIGEST.search(answer):
                return found.group(1)
            message = f"the registry held {reference} but said no digest"
            raise ImageError(message)
        if UNKNOWN_TAG.search(answer):
            return None
        if REFUSED.search(answer):
            print(f"{tool}: {registry} refused to show {reference}: {said}", file=sys.stderr)
            return None
        again(attempt, f"{registry} did not answer for {reference}: {said}", wait, tool=tool)
    message = f"{registry} did not say whether it holds {reference}, in {ATTEMPTS} attempts: {said}"
    raise ImageError(message)


def again(attempt: int, what: str, wait: Callable[[float], None], *, tool: str) -> None:
    """Say a failed attempt, and wait before the next one; the last waits for nothing."""
    if attempt < ATTEMPTS:
        print(f"{tool}: {what}; attempt {attempt + 1} in {PAUSE:g} s", file=sys.stderr)
        wait(PAUSE)


def attempted(
    command: list[str],
    run: Callable[[list[str]], int],
    wait: Callable[[float], None],
    *,
    tool: str,
) -> bool:
    """Run a command of Docker until it succeeds, ATTEMPTS times at most; say whether it did.

    A build tried again starts from the layers its cache kept: only the download that failed is done
    again — an archive, the package of make, the Python of uv, pnpm from npm.
    """
    for attempt in range(1, ATTEMPTS + 1):
        if run(command) == 0:
            return True
        again(attempt, f"{' '.join(command[:2])} failed", wait, tool=tool)
    return False
