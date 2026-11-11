# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendars a task is placed on, read from the resource settings, private to the module.

The calendar applicable to a task gives each day the fewest hours the calendars of the roles of its
labour lines grant; a task without any is on the default calendar (WF-PLA-0010). The planning reads
the calendars by the interface of the resource settings, and the calendars of the roles by the
facets a later module registers (``register_facet``, EP-07): ``calendar_of`` composes them.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.planning.scheduling import Calendar, applicable_calendar
from waterfall.core.resource_settings.interface import (
    CalendarFilters,
    CalendarSort,
    CalendarWindow,
    list_calendars,
    read_calendar,
)

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.resource_settings.interface import WeeklyHours


@dataclass(frozen=True, slots=True)
class Applicable:
    """The calendar applicable to a task: its identifier — none for an intersection — and hours."""

    calendar_id: UUID | None
    calendar: Calendar


def week_of(hours: WeeklyHours) -> Calendar:
    """Give the hours of a calendar of the reference as the engine reads them, Monday first."""
    return Calendar(
        (
            hours.monday,
            hours.tuesday,
            hours.wednesday,
            hours.thursday,
            hours.friday,
            hours.saturday,
            hours.sunday,
        )
    )


def default_calendar(session: Session) -> Applicable:
    """Read the default calendar: the first in the order of ``is_default``, for it is single."""
    page = list_calendars(
        session, CalendarFilters(), CalendarSort("is_default"), CalendarWindow(1, 0)
    )
    view = page.calendars[0]
    return Applicable(view.calendar_id, week_of(view.weekly_hours))


def applicable_of(session: Session, named: Collection[UUID], default: Applicable) -> Applicable:
    """Give the calendar applicable to a task whose roles name these calendars (WF-PLA-0010).

    None named, the default; one, its own; several, their intersection, which has no identifier.
    """
    if not named:
        return default
    weeks = [week_of(read_calendar(session, each).weekly_hours) for each in sorted(named)]
    only = next(iter(named)) if len(set(named)) == 1 else None
    return Applicable(only, applicable_calendar(weeks, default.calendar))
