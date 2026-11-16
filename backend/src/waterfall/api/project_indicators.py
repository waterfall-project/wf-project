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

The indicators of the current day are read in the cache of the process (``Source``, the transaction
of the request with it; US-1720/L2), shared with the curves and the evolution of the indices.
"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.api.scopes import scope_of
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.interface import IndicatorsReading, project_indicators
from waterfall.platform.cache import IndicatorsCache
from waterfall.platform.database import utc_now

router = APIRouter(tags=["indicators"])

READ = "project_indicators.read"


@dataclass(frozen=True, slots=True)
class IndicatorsSource:
    """What a reading of the indicators reads: the transaction of the request, and the cache.

    The cache is that of the indicators of the day of the process, none for a process that
    computes them at each reading (US-1720/L2); a marked revision is never read in it.
    """

    session: Session
    cache: IndicatorsCache | None


def indicators_source(session: Transaction, services: ServicesOf) -> IndicatorsSource:
    """Give the transaction of the request and the cache of the indicators of the process."""
    return IndicatorsSource(session, services.indicators_cache)


Source = Annotated[IndicatorsSource, Depends(indicators_source)]


@router.get(
    "/projects/{project_id}/indicators",
    operation_id="getProjectIndicators",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_project_indicators(
    project_id: UUID,
    source: Source,
    revision_id: Annotated[UUID | None, Query()] = None,
    as_of: Annotated[date | None, Query()] = None,
    scope: Annotated[str, Query()] = PROJECT,
) -> dict[str, Any]:
    """Give the indicators of a project on a scope, on the current day."""
    asked = IndicatorsReading(scope_of(scope), utc_now(), revision_id, as_of)
    return project_indicators(source.session, project_id, asked, source.cache)
