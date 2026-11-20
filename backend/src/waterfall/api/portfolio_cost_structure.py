# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of the costs of the portfolio (WF-PTF-0080).

``getPortfolioCostStructure`` (US-2720), under ``portfolio_cost_structure.read``. A view of the
portfolio is guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker").

The view takes a period, whose completed projects contribute, and a node, which restricts the
labour by node alone.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.evaluation import Requires
from waterfall.api.queries import PortfolioQuery, portfolio_asked
from waterfall.core.portfolio.interface import PortfolioReading, read_portfolio_cost_structure
from waterfall.platform.database import utc_now

router = APIRouter(tags=["portfolio"])

READ = "portfolio_cost_structure.read"


@router.get(
    "/portfolio/cost-structure",
    operation_id="getPortfolioCostStructure",
    dependencies=[Depends(Requires(READ))],
    response_model=None,
)
def get_portfolio_cost_structure(
    query: Annotated[PortfolioQuery, Query()], session: Transaction, services: ServicesOf
) -> dict[str, Any]:
    """Give the budget and the remaining to commit by cost type, and the labour by node."""
    return read_portfolio_cost_structure(
        session,
        portfolio_asked(query),
        PortfolioReading(utc_now(), services.indicators_cache),
    )
