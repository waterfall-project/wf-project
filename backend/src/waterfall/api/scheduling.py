# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The predecessors of a task and the date the planning of a structure starts on.

``setPredecessors`` and ``updateCostStructure`` (US-1390/L2): writes of the planning, made by the
contributors of the project who may write it (``StructureCommand.edit_planning``), each answered
as every write of the grid is (``NodesWritten``). A modification of the structure sends one field
at least beside its counter, none of them null.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import PredecessorsReplace, StructureUpdate
from waterfall.api.evaluation import RequiresProject
from waterfall.api.nodes import STRUCTURE, Placed, Writing, written_of
from waterfall.core.planning.interface import (
    PredecessorSent,
    PredecessorsEntry,
    StructureChange,
    set_predecessors,
    update_cost_structure,
)
from waterfall.platform.errors import FieldError, UnprocessableError

CONSULT = "planning.read"
CHANGE = "planning.write"
VALIDATION_FAILED = "VALIDATION_FAILED"

# Each route its tag, as the contract has them: ``planning`` for ``setPredecessors``, ``revisions``
# for ``updateCostStructure``.
router = APIRouter()


@router.put(
    f"{STRUCTURE}/nodes/{{node_id}}/predecessors",
    operation_id="setPredecessors",
    tags=["planning"],
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def put_predecessors(
    place: Placed,
    node_id: UUID,
    body: PredecessorsReplace,
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Replace the predecessors of a task at the counter read, each with its type and its lag."""
    entry = PredecessorsEntry(
        tuple(
            PredecessorSent(
                each.predecessor_node_id.root,
                each.link_type.value,
                Decimal(each.lag.value.root),
                each.lag.unit.value,
            )
            for each in body.predecessors
        ),
        body.lock_version.root,
    )
    return written_of(set_predecessors(session, place, node_id, entry, writer))


@router.patch(
    STRUCTURE,
    operation_id="updateCostStructure",
    tags=["revisions"],
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def patch_structure(
    place: Placed,
    body: StructureUpdate,
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Write what is sent of the start and the label of a structure, at the counter read."""
    sent = body.model_fields_set - {"lock_version"}
    faults = [
        FieldError(f"/{name}", VALIDATION_FAILED)
        for name in ("planning_start_on", "label")
        if name in sent and getattr(body, name) is None
    ]
    # A modification sends one field at least beside its counter (``minProperties``).
    if faults or not sent:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    start = None if body.planning_start_on is None else body.planning_start_on.root
    change = StructureChange(start, body.label, body.lock_version.root)
    return written_of(update_cost_structure(session, place, change, writer))
