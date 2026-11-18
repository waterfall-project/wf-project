# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The monthly parts a curve is cumulated from (WF-IND-0100-A, WF-IND-0110-A).

A line is spread over the months of its task by ``spreading`` of the estimate, in proportion to
the hours worked; an event — a termination, a document — falls in the month of its date. A part of
the future is translated by the payment delay of its line, in days, for the cash-out. The parts of a
line are those of the estimate (``rounded_parts``, ``remaining_parts``): each the difference of
two roundings to the cent, a half away from nought, of the exact cumulated of the line, so that the
curves, the projection of spending and the plan of workload sum the same parts (US-1690/L4, #3564;
``docs/api/DECISIONS.md``, US-2040/L1). The lines of a sum share one weighing (``weighing``): each
task is weighed once, whatever the number of its lines (#3802), and the parts of a computation are
kept by a ``Spreader`` (#3902). Pure: no database, no clock (the
date of calculation is an argument).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import (
    MONEY,
    amount_parts,
    remaining_parts,
    rounded_parts,
    weighing,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from waterfall.core.estimate.interface import Month, Placement, Weighing


@dataclass(frozen=True, slots=True)
class SpreadLine:
    """A line to spread: its amount, its task as dated, and the payment delay of the line."""

    amount: Decimal
    placement: Placement
    payment_delay_days: int = 0


def _spread_after(
    placement: Placement, amount: Decimal, as_of: date | None, weigh: Weighing | None = None
) -> dict[Month, Decimal]:
    """Spread an amount over the months of a task, the part after the end of ``as_of`` alone.

    The date of calculation belongs to the past — the actual cost counts the documents of its day,
    the planned value is read at its end —, so what is to come is what follows it
    (WF-IND-0100, WF-RAE-0040): the share starts at the first hour of the next day, and a task
    that ends before falls whole on the month of ``as_of``, not on that of the next day. ``weigh``
    is the weighing of the tasks of a sum, the task weighed each time without it.
    """
    if weigh is None:
        if as_of is None:
            return rounded_parts(placement, amount, MONEY)
        return remaining_parts(placement, amount, MONEY, as_of=as_of)
    if as_of is None:
        return rounded_parts(placement, amount, MONEY, weigh=weigh)
    return remaining_parts(placement, amount, MONEY, as_of=as_of, weigh=weigh)


def shifted(
    line: SpreadLine, *, as_of: date | None = None, weigh: Weighing | None = None
) -> dict[Month, Decimal]:
    """Spread a line by month, its curve translated by the payment delay of the line.

    The delayed curve is the other translated by the delay in days: its value at a day is the
    value of the other at that day less the delay, and each month holds what its end reads less
    what the end of the month before did, as the curve of the witness is read (``Flows.by``, at
    each month-end). Two months of the task never fall in one for that. The cumulated at each
    month-end is exact, the last the whole line, and rounded as the estimate rounds it.
    """
    if line.payment_delay_days == 0:
        return _spread_after(line.placement, line.amount, as_of, weigh)
    return spread_delayed(line, as_of=as_of)


def spread_delayed(line: SpreadLine, *, as_of: date | None = None) -> dict[Month, Decimal]:
    """Spread a line by the cumulated of its curve read at each month-end less its payment delay.

    The path of a line with a delay is that of the estimate (``amount_parts``, which the
    projection of spending reads too): one spreading, two readings. With a delay of nought it
    gives what ``_spread_after`` gives, which a test holds (WF-IND-0100-A).
    """
    return amount_parts(
        line.placement, line.amount, as_of=as_of, delay_days=line.payment_delay_days
    )


def line_shares(
    line: SpreadLine,
    *,
    as_of: date | None = None,
    delayed: bool = False,
    weigh: Weighing | None = None,
) -> dict[Month, Decimal]:
    """Spread a line over the months of its task, from the date of calculation when it is given.

    With ``as_of``, only the part of the task after it is spread, and the whole falls on the month
    of that date once the task is over (WF-IND-0100-A). ``delayed`` shifts each part by the payment
    delay of the line. ``weigh`` is the weighing of the tasks of a sum (``spread_lines``).
    """
    if delayed:
        return shifted(line, as_of=as_of, weigh=weigh)
    return _spread_after(line.placement, line.amount, as_of, weigh)


class Spreader:
    """Spread lines for one computation: each line spread once, whatever the sums it enters.

    The parts of a line are a pure value of its task, its amount, the date of calculation and,
    delayed, its payment delay — a line without delay is spread the same delayed or not
    (``shifted``) —: kept as long as the spreader is, never longer, they are added again rather
    than spread again. The cost curve with and without the delays, the curves of earned value, and
    every scope of a computation draw from the same lines (#3902). One weighing serves them all
    (``weighing``).
    """

    def __init__(self) -> None:
        """Start with no line spread, and a weighing of its own."""
        self._weigh = weighing()
        self._held: dict[tuple[Placement, Decimal, date | None, int], dict[Month, Decimal]] = {}

    def shares(
        self, line: SpreadLine, *, as_of: date | None = None, delayed: bool = False
    ) -> dict[Month, Decimal]:
        """Give the parts of a line as ``line_shares`` does, spread once: never to be changed."""
        delay = line.payment_delay_days if delayed else 0
        key = (line.placement, line.amount, as_of, delay)
        found = self._held.get(key)
        if found is None:
            found = line_shares(line, as_of=as_of, delayed=delayed, weigh=self._weigh)
            self._held[key] = found
        return found

    def spread(
        self, lines: Iterable[SpreadLine], *, as_of: date | None = None, delayed: bool = False
    ) -> dict[Month, Decimal]:
        """Add up, month by month, the parts of the lines (``spread_lines``)."""
        total: dict[Month, Decimal] = {}
        for line in lines:
            for month, part in self.shares(line, as_of=as_of, delayed=delayed).items():
                total[month] = total.get(month, Decimal(0)) + part
        return total


def spread_lines(
    lines: Iterable[SpreadLine],
    *,
    as_of: date | None = None,
    delayed: bool = False,
    spreader: Spreader | None = None,
) -> dict[Month, Decimal]:
    """Add up, month by month, the parts of the lines, each task weighed once.

    A line with a payment delay is spread by the path of the estimate (``amount_parts``), which
    weighs the task by itself: the weighing is kept for the lines without delay. ``spreader`` is
    that of the computation, whose lines are spread once for all its sums; a new one without.
    """
    spreading = spreader if spreader is not None else Spreader()
    return spreading.spread(lines, as_of=as_of, delayed=delayed)
