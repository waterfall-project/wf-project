# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A planning of MS Project in the terms of the engine: hours, units and instants of work.

Pure, as the reader (WF-QUA-0080): what the analysis of an import (US-1430/L3) and the test of the
corpus read of a file. MS Project writes a duration in hours — of work, or elapsed —, a lag in
tenths of a minute or in whole percents, a date at the hour of the wall clock; the engine reads a
value in the unit of its entry, and an instant of work, a day and the hours of work elapsed that day
(WF-DAT-0100). A duration or a lag keeps its value in its unit: its hours in the file over the
hours of its unit at the constants of the file — « 2 j » entered at seven hours a day is fourteen
hours of the file and stays two days, sixteen hours at the constants of an installation of eight
(WF-PLA-0160, 1.0.5, US-2000) —; one in minutes or in hours keeps its hours, and elapsed time is
converted without constants. The import and the test of the corpus read a file at its own
constants.

A date of the wall clock is read on the calendar of its task: the hours of work of its day that
precede it. A calendar of the file sets the days it lists, the others being those of its base; a
file that names no calendar of its project is on the calendar MS Project assumes (``STANDARD``).
The report writes the working times of a calendar as hours of the clock (``clock_text``).
"""

from dataclasses import dataclass
from datetime import time, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.planning.scheduling import (
    Calendar,
    Duration,
    Lag,
    UnitConstants,
    WorkInstant,
    decimal_of,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from waterfall.core.planning.msproject.model import (
        MsCalendar,
        MsProject,
        MsTask,
        PredecessorLink,
    )
    from waterfall.core.planning.scheduling import DurationUnit, LagUnit

MINUTES_PER_HOUR = 60
SECONDS_PER_HOUR = 3600
DAY_HOURS = 24
# A lag is written in tenths of a minute; a lag in percent in whole percents, ``10`` for 10 %
# (the file 02 of the corpus: 10 % of a task of 8 hours, 48 minutes for MS Project).
TENTHS = 10
MICROSECOND = timedelta(microseconds=1)
MICROSECONDS_PER_HOUR = 3_600_000_000
# What MS Project assumes of a file that does not say its constants: 8 hours, 40, 20 days.
DEFAULT_CONSTANTS = UnitConstants(Decimal(8), Decimal(40), Decimal(20))
# The ``DayType`` of a day of the week, Sunday 1 to Saturday 7, by the engine's Monday first.
DAY_TYPES = (2, 3, 4, 5, 6, 7, 1)

type Periods = tuple[tuple[Fraction, Fraction], ...]
"""The periods of work of a day, each from an hour to an hour of the clock."""


def constants_of(project: MsProject) -> UnitConstants:
    """Give the constants of the units a file carries: hours per day and per week, days per month.

    A constant the file does not say is MS Project's default (WF-PLA-0160).
    """
    per_day, per_week, per_month = (
        project.minutes_per_day,
        project.minutes_per_week,
        project.days_per_month,
    )
    return UnitConstants(
        DEFAULT_CONSTANTS.hours_per_day
        if per_day is None
        else decimal_of(Fraction(per_day, MINUTES_PER_HOUR)),
        DEFAULT_CONSTANTS.hours_per_week
        if per_week is None
        else decimal_of(Fraction(per_week, MINUTES_PER_HOUR)),
        DEFAULT_CONSTANTS.days_per_month if per_month is None else Decimal(per_month),
    )


def carried(constants: UnitConstants) -> UnitConstants:
    """Give constants as a file carries them: whole minutes a day and a week, whole days a month.

    What the export writes of the constants of the installation (``MinutesPerDay``,
    ``MinutesPerWeek``, ``DaysPerMonth`` are integers of the schema): 21.67 days a month come back
    22, which is not a constant of another installation.
    """
    return UnitConstants(
        decimal_of(Fraction(round(constants.hours_per_day * MINUTES_PER_HOUR), MINUTES_PER_HOUR)),
        decimal_of(Fraction(round(constants.hours_per_week * MINUTES_PER_HOUR), MINUTES_PER_HOUR)),
        Decimal(round(constants.days_per_month)),
    )


def _hour(moment: time, *, end: bool) -> Fraction:
    """Give an hour of the clock in hours from midnight; midnight at the end of a period is 24."""
    hours = Fraction(moment.hour) + Fraction(moment.minute, MINUTES_PER_HOUR)
    hours += Fraction(moment.second, SECONDS_PER_HOUR)
    return Fraction(DAY_HOURS) if end and hours == 0 else hours


@dataclass(frozen=True, slots=True)
class FileCalendar:
    """A calendar of the file resolved: the periods of work of each day of the week, from Monday."""

    week: tuple[Periods, ...]

    @property
    def calendar(self) -> Calendar:
        """Give the calendar as the engine reads it: the hours of work of each day."""
        hours = [
            decimal_of(sum((end - start for start, end in day), Fraction(0))) for day in self.week
        ]
        return Calendar((hours[0], hours[1], hours[2], hours[3], hours[4], hours[5], hours[6]))

    def instant(self, moment: datetime) -> WorkInstant:
        """Give the instant of work of a date of the clock: its day's hours worked before it."""
        at = _hour(moment.time(), end=False)
        worked = sum(
            (max(Fraction(0), min(end, at) - start) for start, end in self.week[moment.weekday()]),
            Fraction(0),
        )
        return WorkInstant(moment.date(), decimal_of(worked))


