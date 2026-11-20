# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``purge``, which the worker runs: what expired, and the tasks ended (US-2830, EP-13).

The schedule deposits it (``test_worker_main.py``); the worker runs it in the one transaction of
the task, the storage losing what the rows designated once that is committed. The purge of the
exchanges and of the history themselves is tried in ``test_purge.py``.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import holder
from sqlalchemy import insert, select
from task_handlers import deposit, task

from waterfall.core.backups.tables import Backup
from waterfall.core.users.tables import IdentitySyncReport
from waterfall.platform.database import utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.settings import load_worker_settings
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import LIFETIME, FileUpload, Whole, object_key_of, record_whole
from waterfall.worker import purge as purge_module
from waterfall.worker.purge import PurgeTask
from waterfall.worker.runner import Timing, Worker
from waterfall.worker.schedule import every

if TYPE_CHECKING:
    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

UNDO = timedelta(hours=12)
THIRTY_DAYS = timedelta(days=30)


def purge_run(
    database: Database,
    queue: TaskQueue,
    bucket: Bucket,
    retention: timedelta = THIRTY_DAYS,
) -> UUID:
    """Deposit a purge as the schedule does, and let a worker run it; give its task."""
    queue.prepare()
    task_id = deposit(database, queue, "purge")
    handlers = {"purge": PurgeTask(bucket, UNDO, retention)}
    assert Worker(database, queue, handlers, "worker", Timing(block=0.1)).step()
    return task_id


def ended_task(
    database: Database,
    finished: datetime,
    *,
    kind: str = "export",
    status: str = "succeeded",
    result: dict[str, Any] | None = None,
) -> UUID:
    """Record a task of the platform that ended at ``finished``."""
    task_id = new_id()
    problem = {"code": "INTERNAL_ERROR", "status": 500} if status == "failed" else None
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=task_id,
                kind=kind,
                status=status,
                progress=100 if status == "succeeded" else 0,
                payload={},
                result=result,
                problem=problem,
                requested_by=None,
                correlation_id="test-purge-task",
                attempts=1,
                submitted_at=finished,
                started_at=finished,
                finished_at=finished,
            )
        )
    return task_id


def kept(database: Database, *task_ids: UUID) -> list[bool]:
    """Tell, for each task, whether the database still holds it."""
    with database.transaction() as session:
        held = set(session.scalars(select(BackgroundTask.id)))
    return [task_id in held for task_id in task_ids]


@pytest.mark.story("US-2830")
def test_a_task_ended_for_longer_than_the_retention_of_its_result_is_no_longer_in_the_database(
    database: Database, queue: TaskQueue, backups_bucket: Bucket
) -> None:
    # propre à US-2830 : « une tâche de fond terminée depuis plus que la rétention de son
    # résultat n'est plus dans la base » : succeeded or failed; one younger stays, as a task that
    # is queued or running, however old.
    now = utc_now()
    old, old_failed = (
        ended_task(database, now - THIRTY_DAYS - timedelta(minutes=1), status=status)
        for status in ("succeeded", "failed")
    )
    recent = ended_task(database, now - THIRTY_DAYS + timedelta(hours=1))
    with database.transaction() as session:
        running = new_id()
        session.execute(
            insert(BackgroundTask).values(
                id=running,
                kind="export",
                status="running",
                progress=0,
                payload={},
                requested_by=None,
                correlation_id="test-purge-task",
                attempts=1,
                submitted_at=now - 2 * THIRTY_DAYS,
                started_at=now - 2 * THIRTY_DAYS,
            )
        )
    purged = purge_run(database, queue, backups_bucket)
    assert kept(database, old, old_failed, recent, running) == [False, False, True, True]
    ran = task(database, purged)
    assert (ran.status, (ran.result or {})["tasks"]) == ("succeeded", 2)


