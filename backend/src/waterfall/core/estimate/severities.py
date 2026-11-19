# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the risks read of the estimate, private to the module (EP-08, US-2570/L1).

The total of an own estimate, the severity of its risk (``structure_amount``, WF-RIS-0010), and the
base of the project the matrix relates a severity to (``risk_base``, WF-REF-0160).
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.provisioning import NOUGHT
from waterfall.core.estimate.reading import budgeted_of, rows_of
from waterfall.core.estimate.remaining.reviewing import provisions_of
from waterfall.core.planning.interface import lines_of_structure, lines_of_structures
from waterfall.core.projects.interface import project_facts
from waterfall.core.revisions.interface import aimed_structure

if TYPE_CHECKING:
    from collections.abc import Collection
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session


def structure_amount(session: Session, project_id: UUID, structure_id: UUID) -> Decimal:
    """Give the total of a structure: the sum of the re-estimated amounts of its lines.

    The severity of a risk, the total of its own estimate (WF-RIS-0010), which has no remaining to
    commit: the re-estimated amount of each of its lines is its amount, inflation included.
    """
    session.flush()
    lines = rows_of(session, project_id, lines_of_structure(session, project_id, structure_id))
    return sum((line.reestimated_amount for line in lines), NOUGHT)


def structure_amounts(
    session: Session, project_id: UUID, structure_ids: Collection[UUID]
) -> dict[UUID, Decimal]:
    """Give the total of each structure named, as ``structure_amount`` does, in few statements.

    The same number of statements whatever the number of structures: a register of risks reads the
    own estimate of each of them at once.
    """
    session.flush()
    held = lines_of_structures(session, project_id, structure_ids)
    rows = rows_of(session, project_id, [node for nodes in held.values() for node in nodes])
    amounts = {row.node_id: row.reestimated_amount for row in rows}
    return {
        structure_id: sum((amounts[node] for node in nodes if node in amounts), NOUGHT)
        for structure_id, nodes in held.items()
    }


def risk_base(session: Session, project_id: UUID, revision_id: UUID) -> Decimal:
    """Give the base the severity of a risk is related to, in the matrix (WF-REF-0160).

    The budget of the reference of the project, the budgeted amounts of the lines of its main
    structure, provisions left out; before a reference, the total of the main structure of the
    revision read, provisions left out.
    """
    reference = project_facts(session, project_id).reference_revision_id
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
