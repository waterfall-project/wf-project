# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of the rates of a revision to those of the reference (WF-REV-0060).

``getRateUpdateProposal`` and ``applyRateUpdate`` (US-1500/L1). The proposal is read by whoever
consults the revisions of the project, as the revision it describes; the update is a write of the
revision, the command ``apply_rate_update``, made by a contributor holding the permission to manage
the revisions, that of ``createRevision``, which applies it at the creation — not that of the
estimate (``RevisionCommand``, #1351). It is sent at the counter of the revision read (412), and
answers the revision, one version higher.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import RateUpdateApply, Revision
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.revisions import CONSULT, MANAGE, REVISION, described, viewer_of
from waterfall.core.estimate.interface import (
    RateUpdate,
    apply_rate_update,
    rate_update_proposal,
)
from waterfall.core.revisions.interface import read_revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["revisions"])

RATE_UPDATE = f"{REVISION}/rate-update"


@router.get(
    RATE_UPDATE,
    operation_id="getRateUpdateProposal",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_proposal(project_id: UUID, revision_id: UUID, session: Transaction) -> dict[str, Any]:
    """Give the rates of a revision the reference would change, category by category."""
    proposal = rate_update_proposal(session, project_id, revision_id)
    return {
        "target_year": proposal.target_year,
        "categories": [
            {
                "cost_category_id": str(each.cost_category_id),
                "label": each.label,
                "previous_amount": str(each.previous_amount),
                "proposed_amount": str(each.proposed_amount),
                "source": each.source,
            }
            for each in proposal.categories
        ],
    }


@router.post(
    RATE_UPDATE,
    operation_id="applyRateUpdate",
    dependencies=[Depends(RequiresProject(CONSULT, MANAGE))],
    response_model_exclude_unset=True,
)
def post_update(
    project_id: UUID, revision_id: UUID, body: RateUpdateApply, actor: Acting, session: Transaction
) -> Revision:
    """Price a revision at the rates proposed for the categories accepted; give it, counted."""
    act = Act(actor.user_id, utc_now())
    accepted = tuple(each.root for each in body.cost_category_ids)
    update = RateUpdate(revision_id, body.lock_version.root, accepted)
    apply_rate_update(session, project_id, update, act)
    view = read_revision(session, project_id, revision_id, viewer_of(actor))
    return described(session, [view])[0]
