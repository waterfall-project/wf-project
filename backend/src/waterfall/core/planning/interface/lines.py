# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning tells EP-07 of the lines of a task, and where a line may be placed.

A line of estimate is a node of the structure, under the task that bears it (EP-06, "Ce que le
cadrage décide"): the planning owns ``node``, and gives the estimate the lines of a task
(``lines_of``) and the rules by which a line is placed — its parent a task, its rank before the
subtasks, renumbered among its siblings — (``place_line``), under the lock of the structure.

Declared by US-1380/L1; US-1380/L2 fills them, and gives each its arguments and its result.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def lines_of(session: Session, project_id: UUID, task_id: UUID) -> None:
    """Give the lines a task bears, in their order."""
    msg = "lines_of is filled by US-1380/L2"
    raise NotImplementedError(msg)


def place_line(session: Session, project_id: UUID, parent_id: UUID) -> None:
    """Judge the parent of a line, and give its node its place among its siblings."""
    msg = "place_line is filled by US-1380/L2"
    raise NotImplementedError(msg)
