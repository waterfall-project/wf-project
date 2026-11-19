# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reviews of a risk, the changes of its state and its deletion (WF-RIS-0020).

``reviewRisk``, ``listRiskReviews`` and ``deleteRisk`` (US-2590/L1), under ``risks.read`` and
``risks.write``. The review and the deletion are entries of the current revision, which they create
when the project has none; the review answers the risk as it leaves it, dated of the day; the
deletion answers 204, the risk deleted with its own estimate and its provision line. The reviews
are read, the most recent first, in the revision named or the one the risks are read in.

Registered by the application from US-2550/L1; served by US-2590/L1.
"""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from waterfall.api.actors import actor_ref
from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import Risk, RiskReview, RiskReviewWrite
from waterfall.api.evaluation import RequiresProject
from waterfall.api.risk_provisions import Entering
from waterfall.api.risks import CHANGE, CONSULT, described, id_of
from waterfall.api.wire import text_of
from waterfall.core.risks.interface import (
    RiskDeletion,
    RiskReviewEntry,
    delete_risk,
    list_risk_reviews,
    review_risk,
    state_named,
)
from waterfall.core.users.interface import read_authors

router = APIRouter(tags=["risks"])


@router.get(
    "/projects/{project_id}/risks/{risk_id}/reviews",
    operation_id="listRiskReviews",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=list[RiskReview],
    response_model_exclude_unset=True,
)
def get_risk_reviews(
    project_id: UUID,
    risk_id: UUID,
    session: Transaction,
    revision_id: Annotated[UUID | None, Query()] = None,
) -> list[RiskReview]:
    """List the reviews of a risk read in a revision, the most recent first."""
    reviews = list_risk_reviews(session, project_id, risk_id, revision_id)
    authors = read_authors(session, {each.actor for each in reviews if each.actor is not None})
    return [
        RiskReview.model_validate(
            {
                "reviewed_on": each.reviewed_on,
                "probability": text_of(each.probability),
                "severity": f"{each.severity:.2f}",
                "state": each.state,
                "actor": actor_ref(None if each.actor is None else authors.get(each.actor)),
            }
        )
        for each in reviews
    ]


@router.post(
    "/projects/{project_id}/risks/{risk_id}/reviews",
    operation_id="reviewRisk",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    status_code=201,
    response_model=Risk,
    response_model_exclude_unset=True,
)
def post_risk_review(
    project_id: UUID,
    risk_id: UUID,
    body: RiskReviewWrite,
    entering: Entering,
    session: Transaction,
) -> Risk:
    """Review a risk in the current revision, created if the project has none, dated today."""
    entry = RiskReviewEntry(
        risk_id,
        Decimal(body.probability.root.root),
        state_named(body.state.value),
        body.lock_version.root,
        provision_cost_category_id=id_of(body.provision_cost_category_id),
    )
    view = review_risk(session, project_id, entry, entering.writer, entering.viewer)
    return described(session, view)


@router.delete(
    "/projects/{project_id}/risks/{risk_id}",
    operation_id="deleteRisk",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    status_code=204,
)
def delete_a_risk(
    project_id: UUID,
    risk_id: UUID,
    lock_version: Annotated[int, Query(ge=0, le=2147483647)],
    entering: Entering,
    session: Transaction,
) -> Response:
    """Delete a risk no marked revision cites, with its own estimate and its provision line."""
    deletion = RiskDeletion(risk_id, lock_version)
    delete_risk(session, project_id, deletion, entering.writer, entering.viewer)
    return Response(status_code=204)
