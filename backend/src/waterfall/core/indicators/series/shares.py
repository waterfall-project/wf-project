# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The monthly parts a curve is cumulated from (WF-IND-0100-A, WF-IND-0110-A).

A line is spread over the months of its task by ``spreading`` of the estimate, in proportion to
the hours worked; an event — a termination, a document — falls in the month of its date. A part of
the future is shifted by the payment delay of its line for the cash-out. Pure: no database, no clock
(the date of calculation is an argument), and the parts are not rounded here (WF-DAT-0100).
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import spread_by_month
from waterfall.core.indicators.series.months import end_of, month_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date

    from waterfall.core.estimate.interface import Month, Placement


@dataclass(frozen=True, slots=True)
class SpreadLine:
    """A line to spread: its amount, its task as dated, and the payment delay of the line."""

    amount: Decimal
    placement: Placement
    payment_delay_days: int = 0


def shifted(shares: Mapping[Month, Decimal], delay_days: int) -> dict[Month, Decimal]:
    """Shift the parts of a line by a payment delay, each from the end of its month.

    A part is dated where the curve counts it, at the end of its month; it falls in the month that
    holds that day plus the delay, so the delayed curve is the other translated by the delay and
    read again at the month-ends. No delay leaves the parts where they are.
    """
    moved: dict[Month, Decimal] = {}
    for month, part in shares.items():
        target = month_of(end_of(month) + timedelta(days=delay_days))
        moved[target] = moved.get(target, Decimal(0)) + part
    return moved


def line_shares(
    line: SpreadLine, *, as_of: date | None = None, delayed: bool = False
) -> dict[Month, Decimal]:
    """Spread a line over the months of its task, from the date of calculation when it is given.

    With ``as_of``, only the part of the task after it is spread, and the whole falls on the month
    of that date once the task is over (WF-IND-0100-A). ``delayed`` shifts each part by the payment
    delay of the line.
    """
    shares = spread_by_month(line.placement, line.amount, as_of=as_of)
    return shifted(shares, line.payment_delay_days) if delayed else shares


def spread_lines(
    lines: Iterable[SpreadLine], *, as_of: date | None = None, delayed: bool = False
) -> dict[Month, Decimal]:
    """Add up, month by month, the parts of the lines."""
    total: dict[Month, Decimal] = {}
    for line in lines:
        for month, part in line_shares(line, as_of=as_of, delayed=delayed).items():
            total[month] = total.get(month, Decimal(0)) + part
    return total


def events_by_month(
    events: Iterable[tuple[date, Decimal]], *, until: date | None = None
) -> dict[Month, Decimal]:
    """Add up, by month of their date, dated amounts; those after ``until`` are left out."""
    total: dict[Month, Decimal] = {}
    for day, amount in events:
        if until is not None and day > until:
            continue
        month = month_of(day)
        total[month] = total.get(month, Decimal(0)) + amount
    return total
