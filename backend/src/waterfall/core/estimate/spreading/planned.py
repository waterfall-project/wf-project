# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned value on given lines and dates (WF-DEV-0080-A).

The planned value at a date is the part of the budget of the reference that should have been
earned by then: each line counts its budgeted amount, spread over the task as the reference dates
it in proportion to the hours worked, up to the end of the day of that date. A line of a milestone,
or of a task that works no hour, counts whole on its date. The lines are given: choosing them (the
lines of the reference outside the provisions) and reading their budgeted amounts is the caller's.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.planning.interface import WorkInstant

if TYPE_CHECKING:
    from collections.abc import Iterable

    from waterfall.core.estimate.spreading.spread import Placement

CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class PlannedLine:
    """A line of the reference: its budgeted amount, and its task as the reference dates it."""

    amount: Decimal
    placement: Placement


def planned_value(lines: Iterable[PlannedLine], at: date) -> Decimal:
    """Return the planned value at the end of a day, rounded once to the cent."""
    end = WorkInstant(at + timedelta(days=1))
    total = Fraction(0)
    for line in lines:
        total += Fraction(line.amount) * _earned(line, end)
    return (Decimal(total.numerator) / Decimal(total.denominator)).quantize(
        CENT, rounding=ROUND_HALF_EVEN
    )


def _earned(line: PlannedLine, end: WorkInstant) -> Fraction:
    """Return the share of a line earned before an instant, from 0 to 1."""
    placement = line.placement
    week, start, finish = placement.week, placement.start, placement.finish
    total = week.worked_between(start, finish)
    if total == 0:
        return Fraction(int(end > WorkInstant(start.day)))
    reached = min(max(end, start), finish)
    return week.worked_between(start, reached) / total
