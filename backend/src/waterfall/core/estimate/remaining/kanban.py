# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks in execution of a project, by column: the board of the Kanban (WF-RAE-0030).

The tasks of the main structure of the current revision — the revision in progress, else the last
one marked —, in the order of the plan, divided by their state in three columns. A summary task is
none of the cards but the one that awaits only its own lines (``awaiting_own_lines``, #1851),
which is started; the state of any other derives from its subordinates, and a card moves nothing
of it. Each card holds the gestures the planning gives it (``progress_commands``), then, after
those of its own, the conditions of the entry of the remaining to commit of the main structure
(``edit_remaining``) the gesture is an entry of; the cards of a caller that may not write the
remaining to commit, or of a terminal project, hold none. A task not started says whether all its
predecessors are completed, which flags a milestone to complete (WF-RAE-0030).

Two readings, never one a task: the nodes of the structure with their links, by the planning
(``list_nodes``), and the tasks that bear a line besides the provisions (``bearing_tasks``).
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from waterfall.core.planning.interface import (
    NodeFilters,
    Place,
    bearing_tasks,
    list_nodes,
    progress_commands,
)
from waterfall.core.revisions.interface import (
    aimed_structure,
    read_revision_for,
    structure_commands,
)
from waterfall.platform.database import frozen_reading
from waterfall.platform.errors import NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import (
        KanbanCommandAvailability,
        KanbanCondition,
        NodeView,
        TaskView,
    )
    from waterfall.core.projects.interface import Viewer

NOT_FOUND = "NOT_FOUND"
TASK = "task"
NOT_STARTED = "not_started"
STARTED = "started"
COMPLETED = "completed"
EDIT_REMAINING = "edit_remaining"
# What ``edit_remaining`` of the main structure can lack, each as the contract's enumeration
# names it (``CommandCondition``): a structure's conditions are plain strings, a card names them
# typed. A condition the structure adds without a place here is refused (KeyError), not passed on.
ENTRY_CONDITIONS: Final[dict[str, KanbanCondition]] = {
    "is_contributor": "is_contributor",
    "project_in_progress": "project_in_progress",
    "revision_draft": "revision_draft",
    "no_background_task_running": "no_background_task_running",
}


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


def _entry_conditions(
    session: Session, place: Place, viewer: Viewer
) -> tuple[KanbanCondition, ...] | None:
    """Give what the entry of the remaining to commit of the main structure lacks; none if unlisted.

    As the structure lists it for the caller (``structure_commands``): absent without
    ``remaining.write`` and on a terminal project, which writes nothing; else its conditions in
    the order of the contract, the capacity first, the phase, then those of the revision.
    """
    for each in structure_commands(
        session, place.project_id, place.revision_id, place.structure_id, viewer
    ):
        if each.command == EDIT_REMAINING:
            return tuple(ENTRY_CONDITIONS[lacking] for lacking in each.missing_conditions)
    return None


def _card(
    task: TaskView, entry: tuple[KanbanCondition, ...], *, bears_lines: bool
) -> tuple[KanbanCommandAvailability, ...]:
    """Give the gestures of the card of a task: its own conditions, then those of the entry."""
    return tuple(
        replace(each, missing_conditions=(*each.missing_conditions, *entry))
        for each in progress_commands(task, bears_lines=bears_lines)
    )


def _is_card(task: TaskView) -> bool:
    """Tell whether a task is a card: a leaf, or a summary that awaits only its own lines."""
    return not task.is_summary or task.awaiting_own_lines


def startable_tasks(session: Session, project_id: UUID, viewer: Viewer) -> StartableTasks:
    """Give the tasks of a project in execution, by column (``listStartableTasks``).

    The main structure of the revision in progress, else of the last one marked, is read as a
    whole — the state a task derives, whatever the column that retains it —, and its links tell
    the tasks not started whose predecessors are all completed.

    A card holds, after the condition of its gesture, every condition of ``edit_remaining`` of the
    main structure, in the order of ``structure_commands`` (``is_contributor``,
    ``project_in_progress``, ``revision_draft``, ``no_background_task_running``): the gesture
    moves the remaining to commit as that entry does, and the 409 of ``setTaskProgress`` names the
    condition the entry names, so that a card and its refusal agree. ``viewer`` is required: the
    structure lists ``edit_remaining`` to the caller who holds ``remaining.write`` alone, so
    without it no card would hold a gesture (the core empties them).

    The nodes, the tasks that bear a line and the gestures are read in a transaction frozen at its
    first read (``frozen_reading``, #2679, #2800): a card never mixes a node with the lines or the
    revision of another moment.
    """
    with frozen_reading(session) as frozen:
        revision_id = read_revision_for(frozen, project_id, None).revision_id
        structure_id = aimed_structure(frozen, project_id, revision_id, None)
        if structure_id is None:
            raise NotFoundError(NOT_FOUND)
        place = Place(project_id, revision_id, structure_id)
        tasks = [
            (each, each.task)
            for each in list_nodes(frozen, place, NodeFilters(kinds=(TASK,))).items
            if each.task is not None
        ]
        bearing = bearing_tasks(frozen, project_id, structure_id)
        listed = _entry_conditions(frozen, place, viewer)
    states = {node.node_id: task.progress for node, task in tasks}
    not_started: list[NotStartedTask] = []
    started: list[KanbanTask] = []
    completed: list[KanbanTask] = []
    for node, task in tasks:
        if not _is_card(task):
            continue
        commands = (
            () if listed is None else _card(task, listed, bears_lines=node.node_id in bearing)
        )
        if task.progress == NOT_STARTED:
            ready = all(states[each.predecessor_id] == COMPLETED for each in node.predecessors)
            not_started.append(NotStartedTask(node, commands, ready))
        elif task.progress == STARTED:
            started.append(KanbanTask(node, commands))
        else:
            completed.append(KanbanTask(node, commands))
    return StartableTasks(tuple(not_started), tuple(started), tuple(completed))
