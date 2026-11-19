# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision of an identified risk changed (WF-RIS-0010).

``updateRiskProvision`` (US-2580/L1), under ``risks.read`` and ``risks.write``: the category, the
subproject and the task of the provision line of a risk, an entry of the current revision, which
it creates when the project has none (H-02, #1782). A field not sent stays the risk's; the
response is the risk, its provision task and its counter as the entry left them.

Registered by the application from US-2550/L1; served by US-2580/L1.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import Risk, RiskProvisionUpdate
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.nodes import Writing
from waterfall.api.projects import viewer_of
from waterfall.api.risks import CHANGE, CONSULT, described, id_of
from waterfall.core.planning.interface import Writer
from waterfall.core.projects.interface import Viewer
from waterfall.core.risks.interface import OMITTED, RiskProvisionChange, update_risk_provision

router = APIRouter(tags=["risks"])


@dataclass(frozen=True, slots=True)
class Entry:
    """Who enters the provision: the writer of the entry and the viewer of its answer."""

    writer: Writer
    viewer: Viewer


def entry_of(actor: Acting, writer: Writing) -> Entry:
    """Give who enters, as the writer of the entry and as the reader of the risk it answers."""
    return Entry(writer, viewer_of(actor))


Entering = Annotated[Entry, Depends(entry_of)]


@router.put(
    "/projects/{project_id}/risks/{risk_id}/provision",
    operation_id="updateRiskProvision",
    dependencies=[Depends(RequiresProject(CONSULT, CHANGE))],
    response_model=Risk,
    response_model_exclude_unset=True,
)
def put_risk_provision(
    project_id: UUID,
    risk_id: UUID,
    body: RiskProvisionUpdate,
    entering: Entering,
    session: Transaction,
) -> Risk:
    """Change the category, the subproject and the task of the provision of an identified risk.

    A subproject sent as ``null`` takes the provision out of its subproject, a task as ``null``
    gives the line back to the first task of the first level; a category sent as ``null`` is a
    category not sent.
    """
    sent = body.model_fields_set
    category = id_of(body.provision_cost_category_id)
    change = RiskProvisionChange(
        risk_id,
        body.lock_version.root,
        provision_cost_category_id=OMITTED if category is None else category,
        provision_subproject_id=(
            id_of(body.provision_subproject_id) if "provision_subproject_id" in sent else OMITTED
        ),
        provision_task_id=(
            id_of(body.provision_task_id) if "provision_task_id" in sent else OMITTED
        ),
    )
    view = update_risk_provision(session, project_id, change, entering.writer, entering.viewer)
    return described(session, view)
