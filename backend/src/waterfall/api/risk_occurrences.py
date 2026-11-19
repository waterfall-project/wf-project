# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The occurrence of a risk (WF-RIS-0060).

``getRiskOccurrenceReport`` (US-2620/L1), the report before the occurrence, a read under
``risks.read`` that writes nothing, without 403 as any read of the project; and
``declareRiskOccurrence`` (US-2620/L2), the occurrence confirmed and handed to the worker, under
``risk_occurrence``.

Registered by the application from US-2550/L1; the report served by US-2620/L1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import RiskOccurrenceReport
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import viewer_of
from waterfall.api.risks import CONSULT
from waterfall.core.risks.interface import occurrence_report

router = APIRouter(tags=["risks"])


@router.get(
    "/projects/{project_id}/risks/{risk_id}/occurrence",
    operation_id="getRiskOccurrenceReport",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=RiskOccurrenceReport,
    response_model_exclude_unset=True,
)
def get_risk_occurrence_report(
    project_id: UUID, risk_id: UUID, actor: Acting, session: Transaction
) -> RiskOccurrenceReport:
    """Tell what the occurrence of an identified risk would do to the main structure."""
    report = occurrence_report(session, project_id, risk_id, viewer_of(actor))
    return RiskOccurrenceReport.model_validate(
        {
            "main_structure_lock_version": report.main_structure_lock_version,
            "risk_lock_version": report.risk_lock_version,
            "creates_current_revision": report.creates_current_revision,
            "differences": [dict(each) for each in report.differences],
            "provision_amount": f"{report.provision_amount:.2f}",
            "refusals": [dict(each) for each in report.refusals],
        }
    )
