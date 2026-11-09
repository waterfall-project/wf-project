# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution: the lines that hold a task open, and the board of the tasks (US-1590).

``open_lines`` answers the question the planning asks before it completes a summary task, reads
one, or makes a leaf of it: which of these tasks bear an own line, not a provision, whose remaining
is not zero (``register_open_lines``, which US-1590/L1 declares in the planning and fills with it).
``startable_tasks`` reads the tasks of the main structure of the current revision of a project in
three columns, each card with its gestures and the conditions of the re-estimation
(``listStartableTasks``, US-1590/L2), which EP-10 reads too (EP-09, "Le Kanban et les lignes
propres").

Declared by US-1580/L1; each raises ``NotImplementedError`` naming the story that fills it, which
gives ``startable_tasks`` its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session


def open_lines(session: Session, task_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give the tasks among these that bear an own line, not a provision, with a remaining."""
    msg = "open_lines is filled by US-1590/L1"
    raise NotImplementedError(msg)


def startable_tasks(session: Session, project_id: UUID) -> None:
    """Give the tasks of a project in execution, by column (``listStartableTasks``)."""
    msg = "startable_tasks is filled by US-1590/L2"
    raise NotImplementedError(msg)
