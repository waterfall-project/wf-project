# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The occurrence of a risk (``getRiskOccurrenceReport``, ``declareRiskOccurrence``; US-2620).

The report tells, before anything is written, what the occurrence would do to the main structure
of the current revision — or of the last marked one, which the occurrence would copy first —: the
tasks and the lines of the own estimate grafted (``graft`` of the planning), the provision line
removed, the reasons that refuse it, and the counters read. The confirmation sends them back, and
the occurrence runs as a background task, one operation, on the model of the marking: the very
computation of the report, applied under the locks; the provision line removed, the cost at
occurrence frozen, a review of occurrence written, the own estimate marked merged (WF-RIS-0060).
It marks nothing.

Declared by US-2550/L1, the socle of EP-08; filled by US-2620/L1 (the report) and US-2620/L2 (the
application, ``applying``).
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.risks.applying import (
    OccurrenceRequest,
    run_occurrence_task,
    submit_occurrence_task,
)
from waterfall.core.risks.occurring import OccurrenceReport, occurred_among, report_occurrence

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.platform.audit import Act
    from waterfall.platform.queue import TaskQueue

# The report and the request, as the interface hands them on (``risks.interface`` re-exports them).
__all__ = ["OccurrenceReport", "OccurrenceRequest"]


def occurrence_report(
    session: Session, project_id: UUID, risk_id: UUID, viewer: Viewer, today: date
) -> OccurrenceReport:
    """Tell what the occurrence of an identified risk would do, writing nothing; or refuse (409).

    In the order of the 409 of the occurrence: the conditions of the project, then, the risk read
    (404), those of the risk (``occurring``). ``today`` is the day of the read, in the time zone of
    the installation: an own estimate that starts before it is told (#4133).
    """
    return report_occurrence(session, project_id, risk_id, viewer, today)


def submit_occurrence(
    session: Session, queue: TaskQueue, request: OccurrenceRequest, act: Act, viewer: Viewer
) -> UUID:
    """Judge an occurrence confirmed, then submit its task, in the transaction of the request."""
    return submit_occurrence_task(session, queue, request, act, viewer)


def run_occurrence(session: Session, payload: Mapping[str, Any], act: Act, task_id: UUID) -> None:
    """Apply the occurrence a task names, in the transaction of the task (the worker's)."""
    run_occurrence_task(session, payload, act, task_id)


def occurred_risk_ids(
    session: Session, project_id: UUID, risk_ids: Collection[UUID]
) -> frozenset[UUID]:
    """Give those of the risks named that occurred in the project, in any of its revisions."""
    return occurred_among(session, project_id, risk_ids)
