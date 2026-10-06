# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hours of work of a calendar, to date the tasks of the fake back's structure.

A calendar gives the hours worked on each day of the week (WF-REF-0110); a task is dated in
hours of work on its applicable calendar, hour after hour (WF-PLA-0010), and an instant of
work is a date and the hours of work elapsed that day (WF-DAT-0100). Everything here counts
the hours of work elapsed since a fixed Monday, ``ORIGIN``: an instant is turned into that
count, moved by hours of work, and turned back into an instant. Two readings of a count fall
on a day boundary: the end of a day's work, where a task finishes, and the first hour of the
next working day, where a task starts.

A simplification of the scheduling of EP-06, to be replaced by its kernel: no holidays, no
part time, as WF-REF-0110 says of a calendar, and nothing but whole weeks of calendar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_FLOOR, Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ORIGIN = date(2026, 1, 5)
"""The Monday the hours of work are counted from; an instant before it counts negatively."""

HOURS_PER_DAY = Decimal(8)
HOURS_PER_WEEK = Decimal(40)
DAYS_PER_MONTH = Decimal(20)
"""The installation's constants, which turn a duration or a lag in days, weeks or months of
work into hours (WF-PLA-0160): 8, 40 and 20, their default values."""

FINISH_TO_START, START_TO_START = "finish_to_start", "start_to_start"


def to_hours(value: Decimal | int, unit: str) -> Decimal:
    """Return a duration or a lag of work in hours, by the installation's constants (WF-PLA-0160).

    The units of work alone: an elapsed time is not placed on a calendar.
    """
    if unit == "min":
        return Decimal(value) / 60
    per_unit = {
        "h": Decimal(1),
        "d": HOURS_PER_DAY,
        "w": HOURS_PER_WEEK,
        "mo": HOURS_PER_DAY * DAYS_PER_MONTH,
    }
    if unit not in per_unit:
        message = f"{unit} is not a unit of work"
        raise ValueError(message)
    return value * per_unit[unit]


@dataclass(frozen=True, slots=True, order=True)
class Instant:
    """An instant of work: a date, and the hours of work elapsed that day (WF-DAT-0100).

    Instants compare by date, then by hours: the hours of two calendars are counted from the
    same start of the day.
    """

    day: date
    hours: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True)
class Calendar:
    """The hours worked on each day of the week, Monday first, under an identifier."""

    calendar_id: str
    week: tuple[Decimal, ...]

    @property
    def weekly(self) -> Decimal:
        """Return the hours of a week of work; a calendar without any cannot date a task."""
        hours = sum(self.week, Decimal(0))
        if hours <= 0:
            message = f"the calendar {self.calendar_id} grants no hour of work in a week"
            raise ValueError(message)
        return hours

    def hours_on(self, day: date) -> Decimal:
        """Return the hours worked on a day."""
        return self.week[day.weekday()]

    def elapsed(self, at: Instant) -> Decimal:
        """Return the hours of work from ORIGIN to an instant; hours past the day's are not."""
        weeks, weekday = divmod((at.day - ORIGIN).days, 7)
        before = sum(self.week[:weekday], Decimal(0))
        return weeks * self.weekly + before + min(at.hours, self.week[weekday])

    def instant(self, count: Decimal, *, finish: bool) -> Instant:
        """Return the instant where a count of hours of work from ORIGIN is reached.

        On a day boundary, a finish is the end of the last day's work, and a start the first
        hour of the next working day.
        """
        # Decimal division truncates towards zero: floored, a count before ORIGIN falls in
        # the week it belongs to.
        weeks = (count / self.weekly).to_integral_value(rounding=ROUND_FLOOR)
        rest = count - weeks * self.weekly
        if finish and rest == 0:
            weeks, rest = weeks - 1, self.weekly
        monday = ORIGIN + timedelta(weeks=int(weeks))
        for weekday, hours in enumerate(self.week):
            if hours > 0 and (rest <= hours if finish else rest < hours):
                return Instant(monday + timedelta(days=weekday), rest)
            rest -= hours
        message = f"no instant reaches {count} hours on {self.calendar_id}"
        raise AssertionError(message)

    def start_at(self, at: Instant) -> Instant:
        """Return the first instant of work from an instant: where a task may start."""
        return self.instant(self.elapsed(at), finish=False)

    def place(self, count: Decimal, hours: Decimal) -> tuple[Instant, Instant]:
        """Return the start and the finish of a task of so many hours from a count of hours.

        A task of no duration, a milestone, sits at one instant: the finish reading of its
        count, where what precedes it finishes (WF-PLA-0050).
        """
        if hours == 0:
            at = self.instant(count, finish=True)
            return at, at
        return self.instant(count, finish=False), self.instant(count + hours, finish=True)

    def finish_after(self, start: Instant, hours: Decimal) -> Instant:
        """Return where a task of so many hours of work, started at an instant, finishes."""
        return self.place(self.elapsed(start), hours)[1]

    def start_before(self, finish: Instant, hours: Decimal) -> Instant:
        """Return where a task of so many hours of work must start to finish at an instant."""
        return self.place(self.elapsed(finish) - hours, hours)[0]

    def work_between(self, first: Instant, last: Instant) -> Decimal:
        """Return the hours of work from one instant to another."""
        return self.elapsed(last) - self.elapsed(first)


def applicable(calendars: list[Calendar], default: Calendar) -> Calendar:
    """Return the calendar of a task: each day, the fewest hours its calendars grant.

    The calendars are those of the roles of its labour lines; a task without one is on the
    default calendar (WF-PLA-0010). One calendar is itself.
    """
    if not calendars:
        return default
    first, *others = calendars
    if all(other == first for other in others):
        return first
    week = tuple(min(hours) for hours in zip(*(each.week for each in calendars), strict=True))
    names = "∩".join(sorted({each.calendar_id for each in calendars}))
    return Calendar(names, week)


@dataclass(frozen=True, slots=True)
class Predecessor:
    """A predecessor as its link sees it: its dates, the type of the link and its signed lag."""

    start: Instant
    finish: Instant
    link_type: str = FINISH_TO_START
    lag: Decimal = Decimal(0)


def follow(
    calendar: Calendar, predecessors: Sequence[Predecessor], hours: Decimal, origin: Instant
) -> tuple[Instant, Instant]:
    """Return the start and the finish of a task in automatic mode, on its calendar.

    Each link counts from its predecessor's finish, or start for a start-to-start link, its
    lag in hours placed on the successor's calendar (WF-PLA-0010): the task starts at the
    latest count its links allow, or at the origin without any (WF-PLA-0030).
    """
    counts = [calendar.elapsed(_anchor(each)) + each.lag for each in predecessors]
    return calendar.place(max(counts, default=calendar.elapsed(origin)), hours)


def _anchor(predecessor: Predecessor) -> Instant:
    """Return where a link counts from: the finish of its predecessor, or its start."""
    if predecessor.link_type == FINISH_TO_START:
        return predecessor.finish
    if predecessor.link_type == START_TO_START:
        return predecessor.start
    message = f"the link {predecessor.link_type} is not placed here"
    raise ValueError(message)
