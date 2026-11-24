# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A command of Docker is tried again when ghcr.io does not answer (#4894)."""

from typing import TYPE_CHECKING

from wftools import retried

if TYPE_CHECKING:
    import pytest

TIMEOUT = (
    "ERROR: failed to solve: DeadlineExceeded: failed to do request: Head "
    '"https://ghcr.io/v2/waterfall-project/mirror/maven/manifests/sha256:3175c44b": '
    "dial tcp 4.149.173.82:443: i/o timeout\n"
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


def test_every_attempt_failing_keeps_the_last_message(capsys: pytest.CaptureFixture[str]) -> None:
    """When ghcr.io never answers the command fails with its code, after the pauses that grow."""
    played = Played(*[(1, TIMEOUT)] * retried.ATTEMPTS)
    assert retried.retried(COMMAND, played.run, played.wait) == 1
    assert played.runs == retried.ATTEMPTS
    assert played.waits == [retried.PAUSE * n for n in range(1, retried.ATTEMPTS)]
    assert f"in {retried.ATTEMPTS} attempts" in capsys.readouterr().err


def test_a_failure_that_is_not_a_connection_is_not_tried_again() -> None:
    """A refusal, or an error of the build, ends the command at its first attempt, its code kept."""
    for output in (DENIED, "ERROR: the build failed\n", "dial tcp 10.0.0.1:5432: i/o timeout\n"):
        played = Played((3, output))
        assert retried.retried(COMMAND, played.run, played.wait) == 3
        assert played.runs == 1
        assert played.waits == []


def test_the_command_is_given_after_the_separator() -> None:
    """Without a command the tool says so and fails; a command that does not exist is said."""
    assert retried.main(["--"]) == 2
    assert retried.main(["--", "wftools-no-such-command"]) == 2
