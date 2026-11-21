# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned command deposits a backup of the platform when the schedule of the backups says so.

The schedule of the backups (``backup_schedule``, written by the migrations and then by an
administrator) says at which time, universal time, the platform backs itself up, every day or one
day of the week (WF-ADM-0170, US-2910/L2); ``planned`` asks the module of the backups whether one is
due, and ``deposit_due`` deposits the task ``backup``, which the worker takes as it takes the one an
administrator asks for, its origin ``scheduled``. A new installation is backed up every day without
any schedule entered: it reads the one the migrations ship.
"""

import threading
import time as clock
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from access_rows import account
from sqlalchemy import func, insert, select, update

from waterfall.core.backups.interface import (
    Schedule,
    ScheduleWriting,
    backup_is_due,
    backup_start_lacks,
    judged_schedule,
    platform_of,
    read_backup_schedule,
    refuse_if_lacking,
    write_backup_schedule,
)
from waterfall.core.backups.schedule import latest_occurrence
from waterfall.core.backups.tables import Backup, BackupSchedule
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.locks import BACKUP_LOCK, RESTORE_LOCK
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ScheduleSettings
from waterfall.platform.tasks import PENDING, PLANNED_KINDS, BackgroundTask, submit
from waterfall.worker.backup import BackupTask
from waterfall.worker.runner import Timing, Worker
from waterfall.worker.schedule import Planned, deposit_due, planned

if TYPE_CHECKING:
    from uuid import UUID

    from installations import Installation

    from waterfall.platform.queue import TaskQueue

pytestmark = pytest.mark.story("US-2910")

SETTINGS = ScheduleSettings.model_construct(identity_sync_interval=86_400, purge_interval=600)
MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def schedule_of(**changes: Any) -> Schedule:
    """Give the schedule the migrations ship, with the changes a test asks for."""
    values: dict[str, Any] = {
        "is_enabled": True,
        "frequency": "daily",
        "at_time": time(1, 0),
        "weekday": None,
        "retained_count": 7,
        "external_copy": None,
    } | changes
    return Schedule(**values)


def at(day: int, hour: int = 0, minute: int = 0, month: int = 10) -> datetime:
    """Give an instant of 2026, universal time: the 1st of October is a Thursday."""
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


SUNDAY_AT_2_30 = schedule_of(frequency="weekly", weekday=7, at_time=time(2, 30))


@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.parametrize(
    ("schedule", "now", "expected"),
    [
        (schedule_of(), at(5, 0, 59), at(4, 1)),
        (schedule_of(), at(5, 1, 0), at(5, 1)),
        (schedule_of(), at(5, 23, 59), at(5, 1)),
        (schedule_of(at_time=time(23, 30)), at(5, 12), at(4, 23, 30)),
        (SUNDAY_AT_2_30, at(4, 2, 29), at(27, 2, 30, month=9)),
        (SUNDAY_AT_2_30, at(4, 2, 30), at(4, 2, 30)),
        (SUNDAY_AT_2_30, at(7, 12), at(4, 2, 30)),
        (schedule_of(frequency="weekly", weekday=1), at(5, 0, 30), at(28, 1, 0, month=9)),
    ],
)
def test_the_latest_occurrence_of_a_schedule_is_the_last_time_it_names_at_or_before_now(
    schedule: Schedule, now: datetime, expected: datetime
) -> None:
    assert latest_occurrence(schedule, now) == expected


def submitted(database: Database, when: datetime, requested_by: UUID | None = None) -> None:
    """Write a backup task, ended, submitted at an instant; the platform's without a requester."""
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=new_id(),
                kind="backup",
                status="succeeded",
                progress=100,
                payload={},
                requested_by=requested_by,
                correlation_id="test-backup-planned",
                attempts=1,
                submitted_at=when,
                started_at=when,
                finished_at=when,
            )
        )


def due(database: Database, now: datetime) -> bool:
    """Ask the module of the backups whether the platform owes a backup at an instant."""
    with database.transaction() as session:
        return backup_is_due(session, now)


