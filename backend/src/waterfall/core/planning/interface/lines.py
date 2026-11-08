# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning tells EP-07 of the lines of a task, where a line is placed, how it is written.

A line of estimate is a node of the structure, under the task that bears it (EP-06, "Ce que le
cadrage décide"): the planning owns ``node``, and gives the estimate the lines of tasks
(``lines_of``), the lineages of lines (``lineages_of``, ``lines_of_revision``) and whether a
revision bears one (``revision_bears``). It places a line it creates (``create_line_node``, from
``createNode``): under a task of the structure, a milestone included (``UNKNOWN_TASK`` otherwise,
WF-PLA-0050), among its lines before its subtasks, after ``after_node_id`` or after the last line —
after the last line too when the sibling named is a subtask (#1187) —; then the facet of its kind
writes its own (``FacetHooks.create``). A write of the facet of a line (``write_facet``,
``updateEstimateLine``) is framed as any write of the tree: its revision judged, its entry of the
history opened, its structure locked and read, the line at the counter read (412); the facet
writes, the node is counted, the structure redated and its lines priced again (``writing``).

On the main structure, a line is neither created, written, deleted nor moved under a completed
task, or from it, which is first reopened from the Kanban: 409 ``STATE_FORBIDS_OPERATION``,
``task_not_completed``, after the conditions of the revision (WF-RAE-0040, WF-DEV-0050; #1767). In
a differential, it is (WF-REV-0050, EP-08). A line a move gives another task is judged by the hooks
of its kind once placed (``FacetHooks.moved``): a role that would leave the task that receives it
without an hour is refused there (WF-PLA-0010).

The estimate asks the planning, of the nodes of its lines, their revision (``node_revisions``) and
their structure with their row number in it (``node_rows``): a subproject that lines bear is named
by them (WF-DAT-0080).

Declared by US-1380/L1; filled by US-1490/L3 (EP-07, "Les points d'extension"); the deletion, the
move and the places of the lines by US-1490/L4.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import exists, select, update

from waterfall.core.planning.interface.facets import (
    BearingTask,
    FacetCreation,
    FacetWrite,
    calendar_of,
    facets,
)
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.shaping import stamp
from waterfall.core.planning.tables import Node
from waterfall.core.planning.tree import LINE, read_tree
from waterfall.core.planning.views import COMPLETED, state_of
from waterfall.core.planning.writing import writing
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface.nodes import NodeCreation
    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.writing import NodesWritten, Place, Write, Writer

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
UNKNOWN_TASK = "UNKNOWN_TASK"
NODE_NOT_SIBLING = "NODE_NOT_SIBLING"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
TASK_NOT_COMPLETED = "task_not_completed"


@dataclass(frozen=True, slots=True)
class FacetChange:
    """A write of the facet of a node: the node, the counter read, and what writes the facet."""

    node_id: UUID
    lock_version: int
    apply: Callable[[FacetWrite], None]


def lines_of(
    session: Session, project_id: UUID, task_ids: Collection[UUID]
) -> dict[UUID, tuple[UUID, ...]]:
    """Give the lines each task named bears, in their order; none for a task without any."""
    found: dict[UUID, list[UUID]] = {task_id: [] for task_id in task_ids}
    if not task_ids:
        return {}
    rows = session.execute(
        select(Node.parent_id, Node.id)
        .where(Node.project_id == project_id, Node.parent_id.in_(list(task_ids)), Node.kind == LINE)
        .order_by(Node.rank)
    )
    for parent, node_id in rows:
        if parent is not None:
            found[parent].append(node_id)
    return {task_id: tuple(lines) for task_id, lines in found.items()}


def lineages_of(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> dict[UUID, UUID]:
    """Give the lineage of each node named, by node; one absent is left out."""
    if not node_ids:
        return {}
    rows = session.execute(
        select(Node.id, Node.lineage_id).where(
            Node.project_id == project_id, Node.id.in_(list(node_ids))
        )
    )
    return dict(rows.all())


def lines_of_revision(session: Session, project_id: UUID, revision_id: UUID) -> dict[UUID, UUID]:
    """Give the lines of every structure of a revision, by their lineage."""
    rows = session.execute(
        select(Node.lineage_id, Node.id).where(
            Node.project_id == project_id, Node.revision_id == revision_id, Node.kind == LINE
        )
    )
    return dict(rows.all())


def revision_bears(session: Session, revision_id: UUID, kind: str) -> bool:
    """Tell whether a structure of a revision holds a node of a kind."""
    return bool(
        session.scalar(select(exists().where(Node.revision_id == revision_id, Node.kind == kind)))
    )


@dataclass(frozen=True, slots=True)
class NodeRow:
    """Where a node stands: its structure, and its row number in the whole of it (WF-PLA-0080)."""

    structure_id: UUID
    row_number: int


def node_revisions(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> dict[UUID, UUID]:
    """Give the revision of each node named, by node; one absent is left out."""
    if not node_ids:
        return {}
    rows = session.execute(
        select(Node.id, Node.revision_id).where(
            Node.project_id == project_id, Node.id.in_(list(node_ids))
        )
    )
    return dict(rows.all())


def node_rows(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> dict[UUID, NodeRow]:
    """Give the structure and the row number of each node named; one absent is left out.

    Each structure that holds one is read whole, once: a row number counts every node above.
    """
    if not node_ids:
        return {}
    held = session.execute(
        select(Node.id, Node.structure_id).where(
            Node.project_id == project_id, Node.id.in_(list(node_ids))
        )
    ).all()
    found: dict[UUID, NodeRow] = {}
    for structure_id in sorted({structure for _, structure in held}):
        numbers = read_tree(session, project_id, structure_id).row_number
        found.update(
            {
                node_id: NodeRow(structure_id, numbers[node_id])
                for node_id, structure in held
                if structure == structure_id
            }
        )
    return found


def _bearing(
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


def _judge_bearer(write: Write, parent: UUID | None) -> UUID:
    """Refuse a bearer that is no task of the structure (422), or completed on the main (409)."""
    tree = write.tree
    if parent is None or parent not in tree.tasks:
        fault = FieldError("/parent_id", UNKNOWN_TASK)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    refuse_completed(write, (parent,))
    return parent


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
                held[each] = _bearing(
                    session, project_id, tree, parent, is_main=write.facts.is_main
                )
        if held:
            hooks.moved(session, project_id, held)


def _rank(tree: Tree, creation: NodeCreation, parent: UUID) -> int:
    """Give the rank of a line created among the lines of its task (#1183, #1187).

    After the last of them by default, and after a subtask of the same task; at their head after
    ``null``; after its sibling otherwise. Another node is refused (``NODE_NOT_SIBLING``).
    """
    siblings = tree.lines(parent)
    last = max((tree.nodes[each].rank for each in siblings), default=0) + 1
    if not creation.after_given:
        return last
    after = creation.after_node_id
    if after is None:
        return 1
    if after in siblings:
        return tree.nodes[after].rank + 1
    if after in tree.tasks and tree.nodes[after].parent_id == parent:
        return last
    raise UnprocessableError(
        VALIDATION_FAILED, fields=(FieldError("/after_node_id", NODE_NOT_SIBLING),)
    )


def create_line_node(
    session: Session, place: Place, creation: NodeCreation, writer: Writer
) -> NodesWritten:
    """Create a node of another kind than the task, and its facet by its hooks (``createNode``).

    Judged under the lock of the structure: its bearer (``UNKNOWN_TASK``, ``task_not_completed`` on
    the main structure), its place (``NODE_NOT_SIBLING``), then its facet, by the hooks of its kind,
    which refuse what they do not accept (422); nothing is created then. The structure is redated —
    a line of a role changes the calendar of its task (WF-PLA-0010) — and the lines of its task
    priced again.
    """
    hooks = facets()[creation.kind]
    node_id = new_id()
    with writing(session, place, writer, ("node_create", (node_id,))) as write:
        tree, act = write.tree, writer.act
        parent = _judge_bearer(write, creation.parent_id)
        rank = _rank(tree, creation, parent)
        shifted = [each for each in tree.lines(parent) if tree.nodes[each].rank >= rank]
        touched = (node_id, *shifted)
        write.before(touched)
        bearer = _bearing(session, place.project_id, tree, parent, is_main=write.facts.is_main)
        if shifted:
            session.execute(
                update(Node)
                .where(Node.project_id == place.project_id, Node.id.in_(shifted))
                .values(
                    rank=Node.rank + 1,
                    lock_version=Node.lock_version + 1,
                    updated_at=act.at,
                    updated_by=act.author,
                )
                .execution_options(synchronize_session=False)
            )
        session.add(
            Node(
                project_id=place.project_id,
                id=node_id,
                revision_id=place.revision_id,
                structure_id=place.structure_id,
                lineage_id=node_id,
                kind=creation.kind,
                parent_id=parent,
                rank=rank,
                origin_risk_id=None,
                lock_version=1,
                created_at=act.at,
                created_by=act.author,
                updated_at=act.at,
                updated_by=act.author,
            )
        )
        session.flush()
        made = FacetCreation(
            session, place.project_id, place.revision_id, node_id, bearer, creation.facet, act
        )
        hooks.create(made)
        redated = write.redate((parent, tree.tasks[parent].label), None, (parent,))
        write.after(touched)
        return redated.written((node_id,))


def write_facet(
    session: Session, place: Place, change: FacetChange, writer: Writer
) -> NodesWritten:
    """Write the facet of a node of another kind, at the counter read (``updateEstimateLine``).

    Under the lock of the structure: refused if the structure holds no such node (404), at another
    version than the one read (412), under a completed task of the main structure (409
    ``task_not_completed``); then the facet writes what is sent (``change.apply``), refusing what
    it does not accept (422). The node is counted, the structure redated and the lines of its task
    priced again.
    """
    node_id = change.node_id
    with writing(session, place, writer, ("cell", (node_id,))) as write:
        tree = write.tree
        node = tree.nodes.get(node_id)
        if node is None or node_id in tree.tasks or node.parent_id is None:
            raise NotFoundError(NOT_FOUND)
        if node.lock_version != change.lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version}
            )
        parent = _judge_bearer(write, node.parent_id)
        bearer = _bearing(session, place.project_id, tree, parent, is_main=write.facts.is_main)
        write.before((node_id,))
        change.apply(
            FacetWrite(session, place.project_id, place.revision_id, node_id, bearer, writer.act)
        )
        stamp(node, writer.act)
        redated = write.redate((parent, tree.tasks[parent].label), None, (parent,))
        write.after((node_id,))
        return redated.written((node_id,))
