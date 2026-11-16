# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit of a project (WF-RAE-0020).

``getRemainingIndicators`` (US-1600), under ``remaining.read``: the revision named, else the
current one, else the last one marked — a marked one as its marking kept it, ``is_stored`` true
(US-1670/L2). The server classifies the overrun of each subproject
(``zone``); the front deduces nothing from the margins.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.api.scopes import kept_document
from waterfall.core.costs.interface import PROJECT
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
    """Give the total of the remaining to commit, its ventilations and its margins at once.

    A marked revision answers the document its marking kept, never computed again; only one marked
    before the indicators were kept, which holds none, is computed at the reading, ``is_stored``
    false.
    """
    read = read_revision_for(session, project_id, revision_id)
    if read.marked:
        # Kept on the project alone: the document carries the balance of each subproject.
        kept = kept_document(session, read.revision_id, "remaining", PROJECT)
        if kept is not None:
            return kept
    found = remaining_indicators(session, project_id, read.revision_id, utc_now())
    return remaining_document(found)
