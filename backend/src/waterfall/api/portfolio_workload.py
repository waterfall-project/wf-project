# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of the portfolio, by role and by month (WF-PTF-0060).

``getPortfolioWorkload`` (US-2700), under ``portfolio_workload.read``. A view of the portfolio is
guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker").

The view takes no period: a ``from`` or a ``to`` sent is not read. The horizon is from 1 to 240
months, six by default, and the threshold of under-load a ratio from 0 to 1, half by default; one
outside its bounds is refused (422, ``VALUE_OUT_OF_RANGE``, its bounds named), with the state's if
it is at fault, and the answer always gives the threshold retained.
"""

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.evaluation import Requires
from waterfall.api.queries import ScopeQuery, portfolio_asked
from waterfall.core.portfolio.interface import PortfolioReading, read_portfolio_workload
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError

router = APIRouter(tags=["portfolio"])

READ = "portfolio_workload.read"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
DEFAULT_HORIZON = 6
GREATEST_HORIZON = 240
DEFAULT_THRESHOLD = "0.5"
# The form of a decimal, as the contract writes it (``Decimal``).
DECIMAL = r"^-?\d+(\.\d+)?$"


class WorkloadQuery(ScopeQuery):
    """What ``getPortfolioWorkload`` is asked besides the scope: its horizon and its threshold.

    The view takes no period. The bounds of the horizon are declared as the contract writes them
    and judged by ``view_faults`` — not by the model, whose refusal would name the bound crossed
    alone —, so that a refusal names both, as the contract's example does, with the state's in one
    answer; the threshold is a decimal, read as text and refused beyond its bounds as well.
    """

    horizon_months: Annotated[
        int, Field(json_schema_extra={"minimum": 1, "maximum": GREATEST_HORIZON})
    ] = DEFAULT_HORIZON
    under_load_threshold: Annotated[str, Field(pattern=DECIMAL)] = DEFAULT_THRESHOLD


def view_faults(query: WorkloadQuery) -> list[FieldError]:
    """Name the horizon and the threshold that are out of their bounds, each with its bounds."""
    faults: list[FieldError] = []
    if not 1 <= query.horizon_months <= GREATEST_HORIZON:
        bounds = {"minimum": 1, "maximum": GREATEST_HORIZON}
        faults.append(FieldError("/query/horizon_months", VALUE_OUT_OF_RANGE, bounds))
    if not 0 <= Decimal(query.under_load_threshold) <= 1:
        bounds = {"minimum": 0, "maximum": 1}
        faults.append(FieldError("/query/under_load_threshold", VALUE_OUT_OF_RANGE, bounds))
    return faults


@router.get(
    "/portfolio/workload",
    operation_id="getPortfolioWorkload",
    dependencies=[Depends(Requires(READ))],
    response_model=None,
)
def get_portfolio_workload(
    query: Annotated[WorkloadQuery, Query()], session: Transaction, services: ServicesOf
) -> dict[str, Any]:
    """Give the load of the projects by role and by month, against the capacity of each role."""
    asked = portfolio_asked(query, view_faults(query))
    return read_portfolio_workload(
        session,
        asked,
        PortfolioReading(utc_now(), services.indicators_cache),
        horizon_months=query.horizon_months,
        under_load_threshold=Decimal(query.under_load_threshold),
    )
