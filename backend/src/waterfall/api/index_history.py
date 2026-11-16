# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evolution of the indices of a project (WF-IND-0130).

``getIndexHistory`` (US-1700), under ``project_indicators.read``: every scope, or the one asked
for by ``scope``, read as ``getProjectIndicators`` reads it. The instant of the computation is read
here, once; the point of the day is read in the cache of the process, as the indicators are
(``Source``, US-1720/L2).
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.evaluation import RequiresProject
from waterfall.api.project_indicators import READ, Source, scope_of
from waterfall.core.indicators.interface import index_history
from waterfall.platform.database import utc_now

router = APIRouter(tags=["indicators"])


@router.get(
    "/projects/{project_id}/indicators/index-history",
    operation_id="getIndexHistory",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_index_history(
    project_id: UUID, source: Source, scope: Annotated[str | None, Query()] = None
) -> dict[str, Any]:
    """Give the evolution of the cost index and of the schedule index, by scope."""
    asked = None if scope is None else scope_of(scope)
    return index_history(source.session, project_id, asked, utc_now(), source.cache)
