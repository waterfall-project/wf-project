# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars, one of them the default.

Read, listed, created, changed, deactivated, reactivated and designated the default
(WF-REF-0110, 0120). A calendar is a label, unique among the calendars deactivated ones included,
and the hours worked on each day of the week, from 0 to 24; one calendar, active, is the default,
which the database keeps single (a partial unique index) and the designation, under a lock of
transaction, moves from one to another. Nothing is deleted. No write is inscribed in the journal
of audit: the columns of audit of the row say who touched it last (EP-05, "Ce que le cadrage
décide").
"""

from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from waterfall.core.resource_settings.interface.extensions import (
    CalendarChange,
    projects_left_idle,
    recalculate,
)
from waterfall.core.resource_settings.interface.readiness import lock_reference
from waterfall.core.resource_settings.tables import DAYS, Calendar
from waterfall.platform.database import contains, unique_violated
from waterfall.platform.errors import (
    STATE_FORBIDS_OPERATION,
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
    json_pointer,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Generator, Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
ALREADY_EXISTS = "ALREADY_EXISTS"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
TASK_WITHOUT_WORKING_HOURS = "TASK_WITHOUT_WORKING_HOURS"
# What an activation or a designation lacks, as a command says it in advance (``CommandCondition``).
CALENDAR_ACTIVE = "calendar_active"
CALENDAR_NOT_DEFAULT = "calendar_not_default"
# The bounds of the hours of a day, and the decimals an hour is written with (``numeric(4,2)``).
LEAST_HOURS = Decimal(0)
GREATEST_HOURS = Decimal(24)
HOURS_SCALE = 2
# The unique index of the label, named as the naming convention names it.
LABEL_INDEX = "uq_calendar_label"
# The key of the advisory lock of the designation: the default is single, whatever the order two
# transactions take its rows in.
DEFAULT_LOCK = 2_200_860
# The first version of a calendar, as the examples of the contract have it.
FIRST_VERSION = 1

type CalendarColumn = Literal[
    "label",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "weekly_hours",
    "is_default",
    "is_active",
]


@dataclass(frozen=True, slots=True)
class WeeklyHours:
    """The hours worked on each day of the week."""

    monday: Decimal
    tuesday: Decimal
    wednesday: Decimal
    thursday: Decimal
    friday: Decimal
    saturday: Decimal
    sunday: Decimal

    def of(self, day: str) -> Decimal:
        """Give the hours of a day, named as the columns and the contract name it."""
        hours: Decimal = getattr(self, day)
        return hours


@dataclass(frozen=True, slots=True)
class CalendarContent:
    """What a calendar is written with: a label and the hours of each day, and nothing else."""

    label: str
    weekly_hours: WeeklyHours


@dataclass(frozen=True, slots=True)
class CalendarView:
    """A calendar as it is read."""

    calendar_id: UUID
    label: str
    weekly_hours: WeeklyHours
    is_default: bool
    is_active: bool
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class CalendarCommand:
    """A command of a calendar, available or not, and the conditions that lack to it."""

    command: Literal["deactivate", "reactivate", "set_default"]
    is_available: bool
    missing_conditions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CalendarFilters:
    """What the table of the calendars keeps (WF-IHM-0130).

    The hours of a day are sorted and never filtered, and the default one, single, is not either
    (C-352). The deactivated are kept when asked for, all of them with ``include_inactive``, alone
    with ``is_active`` false, which prevails over it.
    """

    search: str | None = None
    is_active: bool | None = None
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class CalendarSort:
    """The column of the sort and its direction (WF-IHM-0060).

    Equals keep the order of the table unsorted, by label, then come by identifier, ascending
    whatever the direction. The default calendar comes first in the ascending order of
    ``is_default``, the deactivated after the active in that of ``is_active``.
    """

    column: CalendarColumn = "label"
    descending: bool = False


@dataclass(frozen=True, slots=True)
class CalendarWindow:
    """Which calendars of the order are read: ``limit`` of them, after the first ``offset``."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class CalendarPage:
    """A page of the calendars the filters keep, and how many they keep."""

    calendars: list[CalendarView]
    total: int


def _hours_faults(weekly_hours: WeeklyHours) -> tuple[FieldError, ...]:
    """Name each day whose hours lie out of 0 to 24, or have more decimals than the column keeps."""
    faults: list[FieldError] = []
    for day in DAYS:
        hours = weekly_hours.of(day)
        pointer = json_pointer("weekly_hours", day)
        if hours < LEAST_HOURS:
            faults.append(FieldError(pointer, VALUE_OUT_OF_RANGE, {"minimum": str(LEAST_HOURS)}))
        elif hours > GREATEST_HOURS:
            faults.append(FieldError(pointer, VALUE_OUT_OF_RANGE, {"maximum": str(GREATEST_HOURS)}))
        elif int(hours.normalize().as_tuple().exponent) < -HOURS_SCALE:
            faults.append(FieldError(pointer, VALIDATION_FAILED))
    return tuple(faults)


def _refuse_hours(weekly_hours: WeeklyHours) -> None:
    """Refuse the hours of a week at each day in fault, all named at once (422)."""
    faults = _hours_faults(weekly_hours)
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=faults)


