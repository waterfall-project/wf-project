# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The log of the imports of the actual costs of a project (WF-CRE-0050).

``listCostImports`` (US-1610/L2), under ``actual_costs.read``; the opening, the application and the
abandonment of an import stay with the router of the exchanges, which asks the format of its kind.
Each entry is the one the application of an import wrote, its author the account that confirmed
it: how recent the figures read are.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import CostImport, PaginationMeta
from waterfall.api.evaluation import RequiresProject
from waterfall.core.costs.interface import CostImportView, list_cost_imports

router = APIRouter(tags=["actual-costs"])

READ = "actual_costs.read"
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500


def cost_import(view: CostImportView) -> dict[str, Any]:
    """Describe an entry of the log as the contract does."""
    return CostImport.model_validate(
        {
            "cost_import_id": view.cost_import_id,
            "imported_at": view.imported_at,
            "actor": actor_ref(view.author),
            "period_from": view.period_from,
            "period_to": view.period_to,
            "created_count": view.created_count,
            "updated_count": view.updated_count,
            "unchanged_count": view.unchanged_count,
            "rejected_count": view.rejected_count,
        }
    ).model_dump(mode="json", exclude_unset=True)


@router.get(
    "/projects/{project_id}/cost-imports",
    operation_id="listCostImports",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_cost_imports(
    project_id: UUID,
    session: Transaction,
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Give a page of the log of the imports of a project, the latest first (WF-CRE-0050)."""
    read = list_cost_imports(session, project_id, limit, offset)
    meta = PaginationMeta(limit=limit, offset=offset, total=read.total)
    return {"items": [cost_import(view) for view in read.views], "meta": meta.model_dump()}
