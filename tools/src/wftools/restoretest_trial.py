# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The test of a restoration, played under Compose by the trial of the production (US-2930).

The trial of the production platform (``wftools.production``), asked for the backup and its
restoration, plays after them the test of a restoration the host runs once a month
(``deploy/compose/restore-test.sh``, ``docs/exploitation/test-de-restauration.md``):

- before the manual backup the trial asks of the API, a backup *scheduled*, which the test alone
  restores: the schedule is made due — the date of its last change set back past its latest
  occurrence, as the database of the trial is its own to write —, ``waterfall-worker schedule`` is
  run in the container of the scheduler, which deposits the backup, and the trial waits for it to
  be listed verified;
- after the restoration, the script is run: its status must be 0; the production holds a test
  that succeeded, on a backup scheduled; and nothing of the project of the test remains, neither
  container, nor network, nor volume, which the copy not anonymised would outlive in.

The failure of a test — the number of the projects that differs — is held by the tests of the back
(``backend/tests/test_restore_trial.py``), not here.
"""

import subprocess
from collections.abc import Callable
from typing import Protocol

from wftools import REPOSITORY
from wftools.restoration_trial import PATIENCE, PAUSE, Clock, TrialError

SCRIPT = REPOSITORY / "deploy" / "compose" / "restore-test.sh"
EPHEMERAL = "waterfall-restore-test"
"""The project of Compose of the ephemeral platform (``compose.restore-test.yaml``)."""
DUE = (
    "UPDATE backup_schedule SET is_enabled = true, "
    "timing_changed_at = timing_changed_at - interval '8 days'"
)
"""Make the backup due: a weekly schedule has had an occurrence in the 8 days before."""
VERIFIED = "SELECT count(*) FROM backup WHERE origin = 'scheduled' AND verification = 'passed'"
TESTED = (
    "SELECT t.succeeded FROM restore_test t JOIN backup b ON b.id = t.backup_id "
    "WHERE b.origin = 'scheduled' ORDER BY t.finished_at DESC LIMIT 1"
)
"""Whether the latest test restored a backup scheduled, and succeeded: ``t``."""
OPEN = (
    "SELECT count(*) FROM background_task WHERE kind = 'backup' AND status IN ('queued', 'running')"
)
"""The tasks of a backup not ended: the one that holds the lock of the backups is among them."""
LIMIT = 1800.0
"""The seconds the script of the test has to end, before it is asked to stop (TERM)."""
GRACE = 180.0
"""The seconds the script has, once asked to stop, to remove its platform before it is killed."""

Read = Callable[[list[str]], tuple[int, str]]


class Run(Protocol):
    """Run a command, which a ``limit`` in seconds bounds: TERM, and ``TimeoutExpired`` raised."""

    def __call__(self, command: list[str], limit: float | None = None, /) -> int:
        """Return the status of the command."""
        raise NotImplementedError


def psql(compose: list[str], statement: str) -> list[str]:
    """Return the command that runs a statement on the database of Waterfall, as postgres."""
    return [
        *compose,
        "exec",
        "-T",
        "postgres",
        "psql",
        "--username=postgres",
        "--dbname=waterfall",
        "--no-psqlrc",
        "--tuples-only",
        "--no-align",
        f"--command={statement}",
    ]


def _output(read: Read, command: list[str], what: str) -> str:
    code, output = read(command)
    if code != 0:
        message = f"{what} failed ({code})"
        raise TrialError(message)
    return output.strip()


def scheduled_backup(compose: list[str], read: Read, clock: Clock | None = None) -> None:
    """Have the schedule deposit a backup, and wait for it to be listed verified and ended.

    The line of the backup is verified before its task ends: the manual backup that follows would
    meet the lock of the backups still held, and be refused. The task is waited for as well.
    """
    clock = clock or Clock()
    _output(read, psql(compose, DUE), "making the backup due")
    deposit = [*compose, "exec", "-T", "scheduler", "waterfall-worker", "schedule"]
    _output(read, deposit, "the schedule")
    deadline = clock.now() + PATIENCE
    while clock.now() < deadline:
        counted = _output(read, psql(compose, VERIFIED), "counting the scheduled backups")
        if counted.isdigit() and int(counted) > 0:
            open_tasks = _output(read, psql(compose, OPEN), "counting the tasks of backup open")
            if open_tasks.isdigit() and int(open_tasks) == 0:
                print("  the schedule deposited a backup, which is listed verified and ended")
                return
        clock.pause(PAUSE)
    message = f"no backup scheduled was listed verified, its task ended, in {PATIENCE:.0f} s"
    raise TrialError(message)


def remains(read: Read) -> list[str]:
    """List what the project of the test leaves: its containers, networks and volumes."""
    label = f"label=com.docker.compose.project={EPHEMERAL}"
    asked = {
        "container": ["docker", "ps", "--all", "--quiet", "--filter", label],
        "network": ["docker", "network", "ls", "--quiet", "--filter", label],
        "volume": ["docker", "volume", "ls", "--quiet", "--filter", label],
    }
    left: list[str] = []
    for kind, command in asked.items():
        found = _output(read, command, f"listing the {kind}s of {EPHEMERAL}")
        left.extend(f"{kind} {each}" for each in found.split())
    return left


def restore_test(
    compose: list[str], run: Run, read: Read, project: str, limit: float = LIMIT
) -> None:
    """Run the script of the test beside the production ``project``, and hold what it must do.

    The script is bounded: ``docker compose wait`` does not end of itself if the test hangs.
    """
    # ``env`` executes the script: the signal of the bound reaches the shell and its traps.
    command = ["env", f"WATERFALL_PRODUCTION_PROJECT={project}", "sh", str(SCRIPT)]
    try:
        code = run(command, limit)
    except subprocess.TimeoutExpired as error:
        message = f"restore-test.sh did not end in {limit:.0f} s; it was asked to stop"
        raise TrialError(message) from error
    if code:
        message = f"restore-test.sh failed ({code})"
        raise TrialError(message)
    print("  restore-test.sh succeeded")
    if _output(read, psql(compose, TESTED), "reading the tests of a restoration") != "t":
        message = (
            "the production holds no test of a restoration that succeeded, on a scheduled backup"
        )
        raise TrialError(message)
    print("  the production inscribed the test, on the backup scheduled")
    if left := remains(read):
        message = f"the project {EPHEMERAL} leaves {', '.join(left)}"
        raise TrialError(message)
    print(f"  nothing of {EPHEMERAL} remains: no container, network or volume")
