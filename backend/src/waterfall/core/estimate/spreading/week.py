# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hours worked by a weekly calendar between two instants, counted without visiting the days.

A calendar gives the hours worked on each day of the week, Monday first (WF-REF-0110). The hours
of work from the first day of the proleptic calendar, a Monday, to an instant are the hours of the
full weeks before it plus those of the days of its week, so that an interval of any length costs
the same: no loop on the days (WF-DEV-0040-A).
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal

    from waterfall.core.planning.interface import WorkInstant

DAYS_PER_WEEK = 7
HOURS_PER_DAY = 24


@dataclass(frozen=True, slots=True)
class WorkWeek:
    """The hours worked on each day of the week, Monday first, as a calendar of the reference."""

    hours: tuple[Decimal, ...]
    _before: tuple[Fraction, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Refuse a week that does not hold seven days of zero to twenty-four hours."""
        if len(self.hours) != DAYS_PER_WEEK:
            message = f"a week has {DAYS_PER_WEEK} days, not {len(self.hours)}"
            raise ValueError(message)
        if any(not 0 <= day <= HOURS_PER_DAY for day in self.hours):
            message = f"a day holds from 0 to {HOURS_PER_DAY} hours of work"
            raise ValueError(message)
        before = [Fraction(0)]
        for day in self.hours:
            before.append(before[-1] + Fraction(day))
        object.__setattr__(self, "_before", tuple(before))

    @property
    def weekly(self) -> Fraction:
        """Return the hours of a week of work."""
        return self._before[-1]

    def count(self, instant: WorkInstant) -> Fraction:
        """Return the hours of work from the origin to an instant.

        The hours of the instant's day count up to the hours that day grants: an instant past them
        counts the whole day.
        """
        weeks, weekday = divmod(instant.day.toordinal() - 1, DAYS_PER_WEEK)
        worked = min(Fraction(instant.hours), Fraction(self.hours[weekday]))
        return weeks * self.weekly + self._before[weekday] + worked

    def worked_between(self, first: WorkInstant, last: WorkInstant) -> Fraction:
        """Return the hours of work from one instant to a later one, exactly."""
        return self.count(last) - self.count(first)