@pytest.mark.story("US-2830")
def test_the_retention_of_the_tasks_is_the_one_the_purge_is_given(
    database: Database, queue: TaskQueue, backups_bucket: Bucket
) -> None:
    two_days_ago = ended_task(database, utc_now() - timedelta(days=2))
    purge_run(database, queue, backups_bucket, retention=timedelta(days=3))
    assert kept(database, two_days_ago) == [True]
    purge_run(database, queue, backups_bucket, retention=timedelta(days=1))
    assert kept(database, two_days_ago) == [False]


@pytest.mark.story("US-2830")
def test_the_report_of_a_reading_of_the_accounts_goes_with_its_task(
    database: Database, queue: TaskQueue, backups_bucket: Bucket
) -> None:
    # propre à US-2830 : « le compte rendu d'une lecture des comptes ne l'empêche pas » (#921).
    finished = utc_now() - 2 * THIRTY_DAYS
    old = ended_task(database, finished, kind="identity_sync")
    recent = ended_task(database, utc_now(), kind="identity_sync")
    with database.transaction() as session:
        for task_id, at in ((old, finished), (recent, utc_now())):
            session.execute(
                insert(IdentitySyncReport).values(
                    task_id=task_id,
                    finished_at=at,
                    created=1,
                    updated=0,
                    deactivated=0,
                    skipped=[],
                    removed=[],
                )
            )
    purge_run(database, queue, backups_bucket)
    with database.transaction() as session:
        assert list(session.scalars(select(IdentitySyncReport.task_id))) == [recent]
    assert kept(database, old, recent) == [False, True]


@pytest.mark.story("US-2830")
def test_the_last_reading_purged_with_a_longer_interval_does_not_become_due_again(
    database: Database, queue: TaskQueue, backups_bucket: Bucket
) -> None:
    # propre à US-2830 : la purge épargne la dernière tâche d'un genre planifié, dont
    # l'ordonnancement lit la date : une lecture de 40 jours, un intervalle de 45 jours, ne
    # redevient pas due.
    old = ended_task(database, utc_now() - timedelta(days=40), kind="identity_sync")
    purge_run(database, queue, backups_bucket)
    assert kept(database, old) == [True]
    with database.transaction() as session:
        assert not every("identity_sync", 45 * 86_400).due(session, utc_now())


