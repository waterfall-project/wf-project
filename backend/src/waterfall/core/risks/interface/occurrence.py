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
application).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from waterfall.core.risks.occurring import OccurrenceReport, report_occurrence

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer
    from waterfall.platform.audit import Act
    from waterfall.platform.queue import TaskQueue

# The report, as the interface hands it on (``risks.interface`` re-exports it from here).
__all__ = ["OccurrenceReport"]


@dataclass(frozen=True, slots=True)
class OccurrenceRequest:
    """An occurrence confirmed (``RiskOccurrence``): the risk, and what its report read."""

    project_id: UUID
    risk_id: UUID
    main_structure_lock_version: int
    risk_lock_version: int
    creates_current_revision: bool


def occurrence_report(
    session: Session, project_id: UUID, risk_id: UUID, viewer: Viewer
) -> OccurrenceReport:
    """Tell what the occurrence of an identified risk would do, writing nothing; or refuse (409).

    In the order of the 409 of the occurrence: the conditions of the project, then, the risk read
    (404), those of the risk (``occurring``).
    """
    return report_occurrence(session, project_id, risk_id, viewer)


def submit_occurrence(
    session: Session, queue: TaskQueue, request: OccurrenceRequest, act: Act, viewer: Viewer
) -> UUID:
    """Judge an occurrence confirmed, then submit its task, in the transaction of the request."""
    msg = "submit_occurrence is filled by US-2620/L2"
    raise NotImplementedError(msg)


def run_occurrence(session: Session, payload: Mapping[str, Any], act: Act) -> None:
    """Apply the occurrence a task names, in the transaction of the task (the worker's)."""
    msg = "run_occurrence is filled by US-2620/L2"
    raise NotImplementedError(msg)
