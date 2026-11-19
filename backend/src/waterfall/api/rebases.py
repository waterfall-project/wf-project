# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The update of a differential from the main structure (WF-REV-0100; US-3050).

``getStructureRebaseReport`` (US-3050/L3), the report before the update: what it would carry from
the main structure into the differential, what the differential keeps against it, and what refuses
it, with the counters of the two structures read. ``rebaseCostStructure`` (US-3050/L4) applies it,
under the command ``rebase`` of the structure.

The report is a read, by whoever consults the revisions of the project, without a 403, as the
report of a merge: it writes nothing. A structure that has no report — not a differential not
merged of the current revision, out of date — is refused with the 409 of its update, by the first
condition its command lacks. What the planning and the estimate find of the update
(``rebase_report``) is validated here against the models of the contract
(``StructureRebaseReport``, its ``ImportDifference`` and ``ReportRefusal``).

Registered by the application from US-3050/L3.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import StructureRebaseReport
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.revisions import CONSULT, REVISION
from waterfall.core.revisions.interface import rebase_report
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["revisions"])

REBASE = f"{REVISION}/structures/{{structure_id}}/rebase"


@router.get(
    REBASE,
    operation_id="getStructureRebaseReport",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_rebase_report(
    project_id: UUID, revision_id: UUID, structure_id: UUID, actor: Acting, session: Transaction
) -> dict[str, Any]:
    """Give what the update of a differential would do, and what refuses it; writes nothing."""
    act = Act(actor.user_id, utc_now())
    report = rebase_report(session, (project_id, revision_id, structure_id), act)
    return StructureRebaseReport.model_validate(
        {
            "main_structure_lock_version": report.main_structure_lock_version,
            "structure_lock_version": report.structure_lock_version,
            "differences": list(report.found.differences),
            "refusals": list(report.found.refusals),
        }
    ).model_dump(mode="json", exclude_unset=True)
