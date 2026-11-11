# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of a project: the hours of its lines by role and by month (WF-DEV-0070).

``getProjectWorkload`` (US-1520): the labour lines of the reference revision, of a marked revision
named for its remaining to commit, or of the current revision, spread over the months of their
tasks on the calendar of their roles, with the capacity of each role beside them, restricted to an
organisation node and its descendants. Read under ``estimate.read`` by the readers of the project.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import Basis, WorkloadPlan
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.core.estimate.interface import (
    RoleLoad,
    WorkloadAsked,
    WorkloadBasis,
    WorkloadView,
    workload,
)
from waterfall.core.projects.interface import Viewer
from waterfall.platform.database import utc_now

router = APIRouter(tags=["estimate"])

CONSULT = "estimate.read"


def role_of(role: RoleLoad) -> dict[str, Any]:
    """Give a role of the plan as the contract writes it."""
    return {
        "resource_role_id": role.resource_role_id,
        "label": role.label,
        "org_node_id": role.org_node_id,
        "capacity_monthly_hours": str(role.capacity_monthly_hours),
        "months": [
            {
                "month": each.month,
                "hours": str(each.hours),
                "zone": "alert" if each.is_alert else "nominal",
            }
            for each in role.months
        ],
    }


def plan_of(view: WorkloadView) -> dict[str, Any]:
    """Give the plan of workload as the contract writes it, its hours as exact decimals."""
    plan = WorkloadPlan.model_validate(
        {
            "context": {
                "revision_id": view.revision_id,
                "revision_status": view.revision_status,
                "computed_at": view.computed_at,
                "scope": "project",
                "is_stored": view.is_stored,
            },
            "basis": view.basis.value,
            "org_node_id": view.org_node_id,
            "org_node_label": view.org_node_label,
            "monthly_totals": [
                {"month": month, "hours": str(hours)} for month, hours in view.monthly_totals
            ],
            "roles": [role_of(each) for each in view.roles],
        }
    )
    return plan.model_dump(mode="json")


class WorkloadQuery(BaseModel):
    """The query of the workload, as the contract names it: a basis, a revision, a node."""

    basis: Basis
    revision_id: UUID | None = None
    org_node_id: UUID | None = None


@router.get(
    "/projects/{project_id}/workload",
    operation_id="getProjectWorkload",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_workload(
    project_id: UUID, query: Annotated[WorkloadQuery, Query()], actor: Acting, session: Transaction
) -> dict[str, Any]:
    """Give the workload of a project by role and by month on a basis, the capacities beside it.

    A project without a reference, or without a current revision, lacks the basis of that name
    (409); a marked revision that is not one, or a node the reference does not hold, is refused
    (422, ``/query/revision_id``, ``/query/org_node_id``).
    """
    viewer = Viewer(actor.user_id, actor.permissions)
    basis = WorkloadBasis(query.basis.value)
    asked = WorkloadAsked(basis, query.revision_id, query.org_node_id, utc_now(), viewer)
    return plan_of(workload(session, project_id, asked))
