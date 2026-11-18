# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The register and the matrix of the risks of a project (WF-RIS-0040).

``listRisks`` (US-2600/L1) and ``getProjectRiskMatrix`` (US-2600/L2), under ``risks.read``.

The register is read in a revision (``revision_id``), filtered on each of its columns — the state
and the zone by a list, the label by the search, each column of numbers by its two bounds, the day
of the last review by its period — sorted, paginated, and given with the totals of the risks the
filters retain, not of the page (WF-IHM-0130, #1367; H-01, #1785). Every fault of a filter is named
at once (422): a bound that is no number, a day that is none, an upper bound under the lower one.

Registered by the application, empty until US-2600 serves it (US-2550/L1).
"""

import re
from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import AlertZone, PaginationMeta, SortOrder
from waterfall.api.cost_types import page_of
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import viewer_of
from waterfall.api.queries import Search, read_list, refuse_query
from waterfall.api.risks import authors_of, described
from waterfall.core.cost_settings.interface import Page
from waterfall.core.risks.interface import (
    Bounds,
    RiskColumn,
    RiskFilters,
    RiskPage,
    RiskSort,
    RiskState,
    list_risks,
)
from waterfall.platform.errors import FieldError

router = APIRouter(tags=["risks"])

CONSULT = "risks.read"
NUMBER_INVALID = "NUMBER_INVALID"
DATE_INVALID = "DATE_INVALID"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# The forms of a bound, as the patterns of the contract say them (``Percent``, ``Money``,
# ``PlanningDate``): their digits are 0 to 9, another digit malforms the bound.
DECIMAL = re.compile(r"-?[0-9]+(\.[0-9]+)?")
MONEY = re.compile(r"-?[0-9]+(\.[0-9]{1,2})?")
DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class RegisterQuery(BaseModel):
    """The parameters of ``listRisks`` the service reads typed; the lists and bounds are text."""

    revision_id: UUID | None = None
    states: str | None = None
    zones: str | None = None
    probability_min: str | None = None
    probability_max: str | None = None
    severity_min: str | None = None
    severity_max: str | None = None
    provision_amount_min: str | None = None
    provision_amount_max: str | None = None
    occurrence_cost_min: str | None = None
    occurrence_cost_max: str | None = None
    occurred_reestimated_amount_min: str | None = None
    occurred_reestimated_amount_max: str | None = None
    last_review_on_from: str | None = None
    last_review_on_to: str | None = None
    sort_by: RiskColumn | None = None
    sort_order: SortOrder | None = None


def _text(query: RegisterQuery, name: str) -> str | None:
    """Give a parameter of the query as the model read it, the one source of their names."""
    if name not in RegisterQuery.model_fields:
        raise KeyError(name)
    value = getattr(query, name)
    return value if isinstance(value, str) else None


def _number(
    query: RegisterQuery, column: str, form: re.Pattern[str]
) -> tuple[Bounds[Decimal], list[FieldError]]:
    """Read the two bounds of a column of numbers; the upper one under the lower one is refused.

    A bound that is no number is ``NUMBER_INVALID`` at its parameter; the upper bound lower than
    the lower one ``VALUE_OUT_OF_RANGE`` at ``<column>_max``, the lower bound sent its minimum.
    """
    faults: list[FieldError] = []
    read: list[Decimal | None] = []
    for name in (f"{column}_min", f"{column}_max"):
        text = _text(query, name)
        if text is not None and form.fullmatch(text) is None:
            faults.append(FieldError(f"/query/{name}", NUMBER_INVALID))
        read.append(Decimal(text) if text is not None and form.fullmatch(text) else None)
    least, most = read
    if least is not None and most is not None and most < least:
        named = {"minimum": str(least)}
        faults.append(FieldError(f"/query/{column}_max", VALUE_OUT_OF_RANGE, named))
    return Bounds(least, most), faults


def _day(query: RegisterQuery, name: str) -> tuple[date | None, list[FieldError]]:
    """Read the bound of a period as a day; a day that is none is ``DATE_INVALID`` there."""
    text = _text(query, name)
    if text is None:
        return None, []
    try:
        if DAY.fullmatch(text):
            return date.fromisoformat(text), []
    except ValueError:
        pass
    return None, [FieldError(f"/query/{name}", DATE_INVALID)]


def _period(query: RegisterQuery) -> tuple[Bounds[date], list[FieldError]]:
    """Read the period of the last review, the end included; an end before the start is refused."""
    since, faults = _day(query, "last_review_on_from")
    until, ended = _day(query, "last_review_on_to")
    faults += ended
    if since is not None and until is not None and until < since:
        named = {"minimum": since.isoformat()}
        faults.append(FieldError("/query/last_review_on_to", VALUE_OUT_OF_RANGE, named))
    return Bounds(since, until), faults


def _state(text: str) -> RiskState:
    """Read a state of the query; ``ValueError`` for a text that is none."""
    if text not in ("identified", "occurred", "dismissed"):
        raise ValueError(text)
    return text


def register_filters(
    query: Annotated[RegisterQuery, Query()], search: Search = None
) -> RiskFilters:
    """Read the filters of the register; every fault of a list, a bound or a period at once."""
    faults: list[FieldError] = []
    states, wrong = read_list("states", query.states, _state)
    faults += wrong
    zones, wrong = read_list("zones", query.zones, lambda text: AlertZone(text).value)
    faults += wrong
    columns: dict[str, Bounds[Decimal]] = {}
    for column, form in (
        ("probability", DECIMAL),
        ("severity", MONEY),
        ("provision_amount", MONEY),
        ("occurrence_cost", MONEY),
        ("occurred_reestimated_amount", MONEY),
    ):
        columns[column], wrong = _number(query, column, form)
        faults += wrong
    period, wrong = _period(query)
    faults += wrong
    refuse_query(faults)
    return RiskFilters(
        revision_id=query.revision_id,
        states=states,
        zones=zones,
        search=search,
        probability=columns["probability"],
        severity=columns["severity"],
        provision_amount=columns["provision_amount"],
        occurrence_cost=columns["occurrence_cost"],
        occurred_reestimated_amount=columns["occurred_reestimated_amount"],
        last_review_on=period,
    )


def _money(value: Decimal) -> str:
    """Give an amount as the contract writes it: to the cent."""
    return f"{value:.2f}"


def register_query(
    filters: Annotated[RiskFilters, Depends(register_filters)],
    query: Annotated[RegisterQuery, Query()],
    page: Annotated[Page, Depends(page_of)],
) -> tuple[RiskFilters, RiskSort, RiskPage]:
    """Read what ``listRisks`` asks: its filters, its sort and its page."""
    sort = RiskSort(query.sort_by, descending=query.sort_order is SortOrder.desc)
    return filters, sort, RiskPage(page.limit, page.offset)


@router.get(
    "/projects/{project_id}/risks",
    operation_id="listRisks",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_risks(
    project_id: UUID,
    actor: Acting,
    session: Transaction,
    query: Annotated[tuple[RiskFilters, RiskSort, RiskPage], Depends(register_query)],
) -> dict[str, object]:
    """Give a page of the register of a project in a revision, and the totals of all it retains."""
    read = list_risks(session, project_id, query, viewer_of(actor))
    authors = authors_of(session, read.risks)
    totals = read.totals
    page = query[2]
    return {
        "items": [
            described(session, view, authors).model_dump(mode="json", exclude_unset=True)
            for view in read.risks
        ],
        "totals": {
            "identified": _money(totals.identified),
            "occurred": _money(totals.occurred),
            "dismissed": _money(totals.dismissed),
            "total": _money(totals.total),
            "reserve": _money(totals.reserve),
        },
        "meta": PaginationMeta(limit=page.limit, offset=page.offset, total=read.total).model_dump(
            mode="json"
        ),
    }
