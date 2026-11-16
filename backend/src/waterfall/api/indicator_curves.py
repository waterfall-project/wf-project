# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of a project: the cumulative costs and the earned value (WF-IND-0100, WF-IND-0110).

``getCostCurve`` and ``getEarnedValueCurves`` (US-1690/L2: the current day; US-1690/L3: a marked
revision), under ``project_indicators.read``. The instant of the computation is read here, once;
the scope and the refusals are those of ``getProjectIndicators``, which this module reads the
scope of (``scope_of``); the curves of the current day are read in the cache of the process, as
the indicators are (``Source``, US-1720/L2).
"""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from waterfall.api.evaluation import RequiresProject
from waterfall.api.project_indicators import READ, Source
from waterfall.api.scopes import scope_of
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.interface import IndicatorsReading, cost_curve, earned_value_curves
from waterfall.platform.database import utc_now

router = APIRouter(tags=["indicators"])


class CostCurveQuery(BaseModel):
    """What ``getCostCurve`` asks: the revision or the date, the scope, the payment delays."""

    revision_id: UUID | None = None
    as_of: date | None = None
    scope: str = PROJECT
    payment_delays: bool = False


@router.get(
    "/projects/{project_id}/indicators/cost-curve",
    operation_id="getCostCurve",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_cost_curve(
    project_id: UUID, source: Source, query: Annotated[CostCurveQuery, Query()]
) -> dict[str, Any]:
    """Give the cumulative costs of a project on a scope, on the current day."""
    asked = IndicatorsReading(scope_of(query.scope), utc_now(), query.revision_id, query.as_of)
    delays = query.payment_delays
    return cost_curve(source.session, project_id, asked, payment_delays=delays, cache=source.cache)


@router.get(
    "/projects/{project_id}/indicators/earned-value-curves",
    operation_id="getEarnedValueCurves",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_earned_value_curves(
    project_id: UUID,
    source: Source,
    revision_id: Annotated[UUID | None, Query()] = None,
    as_of: Annotated[date | None, Query()] = None,
    scope: Annotated[str, Query()] = PROJECT,
) -> dict[str, Any]:
    """Give the planned value, the earned value and the actual cost of a project on a scope."""
    asked = IndicatorsReading(scope_of(scope), utc_now(), revision_id, as_of)
    return earned_value_curves(source.session, project_id, asked, source.cache)
