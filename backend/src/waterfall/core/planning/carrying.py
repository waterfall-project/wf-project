# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task that carries a node of another kind, as a write judges it, private to the module.

What the writes of the lines (``interface.lines``) and the deletion and the move of the tree
(``interface.nodes``) share, kept here so that neither file offers it to the other modules: a task
told to the facet of a node it bears (``bearing``); a line neither written, deleted nor moved under
a completed task of the main structure, or from it, which is first reopened from the Kanban (409
``task_not_completed``, WF-RAE-0040, WF-DEV-0050; #1767), what a differential permits (EP-08); the
lines a move gives another task judged by the hooks of their kind once placed (``FacetHooks.moved``,
WF-PLA-0010).

Written by US-1490/L4, ``bearing`` moved from ``interface.lines`` (US-1490/L3).
"""

from typing import TYPE_CHECKING

from waterfall.core.planning.interface.facets import BearingTask, calendar_of, facets
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.views import COMPLETED, state_of
from waterfall.platform.errors import ConflictError

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.writing import Write

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
TASK_NOT_COMPLETED = "task_not_completed"


def bearing(
    session: Session, project_id: UUID, tree: Tree, task_id: UUID, *, is_main: bool
) -> BearingTask:
    """Give a task of a tree as the facet of a node it bears is told of it."""
    task = tree.tasks[task_id]
    return BearingTask(
        task_id,
        tree.nodes[task_id].revision_id,
        task.label,
        WorkInstant(task.start_date, task.start_hours),
        WorkInstant(task.finish_date, task.finish_hours),
        calendar_of(session, project_id, task_id).calendar.week,
        state_of(tree, task_id).progress,
        is_main,
    )


def refuse_completed(write: Write, task_ids: Iterable[UUID | None]) -> None:
    """Refuse a write of a line under one of these tasks completed, on the main structure (409)."""
    tree = write.tree
    if not write.facts.is_main:
        return
    for each in task_ids:
        if each is not None and each in tree.tasks and state_of(tree, each).progress == COMPLETED:
            raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": TASK_NOT_COMPLETED})


def judge_lines_moved(write: Write, node_ids: Collection[UUID], parent: UUID | None) -> None:
    """Refuse a move of lines to a completed task or from one, on the main structure (409).

    ``node_ids`` the nodes the move places, ``parent`` the task that receives them; the tasks moved
    take their lines with them, which change no bearer.
    """
    tree = write.tree
    lines = [each for each in node_ids if each not in tree.tasks]
    if lines:
        refuse_completed(write, (parent, *(tree.nodes[each].parent_id for each in lines)))


def judge_facets_moved(write: Write, node_ids: Collection[UUID]) -> None:
    """Have the hooks of each kind judge the nodes a move gave another task, once placed.

    ``node_ids`` those nodes, under their new task in the tree written: each kind is handed its
    own, in the order of the plan read, with the task that now bears them.
    """
    if not node_ids:
        return
    session, tree, project_id = write.session, write.tree, write.place.project_id
    ordered = sorted(node_ids, key=tree.row_number.__getitem__)
    for kind, hooks in facets().items():
        held: dict[UUID, BearingTask] = {}
        for each in ordered:
            parent = tree.nodes[each].parent_id
            if tree.nodes[each].kind == kind and parent is not None:
                held[each] = bearing(session, project_id, tree, parent, is_main=write.facts.is_main)
        if held:
            hooks.moved(session, project_id, held)
