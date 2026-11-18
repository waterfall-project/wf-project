# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The five amounts of each scope of a project at a day, in one pass (EP-10, "Le calcul").

The revision computed R and the reference Ref of the project are read once — their lines, the tasks
of R, the remaining to commit of R drawn from them —, and the scopes asked are drawn from them in
memory, the actual cost of each from the sums by subproject at the day, read once (WF-IND-0010 to
WF-IND-0030, WF-IND-0020; #3569):

- the reference budget, the budgeted amounts of the lines of Ref, provisions left out, that bear
  the scope in Ref (``unassigned``: no subproject);
- the planned value, those lines spread over their tasks as Ref dates them, at the end of the day;
- the earned value, the budgeted amounts of those lines whose task, by its lineage, is completed in
  R on or before the day — a task started, or completed after, earns nothing, a lineage R does not
  hold neither, and a line of a task created by an occurred risk is not earned;
- the actual cost, the tracked lines of the scope dated on or before the day
  (``actual_costs_until_by_subproject``, ``scope_cost``);
- the remaining to commit, that of each line of R (``remaining_of_lines``) whose subproject in R
  is the scope: a line moved from a subproject to another since the reference earns in the first
  and counts its remaining in the second.

Nothing is rounded here but the planned value, whose share of each line is rounded by the
spreading, so that the scopes sum to the project (WF-IND-0020-A); the formulas round the rest
(WF-DAT-0100).
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from waterfall.core.costs.interface import (
    PROJECT,
    UNASSIGNED,
    actual_costs_until_by_subproject,
    scope_cost,
)
from waterfall.core.estimate.interface import (
    lines_for_indicators,
    planned_value_at,
    remaining_of_lines,
)
from waterfall.core.indicators.formulas import NOUGHT, Amounts, indicators_of
from waterfall.core.indicators.shaping import Context, indicators_document
from waterfall.core.planning.interface import tasks_for_indicators
from waterfall.core.projects.interface import current_day

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.estimate.interface import IndicatorLine
    from waterfall.core.indicators.interface.documents import Document
    from waterfall.core.planning.interface import IndicatorTask

COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class Basis:
    """What a computation reads: a project, its revision computed, and its reference if any."""

    project_id: UUID
    revision_id: UUID
    reference_id: UUID | None


def in_scope(scope: CostScope, subproject_id: UUID | None) -> bool:
    """Tell whether a line of this subproject, none for the project alone, is of the scope."""
    if scope == PROJECT:
        return True
    if scope == UNASSIGNED:
        return subproject_id is None
    return subproject_id == scope


def _summed(amounts: Iterable[Decimal]) -> Decimal:
    return sum(amounts, NOUGHT)


def read_lines(
    session: Session, basis: Basis
) -> tuple[tuple[IndicatorTask, ...], tuple[IndicatorLine, ...], tuple[IndicatorLine, ...]]:
    """Read the tasks of the revision computed, its lines, and those of the reference, once.

    The reference is empty without one, and the lines of the revision when it is the reference.
    """
    project_id, revision_id, reference_id = basis.project_id, basis.revision_id, basis.reference_id
    tasks = tasks_for_indicators(session, project_id, revision_id)
    lines = lines_for_indicators(session, project_id, revision_id, tasks)
    reference: tuple[IndicatorLine, ...] = ()
    if reference_id == revision_id:
        reference = lines
    elif reference_id is not None:
        reference = lines_for_indicators(session, project_id, reference_id)
    return tasks, lines, reference


def amounts_by_scope(
    session: Session, basis: Basis, day: date, scopes: Collection[CostScope]
) -> dict[CostScope, Amounts]:
    """Give the five amounts of each scope asked, on a revision and the reference, at a day.

    Without a reference, the budget, the planned value and the earned value are nought.
    """
    tasks, lines, reference = read_lines(session, basis)
    read = LinesRead(reference, lines, remaining_of_lines(tasks, lines).by_line, completions(tasks))
    return amounts_from(session, basis.project_id, read, day, scopes)


def completions(tasks: Iterable[IndicatorTask]) -> dict[UUID, date]:
    """Give the day each lineage of task completed in a revision was completed on."""
    return {
        task.lineage_id: task.completed_on
        for task in tasks
        if task.progress == COMPLETED and task.completed_on is not None
    }


@dataclass(frozen=True, slots=True)
class LinesRead:
    """What the amounts of every scope are drawn from, read once on a revision and the reference.

    The lines of Ref and of R, the remaining to commit of each line of R, and the day each lineage
    of task completed in R was completed on.
    """

    reference: tuple[IndicatorLine, ...]
    lines: tuple[IndicatorLine, ...]
    remaining: Mapping[UUID, Decimal]
    completed: Mapping[UUID, date]


def amounts_from(
    session: Session, project_id: UUID, read: LinesRead, day: date, scopes: Collection[CostScope]
) -> dict[CostScope, Amounts]:
    """Give the five amounts of each scope asked, from the lines read, at a day.

    Only the actual cost is read here, once for every scope; what the curves read once serves as
    well (the cache of the indicators, US-1720/L2).
    """
    reference, lines, remaining = read.reference, read.lines, read.remaining
    spent = actual_costs_until_by_subproject(session, project_id, day)
    earned = {lineage for lineage, done in read.completed.items() if done <= day}
    subprojects = {line.node_id: line.subproject_id for line in lines}
    found: dict[CostScope, Amounts] = {}
    for scope in scopes:
        budgeted = [line for line in reference if in_scope(scope, line.subproject_id)]
        found[scope] = Amounts(
            reference_budget=_summed(line.budgeted_amount for line in budgeted),
            planned_value=planned_value_at(budgeted, day),
            earned_value=_summed(
                line.budgeted_amount
                for line in budgeted
                if line.task_origin_risk_id is None and line.task_lineage_id in earned
            ),
            actual_cost=scope_cost(spent, scope),
            remaining=_summed(
                amount
                for node_id, amount in remaining.items()
                if in_scope(scope, subprojects[node_id])
            ),
        )
    return found


def day_documents(
    session: Session, basis: Basis, context: Context, scopes: Collection[CostScope]
) -> dict[CostScope, Document]:
    """Compute the indicators of the scopes asked on a revision, at the day of ``context``.

    In one pass; each document carries the context given, its own scope, and no zone.
    """
    amounts = amounts_by_scope(session, basis, current_day(context.computed_at), scopes)
    return {
        scope: indicators_document(indicators_of(found, None), replace(context, scope=scope))
        for scope, found in amounts.items()
    }
