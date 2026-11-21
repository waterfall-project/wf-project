# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule of the backups: when the platform backs itself up, how many it keeps, and where.

One row, which the migrations write at its shipped values — daily at 01:00 UTC, seven kept, no
external copy (WF-ADM-0170, WF-EXP-0050) — and an administrator then writes whole. A writing is
judged all at once, each field in default named with its reason (422), before anything is read;
then written under the counter of the row, read under its lock (412). The external copy names a
location the installation declares, a folder in it, and keeps at least as many copies as the
platform keeps backups (WF-EXP-0050). A restoration keeps the schedule, as it keeps the list it
governs (``keep_for_restoration``, #1743).
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from waterfall.core.backups.tables import (
    LOCATION_FORM,
    PATH_FORM,
    PATH_LENGTH,
    RETENTIONS,
    SINGLE_ROW,
    BackupSchedule,
)
from waterfall.platform.errors import (
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    FieldError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.tasks import last_submitted

if TYPE_CHECKING:
    from collections.abc import Collection

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
UNKNOWN_EXTERNAL_BACKUP_LOCATION = "UNKNOWN_EXTERNAL_BACKUP_LOCATION"
PATH_INVALID = "PATH_INVALID"
WEEKLY = "weekly"
# The days of a weekly backup, 1 Monday to 7 Sunday (ISO 8601).
WEEKDAYS = (1, 7)
# A time ``HH:MM``, as the contract writes it (`BackupSchedule.at_time`): digits of 0 to 9 alone,
# which ``\d`` would not keep to.
AT_TIME = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")
LOCATION = re.compile(LOCATION_FORM.removeprefix("^").removesuffix("$"))
PATH = re.compile(PATH_FORM.removeprefix("^").removesuffix("$"))


@dataclass(frozen=True, slots=True)
class ExternalCopy:
    """The copy of each scheduled backup to a location: suspended or not, where, how many kept."""

    is_enabled: bool
    location: str
    path: str
    retained_count: int


@dataclass(frozen=True, slots=True)
class ScheduleWriting:
    """A schedule as a writing sends it, not judged yet: the time as its text."""

    is_enabled: bool
    frequency: str
    at_time: str
    weekday: int | None
    retained_count: int
    external_copy: ExternalCopy | None


@dataclass(frozen=True, slots=True)
class Schedule:
    """A schedule judged: the time in universal time, to the minute; no copy set when ``None``."""

    is_enabled: bool
    frequency: str
    at_time: time
    weekday: int | None
    retained_count: int
    external_copy: ExternalCopy | None


@dataclass(frozen=True, slots=True)
class BackupScheduleView:
    """The schedule of the backups as it is, and the counter of its writes."""

    schedule: Schedule
    lock_version: int


def _bounded(pointer: str, value: int, least: int) -> list[FieldError]:
    """Refuse a retention below ``least`` or beyond the longest, naming the one bound crossed."""
    if value < least:
        return [FieldError(pointer, VALUE_OUT_OF_RANGE, {"minimum": least})]
    if value > RETENTIONS[1]:
        return [FieldError(pointer, VALUE_OUT_OF_RANGE, {"maximum": RETENTIONS[1]})]
    return []


def _weekday_faults(frequency: str, weekday: int | None) -> list[FieldError]:
    """Ask a day of a weekly schedule, within the week, and refuse one to a daily schedule."""
    if frequency != WEEKLY:
        return [] if weekday is None else [FieldError("/weekday", VALIDATION_FAILED)]
    if weekday is None:
        return [FieldError("/weekday", VALUE_REQUIRED)]
    if weekday < WEEKDAYS[0]:
        return [FieldError("/weekday", VALUE_OUT_OF_RANGE, {"minimum": WEEKDAYS[0]})]
    if weekday > WEEKDAYS[1]:
        return [FieldError("/weekday", VALUE_OUT_OF_RANGE, {"maximum": WEEKDAYS[1]})]
    return []


def _copy_faults(copy: ExternalCopy, declared: Collection[str], least: int) -> list[FieldError]:
    """Judge the copy: a location declared, a relative folder in it, at least ``least`` kept.

    A name that is not one of a location (`ExternalBackupLocationName`) is malformed; one that is,
    and that the installation does not declare, is unknown.
    """
    faults: list[FieldError] = []
    if LOCATION.fullmatch(copy.location) is None:
        faults.append(FieldError("/external_copy/location", VALIDATION_FAILED))
    elif copy.location not in declared:
        params = {"location": copy.location}
        faults.append(
            FieldError("/external_copy/location", UNKNOWN_EXTERNAL_BACKUP_LOCATION, params)
        )
    if not copy.path:
        faults.append(FieldError("/external_copy/path", VALUE_REQUIRED))
    elif len(copy.path) > PATH_LENGTH:
        params = {"max_length": PATH_LENGTH}
        faults.append(FieldError("/external_copy/path", VALUE_TOO_LONG, params))
    elif PATH.fullmatch(copy.path) is None:
        faults.append(FieldError("/external_copy/path", PATH_INVALID))
    faults.extend(_bounded("/external_copy/retained_count", copy.retained_count, least))
    return faults


def judged_schedule(writing: ScheduleWriting, declared: Collection[str]) -> Schedule:
    """Give the schedule a writing sends, or refuse (422) every field in default, in their order.

    ``declared`` names the locations the installation declares. The copy keeps at least as many
    copies as the platform keeps backups; at least one when the platform's retention is itself out
    of its bounds (`BackupExternalCopy.retained_count`).
    """
    faults: list[FieldError] = []
    held = AT_TIME.fullmatch(writing.at_time)
    if held is None:
        faults.append(FieldError("/at_time", VALIDATION_FAILED))
    faults.extend(_weekday_faults(writing.frequency, writing.weekday))
    platform = _bounded("/retained_count", writing.retained_count, RETENTIONS[0])
    faults.extend(platform)
    if writing.external_copy is not None:
        least = RETENTIONS[0] if platform else writing.retained_count
        faults.extend(_copy_faults(writing.external_copy, declared, least))
    if faults or held is None:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return Schedule(
        writing.is_enabled,
        writing.frequency,
        time(int(held[1]), int(held[2])),
        writing.weekday,
        writing.retained_count,
        writing.external_copy,
    )


def _view(row: BackupSchedule) -> BackupScheduleView:
    copy = None
    if row.external_copy_is_enabled is not None:
        copy = ExternalCopy(
            row.external_copy_is_enabled,
            row.external_copy_location or "",
            row.external_copy_path or "",
            row.external_copy_retained_count or 0,
        )
    schedule = Schedule(
        row.is_enabled, row.frequency, row.at_time, row.weekday, row.retained_count, copy
    )
    return BackupScheduleView(schedule, row.lock_version)


def read_backup_schedule(session: Session) -> BackupScheduleView:
    """Give the schedule of the backups: the one row the migrations write, then the writings."""
    return _view(session.get_one(BackupSchedule, SINGLE_ROW))


def write_backup_schedule(
    session: Session, schedule: Schedule, lock_version: int, act: Act
) -> BackupScheduleView:
    """Write the schedule whole, under the counter the writer read; give it as written.

    The row is locked, then read: a counter that is not its own is refused (412), and nothing is
    written. A copy absent removes the one set.

    ``updated_at`` and ``updated_by`` are those of every writing (WF-DAT-0070).
    ``timing_changed_at`` says when the *timing* last changed — enabled, frequency, time, weekday —,
    which is what ``backup_is_due`` takes as the base of what is owed: a writing of the retention
    or of the copy alone leaves it, so that it does not make a backup skip the occurrence it was
    written just after.
    """
    held = session.scalars(
        select(BackupSchedule)
        .where(BackupSchedule.id == SINGLE_ROW)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if held.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": held.lock_version}
        )
    copy = schedule.external_copy
    retimed = (held.is_enabled, held.frequency, held.at_time, held.weekday) != (
        schedule.is_enabled,
        schedule.frequency,
        schedule.at_time,
        schedule.weekday,
    )
    stamp = {"timing_changed_at": act.at} if retimed else {}
    session.execute(
        update(BackupSchedule)
        .where(BackupSchedule.id == SINGLE_ROW)
        .values(
            is_enabled=schedule.is_enabled,
            frequency=schedule.frequency,
            at_time=schedule.at_time,
            weekday=schedule.weekday,
            retained_count=schedule.retained_count,
            external_copy_is_enabled=None if copy is None else copy.is_enabled,
            external_copy_location=None if copy is None else copy.location,
            external_copy_path=None if copy is None else copy.path,
            external_copy_retained_count=None if copy is None else copy.retained_count,
            lock_version=lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
            **stamp,
        )
    )
    return BackupScheduleView(schedule, lock_version + 1)


def latest_occurrence(schedule: Schedule, now: datetime) -> datetime:
    """Give the latest moment, ``now`` included, at which the schedule says a backup is taken.

    Daily, the time of the day; weekly, the time of the day of the week (1 Monday to 7 Sunday).
    All in universal time.
    """
    today = now.astimezone(UTC).date()
    day = today
    if schedule.frequency == WEEKLY and schedule.weekday is not None:
        day = today - timedelta(days=(today.isoweekday() - schedule.weekday) % 7)
    occurrence = datetime.combine(day, schedule.at_time, tzinfo=UTC)
    if occurrence > now:
        occurrence -= timedelta(days=7 if schedule.frequency == WEEKLY else 1)
    return occurrence


def backup_is_due(session: Session, now: datetime) -> bool:
    """Tell whether the platform owes a backup of itself at ``now`` (WF-ADM-0170).

    It is when the schedule is enabled and its latest occurrence is later than the latest backup
    the platform deposited of itself, and later than the last change of its timing
    (``timing_changed_at``, see ``write_backup_schedule``): a schedule just enabled, moved or
    installed owes nothing for an occurrence it did not announce; one whose retention or copy alone
    is written owes what it owed. A backup deposited late, or not yet deposited, is deposited once,
    not once per occurrence missed.
    """
    row = session.get_one(BackupSchedule, SINGLE_ROW)
    if not row.is_enabled:
        return False
    schedule = _view(row).schedule
    since = max(row.timing_changed_at, last_submitted(session, "backup") or row.timing_changed_at)
    return latest_occurrence(schedule, now) > since
