# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The list of the projects of the portfolio (WF-PTF-0040, WF-PTF-0030).

``getPortfolioProjects`` (US-2690/L2), under ``portfolio_projects.read``. A view of the portfolio is
guarded by the permission of its function alone: neither the quality of contributor nor
``all_projects_read`` enters it (EP-11, "Le service d'API et le worker") — the latter only decides,
for each row, whether the caller opens the project (``can_open``, WF-PTF-0030).

The list is filtered by state, period, zone and a search on the label, and each column by its own
filter, as the tables of the contract are (README, "A column of numbers…", "A period…";
WF-IHM-0130): the code by the text it contains, each column of numbers by its two bounds, the
instant of the last marked revision by its period. Every fault of a bound is named at once (422):
a bound that is no number (``NUMBER_INVALID``), an upper bound lower than the lower
(``VALUE_OUT_OF_RANGE`` on the upper), the end of the period of the marking before its start.
"""

import re
from datetime import UTC
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, Field

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.contract.base import Text
from waterfall.api.contract.models import AlertZone, SortOrder
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.queries import (
    GREATEST_OFFSET,
    PORTFOLIO_READ,
    PortfolioQuery,
    Search,
    portfolio_asked,
    read_list,
)
from waterfall.core.portfolio.interface import (
    Bounds,
    PortfolioListing,
    PortfolioReading,
    read_portfolio_projects,
)
from waterfall.core.projects.interface import Viewer
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError

router = APIRouter(tags=["portfolio"])

DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
NUMBER_INVALID = "NUMBER_INVALID"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# The forms of a bound: an amount, a decimal — a share, an index —, the digits being 0 to 9 as the
# patterns of the contract say them.
MONEY = re.compile(r"-?[0-9]+(\.[0-9]{1,2})?")
DECIMAL = re.compile(r"-?[0-9]+(\.[0-9]+)?")
# The columns of numbers filtered by two bounds, each with the form of its bound.
BOUNDED: dict[str, re.Pattern[str]] = {
    "reference_budget": MONEY,
    "current_estimate": MONEY,
    "win_probability": DECIMAL,
    "project_manager_projection": MONEY,
    "delta_to_reference": MONEY,
    "cost_index": DECIMAL,
    "schedule_index": DECIMAL,
}
type Column = Literal[
    "label",
    "code",
    "state",
    "reference_budget",
    "current_estimate",
    "win_probability",
    "project_manager_projection",
    "delta_to_reference",
    "cost_index",
    "schedule_index",
    "last_marked_at",
]


class ProjectsQuery(PortfolioQuery):
    """What ``getPortfolioProjects`` is asked besides the scope: filters, sort, page.

    The bounds are texts, read here in the form of their column, so that every one at fault is
    named at once; the instants of the period of the marking are read as instants.
    """

    limit: Annotated[int, Field(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT
    offset: Annotated[int, Field(ge=0, le=GREATEST_OFFSET)] = 0
    search: Search = None
    zones: str | None = None
    code: Annotated[Text | None, Field(min_length=1, max_length=50)] = None
    reference_budget_min: str | None = None
    reference_budget_max: str | None = None
    current_estimate_min: str | None = None
    current_estimate_max: str | None = None
    win_probability_min: str | None = None
    win_probability_max: str | None = None
    project_manager_projection_min: str | None = None
    project_manager_projection_max: str | None = None
    delta_to_reference_min: str | None = None
    delta_to_reference_max: str | None = None
    cost_index_min: str | None = None
    cost_index_max: str | None = None
    schedule_index_min: str | None = None
    schedule_index_max: str | None = None
    last_marked_at_from: AwareDatetime | None = None
    last_marked_at_to: AwareDatetime | None = None
    sort_by: Column = "label"
    sort_order: SortOrder = SortOrder.asc


def _bound(text: str | None, form: re.Pattern[str]) -> tuple[Decimal | None, bool]:
    """Read a bound in the form of its column; whether it is at fault is the second answer."""
    if text is None:
        return None, False
    if form.fullmatch(text) is None:
        return None, True
    return Decimal(text), False


def _texts(query: ProjectsQuery, column: str) -> tuple[str | None, str | None]:
    """Give the two texts of the bounds of a column, as the query holds them.

    Each column of ``BOUNDED`` has its two parameters on the query, named after it: a test holds it.
    """
    low: str | None = getattr(query, f"{column}_min")
    high: str | None = getattr(query, f"{column}_max")
    return low, high


def _bounds(query: ProjectsQuery, column: str, faults: list[FieldError]) -> Bounds:
    """Read the two bounds of a column; the faults found are added to ``faults``.

    A bound that is no number is the fault of its parameter; an upper bound lower than the lower,
    the fault of the upper, which names the lower given.
    """
    low_name, high_name = f"{column}_min", f"{column}_max"
    low_text, high_text = _texts(query, column)
    low, low_fault = _bound(low_text, BOUNDED[column])
    high, high_fault = _bound(high_text, BOUNDED[column])
    faults += [
        FieldError(f"/query/{name}", NUMBER_INVALID)
        for name, fault in ((low_name, low_fault), (high_name, high_fault))
        if fault
    ]
    if low is not None and high is not None and high < low:
        faults.append(FieldError(f"/query/{high_name}", VALUE_OUT_OF_RANGE, {"minimum": low_text}))
    return Bounds(low, high)


def listing_of(query: ProjectsQuery, faults: list[FieldError]) -> PortfolioListing:
    """Read what the list is asked besides its scope; the faults of a filter go to ``faults``.

    The caller refuses them all at once, with those of the scope (422): the listing returned is
    to be used only when ``faults`` stays empty.
    """
    bounds = {column: _bounds(query, column, faults) for column in BOUNDED}
    since, until = query.last_marked_at_from, query.last_marked_at_to
    if since is not None and until is not None and until < since:
        faults.append(
            FieldError(
                "/query/last_marked_at_to", VALUE_OUT_OF_RANGE, {"minimum": since.astimezone(UTC)}
            )
        )
    zones, zone_faults = read_list("zones", query.zones, AlertZone)
    faults += zone_faults
    return PortfolioListing(
        limit=query.limit,
        offset=query.offset,
        search=query.search,
        zones=() if zones is None else tuple(zone.value for zone in zones),
        sort_by=query.sort_by,
        descending=query.sort_order is SortOrder.desc,
        code=query.code,
        last_marked_from=since,
        last_marked_before=until,
        **bounds,
    )


@router.get(
    "/portfolio/projects",
    operation_id="getPortfolioProjects",
    dependencies=[Depends(Requires(PORTFOLIO_READ))],
    response_model=None,
)
def get_portfolio_projects(
    query: Annotated[ProjectsQuery, Query()],
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> dict[str, Any]:
    """Give a page of the projects of the portfolio, filtered and sorted by the server.

    A project the caller cannot open is listed under its label and its code, ``can_open`` false.
    The list reads the indicators of the day in the cache of the process, if there is one.
    """
    faults: list[FieldError] = []
    listing = listing_of(query, faults)
    asked = portfolio_asked(query, faults)
    return read_portfolio_projects(
        session,
        asked,
        listing,
        PortfolioReading(utc_now(), services.indicators_cache),
        Viewer(actor.user_id, actor.permissions),
    )
