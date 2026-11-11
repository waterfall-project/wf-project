# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines of the actual costs of a project, read and excluded (WF-CRE-0030, WF-CRE-0040).

``listActualCosts`` (US-1620/L1), under ``actual_costs.read``; ``setActualCostTrackedScope``
(US-1620/L1), under the quality of contributor and ``cost_line_exclude``.

The server filters, sorts and paginates; the three totals, the instant of the last import and the
union of the columns kept are those of all the lines retained, not of the page. The exclusion is
a ``PUT`` of the state aimed at, without a counter: the answer is the line, and the totals follow
on the next reading.
"""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import (
    ActualCostLine,
    ActualCostListMeta,
    ActualCostTotals,
    ScopeExclusion,
    SortOrder,
    Timestamp,
)
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.core.costs.interface import (
    CostLineFilters,
    CostLinePage,
    CostLineSort,
    CostLineView,
    ScopeChange,
    list_actual_costs,
    set_tracked_scope,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["actual-costs"])

READ = "actual_costs.read"
EXCLUDE = "cost_line_exclude"
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500
# The columns a sort names: those of the grid, or a column kept of the files.
SORT_COLUMN = (
    r"^(document_date|document_number|document_item|amount|subproject|in_tracked_scope"
    r"|excluded_reason|passthrough\..+)$"
)


def cost_line(view: CostLineView) -> dict[str, Any]:
    """Describe a line as the contract does, its authors named as they are today."""
    return ActualCostLine.model_validate(
        {
            "cost_line_id": view.cost_line_id,
            "document_number": view.document_number,
            "document_item": view.document_item,
            "document_date": view.document_date,
            "amount": str(view.amount),
            "project_id": view.project_id,
            "subproject_id": view.subproject_id,
            "subproject_code": view.subproject_code,
            "subproject_label": view.subproject_label,
            "is_in_tracked_scope": view.is_in_tracked_scope,
            "excluded_reason": view.excluded_reason,
            "passthrough": view.passthrough,
            "audit": {
                "created_at": view.created_at,
                "created_by": actor_ref(view.created_by),
                "updated_at": view.updated_at,
                "updated_by": actor_ref(view.updated_by),
            },
        }
    ).model_dump(mode="json", exclude_unset=True)


def cost_line_filters(
    subproject_id: Annotated[str | None, Query()] = None,
    from_date: Annotated[date | None, Query(alias="from")] = None,
    to_date: Annotated[date | None, Query(alias="to")] = None,
    in_tracked_scope: Annotated[bool | None, Query()] = None,
) -> CostLineFilters:
    """Read the filters of the list: a subproject, a period on the date of the document, a scope."""
    return CostLineFilters(subproject_id, from_date, to_date, in_tracked_scope)


def cost_line_sort(
    sort_by: Annotated[str | None, Query(pattern=SORT_COLUMN)] = None,
    sort_order: SortOrder = SortOrder.asc,
) -> CostLineSort:
    """Read the sort the list asks for; none, the most recent documents first."""
    return CostLineSort(sort_by, descending=sort_order is SortOrder.desc)


def page_asked(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CostLinePage:
    """Read the page asked for: its size and the lines skipped before it."""
    return CostLinePage(limit, offset)


@router.get(
    "/projects/{project_id}/actual-costs",
    operation_id="listActualCosts",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_actual_costs(
    project_id: UUID,
    session: Transaction,
    filters: Annotated[CostLineFilters, Depends(cost_line_filters)],
    sort: Annotated[CostLineSort, Depends(cost_line_sort)],
    page: Annotated[CostLinePage, Depends(page_asked)],
) -> dict[str, Any]:
    """Give a page of the actual costs of a project, with the totals of all those retained."""
    read = list_actual_costs(session, project_id, filters, sort, page)
    totals = ActualCostTotals.model_validate(
        {
            "tracked": str(read.totals.tracked),
            "excluded": str(read.totals.excluded),
            "overall": str(read.totals.overall),
        }
    )
    meta = ActualCostListMeta(
        limit=page.limit,
        offset=page.offset,
        total=read.total,
        passthrough_columns=read.passthrough_columns,
    )
    return {
        "items": [cost_line(view) for view in read.views],
        "totals": totals.model_dump(mode="json"),
        "last_import_at": (
            None
            if read.last_import_at is None
            else Timestamp(read.last_import_at).model_dump(mode="json")
        ),
        "meta": meta.model_dump(mode="json"),
    }


@router.put(
    "/projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope",
    operation_id="setActualCostTrackedScope",
    dependencies=[Depends(RequiresProject(EXCLUDE))],
    response_model=None,
)
def put_tracked_scope(
    project_id: UUID,
    cost_line_id: UUID,
    body: ScopeExclusion,
    actor: Acting,
    session: Transaction,
) -> dict[str, Any]:
    """Exclude a line from the tracked scope, or reinstate it, as aimed at (idempotent)."""
    act = Act(actor.user_id, utc_now())
    change = ScopeChange(body.is_in_tracked_scope, body.reason)
    return cost_line(set_tracked_scope(session, project_id, cost_line_id, change, act))
