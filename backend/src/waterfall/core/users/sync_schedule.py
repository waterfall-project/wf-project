# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule of the readings of the accounts: when the platform reads its identity provider.

One row, which the migrations write at its shipped values — every day at 01:30 UTC, enabled, half
an hour after the shipped backup (WF-ADM-0070) — and an administrator then writes whole, as the
schedule of the backups is written (``waterfall.core.backups.schedule``). A writing is judged all
at once, each field in default named with its reason (422), before anything is read; then written
under the counter of the row, read under its lock (412). A restoration does not keep it: the
specification names it not among what a restoration keeps (WF-ADM-0160, #4126).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.users.tables import SINGLE_ROW, IdentitySyncSchedule
from waterfall.platform import timing
from waterfall.platform.errors import (
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    FieldError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.tasks import last_submitted
from waterfall.platform.timing import parsed_time, weekday_faults

if TYPE_CHECKING:
    from datetime import datetime, time

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act


@dataclass(frozen=True, slots=True)
class SyncScheduleWriting:
    """A schedule as a writing sends it, not judged yet: the time as its text."""

    is_enabled: bool
    frequency: str
    at_time: str
    weekday: int | None


@dataclass(frozen=True, slots=True)
class SyncSchedule:
    """A schedule judged: the time in universal time, to the minute."""

    is_enabled: bool
    frequency: str
    at_time: time
    weekday: int | None


@dataclass(frozen=True, slots=True)
class SyncScheduleView:
    """The schedule of the readings as it is, and the counter of its writes."""

    schedule: SyncSchedule
    lock_version: int


def judged_sync_schedule(writing: SyncScheduleWriting) -> SyncSchedule:
    """Give the schedule a writing sends, or refuse (422) every field in default, in their order."""
    faults: list[FieldError] = []
    held = parsed_time(writing.at_time)
    if held is None:
        faults.append(FieldError("/at_time", VALIDATION_FAILED))
    faults.extend(weekday_faults(writing.frequency, writing.weekday))
    if faults or held is None:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return SyncSchedule(writing.is_enabled, writing.frequency, held, writing.weekday)


def _view(row: IdentitySyncSchedule) -> SyncScheduleView:
    schedule = SyncSchedule(row.is_enabled, row.frequency, row.at_time, row.weekday)
    return SyncScheduleView(schedule, row.lock_version)


def read_sync_schedule(session: Session) -> SyncScheduleView:
    """Give the schedule of the readings: the one row the migrations write, then the writings."""
    return _view(session.get_one(IdentitySyncSchedule, SINGLE_ROW))


def write_sync_schedule(
    session: Session, schedule: SyncSchedule, lock_version: int, act: Act
) -> SyncScheduleView:
    """Write the schedule whole, under the counter the writer read; give it as written.

    The row is locked, then read: a counter that is not its own is refused (412), and nothing is
    written. Every field of the schedule is its timing, so ``updated_at``, the date of every
    writing (WF-DAT-0070), is also the instant ``sync_is_due`` takes as the base of what is owed.
    """
    held = session.scalars(
        select(IdentitySyncSchedule)
        .where(IdentitySyncSchedule.id == SINGLE_ROW)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if held.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": held.lock_version}
        )
    session.execute(
        update(IdentitySyncSchedule)
        .where(IdentitySyncSchedule.id == SINGLE_ROW)
        .values(
            is_enabled=schedule.is_enabled,
            frequency=schedule.frequency,
            at_time=schedule.at_time,
            weekday=schedule.weekday,
            lock_version=lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    return SyncScheduleView(schedule, lock_version + 1)


def sync_is_due(session: Session, now: datetime) -> bool:
    """Tell whether the platform owes a reading of the accounts at ``now`` (WF-ADM-0070).

    It is when the schedule is enabled and its latest occurrence is later than the latest reading
    the platform deposited of itself, and later than its last writing (``updated_at``, which the
    installation sets as it writes the row): a schedule just enabled, moved or installed owes
    nothing for an occurrence it did not announce. A reading asked for by an administrator is
    another reading, which does not count; one deposited late, or not yet deposited, is deposited
    once, not once per occurrence missed.
    """
    row = session.get_one(IdentitySyncSchedule, SINGLE_ROW)
    if not row.is_enabled:
        return False
    since = max(row.updated_at, last_submitted(session, "identity_sync") or row.updated_at)
    schedule = _view(row).schedule
    occurrence = timing.latest_occurrence(
        schedule.frequency, schedule.weekday, schedule.at_time, now
    )
    return occurrence > since
