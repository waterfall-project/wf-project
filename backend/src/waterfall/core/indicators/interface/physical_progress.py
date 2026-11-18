# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The physical progress of the summary tasks of a structure (WF-IND-0030, WF-IND-0060; US-1680).

For each summary asked, the share of the budgeted amounts of its subtree — its own lines included,
provisions excluded — its completed tasks carry, to four decimals, whatever the state of the
project; not computable when that total is nought (``no_budgeted_amount``). The planning asks it at
a reading of a structure through its registry ``register_physical_progress``, which this function
fills at the import of the interface, and answers it in the facet of a task (EP-10, "L'avancement
physique").

What it reads: the tasks of the structure and their states, which the reading holds and hands it,
and the budgeted amounts each task bears by the tally of the planning (``earnable_amounts``), in one
statement grouped by task, or as a reading of the tasks alone read them already; no line is read
again. A marked revision is computed alike, on its own lines and states, which do not change.

Declared by US-1660/L1, the socle of EP-10; filled by US-1680, which hands it the summaries of a
structure (``SummariesAsked``) rather than the nodes of a revision.
"""

from typing import TYPE_CHECKING

from waterfall.core.indicators.formulas import NOUGHT, SummaryTask, summary_progress
from waterfall.core.planning.interface import PhysicalShare, earnable_amounts

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import SummariesAsked


def physical_progress(session: Session, asked: SummariesAsked) -> dict[UUID, PhysicalShare]:
    """Give the physical progress of each summary asked, not computable without budgeted amount."""
    earnable = earnable_amounts(session, asked)
    tasks = {
        task_id: SummaryTask(task.parent_id, task.completed, earnable.get(task_id, NOUGHT))
        for task_id, task in asked.tasks.items()
    }
    return {
        summary: PhysicalShare(figure.value, figure.reason)
        for summary, figure in summary_progress(tasks, asked.summaries).items()
    }
