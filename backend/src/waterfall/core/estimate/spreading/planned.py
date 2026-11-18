# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned value on given lines and dates (WF-DEV-0080-A).

The planned value at a date is the part of the budget of the reference that should have been
earned by then: each line counts its budgeted amount, spread over the task as the reference dates
it in proportion to the hours worked, up to the end of the day of that date. A line of a milestone,
or of a task that works no hour, counts whole at the end of the task. The share of each line is
rounded to the cent on its own (``MONEY``), the planned value being the sum of those, and the
calendars the lines are worked on are those their marking kept. The lines are given: choosing them
(the lines of the reference outside the provisions) and reading their budgeted amounts is the
caller's.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.estimate.spreading.rounding import MONEY
from waterfall.core.planning.interface import WorkInstant

if TYPE_CHECKING:
    from collections.abc import Iterable

    from waterfall.core.estimate.spreading.spread import Placement


@dataclass(frozen=True, slots=True)
class PlannedLine:
    """A line of the reference: its budgeted amount, and its task as the reference dates it."""

    amount: Decimal
    placement: Placement


def planned_value(lines: Iterable[PlannedLine], at: date) -> Decimal:
    """Return the planned value at the end of a day: the sum of the shares of the lines.

    The share of each line is rounded once to the cent from its exact value, a half away from nought
    (``MONEY``), so that the planned value of any set of lines is exactly the sum of those of its
    parts (WF-IND-0020-A), and that of a line at the end of a month the sum of its parts rounded up
    to that month (``parting``). EP-07 and the indicators of EP-10 read it alike (#3566).
    """
    end = WorkInstant(at + timedelta(days=1))
    # The share earned depends on the task alone, not on the amount: each task counted once (#3802).
    shares: dict[Placement, Fraction] = {}
    total = Decimal("0.00")
    for line in lines:
        share = shares.get(line.placement)
        if share is None:
            share = shares[line.placement] = _earned(line.placement, end)
        total += MONEY.of(Fraction(line.amount) * share)
    return total


def _earned(placement: Placement, end: WorkInstant) -> Fraction:
    """Return the share of a task earned before an instant, from 0 to 1."""
    week, start, finish = placement.week, placement.start, placement.finish
    total = week.worked(finish) - week.worked(start)
    if total == 0:
        # No hour worked (a milestone, or a task over a weekend): the line counts whole at the
        # end of the task, the prudent side for the delay index, as ``spreading`` carries it.
        return Fraction(int(end > WorkInstant(finish.day)))
    reached = min(max(end, start), finish)
    return (week.worked(reached) - week.worked(start)) / total