@pytest.mark.story("US-2830")
def test_the_task_of_a_backup_still_listed_is_spared_by_the_purge_of_the_tasks(
    database: Database, queue: TaskQueue, backups_bucket: Bucket
) -> None:
    # propre à US-2830 : « en épargnant la tâche d'une sauvegarde gardée » : only the rotation
    # deletes a backup; the task its row names, which the table refuses to lose, stays however old.
    finished = utc_now() - 2 * THIRTY_DAYS
    listed = ended_task(database, finished, kind="backup")
    unlisted = ended_task(database, finished, kind="backup")
    with database.transaction() as session:
        session.execute(
            insert(Backup).values(
                id=new_id(),
                taken_at=finished,
                size_bytes=1,
                verification="passed",
                origin="scheduled",
                is_retained=False,
                object_key=f"backups/{uuid4()}.tar",
                application_version="test",
                schema_revision="0035",
                task_id=listed,
            )
        )
    purged = purge_run(database, queue, backups_bucket)
    assert kept(database, listed, unlisted) == [True, False]
    assert task(database, purged).status == "succeeded"


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.story("US-2830")
def test_the_purge_task_deletes_the_deposit_expired_and_its_object_once_it_is_committed(
    database: Database, queue: TaskQueue, backups_bucket: Bucket
) -> None:
    # « Un fichier déposé et jamais confirmé disparaît au terme du délai d'expiration. » : the
    # task the worker runs deletes the row, commits, then the object; the storage is the worker's.
    upload_id = uuid4()
    key = object_key_of(upload_id)
    backups_bucket.put(key, b"WF")
    with database.transaction() as session:
        whole = Whole("oublie.wft", 2, holder(database))
        record_whole(session, upload_id, whole, utc_now() - LIFETIME * 2)
    purged = purge_run(database, queue, backups_bucket)
    assert backups_bucket.size(key) is None
    with database.transaction() as session:
        assert session.get(FileUpload, upload_id) is None
    ran = task(database, purged)
    assert (ran.status, ran.result) == ("succeeded", {"objects": 1, "deposits": 0, "tasks": 0})


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.story("US-2830")
def test_a_purge_task_that_fails_keeps_the_rows_and_the_object_it_would_have_deleted(
    database: Database,
    queue: TaskQueue,
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An object is not deleted for a row a failed transaction keeps: the task fails after the
    # deposit was deleted, its work is undone, and the storage is left as it was.
    upload_id = uuid4()
    key = object_key_of(upload_id)
    backups_bucket.put(key, b"WF")
    with database.transaction() as session:
        whole = Whole("oublie.wft", 2, holder(database))
        record_whole(session, upload_id, whole, utc_now() - LIFETIME * 2)

    def refuse(*_arguments: object, **_keywords: object) -> None:
        message = "the history is out of reach"
        raise RuntimeError(message)

    monkeypatch.setattr(purge_module.history_interface, "purge", refuse)
    failed = purge_run(database, queue, backups_bucket)
    assert task(database, failed).status == "failed"
    assert backups_bucket.size(key) == 2
    with database.transaction() as session:
        assert session.get(FileUpload, upload_id) is not None


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.story("US-2830")
@pytest.mark.usefixtures("logs")
def test_a_purge_task_whose_storage_does_not_answer_still_purges_the_rows(
    database: Database, queue: TaskQueue
) -> None:
    # The storage out of reach is no reason to keep the rows, nor to fail the task: what it
    # holds, the next pass sweeps.
    unreachable = Bucket.connect("backups", "http://127.0.0.1:9", "us-east-1", "key", "secret")
    upload_id = uuid4()
    with database.transaction() as session:
        whole = Whole("oublie.wft", 2, holder(database))
        record_whole(session, upload_id, whole, utc_now() - LIFETIME * 2)
    purged = purge_run(database, queue, unreachable)
    assert task(database, purged).status == "succeeded"
    with database.transaction() as session:
        assert session.get(FileUpload, upload_id) is None


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.story("US-2830")
@pytest.mark.usefixtures("platform_environment")
@pytest.mark.parametrize(
    ("hours", "days", "expected"),
    [(None, None, (12, 30)), ("3", "7", (3, 7))],
)
def test_the_retentions_of_the_purge_are_the_settings_of_the_worker_twelve_hours_and_thirty_days(
    hours: str | None,
    days: str | None,
    expected: tuple[int, int],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « [L'historique annulable] ne survit ni à la fin de la session, ni au marquage, ni à
    # l'abandon de la révision. » : the longest session of the realm, ``WATERFALL_UNDO_RETENTION_
    # HOURS``; and ``background_task_retention_days``, the operating parameter, thirty days.
    if hours is not None and days is not None:
        monkeypatch.setenv("WATERFALL_UNDO_RETENTION_HOURS", hours)
        monkeypatch.setenv("WATERFALL_BACKGROUND_TASK_RETENTION_DAYS", days)
    purging = PurgeTask.of(load_worker_settings())
    assert purging.undo_retention == timedelta(hours=expected[0])
    assert purging.task_retention == timedelta(days=expected[1])


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.story("US-2830")
def test_the_purge_task_removes_the_history_older_than_the_retention_it_is_given(
    database: Database,
    queue: TaskQueue,
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[tuple[datetime, datetime]] = []

    def purge(_session: object, *, before: datetime, now: datetime) -> None:
        called.append((before, now))

    monkeypatch.setattr(purge_module.history_interface, "purge", purge)
    purge_run(database, queue, backups_bucket)
    ((before, now),) = called
    assert now - before == UNDO
