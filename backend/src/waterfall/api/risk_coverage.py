# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reserve for risks and the coverage of a project (WF-RIS-0050).

``getProjectRiskCoverage`` (US-2610/L1), under ``risks.read``: the reserve of the reference, the
provisions left of the risks identified in the revision read, the cost at occurrence of the
occurred ones, their signed variance, and the re-estimated amount of the lines that came from them
beside, outside the variance (#1761). The revision named, else the current one, else the last one
marked; a marked revision gives the coverage its marking kept in the document of the remaining to
commit, never computed again (WF-DAT-0040), and one marked before the indicators were kept, the
coverage computed at the reading.

Registered by the application from US-2550/L1; served by US-2610/L1.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.api.scopes import kept_document
from waterfall.core.costs.interface import PROJECT
from waterfall.core.estimate.interface import CalculationContext, risk_coverage
from waterfall.core.indicators.interface import risk_coverage_document
from waterfall.core.revisions.interface import read_revision_for
from waterfall.platform.database import utc_now

router = APIRouter(tags=["risks"])

CONSULT = "risks.read"


@router.get(
    "/projects/{project_id}/risks/coverage",
    operation_id="getProjectRiskCoverage",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_project_risk_coverage(
    project_id: UUID, session: Transaction, revision_id: Annotated[UUID | None, Query()] = None
) -> dict[str, Any]:
    """Give the coverage of the risks of a project in a revision, its reserve and its variance."""
    read = read_revision_for(session, project_id, revision_id)
    if read.marked:
        kept = kept_document(session, read.revision_id, "remaining", PROJECT)
        if kept is not None:
            return {"context": kept["context"], **kept["coverage"]}
    context = CalculationContext(
        read.revision_id, "marked" if read.marked else "draft", utc_now(), PROJECT, is_stored=False
    )
    return risk_coverage_document(context, risk_coverage(session, project_id, read.revision_id))
