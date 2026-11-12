# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution: the lines that hold a task open, and the board of the tasks (US-1590).

``open_lines`` answers the question the planning asks when it reads a tree — before it completes a
summary task, reads one, or makes a leaf of it —: which of these tasks bear an own line, not a
provision, whose remaining is not zero (``register_open_lines``, which US-1590/L1 declares in the
planning and fills with it at the import of this interface), and ``zeroed_lines`` when the lines of
a task were set to nought, which a summary completed again reads (``register_zeroed_at``,
US-1650/L2, #2803). ``startable_tasks``
(``listStartableTasks``, US-1590/L2) reads the tasks of the main structure of the current revision
of a project in three columns, each card with its gestures (``progress_commands``, #2714) and the
conditions of the entry of the remaining to commit, which EP-10 reads too (EP-09, "Le Kanban et
les lignes propres").

Declared by US-1580/L1 with their arguments and their results, which EP-10 reads; ``open_lines``
filled by US-1590/L1; ``startable_tasks`` and the types of its result are computed in
``remaining/kanban.py`` (US-1590/L2), which this interface re-exports.
"""

from typing import TYPE_CHECKING

from waterfall.core.estimate.remaining import reviewing
from waterfall.core.estimate.remaining.kanban import (
    KanbanTask,
    NotStartedTask,
    StartableTasks,
    startable_tasks,
)

__all__ = [
    "KanbanTask",
    "NotStartedTask",
    "StartableTasks",
    "open_lines",
    "startable_tasks",
    "zeroed_lines",
]

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session


def open_lines(
    session: Session, project_id: UUID, lines_by_task: Mapping[UUID, Sequence[UUID]]
) -> frozenset[UUID]:
    """Give the tasks among these that bear an own line, not a provision, with a remaining.

    ``lines_by_task`` the lines each task of a project bears, those of a risk left out by the
    planning; read in one statement, a provision line by its category never holding a task
    (WF-PLA-0040).
    """
    return reviewing.open_tasks(session, project_id, lines_by_task)


def zeroed_lines(
    session: Session, project_id: UUID, lines_by_task: Mapping[UUID, Sequence[UUID]]
) -> dict[UUID, datetime]:
    """Give the tasks among these whose own lines, not provisions, were all set to nought, and when.

    The latest instant one of them was re-estimated (``reestimated_at``), the day of the zeroing of
    the lines of a summary completed again (WF-PLA-0130, #2803).
    """
    return reviewing.zeroed_tasks(session, project_id, lines_by_task)
