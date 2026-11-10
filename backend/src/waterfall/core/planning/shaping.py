# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree reshaped: a node deleted, nodes moved, private to the module (US-1380/L3).

A summary that loses its last subordinate becomes a leaf in automatic mode, of the duration it
computed, in its state — a milestone if that duration is nought and it is not started, a leaf of a
day if it is — with its attachment (WF-PLA-0040, WF-PLA-0170). A move places each node it moves
under its parent after the sibling named, by kind: the lines of a task precede its subtasks
(``NodeMove``, #1187); the ranks of the siblings change only where the nodes placed need it, each
change parked first so that the rank stays unique under its parent at every statement.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.tables import Node, TrackingEntry
from waterfall.core.planning.tree import LINE, TASK
from waterfall.core.planning.views import COMPLETED, STARTED, state_of
from waterfall.platform.errors import FieldError, UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.writing import Write
    from waterfall.platform.audit import Act

VALIDATION_FAILED = "VALIDATION_FAILED"
NODE_NOT_SIBLING = "NODE_NOT_SIBLING"
AUTOMATIC = "automatic"
# Where a rank is parked while the siblings exchange theirs: above any rank a structure holds.
PARKED = 1_000_000_000


@dataclass(frozen=True, slots=True)
class Placing:
    """Where a move puts its nodes: under a parent, after a sibling — absent, after the last."""

    node_ids: tuple[UUID, ...]
    parent_id: UUID | None
    after_node_id: UUID | None
    after_given: bool


def stamp(node: Node, act: Act) -> None:
    """Count a write of a node: its version advanced, its author and its instant."""
    node.lock_version += 1
    node.updated_at = act.at
    node.updated_by = act.author


def emptied(tree: Tree, parent_id: UUID) -> None:
    """Make a summary that loses its last subordinate a leaf, in its state (WF-PLA-0040).

    Its state is the one its subordinates gave it, read on the tree before the write; it keeps the
    duration it computed, a day if that is nought and it is started — a milestone is never
    started (WF-PLA-0050) —, in automatic mode, and its attachment.
    """
    state = state_of(tree, parent_id)
    task = tree.tasks[parent_id]
    task.progress = state.progress
    task.started_on = state.started_on
    task.completed_on = state.completed_on
    task.scheduling_mode = AUTOMATIC
    if task.duration_value == 0 and state.progress == STARTED:
        task.duration_value, task.duration_unit = Decimal(1), "d"


def closed_above(tree: Tree, parent_id: UUID | None) -> tuple[UUID, ...]:
    """Give the tasks, a task and the summaries above it, whose facet keeps a completion.

    A task not completed under ``parent_id`` — created or moved there — makes it and every
    summary above it not completed: what their facet keeps of the completion — the state and the
    day the last own line set to nought gave (``own_lines``) — is stale, and a later completion
    must not read it (WF-PLA-0040, WF-PLA-0130; #2769).
    """
    if parent_id is None:
        return ()
    return tuple(
        each
        for each in (parent_id, *tree.ancestors(parent_id))
        if tree.tasks[each].progress == COMPLETED
    )


def reopened(tree: Tree, node_ids: Collection[UUID], act: Act) -> None:
    """Put back to started the tasks whose completion is stale, and clear the day they closed at.

    Written once: a task whose facet keeps no completion any more is left as it is.
    """
    for each in node_ids:
        task = tree.tasks[each]
        if task.progress == COMPLETED:
            task.progress, task.completed_on = STARTED, None
            stamp(tree.nodes[each], act)


def deleted(session: Session, project_id: UUID, tree: Tree, node_ids: list[UUID]) -> None:
    """Delete nodes, their facets, and the inscriptions of lineages no node holds any more.

    The facets of the later kinds go by their hooks; the facet task, the links and the children
    follow the nodes by the keys that cascade inside a current revision. An inscription follows
    its lineage, which a marked revision may still hold (WF-PLA-0060). The structure is locked by
    the caller, which read ``tree`` under that lock.
    """
    for kind, hooks in facets().items():
        held = [each for each in node_ids if tree.nodes[each].kind == kind]
        if held:
            hooks.delete(session, project_id, held)
    lineages = {tree.nodes[each].lineage_id for each in node_ids if each in tree.tasks}
    for each in node_ids:
        for row in (tree.nodes[each], tree.tasks.get(each)):
            if row is not None:
                session.expunge(row)
    session.execute(
        delete(Node)
        .where(Node.project_id == project_id, Node.id.in_(node_ids))
        .execution_options(synchronize_session=False)
    )
    kept = set(
        session.scalars(
            select(Node.lineage_id).where(
                Node.project_id == project_id, Node.lineage_id.in_(lineages)
            )
        )
    )
    gone = lineages - kept
    if gone:
        session.execute(
            delete(TrackingEntry)
            .where(TrackingEntry.project_id == project_id, TrackingEntry.lineage_id.in_(gone))
            .execution_options(synchronize_session=False)
        )


def _not_sibling() -> UnprocessableError:
    return UnprocessableError(
        VALIDATION_FAILED, fields=(FieldError("/after_node_id", NODE_NOT_SIBLING),)
    )


def _index(placing: Placing, kind: str, siblings: list[UUID]) -> int:
    """Give where the nodes of a kind moved go among their siblings of that kind (#1187).

    Absent, after the last; null, at their head; after a sibling of the kind, after it; after a
    sibling of the other kind, at the boundary — a task at the head of the subtasks, a line after
    the last line.
    """
    after = placing.after_node_id
    if not placing.after_given:
        return len(siblings)
    if after is None:
        return 0
    if after in siblings:
        return siblings.index(after) + 1
    return 0 if kind == TASK else len(siblings)


def judge_place(tree: Tree, placing: Placing) -> None:
    """Refuse a sibling named that is none under the parent: moved, of another, unknown."""
    after = placing.after_node_id
    if not placing.after_given or after is None:
        return
    node = tree.nodes.get(after)
    if node is None or after in placing.node_ids or node.parent_id != placing.parent_id:
        raise _not_sibling()


def placed(tree: Tree, placing: Placing) -> dict[UUID, tuple[UUID | None, int]]:
    """Give the parent and the rank of every node whose place a move changes.

    The nodes of each kind go together, in the order sent; a sibling keeps its rank unless a node
    placed before it takes it, then it follows.
    """
    moved = set(placing.node_ids)
    parent = placing.parent_id
    changes: dict[UUID, tuple[UUID | None, int]] = {}
    for kind in (LINE, TASK):
        coming = [each for each in placing.node_ids if tree.nodes[each].kind == kind]
        if not coming:
            continue
        siblings = [
            each
            for each in tree.children.get(parent, [])
            if tree.nodes[each].kind == kind and each not in moved
        ]
        at = _index(placing, kind, siblings)
        rank = 0
        for each in [*siblings[:at], *coming, *siblings[at:]]:
            node = tree.nodes[each]
            rank = rank + 1 if each in moved else max(node.rank, rank + 1)
            if (node.parent_id, node.rank) != (parent, rank):
                changes[each] = (parent, rank)
    return changes


def place(
    write: Write, changes: dict[UUID, tuple[UUID | None, int]], stamped: Collection[UUID]
) -> None:
    """Write the places a move gives, every rank changed parked first, the nodes stamped."""
    session, tree, act = write.session, write.tree, write.writer.act
    for turn, node_id in enumerate(changes, start=1):
        tree.nodes[node_id].rank = PARKED + turn
    session.flush()
    for node_id, (parent, rank) in changes.items():
        node = tree.nodes[node_id]
        node.parent_id, node.rank = parent, rank
    for node_id in stamped:
        stamp(tree.nodes[node_id], act)
    session.flush()
