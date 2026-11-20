# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The worker and its schedule as processes of their own, stopped and started as the platform does.

A worker of the tests runs as ``waterfall-worker`` does (``worker_process``), on the queue of the
test; the schedule is the command of the service ``scheduler`` of the Compose file of the
platform, run as its shell runs it, with ``waterfall-worker schedule``.
"""

import itertools
import os
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

import pytest
import yaml
from access_rows import holder
from sqlalchemy import insert, select
from support import raw_account
from task_handlers import REQUEST, Runs, deposit, inscriptions, task

from waterfall.core.users.tables import UserAccount
from waterfall.platform.correlation import FORM
from waterfall.platform.database import utc_now
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import LIFETIME, FileUpload, Whole, object_key_of, record_whole
from waterfall.worker.purge import PurgeTask
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.storage import Bucket

TESTS = Path(__file__).resolve().parent
COMPOSE = TESTS.parents[1] / "deploy" / "compose" / "compose.service.yaml"
PRODUCTION = TESTS.parents[1] / "deploy" / "compose" / "compose.prod.yaml"
# Long enough for a process to start, and short enough for a test to fail in reasonable time.
PATIENCE = 30.0
INTERVAL = 1
PURGE = "WATERFALL_PURGE_INTERVAL"
SCHEDULE = "WATERFALL_SCHEDULE_INTERVAL"


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


def scheduler(compose: Path = COMPOSE) -> tuple[dict[str, str], list[str]]:
    """Read the service that schedules the tasks in a Compose file: settings and command.

    The command is given as its shell reads it, once Compose has written ``$$`` as ``$``.
    """
    service = yaml.safe_load(compose.read_text(encoding="utf-8"))["services"]["scheduler"]
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
    handlers = {"identity_sync": runs, "purge": Runs()}
    taker = Worker(database, platform_queue, handlers, "worker", Timing(block=0.1))
    # The schedule looks at each second; the purge, deposited with the reading, waits for its hour.
    environment = {**service_environment, SCHEDULE: str(INTERVAL), variable: str(INTERVAL)}
    with started(shell, {**environment, PURGE: "3600"}):
        wait_for(lambda: taker.step() and len(runs) == 2)
    with database.transaction() as session:
        readings = BackgroundTask.kind == "identity_sync"
        scheduled = list(session.scalars(select(BackgroundTask).where(readings)))
    scheduled.sort(key=lambda row: row.submitted_at)
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


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.story("US-2830")
def test_the_platform_purges_what_expired_at_its_interval_by_the_task_its_schedule_deposits(
    database: Database,
    platform_queue: TaskQueue,
    backups_bucket: Bucket,
    service_environment: dict[str, str],
) -> None:
    # « Un fichier déposé et jamais confirmé disparaît au terme du délai d'expiration. » : the
    # schedule, which reaches neither the storage nor the tables of the exchanges, deposits the
    # purge at the interval of ``WATERFALL_PURGE_INTERVAL``, ten minutes by default; the worker,
    # which holds the storage, runs it.
    scheduled_with, shell = scheduler()
    assert scheduled_with[PURGE] == f"${{{PURGE}:-600}}"
    assert not [name for name in scheduled_with if "STORAGE" in name]
    upload_id = uuid4()
    key = object_key_of(upload_id)
    backups_bucket.put(key, b"WF")
    user = holder(database)
    with database.transaction() as session:
        record_whole(session, upload_id, Whole("oublie.wft", 2, user), utc_now() - LIFETIME * 2)
    platform_queue.prepare()
    purging = PurgeTask(backups_bucket, timedelta(hours=12), timedelta(days=30))
    handlers = {"purge": purging, "identity_sync": Runs()}
    taker = Worker(database, platform_queue, handlers, "worker", Timing(block=0.1))
    # The schedule is run by a process that holds no setting of the storage.
    environment = {
        **service_environment,
        SCHEDULE: str(INTERVAL),
        PURGE: str(INTERVAL),
        "WATERFALL_IDENTITY_SYNC_INTERVAL": "3600",
    }

    def purged() -> bool:
        taker.step()
        # The row and the object go each in its own step of the purge: both are waited for (#2566).
        with database.transaction() as session:
            if session.get(FileUpload, upload_id) is not None:
                return False
        return backups_bucket.size(key) is None

    with started(shell, environment):
        wait_for(purged)
    with database.transaction() as session:
        ran = session.scalars(
            select(BackgroundTask).where(
                BackgroundTask.kind == "purge", BackgroundTask.status == "succeeded"
            )
        ).first()
    assert ran is not None
    assert ran.requested_by is None


@pytest.mark.story("US-2830")
@pytest.mark.parametrize("interval", ["0", "soon", ""])
def test_a_schedule_whose_interval_is_no_positive_number_stops_with_two(
    interval: str, service_environment: dict[str, str]
) -> None:
    # A schedule at no interval would never come, so the service refuses to start. It guards the
    # purge of WF-DAT-0120 without trying its Vérif, which the test above tries: it cites no
    # requirement (#2533).
    _, shell = scheduler()
    with started(shell, {**service_environment, SCHEDULE: interval}) as process:
        assert process.wait(timeout=PATIENCE) == 2


@pytest.mark.story("US-2830")
@pytest.mark.parametrize("variable", ["WATERFALL_IDENTITY_SYNC_INTERVAL", PURGE])
def test_a_schedule_that_says_an_interval_is_wrong_stops_the_service_with_two(
    variable: str, service_environment: dict[str, str]
) -> None:
    # The command returns 2 for a setting wrong, and the loop does not call it again.
    _, shell = scheduler()
    environment = {**service_environment, SCHEDULE: str(INTERVAL), variable: "soon"}
    with started(shell, environment) as process:
        assert process.wait(timeout=PATIENCE) == 2


def test_the_two_compose_files_schedule_the_same_loop_with_the_same_settings() -> None:
    # The purge that makes a deposit never confirmed disappear must run in production as the tests
    # run it: the same script of the loop, the same intervals and retentions by default. A
    # comparison of two files, not the Vérif of WF-DAT-0120: it cites no requirement (#2533).
    service_settings, service_shell = scheduler(COMPOSE)
    production_settings, production_shell = scheduler(PRODUCTION)
    assert production_shell == service_shell
    assert [part for part in service_shell if "waterfall-worker" in part] == [
        part for part in production_shell if "waterfall-worker" in part
    ]
    assert "waterfall-worker schedule" in service_shell[-1]
    assert "waterfall-worker purge" not in service_shell[-1]
    names = ("WATERFALL_SCHEDULE_INTERVAL", "WATERFALL_IDENTITY_SYNC_INTERVAL", PURGE)
    assert service_settings[SCHEDULE] == f"${{{SCHEDULE}:-300}}"
    assert {each: production_settings[each] for each in names} == {
        each: service_settings[each] for each in names
    }
    # What the purge keeps is the worker's, which runs it.
    undo, tasks = "WATERFALL_UNDO_RETENTION_HOURS", "WATERFALL_BACKGROUND_TASK_RETENTION_DAYS"
    retentions = {undo: f"${{{undo}:-12}}", tasks: f"${{{tasks}:-30}}"}
    for compose in (COMPOSE, PRODUCTION):
        worker = yaml.safe_load(compose.read_text(encoding="utf-8"))["services"]["worker"]
        assert {name: worker["environment"][name] for name in retentions} == retentions
