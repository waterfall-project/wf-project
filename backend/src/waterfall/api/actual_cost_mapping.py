# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The mapping of the extraction of the actual costs (FBS-3.1).

``getActualCostMapping`` and ``setActualCostMapping`` (WF-REF-0190): the mapping is read under
the permission to read the cost settings, and replaced whole under the one to change them.
"""

from fastapi import APIRouter, Depends

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.models import ActualCostMapping, ActualCostMappingWrite
from waterfall.api.evaluation import Requires
from waterfall.core.cost_settings.interface import (
    ActualCostMappingView,
    ColumnLabels,
    read_actual_cost_mapping,
    replace_actual_cost_mapping,
)
from waterfall.core.cost_settings.interface import ActualCostMappingWrite as MappingWrite
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["reference"])

CONSULTATION = "cost_settings.read"
CHANGE = "cost_settings.write"
# The contract declares no 404 for the writing: it asks for the permission to change alone.
READ = [Depends(Requires(CONSULTATION))]
WRITE = [Depends(Requires(CHANGE))]


def actual_cost_mapping(view: ActualCostMappingView) -> ActualCostMapping:
    """Describe the mapping as the contract does."""
    return ActualCostMapping.model_validate(
        {
            "columns": [
                {"column": c.column, "required": c.required, "labels": list(c.labels)}
                for c in view.columns
            ],
            "kept_columns": list(view.kept_columns),
            "is_complete": view.is_complete,
            "missing_columns": list(view.missing_columns),
            "lock_version": view.lock_version,
            "audit": {
                "created_at": view.created_at,
                "created_by": actor_ref(view.created_by),
                "updated_at": view.updated_at,
                "updated_by": actor_ref(view.updated_by),
            },
        }
    )


@router.get(
    "/reference/actual-cost-mapping",
    operation_id="getActualCostMapping",
    dependencies=READ,
    response_model_exclude_unset=True,
)
def get_actual_cost_mapping(session: Transaction) -> ActualCostMapping:
    """Give the mapping, which is born empty with the installation."""
    return actual_cost_mapping(read_actual_cost_mapping(session))


@router.put(
    "/reference/actual-cost-mapping",
    operation_id="setActualCostMapping",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_actual_cost_mapping(
    body: ActualCostMappingWrite, account: Caller, session: Transaction
) -> ActualCostMapping:
    """Replace the whole mapping unless the counter is stale (412); an incomplete one is kept."""
    write = MappingWrite(
        columns=[
            ColumnLabels(column.column.value, [label.root for label in column.labels])
            for column in body.columns
        ],
        kept_columns=[label.root for label in body.kept_columns],
    )
    act = Act(account.user_id, utc_now())
    view = replace_actual_cost_mapping(session, write, body.lock_version.root, act)
    return actual_cost_mapping(view)
