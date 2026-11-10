# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hours of work of a calendar, and the instants a task is placed at (WF-PLA-0010).

A calendar gives the hours worked on each day of the week (WF-REF-0110), without holidays or part
time. An instant of work is a day and the hours of work elapsed that day (WF-DAT-0100): the
engine counts the hours of work of a calendar from the first day of the proleptic calendar, a
Monday, turns an instant into that count, moves it by hours of work and turns it back into an
instant. A count that falls on the end of a day's work reads two ways: the finish of a task ends
that day, the start of the next begins at the first hour of work of the next working day.

The days are their ordinals inside the engine, which overflow nothing: a planning beyond the
horizon (WF-PLA-0150) may reach past the last day a ``date`` holds, and is refused before any of
its days is read as one.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.planning.scheduling.units import HOURS_PER_ELAPSED_DAY, decimal_of

if TYPE_CHECKING:
    from collections.abc import Sequence

DAYS_PER_WEEK = 7


@dataclass(frozen=True, slots=True, order=True)
class WorkInstant:
    """The start or the finish of a task: a day, and the hours of work elapsed that day.

    The contract's `WorkInstant` (WF-DAT-0100): two tasks of four hours linked finish to start on a
    calendar of eight hours start and finish the same day, the first finishing at 4, the second
    starting at 4. Instants compare by day, then by hours.
    """

    day: date
    hours: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True, order=True)
class Moment:
    """An instant inside the engine: the ordinal of its day, and the exact hours elapsed that day.

    The ordinal of the first of January of the year 1 is 1, a Monday.
    """

    ordinal: int
    hours: Fraction = Fraction(0)

    @classmethod
    def of(cls, instant: WorkInstant) -> Moment:
        """Return the moment of an instant of work."""
        return cls(instant.day.toordinal(), Fraction(instant.hours))

    def instant(self) -> WorkInstant:
        """Return the instant of work of a moment, which must lie within the days a date holds."""
        return WorkInstant(date.fromordinal(self.ordinal), decimal_of(self.hours))

    def elapsed(self, hours: Fraction) -> Moment:
        """Return the moment so many elapsed hours later, or earlier when they are negative.

        Elapsed time runs on days of twenty-four hours whose hours of work take the first places,
        from the first hour of work of the day (WF-PLA-0160): the hours of a moment are also its
        place in its day of twenty-four. The moment reached may lie past the day's hours of work.
        """
        position = self.ordinal * HOURS_PER_ELAPSED_DAY + self.hours + hours
        ordinal = position // HOURS_PER_ELAPSED_DAY
        return Moment(ordinal, position - ordinal * HOURS_PER_ELAPSED_DAY)


@dataclass(frozen=True, slots=True)
class Calendar:
    """The hours worked on each day of the week, Monday first (WF-REF-0110).

    The engine counts them exactly, as fractions (``units``).
    """

    week: tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]
    _week: tuple[Fraction, ...] = field(init=False, repr=False, compare=False)
    _before: tuple[Fraction, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        week = tuple(Fraction(hours) for hours in self.week)
        before = [Fraction(0)]
        for hours in week:
            before.append(before[-1] + hours)
        object.__setattr__(self, "_week", week)
        object.__setattr__(self, "_before", tuple(before))

    @property
    def weekly(self) -> Fraction:
        """Return the hours of a week of work: a calendar without any can place no task."""
        return self._before[-1]

    def hours_on(self, day: date) -> Decimal:
        """Return the hours worked on a day."""
        return self.week[day.weekday()]

    def next_working_day(self, day: date) -> date:
        """Return the first day after a day that grants hours of work (WF-PLA-0020).

        What a refused date entered on a day without hours of work names. Looks one week ahead:
        a calendar without any hour of work has no such day, and raises ``ValueError``.
        """
        for offset in range(1, DAYS_PER_WEEK + 1):
            after = day + timedelta(days=offset)
            if self.hours_on(after) > 0:
                return after
        message = "the calendar grants no hour of work in a week"
        raise ValueError(message)

    def work_between(self, first: WorkInstant, last: WorkInstant) -> Decimal:
        """Return the hours of work from one instant to another, negative when it comes first."""
        return decimal_of(self.count(Moment.of(last)) - self.count(Moment.of(first)))

    def worked(self, instant: WorkInstant) -> Fraction:
        """Return the hours of work from the origin to an instant, exactly, as ``count`` does.

        What the estimate spreads the load and the amount of a line by, on the calendar it is
        worked on (EP-07, #2549): one count of the hours of work, the engine's.
        """
        return self.count(Moment.of(instant))

    def count(self, moment: Moment) -> Fraction:
        """Return the hours of work from the origin to a moment; hours past the day's are not.

        A moment past the hours of work of its day counts as their end: an elapsed lag that ends
        outside them places a successor at the first hour of work that follows (WF-PLA-0160).
        """
        weeks, weekday = divmod(moment.ordinal - 1, DAYS_PER_WEEK)
        worked = min(moment.hours, self._week[weekday])
        return weeks * self.weekly + self._before[weekday] + worked

    def bounded(self, moment: Moment) -> Moment:
        """Return a moment on its own day, its hours bounded to the hours of work of that day.

        Where an elapsed duration finishes: on the day it reaches, as MS Project finishes it, even a
        day without hours of work, rather than at the end of the last hours of work before.
        """
        weekday = (moment.ordinal - 1) % DAYS_PER_WEEK
        return Moment(moment.ordinal, min(moment.hours, self._week[weekday]))

    def moment(self, count: Fraction, *, finish: bool) -> Moment:
        """Return where a count of hours of work from the origin is reached.

        On the end of a day's work, a finish reads that day's end, a start the first hour of work
        of the next working day.
        """
        weeks = count // self.weekly
        rest = count - weeks * self.weekly
        if finish and rest == 0:
            weeks, rest = weeks - 1, self.weekly
        monday = weeks * DAYS_PER_WEEK + 1
        for weekday, hours in enumerate(self._week):
            if hours > 0 and (rest <= hours if finish else rest < hours):
                return Moment(monday + weekday, rest)
            rest -= hours
        message = f"no moment reaches {count} hours of work"
        raise AssertionError(message)


def applicable_calendar(calendars: list[Calendar], default: Calendar) -> Calendar:
    """Return the calendar applicable to a task: each day, the fewest hours its calendars grant.

    The calendars are those of the roles of its labour lines; a task without any is on the
    default calendar (WF-PLA-0010).
    """
    if not calendars:
        return default
    days = zip(*(calendar.week for calendar in calendars), strict=True)
    fewest = tuple(min(hours) for hours in days)
    return Calendar((fewest[0], fewest[1], fewest[2], fewest[3], fewest[4], fewest[5], fewest[6]))


def weekly_calendar(hours: Sequence[Decimal]) -> Calendar:
    """Return the calendar of the hours worked on each day of a week, Monday first.

    Refuses, by ``ValueError``, a week that does not hold seven days of zero to twenty-four hours:
    what the estimate reads of a calendar of the reference, or of the applicable calendar of a task,
    to spread a line on (EP-07, #2549).
    """
    if len(hours) != DAYS_PER_WEEK:
        message = f"a week has {DAYS_PER_WEEK} days, not {len(hours)}"
        raise ValueError(message)
    if any(not 0 <= day <= HOURS_PER_ELAPSED_DAY for day in hours):
        message = f"a day holds from 0 to {HOURS_PER_ELAPSED_DAY} hours of work"
        raise ValueError(message)
    return Calendar((hours[0], hours[1], hours[2], hours[3], hours[4], hours[5], hours[6]))
