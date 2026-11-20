# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio reads of the estimate of a revision: its totals by nature and by role (EP-11).

The structure of the costs of the portfolio (WF-PTF-0080) sums, by project, the totals of the
reference budget by cost type, provision lines left out, and those of the remaining to commit,
provisions included; and the labour of each, by role of resources. The estimate of an offer stands
for both. Each amount is rounded once, to the cent, as the indicators round it (EP-11, "Ce que le
cadrage décide").

- The reference budget is that of ``budget_revision_id``: the reference of the project, or, for an
  offer, which has none, the revision itself — its estimate. Each line counts its budgeted amount
  (``budgeted_of``, a line of the reference itself its re-estimated one), as the balances of the
  subprojects read it (``reference_budgets``, US-1600); a provision line, none.
- The remaining to commit is that of the revision, provisions included, as its indicators read it
  (``remaining_indicators``, WF-RAE-0010; US-2580/L1): a line of a task not completed counts its
  re-estimated amount, a provision line counts whatever the state of its task.
- The nature of a line is that of its category, on the images a marked revision kept, else on the
  reference as it stands (``natures_of``); the label of each nature with it. The labour is the
  lines that name a role, by that role: the portfolio groups the roles by their current node when
  it reads them (EP-11, "Ce que le cadrage décide"), so no node is kept here.

The amounts of the lines are in cents, and their sums are exact: nothing is rounded again. Neither
writes nor reads the clock.

Declared by US-2670/L1, the socle of EP-11; filled by US-2680/L2.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.indicating import natures_of
from waterfall.core.estimate.placing import placed_lines
from waterfall.core.estimate.reading import budgeted_of, rows_of
from waterfall.core.estimate.remaining.reviewing import provisions_of, remaining_of_placed
from waterfall.core.planning.interface import lines_of_structure
from waterfall.core.revisions.interface import aimed_structure, read_revision_for

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.indicating import Nature
    from waterfall.core.estimate.tables import EstimateLine

# An empty sum, to the cent.
NOUGHT = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class PortfolioTotals:
    """The totals of a revision by cost type, and its labour by role, each an amount.

    ``budget`` leaves the provision lines out; ``remaining`` includes them. ``budget_revision_id``
    is the revision the budget is read on: the reference of the project, or the revision itself
    for an offer. ``cost_type_labels`` names each cost type of either total, as the revisions read
    it. A key without an amount is absent: no total holds a zero it did not sum.
    """

    budget_by_cost_type: Mapping[UUID, Decimal]
    remaining_by_cost_type: Mapping[UUID, Decimal]
    budget_labour_by_role: Mapping[UUID, Decimal]
    remaining_labour_by_role: Mapping[UUID, Decimal]
    budget_revision_id: UUID
    cost_type_labels: Mapping[UUID, str]


def _summed(
    lines: Iterable[tuple[EstimateLine, Decimal]], natures: Mapping[UUID, Nature]
) -> tuple[dict[UUID, Decimal], dict[UUID, Decimal]]:
    """Sum amounts of lines by the nature of their category, and those of the labour by role."""
    by_type: dict[UUID, Decimal] = {}
    by_role: dict[UUID, Decimal] = {}
    for line, amount in lines:
        cost_type = natures[line.cost_category_id].cost_type_id
        by_type[cost_type] = by_type.get(cost_type, NOUGHT) + amount
        if line.resource_role_id is not None:
            role = line.resource_role_id
            by_role[role] = by_role.get(role, NOUGHT) + amount
    return by_type, by_role


def _budget_lines(session: Session, project_id: UUID, revision_id: UUID) -> list[EstimateLine]:
    """Read the lines of the main structure of a revision, provision lines left out."""
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        return []
    lines = rows_of(session, project_id, lines_of_structure(session, project_id, structure_id))
    provisions = provisions_of(session, lines)
    return [line for line in lines if line.node_id not in provisions]


def portfolio_totals(session: Session, project_id: UUID, revision_id: UUID) -> PortfolioTotals:
    """Give the totals by cost type and the labour by role of a revision of a project.

    The budget on the reference of the project, or on the revision itself without one (an offer);
    the remaining on the revision. A revision unknown is refused (404).
    """
    read = read_revision_for(session, project_id, revision_id)
    placed = placed_lines(session, project_id, read.revision_id)
    _, by_line = remaining_of_placed(session, placed, provisions=True)
    remaining = [
        (each.line, by_line[each.line.node_id]) for each in placed if each.line.node_id in by_line
    ]
    natures = natures_of(
        session, project_id, read, {line.cost_category_id for line, _ in remaining}
    )
    budget_id = read.reference_revision_id or read.revision_id
    budget_read = (
        read if budget_id == read.revision_id else read_revision_for(session, project_id, budget_id)
    )
    budgeted = _budget_lines(session, project_id, budget_id)
    budget_natures = natures_of(
        session, project_id, budget_read, {line.cost_category_id for line in budgeted}
    )
    budget_by_type, budget_by_role = _summed(
        ((line, budgeted_of(line)) for line in budgeted), budget_natures
    )
    remaining_by_type, remaining_by_role = _summed(remaining, natures)
    labels = {
        each.cost_type_id: each.label for each in (*budget_natures.values(), *natures.values())
    }
    return PortfolioTotals(
        budget_by_type, remaining_by_type, budget_by_role, remaining_by_role, budget_id, labels
    )
