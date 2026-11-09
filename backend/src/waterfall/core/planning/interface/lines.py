# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the planning tells EP-07 of the lines of a task, where a line is placed, how it is written.

A line of estimate is a node of the structure, under the task that bears it (EP-06, "Ce que le
cadrage décide"): the planning owns ``node``, and gives the estimate the lines of tasks
(``lines_of``) and the task of lines (``bearers_of``, US-1500), the lineages of lines
(``lineages_of``, ``lines_of_revision``), the structures that hold nodes (``structures_of``) and
whether a revision bears one (``revision_bears``). It places a line it creates
(``create_line_node``, from ``createNode``): under a task of the structure, a milestone included
(``UNKNOWN_TASK`` otherwise, WF-PLA-0050), among its lines before its subtasks, after
``after_node_id`` or after the last line — after the last line too when the sibling named is a
subtask (#1187) —; then the facet of its kind writes its own (``FacetHooks.create``). A write of
the facet of a line (``write_facet``, ``updateEstimateLine``) is framed as any write of the tree:
its revision judged, its entry of the history opened, its structure locked and read, the line at
the counter read (412); the facet writes, the node is counted, the structure redated and its lines
priced again (``writing``).

On the main structure, a line is neither created, written, deleted nor moved under a completed
task, or from it, which is first reopened from the Kanban: 409 ``STATE_FORBIDS_OPERATION``,
``task_not_completed``, after the conditions of the revision (WF-RAE-0040, WF-DEV-0050; #1767). In
a differential, it is (WF-REV-0050, EP-08). A line a move gives another task is judged by the hooks
of its kind once placed (``FacetHooks.moved``): a role that would leave the task that receives it
without an hour is refused there (WF-PLA-0010).

The estimate asks the planning, of the nodes of its lines, their revision (``node_revisions``) and
their structure with their row number in it (``node_rows``): a subproject that lines bear is named
by them (WF-DAT-0080).

An import of an estimate writes the lines it moves, changes and creates in one write of the tree
(``write_lines``): a write a line at a time would pass through structures the file does not give —
two lines of a task that exchange their roles leave it, between the two writes, without an hour —,
which the engine refuses (WF-PLA-0010).

Declared by US-1380/L1; filled by US-1490/L3 (EP-07, "Les points d'extension"); the deletion, the
move and the places of the lines by US-1490/L4; the counters of nodes an import reads before each
of its deletions (``node_versions``) and the write of its lines (``write_lines``) by US-1550/L3.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import exists, select, update

from waterfall.core.planning.carrying import bearing, refuse_completed
from waterfall.core.planning.interface.facets import (
    FacetCreation,
    FacetWrite,
    facets,
)
from waterfall.core.planning.shaping import place as put_in_place
from waterfall.core.planning.shaping import stamp
from waterfall.core.planning.tables import Node
from waterfall.core.planning.tree import LINE, read_tree
from waterfall.core.planning.writing import writing
from waterfall.platform.errors import (
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface.facets import FacetHooks
    from waterfall.core.planning.interface.nodes import NodeCreation
    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.writing import NodesWritten, Place, Write, Writer
    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
UNKNOWN_TASK = "UNKNOWN_TASK"
NODE_NOT_SIBLING = "NODE_NOT_SIBLING"


@dataclass(frozen=True, slots=True)
class FacetChange:
    """A write of the facet of a node: the node, the counter read, and what writes the facet."""

    node_id: UUID
    lock_version: int
    apply: Callable[[FacetWrite], None]


@dataclass(frozen=True, slots=True)
class LinesWrite:
    """The lines an import writes in one write of the tree (``write_lines``, US-1550).

    ``moved`` the lines given another task, by the task that receives them, in their order;
    ``changed`` the lines whose facet is written, each with what writes it; ``created`` the lines
    created, each by its task and what its facet sends (``FacetCreation.entry``), in their order.
    """

    moved: Mapping[UUID, tuple[UUID, ...]]
    changed: Mapping[UUID, Callable[[FacetWrite], None]]
    created: tuple[tuple[UUID, object], ...]


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


def bearers_of(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> dict[UUID, UUID]:
    """Give the task that bears each line named, by line; one absent is left out (US-1500)."""
    if not node_ids:
        return {}
    rows = session.execute(
        select(Node.id, Node.parent_id).where(
            Node.project_id == project_id, Node.id.in_(list(node_ids)), Node.kind == LINE
        )
    )
    return {node_id: parent for node_id, parent in rows if parent is not None}


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


def node_versions(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> dict[UUID, int]:
    """Give the counter of each node named, as it is now, by node; one absent is left out.

    What an import sends to delete a line, read again before each deletion: a deletion moves the
    counters of the lines whose place it changes (US-1550).
    """
    if not node_ids:
        return {}
    rows = session.execute(
        select(Node.id, Node.lock_version).where(
            Node.project_id == project_id, Node.id.in_(list(node_ids))
        )
    )
    return dict(rows.all())


def structures_of(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> tuple[UUID, ...]:
    """Give the structures that hold nodes, in the order of their identifiers, which locks them."""
    if not node_ids:
        return ()
    return tuple(
        session.scalars(
            select(Node.structure_id)
            .where(Node.project_id == project_id, Node.id.in_(list(node_ids)))
            .distinct()
            .order_by(Node.structure_id)
        )
    )


def lines_of_revision(session: Session, project_id: UUID, revision_id: UUID) -> dict[UUID, UUID]:
    """Give the lines of every structure of a revision, by their lineage."""
    rows = session.execute(
        select(Node.lineage_id, Node.id).where(
            Node.project_id == project_id, Node.revision_id == revision_id, Node.kind == LINE
        )
    )
    return dict(rows.all())


def lines_of_structure(session: Session, project_id: UUID, structure_id: UUID) -> tuple[UUID, ...]:
    """Give the estimate lines of a structure, whichever task bears them, in node order."""
    return tuple(
        session.scalars(
            select(Node.id)
            .where(
                Node.project_id == project_id,
                Node.structure_id == structure_id,
                Node.kind == LINE,
            )
            .order_by(Node.id)
        )
    )


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


def judge_bearer(tree: Tree, parent: UUID | None) -> UUID:
    """Refuse a bearer that is no task of the structure (422); give it."""
    if parent is None or parent not in tree.tasks:
        fault = FieldError("/parent_id", UNKNOWN_TASK)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    return parent


def _judge_bearer(write: Write, parent: UUID | None) -> UUID:
    """Refuse a bearer that is no task of the structure (422), or completed on the main (409)."""
    bearer = judge_bearer(write.tree, parent)
    refuse_completed(write, (bearer,))
    return bearer


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


@dataclass(frozen=True, slots=True)
class LineJudged:
    """A node of another kind than the task to create, as judged on a tree: its place.

    ``parent_id`` the task that bears it, ``rank`` its rank among that task's lines, ``shifted`` the
    lines its rank moves down.
    """

    node_id: UUID
    kind: str
    parent_id: UUID
    rank: int
    shifted: tuple[UUID, ...]

    @property
    def touched(self) -> tuple[UUID, ...]:
        """Give the nodes its write touches: itself and the lines it moves down."""
        return (self.node_id, *self.shifted)


def judge_line_creation(tree: Tree, creation: NodeCreation, node_id: UUID) -> LineJudged:
    """Judge the place of a node of another kind to create on a tree: its bearer and its rank.

    Refused if its bearer is no task of the structure (``UNKNOWN_TASK``) or its place is no sibling
    (``NODE_NOT_SIBLING``); nothing is written. A paste calls it for the rows past the last node.
    """
    parent = judge_bearer(tree, creation.parent_id)
    rank = _rank(tree, creation, parent)
    shifted = tuple(each for each in tree.lines(parent) if tree.nodes[each].rank >= rank)
    return LineJudged(node_id, creation.kind, parent, rank, shifted)


def new_line_node(place: Place, act: Act, judged: LineJudged) -> Node:
    """Give the node of a line created, at its first version; nothing is written."""
    return Node(
        project_id=place.project_id,
        id=judged.node_id,
        revision_id=place.revision_id,
        structure_id=place.structure_id,
        lineage_id=judged.node_id,
        kind=judged.kind,
        parent_id=judged.parent_id,
        rank=judged.rank,
        origin_risk_id=None,
        lock_version=1,
        created_at=act.at,
        created_by=act.author,
        updated_at=act.at,
        updated_by=act.author,
    )


def write_line_node(write: Write, judged: LineJudged, facet: object) -> None:
    """Write a node ``judge_line_creation`` judged, then its facet by the hooks of its kind.

    The lines at its rank or after move down by one in one statement; the node is flushed before
    its facet is written. The facet refuses what it does not accept (422).
    """
    session, place, act = write.session, write.place, write.writer.act
    if judged.shifted:
        session.execute(
            update(Node)
            .where(Node.project_id == place.project_id, Node.id.in_(judged.shifted))
            .values(
                rank=Node.rank + 1,
                lock_version=Node.lock_version + 1,
                updated_at=act.at,
                updated_by=act.author,
            )
            .execution_options(synchronize_session=False)
        )
    session.add(new_line_node(place, act, judged))
    session.flush()
    bearer = bearing(
        session, place.project_id, write.tree, judged.parent_id, is_main=write.facts.is_main
    )
    made = FacetCreation(
        session, place.project_id, place.revision_id, judged.node_id, bearer, facet, act
    )
    facets()[judged.kind].create(made)


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
    node_id = new_id()
    with writing(session, place, writer, ("node_create", (node_id,))) as write:
        tree = write.tree
        refuse_completed(write, (judge_bearer(tree, creation.parent_id),))
        judged = judge_line_creation(tree, creation, node_id)
        write.before(judged.touched)
        write_line_node(write, judged, creation.facet)
        parent = judged.parent_id
        redated = write.redate((parent, tree.tasks[parent].label), None, (parent,))
        write.after(judged.touched)
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
        bearer = bearing(session, place.project_id, tree, parent, is_main=write.facts.is_main)
        write.before((node_id,))
        change.apply(
            FacetWrite(session, place.project_id, place.revision_id, node_id, bearer, writer.act)
        )
        stamp(node, writer.act)
        redated = write.redate((parent, tree.tasks[parent].label), None, (parent,))
        write.after((node_id,))
        return redated.written((node_id,))


def write_lines(session: Session, place: Place, lines: LinesWrite, writer: Writer) -> NodesWritten:
    """Write the lines of an import, moved, changed and created, in one write of the tree.

    Under the lock of the structure: a line it does not hold is not found (404), a task that is
    none refused (``UNKNOWN_TASK``), a line moved from a completed task of the main structure or
    written under one refused (409 ``task_not_completed``). The lines moved go after those that
    stay under the task that receives them, in the order given, the lines created after them; the
    facet of each line changed, then created, writes what it sends under its task as the moves
    leave it. Nothing is judged across lines before the end — the hooks of the kind do not judge
    the lines moved (``FacetHooks.moved``) —: the caller has judged, under the lock of the
    structure, the structure the whole write leaves, which the engine replays once (WF-PLA-0010).
    The counters are not read: the caller holds that lock since it read the structure. The entry
    of the history is named a paste, which writes several lines; an import keeps none (WF-IHM-0110).
    """
    hooks = facets()[LINE]
    created = [(new_id(), task_id, entry) for task_id, entry in lines.created]
    moving = [node for nodes in lines.moved.values() for node in nodes]
    named = tuple(dict.fromkeys((*moving, *lines.changed, *(node for node, _, _ in created))))
    with writing(session, place, writer, ("paste", named)) as write:
        tree, act = write.tree, writer.act
        lined = [*moving, *lines.changed]
        if not all(each in tree.nodes and each not in tree.tasks for each in lined):
            raise NotFoundError(NOT_FOUND)
        former = {parent for each in lined if (parent := tree.nodes[each].parent_id) is not None}
        receiving = {*lines.moved, *(task_id for _, task_id, _ in created)}
        for task_id in receiving:
            _judge_bearer(write, task_id)
        refuse_completed(write, former)
        places = _places(tree, lines.moved)
        ranks = {task_id: _last_rank(tree, task_id, places) for task_id in receiving}
        write.before(named)
        put_in_place(write, places, places)
        for node_id, apply in lines.changed.items():
            parent = tree.nodes[node_id].parent_id
            if parent is None:
                raise NotFoundError(NOT_FOUND)
            bearer = bearing(session, place.project_id, tree, parent, is_main=write.facts.is_main)
            apply(FacetWrite(session, place.project_id, place.revision_id, node_id, bearer, act))
            if node_id not in places:
                stamp(tree.nodes[node_id], act)
        for node_id, task_id, entry in created:
            ranks[task_id] += 1
            _created(write, (node_id, task_id, ranks[task_id]), hooks, entry)
        redated = write.redate(None, None, (*former, *receiving))
        write.after(named)
        return redated.written(named, former)


def _places(
    tree: Tree, moved: Mapping[UUID, tuple[UUID, ...]]
) -> dict[UUID, tuple[UUID | None, int]]:
    """Give the parent and the rank of each line moved, after the lines that stay under its task."""
    leaving = {node for nodes in moved.values() for node in nodes}
    places: dict[UUID, tuple[UUID | None, int]] = {}
    for task_id, nodes in moved.items():
        staying = [tree.nodes[each].rank for each in tree.lines(task_id) if each not in leaving]
        rank = max(staying, default=0)
        for node in nodes:
            rank += 1
            places[node] = (task_id, rank)
    return places


def _last_rank(tree: Tree, task_id: UUID, places: Mapping[UUID, tuple[UUID | None, int]]) -> int:
    """Give the last rank of the lines a task bears once the lines moved are placed."""
    staying = (tree.nodes[each].rank for each in tree.lines(task_id) if each not in places)
    arrived = (rank for parent, rank in places.values() if parent == task_id)
    return max((*staying, *arrived), default=0)


def _created(write: Write, made: tuple[UUID, UUID, int], hooks: FacetHooks, entry: object) -> None:
    """Create a line under its task at its rank, and have the hooks of its kind write its facet."""
    session, place, tree, act = write.session, write.place, write.tree, write.writer.act
    node_id, task_id, rank = made
    session.add(
        Node(
            project_id=place.project_id,
            id=node_id,
            revision_id=place.revision_id,
            structure_id=place.structure_id,
            lineage_id=node_id,
            kind=LINE,
            parent_id=task_id,
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
    bearer = bearing(session, place.project_id, tree, task_id, is_main=write.facts.is_main)
    hooks.create(
        FacetCreation(session, place.project_id, place.revision_id, node_id, bearer, entry, act)
    )
