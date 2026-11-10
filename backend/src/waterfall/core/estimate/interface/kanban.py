# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution: the lines that hold a task open, and the board of the tasks (US-1590).

``open_lines`` answers the question the planning asks when it reads a tree — before it completes a
summary task, reads one, or makes a leaf of it —: which of these tasks bear an own line, not a
provision, whose remaining is not zero (``register_open_lines``, which US-1590/L1 declares in the
planning and fills with it at the import of this interface). ``startable_tasks`` reads the tasks of
the main structure of the current revision of a project in three columns, each card with its
gestures — those the planning gives (``progress_commands``, of the type it declares,
``KanbanCommandAvailability``, #2714) — and the conditions of the re-estimation
(``listStartableTasks``, US-1590/L2), which EP-10 reads too (EP-09, "Le Kanban et les lignes
propres").

Declared by US-1580/L1 with their arguments and their results, which EP-10 reads; ``open_lines``
filled by US-1590/L1, ``startable_tasks`` raises ``NotImplementedError`` naming the story that fills
it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.estimate.remaining import reviewing

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import KanbanCommandAvailability, NodeView


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


def open_lines(
    session: Session, project_id: UUID, borne: Mapping[UUID, Sequence[UUID]]
) -> frozenset[UUID]:
    """Give the tasks among these that bear an own line, not a provision, with a remaining.

    ``borne`` the lines each task of a project bears, those of a risk left out by the planning;
    read in one statement, a provision line by its category never holding a task (WF-PLA-0040).
    """
    return reviewing.open_tasks(session, project_id, borne)


def startable_tasks(session: Session, project_id: UUID) -> StartableTasks:
    """Give the tasks of a project in execution, by column (``listStartableTasks``)."""
    msg = "startable_tasks is filled by US-1590/L2"
    raise NotImplementedError(msg)
