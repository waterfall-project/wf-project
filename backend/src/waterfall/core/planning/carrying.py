# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task that carries a node of another kind, as a write judges it, private to the module.

What the writes of the lines (``interface.lines``) and the deletion and the move of the tree
(``interface.nodes``) share, kept here so that neither file offers it to the other modules: a task
told to the facet of a node it bears (``bearing``); a line neither written, deleted nor moved under
a completed task of the main structure, or from it, which is first reopened from the Kanban (409
``task_not_completed``, WF-RAE-0040, WF-DEV-0050; #1767), what a differential permits (EP-08); the
lines a move gives another task judged by the hooks of their kind once placed (``FacetHooks.moved``,
WF-PLA-0010); the provision lines a deletion does not take with their task, which pass to the
parent of the task deleted (``judge_provisions``, ``carry_provisions``; US-2580/L1).

Written by US-1490/L4, ``bearing`` moved from ``interface.lines`` (US-1490/L3).
"""

from typing import TYPE_CHECKING

from waterfall.core.planning.interface.facets import BearingTask, calendar_of, facets
from waterfall.core.planning.provisioning import (
    first_left,
    lines_reported,
    owners_named,
    provision_moves,
)
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.shaping import Placing, place, placed
from waterfall.core.planning.views import COMPLETED, state_of
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.tree import NodeColumns, TaskColumns, Tree
    from waterfall.core.planning.writing import Write

TASK_NOT_COMPLETED = "task_not_completed"
AT_LEAST_ONE_TASK = "at_least_one_task"


def bearing[N: NodeColumns, T: TaskColumns](
    session: Session, project_id: UUID, tree: Tree[N, T], task_id: UUID, *, is_main: bool
) -> BearingTask:
    """Give a task of a tree as the facet of a node it bears is told of it."""
    return borne(tree, task_id, calendar_of(session, project_id, task_id), is_main=is_main)


def borne[N: NodeColumns, T: TaskColumns](
    tree: Tree[N, T], task_id: UUID, calendar: Applicable, *, is_main: bool
) -> BearingTask:
    """Give a task of a tree as ``bearing`` does, its applicable calendar read already.

    For a write that tells many tasks at once, their calendars read together (``calendars_of``).
    """
    task = tree.tasks[task_id]
    return BearingTask(
        task_id,
        tree.nodes[task_id].revision_id,
        task.label,
        WorkInstant(task.start_date, task.start_hours),
        WorkInstant(task.finish_date, task.finish_hours),
        calendar.calendar.week,
        state_of(tree, task_id).progress,
        is_main,
    )


def refuse_completed(write: Write, task_ids: Iterable[UUID | None]) -> None:
    """Refuse a write of a line under one of these tasks completed, on the main structure (409)."""
    if write.facts.is_main:
        refuse_completed_on(write.tree, task_ids)


def refuse_completed_on[N: NodeColumns, T: TaskColumns](
    tree: Tree[N, T], task_ids: Iterable[UUID | None]
) -> None:
    """Refuse a write of a line under one of these tasks completed, on a tree of the main (409).

    What ``refuse_completed`` judges, on the tree a write holds: objects of the session, or rows
    for a write whose columns are all inert (``read_inert``).
    """
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
        # A completed task freezes its lines on the main structure, their rank included: a line
        # reordered under its own completed task is refused as one moved to it.
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


def judge_provisions(write: Write, removed: Iterable[UUID]) -> dict[UUID, UUID]:
    """Give the task each provision line under the nodes removed passes to, by line (WF-PLA-0070).

    The parent of the node deleted, the first task of the first level left for a task of the first
    level — the removal of the last task of a main structure that bears a provision is refused
    instead (409 ``at_least_one_task``, ``params.risks`` naming each risk whose provision it would
    carry, WF-RIS-0010). Nothing is written.
    """
    tree, where = write.tree, write.place
    gone = list(removed)
    moves = provision_moves(tree, gone, first_left(tree, gone))
    stranded = [line for line, task in moves.items() if task is None]
    if stranded:
        owners = owners_named(write.session, where.project_id, where.revision_id, stranded)
        named = [{"risk_id": str(each.risk_id), "label": each.label} for each in owners]
        params = {"missing_condition": AT_LEAST_ONE_TASK, "risks": named}
        raise ConflictError(STATE_FORBIDS_OPERATION, params)
    return {line: task for line, task in moves.items() if task is not None}


def carry_provisions(write: Write, moves: dict[UUID, UUID]) -> None:
    """Place the provision lines of ``moves`` under their new task, after its lines; tell the risks.

    Each line is stamped, its place written before the nodes removed are deleted — the risk holds
    its line by a key that refuses a deletion — and the risks told once all are placed.
    """
    tree, where = write.tree, write.place
    changes: dict[UUID, tuple[UUID | None, int]] = {}
    for task in dict.fromkeys(moves.values()):
        lines = tuple(line for line, target in moves.items() if target == task)
        changes.update(placed(tree, Placing(lines, task, None, after_given=False)))
    if changes:
        place(write, changes, tuple(moves))
        lines_reported(write.session, where.project_id, where.revision_id, tuple(moves))
