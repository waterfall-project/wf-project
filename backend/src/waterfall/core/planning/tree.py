# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of a structure as the planning reads it, private to the module (EP-06, "Modules").

The nodes of a structure, each with its facet task if it is one, ordered as the plan reads them:
under each parent, its lines first, then its subtasks, each kind by its rank (``Node.rank``);
the whole depth first. ``row_number``, ``level`` and ``position`` are computed here, on the whole
structure, whatever a reading returns of it (``Node.row_number``, WF-PLA-0080); a tree of the tasks
alone, read without the nodes they bear (``read_task_rows``), is numbered from how many each bears
(``numbered``, US-2280). A task is a
summary when it bears a subtask (WF-PLA-0040), a milestone when it is a leaf of nought duration
(WF-PLA-0050); its lines do not make it a summary. The lines of provision of the structure are read
with the tree (``provisions``), which the estimate tells by their category
(``FacetHooks.provisions``) and the planning never judges by the risk a node came from (EP-08, "Ce
qui reconnaît une ligne de provision"): a line an occurrence merged is work. The summaries an own
line holds open are read with the tree too (``held``, US-1590/L1): those whose subordinates are all
completed and one of whose
lines, the provisions left out, keeps a remaining to commit, which the estimate tells
(``register_open_lines``); a summary is completed only once none does (WF-PLA-0040), on every path
that derives its state.

Two paths read a tree (US-2220, EP-26, "La lecture d'une structure"). A write reads it as objects
of the session (``read_tree``, ``read_links``), which it changes and flushes; a reading that writes
nothing reads the same columns as rows (``read_rows``, ``read_link_rows``), which cost a fraction of
an object of the session: a structure read whole holds six thousand nodes. The tree is generic in
what it holds of a node and of a task (``NodeColumns``, ``TaskColumns``), the objects by default;
a test holds the two paths to the same reading on the witness. A write reads its tree once, under
the lock: the replay that follows it is handed that tree brought to what the write made of it, the
place and the counter of each node read as rows, the nodes written past their objects read again
(``reshaped``, US-2250). A write whose columns are all inert reads its structure as rows, the nodes
it writes alone as objects (``read_inert``, US-2250/L2).
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple
from uuid import UUID

from sqlalchemy import and_, inspect, or_, select

from waterfall.core.planning.interface.open_lines import held_open
from waterfall.core.planning.tables import Node, Task, TaskLink, TrackingEntry
from waterfall.core.planning.tallying import provision_lines
from waterfall.platform.database import among

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping
    from datetime import date
    from decimal import Decimal

    from sqlalchemy.orm import Session

TASK = "task"
LINE = "estimate_line"
COMPLETED = "completed"
# What an expired object holds of an attribute: nothing, which no row matches.
_EXPIRED = object()


class NodeRow(NamedTuple):
    """A node as a reading reads it, its columns alone (``read_rows``)."""

    id: UUID
    revision_id: UUID
    lineage_id: UUID
    kind: str
    parent_id: UUID | None
    rank: int
    origin_risk_id: UUID | None
    lock_version: int


class TaskRow(NamedTuple):
    """The facet of a task as a reading reads it, its columns alone (``read_rows``)."""

    label: str
    description: str | None
    scheduling_mode: str
    duration_value: Decimal
    duration_unit: str
    start_date: date
    start_hours: Decimal
    finish_date: date
    finish_hours: Decimal
    progress: str
    started_on: date | None
    completed_on: date | None
    external_id: str | None
    order_item_id: UUID | None
    work_package_id: UUID | None
    total_float_days: Decimal | None
    is_critical: bool


class LinkRow(NamedTuple):
    """A link as a reading reads it, its columns alone (``read_link_rows``)."""

    predecessor_id: UUID
    successor_id: UUID
    link_type: str
    lag_value: Decimal
    lag_unit: str
    in_conflict: bool


# What a tree holds of a node, of a task and of a link: objects of the session, or rows.
type NodeColumns = Node | NodeRow
type TaskColumns = Task | TaskRow
type LinkColumns = TaskLink | LinkRow

# The columns of each row, in the order of its fields.
_NODE_COLUMNS = (
    Node.id,
    Node.revision_id,
    Node.lineage_id,
    Node.kind,
    Node.parent_id,
    Node.rank,
    Node.origin_risk_id,
    Node.lock_version,
)
_TASK_COLUMNS = (
    Task.label,
    Task.description,
    Task.scheduling_mode,
    Task.duration_value,
    Task.duration_unit,
    Task.start_date,
    Task.start_hours,
    Task.finish_date,
    Task.finish_hours,
    Task.progress,
    Task.started_on,
    Task.completed_on,
    Task.external_id,
    Task.order_item_id,
    Task.work_package_id,
    Task.total_float_days,
    Task.is_critical,
)
_LINK_COLUMNS = (
    TaskLink.predecessor_id,
    TaskLink.successor_id,
    TaskLink.link_type,
    TaskLink.lag_value,
    TaskLink.lag_unit,
    TaskLink.in_conflict,
)


@dataclass(slots=True)
class Tree[N: NodeColumns = Node, T: TaskColumns = Task]:
    """A structure read whole: its nodes, their facet task, and the order of the plan.

    ``held`` the summaries an own line holds open as the tree is read (``read_tree``),
    ``provisions`` its lines of provision; a tree built from another's nodes carries that one's.
    Its nodes and tasks are objects of the session, or rows for a reading (``read_rows``).
    """

    nodes: dict[UUID, N]
    tasks: dict[UUID, T]
    children: dict[UUID | None, list[UUID]] = field(default_factory=dict[UUID | None, list[UUID]])
    order: list[UUID] = field(default_factory=list[UUID])
    row_number: dict[UUID, int] = field(default_factory=dict[UUID, int])
    level: dict[UUID, int] = field(default_factory=dict[UUID, int])
    position: dict[UUID, int] = field(default_factory=dict[UUID, int])
    held: frozenset[UUID] = frozenset()
    provisions: frozenset[UUID] = frozenset()

    def with_nodes(self, nodes: dict[UUID, N], tasks: dict[UUID, T]) -> Tree[N, T]:
        """Give the tree of other nodes and tasks, which holds what this one's lines tell."""
        return Tree(nodes, tasks, held=self.held, provisions=self.provisions)

    def __post_init__(self) -> None:
        """Order the nodes: under each parent, the lines then the subtasks, each by its rank."""
        for node in sorted(self.nodes.values(), key=lambda each: (each.kind == TASK, each.rank)):
            self.children.setdefault(node.parent_id, []).append(node.id)
        for place, node_id in enumerate(self.children.get(None, []), start=1):
            self.position[node_id] = place
        pending = [(node_id, 1) for node_id in reversed(self.children.get(None, []))]
        while pending:
            node_id, level = pending.pop()
            self.order.append(node_id)
            self.row_number[node_id] = len(self.order)
            self.level[node_id] = level
            below = self.children.get(node_id, [])
            for place, child in enumerate(below, start=1):
                self.position[child] = place
            pending.extend((child, level + 1) for child in reversed(below))

    def subtasks(self, node_id: UUID | None) -> list[UUID]:
        """Give the subtasks of a task — the tasks of the first level for ``None`` —, in order."""
        return [child for child in self.children.get(node_id, []) if child in self.tasks]

    def lines(self, node_id: UUID) -> list[UUID]:
        """Give the lines a task bears, in their order."""
        return [child for child in self.children.get(node_id, []) if child not in self.tasks]

    def own_lines(self, node_id: UUID) -> list[UUID]:
        """Give the lines a task bears besides the provisions, in their order (WF-PLA-0040)."""
        return [each for each in self.lines(node_id) if each not in self.provisions]

    def is_summary(self, node_id: UUID) -> bool:
        """Tell whether a task bears a subtask: its dates, duration and state are derived."""
        return bool(self.subtasks(node_id))

    def is_milestone(self, node_id: UUID) -> bool:
        """Tell whether a task is a leaf of nought duration (WF-PLA-0050)."""
        task = self.tasks[node_id]
        return not self.is_summary(node_id) and task.duration_value == 0

    def ancestors(self, node_id: UUID) -> list[UUID]:
        """Give the ancestors of a node, its parent first."""
        found: list[UUID] = []
        parent = self.nodes[node_id].parent_id
        while parent is not None:
            found.append(parent)
            parent = self.nodes[parent].parent_id
        return found

    def subtree(self, node_id: UUID) -> Iterator[UUID]:
        """Give a node and every node under it, in the order of the plan."""
        pending = [node_id]
        while pending:
            current = pending.pop()
            yield current
            pending.extend(reversed(self.children.get(current, [])))

    def ordered(self, node_ids: Collection[UUID]) -> list[UUID]:
        """Give nodes of the tree in the order of the plan, each once."""
        return sorted(set(node_ids), key=self.row_number.__getitem__)


def read_tree(session: Session, project_id: UUID, structure_id: UUID) -> Tree:
    """Read the nodes of a structure and their facet task, as they are in the transaction.

    The nodes and their tasks come in one statement, so one snapshot: a task created between two
    statements would be a node without its task, or a task without its node.
    """
    rows = session.execute(
        select(Node, Task)
        .outerjoin(Task, and_(Task.project_id == Node.project_id, Task.node_id == Node.id))
        .where(Node.project_id == project_id, Node.structure_id == structure_id)
        .execution_options(populate_existing=True)
    ).all()
    tasks = {node.id: task for node, task in rows if node.kind == TASK}
    tree = Tree({node.id: node for node, _ in rows}, tasks)
    reheld(session, (project_id, structure_id), tree)
    return tree


def reheld[N: NodeColumns, T: TaskColumns](
    session: Session, structure: tuple[UUID, UUID], tree: Tree[N, T]
) -> None:
    """Read what the lines of a tree tell it, as it now stands (``provisions``, ``held``).

    ``structure`` is its project and itself. At the reading of the tree, and again once a write has
    written (``reshaped``): a state, a category or a remaining to commit it wrote changes them
    (US-2250). A tree of the tasks alone bears no line, and asks nothing.
    """
    project_id, structure_id = structure
    if all(node.kind == TASK for node in tree.nodes.values()):
        tree.provisions, tree.held = frozenset(), frozenset()
        return
    tree.provisions = provision_lines(session, project_id, structure_id)
    tree.held = held_open(session, project_id, _closing(tree))


def reshaped(session: Session, project_id: UUID, structure_id: UUID, tree: Tree) -> Tree:
    """Bring a tree a write read under the lock of its structure to what the write made of it.

    What a write gives the replay instead of reading the tree a second time (US-2250, #3169). Its
    objects of the session already hold what the write changed through them; what a statement
    wrote past them — a node created, deleted with the nodes under it, its siblings moved down by
    one — is told by the place and the counter of each node of the structure, read as rows: a node
    the tree does not hold, or whose parent, rank or counter differs from its object, is read with
    its facet, the others kept, those gone dropped. A write advances the counter of every node it
    writes (``Node.lock_version``), by its objects or by its statements, which is what makes a
    node written past its object read again. The order of the plan is computed again on what the
    tree then holds — a move through the objects changes it without any node read again —, and the
    summaries an own line holds open read again (``reheld``). Called once the write is flushed.

    It rests on two facts about what a write does, which ``test_inert_writes.py`` holds by
    listening to the statements of every write: a statement that writes a node (a rank moved down,
    a node deleted) advances its counter in the same statement, and none writes a facet task — the
    task is written through its object alone, which the tree holds. The structure is locked
    (``structure_facts``) since the write read its tree, so the rows read here and the nodes read
    again after them are one snapshot: no other write advances a counter between the two reads.
    A statement that wrote a node without its counter, or a task, would leave it kept stale.

    The test holds the statements ``UPDATE`` alone, outside the flush of the objects — whose node
    is one whose object holds the counter it compares — and asks of one that writes a node that its
    ``SET`` advance the counter (``lock_version = node.lock_version + …``), naming it is not enough
    (#3563). An ``INSERT`` and a ``DELETE`` are not held, and need not be: a node a statement
    creates is one the tree does not hold, read whatever its counter, and one it deletes is no
    longer among the rows, dropped. Neither can leave a node kept stale.
    """
    shape = session.execute(
        select(Node.id, Node.parent_id, Node.rank, Node.lock_version).where(
            Node.project_id == project_id, Node.structure_id == structure_id
        )
    ).all()
    nodes: dict[UUID, Node] = {}
    tasks: dict[UUID, Task] = {}
    stale: list[UUID] = []
    for node_id, parent_id, rank, version in shape:
        node = tree.nodes.get(node_id)
        if node is None or _held_place(node) != (parent_id, rank, version):
            stale.append(node_id)
            continue
        nodes[node_id] = node
        task = tree.tasks.get(node_id)
        if task is not None:
            tasks[node_id] = task
    if stale:
        rows = session.execute(
            select(Node, Task)
            .outerjoin(Task, and_(Task.project_id == Node.project_id, Task.node_id == Node.id))
            .where(Node.project_id == project_id, among(Node.id, stale))
            .execution_options(populate_existing=True)
        ).all()
        for node, task in rows:
            nodes[node.id] = node
            if node.kind == TASK:
                tasks[node.id] = task
    rebuilt = Tree(nodes, tasks)
    reheld(session, (project_id, structure_id), rebuilt)
    return rebuilt


def _held_place(node: Node) -> tuple[object, object, object]:
    """Give the parent, the rank and the counter an object holds, none read for an expired one."""
    held = inspect(node).dict
    return held.get("parent_id", _EXPIRED), held.get("rank"), held.get("lock_version")


def _columns_of(
    session: Session, project_id: UUID, structure_id: UUID
) -> tuple[dict[UUID, NodeRow], dict[UUID, TaskRow]]:
    """Read the nodes of a structure and their facet task as rows, in one statement."""
    rows = session.execute(
        select(*_NODE_COLUMNS, *_TASK_COLUMNS)
        .outerjoin(Task, and_(Task.project_id == Node.project_id, Task.node_id == Node.id))
        .where(Node.project_id == project_id, Node.structure_id == structure_id)
    )
    split = len(_NODE_COLUMNS)
    nodes: dict[UUID, NodeRow] = {}
    tasks: dict[UUID, TaskRow] = {}
    for row in rows:
        node = NodeRow._make(row[:split])
        nodes[node.id] = node
        if node.kind == TASK:
            tasks[node.id] = TaskRow._make(row[split:])
    return nodes, tasks


def read_rows(session: Session, project_id: UUID, structure_id: UUID) -> Tree[NodeRow, TaskRow]:
    """Read the nodes of a structure and their facet task as rows, for a reading alone.

    The columns ``read_tree`` reads, in one statement as it does, but as rows, not as objects of
    the session: what a reading of six thousand nodes spent most in building (#3174).
    """
    tree = Tree(*_columns_of(session, project_id, structure_id))
    reheld(session, (project_id, structure_id), tree)
    return tree


@dataclass(frozen=True, slots=True)
class InertTree:
    """The tree a write whose columns are all inert holds (``read_inert``, US-2250/L2, #3540).

    ``tree`` the structure, its nodes as rows but those the write names, which are the objects of
    the session ``nodes`` and ``tasks`` hold, through which it writes.
    """

    tree: Tree[NodeColumns, TaskColumns]
    nodes: dict[UUID, Node]
    tasks: dict[UUID, Task]


def read_inert(
    session: Session, project_id: UUID, structure_id: UUID, node_ids: Collection[UUID]
) -> InertTree:
    """Read a structure for a write whose columns are all inert: as rows, but the nodes it names.

    Those it writes are read as objects of the session, with their facet task, as ``read_tree``
    reads them; the others as rows, as ``read_rows`` does, a fraction of an object each: the whole
    structure as objects was two thirds of a label entered (#3540). The write locks its structure
    before, so the two statements are one snapshot: no other write changes a node between them.
    The structure is still read whole: what the write gives back — the rows of the plan, the sums
    and the states of the summaries above the node, the totals of the structure — is computed on it.
    """
    found = session.execute(
        select(Node, Task)
        .outerjoin(Task, and_(Task.project_id == Node.project_id, Task.node_id == Node.id))
        .where(
            Node.project_id == project_id,
            Node.structure_id == structure_id,
            among(Node.id, node_ids),
        )
        .execution_options(populate_existing=True)
    ).all()
    rows, row_tasks = _columns_of(session, project_id, structure_id)
    nodes: dict[UUID, NodeColumns] = {**rows}
    tasks: dict[UUID, TaskColumns] = {**row_tasks}
    objects = {node.id: node for node, _ in found}
    facets = {node.id: task for node, task in found if node.kind == TASK}
    nodes.update(objects)
    tasks.update(facets)
    tree = Tree(nodes, tasks)
    reheld(session, (project_id, structure_id), tree)
    return InertTree(tree, objects, facets)


def read_task_rows(
    session: Session, project_id: UUID, structure_id: UUID
) -> Tree[NodeRow, TaskRow]:
    """Read the tasks of a structure alone as rows, none of the nodes they bear (US-2280).

    The columns ``read_rows`` reads of a task, in one statement; numbered as the whole structure
    once ``numbered`` is told how many nodes each task bears, held open as its reader tells.
    """
    rows = session.execute(
        select(*_NODE_COLUMNS, *_TASK_COLUMNS)
        .join(Task, and_(Task.project_id == Node.project_id, Task.node_id == Node.id))
        .where(Node.project_id == project_id, Node.structure_id == structure_id, Node.kind == TASK)
    )
    split = len(_NODE_COLUMNS)
    nodes: dict[UUID, NodeRow] = {}
    tasks: dict[UUID, TaskRow] = {}
    for row in rows:
        node = NodeRow._make(row[:split])
        nodes[node.id] = node
        tasks[node.id] = TaskRow._make(row[split:])
    return Tree(nodes, tasks)


def numbered[N: NodeColumns, T: TaskColumns](tree: Tree[N, T], borne: Mapping[UUID, int]) -> None:
    """Set the rows and places of a tree of the tasks alone, from how many nodes each task bears.

    As the whole structure numbers them: under a task its lines come first, then its subtasks, so
    a task is followed by the rows of its lines, and its subtasks are placed after them. The level
    does not change: no task is under a line.
    """
    row = 0
    for node_id in tree.order:
        row += 1
        tree.row_number[node_id] = row
        row += borne.get(node_id, 0)
    for parent, below in tree.children.items():
        if parent is not None:
            for place, child in enumerate(below, start=1 + borne.get(parent, 0)):
                tree.position[child] = place


def completed_below[N: NodeColumns, T: TaskColumns](tree: Tree[N, T]) -> list[UUID]:
    """Give the summaries whose subtasks are all completed, their leaves, deepest first.

    Whatever the lines of the summaries between hold: a summary held open by its own line is
    completed below.
    """
    done: dict[UUID, bool] = {}
    found: list[UUID] = []
    for node_id in reversed(tree.order):
        if node_id not in tree.tasks:
            continue
        below = tree.subtasks(node_id)
        done[node_id] = (
            all(done[each] for each in below)
            if below
            else tree.tasks[node_id].progress == COMPLETED
        )
        if below and done[node_id]:
            found.append(node_id)
    return found


def _closing[N: NodeColumns, T: TaskColumns](tree: Tree[N, T]) -> dict[UUID, list[UUID]]:
    """Give the summaries whose subtasks are all completed, each with its own lines to ask.

    The lines of provision left out (WF-PLA-0040), and a summary without another line too: nothing
    holds it.
    """
    found: dict[UUID, list[UUID]] = {}
    for node_id in completed_below(tree):
        lines = tree.own_lines(node_id)
        if lines:
            found[node_id] = lines
    return found


def read_links(session: Session, project_id: UUID, structure_id: UUID) -> list[TaskLink]:
    """Read the links between the tasks of a structure."""
    return list(
        session.scalars(
            select(TaskLink)
            .where(TaskLink.project_id == project_id, TaskLink.structure_id == structure_id)
            .order_by(TaskLink.id)
            .execution_options(populate_existing=True)
        )
    )


def read_link_rows(session: Session, project_id: UUID, structure_id: UUID) -> list[LinkRow]:
    """Read the links between the tasks of a structure as rows, for a reading alone."""
    rows = session.execute(
        select(*_LINK_COLUMNS)
        .where(TaskLink.project_id == project_id, TaskLink.structure_id == structure_id)
        .order_by(TaskLink.id)
    )
    return [LinkRow._make(row) for row in rows]


def links_of(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> dict[UUID, list[TaskLink]]:
    """Read the links of nodes, each kept under its predecessor and under its successor."""
    found: dict[UUID, list[TaskLink]] = {node_id: [] for node_id in node_ids}
    if not node_ids:
        return found
    rows = session.scalars(
        select(TaskLink)
        .where(
            TaskLink.project_id == project_id,
            or_(TaskLink.predecessor_id.in_(node_ids), TaskLink.successor_id.in_(node_ids)),
        )
        .order_by(TaskLink.id)
    )
    for link in rows:
        for end in {link.predecessor_id, link.successor_id} & found.keys():
            found[end].append(link)
    return found


def tracking_of(
    session: Session, project_id: UUID, lineage_ids: Collection[UUID]
) -> dict[UUID, list[TrackingEntry]]:
    """Read the inscriptions of lineages, by lineage, the time/time tracking first."""
    found: dict[UUID, list[TrackingEntry]] = {lineage: [] for lineage in lineage_ids}
    if not lineage_ids:
        return found
    rows = session.scalars(
        select(TrackingEntry)
        .where(TrackingEntry.project_id == project_id, among(TrackingEntry.lineage_id, lineage_ids))
        .order_by(TrackingEntry.kind, TrackingEntry.created_at, TrackingEntry.id)
    )
    for entry in rows:
        found[entry.lineage_id].append(entry)
    return found
