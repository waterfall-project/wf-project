# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The time/time diagram of a project (WF-IND-0090).

``getMilestoneTracking`` (US-1710), under ``project_indicators.read``: for the project alone,
without ``scope``. The instant of the computation is read here, once.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.api.project_indicators import READ
from waterfall.core.indicators.interface import milestone_tracking
from waterfall.platform.database import utc_now

router = APIRouter(tags=["indicators"])


@router.get(
    "/projects/{project_id}/indicators/milestone-tracking",
    operation_id="getMilestoneTracking",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_milestone_tracking(project_id: UUID, session: Transaction) -> dict[str, Any]:
    """Give the forecast finishes of the milestones inscribed in the time/time tracking."""
    return milestone_tracking(session, project_id, utc_now())