def installed_at(database: Database) -> datetime:
    """Read when the schedule was written last: for a new installation, when it was installed."""
    with database.transaction() as session:
        return session.get_one(BackupSchedule, 1).updated_at


def one_o_clock_after(instant: datetime) -> datetime:
    """Give the first 01:00, universal time, after an instant."""
    first = datetime.combine(instant.date(), time(1, 0), tzinfo=UTC)
    return first if first > instant else first + DAY


@pytest.mark.requirement("WF-ADM-0170-A")
def test_on_a_new_installation_a_backup_is_due_every_day_at_one_o_clock_without_any_schedule_set(
    database: Database,
) -> None:
    # « Sur une installation neuve, une sauvegarde est produite chaque jour sans qu'aucune
    # planification ait été saisie. » : the schedule the migrations ship is enabled and daily at
    # 01:00 UTC; the first backup is due at the first 01:00 after the installation, and the next
    # one a day later, the platform having deposited the first.
    first = one_o_clock_after(installed_at(database))
    assert not due(database, first - MINUTE)
    assert due(database, first)
    assert due(database, first + 5 * MINUTE)
    submitted(database, first + MINUTE)
    assert not due(database, first + 5 * MINUTE)
    assert not due(database, first + DAY - MINUTE)
    assert due(database, first + DAY)
    submitted(database, first + DAY + MINUTE)
    assert not due(database, first + DAY + 5 * MINUTE)
    assert due(database, first + 2 * DAY)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_backup_missed_is_deposited_once_and_not_once_per_occurrence_missed(
    database: Database,
) -> None:
    installation = installed_at(database)
    submitted(database, installation + MINUTE)
    assert due(database, installation + 5 * DAY)
    submitted(database, installation + 5 * DAY)
    assert not due(database, installation + 5 * DAY + 5 * MINUTE)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_backup_an_administrator_asked_for_does_not_stand_for_the_one_the_platform_owes(
    database: Database,
) -> None:
    # The latest backup the platform deposited of itself is what the schedule reads: a manual one,
    # asked for by an account, leaves the scheduled one due.
    first = one_o_clock_after(installed_at(database)) + 2 * DAY
    submitted(database, first + MINUTE, requested_by=account(database, "Durand", "Paul"))
    assert due(database, first + 5 * MINUTE)


def set_schedule(database: Database, writing: ScheduleWriting, at_instant: datetime) -> None:
    """Write the schedule as an administrator does, at an instant.

    The row is taken as installed at that instant first: whatever the writing changes of the
    timing is then dated by it, and a writing that changes none leaves the instant as it was.
    """
    with database.transaction() as session:
        session.execute(update(BackupSchedule).values(updated_at=at_instant))
    rewrite(database, writing, at_instant)


def rewrite(database: Database, writing: ScheduleWriting, at_instant: datetime) -> None:
    """Write the schedule as an administrator does, at an instant, the row as it stands."""
    with database.transaction() as session:
        held = read_backup_schedule(session).lock_version
        schedule = judged_schedule(writing, set())
        write_backup_schedule(session, schedule, held, Act(None, at_instant))


