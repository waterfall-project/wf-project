# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The monthly parts a curve is cumulated from (WF-IND-0100-A, WF-IND-0110-A).

A line is spread over the months of its task by ``spreading`` of the estimate, in proportion to
the hours worked; an event — a termination, a document — falls in the month of its date. A part of
the future is translated by the payment delay of its line, in days, for the cash-out. Pure: no
database, no clock (the date of calculation is an argument), and the parts are not rounded here
(WF-DAT-0100).
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import spread_by_month
from waterfall.core.indicators.series.months import end_of, month_of, months_between
from waterfall.core.planning.interface import WorkInstant

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from waterfall.core.estimate.interface import Month, Placement


# The parts of a delayed line are cut at ten places — far below the cent, so that the rounding of
# the cumulative total at the cent never sees them — and the last part takes the rest, so that the
# sum is the amount. The estimate exposes no such constant in its interface. 50 significant digits
# hold the quotient of any amount by the hours of a task with ten places to spare, so the context
# never rounds before ``quantize`` does: an amount has at most 14 digits, the precision of the
# columns that hold the amounts (``AMOUNT_PRECISION`` of the tables of the estimate, ``Numeric(14,
# 2)``; WF-DAT-0100), as ``Money`` of the contract.
TEN_PLACES = Decimal("0.0000000001")
PRECISION = 50
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


def _to_ten_places(share: Fraction) -> Decimal:
    with localcontext() as context:
        context.prec = PRECISION
        return (Decimal(share.numerator) / Decimal(share.denominator)).quantize(
            TEN_PLACES, rounding=ROUND_HALF_UP
        )


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
        return spread_by_month(placement, amount)
    after = as_of + ONE_DAY
    if placement.finish <= WorkInstant(after):
        return {month_of(as_of): amount}
    return spread_by_month(placement, amount, as_of=after)


def shifted(line: SpreadLine, *, as_of: date | None = None) -> dict[Month, Decimal]:
    """Spread a line by month, its curve translated by the payment delay of the line.

    The delayed curve is the other translated by the delay in days: its value at a day is the
    value of the other at that day less the delay, and each month holds what its end reads less
    what the end of the month before did, as the curve of the witness is read (``Flows.by``, at
    each month-end). Two months of the task never fall in one for that. The parts keep ten places,
    the last taking the rest, so that they add up to the amount.
    """
    if line.payment_delay_days == 0:
        return _spread_after(line.placement, line.amount, as_of)
    delay = timedelta(days=line.payment_delay_days)
    start, finish = line.placement.start.day, line.placement.finish.day
    if as_of is not None:
        start, finish = max(start, as_of), max(finish, as_of)
    parts: dict[Month, Decimal] = {}
    left, before = line.amount, Fraction(0)
    months = months_between(month_of(start + delay), month_of(finish + delay))
    for month in months:
        reached = _fraction_spent(line, as_of, end_of(month) - delay)
        if month == months[-1]:
            share = left
        else:
            share = _to_ten_places(Fraction(line.amount) * (reached - before))
        before = reached
        left -= share
        if share:
            parts[month] = share
    return parts


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
