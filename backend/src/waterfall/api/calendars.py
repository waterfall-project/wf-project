# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars and the units of duration (FBS-3.2).

``listCalendars``, ``createCalendar``, ``updateCalendar``, ``setDefaultCalendar``,
``setCalendarActivation``, ``getDurationUnits`` and ``setDurationUnits``.

The active calendars and the constants are read by any session: they are the vocabulary of the
projects (FBS-4). The deactivated calendars (``include_inactive``, ``is_active`` false) and every
write ask for the permission to change the resource settings (WF-ADM-0100). A calendar is
described with the commands its caller may exercise, each available or not (WF-IHM-0090).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import ContractModel, Text
from waterfall.api.contract.models import (
    Calendar,
    CalendarUpdate,
    CalendarWrite,
    DurationUnits,
    DurationUnitsWrite,
    LockVersion,
    PaginationMeta,
    SortOrder,
)
from waterfall.api.evaluation import Acting, Requires, RequiresForInactive
from waterfall.api.queries import GREATEST_OFFSET
from waterfall.core.resource_settings.interface import (
    DAYS,
    CalendarColumn,
    CalendarContent,
    CalendarFilters,
    CalendarSort,
    CalendarView,
    CalendarWindow,
    DurationUnitsView,
    Units,
    WeeklyHours,
    calendar_commands,
    create_calendar,
    get_duration_units,
    list_calendars,
    set_calendar_activation,
    set_default_calendar,
    set_duration_units,
    update_calendar,
)
from waterfall.core.users.interface import Author, read_authors
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from sqlalchemy.orm import Session

router = APIRouter(tags=["reference"])

CHANGE = "resource_settings.write"
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
# Read by any session: the active calendars and the constants ask for no permission.
OPEN = [Depends(Requires())]
# The deactivated calendars are read under the permission to change, after the evaluation above.
LIST = [Depends(Requires()), Depends(RequiresForInactive(CHANGE))]
WRITE = [Depends(Requires(CHANGE))]


@dataclass(frozen=True, slots=True)
class CalendarQuery:
    """What the table of the calendars asks for."""

    filters: CalendarFilters
    sort: CalendarSort
    window: CalendarWindow


class DefaultWrite(ContractModel):
    """The body of a designation: the version read of the calendar designated, alone."""

    lock_version: LockVersion


class ActivationWrite(ContractModel):
    """The body of an activation: the state asked for and the version read."""

    is_active: bool
    lock_version: LockVersion


def _plain(value: Decimal) -> str:
    """Write a decimal as the contract's examples do, without a useless exponent or zero: ``10``."""
    return format(value.normalize(), "f")


def authors_of(session: Session, views: Sequence[CalendarView]) -> dict[UUID, Author]:
    """Name the authors of calendars as they are today."""
    return read_authors(
        session,
        {
            author
            for view in views
            for author in (view.created_by, view.updated_by)
            if author is not None
        },
    )


def calendar(view: CalendarView, authors: Mapping[UUID, Author], *, may_change: bool) -> Calendar:
    """Describe a calendar as the contract does, its commands those its caller may exercise."""
    return Calendar.model_validate(
        {
            "calendar_id": view.calendar_id,
            "label": view.label,
            "weekly_hours": {day: _plain(view.weekly_hours.of(day)) for day in DAYS},
            "is_default": view.is_default,
            "is_active": view.is_active,
            "available_commands": [
                {
                    "command": each.command,
                    "is_available": each.is_available,
                    "missing_conditions": list(each.missing_conditions),
                }
                for each in calendar_commands(view, may_change=may_change)
            ],
            "audit": {
                "created_at": view.created_at,
                "created_by": actor_ref(
                    None if view.created_by is None else authors.get(view.created_by)
                ),
                "updated_at": view.updated_at,
                "updated_by": actor_ref(
                    None if view.updated_by is None else authors.get(view.updated_by)
                ),
            },
            "lock_version": view.lock_version,
        }
    )


def duration_units(view: DurationUnitsView, authors: Mapping[UUID, Author]) -> DurationUnits:
    """Describe the constants as the contract does."""
    return DurationUnits.model_validate(
        {
            "hours_per_day": _plain(view.units.hours_per_day),
            "hours_per_week": _plain(view.units.hours_per_week),
            "days_per_month": _plain(view.units.days_per_month),
            "audit": {
                "created_at": view.created_at,
                "created_by": actor_ref(
                    None if view.created_by is None else authors.get(view.created_by)
                ),
                "updated_at": view.updated_at,
                "updated_by": actor_ref(
                    None if view.updated_by is None else authors.get(view.updated_by)
                ),
            },
            "lock_version": view.lock_version,
        }
    )


def authors_of_units(session: Session, view: DurationUnitsView) -> dict[UUID, Author]:
    """Name the authors of the constants as they are today."""
    return read_authors(
        session, {each for each in (view.created_by, view.updated_by) if each is not None}
    )


