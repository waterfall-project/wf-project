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


@dataclass(frozen=True, slots=True, order=True)
class Month:
    """A civil month."""

    year: int
    month: int


# The months a task works in, in their order, each with its share of the hours, exact: what does not
# depend on the amount a line spreads, so that the lines of one task are weighed once (#3802).
type MonthWeights = tuple[tuple[Month, Fraction], ...]


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


def exact_by_month(
    placement: Placement, amount: Decimal, *, as_of: date | None = None
) -> dict[Month, Fraction]:
    """Share an amount among the months of a task, exactly, in the order of the months.

    The fractions ``spread_by_month`` rounds to ten decimals, which add up to the amount exactly: a
    caller that rounds a cumulated of them rounds it once (``parting``).
    """
    return exact_of(amount, month_weights(placement, as_of=as_of))


def month_weights(placement: Placement, *, as_of: date | None = None) -> MonthWeights:
    """Give the months a task works in, each with its share of the hours, exact, in their order.

    What ``exact_by_month`` shares an amount by, whatever the amount: a caller that spreads many
    lines of one task weighs it once, and gives the weights to ``exact_of``.
    """
    return tuple(_weights(placement, as_of, _month_of, _months))


def exact_of(amount: Decimal, weights: MonthWeights) -> dict[Month, Fraction]:
    """Share an amount among months by their weights, exactly (``exact_by_month``)."""
    return {month: Fraction(amount) * weight for month, weight in weights}


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
    return _shares(amount, _weights(placement, as_of, key, starts))


def _weights[K](
    placement: Placement,
    as_of: date | None,
    key: Callable[[date], K],
    starts: Callable[[date, date], Iterator[date]],
) -> list[tuple[K, Fraction]]:
    """Give the periods a task works in, in their order, each with its share of the hours, exact."""
    start, finish = placement.start, placement.finish
    if as_of is not None:
        cut = WorkInstant(as_of)
        if finish <= cut:
            return [(key(as_of), Fraction(1))]
        start = max(start, cut)
    week = placement.week
    total = week.worked(finish) - week.worked(start)
    if total == 0:
        # No hour worked: the whole falls where the task ends (a milestone: where it stands).
        return [(key(finish.day), Fraction(1))]
    firsts = list(starts(start.day, finish.day))
    edges = [week.worked(min(max(WorkInstant(first), start), finish)) for first in firsts]
    edges.append(week.worked(finish))
    hours = [(key(first), edges[i + 1] - edges[i]) for i, first in enumerate(firsts)]
    return [(period, worked / total) for period, worked in hours if worked > 0]


DECIMALS = 10
"""The scale of a part, a ten-billionth: the parts add up exactly in any context."""


def _rounded(share: Fraction) -> Decimal:
    """Round the fraction to the places once, a half going away from zero."""
    quotient, rest = divmod(abs(share.numerator) * 10**DECIMALS, share.denominator)
    if 2 * rest >= share.denominator:
        quotient += 1
    return Decimal(quotient if share >= 0 else -quotient).scaleb(-DECIMALS)


def _shares[K](amount: Decimal, weights: list[tuple[K, Fraction]]) -> dict[K, Decimal]:
    """Divide an amount in proportion to the hours; the last part is what the others leave."""
    parts: dict[K, Decimal] = {}
    left = amount
    for period, weight in weights[:-1]:
        part = _rounded(Fraction(amount) * weight)
        parts[period] = part
        left = EXACT.subtract(left, part)
    parts[weights[-1][0]] = left
    return parts