def written(**changes: Any) -> ScheduleWriting:
    """Give a writing of the shipped schedule, with the changes a test asks for."""
    values: dict[str, Any] = {
        "is_enabled": True,
        "frequency": "daily",
        "at_time": "01:00",
        "weekday": None,
        "retained_count": 7,
        "external_copy": None,
    } | changes
    return ScheduleWriting(**values)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_disabled_schedule_owes_no_backup(database: Database) -> None:
    set_schedule(database, written(is_enabled=False), utc_now() - 10 * DAY)
    assert not due(database, utc_now() + 5 * DAY)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_schedule_that_has_just_been_written_owes_nothing_for_the_time_it_has_passed(
    database: Database,
) -> None:
    # Written at 10:00 for 09:00, it takes its first backup at 09:00 the next day: not one at once.
    written_at = datetime.combine(utc_now().date(), time(10, 0), tzinfo=UTC)
    set_schedule(database, written(at_time="09:00"), written_at)
    assert not due(database, written_at + MINUTE)
    assert not due(database, written_at + 23 * HOUR - MINUTE)
    assert due(database, written_at + 23 * HOUR)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_retention_written_just_after_the_hour_leaves_the_backup_of_the_day_due(
    database: Database,
) -> None:
    # The schedule is daily at 01:00, long written; its retention alone is written at 01:00:30: the
    # backup of 01:00 is still owed, a timing unchanged not being a schedule newly announced.
    day = datetime.combine(utc_now().date(), time(1, 0), tzinfo=UTC)
    set_schedule(database, written(), day - 10 * DAY)
    rewrite(database, written(retained_count=3), day + timedelta(seconds=30))
    assert due(database, day + MINUTE)
    # Moved, the same writing does announce a new time: nothing is owed for the one passed.
    rewrite(database, written(at_time="00:30", retained_count=3), day + timedelta(seconds=40))
    assert not due(database, day + MINUTE)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_weekly_schedule_is_due_on_its_day_of_the_week_alone(database: Database) -> None:
    # Weekly, on the Sunday at 02:30, written long ago: due on the Sunday at 02:30 until the
    # platform has deposited it, then not until the next Sunday, whatever the days in between.
    set_schedule(
        database,
        written(frequency="weekly", weekday=7, at_time="02:30"),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert due(database, at(4, 2, 30))
    submitted(database, at(4, 2, 31))
    assert not due(database, at(4, 2, 40))
    assert not due(database, at(10, 23))
    assert due(database, at(11, 2, 30))


def backup_plan() -> tuple[Planned, ...]:
    """Give the line of ``planned`` that schedules the backups, and none of the others."""
    return tuple(each for each in planned(SETTINGS) if each.kind == "backup")


@pytest.mark.requirement("WF-ADM-0170-A")
def test_the_planned_command_deposits_a_backup_of_the_platform_once_when_it_is_due(
    database: Database, queue: TaskQueue
) -> None:
    # Due since the 01:00 of the day before and not yet deposited: the command deposits the task
    # of the platform (no requester), once, whatever the number of schedules that look.
    set_schedule(database, written(), utc_now() - 10 * DAY)
    queue.prepare()
    with logging_context(correlation_id="planned-backup"):
        first = deposit_due(database, queue, backup_plan())
        second = deposit_due(database, queue, backup_plan())
    assert (first, second) == (["backup"], [])
    with database.transaction() as session:
        rows = session.execute(
            select(BackgroundTask.kind, BackgroundTask.requested_by, BackgroundTask.status)
        ).all()
    assert [tuple(row) for row in rows] == [("backup", None, "queued")]


@pytest.mark.requirement("WF-ADM-0170-A")
def test_the_backup_the_planned_command_deposits_is_taken_by_the_worker_as_scheduled(
    installation: Installation, queue: TaskQueue
) -> None:
    # « Une sauvegarde planifiée quotidiennement est présente chaque jour dans la liste. » : the
    # installation was installed ten days ago, its schedule shipped: the command deposits the
    # backup, the worker takes it, and the list holds it, scheduled and verified.
    database = installation.database
    with database.transaction() as session:
        session.execute(update(BackupSchedule).values(updated_at=utc_now() - 10 * DAY))
    queue.prepare()
    with logging_context(correlation_id="planned-backup"):
        assert deposit_due(database, queue, backup_plan()) == ["backup"]
    worker = Worker(
        database,
        queue,
        {"backup": BackupTask(installation.backup, installation.bucket)},
        "worker-planned",
        Timing(0, 0.1),
    )
    assert worker.step()
    with database.transaction() as session:
        rows = session.execute(select(Backup.origin, Backup.verification)).all()
    assert [tuple(row) for row in rows] == [("scheduled", "passed")]
    with logging_context(correlation_id="planned-backup"):
        assert deposit_due(database, queue, backup_plan()) == []


# The kinds the purge keeps the latest of that the planned command does not schedule: the copy a
# backup deposits, and the test of a restoration, which US-2930 will plan.
NOT_PLANNED_BY_THE_COMMAND = {"backup_copy", "restore_test"}


def test_every_kind_the_planned_command_schedules_is_one_the_purge_keeps_the_latest_of() -> None:
    # #4347: a kind added to ``planned`` and not to ``PLANNED_KINDS`` would see its latest task
    # purged, and its schedule read it due again at once after each purge; and a kind of
    # ``PLANNED_KINDS`` that nothing schedules is named, not silently kept.
    planned_kinds = {each.kind for each in planned(SETTINGS)}
    assert "backup" in planned_kinds
    assert planned_kinds == set(PLANNED_KINDS) - NOT_PLANNED_BY_THE_COMMAND
    assert set(PLANNED_KINDS) >= NOT_PLANNED_BY_THE_COMMAND


def restore_queued(database: Database) -> None:
    """Write a restoration queued, as ``startRestore`` leaves it."""
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=new_id(),
                kind="restore",
                status="queued",
                progress=0,
                payload={},
                requested_by=None,
                correlation_id="test-backup-planned",
                attempts=0,
                submitted_at=utc_now(),
            )
        )


