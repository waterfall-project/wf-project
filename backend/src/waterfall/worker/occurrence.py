# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``risk_occurrence``: the occurrence of a risk, merged into the main structure (US-2620).

The risks apply it (``run_occurrence``), in the one transaction the worker runs the task in: a
refusal fails the task with its code, nothing written, and a worker stopped during it leaves the
database as it was (WF-RIS-0060, WF-DAT-0040, WF-ARC-0090). Its author is the requester of the
task, its instant that of the run.
"""

from typing import TYPE_CHECKING

from waterfall.core.risks.interface import run_occurrence
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task


def occur(session: Session, task: Task) -> None:
    """Apply the occurrence a task names, asked for by its requester, now."""
    run_occurrence(session, task.payload, Act(task.requested_by, utc_now()), task.task_id)
