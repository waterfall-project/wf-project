# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parts of the amount of a line by month, as it is consumed or paid out (US-2050, WF-DEV-0100).

Pure. The amount of a line is spread over the hours worked of its task (``spreading``); a part is
the difference of two roundings to the cent of its cumulated amount at the end of a month and at
the end of the month before, the last month closing on the whole line (``parting``). On request
the line is paid out: its curve is shifted by the payment delay of the line, in days, so that its
cumulated amount at the end of a month is what the task had spent at that day less the delay, as
the curve of the costs reads it (``getCostCurve``, WF-IND-0100). With a date of calculation, only
the part of the task after that day is spread — the day itself belongs to the past —, and a task
that ends before it falls whole in the month of that day, shifted by the delay.

The cumulated is exact, rounded once; a month the rounding leaves at nought is not one the line
loads (#3096).
"""

from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.estimate.parting import ONE_DAY
from waterfall.core.estimate.spreading import MONEY, Month
from waterfall.core.planning.interface import WorkInstant

if TYPE_CHECKING:
    from waterfall.core.estimate.spreading import Placement

MONTHS_PER_YEAR = 12
WHOLE = Fraction(1)
NOUGHT = Fraction(0)


def month_of(day: date) -> Month:
    """Give the month of a day."""
    return Month(day.year, day.month)


def _last_day(month: Month) -> date:
    """Give the last day of a month."""
    year, rest = divmod(month.year * MONTHS_PER_YEAR + month.month, MONTHS_PER_YEAR)
    return date(year, rest + 1, 1) - ONE_DAY


def _months(first: Month, last: Month) -> list[Month]:
    """Give the months from one to another, the two included."""
    index = first.year * MONTHS_PER_YEAR + first.month - 1
    end = last.year * MONTHS_PER_YEAR + last.month - 1
    found: list[Month] = []
    for number in range(index, end + 1):
        year, rest = divmod(number, MONTHS_PER_YEAR)
        found.append(Month(year, rest + 1))
    return found


def _spent(placement: Placement, start: WorkInstant, day: date) -> Fraction:
    """Give the part of the hours worked from ``start`` to the finish done by the end of a day.

    A task without an hour of work to do is spent whole at the day it ends.
    """
    week, finish = placement.week, placement.finish
    total = week.worked(finish) - week.worked(start)
    if total == 0:
        return WHOLE if day >= finish.day else NOUGHT
    reached = min(max(WorkInstant(day + ONE_DAY), start), finish)
    return (week.worked(reached) - week.worked(start)) / total


def amount_parts(
    placement: Placement,
    amount: Decimal,
    *,
    as_of: date | None = None,
    delay_days: int = 0,
) -> dict[Month, Decimal]:
    """Give the parts of an amount in the months it loads, in their order, rounded to the cent.

    ``as_of`` is the date of calculation of a remaining to commit: the amount is then spread over
    the part of its task after that day, or falls whole in its month once the task is over;
    ``delay_days`` shifts each part by the payment delay of the line. The parts sum to the amount,
    rounded, and none is negative for an amount that is not.
    """
    start, finish = placement.start, placement.finish
    delay = timedelta(days=delay_days)
    if as_of is not None:
        cut = WorkInstant(as_of + ONE_DAY)
        if finish <= cut:
            return {month_of(as_of + delay): MONEY.of(amount)} if amount else {}
        start = max(start, cut)
    found: dict[Month, Decimal] = {}
    months = _months(month_of(start.day + delay), month_of(finish.day + delay))
    before = Decimal(0)
    for month in months:
        # Exact, the cumulated of the last month is the whole line.
        spent = WHOLE if month == months[-1] else _spent(placement, start, _last_day(month) - delay)
        done = MONEY.of(Fraction(amount) * spent)
        if part := done - before:
            found[month] = part
        before = done
    return found