def backups_pending(database: Database) -> int:
    """Count the backups queued or running."""
    with database.transaction() as session:
        return len(
            session.execute(
                select(BackgroundTask.id).where(
                    BackgroundTask.kind == "backup", BackgroundTask.status.in_(PENDING)
                )
            ).all()
        )


@pytest.mark.requirement("WF-ADM-0170-A")
def test_the_planned_command_deposits_no_backup_while_a_restoration_is_queued(
    database: Database, queue: TaskQueue
) -> None:
    # The conditions of ``startBackup``: a backup is not deposited beside a restoration, which
    # replaces the database it would copy; once the restoration is over, the backup is deposited.
    set_schedule(database, written(), utc_now() - 10 * DAY)
    queue.prepare()
    restore_queued(database)
    with logging_context(correlation_id="planned-backup"):
        assert deposit_due(database, queue, backup_plan()) == []
    assert backups_pending(database) == 0
    with database.transaction() as session:
        restored = update(BackgroundTask).where(BackgroundTask.kind == "restore")
        session.execute(restored.values(status="succeeded", finished_at=utc_now()))
    with logging_context(correlation_id="planned-backup"):
        assert deposit_due(database, queue, backup_plan()) == ["backup"]


def planned_deposit(database: Database, queue: TaskQueue) -> list[str]:
    """Run the planned command for the backups, in a thread of its own."""
    with logging_context(correlation_id="planned-backup"):
        return deposit_due(database, queue, backup_plan())


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_backup_asked_for_and_the_planned_command_run_together_leave_one_backup_queued(
    database: Database, queue: TaskQueue
) -> None:
    # ``post_backup`` and the command deposit under the same locks and conditions: whichever
    # comes second sees the first one's task and deposits none.
    set_schedule(database, written(), utc_now() - 10 * DAY)
    queue.prepare()
    entered = threading.Event()
    release = threading.Event()

    def asked_for() -> None:
        with logging_context(correlation_id="asked-for-backup"), database.transaction() as session:
            session.execute(select(func.pg_advisory_xact_lock(BACKUP_LOCK)))
            session.execute(select(func.pg_advisory_xact_lock_shared(RESTORE_LOCK)))
            refuse_if_lacking(backup_start_lacks(platform_of(session)))
            submit(session, queue, "backup", None)
            entered.set()
            release.wait(10)

    with ThreadPoolExecutor(max_workers=2) as pool:
        asking = pool.submit(asked_for)
        assert entered.wait(10)
        planned_run = pool.submit(planned_deposit, database, queue)
        clock.sleep(0.5)
        assert not planned_run.done()
        release.set()
        asking.result(10)
        assert planned_run.result(10) == []
    assert backups_pending(database) == 1
