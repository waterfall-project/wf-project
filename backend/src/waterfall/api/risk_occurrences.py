# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The occurrence of a risk (WF-RIS-0060).

``getRiskOccurrenceReport`` (US-2620/L1), the report before the occurrence, a read under
``risks.read`` that writes nothing, without 403 as any read of the project; and
``declareRiskOccurrence`` (US-2620/L2), the occurrence confirmed and handed to the worker, under
``risk_occurrence``.

Registered by the application from US-2550/L1; the report served by US-2620/L1.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from waterfall.api.authentication import ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, RiskOccurrence, RiskOccurrenceReport
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.projects import viewer_of
from waterfall.api.risks import CONSULT
from waterfall.api.tasks import task_ref
from waterfall.core.projects.interface import current_day
from waterfall.core.risks.interface import OccurrenceRequest, occurrence_report, submit_occurrence
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.tasks import BackgroundTask

# The permission that guards the occurrence, which includes the merge it triggers (WF-ADM-0100).
OCCURRENCE = "risk_occurrence"

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
    today = current_day(utc_now())
    report = occurrence_report(session, project_id, risk_id, viewer_of(actor), today)
    return RiskOccurrenceReport.model_validate(
        {
            "main_structure_lock_version": report.main_structure_lock_version,
            "risk_lock_version": report.risk_lock_version,
            "creates_current_revision": report.creates_current_revision,
            "differences": [dict(each) for each in report.differences],
            "provision_amount": f"{report.provision_amount:.2f}",
            "refusals": [dict(each) for each in report.refusals],
            "own_estimate_past_planning_start_on": report.own_estimate_past_planning_start_on,
            "completed_provision_task": (
                None
                if report.completed_provision_task is None
                else dict(report.completed_provision_task)
            ),
        }
    )


def occurrence_request(project_id: UUID, risk_id: UUID, body: RiskOccurrence) -> OccurrenceRequest:
    """Read what the confirmation sends: the risk, and the counters and the creation it read."""
    return OccurrenceRequest(
        project_id,
        risk_id,
        body.main_structure_lock_version.root,
        body.risk_lock_version.root,
        body.creates_current_revision,
    )


@router.post(
    "/projects/{project_id}/risks/{risk_id}/occurrence",
    operation_id="declareRiskOccurrence",
    dependencies=[Depends(RequiresProject(CONSULT, OCCURRENCE))],
    status_code=202,
    response_model=BackgroundTaskRef,
    response_model_exclude_unset=True,
)
def post_risk_occurrence(
    request: Annotated[OccurrenceRequest, Depends(occurrence_request)],
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> BackgroundTaskRef:
    """Deposit the occurrence of a risk for the worker, and say where it stands.

    Judged under the locks at the counters the report read, nothing deposited if refused; the task
    is written in the transaction of the request, and deposited once it is committed.
    """
    act = Act(actor.user_id, utc_now())
    task_id = submit_occurrence(session, services.queue, request, act, viewer_of(actor))
    return task_ref(session.get_one(BackgroundTask, task_id))
