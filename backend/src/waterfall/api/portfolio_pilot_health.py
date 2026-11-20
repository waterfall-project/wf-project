# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The health of the control of the projects (WF-PTF-0110).

``getPortfolioPilotHealth`` (US-2750), under ``portfolio_pilot_health.read``. A view of the
portfolio is guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker").

The view retains the projects In progress alone, takes no period and, as the contract writes it, no
node: an ``org_node_id`` sent is not read. A signal says whether the caller opens its project
(``can_open``), as the list does.
"""

from dataclasses import replace
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.queries import ScopeQuery, portfolio_asked
from waterfall.core.portfolio.interface import PortfolioReading, read_pilot_health
from waterfall.core.projects.interface import Viewer
from waterfall.platform.database import utc_now

router = APIRouter(tags=["portfolio"])

READ = "portfolio_pilot_health.read"


@router.get(
    "/portfolio/pilot-health",
    operation_id="getPortfolioPilotHealth",
    dependencies=[Depends(Requires(READ))],
    response_model=None,
)
def get_portfolio_pilot_health(
    query: Annotated[ScopeQuery, Query()],
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> dict[str, Any]:
    """Give the signals of the control of the projects In progress, by project."""
    asked = replace(portfolio_asked(query), org_node_id=None)
    return read_pilot_health(
        session,
        asked,
        PortfolioReading(utc_now(), services.indicators_cache),
        Viewer(actor.user_id, actor.permissions),
    )
