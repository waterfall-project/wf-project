# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio is worth: order book, pipeline, delivered (WF-PTF-0050).

``getPortfolioValue`` (US-2690/L2), under ``portfolio_projects.read``, the permission of the list
(FBS-2.1). A view of the portfolio is guarded by the permission of its function alone: neither the
quality of contributor nor ``all_projects_read`` enters it (EP-11, "Le service d'API et le worker").
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.evaluation import Requires
from waterfall.api.queries import PORTFOLIO_READ, PortfolioQuery, portfolio_asked
from waterfall.core.portfolio.interface import PortfolioReading, read_portfolio_value
from waterfall.platform.database import utc_now

router = APIRouter(tags=["portfolio"])


@router.get(
    "/portfolio/value",
    operation_id="getPortfolioValue",
    dependencies=[Depends(Requires(PORTFOLIO_READ))],
    response_model=None,
)
def get_portfolio_value(
    query: Annotated[PortfolioQuery, Query()], session: Transaction, services: ServicesOf
) -> dict[str, Any]:
    """Give the order book, the pipeline, the delivered and the conversion rate of the scope."""
    asked = portfolio_asked(query)
    return read_portfolio_value(
        session, asked, PortfolioReading(utc_now(), services.indicators_cache)
    )
