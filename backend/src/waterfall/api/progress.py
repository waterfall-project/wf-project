# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The state of a task (WF-PLA-0130).

``setTaskProgress`` (US-1410): the gesture of a card of the Kanban, served here without a screen.

It is an entry of the remaining to commit (``StructureCommand.edit_remaining``, FBS-4.5.3): read by
whoever may consult the remaining to commit, written by the contributors of the project who may
write it (WF-RAE-0030).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import ProgressUpdate
from waterfall.api.evaluation import RequiresProject
from waterfall.api.nodes import STRUCTURE, Placed, Writing, written_of
from waterfall.core.planning.interface import ProgressEntry, set_task_progress

# The tag of ``setTaskProgress`` in the contract.
router = APIRouter(tags=["remaining"])

CONSULT = "remaining.read"
CHANGE = "remaining.write"


@router.put(
    f"{STRUCTURE}/nodes/{{node_id}}/progress",
    operation_id="setTaskProgress",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=None,
)
def put_progress(
    place: Placed,
    node_id: UUID,
    body: ProgressUpdate,
    writer: Writing,
    session: Transaction,
) -> dict[str, Any]:
    """Start, complete or reopen a task at the counter read, on the day sent or today."""
    entry = ProgressEntry(
        progress=body.progress.value,
        lock_version=body.lock_version.root,
        occurred_on=None if body.occurred_on is None else body.occurred_on.root,
    )
    return written_of(set_task_progress(session, place, node_id, entry, writer))
