# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hourly rates of the categories of labour (FBS-3.1).

``getHourlyRateGrid``, ``listHourlyRates`` and ``setHourlyRate`` (WF-REF-0050, WF-REF-0060).

The rates are close to the payroll: they are read under the permission to read the cost settings
(``cost_settings.read``, a session without it is told 404, WF-ADM-0110) and set under the one to
change them. The deactivated categories of the grid — ``include_inactive``, ``is_active`` false —
ask for the permission to change, not to read (decision of the author of 2026-11-06, #2084): a
read so asked, without it, is refused by 403 before it reads.
"""

import re
from decimal import Decimal
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.models import (
    HourlyRate,
    HourlyRateGrid,
    HourlyRateWrite,
    PaginationMeta,
    SortOrder,
    Year,
)
from waterfall.api.cost_types import kept_states, page_of
from waterfall.api.evaluation import Requires, RequiresForInactive
from waterfall.api.queries import Search, refuse_query
from waterfall.core.cost_settings.interface import (
    GridColumn,
    HourlyRateFilters,
    HourlyRateSort,
    HourlyRateView,
    Page,
    list_hourly_rates,
    read_hourly_rate_grid,
    set_hourly_rate,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError

router = APIRouter(tags=["reference"])

CONSULTATION = "cost_settings.read"
CHANGE = "cost_settings.write"
NUMBER_INVALID = "NUMBER_INVALID"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
VALUE_REQUIRED = "VALUE_REQUIRED"
# The grid is read under CONSULTATION; its deactivated categories ask for CHANGE besides.
READ_GRID = [Depends(Requires(CONSULTATION)), Depends(RequiresForInactive(CHANGE))]
READ = [Depends(Requires(CONSULTATION))]
WRITE = [Depends(Requires(CHANGE))]
# A money as the contract writes it (``Money``): at most two decimals; no more digits than a rate.
MONEY = re.compile(r"-?\d{1,20}(\.\d{1,2})?")

type SortBy = Annotated[str, Query(pattern=r"^(code|label|is_active|rate\.(20[0-9]{2}|2100))$")]


def hourly_rate(view: HourlyRateView) -> HourlyRate:
    """Describe a rate as the contract does."""
    return HourlyRate.model_validate(
        {
            "cost_category_id": view.cost_category_id,
            "year": view.year,
            "amount": f"{view.amount:.2f}",
            "audit": {
                "created_at": view.audit.created_at,
                "created_by": actor_ref(view.audit.created_by),
                "updated_at": view.audit.updated_at,
                "updated_by": actor_ref(view.audit.updated_by),
            },
            "lock_version": view.audit.lock_version,
        }
    )


def grid_sort(sort_by: SortBy = "code", sort_order: SortOrder = SortOrder.asc) -> HourlyRateSort:
    """Read the sort the grid asks for: a column, or the rate of a year (``rate.2026``)."""
    descending = sort_order is SortOrder.desc
    if sort_by.startswith("rate."):
        return HourlyRateSort("rate", int(sort_by.removeprefix("rate.")), descending)
    return HourlyRateSort(cast("GridColumn", sort_by), None, descending=descending)


def _bound(name: str, text: str | None) -> tuple[Decimal | None, FieldError | None]:
    """Read a bound as a money (``NUMBER_INVALID`` at the parameter if it is none)."""
    if text is None:
        return None, None
    if MONEY.fullmatch(text) is None:
        return None, FieldError(f"/query/{name}", NUMBER_INVALID)
    return Decimal(text), None


def grid_filters(
    states: Annotated[frozenset[bool], Depends(kept_states)],
    search: Search = None,
    rate_year: Annotated[int, Query(ge=2000, le=2100)] | None = None,
    rate_min: Annotated[str, Query()] | None = None,
    rate_max: Annotated[str, Query()] | None = None,
) -> HourlyRateFilters:
    """Read the filters of the grid; a bound malformed, inverted or without its year is refused.

    All the faults are named at once (422): a bound that is no money (``NUMBER_INVALID``), the
    upper bound under the lower one (``VALUE_OUT_OF_RANGE``, the lower one its minimum), a bound
    without the year it bounds (``VALUE_REQUIRED`` at ``rate_year``).
    """
    low, low_fault = _bound("rate_min", rate_min)
    high, high_fault = _bound("rate_max", rate_max)
    faults = [fault for fault in (low_fault, high_fault) if fault is not None]
    if low is not None and high is not None and high < low:
        faults.append(FieldError("/query/rate_max", VALUE_OUT_OF_RANGE, {"minimum": rate_min}))
    if rate_year is None and (rate_min is not None or rate_max is not None):
        faults.append(FieldError("/query/rate_year", VALUE_REQUIRED))
    refuse_query(faults)
    return HourlyRateFilters(search, states, rate_year, low, high)


@router.get(
    "/reference/hourly-rates",
    operation_id="getHourlyRateGrid",
    dependencies=READ_GRID,
    response_model=None,
)
def get_hourly_rate_grid(
    session: Transaction,
    filters: Annotated[HourlyRateFilters, Depends(grid_filters)],
    sort: Annotated[HourlyRateSort, Depends(grid_sort)],
    page: Annotated[Page, Depends(page_of)],
) -> dict[str, object]:
    """Give a page of the grid, a row per category of labour, a column per year (WF-REF-0050)."""
    read = read_hourly_rate_grid(session, filters, sort, page)
    grid = HourlyRateGrid.model_validate(
        {
            "years": [Year(read_year) for read_year in read.years],
            "rows": [
                {
                    "cost_category_id": row.cost_category_id,
                    "code": row.code,
                    "label": row.label,
                    "is_active": row.is_active,
                    "cells": [None if cell is None else hourly_rate(cell) for cell in row.cells],
                }
                for row in read.rows
            ],
            "meta": PaginationMeta(limit=page.limit, offset=page.offset, total=read.total),
        }
    )
    return grid.model_dump(mode="json", exclude_unset=True)


@router.get(
    "/reference/cost-categories/{cost_category_id}/hourly-rates",
    operation_id="listHourlyRates",
    dependencies=READ,
    response_model_exclude_unset=True,
)
def get_hourly_rates(cost_category_id: UUID, session: Transaction) -> list[HourlyRate]:
    """Give the rates of a category, one per year, the oldest first (WF-REF-0050)."""
    return [hourly_rate(view) for view in list_hourly_rates(session, cost_category_id)]


@router.put(
    "/reference/cost-categories/{cost_category_id}/hourly-rates/{year}",
    operation_id="setHourlyRate",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_hourly_rate(
    cost_category_id: UUID,
    year: Annotated[int, Path(ge=2000, le=2100)],
    body: HourlyRateWrite,
    account: Caller,
    session: Transaction,
) -> HourlyRate:
    """Set the rate of a year once, without a version; correct it with the version read."""
    version = None if body.lock_version is None else body.lock_version.root
    act = Act(account.user_id, utc_now())
    amount = Decimal(body.amount.root)
    return hourly_rate(set_hourly_rate(session, (cost_category_id, year), amount, version, act))
