# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spreading of a load or an amount over the years and the months of a dated task.

A task is dated from an instant to another, on the calendar the line is worked on; its load or
amount is shared among the periods it crosses in proportion to the hours worked in each
(WF-DEV-0040-A, WF-DEV-0070-A, WF-DEV-0080-A). Past a date of calculation, only the part of the
task that follows it is shared, and the whole falls on the month of that date once the task is
over (WF-DEV-0070-A). The parts are not rounded: the last takes the rest, so that they always add
up to the total, to a ten-billionth, and the caller rounds once what it keeps (WF-DAT-0100).
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Context, Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.planning.interface import WorkInstant

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from waterfall.core.planning.interface import Calendar

MONTHS_PER_YEAR = 12
EXACT = Context(prec=34, rounding=ROUND_HALF_EVEN)
"""The context the parts are divided in: wide enough for an amount to the cent, and a few hours."""

PLACES = Decimal(1).scaleb(-10)
"""The scale of a part, a ten-billionth: the parts add up exactly in any context."""


@dataclass(frozen=True, slots=True, order=True)
class Month:
    """A civil month."""

    year: int
    month: int


@dataclass(frozen=True, slots=True)
class Placement:
    """A task as a line sees it: the calendar it is worked on, and its start and finish."""

    week: Calendar
    start: WorkInstant
    finish: WorkInstant

    def __post_init__(self) -> None:
        """Refuse a task that finishes before it starts."""
        if self.finish < self.start:
            message = "a task cannot finish before it starts"
            raise ValueError(message)


def spread_by_month(
    placement: Placement, amount: Decimal, *, as_of: date | None = None
) -> dict[Month, Decimal]:
    """Share an amount among the months of a task, in the order of the months.

    ``as_of`` is the date of calculation: the share then runs on the part of the task after it.

    The parts are not rounded to the cent: they keep ten decimals and the projection takes them
    as they are; the rounding to the cent is done once, after the projection.
    """
    return _spread(placement, amount, as_of, _month_of, _months)


def spread_by_year(
    placement: Placement, amount: Decimal, *, as_of: date | None = None
) -> dict[int, Decimal]:
    """Share an amount among the years of a task, in the order of the years.

    The parts are not rounded to the cent: they keep ten decimals and the projection takes them
    as they are; the rounding to the cent is done once, after the projection.
    """
    return _spread(placement, amount, as_of, _year_of, _years)


def _month_of(day: date) -> Month:
    return Month(day.year, day.month)


def _year_of(day: date) -> int:
    return day.year


def _months(first: date, last: date) -> Iterator[date]:
    """Yield the first day of each month from the one of ``first`` to the one of ``last``."""
    index = first.year * MONTHS_PER_YEAR + first.month - 1
    end = last.year * MONTHS_PER_YEAR + last.month - 1
    for number in range(index, end + 1):
        year, month = divmod(number, MONTHS_PER_YEAR)
        yield date(year, month + 1, 1)


def _years(first: date, last: date) -> Iterator[date]:
    """Yield the first day of each year from the one of ``first`` to the one of ``last``."""
    for year in range(first.year, last.year + 1):
        yield date(year, 1, 1)


def _spread[K](
    placement: Placement,
    amount: Decimal,
    as_of: date | None,
    key: Callable[[date], K],
    starts: Callable[[date, date], Iterator[date]],
) -> dict[K, Decimal]:
    start, finish = placement.start, placement.finish
    if as_of is not None:
        cut = WorkInstant(as_of)
        if finish <= cut:
            return {key(as_of): amount}
        start = max(start, cut)
    week = placement.week
    total = week.worked(finish) - week.worked(start)
    if total == 0:
        # No hour worked: the whole falls where the task ends (a milestone: where it stands).
        return {key(finish.day): amount}
    firsts = list(starts(start.day, finish.day))
    edges = [week.worked(min(max(WorkInstant(first), start), finish)) for first in firsts]
    edges.append(week.worked(finish))
    hours = [(key(first), edges[i + 1] - edges[i]) for i, first in enumerate(firsts)]
    return _shares(amount, total, [(period, worked) for period, worked in hours if worked > 0])


def _shares[K](
    amount: Decimal, total: Fraction, hours: list[tuple[K, Fraction]]
) -> dict[K, Decimal]:
    """Divide an amount in proportion to the hours; the last part is what the others leave."""
    parts: dict[K, Decimal] = {}
    left = amount
    for period, worked in hours[:-1]:
        share = Fraction(amount) * worked / total
        part = EXACT.divide(Decimal(share.numerator), Decimal(share.denominator)).quantize(
            PLACES, rounding=ROUND_HALF_EVEN
        )
        parts[period] = part
        left = EXACT.subtract(left, part)
    parts[hours[-1][0]] = left
    return parts
