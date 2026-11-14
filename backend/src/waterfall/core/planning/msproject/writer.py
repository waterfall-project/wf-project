# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writer of a planning of MS Project: the model into an MSPDI file, in the order of the schema.

The schema of MS Project 2013 is a sequence at each level: an element out of its place makes the
file invalid (WF-QUA-0080), and MS Project may refuse to open it (WF-INTF-0050). Each function
here builds one element of the schema, its children in the order the schema declares them —
``Project``, ``ExtendedAttribute``, ``Calendar``, ``WeekDay``, ``Task``, ``PredecessorLink`` —, and
leaves out what the model does not carry. It adds what MS Project reads and the model does not
say (#2923): the working day of the calendar of the project in the head, a duration never
estimated, the dates and the duration of a manual task again where MS Project reads them. What it
writes, the reader reads back the same (``test_msproject.py``); what MS Project reads of it, the
tests read in the XML written.
"""

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.planning.msproject.model import (
    CONSTRAINT_TYPES,
    FORMAT_CODES,
    LINEAGE_ALIAS,
    LINEAGE_FIELD_ID,
    LINEAGE_FIELD_NAME,
    LINK_TYPES,
)
from waterfall.core.planning.msproject.tree import Tag, leaf, serialise, tag

if TYPE_CHECKING:
    from datetime import datetime, time

    from waterfall.core.planning.msproject.model import (
        MsCalendar,
        MsProject,
        MsTask,
        PredecessorLink,
        WorkingDay,
    )
    from waterfall.core.planning.scheduling import LagUnit

SAVE_VERSION = "14"
"""The version of the XML of the file: Project 2013 saves the one of Project 2010 (the schema)."""

BOOLEANS = {False: "0", True: "1"}
"""A boolean as MS Project writes it."""


class NegativeDurationError(ValueError):
    """A duration below nought: ``xsd:duration`` as MS Project reads it has no such value here."""


MONDAY_FIRST = (2, 3, 4, 5, 6, 7, 1)
"""The ``DayType`` of the days of the week, Monday first: Sunday is 1."""

HOUR = timedelta(hours=1)
MINUTE = timedelta(minutes=1)
MICROSECOND = timedelta(microseconds=1)


def write_project(project: MsProject) -> bytes:
    """Write a planning of MS Project as its MSPDI file, valid against the schema."""
    opening, closing = _working_hours(project)
    return serialise(
        tag(
            "Project",
            Tag("SaveVersion", SAVE_VERSION),
            leaf("Name", project.name),
            leaf("StartDate", _datetime(project.start)),
            # The schema requires a currency: the export gives the one of the installation; a model
            # without one writes it empty, which is valid, and MS Project takes its own.
            Tag("CurrencyCode", project.currency_code or ""),
            leaf("CalendarUID", _integer(project.calendar_uid)),
            leaf("DefaultStartTime", opening),
            leaf("DefaultFinishTime", closing),
            leaf("MinutesPerDay", _integer(project.minutes_per_day)),
            leaf("MinutesPerWeek", _integer(project.minutes_per_week)),
            leaf("DaysPerMonth", _integer(project.days_per_month)),
            _lineage_field(project),
            tag("Calendars", *map(_calendar, project.calendars)) if project.calendars else None,
            tag("Tasks", *(_task(rank, task) for rank, task in enumerate(project.tasks, 1)))
            if project.tasks
            else None,
        )
    )


def _integer(value: int | None) -> str | None:
    """Write an integer, ``None`` left out."""
    return None if value is None else str(value)


def _datetime(value: datetime | None) -> str | None:
    """Write a date and an hour of the wall clock of the project, to the second."""
    return None if value is None else value.isoformat(timespec="seconds")


def _time(value: time) -> str:
    """Write an hour of the day."""
    return value.isoformat(timespec="seconds")


def _duration(value: timedelta | None) -> str | None:
    """Write an ``xsd:duration`` as MS Project does, hours, minutes and seconds: ``PT16H0M0S``."""
    if value is None:
        return None
    if value < timedelta(0):
        raise NegativeDurationError(value)
    hours, rest = divmod(value, HOUR)
    minutes, rest = divmod(rest, MINUTE)
    seconds = Decimal(rest // MICROSECOND).scaleb(-6).normalize()
    return f"PT{hours}H{minutes}M{seconds:f}S"


def _working_hours(project: MsProject) -> tuple[str | None, str | None]:
    """Write the start and the end of the working day of the calendar of the project.

    MS Project places at them a date entered without its hour, and takes 8:00 and 17:00 without
    them, past the end of a day of seven hours (#2923). The day is the first the calendar works in
    the week, from Monday — every working day of an export opens at the same hour —; a calendar
    that the file does not carry, or that works no day it lists, writes neither.
    """
    calendar = next((each for each in project.calendars if each.uid == project.calendar_uid), None)
    days = {} if calendar is None else {day.day_type: day for day in calendar.days}
    for day_type in MONDAY_FIRST:
        day = days.get(day_type)
        if day is not None and day.working and day.times:
            return _time(day.times[0][0]), _time(day.times[-1][1])
    return None, None


def _format(unit: LagUnit | None) -> str | None:
    """Write the format of a unit, ``None`` left out."""
    return None if unit is None else str(FORMAT_CODES[unit])


def _lineage_field(project: MsProject) -> Tag | None:
    """Declare the custom field the lineages travel in, when a task carries one."""
    if all(task.lineage is None for task in project.tasks):
        return None
    return tag(
        "ExtendedAttributes",
        tag(
            "ExtendedAttribute",
            Tag("FieldID", LINEAGE_FIELD_ID),
            Tag("FieldName", LINEAGE_FIELD_NAME),
            Tag("Alias", LINEAGE_ALIAS),
        ),
    )


def _day(day: WorkingDay) -> Tag:
    """Write a day of the week of a calendar and its working times."""
    return tag(
        "WeekDay",
        Tag("DayType", str(day.day_type)),
        Tag("DayWorking", BOOLEANS[day.working]),
        tag(
            "WorkingTimes",
            *(
                tag("WorkingTime", Tag("FromTime", _time(start)), Tag("ToTime", _time(finish)))
                for start, finish in day.times
            ),
        )
        if day.times
        else None,
    )


def _calendar(calendar: MsCalendar) -> Tag:
    """Write a calendar and the days of the week it sets."""
    return tag(
        "Calendar",
        Tag("UID", str(calendar.uid)),
        leaf("Name", calendar.name),
        Tag("IsBaseCalendar", BOOLEANS[calendar.is_base]),
        leaf("BaseCalendarUID", _integer(calendar.base_uid)),
        tag("WeekDays", *map(_day, calendar.days)) if calendar.days else None,
    )


def _link(link: PredecessorLink) -> Tag:
    """Write a link of a task to its predecessor."""
    return tag(
        "PredecessorLink",
        Tag("PredecessorUID", str(link.predecessor_uid)),
        Tag("Type", str(LINK_TYPES.index(link.link_type))),
        Tag("LinkLag", str(link.lag)),
        leaf("LagFormat", _format(link.lag_unit)),
    )


def _task(rank: int, task: MsTask) -> Tag:
    """Write a task, its rank in the file as its ``ID``, its links and its lineage.

    A duration is never estimated: without ``Estimated`` at nought, MS Project shows it so, « 0 j? »
    for a milestone. A manual task carries its dates and its duration again in ``ManualStart``,
    ``ManualFinish`` and ``ManualDuration``, where MS Project reads them for a task in manual mode:
    without them, it opens a manual milestone as a task of one estimated day, and its successors a
    day later (#2923, WF-INTF-0050).
    """
    start, finish, duration = (
        _datetime(task.start),
        _datetime(task.finish),
        _duration(task.duration),
    )
    return tag(
        "Task",
        Tag("UID", str(task.uid)),
        Tag("ID", str(rank)),
        Tag("Name", task.name),
        Tag("OutlineLevel", str(task.outline_level)),
        leaf("Start", start),
        leaf("Finish", finish),
        leaf("Duration", duration),
        leaf("DurationFormat", _format(task.duration_unit)),
        Tag("Estimated", BOOLEANS[False]),
        Tag("Milestone", BOOLEANS[task.milestone]),
        Tag("ConstraintType", str(CONSTRAINT_TYPES.index(task.constraint))),
        leaf("CalendarUID", _integer(task.calendar_uid)),
        leaf("ConstraintDate", _datetime(task.constraint_date)),
        leaf("Notes", task.notes),
        *map(_link, task.predecessors),
        tag("ExtendedAttribute", Tag("FieldID", LINEAGE_FIELD_ID), Tag("Value", str(task.lineage)))
        if task.lineage is not None
        else None,
        Tag("Manual", BOOLEANS[task.manual]),
        *(
            (
                leaf("ManualStart", start),
                leaf("ManualFinish", finish),
                leaf("ManualDuration", duration),
            )
            if task.manual
            else ()
        ),
    )
