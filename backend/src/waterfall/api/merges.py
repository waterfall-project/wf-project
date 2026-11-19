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

Registered by the application from US-2550/L1; the report served by US-2560/L1.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import StructureMergeReport
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import viewer_of
from waterfall.api.revisions import CONSULT, REVISION
from waterfall.core.revisions.interface import merge_report
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["revisions"])

MERGE = f"{REVISION}/structures/{{structure_id}}/merge"


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
