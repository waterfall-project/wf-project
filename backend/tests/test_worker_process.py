# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The worker and its schedule as processes of their own, stopped and started as the platform does.

A worker of the tests runs as ``waterfall-worker`` does (``worker_process``), on the queue of the
test; the schedule is the command of the service ``scheduler`` of the Compose file of the
platform, run as its shell runs it, with ``waterfall-worker enqueue``.
"""

import itertools
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest
import yaml
from sqlalchemy import insert, select
from support import raw_account
from task_handlers import REQUEST, Runs, deposit, inscriptions, task

from waterfall.core.users.tables import UserAccount
from waterfall.platform.correlation import FORM
from waterfall.platform.database import Database
from waterfall.platform.queue import TaskQueue
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.runner import Timing, Worker

TESTS = Path(__file__).resolve().parent
COMPOSE = TESTS.parents[1] / "deploy" / "compose" / "compose.service.yaml"
# Long enough for a process to start, and short enough for a test to fail in reasonable time.
PATIENCE = 30.0
INTERVAL = 1


def wait_for(condition: Callable[[], bool]) -> None:
    """Wait until a condition holds, or fail."""
    deadline = time.monotonic() + PATIENCE
    while not condition():
        assert time.monotonic() < deadline, "the condition never held"
        time.sleep(0.05)


@contextmanager
def started(arguments: list[str], environment: dict[str, str]) -> Generator[subprocess.Popen[str]]:
    """Run a process, in a group of its own, and stop the whole group when the block ends."""
    process = subprocess.Popen(
        arguments,
        env={"PATH": os.environ["PATH"], **environment},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        yield process
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        _, errors = process.communicate(timeout=PATIENCE)
        # What the process said, shown with the failure of the test.
        sys.stderr.write(errors)


@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.parametrize("stop", [signal.SIGTERM, signal.SIGKILL], ids=["stopped", "killed"])
def test_a_worker_stopped_during_a_task_leaves_the_base_unchanged_and_resumes_it_after_restart(
    database: Database,
    queue: TaskQueue,
    service_environment: dict[str, str],
    tmp_path: Path,
    stop: signal.Signals,
) -> None:
    # « L'arrêt du worker pendant une tâche laisse la base inchangée, et la tâche est reprise après
    # redémarrage. » : the stop of the platform, or the end of the process, during the work.
    task_id = deposit(database, queue)
    stalled = tmp_path / "stalled"
    worker = [sys.executable, str(TESTS / "worker_process.py"), queue.stream]
    with started([*worker, "first", "stall", str(stalled)], service_environment) as first:
        wait_for(stalled.exists)
        first.send_signal(stop)
        assert first.wait(timeout=PATIENCE) == (0 if stop is signal.SIGTERM else -stop)
    assert inscriptions(database) == []
    stopped = task(database, task_id)
    assert (stopped.status, stopped.attempts) == ("running", 1)
    with started([*worker, "second", "finish", str(stalled)], service_environment):
        wait_for(lambda: task(database, task_id).status == "succeeded")
    (inscribed,) = inscriptions(database)
    assert (inscribed.correlation_id, inscribed.params) == (REQUEST, {"task_id": str(task_id)})
    assert task(database, task_id).attempts == 2


def scheduler() -> tuple[dict[str, str], list[str]]:
    """Read the service that schedules the tasks in the Compose file: settings and command.

    The command is given as its shell reads it, once Compose has written ``$$`` as ``$``.
    """
    service = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))["services"]["scheduler"]
    command = cast("list[str]", service["command"])
    return cast("dict[str, str]", service["environment"]), [
        part.replace("$$", "$") for part in command
    ]


def test_the_platform_deposits_the_reading_of_the_accounts_at_its_interval_as_an_administrator(
    database: Database, platform_queue: TaskQueue, service_environment: dict[str, str]
) -> None:
    # The criterion of US-0370 of its own: « la lecture se dépose en file à l'intervalle que fixe
    # la configuration de l'installation, et le worker la prend comme celle qu'un administrateur
    # demande (PBS-5.3) » — a day by default. The reading itself, and the accounts it gives
    # (WF-ADM-0070-A), are tried against the platform (test_keycloak_identity_sync.py).
    variable = "WATERFALL_IDENTITY_SYNC_INTERVAL"
    scheduled_with, shell = scheduler()
    assert scheduled_with[variable] == f"${{{variable}:-86400}}"
    runs = Runs()
    platform_queue.prepare()
    taker = Worker(database, platform_queue, {"identity_sync": runs}, "worker", Timing(block=0.1))
    with started(shell, {**service_environment, variable: str(INTERVAL)}):
        wait_for(lambda: taker.step() and len(runs) == 2)
    with database.transaction() as session:
        scheduled = list(session.scalars(select(BackgroundTask).order_by(BackgroundTask.id)))
    assert [row.id for row in scheduled[:2]] == runs
    assert {(row.kind, row.requested_by) for row in scheduled} == {("identity_sync", None)}
    assert [row.status for row in scheduled[:2]] == ["succeeded", "succeeded"]
    for earlier, later in itertools.pairwise(scheduled):
        assert (later.submitted_at - earlier.submitted_at).total_seconds() >= INTERVAL
    assert len({row.correlation_id for row in scheduled}) == len(scheduled)
    assert all(FORM.fullmatch(row.correlation_id) for row in scheduled)
    administrator = raw_account()
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**administrator))
    administrator_id = administrator["id"]
    assert isinstance(administrator_id, UUID)
    asked = deposit(database, platform_queue, requested_by=administrator_id)
    wait_for(lambda: not taker.step())
    assert asked in runs
    assert task(database, asked).status == "succeeded"
