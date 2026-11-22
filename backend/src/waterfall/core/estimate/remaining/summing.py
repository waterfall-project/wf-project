# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The remaining to commit summed, private to the module: a pure function (US-1580/L2).

The remaining to commit is the sum of the re-estimated amounts of the lines of the tasks not
completed, started or not, re-estimated or not; a provision line counts the amount its risk
computes, EP-08's, and is left out here unless asked (WF-RAE-0010; EP-09, "Les indicateurs du reste
à engager"): the indicators of the remaining ask for it, and count it whatever the state of its task
(``provisions``, US-2580/L1). Neither the base nor the clock is read: the numeric examples run on it
alone.
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


def remaining_sum(
    lines: Iterable[LineAmount], *, provisions: bool = False
) -> tuple[Decimal, dict[UUID, Decimal]]:
    """Give the remaining to commit of the lines, and each line's that counts, in their order.

    A line of a task not completed counts; a provision line counts if ``provisions`` is asked, and
    then whatever the state of its task, and no other way.
    """
    by_line = {
        line.node_id: line.reestimated_amount
        for line in lines
        if (provisions if line.is_provision else not line.is_completed)
    }
    return sum(by_line.values(), NOUGHT), by_line
