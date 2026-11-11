# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The skeleton of a planning, engendered from the work breakdown (WF-PRJ-0030, WF-PLA-0170).

``generatePlanningSkeleton`` (US-1460): written by the contributors of the project who may write the
planning (``RevisionCommand.generate_skeleton``), on the main structure of the revision the path
names — the operation names no structure —, and answered as every write of the grid is
(``NodesWritten``), the tasks created in ``nodes`` in the order of the plan.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.api.nodes import CHANGE, CONSULT, Writing, written_of
from waterfall.core.planning.interface import Place, generate_skeleton
from waterfall.core.revisions.interface import aimed_structure
from waterfall.platform.errors import NOT_FOUND, NotFoundError

router = APIRouter(tags=["planning"])


@router.post(
    "/projects/{project_id}/revisions/{revision_id}/skeleton",
    operation_id="generatePlanningSkeleton",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    status_code=201,
    response_model=None,
)
def post_skeleton(
    project_id: UUID, revision_id: UUID, writer: Writing, session: Transaction
) -> dict[str, Any]:
    """Generate the skeleton of the planning on the main structure of a revision (404 if none)."""
    structure_id = aimed_structure(session, project_id, revision_id, None)
    if structure_id is None:
        raise NotFoundError(NOT_FOUND)
    place = Place(project_id, revision_id, structure_id)
    return written_of(generate_skeleton(session, place, writer))