def _left_idle(
    session: Session, calendar_id: UUID, weekly_hours: WeeklyHours, *, default: bool
) -> tuple[dict[str, str | None], ...]:
    """Name the projects the change would leave with a task without an hour, by each guard."""
    change = CalendarChange(calendar_id, _weekly(weekly_hours), default)
    return tuple(
        {"project_label": project.label, "project_code": project.code}
        for project in projects_left_idle(session, change)
    )


def calendar_change_is_admissible(
    session: Session, calendar_id: UUID, weekly_hours: WeeklyHours, *, default: bool
) -> bool:
    """Tell whether the calendar may take these hours, or be the default, without a task left idle.

    The planning answers, by the guards it registers (``register_idle_task_guard``, WF-PLA-0010).
    """
    return not _left_idle(session, calendar_id, weekly_hours, default=default)


def _refuse_idle_tasks(
    session: Session, calendar_id: UUID, weekly_hours: WeeklyHours, *, default: bool
) -> None:
    """Refuse a change that would leave a task without an hour, naming its projects (422)."""
    projects = _left_idle(session, calendar_id, weekly_hours, default=default)
    if projects:
        raise UnprocessableError(
            TASK_WITHOUT_WORKING_HOURS, {"resource_roles": [], "projects": list(projects)}
        )


def _deactivation_missing(*, is_default: bool) -> str | None:
    """Name what a deactivation lacks: another calendar designated the default first."""
    return CALENDAR_NOT_DEFAULT if is_default else None


def _designation_missing(*, is_active: bool) -> str | None:
    """Name what a designation lacks: a calendar active, a deactivated one is reactivated first."""
    return None if is_active else CALENDAR_ACTIVE


def _command(
    command: Literal["deactivate", "reactivate", "set_default"], missing: str | None
) -> CalendarCommand:
    return CalendarCommand(command, missing is None, () if missing is None else (missing,))


def calendar_commands(calendar: CalendarView, *, may_change: bool) -> tuple[CalendarCommand, ...]:
    """Give the commands of a calendar its reader may exercise, in the order of the contract.

    None for who may not change the resource settings. The conditions are those the refusals of
    the writes give, by the same functions.
    """
    if not may_change:
        return ()
    state = (
        _command("deactivate", _deactivation_missing(is_default=calendar.is_default))
        if calendar.is_active
        else _command("reactivate", None)
    )
    if calendar.is_default:
        return (state,)
    return (state, _command("set_default", _designation_missing(is_active=calendar.is_active)))


def _hours_of(calendar: Calendar) -> WeeklyHours:
    return WeeklyHours(
        calendar.monday,
        calendar.tuesday,
        calendar.wednesday,
        calendar.thursday,
        calendar.friday,
        calendar.saturday,
        calendar.sunday,
    )


def _views(calendars: Sequence[Calendar]) -> list[CalendarView]:
    """Describe the calendars; the authors stay identifiers, the API names them."""
    return [
        CalendarView(
            calendar_id=calendar.id,
            label=calendar.label,
            weekly_hours=_hours_of(calendar),
            is_default=calendar.is_default,
            is_active=calendar.is_active,
            created_at=calendar.created_at,
            created_by=calendar.created_by,
            updated_at=calendar.updated_at,
            updated_by=calendar.updated_by,
            lock_version=calendar.lock_version,
        )
        for calendar in calendars
    ]


def read_calendar(session: Session, calendar_id: UUID) -> CalendarView:
    """Read a calendar, deactivated or not, or refuse (404)."""
    calendar = session.scalars(
        select(Calendar).where(Calendar.id == calendar_id).execution_options(populate_existing=True)
    ).first()
    if calendar is None:
        raise NotFoundError(NOT_FOUND)
    return _views([calendar])[0]


