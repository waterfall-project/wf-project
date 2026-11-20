# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks of the portfolio and their coverage (WF-PTF-0090).

``getPortfolioRisks`` (US-2730), under ``portfolio_risks.read``. A view of the portfolio is guarded
by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker") — the latter only decides,
for each risk, whether the caller opens its project (``can_open``, WF-PTF-0030).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.queries import NodelessQuery, portfolio_asked
from waterfall.core.portfolio.interface import PortfolioReading, read_portfolio_risks
from waterfall.core.projects.interface import Viewer
from waterfall.platform.database import utc_now

router = APIRouter(tags=["portfolio"])

READ = "portfolio_risks.read"


@router.get(
    "/portfolio/risks",
    operation_id="getPortfolioRisks",
    dependencies=[Depends(Requires(READ))],
    response_model=None,
)
def get_portfolio_risks(
    query: Annotated[NodelessQuery, Query()],
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> dict[str, Any]:
    """Give the identified provisions, the heaviest risks, the matrix, the coverage, the outcomes.

    A risk of a project the caller cannot open is named with its project, ``can_open`` false.
    """
    return read_portfolio_risks(
        session,
        portfolio_asked(query),
        PortfolioReading(utc_now(), services.indicators_cache),
        Viewer(actor.user_id, actor.permissions),
    )
