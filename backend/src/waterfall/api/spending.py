# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spending projection of a project: its amounts by nature of cost and by month (WF-DEV-0100).

``getProjectSpending`` (US-2050): the amounts of the lines of the reference revision, of a marked
revision named for its remaining to commit, or of the current revision — the provisions left out —,
spread over the months of their tasks, by nature of cost then by category, restricted to a
subproject or to what falls under none, and shifted by the payment delays on request. Read under
``estimate.read`` by the readers of the project; computed when read, a marked revision too.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import Basis, SpendingProjection
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.core.estimate.interface import (
    SpendingAsked,
    SpendingCategory,
    SpendingCostType,
    SpendingView,
    WorkloadBasis,
    project_spending,
)
from waterfall.core.projects.interface import Viewer
from waterfall.platform.database import utc_now

router = APIRouter(tags=["estimate"])

CONSULT = "estimate.read"


def months_of(months: tuple[tuple[str, Any], ...]) -> list[dict[str, str]]:
    """Give the months of an amount as the contract writes them: the amount an exact decimal."""
    return [{"month": month, "amount": str(amount)} for month, amount in months]


def category_of(category: SpendingCategory) -> dict[str, Any]:
    """Give a category of the projection as the contract writes it."""
    return {
        "cost_category_id": category.cost_category_id,
        "label": category.label,
        "total": str(category.total),
        "months": months_of(category.months),
    }


def cost_type_of(nature: SpendingCostType) -> dict[str, Any]:
    """Give a nature of cost of the projection as the contract writes it."""
    return {
        "cost_type_id": nature.cost_type_id,
        "label": nature.label,
        "total": str(nature.total),
        "months": months_of(nature.months),
        "categories": [category_of(each) for each in nature.categories],
    }


def projection_of(view: SpendingView) -> dict[str, Any]:
    """Give the projection as the contract writes it, its amounts as exact decimals."""
    projection = SpendingProjection.model_validate(
        {
            "context": {
                "revision_id": view.revision_id,
                "revision_status": view.revision_status,
                "computed_at": view.computed_at,
                "scope": view.scope,
                "is_stored": False,
            },
            "basis": view.basis.value,
            "payment_delays": view.payment_delays,
            "total": str(view.total),
            "monthly_totals": months_of(view.monthly_totals),
            "cost_types": [cost_type_of(each) for each in view.cost_types],
        }
    )
    return projection.model_dump(mode="json")


class SpendingQuery(BaseModel):
    """The query of the projection, as the contract names it: a basis, a revision, a scope."""

    basis: Basis
    revision_id: UUID | None = None
    payment_delays: bool = False
    subproject_id: str | None = None


@router.get(
    "/projects/{project_id}/spending",
    operation_id="getProjectSpending",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_spending(
    project_id: UUID, query: Annotated[SpendingQuery, Query()], actor: Acting, session: Transaction
) -> dict[str, Any]:
    """Give the spending of a project by nature of cost and by month on a basis.

    A project without a reference, or without a current revision, lacks the basis of that name
    (409); a marked revision that is not one, or a subproject the project does not have, is refused
    (422, ``/query/revision_id``, ``/query/subproject_id``), as a labour category without an hourly
    rate for the reference year of the revision read (422, ``HOURLY_RATE_MISSING``).
    """
    viewer = Viewer(actor.user_id, actor.permissions)
    basis = WorkloadBasis(query.basis.value)
    asked = SpendingAsked(
        basis, query.revision_id, query.subproject_id, query.payment_delays, utc_now(), viewer
    )
    return projection_of(project_spending(session, project_id, asked))
