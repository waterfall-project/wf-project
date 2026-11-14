# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The calendar gap of a planning of MS Project, and its dates kept, private to the module.

What the analysis of an import (``importing``) asks of a file entered on other days than those of
the installation (US-2000/L2; WF-INTF-0040, WF-PLA-0160):

- **The gap.** A file is in calendar gap when its unit constants differ from those of the
  installation as a file carries them (``carried``), when the days of the calendar of its project —
  MS Project's when it names none — do not hold, day by day, the hours of the default calendar of
  the installation, or when the own calendar of one of its tasks does not hold those of the
  applicable Waterfall calendar of the task (WF-PLA-0010). The report says it
  (``ImportReport.calendar_gap``): the calendar of the project of the file — its name, its hours per
  day and its working times —, the default calendar of the installation, each task whose own
  calendar differs, in the order of the file, and the rule it was computed under. A file exported
  by Waterfall carries the calendars and the constants it was dated with: it is in no gap.
- **Keeping the dates.** An automatic task takes for duration the work between its start and its
  finish in the file, on its applicable Waterfall calendar, in the unit of its duration at the
  constants of the installation. A Waterfall calendar has no hours of the clock, only the hours of
  work of each day: an instant of the file is placed at the same share of the work of its day — the
  end of a day of seven hours at the end of a day of eight, the middle at the middle —, so that a
  task of two whole days of the file lasts two whole days. A day without hours in the file starts
  its day.
- **The dates compared** (``importing``). In a gap, the hours of work of a day do not read the
  same in the file and in Waterfall: a start or a finish differs when its day differs, and the
  duration of a summary when its value in its unit differs, at the constants of each side.
"""

from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING, Any

from waterfall.core.planning.entries import decimal_text
from waterfall.core.planning.msproject import STANDARD, FileCalendar, clock_text
from waterfall.core.planning.scheduling import Duration, Moment, WorkInstant, decimal_of

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from waterfall.core.exchanges.interface import DurationRule
    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.msproject import MsProject, MsTask
    from waterfall.core.planning.scheduling import Calendar, DurationUnit, UnitConstants

type Json = dict[str, Any]

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def weekly_hours(calendar: Calendar) -> Json:
    """Give the hours of each day of a calendar as the report writes them (``WeeklyHours``)."""
    return {day: decimal_text(hours) for day, hours in zip(DAYS, calendar.week, strict=True)}


def file_calendar(name: str | None, calendar: FileCalendar) -> Json:
    """Give a calendar of the file as the report writes it (``ImportFileCalendar``)."""
    return {
        "name": name,
        "weekly_hours": weekly_hours(calendar.calendar),
        "working_times": {
            day: [{"from": clock_text(start), "to": clock_text(end)} for start, end in periods]
            for day, periods in zip(DAYS, calendar.week, strict=True)
        },
    }


def _project_calendar(
    project: MsProject, calendars: Mapping[int, FileCalendar]
) -> tuple[str | None, FileCalendar]:
    """Give the calendar of the project of a file and its name; MS Project's for a file without."""
    uid = project.calendar_uid
    found = None if uid is None else calendars.get(uid)
    if uid is None or found is None:
        return None, STANDARD
    return _name(project, uid), found


def _name(project: MsProject, uid: int) -> str | None:
    """Give the name of a calendar of the file."""
    return next((each.name for each in project.calendars if each.uid == uid), None)


def gap_tasks(
    project: MsProject,
    calendars: Mapping[int, FileCalendar],
    tasks: Sequence[tuple[MsTask, UUID | None, Calendar]],
) -> list[Json]:
    """Name the tasks whose own calendar in the file differs from their Waterfall one, in order.

    ``tasks`` gives each task of the file the import writes, its lineage and its applicable
    calendar; a task on the calendar of the project has none of its own.
    """
    found: list[Json] = []
    for task, lineage, applicable in tasks:
        own = None if task.calendar_uid is None else calendars.get(task.calendar_uid)
        if own is None or own.calendar.week == applicable.week:
            continue
        found.append(
            {
                "lineage_id": None if lineage is None else str(lineage),
                "label": task.name,
                "file_calendar": file_calendar(_name(project, task.calendar_uid or 0), own),
                "weekly_hours": weekly_hours(applicable),
            }
        )
    return found


def calendar_gap(
    project: MsProject,
    calendars: Mapping[int, FileCalendar],
    sides: tuple[bool, tuple[Applicable, str]],
    tasks: list[Json],
    rule: DurationRule,
) -> Json | None:
    """Give the calendar gap of a file, under the rule of its durations; ``None`` without one.

    ``sides`` say whether the constants of the file differ from those of the installation, and
    give the default calendar of the installation with its label; ``tasks`` those whose own
    calendar differs (``gap_tasks``).
    """
    constants_differ, (default, label) = sides
    name, of_project = _project_calendar(project, calendars)
    if not constants_differ and of_project.calendar.week == default.calendar.week and not tasks:
        return None
    return {
        "project_calendar": file_calendar(name, of_project),
        "installation_calendar": {
            "calendar_id": str(default.calendar_id),
            "label": label,
            "weekly_hours": weekly_hours(default.calendar),
        },
        "tasks": tasks,
        "duration_rule": rule,
    }


def placed_on(instant: WorkInstant, file_day: Calendar, calendar: Calendar) -> Moment:
    """Give an instant of the file at the same share of the work of its day on a Waterfall one."""
    worked = Fraction(file_day.hours_on(instant.day))
    share = Fraction(0) if worked == 0 else Fraction(instant.hours) / worked
    return Moment(instant.day.toordinal(), share * Fraction(calendar.hours_on(instant.day)))


def kept_dates(
    dates: tuple[WorkInstant, WorkInstant],
    calendars: tuple[Calendar, Calendar],
    unit: DurationUnit,
    constants: UnitConstants,
) -> Duration:
    """Give a task the work between its dates of the file on its Waterfall calendar, in its unit.

    ``calendars`` are the calendar it is dated on in the file and its applicable one in Waterfall;
    the unit is converted at the constants of the installation.
    """
    on_file, calendar = calendars
    start, finish = (placed_on(each, on_file, calendar) for each in dates)
    worked = max(Fraction(0), calendar.count(finish) - calendar.count(start))
    return Duration(value_in_unit(worked, unit, constants), unit)


def value_in_unit(hours: Fraction, unit: DurationUnit, constants: UnitConstants) -> Decimal:
    """Give hours of work as a value in a unit, at the constants of one side of the gap."""
    return decimal_of(hours / Duration(Decimal(1), unit).hours(constants))
