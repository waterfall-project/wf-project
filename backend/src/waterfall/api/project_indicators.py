# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The earned value indicators of a project (WF-IND-0010 to WF-IND-0080).

``getProjectIndicators`` (US-1660/L3: the current day; US-1670/L2: a marked revision named, a
date), under ``project_indicators.read``. The instant of the computation is read here, once, and
its day is that of the time zone of the installation; the server classifies the zone of each index
on the thresholds of the reference data, the front deduces nothing.

The scope is read (``waterfall.api.scopes``) as the contract writes it: ``project``,
``unassigned``, or the identifier of a subproject. A text that is none of them is read as the nil
identifier, which no subproject bears: the indicators refuse it as unknown
(``UNKNOWN_SUBPROJECT``), after the state of the project, in the order of the contract, as a
subproject the project does not have.
"""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.api.scopes import scope_of
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.interface import IndicatorsReading, project_indicators
from waterfall.platform.database import utc_now

router = APIRouter(tags=["indicators"])

READ = "project_indicators.read"


@router.get(
    "/projects/{project_id}/indicators",
    operation_id="getProjectIndicators",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_project_indicators(
    project_id: UUID,
    session: Transaction,
    revision_id: Annotated[UUID | None, Query()] = None,
    as_of: Annotated[date | None, Query()] = None,
    scope: Annotated[str, Query()] = PROJECT,
) -> dict[str, Any]:
    """Give the indicators of a project on a scope, on the current day."""
    asked = IndicatorsReading(scope_of(scope), utc_now(), revision_id, as_of)
    return project_indicators(session, project_id, asked)
