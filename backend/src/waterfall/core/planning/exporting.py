# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A structure as a planning of MS Project, private to the module (US-1430/L4).

What the exporter ``ms_project_schedule`` writes (EP-06, "Le format MS Project"), as the model the
writer of ``msproject/`` turns into the file, in the order of the schema, and the import reads
back to the same plan (WF-INTF-0060):

- **The project.** Its label, its start the day of ``planning_start_on`` at the opening hour, the
  constants of the units of the installation, and the calendars.
- **The calendars.** The default calendar is the calendar of the project (unique identifier 1);
  each other calendar applicable to a task, distinct by its hours, is a calendar of its own, after
  it. A calendar is a base calendar that lists its seven days, a day of work being a single period
  from the opening hour for as many hours as it grants (earlier if it would pass midnight), so
  that an instant of work is a date of the clock and back, exactly.
- **The tasks.** In the order of the plan, the ``UID`` its rank from 1, the outline level its depth
  in the tree, the notes the description (#1339), the lineage in the field of the lineages; a
  duration in the unit it was entered in, as hours of work or elapsed (WF-PLA-0160), a summary's
  in days; a milestone a leaf of nought duration; the mode manual for a leaf entered so.
- **The links.** ``Type`` by the position of the type, ``LinkLag`` in tenths of a minute — of work
  or elapsed as its unit says — or of a percent, in the format of its unit.
"""

from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from fractions import Fraction
from typing import TYPE_CHECKING, cast

from waterfall.core.planning.calendars import default_calendar
from waterfall.core.planning.dating import MANUAL, constants_of, duration_of
from waterfall.core.planning.interface.facets import calendars_of
from waterfall.core.planning.msproject import (
    MsCalendar,
    MsProject,
    MsTask,
    PredecessorLink,
    WorkingDay,
)
from waterfall.core.planning.msproject.model import LINK_TYPES
from waterfall.core.planning.scheduling import Duration, WorkInstant
from waterfall.core.planning.tree import read_links, read_tree
from waterfall.core.projects.interface import project_label
from waterfall.core.revisions.interface import structure_facts

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import LagUnit, LinkType, UnitConstants
    from waterfall.core.planning.tables import Task, TaskLink
    from waterfall.core.planning.tree import Tree

PROJECT_CALENDAR = 1
OPENING = time(8, 0)
SECONDS_PER_HOUR = 3600
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR
MINUTES_PER_HOUR = 60
MICROSECONDS_PER_HOUR = 3_600_000_000
# A lag is written in tenths of a minute, a lag in percent in tenths of a percent.
TENTHS = 10
# The ``DayType`` of a day of the week, Monday first: Monday is 2, Sunday 1.
DAY_TYPES = (2, 3, 4, 5, 6, 7, 1)
CALENDAR_NAME = "Waterfall"

type Week = tuple[Decimal, ...]
type Period = tuple[timedelta, timedelta]
"""A period of work of a day: from an offset after midnight to another."""


@dataclass(frozen=True, slots=True)
class Calendars:
    """The calendars of the file: the unique identifier of each distinct week, and its periods."""

    uids: dict[Week, int]
    periods: dict[int, tuple[Period | None, ...]]


def _period(hours: Decimal) -> Period | None:
    """Give the period a day of as many hours of work is written as: none for a day off."""
    length = min(round(Fraction(hours) * SECONDS_PER_HOUR), SECONDS_PER_DAY)
    if length <= 0:
        return None
    opening = min(timedelta(hours=OPENING.hour), timedelta(seconds=SECONDS_PER_DAY - length))
    return opening, opening + timedelta(seconds=length)


def _clock(offset: timedelta) -> time:
    """Give the hour of the clock an offset after midnight falls on: midnight for a day's end."""
    seconds = round(offset.total_seconds())
    if seconds >= SECONDS_PER_DAY:
        return time(0)
    hours, rest = divmod(seconds, SECONDS_PER_HOUR)
    return time(hours, *divmod(rest, MINUTES_PER_HOUR))


def _calendars(default: Applicable, applicable: dict[UUID, Applicable]) -> Calendars:
    """Give the calendars of the file: the default one first, the others in their order of use."""
    uids: dict[Week, int] = {default.calendar.week: PROJECT_CALENDAR}
    for each in applicable.values():
        uids.setdefault(each.calendar.week, len(uids) + 1)
    return Calendars(
        uids, {uid: tuple(_period(hours) for hours in week) for week, uid in uids.items()}
    )


def _ms_calendar(uid: int, week: tuple[Period | None, ...]) -> MsCalendar:
    """Write a calendar of the file: a base calendar that lists its seven days."""
    days = {
        DAY_TYPES[number]: WorkingDay(
            DAY_TYPES[number],
            period is not None,
            () if period is None else ((_clock(period[0]), _clock(period[1])),),
        )
        for number, period in enumerate(week)
    }
    name = CALENDAR_NAME if uid == PROJECT_CALENDAR else f"{CALENDAR_NAME} {uid}"
    return MsCalendar(
        uid, name, is_base=True, base_uid=None, days=tuple(days[each] for each in sorted(days))
    )


def _clock_of(moment: WorkInstant, week: tuple[Period | None, ...]) -> datetime:
    """Give the date of the clock of an instant of work on a calendar: its hours after opening."""
    day = datetime.combine(moment.day, time(0))
    period = week[moment.day.weekday()]
    if period is None:
        return day + timedelta(hours=OPENING.hour)
    worked = timedelta(seconds=round(Fraction(moment.hours) * SECONDS_PER_HOUR))
    return day + min(period[0] + worked, period[1])


def _link(link: TaskLink, uids: dict[UUID, int], constants: UnitConstants) -> PredecessorLink:
    """Give a link of the structure as the file carries it, its lag in tenths of its unit."""
    unit = cast("LagUnit", link.lag_unit)
    if unit == "percent":
        lag = round(Fraction(link.lag_value) * TENTHS)
    else:
        hours = Duration(link.lag_value, unit).hours(constants)
        lag = round(hours * MINUTES_PER_HOUR * TENTHS)
    link_type = LINK_TYPES[LINK_TYPES.index(cast("LinkType", link.link_type))]
    return PredecessorLink(uids[link.predecessor_id], link_type, lag, unit)


def _task(
    tree: Tree,
    node_id: UUID,
    uid: int,
    calendar: tuple[int, tuple[Period | None, ...]],
    constants: UnitConstants,
) -> MsTask:
    """Give a task of the structure as the file carries it, its links not yet.

    ``calendar`` is the unique identifier of the calendar of the task and its week of periods.
    """
    calendar_uid, week = calendar
    task: Task = tree.tasks[node_id]
    duration = duration_of(task)
    return MsTask(
        uid=uid,
        name=task.label,
        outline_level=tree.level[node_id],
        manual=task.scheduling_mode == MANUAL and not tree.is_summary(node_id),
        duration=timedelta(microseconds=round(duration.hours(constants) * MICROSECONDS_PER_HOUR)),
        duration_unit=duration.unit,
        start=_clock_of(WorkInstant(task.start_date, task.start_hours), week),
        finish=_clock_of(WorkInstant(task.finish_date, task.finish_hours), week),
        milestone=tree.is_milestone(node_id),
        calendar_uid=calendar_uid,
        notes=task.description,
        lineage=tree.nodes[node_id].lineage_id,
    )


def project_of(session: Session, project_id: UUID, structure_id: UUID) -> MsProject:
    """Give a structure of a project as a planning of MS Project, reading and writing nothing.

    The calendars and the constants are those of the installation, the tasks and the links those
    of the structure, as the transaction sees them.
    """
    facts = structure_facts(session, project_id, structure_id, lock=False)
    tree = read_tree(session, project_id, structure_id)
    constants = constants_of(session)
    ordered = [each for each in tree.order if each in tree.tasks]
    uids = {node_id: rank for rank, node_id in enumerate(ordered, start=1)}
    applicable = calendars_of(session, project_id, ordered)
    calendars = _calendars(default_calendar(session), applicable)
    links: dict[UUID, list[PredecessorLink]] = {}
    for each in read_links(session, project_id, structure_id):
        links.setdefault(each.successor_id, []).append(_link(each, uids, constants))
    tasks: list[MsTask] = []
    for node_id in ordered:
        calendar_uid = calendars.uids[applicable[node_id].calendar.week]
        placed = _task(
            tree, node_id, uids[node_id], (calendar_uid, calendars.periods[calendar_uid]), constants
        )
        tasks.append(replace(placed, predecessors=tuple(links.get(node_id, ()))))
    return MsProject(
        start=datetime.combine(facts.planning_start_on, OPENING),
        name=project_label(session, project_id),
        calendar_uid=PROJECT_CALENDAR,
        minutes_per_day=round(constants.hours_per_day * MINUTES_PER_HOUR),
        minutes_per_week=round(constants.hours_per_week * MINUTES_PER_HOUR),
        days_per_month=round(constants.days_per_month),
        calendars=tuple(_ms_calendar(uid, week) for uid, week in sorted(calendars.periods.items())),
        tasks=tuple(tasks),
    )
