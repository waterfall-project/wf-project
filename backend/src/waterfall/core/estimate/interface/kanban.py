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

Declared by US-1580/L1 with their arguments and their results, which EP-10 reads; each raises
``NotImplementedError`` naming the story that fills it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import NodeView


@dataclass(frozen=True, slots=True)
class KanbanCommandAvailability:
    """A gesture of a card, what it lacks and the state it sends (``KanbanCommandAvailability``).

    ``command`` is ``start``, ``complete``, ``reopen`` or ``enter_remaining``; ``progress`` the
    state ``setTaskProgress`` receives, none for ``enter_remaining``, which writes nothing.
    """

    command: str
    progress: str | None
    missing_conditions: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Whether nothing is lacking."""
        return not self.missing_conditions


@dataclass(frozen=True, slots=True)
class KanbanTask:
    """A task of the board (``KanbanTask``): the whole node, and the gestures of its card."""

    node: NodeView
    available_commands: tuple[KanbanCommandAvailability, ...]


@dataclass(frozen=True, slots=True)
class NotStartedTask(KanbanTask):
    """A task not started (``NotStartedTask``): whether all its predecessors are completed."""

    predecessors_completed: bool


@dataclass(frozen=True, slots=True)
class StartableTasks:
    """The tasks of a project in execution, three columns each in the order of the plan."""

    not_started: tuple[NotStartedTask, ...]
    started: tuple[KanbanTask, ...]
    completed: tuple[KanbanTask, ...]


def open_lines(session: Session, task_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give the tasks among these that bear an own line, not a provision, with a remaining."""
    msg = "open_lines is filled by US-1590/L1"
    raise NotImplementedError(msg)


def startable_tasks(session: Session, project_id: UUID) -> StartableTasks:
    """Give the tasks of a project in execution, by column (``listStartableTasks``)."""
    msg = "startable_tasks is filled by US-1590/L2"
    raise NotImplementedError(msg)
