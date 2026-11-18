# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit, and the coverage of the risks they show (US-1600).

``remaining_of_revision`` sums the reestimated amounts of the lines, not provisions, of the tasks
not completed of the main structure of a revision, at the state of its tasks, and gives each line's
— what the indicators read, and EP-10 for the projection of the project manager and the index of
cost. ``remaining_of_lines`` gives the same from the tasks and the lines of the revision the
indicators have read already (``tasks_for_indicators``, ``lines_for_indicators``), without reading
the tree again (#3569, #3802). ``remaining_indicators`` reads the indicators of a revision
(``getRemainingIndicators``), their coverage of the risks by ``risk_coverage`` (EP-09, "Les
indicateurs du reste à engager").

The coverage is a registry the estimate declares and the risks fill (``register_coverage``, EP-08):
until then none is registered, and the coverage is zero — no reserve, no provision left, no cost of
a risk occurred, no variance —, what is true of a project without risk.

Declared by US-1580/L1 with their results, the coverage served from then on;
``remaining_of_revision`` filled by US-1580/L2 (EP-09, "Ce que le cadrage laisse à EP-10"; #2708),
``remaining_indicators`` by US-1600, which reads the clock from its caller (``at``), as the
indicators of the estimate do. The margins are ``Decimal``, never absent: a subproject without a
reference has a budget of nought (#2715).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from waterfall.core.costs.interface import UNASSIGNED, actual_cost_by_subproject
from waterfall.core.estimate.indicating import natures_of
from waterfall.core.estimate.placing import placed_lines
from waterfall.core.estimate.reading import COMPLETED, rows_of
from waterfall.core.estimate.remaining.balancing import (
    balances,
    delta_to_previous,
    delta_to_reference,
    distributed,
)
from waterfall.core.estimate.remaining.comparing import (
    reference_budgets,
    summed_by_subproject,
)
from waterfall.core.estimate.remaining.reviewing import (
    remaining_of_placed,
    revision_remaining,
)
from waterfall.core.estimate.remaining.summing import NOUGHT, LineAmount, remaining_sum
from waterfall.core.projects.interface import subproject_labels
from waterfall.core.revisions.interface import read_revision_for
from waterfall.platform.registry import Registry

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence
    from datetime import datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.estimate.indicating import AmountByKey
    from waterfall.core.estimate.lining import IndicatorLine
    from waterfall.core.estimate.placing import Placed
    from waterfall.core.planning.interface import IndicatorTask
    from waterfall.core.revisions.interface import RevisionRead


# The zones a subproject is classified in: the contract's ``AlertZone`` without ``watch``.
type AlertZone = Literal["alert", "nominal"]


@dataclass(frozen=True, slots=True)
class RevisionRemaining:
    """The remaining to commit of a revision: its total, and each line's, by its node."""

    total: Decimal
    by_line: Mapping[UUID, Decimal]


@dataclass(frozen=True, slots=True)
class Coverage:
    """The coverage of the risks of a revision (``RiskCoverageTotals``, WF-RIS-0050)."""

    reserve: Decimal
    remaining_provisions: Decimal
    occurred_cost: Decimal
    occurred_reestimated: Decimal
    coverage_variance: Decimal


@dataclass(frozen=True, slots=True)
class SubprojectBalance:
    """The margin of a subproject, or of the lines of the project alone (``SubprojectBalance``).

    ``key`` is the identifier of the subproject, or ``unassigned``; ``budget`` the budgeted amounts
    of the reference, nought without one — the amount, not the absence, as the contract's ``Money``
    asks; ``variance`` the budget minus the actual cost and the remaining, negative beyond the
    budget; ``zone`` ``alert`` when it is, ``nominal`` otherwise, never ``watch``.
    """

    key: str
    label: str | None
    budget: Decimal
    actual_cost: Decimal
    remaining: Decimal
    variance: Decimal
    is_over_budget: bool
    zone: AlertZone


@dataclass(frozen=True, slots=True)
class CalculationContext:
    """The context of a computation, as the screens display it (``CalculationContext``).

    ``revision_status`` is the status of the revision as the contract writes it; ``scope`` is
    ``project``, ``unassigned`` or a subproject, the ``CostScope`` of the actual
    costs; ``is_stored`` is false until EP-10 keeps the indicators.
    """

    revision_id: UUID
    revision_status: str
    computed_at: datetime
    scope: CostScope
    is_stored: bool


@dataclass(frozen=True, slots=True)
class RemainingIndicators:
    """The indicators of the remaining to commit of a revision (``RemainingIndicators``).

    Computed at the reading, never stored (``context.is_stored`` false until EP-10 keeps them);
    the deltas none without a reference, or without a revision marked after the passage In progress.
    """

    context: CalculationContext
    total: Decimal
    by_cost_type: tuple[AmountByKey, ...]
    by_subproject: tuple[SubprojectBalance, ...]
    coverage: Coverage
    delta_to_reference: Decimal | None
    delta_to_previous_revision: Decimal | None


ZERO = NOUGHT
NO_COVERAGE = Coverage(ZERO, ZERO, ZERO, ZERO, ZERO)

# What answers the coverage of the risks of a revision of a project: one at most, the risks'.
_COVERAGE: Registry[Callable[[Session, UUID, UUID], Coverage]] = Registry("estimate.coverage")


def register_coverage(cover: Callable[[Session, UUID, UUID], Coverage]) -> Callable[[], None]:
    """Add what answers the coverage of the risks; give its withdrawal; refused if one answers."""
    if _COVERAGE.entries():
        msg = "the coverage of the risks has its answer already"
        raise ValueError(msg)
    return _COVERAGE.register(cover)


def risk_coverage(session: Session, project_id: UUID, revision_id: UUID) -> Coverage:
    """Give the coverage of the risks of a revision of a project: zero while nothing answers."""
    held = _COVERAGE.entries()
    return held[0](session, project_id, revision_id) if held else NO_COVERAGE


def remaining_of_revision(
    session: Session, project_id: UUID, revision_id: UUID
) -> RevisionRemaining:
    """Give the remaining to commit of a revision, total and by line, at the state of its tasks.

    The re-estimated amounts of the lines, provisions left out, of the tasks not completed of its
    main structure — started or not, re-estimated or not —, the current revision or a marked one,
    as its tasks stand in it (WF-RAE-0010); none for a revision without a main structure.
    """
    total, by_line = revision_remaining(session, project_id, revision_id)
    return RevisionRemaining(total, by_line)


def remaining_of_lines(
    tasks: Iterable[IndicatorTask], lines: Iterable[IndicatorLine]
) -> RevisionRemaining:
    """Give the remaining to commit of a revision from its tasks and its lines, read already.

    ``tasks`` are those of the main structure of the revision (``tasks_for_indicators``), ``lines``
    its lines on them, provisions left out (``lines_for_indicators``): the re-estimated amount of
    each line whose task is not completed, in their order — what ``remaining_of_revision`` gives on
    the same revision, without reading it.
    """
    completed = {task.node_id for task in tasks if task.progress == COMPLETED}
    total, by_line = remaining_sum(
        LineAmount(line.node_id, line.reestimated_amount, line.task_id in completed)
        for line in lines
    )
    return RevisionRemaining(total, by_line)


def _ventilated(
    session: Session,
    project_id: UUID,
    read: RevisionRead,
    placed: Sequence[Placed],
    remaining: RevisionRemaining,
) -> tuple[AmountByKey, ...]:
    """Ventilate the remaining by the nature of cost of the category of each line that counts.

    The nature provision is the provisions of the risks identified, counted whatever the state of
    their task, under the nature of the category each designates (WF-RAE-0010, WF-RAE-0020;
    US-2580/L1). ``placed`` are the lines of the revision on their tasks, read once.
    """
    kept = [each.line for each in placed if each.line.node_id in remaining.by_line]
    natures = natures_of(session, project_id, read, {line.cost_category_id for line in kept})
    amounts: dict[str, Decimal] = {}
    labels: dict[str, str | None] = {}
    for line in kept:
        nature = natures[line.cost_category_id]
        key = str(nature.cost_type_id)
        amounts[key] = amounts.get(key, NOUGHT) + remaining.by_line.get(line.node_id, NOUGHT)
        labels[key] = nature.label
    return distributed(amounts, labels)


def previous_total(session: Session, project_id: UUID, revision_id: UUID) -> Decimal:
    """Give the remaining to commit of the revision marked before, the risks provisions included."""
    return revision_remaining(session, project_id, revision_id, provisions=True)[0]


def remaining_indicators(
    session: Session, project_id: UUID, revision_id: UUID, at: datetime
) -> RemainingIndicators:
    """Give the indicators of the remaining to commit of a revision (``getRemainingIndicators``).

    Computed at ``at``, never stored. The total and its ventilation by nature are the remaining of
    the revision; each subproject — the lines out of any, and the cost imputed to the project
    alone, as ``unassigned`` — compares its budget in the reference with its actual cost and its
    remaining; the margin on the reference is none without one, the difference with the revision
    marked before this one — the offer, when it is the only one — none without one, as the estimate
    reads it. The remaining counts the provisions of the risks identified, whatever the state of the
    task that bears them, the revision marked before it too (WF-RAE-0010; US-2580/L1). A revision
    unknown is 404.
    """
    read = read_revision_for(session, project_id, revision_id)
    # The lines on their tasks, the costliest read: once for the remaining and its ventilation.
    placed = placed_lines(session, project_id, read.revision_id)
    held = RevisionRemaining(*remaining_of_placed(session, placed, provisions=True))
    lines = rows_of(session, project_id, list(held.by_line))
    remainings = summed_by_subproject(lines, held.by_line)
    actual_costs = {
        str(key): amount for key, amount in actual_cost_by_subproject(session, project_id).items()
    }
    budgets = (
        None
        if read.reference_revision_id is None
        else reference_budgets(session, project_id, read.reference_revision_id)
    )
    found = balances(budgets or {}, actual_costs, remainings)
    labels = subproject_labels(
        session, project_id, [UUID(each.key) for each in found if each.key != UNASSIGNED]
    )
    return RemainingIndicators(
        context=CalculationContext(
            read.revision_id, "marked" if read.marked else "draft", at, "project", is_stored=False
        ),
        total=held.total,
        by_cost_type=_ventilated(session, project_id, read, placed, held),
        by_subproject=tuple(
            SubprojectBalance(
                each.key,
                labels.get(UUID(each.key)) if each.key != UNASSIGNED else None,
                each.budget,
                each.actual_cost,
                each.remaining,
                each.variance,
                each.is_over_budget,
                "alert" if each.is_over_budget else "nominal",
            )
            for each in found
        ),
        coverage=risk_coverage(session, project_id, read.revision_id),
        delta_to_reference=delta_to_reference(budgets, actual_costs, remainings),
        delta_to_previous_revision=delta_to_previous(
            held.total,
            None
            if read.previous_marked_id is None
            else revision_remaining(session, project_id, read.previous_marked_id, provisions=True)[
                0
            ],
        ),
    )