def _lock_calendar(session: Session, calendar_id: UUID) -> Calendar:
    """Lock a calendar, then read it under the lock; or refuse (404)."""
    calendar = session.scalars(
        select(Calendar)
        .where(Calendar.id == calendar_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if calendar is None:
        raise NotFoundError(NOT_FOUND)
    return calendar


def _lock_designation(session: Session) -> None:
    """Wait for, then hold until the end of the transaction, the lock of the designation."""
    session.execute(select(func.pg_advisory_xact_lock(DEFAULT_LOCK)))


def _expect(calendar: Calendar, lock_version: int) -> None:
    """Refuse a version that is not the one the locked calendar holds (412)."""
    if calendar.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": calendar.lock_version}
        )


def _weekly(weekly_hours: WeeklyHours) -> dict[str, Decimal]:
    return {day: weekly_hours.of(day) for day in DAYS}


@contextmanager
def _unique_label(session: Session, label: str) -> Generator[None]:
    """Run a write that gives a calendar ``label``, refused if another one holds it (409).

    The unique index decides, whatever wrote first: a write that breaks it is undone alone, in a
    savepoint, and refused with the calendar that holds the label — by then committed, since the
    index made the write wait for it.
    """
    try:
        with session.begin_nested():
            yield
    except IntegrityError as error:
        if unique_violated(error) != LABEL_INDEX:
            raise
        holder = session.scalars(select(Calendar.id).where(Calendar.label == label)).first()
        params = {} if holder is None else {"conflicting_object_id": str(holder)}
        raise ConflictError(
            ALREADY_EXISTS, fields=(FieldError("/label", ALREADY_EXISTS, params),)
        ) from None


def _retire_default(session: Session, act: Act) -> None:
    """Take the designation from the calendar that holds it, if any, and advance its version."""
    session.execute(
        update(Calendar)
        .where(Calendar.is_default)
        .values(
            is_default=False,
            lock_version=Calendar.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
    )


def _write(session: Session, calendar: Calendar, act: Act, **values: object) -> None:
    """Write a locked calendar, its version advanced and its author the actor's."""
    session.execute(
        update(Calendar)
        .where(Calendar.id == calendar.id, Calendar.lock_version == calendar.lock_version)
        .values(
            **values,
            lock_version=Calendar.lock_version + 1,
            updated_at=act.at,
            updated_by=act.author,
        )
    )


def create_calendar(
    session: Session,
    new: CalendarContent,
    act: Act,
    *,
    identifier: UUID | None = None,
    default: bool = False,
) -> CalendarView:
    """Create an active calendar, and read it back; a label already held is refused (409).

    ``default`` designates it, the previous default retired: how the bootstrap and the loader of
    the witness give the installation its calendar. It is designated as ``set_default_calendar``
    designates (#2510): refused if it would leave a task without an hour (422), and the structures
    of the current revisions redated in the transaction once it is written (``recalculate``) —
    none, at the bootstrap and before the projects of the witness. ``identifier`` is imposed by the
    loader of the witness alone (EP-05): the API never passes one, and one already held fails.
    """
    _refuse_hours(new.weekly_hours)
    calendar_id = new_id() if identifier is None else identifier
    if default:
        lock_reference(session)
        _lock_designation(session)
        _refuse_idle_tasks(session, calendar_id, new.weekly_hours, default=True)
        _retire_default(session, act)
    with _unique_label(session, new.label):
        session.execute(
            insert(Calendar).values(
                id=calendar_id,
                label=new.label,
                **_weekly(new.weekly_hours),
                is_default=default,
                is_active=True,
                lock_version=FIRST_VERSION,
                created_at=act.at,
                created_by=act.author,
                updated_at=act.at,
                updated_by=act.author,
            )
        )
    if default:
        recalculate(session, act.at)
    return read_calendar(session, calendar_id)


def update_calendar(
    session: Session, calendar_id: UUID, change: CalendarContent, lock_version: int, act: Act
) -> CalendarView:
    """Change the label and the hours of a calendar, if its version is the one read (412).

    The days are refused first (422), then the version, then the label (409); a change that would
    leave a task without an hour is refused (422), which EP-06 judges. The structures of the current
    revisions are redated in the transaction, once the calendar is written (``recalculate``), when
    the hours of the default change: a label, or the hours of another calendar, which no task of
    EP-06 is on, redate nothing.
    """
    _refuse_hours(change.weekly_hours)
    lock_reference(session)
    calendar = _lock_calendar(session, calendar_id)
    _expect(calendar, lock_version)
    _refuse_idle_tasks(session, calendar_id, change.weekly_hours, default=calendar.is_default)
    redating = calendar.is_default and _weekly(_hours_of(calendar)) != _weekly(change.weekly_hours)
    with _unique_label(session, change.label):
        _write(session, calendar, act, label=change.label, **_weekly(change.weekly_hours))
    if redating:
        recalculate(session, act.at)
    return read_calendar(session, calendar_id)


def set_default_calendar(
    session: Session, calendar_id: UUID, lock_version: int, act: Act
) -> CalendarView:
    """Designate a calendar the default, the previous one losing it and its version advancing.

    The version is judged first, as for any versioned write. A calendar that is the default
    already answers as it is, nothing written; a deactivated one is not designated (409), nor one
    that would leave a task without an hour (422). The structures of the current revisions are
    redated in the transaction, once it is designated (``recalculate``).
    """
    lock_reference(session)
    _lock_designation(session)
    calendar = _lock_calendar(session, calendar_id)
    _expect(calendar, lock_version)
    if not calendar.is_default:
        missing = _designation_missing(is_active=calendar.is_active)
        if missing is not None:
            raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": missing})
        _refuse_idle_tasks(session, calendar_id, _hours_of(calendar), default=True)
        _retire_default(session, act)
        _write(session, calendar, act, is_default=True)
        recalculate(session, act.at)
    return read_calendar(session, calendar_id)


def set_calendar_activation(
    session: Session, calendar_id: UUID, lock_version: int, act: Act, *, is_active: bool
) -> CalendarView:
    """Deactivate or reactivate a calendar, if its version is the one read (412).

    The default calendar is not deactivated until another is designated (409). A calendar already
    in the state asked for is answered as it is, nothing written.
    """
    calendar = _lock_calendar(session, calendar_id)
    _expect(calendar, lock_version)
    if calendar.is_active != is_active:
        missing = None if is_active else _deactivation_missing(is_default=calendar.is_default)
        if missing is not None:
            raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": missing})
        _write(session, calendar, act, is_active=is_active)
    return read_calendar(session, calendar_id)


def calendars_present(session: Session, calendar_ids: Collection[UUID]) -> frozenset[UUID]:
    """Keep, of these identifiers, those a calendar bears: what the loader of the witness asks."""
    found = session.scalars(select(Calendar.id).where(Calendar.id.in_(calendar_ids)))
    return frozenset(found)


def list_calendars(
    session: Session, filters: CalendarFilters, sort: CalendarSort, window: CalendarWindow
) -> CalendarPage:
    """Read a page of the calendars the filters keep, in the order of the sort.

    Equals come by label, then identifier. The hours of a week are the sum of those of its days.
    """
    criteria: list[ColumnElement[bool]] = []
    if filters.search is not None:
        criteria.append(contains(Calendar.label, filters.search))
    if filters.is_active is not None:
        criteria.append(Calendar.is_active.is_(filters.is_active))
    elif not filters.include_inactive:
        criteria.append(Calendar.is_active.is_(True))
    week = (
        Calendar.monday
        + Calendar.tuesday
        + Calendar.wednesday
        + Calendar.thursday
        + Calendar.friday
        + Calendar.saturday
        + Calendar.sunday
    )
    keys: dict[CalendarColumn, SQLColumnExpression[Any]] = {
        "label": Calendar.label,
        "monday": Calendar.monday,
        "tuesday": Calendar.tuesday,
        "wednesday": Calendar.wednesday,
        "thursday": Calendar.thursday,
        "friday": Calendar.friday,
        "saturday": Calendar.saturday,
        "sunday": Calendar.sunday,
        "weekly_hours": week,
        # False sorts first: the default, then the active, in the ascending order.
        "is_default": ~Calendar.is_default,
        "is_active": ~Calendar.is_active,
    }
    key = keys[sort.column]
    order = (key.desc() if sort.descending else key, Calendar.label, Calendar.id)
    total = session.scalars(select(func.count()).select_from(Calendar).where(*criteria)).one()
    rows = session.scalars(
        select(Calendar)
        .where(*criteria)
        .order_by(*order)
        .limit(window.limit)
        .offset(window.offset)
        .execution_options(populate_existing=True)
    ).all()
    return CalendarPage(_views(rows), total)
