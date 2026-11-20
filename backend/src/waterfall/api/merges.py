# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge of an amendment into the main structure (WF-REV-0050).

``getStructureMergeReport`` (US-2560/L1), the report before the merge, and ``mergeCostStructure``
(US-2560/L2), the merge confirmed and handed to the worker, under ``structure_merge``.

The report is a read, by whoever consults the revisions of the project, without a 403, as any
read of the project: it writes nothing, and abandoning at this stage is not confirming. A structure
that has no report is refused with the 409 of its merge, by the first condition its command lacks.
What the planning and the estimate find of the merge (``merge_report``) is validated here against
the models of the contract (``StructureMergeReport``, its ``ImportDifference``,
``ImportCompletedTask`` and ``ReportRefusal``), the parts of the modules being only mappings to them
(#3948).

``mergeCostStructure`` is a structuring action of its own permission (``structure_merge``),
reserved to the project managers (WF-ADM-0100, WF-PRJ-0060): judged under the lock of the project
and of the two structures, in the order of the contract, its task submitted in the transaction of
the request, and answered 202 with it, which ``getBackgroundTask`` follows (WF-ARC-0090).

Registered by the application from US-2550/L1; the report served by US-2560/L1, the merge by
US-2560/L2.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, StructureMerge, StructureMergeReport
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import viewer_of
from waterfall.api.revisions import CONSULT, REVISION
from waterfall.api.tasks import task_ref
from waterfall.core.revisions.interface import MergeRequest, merge_report, submit_merge
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.tasks import BackgroundTask

router = APIRouter(tags=["revisions"])

MERGE = f"{REVISION}/structures/{{structure_id}}/merge"
STRUCTURE_MERGE = "structure_merge"


@router.get(
    MERGE,
    operation_id="getStructureMergeReport",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_merge_report(
    project_id: UUID, revision_id: UUID, structure_id: UUID, actor: Acting, session: Transaction
) -> dict[str, Any]:
    """Give what the merge of a differential would do, and what refuses it; writes nothing."""
    act = Act(actor.user_id, utc_now())
    report = merge_report(session, (project_id, revision_id, structure_id), viewer_of(actor), act)
    found = report.found
    return StructureMergeReport.model_validate(
        {
            "main_structure_lock_version": report.main_structure_lock_version,
            "amendment_lock_version": report.amendment_lock_version,
            "creates_current_revision": report.creates_current_revision,
            "differences": list(found.differences),
            "completed_tasks": list(found.completed_tasks),
            "refusals": list(found.refusals),
        }
    ).model_dump(mode="json", exclude_unset=True)


def merge_request(
    project_id: UUID, revision_id: UUID, structure_id: UUID, body: StructureMerge
) -> MergeRequest:
    """Read the merge confirmed: the differential of the path, the name, the counters read."""
    counters = (body.main_structure_lock_version.root, body.amendment_lock_version.root)
    return MergeRequest(
        project_id, revision_id, structure_id, body.version_name, body.description, counters
    )


@router.post(
    MERGE,
    operation_id="mergeCostStructure",
    dependencies=[Depends(RequiresProject(CONSULT, STRUCTURE_MERGE, manager=True))],
    status_code=202,
    response_model_exclude_unset=True,
)
def post_merge(
    request: Annotated[MergeRequest, Depends(merge_request)],
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> BackgroundTaskRef:
    """Deposit the merge of a differential for the worker, at the counters of the report confirmed.

    Refused as its report is (409), at another counter of either structure (412), out of date
    (409), under a name of version taken (409); nothing is deposited then.
    """
    act = Act(actor.user_id, utc_now())
    task_id = submit_merge(session, services.queue, request, act, viewer_of(actor))
    return task_ref(session.get_one(BackgroundTask, task_id))
