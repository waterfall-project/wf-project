# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit of a project (WF-RAE-0020).

``getRemainingIndicators`` (US-1600), under ``remaining.read``: the revision named, else the
current one, else the last one marked. The server classifies the overrun of each subproject
(``zone``); the front deduces nothing from the margins.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.core.estimate.interface import remaining_indicators
from waterfall.core.indicators.interface import remaining_document
from waterfall.core.revisions.interface import read_revision_for
from waterfall.platform.database import utc_now

router = APIRouter(tags=["remaining"])

READ = "remaining.read"


@router.get(
    "/projects/{project_id}/remaining-indicators",
    operation_id="getRemainingIndicators",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_remaining_indicators(
    project_id: UUID, session: Transaction, revision_id: Annotated[UUID | None, Query()] = None
) -> dict[str, Any]:
    """Give the total of the remaining to commit, its ventilations and its margins at once."""
    read = read_revision_for(session, project_id, revision_id)
    found = remaining_indicators(session, project_id, read.revision_id, utc_now())
    return remaining_document(found)
