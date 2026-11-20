# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``structure_merge``: the merge of a differential into the main structure (US-2560/L2).

The revisions apply it (``run_merge``), in the one transaction the worker runs the task in: the
differences written, the revision marked, the reference designated; a refusal fails the task with
its code, nothing written, and a worker stopped during it leaves the database as it was
(WF-REV-0050, WF-DAT-0040, WF-ARC-0090). Its author is the requester of the task, its instant that
of the run.
"""

from typing import TYPE_CHECKING

from waterfall.core.revisions.interface import run_merge
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task


def merge(session: Session, task: Task) -> None:
    """Apply the merge a task names, asked for by its requester, now."""
    run_merge(session, task.payload, Act(task.requested_by, utc_now()), task.task_id)