def content(body: CalendarWrite) -> CalendarContent:
    """Read the label and the seven days of a calendar written."""
    hours = body.weekly_hours
    return CalendarContent(
        body.label,
        WeeklyHours(*(Decimal(getattr(hours, day).root.root) for day in DAYS)),
    )


class CalendarQueryParams(BaseModel):
    """The parameters of the query of the table of the calendars, as the contract names them."""

    search: Text | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    include_inactive: bool = False
    sort_by: CalendarColumn = "label"
    sort_order: SortOrder = SortOrder.asc
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=GREATEST_LIMIT)
    offset: int = Field(default=0, ge=0, le=GREATEST_OFFSET)


def calendar_query(params: Annotated[CalendarQueryParams, Query()]) -> CalendarQuery:
    """Read the filters, the sort and the page the table asks for."""
    return CalendarQuery(
        CalendarFilters(params.search, params.is_active, params.include_inactive),
        CalendarSort(params.sort_by, descending=params.sort_order is SortOrder.desc),
        CalendarWindow(params.limit, params.offset),
    )


# The platform as an author has no account: its absent fields stay absent, not null.
@router.get(
    "/reference/calendars", operation_id="listCalendars", dependencies=LIST, response_model=None
)
def get_calendars(
    actor: Acting, session: Transaction, asked: Annotated[CalendarQuery, Depends(calendar_query)]
) -> dict[str, object]:
    """Give a page of the calendars, filtered and sorted by the server (WF-REF-0110, 0120)."""
    page = list_calendars(session, asked.filters, asked.sort, asked.window)
    may_change = CHANGE in actor.permissions
    authors = authors_of(session, page.calendars)
    meta = PaginationMeta(limit=asked.window.limit, offset=asked.window.offset, total=page.total)
    return {
        "items": [
            calendar(each, authors, may_change=may_change).model_dump(
                mode="json", exclude_unset=True
            )
            for each in page.calendars
        ],
        "meta": meta.model_dump(),
    }


@router.post(
    "/reference/calendars",
    operation_id="createCalendar",
    dependencies=WRITE,
    status_code=201,
    response_model_exclude_unset=True,
)
def post_calendar(body: CalendarWrite, account: Caller, session: Transaction) -> Calendar:
    """Create an active calendar, not the default, of a label and seven days (WF-REF-0110)."""
    created = create_calendar(session, content(body), Act(account.user_id, utc_now()))
    return calendar(created, authors_of(session, [created]), may_change=True)


@router.patch(
    "/reference/calendars/{calendar_id}",
    operation_id="updateCalendar",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def patch_calendar(
    calendar_id: UUID, body: CalendarUpdate, account: Caller, session: Transaction
) -> Calendar:
    """Change the label and the hours of a calendar, unless stale (412) (WF-REF-0110)."""
    act = Act(account.user_id, utc_now())
    changed = update_calendar(session, calendar_id, content(body), body.lock_version.root, act)
    return calendar(changed, authors_of(session, [changed]), may_change=True)


@router.put(
    "/reference/calendars/{calendar_id}/default",
    operation_id="setDefaultCalendar",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_default_calendar(
    calendar_id: UUID, body: DefaultWrite, account: Caller, session: Transaction
) -> Calendar:
    """Designate a calendar the default, the previous one losing it (WF-REF-0120)."""
    act = Act(account.user_id, utc_now())
    designated = set_default_calendar(session, calendar_id, body.lock_version.root, act)
    return calendar(designated, authors_of(session, [designated]), may_change=True)


@router.put(
    "/reference/calendars/{calendar_id}/activation",
    operation_id="setCalendarActivation",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_calendar_activation(
    calendar_id: UUID, body: ActivationWrite, account: Caller, session: Transaction
) -> Calendar:
    """Deactivate or reactivate a calendar; the default one is not deactivated (WF-REF-0120)."""
    act = Act(account.user_id, utc_now())
    changed = set_calendar_activation(
        session, calendar_id, body.lock_version.root, act, is_active=body.is_active
    )
    return calendar(changed, authors_of(session, [changed]), may_change=True)


@router.get(
    "/reference/duration-units",
    operation_id="getDurationUnits",
    dependencies=OPEN,
    response_model_exclude_unset=True,
)
def get_units(session: Transaction) -> DurationUnits:
    """Give the constants the days, weeks and months convert by (WF-PLA-0160)."""
    view = get_duration_units(session)
    return duration_units(view, authors_of_units(session, view))


@router.put(
    "/reference/duration-units",
    operation_id="setDurationUnits",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_units(body: DurationUnitsWrite, account: Caller, session: Transaction) -> DurationUnits:
    """Write the three constants, strictly positive, unless stale (412) (WF-PLA-0160)."""
    units = Units(
        Decimal(body.hours_per_day.root),
        Decimal(body.hours_per_week.root),
        Decimal(body.days_per_month.root),
    )
    act = Act(account.user_id, utc_now())
    view = set_duration_units(session, units, body.lock_version.root, act)
    return duration_units(view, authors_of_units(session, view))
