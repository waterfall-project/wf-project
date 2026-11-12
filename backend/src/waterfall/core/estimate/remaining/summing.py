# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The remaining to commit summed, private to the module: a pure function (US-1580/L2).

The remaining to commit is the sum of the re-estimated amounts of the lines of the tasks not
completed, started or not, re-estimated or not; a provision line counts the amount its risk
computes, EP-08's, and is left out here (WF-RAE-0010; EP-09, "Les indicateurs du reste à
engager"). Neither the base nor the clock is read: the numeric examples run on it alone.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from uuid import UUID

NOUGHT = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class LineAmount:
    """A line as the remaining reads it: its re-estimated amount, its task completed, its kind."""

    node_id: UUID
    reestimated_amount: Decimal
    is_completed: bool
    is_provision: bool = False


def remaining_sum(lines: Iterable[LineAmount]) -> tuple[Decimal, dict[UUID, Decimal]]:
    """Give the remaining to commit of the lines, and each line's that counts, in their order."""
    by_line = {
        line.node_id: line.reestimated_amount
        for line in lines
        if not line.is_completed and not line.is_provision
    }
    return sum(by_line.values(), NOUGHT), by_line
