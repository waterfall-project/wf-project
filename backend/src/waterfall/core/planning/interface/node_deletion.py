# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The deletion of a node and its subtree (``deleteNode``, US-1380/L3).

Split from ``nodes`` to keep it under its bound: the provision lines under the subtree pass to the
parent (US-2580/L1), the rest is the deletion as it was.
"""

from typing import TYPE_CHECKING

from waterfall.core.planning.carrying import (
    carry_provisions,
    judge_provisions,
    refuse_completed,
    refuse_provision,
)
from waterfall.core.planning.interface.nodes import TASK_NOT_STARTED
from waterfall.core.planning.shaping import (
    closed_again,
    completed_again,
    deleted,
    emptied,
    stamp,
)
from waterfall.core.planning.views import NOT_STARTED, state_of
from waterfall.core.planning.writing import NodesWritten, Place, Writer, writing
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    STATE_FORBIDS_OPERATION,
    ConflictError,
    NotFoundError,
    PreconditionFailedError,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def delete_node(
    session: Session, place: Place, node_id: UUID, lock_version: int, writer: Writer
) -> NodesWritten:
    """Delete a node and its subtree, and give the nodes written (``deleteNode``).

    Under the lock of the structure: refused if the structure does not hold the node (404), at
    another version than the one read (412), for a task started or completed, or a summary one of
    whose subordinates is, but in the own estimate of a risk, which abandons it whatever its state
    (409 ``task_not_started``, WF-PLA-0070; EP-30), for a line of a completed task
    of the main structure (409 ``task_not_completed``, WF-RAE-0040; #1767), then for a provision
    line of the main structure, which its risk alone writes (409 ``line_not_provision``,
    ``params.risks``; #4007). The subtree goes, its lines, its links and the inscriptions of its
    lineages with it (WF-DAT-0090); a summary left
    without subordinate becomes a leaf in its state (WF-PLA-0040) and is given back among the
    ancestors, with the tasks the links taken away redate — and the task a line leaves, whose
    calendar may change (WF-PLA-0010) — and the totals without them; a summary it leaves completed
    again reads the zeroing of its lines (``closed_again``, #2803). The provision lines under the
    subtree pass to the parent of the node, the first task of the first level left for a task of
    the first level, and are the ``nodes`` given (``judge_provisions``, WF-PLA-0070).
    """
    with writing(session, place, writer, ("node_delete", (node_id,))) as write:
        tree = write.tree
        if node_id not in tree.nodes:
            raise NotFoundError(NOT_FOUND)
        node = tree.nodes[node_id]
        if node.lock_version != lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version}
            )
        started = node_id in tree.tasks and state_of(tree, node_id).progress != NOT_STARTED
        # The own estimate of a risk abandons a task whatever its state: its occurrence completes
        # it at its budget (EP-30, "Une désignation sur une tâche terminée s'applique").
        if started and not write.facts.is_own_estimate:
            raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": TASK_NOT_STARTED})
        parent = node.parent_id
        if node_id not in tree.tasks:
            refuse_completed(write, (parent,))
            refuse_provision(write, node_id)
        former = () if parent is None else (parent, *tree.ancestors(parent))
        subtree = list(tree.subtree(node_id))
        carried = judge_provisions(write, subtree)
        left_bare = parent is not None and tree.subtasks(parent) == [node_id]
        again = closed_again(session, place.project_id, tree, (node_id,))
        bare = (parent,) if left_bare and parent is not None else ()
        touched = (*subtree, *bare, *again)
        write.before(touched)
        if left_bare and parent is not None:
            emptied(tree, parent)
            stamp(tree.nodes[parent], writer.act)
        completed_again(tree, again, writer.act)
        carry_provisions(write, carried)
        deleted(session, place.project_id, tree, [each for each in subtree if each not in carried])
        redated = write.redate(None)
        write.after(touched)
        return redated.written(tuple(carried), former)
