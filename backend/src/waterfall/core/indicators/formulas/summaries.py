# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The physical progress of the summary tasks, pure (WF-IND-0060; US-1680).

For each summary asked, the budgeted amounts its subtree bears, its own lines included, the
provisions left out by whoever gives them, and the share of them its completed tasks earn: a task
earns the amounts of its own lines when it is completed — a summary when all its subordinates are
—, a task started earns nothing, whatever its time spent (WF-IND-0030). The ratio is rounded once,
to four decimals; a subtree that bears no budgeted amount is not computable (``no_budgeted_amount``,
WF-IND-0010), never nought.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.indicators.formulas.computable import NO_BUDGETED_AMOUNT, Computable
from waterfall.core.indicators.formulas.rounding import NOUGHT, round_ratio

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from decimal import Decimal
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class SummaryTask:
    """A task of a structure as its physical progress weighs it.

    Its parent task, none at the root; whether it is completed; the budgeted amounts of its own
    lines, the provisions left out.
    """

    parent_id: UUID | None
    completed: bool
    earnable: Decimal


def summary_progress(
    tasks: Mapping[UUID, SummaryTask], summaries: Collection[UUID]
) -> dict[UUID, Computable]:
    """Give the physical progress of each summary asked, from every task of its structure.

    The amounts of each task climb to each of its ancestors asked, so that every subtree is summed
    in one pass over the tasks.
    """
    totals = dict.fromkeys(summaries, NOUGHT)
    earned = dict.fromkeys(summaries, NOUGHT)
    for task_id, task in tasks.items():
        if task.earnable == NOUGHT:
            continue
        held: UUID | None = task_id
        while held is not None:
            if held in totals:
                totals[held] += task.earnable
                if task.completed:
                    earned[held] += task.earnable
            above = tasks.get(held)
            held = None if above is None else above.parent_id
    return {each: _share(earned[each], totals[each]) for each in totals}


def _share(earned: Decimal, total: Decimal) -> Computable:
    if total == NOUGHT:
        return Computable.not_computable(NO_BUDGETED_AMOUNT)
    return Computable.of(round_ratio(earned / total))
