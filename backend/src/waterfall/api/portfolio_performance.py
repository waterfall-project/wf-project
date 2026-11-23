# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The performance of the portfolio: indices, projections, quarters (WF-PTF-0070).

``getPortfolioPerformance`` (US-2710), under ``portfolio_performance.read``. A view of the portfolio
is guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker"). The states are separated
by commas (``explode: false``), a state unknown refused at ``/query/states`` (422); the period and
the node are judged by the scope, with the same refusals as every view. The indicators of the day
are read in the cache of the process, as those of a project are (``Source``).

Registered by the application, served by US-2710 (declared empty by US-2670/L1).
"""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.evaluation import Requires
from waterfall.api.project_indicators import Source
from waterfall.api.queries import listed
from waterfall.core.portfolio.interface import (
    PortfolioAsked,
    PortfolioReading,
    read_portfolio_performance,
)
from waterfall.core.projects.interface import ProjectState
from waterfall.platform.database import utc_now

router = APIRouter(tags=["portfolio"])

READ = "portfolio_performance.read"


def _state(text: str) -> ProjectState:
    """Read a state of the query; a text that is none is a fault of the parameter."""
    match text:
        case "created" | "pricing" | "in_progress" | "completed" | "lost" | "abandoned" as state:
            return state
        case _:
            message = f"unknown state: {text}"
            raise ValueError(message)


def portfolio_asked(
    states: Annotated[str | None, Query()] = None,
    period_from: Annotated[date | None, Query(alias="from")] = None,
    period_to: Annotated[date | None, Query(alias="to")] = None,
    as_of: Annotated[date | None, Query()] = None,
    org_node_id: Annotated[UUID | None, Query()] = None,
) -> PortfolioAsked:
    """Read what a view of the portfolio is asked, as the query of the contract says it."""
    named = listed("states", states, _state)
    return PortfolioAsked(
        states=() if named is None else named,
        period_from=period_from,
        period_to=period_to,
        as_of=as_of,
        org_node_id=org_node_id,
    )


@router.get(
    "/portfolio/performance",
    operation_id="getPortfolioPerformance",
    dependencies=[Depends(Requires(READ))],
    response_model=None,
)
def get_portfolio_performance(
    source: Source, asked: Annotated[PortfolioAsked, Depends(portfolio_asked)]
) -> dict[str, Any]:
    """Give the indices, the projections, the zones and the quarters of the projects In progress."""
    reading = PortfolioReading(utc_now(), source.cache)
    return read_portfolio_performance(source.session, asked, reading)
