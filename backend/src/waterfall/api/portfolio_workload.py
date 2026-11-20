# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of the portfolio, by role and by month (WF-PTF-0060).

``getPortfolioWorkload`` (US-2700), under ``portfolio_workload.read``. A view of the portfolio is
guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker").

The view takes no period: a ``from`` or a ``to`` sent is not read. The horizon is from 1 to 240
months, six by default, and the threshold of under-load a ratio from 0 to 1, half by default; one
outside its bounds is refused (422, ``VALUE_OUT_OF_RANGE``, its bounds named), with the state's if
it is at fault, and the answer always gives the threshold retained. A horizon or a threshold that
is no number is refused as well (``NUMBER_INVALID``), in the same answer as the other's fault. The
roles come by label, then by identifier.
"""

import re
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
NUMBER_INVALID = "NUMBER_INVALID"
# The forms of an integer and of a decimal, as the contract writes them (``Decimal``).
INTEGER = re.compile(r"-?\d+")
DECIMAL = re.compile(r"-?\d+(\.\d+)?")


class WorkloadQuery(ScopeQuery):
    """What ``getPortfolioWorkload`` is asked besides the scope: its horizon and its threshold.

    The view takes no period. The bounds of the horizon are declared as the contract writes them
    and judged by ``view_faults`` — not by the model, whose refusal would name the bound crossed
    alone —, so that a refusal names both, as the contract's example does, with the state's in one
    answer; the horizon and the threshold are read as text, so that one that is no number is
    judged there too, as the bounds of the lists are (``_bound``).
    """

    horizon_months: Annotated[
        str, Field(json_schema_extra={"minimum": 1, "maximum": GREATEST_HORIZON})
    ] = str(DEFAULT_HORIZON)
    under_load_threshold: str = DEFAULT_THRESHOLD


def horizon_faults(text: str) -> list[FieldError]:
    """Name the horizon that is malformed or out of its bounds, as every view that takes one does.

    A malformed one is ``NUMBER_INVALID``; one outside its bounds is ``VALUE_OUT_OF_RANGE`` with
    them (the S-curve, ``getPortfolioCostCurve``, judges its own the same way).
    """
    if INTEGER.fullmatch(text) is None:
        return [FieldError("/query/horizon_months", NUMBER_INVALID)]
    if not 1 <= int(text) <= GREATEST_HORIZON:
        bounds = {"minimum": 1, "maximum": GREATEST_HORIZON}
        return [FieldError("/query/horizon_months", VALUE_OUT_OF_RANGE, bounds)]
    return []


def view_faults(query: WorkloadQuery) -> list[FieldError]:
    """Name the horizon and the threshold that are malformed or out of their bounds.

    A malformed one is ``NUMBER_INVALID``; one outside its bounds is ``VALUE_OUT_OF_RANGE`` with
    its bounds. Both are judged, so that every fault of the view comes in one answer.
    """
    faults = horizon_faults(query.horizon_months)
    if DECIMAL.fullmatch(query.under_load_threshold) is None:
        faults.append(FieldError("/query/under_load_threshold", NUMBER_INVALID))
    elif not 0 <= Decimal(query.under_load_threshold) <= 1:
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
        horizon_months=int(query.horizon_months),
        under_load_threshold=Decimal(query.under_load_threshold),
    )
