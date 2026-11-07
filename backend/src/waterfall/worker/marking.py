# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``revision_mark``: the marking of a revision, the first task of the trade (US-0970).

The revisions mark it (``run_marking``), in the one transaction the worker runs the task in: a
refusal fails the task with its code, nothing written, and a worker stopped during it leaves the
database as it was (WF-REV-0020, WF-DAT-0040, WF-ARC-0090). Its author is the requester of the
task, its instant that of the run, at which the marking takes effect.
"""

from typing import TYPE_CHECKING

from waterfall.core.revisions.interface import run_marking
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.platform.tasks import Task


def mark(session: Session, task: Task) -> None:
    """Mark the revision a task names, asked for by its requester, now."""
    run_marking(session, task.payload, Act(task.requested_by, utc_now()))
