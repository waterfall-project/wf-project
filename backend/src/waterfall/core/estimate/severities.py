# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks read of the estimate, private to the module (EP-08, US-2570/L1).

The gap of the totals of the own estimate of a risk and of its base, the severity of its risk
(``own_estimate_gap``, WF-RIS-0010; EP-30, US-3070/L3); and the base of the project the matrix
relates a severity to (``risk_base``, WF-REF-0160).
"""

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.estimate.provisioning import NOUGHT
from waterfall.core.estimate.reading import budgeted_of, rows_of
from waterfall.core.estimate.remaining.reviewing import provisions_of
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import line_nodes_of, lines_of_structure
from waterfall.core.projects.interface import project_facts
from waterfall.core.revisions.interface import (
    aimed_structure,
    differential_base,
    reference_at_marking,
)

if TYPE_CHECKING:
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session


def own_estimate_gap(session: Session, project_id: UUID, structure_id: UUID) -> Decimal | None:
    """Give the gap of the totals of an own estimate whole and of its base; none without a base.

    The severity of its risk, signed (EP-30, "La gravité et la provision"): the re-estimated amount
    of the project with the risk, the main structure as the own estimate carries it, less that of
    the project without it, its base; neither holds a provision line. An own estimate without a
    base — pruned, or consumed and taken up empty — has none to give.
    """
    base_id = differential_base(session, project_id, structure_id)
    if base_id is None:
        return None
    session.flush()
    held = line_nodes_of(project_id, (structure_id, base_id))
    # The two totals in one statement: the two structures hold the project twice over.
    rows = session.execute(
        select(held.c.structure_id, func.sum(EstimateLine.reestimated_amount))
        .join(EstimateLine, EstimateLine.node_id == held.c.node_id)
        .where(EstimateLine.project_id == project_id)
        .group_by(held.c.structure_id)
    )
    totals: dict[UUID, Decimal] = dict(rows.all())
    return totals.get(structure_id, NOUGHT) - totals.get(base_id, NOUGHT)


def risk_base(session: Session, project_id: UUID, revision_id: UUID) -> Decimal:
    """Give the base the severity of a risk is related to, in the matrix (WF-REF-0160).

    The budget of the reference of the project, the budgeted amounts of the lines of its main
    structure, provisions left out; before a reference, the total of the main structure of the
    revision read, provisions left out. A revision a merge marks and designates at once is the
    reference from that instant (``designated_at_marking``): what its marking keeps is related to
    its own budget (US-2680/L3).
    """
    reference = reference_at_marking(
        session, revision_id, project_facts(session, project_id).reference_revision_id
    )
    read = revision_id if reference is None else reference
    structure_id = aimed_structure(session, project_id, read, None)
    if structure_id is None:
        return NOUGHT
    lines = rows_of(session, project_id, lines_of_structure(session, project_id, structure_id))
    provisions = provisions_of(session, lines)
    kept = [line for line in lines if line.node_id not in provisions]
    if reference is None:
        return sum((line.reestimated_amount for line in kept), NOUGHT)
    return sum((budgeted_of(line) for line in kept), NOUGHT)