def _periods(calendar: MsCalendar) -> dict[int, Periods]:
    """Give the periods of the days a calendar lists, by their ``DayType``."""
    return {
        day.day_type: tuple(
            (_hour(start, end=False), _hour(finish, end=True)) for start, finish in day.times
        )
        if day.working
        else ()
        for day in calendar.days
    }


# The calendar MS Project gives a project that names none: from 8:00 to 12:00 and from 13:00 to
# 17:00, Monday to Friday.
_DAY: Periods = ((Fraction(8), Fraction(12)), (Fraction(13), Fraction(17)))
STANDARD = FileCalendar((_DAY, _DAY, _DAY, _DAY, _DAY, (), ()))


def clock_text(hours: Fraction) -> str:
    """Give an hour of the clock as the report writes it (``ImportWorkingTime``).

    ``HH:MM``, or ``HH:MM:SS`` when it falls on a second; the end of the day is ``24:00``.
    """
    whole, seconds = divmod(round(hours * SECONDS_PER_HOUR), SECONDS_PER_HOUR)
    minutes, seconds = divmod(seconds, MINUTES_PER_HOUR)
    return f"{whole:02d}:{minutes:02d}" + (f":{seconds:02d}" if seconds else "")


def calendars_of(project: MsProject) -> dict[int, FileCalendar]:
    """Give each calendar of a file resolved, by its unique identifier.

    A day a calendar does not list is its base's, and so on up; a day no calendar of the chain
    lists has no hour of work. A chain that loops stops where it would come back.
    """
    by_uid = {calendar.uid: calendar for calendar in project.calendars}
    resolved: dict[int, FileCalendar] = {}
    for uid in by_uid:
        days: dict[int, Periods] = {}
        seen: set[int] = set()
        current: int | None = uid
        while current is not None and current in by_uid and current not in seen:
            seen.add(current)
            for day_type, periods in _periods(by_uid[current]).items():
                days.setdefault(day_type, periods)
            current = by_uid[current].base_uid
        resolved[uid] = FileCalendar(tuple(days.get(day_type, ()) for day_type in DAY_TYPES))
    return resolved


def calendar_of(
    project: MsProject, calendars: Mapping[int, FileCalendar], task: MsTask
) -> FileCalendar | None:
    """Give the calendar a task is dated on in the file: its own, else the project's."""
    uid = project.calendar_uid if task.calendar_uid is None else task.calendar_uid
    return None if uid is None else calendars.get(uid)


def hours_of(span: timedelta) -> Fraction:
    """Give a duration of the file in exact hours."""
    return Fraction(span // MICROSECOND, MICROSECONDS_PER_HOUR)


def _per_unit(unit: DurationUnit, constants: UnitConstants) -> Fraction:
    """Give the hours of one unit, of work at the constants given, or elapsed."""
    return Duration(Decimal(1), unit).hours(constants)


def duration_of(task: MsTask, constants: UnitConstants) -> Duration:
    """Give the duration of a task in the unit of the file, at the constants given (WF-PLA-0160).

    Its hours over those of its unit: at the constants of the file, it keeps its value in its unit.
    A task without a duration lasts nought; a format that says no unit reads in days.
    """
    unit: DurationUnit = task.duration_unit or "d"
    hours = Fraction(0) if task.duration is None else hours_of(task.duration)
    return Duration(decimal_of(hours / _per_unit(unit, constants)), unit)


def lag_of(link: PredecessorLink, constants: UnitConstants) -> Lag:
    """Give the lag of a link in the unit of the file, at the constants given; a percent as such.

    ``LinkLag`` is in tenths of a minute — of work, or elapsed —, or in whole percents.
    """
    unit: LagUnit = link.lag_unit or "d"
    if unit == "percent":
        return Lag(Decimal(link.lag), unit)
    hours = Fraction(link.lag, TENTHS * MINUTES_PER_HOUR)
    return Lag(decimal_of(hours / _per_unit(unit, constants)), unit)
