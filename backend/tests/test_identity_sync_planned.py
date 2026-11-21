# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned command deposits a reading of the accounts when the schedule of the readings says so.

The schedule of the readings (``identity_sync_schedule``, written by the migrations and then by an
administrator) says at which time, universal time, the platform reads the accounts of its identity
provider, every day or one day of the week (WF-ADM-0070, US-3040); ``planned`` asks the module of
the accounts whether a reading is due, and ``deposit_due`` deposits the task ``identity_sync``, as
the one an administrator asks for. A new installation reads every day without any schedule entered.
"""

from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from access_rows import account
from sqlalchemy import insert, select, update

from waterfall.core.users.interface import (
    SyncScheduleWriting,
    judged_sync_schedule,
    read_sync_schedule,
    sync_is_due,
    write_sync_schedule,
)
from waterfall.core.users.tables import IdentitySyncSchedule
from waterfall.platform.audit import Act
from waterfall.platform.database import Database, utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ScheduleSettings
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.schedule import Planned, deposit_due, planned

if TYPE_CHECKING:
    from uuid import UUID

    from waterfall.platform.queue import TaskQueue

pytestmark = pytest.mark.story("US-3040")

SETTINGS = ScheduleSettings.model_construct(purge_interval=600)
MINUTE = timedelta(minutes=1)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def at(day: int, hour: int = 0, minute: int = 0, month: int = 10) -> datetime:
    """Give an instant of 2026, universal time: the 1st of October is a Thursday."""
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


def written(**changes: Any) -> SyncScheduleWriting:
    """Give a writing of the shipped schedule, with the changes a test asks for."""
    values: dict[str, Any] = {
        "is_enabled": True,
        "frequency": "daily",
        "at_time": "01:30",
        "weekday": None,
    } | changes
    return SyncScheduleWriting(**values)


def set_schedule(database: Database, writing: SyncScheduleWriting, at_instant: datetime) -> None:
    """Write the schedule as an administrator does, at an instant.

    The timing is taken as dated by that instant first: whatever the writing changes of it is then
    dated by the instant, and a writing that changes none leaves it as it was.
    """
    with database.transaction() as session:
        session.execute(update(IdentitySyncSchedule).values(timing_changed_at=at_instant))
    rewrite(database, writing, at_instant)


def rewrite(database: Database, writing: SyncScheduleWriting, at_instant: datetime) -> None:
    """Write the schedule as an administrator does, at an instant, the row as it stands."""
    with database.transaction() as session:
        held = read_sync_schedule(session).lock_version
        write_sync_schedule(session, judged_sync_schedule(writing), held, Act(None, at_instant))


def submitted(
    database: Database,
    when: datetime,
    status: str = "succeeded",
    requested_by: UUID | None = None,
) -> None:
    """Write a reading task at an instant; the platform's without a requester."""
    ended = status in {"succeeded", "failed"}
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=new_id(),
                kind="identity_sync",
                status=status,
                progress=100 if ended else 0,
                payload={},
                requested_by=requested_by,
                correlation_id="test-identity-sync-planned",
                attempts=1,
                submitted_at=when,
                started_at=None if status == "queued" else when,
                finished_at=when if ended else None,
            )
        )


def due(database: Database, now: datetime) -> bool:
    """Ask the module of the accounts whether the platform owes a reading at an instant."""
    with database.transaction() as session:
        return sync_is_due(session, now)


def installed_at(database: Database) -> datetime:
    """Read when the schedule was written last: for a new installation, when it was installed."""
    with database.transaction() as session:
        return session.get_one(IdentitySyncSchedule, 1).timing_changed_at


def half_past_one_after(instant: datetime) -> datetime:
    """Give the first 01:30, universal time, after an instant."""
    first = datetime.combine(instant.date(), time(1, 30), tzinfo=UTC)
    return first if first > instant else first + DAY


@pytest.mark.requirement("WF-ADM-0070-A")
def test_on_a_new_installation_a_reading_is_due_every_day_at_half_past_one_without_any_schedule_set(
    database: Database,
) -> None:
    # Enabled and daily at 01:30 UTC as shipped: the first reading is due at the first 01:30 after
    # the installation, and the next one a day later, the platform having deposited the first.
    first = half_past_one_after(installed_at(database))
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


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_reading_missed_is_deposited_once_and_not_once_per_occurrence_missed(
    database: Database,
) -> None:
    installation = installed_at(database)
    submitted(database, installation + MINUTE)
    assert due(database, installation + 5 * DAY)
    submitted(database, installation + 5 * DAY)
    assert not due(database, installation + 5 * DAY + 5 * MINUTE)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_reading_an_administrator_asked_for_does_not_stand_for_the_one_the_platform_owes(
    database: Database,
) -> None:
    # The latest reading the platform deposited of itself is what the schedule reads: one asked
    # for by an account, on demand, leaves the scheduled one due.
    first = half_past_one_after(installed_at(database)) + 2 * DAY
    submitted(database, first + MINUTE, requested_by=account(database, "Durand", "Paul"))
    assert due(database, first + 5 * MINUTE)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_disabled_schedule_owes_no_reading(database: Database) -> None:
    set_schedule(database, written(is_enabled=False), utc_now() - 10 * DAY)
    assert not due(database, utc_now() + 5 * DAY)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_schedule_that_has_just_been_written_owes_nothing_for_the_time_it_has_passed(
    database: Database,
) -> None:
    # Written at 10:00 for 09:00, it takes its first reading at 09:00 the next day: not one at once.
    written_at = datetime.combine(utc_now().date(), time(10, 0), tzinfo=UTC)
    set_schedule(database, written(at_time="09:00"), written_at)
    assert not due(database, written_at + MINUTE)
    assert not due(database, written_at + 23 * HOUR - MINUTE)
    assert due(database, written_at + 23 * HOUR)


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_schedule_written_again_unchanged_still_owes_the_occurrence_it_was_written_just_after(
    database: Database,
) -> None:
    # The occurrence of 01:30 is not deposited yet when the same schedule is written at 01:31: it
    # stays owed. Written moved, it owes nothing for the occurrence it has passed.
    set_schedule(database, written(), at(1, 0, 0))
    assert due(database, at(2, 1, 30))
    rewrite(database, written(), at(2, 1, 31))
    assert due(database, at(2, 1, 35))
    rewrite(database, written(at_time="01:00"), at(2, 1, 36))
    assert not due(database, at(2, 1, 40))
    assert due(database, at(3, 1, 0))


