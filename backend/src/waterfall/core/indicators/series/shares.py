# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The monthly parts a curve is cumulated from (WF-IND-0100-A, WF-IND-0110-A).

A line is spread over the months of its task by ``spreading`` of the estimate, in proportion to
the hours worked; an event — a termination, a document — falls in the month of its date. A part of
the future is translated by the payment delay of its line, in days, for the cash-out. The parts of a
line are those of the estimate (``rounded_parts``, ``parts_of_cumulated``): each the difference of
two roundings to the cent, a half away from nought, of the exact cumulated of the line, so that the
curves, the projection of spending and the plan of workload sum the same parts (US-1690/L4, #3564;
``docs/api/DECISIONS.md``, US-2040/L1). Pure: no database, no clock (the date of calculation is an
argument).
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import MONEY, parts_of_cumulated, rounded_parts
from waterfall.core.indicators.series.months import end_of, month_of, months_between
from waterfall.core.planning.interface import WorkInstant

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from waterfall.core.estimate.interface import Month, Placement


ONE_DAY = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class SpreadLine:
    """A line to spread: its amount, its task as dated, and the payment delay of the line."""

    amount: Decimal
    placement: Placement
    payment_delay_days: int = 0


def _fraction_spent(line: SpreadLine, as_of: date | None, day: date) -> Fraction:
    """Return the part of the amount a line has spent by the end of a day, in proportion to hours.

    What ``_spread_after`` shares, read at any day: the hours of work of the task up to the end
    of the day over its hours of work, those after the end of ``as_of`` alone when it is given;
    spent whole at the day of the task's end — at ``as_of`` for a task past its end, where it
    stands for a task without an hour of work.
    """
    start, finish = line.placement.start, line.placement.finish
    if as_of is not None:
        cut = WorkInstant(as_of + ONE_DAY)
        if finish <= cut:
            return Fraction(int(day >= as_of))
        start = max(start, cut)
    week = line.placement.week
    total = week.worked(finish) - week.worked(start)
    if total == 0:
        return Fraction(int(day >= finish.day))
    reached = min(max(WorkInstant(day + timedelta(days=1)), start), finish)
    return (week.worked(reached) - week.worked(start)) / total


def _spread_after(
    placement: Placement, amount: Decimal, as_of: date | None
) -> dict[Month, Decimal]:
    """Spread an amount over the months of a task, the part after the end of ``as_of`` alone.

    The date of calculation belongs to the past — the actual cost counts the documents of its day,
    the planned value is read at its end —, so what is to come is what follows it
    (WF-IND-0100, WF-RAE-0040): the share starts at the first hour of the next day, and a task
    that ends before falls whole on the month of ``as_of``, not on that of the next day.
    """
    if as_of is None:
        return rounded_parts(placement, amount, MONEY)
    after = as_of + ONE_DAY
    if placement.finish <= WorkInstant(after):
        return parts_of_cumulated([(month_of(as_of), Fraction(amount))], MONEY)
    return rounded_parts(placement, amount, MONEY, as_of=after)


def shifted(line: SpreadLine, *, as_of: date | None = None) -> dict[Month, Decimal]:
    """Spread a line by month, its curve translated by the payment delay of the line.

    The delayed curve is the other translated by the delay in days: its value at a day is the
    value of the other at that day less the delay, and each month holds what its end reads less
    what the end of the month before did, as the curve of the witness is read (``Flows.by``, at
    each month-end). Two months of the task never fall in one for that. The cumulated at each
    month-end is exact, the last the whole line, and rounded as the estimate rounds it.
    """
    if line.payment_delay_days == 0:
        return _spread_after(line.placement, line.amount, as_of)
    delay = timedelta(days=line.payment_delay_days)
    start, finish = line.placement.start.day, line.placement.finish.day
    if as_of is not None:
        start, finish = max(start, as_of), max(finish, as_of)
    amount = Fraction(line.amount)
    months = months_between(month_of(start + delay), month_of(finish + delay))
    cumulated = [
        (month, amount * _fraction_spent(line, as_of, end_of(month) - delay)) for month in months
    ]
    cumulated[-1] = (months[-1], amount)
    return parts_of_cumulated(cumulated, MONEY)


def line_shares(
    line: SpreadLine, *, as_of: date | None = None, delayed: bool = False
) -> dict[Month, Decimal]:
    """Spread a line over the months of its task, from the date of calculation when it is given.

    With ``as_of``, only the part of the task after it is spread, and the whole falls on the month
    of that date once the task is over (WF-IND-0100-A). ``delayed`` shifts each part by the payment
    delay of the line.
    """
    if delayed:
        return shifted(line, as_of=as_of)
    return _spread_after(line.placement, line.amount, as_of)


def spread_lines(
    lines: Iterable[SpreadLine], *, as_of: date | None = None, delayed: bool = False
) -> dict[Month, Decimal]:
    """Add up, month by month, the parts of the lines."""
    total: dict[Month, Decimal] = {}
    for line in lines:
        for month, part in line_shares(line, as_of=as_of, delayed=delayed).items():
            total[month] = total.get(month, Decimal(0)) + part
    return total
