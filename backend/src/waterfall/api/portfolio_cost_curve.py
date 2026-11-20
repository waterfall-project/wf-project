# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The S-curve of the portfolio (WF-PTF-0100).

``getPortfolioCostCurve`` (US-2740), under ``portfolio_cost_curve.read``. A view of the portfolio is
guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker").

The view takes a period, which chooses the projects Completed and bounds no month of the curve. The
horizon is from 1 to 240 months, six by default; one outside its bounds is refused (422,
``VALUE_OUT_OF_RANGE``, its bounds named), one that is no number as well (``NUMBER_INVALID``), in
the same answer as the state's fault. The twelve months before that of the date always precede it.
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.evaluation import Requires
from waterfall.api.queries import (
    DEFAULT_HORIZON,
    GREATEST_HORIZON,
    DatedQuery,
    horizon_faults,
    portfolio_asked,
)
from waterfall.core.portfolio.interface import PortfolioReading, read_portfolio_cost_curve
from waterfall.platform.database import utc_now

router = APIRouter(tags=["portfolio"])

READ = "portfolio_cost_curve.read"


class PortfolioCostCurveQuery(DatedQuery):
    """What ``getPortfolioCostCurve`` is asked: states, date, period, horizon, payment delays.

    It takes no node: the contract names none, a node restricting only the labour. The horizon is
    read as text and judged by ``horizon_faults``, as the workload's is.
    """

    period_from: Annotated[date | None, Field(alias="from")] = None
    period_to: Annotated[date | None, Field(alias="to")] = None
    horizon_months: Annotated[
        str, Field(json_schema_extra={"minimum": 1, "maximum": GREATEST_HORIZON})
    ] = str(DEFAULT_HORIZON)
    payment_delays: bool = False

    def period(self) -> tuple[date | None, date | None]:
        """Give the period asked, each bound absent when the query leaves it out."""
        return self.period_from, self.period_to


@router.get(
    "/portfolio/cost-curve",
    operation_id="getPortfolioCostCurve",
    dependencies=[Depends(Requires(READ))],
    response_model=None,
)
def get_portfolio_cost_curve(
    query: Annotated[PortfolioCostCurveQuery, Query()], session: Transaction, services: ServicesOf
) -> dict[str, Any]:
    """Give the sum, month by month, of the cumulative cost curves of the projects of the scope."""
    asked = portfolio_asked(query, horizon_faults(query.horizon_months))
    return read_portfolio_cost_curve(
        session,
        asked,
        PortfolioReading(utc_now(), services.indicators_cache),
        horizon_months=int(query.horizon_months),
        payment_delays=query.payment_delays,
    )