@pytest.mark.requirement("WF-ADM-0070-A")
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


def reading_plan() -> tuple[Planned, ...]:
    """Give the line of ``planned`` that schedules the readings, and none of the others."""
    return tuple(each for each in planned(SETTINGS) if each.kind == "identity_sync")


def tasks(database: Database) -> list[tuple[Any, ...]]:
    """List the tasks written: kind, requester and state."""
    with database.transaction() as session:
        rows = session.execute(
            select(BackgroundTask.kind, BackgroundTask.requested_by, BackgroundTask.status)
        ).all()
    return [tuple(row) for row in rows]


@pytest.mark.requirement("WF-ADM-0070-A")
def test_the_planned_command_deposits_a_reading_of_the_platform_once_when_it_is_due(
    database: Database, queue: TaskQueue
) -> None:
    # « Une personne ajoutée à l'annuaire a un compte dans Waterfall au terme de la périodicité
    # choisie, sans intervention. » Due since the 01:30 of the day before and not yet deposited:
    # the command deposits the task of the platform (no requester), once, whatever the number of
    # schedules that look; the worker reads the accounts when it takes it.
    set_schedule(database, written(), utc_now() - 10 * DAY)
    queue.prepare()
    with logging_context(correlation_id="planned-identity-sync"):
        first = deposit_due(database, queue, reading_plan())
        second = deposit_due(database, queue, reading_plan())
    assert (first, second) == (["identity_sync"], [])
    assert tasks(database) == [("identity_sync", None, "queued")]
    assert len(queue.waiting()) == 1


@pytest.mark.requirement("WF-ADM-0070-A")
def test_a_weekly_schedule_is_deposited_by_the_planned_command_once_in_the_week(
    database: Database, queue: TaskQueue
) -> None:
    # Weekly on the day of the week before yesterday, written long ago, the platform having read
    # the accounts ten days ago: the command deposits the reading the week owes, once.
    now = utc_now()
    day = (now - 2 * DAY).isoweekday()
    weekly = written(frequency="weekly", weekday=day, at_time="00:00")
    set_schedule(database, weekly, now - 30 * DAY)
    submitted(database, now - 10 * DAY)
    queue.prepare()
    with logging_context(correlation_id="planned-identity-sync"):
        assert deposit_due(database, queue, reading_plan()) == ["identity_sync"]
        assert deposit_due(database, queue, reading_plan()) == []


@pytest.mark.requirement("WF-ADM-0070-A")
def test_the_planned_command_deposits_no_reading_when_the_schedule_is_disabled(
    database: Database, queue: TaskQueue
) -> None:
    set_schedule(database, written(is_enabled=False), utc_now() - 10 * DAY)
    queue.prepare()
    with logging_context(correlation_id="planned-identity-sync"):
        assert deposit_due(database, queue, reading_plan()) == []
    assert tasks(database) == []


@pytest.mark.requirement("WF-ADM-0070-A")
@pytest.mark.parametrize("status", ["queued", "running"])
@pytest.mark.parametrize("asked", [False, True])
def test_the_planned_command_deposits_no_reading_while_one_is_queued_or_running(
    database: Database, queue: TaskQueue, status: str, asked: bool
) -> None:
    # Due, but a reading is in the queue or being run — the platform's, or one asked for on
    # demand: none is deposited, and the schedule written again unchanged meanwhile does not take
    # the occurrence from the platform: once the reading has ended, the one owed is deposited.
    set_schedule(database, written(), utc_now() - 10 * DAY)
    requester = account(database, "Durand", "Paul") if asked else None
    submitted(database, utc_now() - 3 * DAY, status=status, requested_by=requester)
    queue.prepare()
    with logging_context(correlation_id="planned-identity-sync"):
        assert deposit_due(database, queue, reading_plan()) == []
    assert len(tasks(database)) == 1
    rewrite(database, written(), utc_now())
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask).values(
                status="succeeded", progress=100, finished_at=utc_now() - 2 * DAY
            )
        )
    with logging_context(correlation_id="planned-identity-sync"):
        assert deposit_due(database, queue, reading_plan()) == ["identity_sync"]
