# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A command of Docker is tried again when ghcr.io does not answer (#4894)."""

import os
import subprocess
import sys
from typing import TYPE_CHECKING

from wftools import REPOSITORY, retried, slots

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

TIMEOUT = (
    "ERROR: failed to solve: DeadlineExceeded: failed to do request: Head "
    '"https://ghcr.io/v2/waterfall-project/mirror/maven/manifests/sha256:3175c44b": '
    "dial tcp 4.149.173.82:443: i/o timeout\n"
)
RESOLVE = (
    'ERROR: failed to resolve reference "ghcr.io/waterfall-project/mirror/node@sha256:3175c44b": '
    'failed to do request: Head "https://ghcr.io/v2/waterfall-project/mirror/node/manifests/'
    'sha256:3175c44b": dial tcp 20.29.134.18:443: i/o timeout\n'
)
OTHER_HOST = (
    "#4 [1/3] load metadata for ghcr.io/waterfall-project/mirror/maven\n"
    "Image ghcr.io/waterfall-project/mirror/maven Pulled\n"
    'Get "https://repo.maven.apache.org/x": dial tcp 199.232.1.1:443: i/o timeout\n'
    "unexpected EOF\n"
)
DENIED = 'failed to resolve reference "ghcr.io/waterfall-project/mirror/node": denied\n'
COMMAND = ["docker", "build", "."]


class Played:
    """A command that answers as scripted, and a wait that records its seconds."""

    def __init__(self, *answers: tuple[int, str]) -> None:
        self.answers = list(answers)
        self.runs = 0
        self.waits: list[float] = []

    def run(self, _command: object) -> tuple[int, str]:
        self.runs += 1
        return self.answers.pop(0)

    def wait(self, seconds: float) -> None:
        self.waits.append(seconds)


def test_a_connection_failure_then_a_success_is_a_success() -> None:
    """The first attempt times out reaching ghcr.io, the second succeeds: code 0, one pause."""
    played = Played((1, TIMEOUT), (0, "done\n"))
    assert retried.retried(COMMAND, played.run, played.wait) == 0
    assert played.runs == 2
    assert played.waits == [retried.PAUSE]


def test_the_failure_to_resolve_a_reference_of_the_mirror_is_tried_again() -> None:
    """The message of BuildKit that names the reference then the request is a connection failure."""
    played = Played((1, RESOLVE), (0, ""))
    assert retried.retried(COMMAND, played.run, played.wait) == 0
    assert played.runs == 2


def test_every_attempt_failing_keeps_the_last_message(capsys: pytest.CaptureFixture[str]) -> None:
    """When ghcr.io never answers the command fails with its code, after the pauses that grow."""
    played = Played(*[(1, TIMEOUT)] * retried.ATTEMPTS)
    assert retried.retried(COMMAND, played.run, played.wait) == 1
    assert played.runs == retried.ATTEMPTS
    assert played.waits == [retried.PAUSE * n for n in range(1, retried.ATTEMPTS)]
    assert f"in {retried.ATTEMPTS} attempts" in capsys.readouterr().err


def test_a_failure_that_is_not_a_connection_is_not_tried_again() -> None:
    """A refusal, or an error of the build, ends the command at its first attempt, its code kept."""
    for output in (
        DENIED,
        "ERROR: the build failed\n",
        "dial tcp 10.0.0.1:5432: i/o timeout\n",
        OTHER_HOST,
    ):
        played = Played((3, output))
        assert retried.retried(COMMAND, played.run, played.wait) == 3
        assert played.runs == 1
        assert played.waits == []


def test_main_refuses_a_missing_command_and_one_that_cannot_run() -> None:
    """Without a command the tool says so and fails; a command that does not exist is said."""
    assert retried.main(["--"]) == 2
    assert retried.main(["--", "wftools-no-such-command"]) == 2


def test_main_plays_the_command_on_the_error_stream_and_returns_its_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A command that fails otherwise than by a connection keeps its code, its output on stderr."""
    message = "the build failed"
    command = [sys.executable, "-c", f"import sys; print({message!r}); sys.exit(7)"]
    assert retried.main(["--", *command]) == 7
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err


def test_the_makefile_plays_its_builds_of_the_mirror_through_the_tool(tmp_path: Path) -> None:
    """The commands that resolve the images of ghcr.io are all played by `wftools.retried`."""
    # The ports and names of slot 0, as the other tests of the Makefile give them: the plan is the
    # same in a worktree that holds no slot.
    outer = ("MAKEFLAGS", "MAKELEVEL", "MFLAGS", "TESTS", "WATERFALL_PROCESSORS", "WATERFALL_SLOTS")
    environment = {k: v for k, v in os.environ.items() if k not in outer} | slots.variables(0)
    for target, command in (
        ("service-up", "up --build --detach --wait"),
        ("build-keycloak", "docker build"),
        ("service-witness", "build --quiet witness"),
        ("build-cache", "--target production"),
    ):
        done = subprocess.run(
            ["make", "-n", "--no-print-directory", target],
            cwd=REPOSITORY,
            env={**environment, "WATERFALL_RUNTIME_DIR": str(tmp_path)},
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [line for line in done.stdout.splitlines() if command in line]
        assert lines, (target, done.stderr)
        assert all("wftools.retried -- env" in line for line in lines), (target, lines)
