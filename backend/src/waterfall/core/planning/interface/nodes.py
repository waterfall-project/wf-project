# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The nodes of a structure: the tree read and written, what the revisions ask of it, its copy.

The planning registers, at the import of its interface, the copy of the nodes of a revision opened
from a marked one (``copy_nodes``, after the structures', whose copies it finds in
``RevisionCopy.identifiers``) and the question the designation of the reference asks of its tasks
(``revision_has_tasks``, WF-CYC-0030). The reading and the writes of the tree — ``listNodes``,
``createNode``, ``updateTaskFacet``, ``getComputedValueDependencies``, ``resolveRowNumber`` — are
US-1380/L2's, the deletion and the move (``deleteNode``, ``moveNodes``) US-1380/L3's; each write
judges its revision, opens its entry of the history, locks its structure, replays the engine on it
and gives back what it wrote (``writing``). A marked revision reads as the current one. The
attachment to the work breakdown is US-1380/L3's: a creation and a modification leave it as it is.
``load_task`` writes a task of the witness at the identifiers and the instant it imposes
(US-1480/L2).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import exists, insert, inspect, select, update

from waterfall.core.planning.dating import constants_of
from waterfall.core.planning.entries import (
    AUTOMATIC,
    MANUAL,
    judged_change,
    judged_creation,
)
from waterfall.core.planning.filters import NodeFilters, retained
from waterfall.core.planning.interface.facets import calendar_of, calendars_of, facets
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import TASK, Tree, read_links, read_tree
from waterfall.core.planning.views import NodeView, Reading
from waterfall.core.planning.writing import (
    NodesWritten,
    Place,
    Write,
    Writer,
    facts_of,
    writing,
)
from waterfall.platform.errors import (
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.entries import Facet
    from waterfall.core.planning.scheduling import Duration
    from waterfall.core.revisions.interface import RevisionCopy
    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
UNKNOWN_TASK = "UNKNOWN_TASK"
NODE_NOT_SIBLING = "NODE_NOT_SIBLING"
MILESTONE_HAS_NO_SUBTASK = "MILESTONE_HAS_NO_SUBTASK"
NOT_STARTED = "not_started"


@dataclass(frozen=True, slots=True)
class InstantSent:
    """A start or a finish as it is sent: a day, and the hours of work elapsed, if sent."""

    day: date
    hours: Decimal | None = None


@dataclass(frozen=True, slots=True)
class TaskEntry:
    """The facet of a task as a write sends it; ``sent`` names what a modification sends.

    At a creation, a field absent is ``None``, and neither ``sent`` nor ``lock_version`` — the
    counter a modification read — is read.
    """

    label: str | None = None
    description: str | None = None
    scheduling_mode: str | None = None
    duration: Duration | None = None
    start: InstantSent | None = None
    finish: InstantSent | None = None
    sent: frozenset[str] = frozenset()
    lock_version: int | None = None


@dataclass(frozen=True, slots=True)
class NodeList:
    """A reading of a structure (``listNodes``): its nodes, its tasks counted, its meta."""

    items: tuple[NodeView, ...]
    task_count: int
    summary_depth: int
    scheduled_at: datetime


@dataclass(frozen=True, slots=True)
class NodeCreation:
    """A task to create: its parent, the sibling it follows, its facet.

    ``after_given`` false places it after the last subtask of its parent; given, ``after_node_id``
    null places it at their head.
    """

    parent_id: UUID | None
    after_node_id: UUID | None
    after_given: bool
    task: TaskEntry


@dataclass(frozen=True, slots=True)
class RowResolution:
    """The node a row number designates (``RowNumberResolution``)."""

    node_id: UUID
    row_number: int
    label: str
    kind: str


@dataclass(frozen=True, slots=True)
class DependencyRow:
    """A row a computed value depends on: its node, its number, its label."""

    node_id: UUID
    row_number: int
    label: str


@dataclass(frozen=True, slots=True)
class Dependencies:
    """What the computed value of a field of a node depends on (``ComputedValueDependencies``)."""

    node_id: UUID
    field: str
    depends_on: tuple[str, ...]
    rows: tuple[DependencyRow, ...]


def revision_has_tasks(session: Session, revision_id: UUID) -> bool:
    """Tell whether a revision bears a task: the planning's part of a designation (WF-CYC-0030)."""
    return bool(
        session.scalar(select(exists().where(Node.revision_id == revision_id, Node.kind == TASK)))
    )


def _columns(row: Node | Task | TaskLink) -> dict[str, object]:
    """Give the columns of a row, by name."""
    return {column.key: getattr(row, column.key) for column in inspect(row).mapper.column_attrs}


def _depth_first(nodes: list[Node]) -> list[Node]:
    """Order nodes so that each parent comes before its children."""
    held = {node.id for node in nodes}
    depth: dict[UUID, int] = {}

    def level(node: Node) -> int:
        if node.id not in depth:
            parent = node.parent_id
            depth[node.id] = 0 if parent is None or parent not in held else 1 + level(by[parent])
        return depth[node.id]

    by = {node.id: node for node in nodes}
    return sorted(nodes, key=lambda node: (level(node), node.id))


def copy_nodes(copy: RevisionCopy) -> None:
    """Copy the nodes of the source, their facet task and their links (WF-DAT-0010).

    The nodes of each structure copied, under identifiers of their own and their lineage, at their
    place, at their first version, their dates as computed; the facets the later modules register
    after them (``register_facet``). The inscriptions follow the lineage, and stay.
    """
    session, ids = copy.session, copy.identifiers
    nodes = [
        node
        for node in session.scalars(
            select(Node).where(Node.project_id == copy.project_id, Node.revision_id == copy.source)
        )
        if node.structure_id in ids
    ]
    for node in nodes:
        ids[node.id] = new_id()
    stamp = {
        "created_at": copy.at,
        "created_by": copy.author,
        "updated_at": copy.at,
        "updated_by": copy.author,
    }
    rows = [
        {
            "project_id": copy.project_id,
            "id": ids[node.id],
            "revision_id": copy.target,
            "structure_id": ids[node.structure_id],
            "lineage_id": node.lineage_id,
            "kind": node.kind,
            "parent_id": None if node.parent_id is None else ids[node.parent_id],
            "rank": node.rank,
            "origin_risk_id": node.origin_risk_id,
            "lock_version": 1,
            **stamp,
        }
        for node in _depth_first(nodes)
    ]
    if not rows:
        return
    session.execute(insert(Node), rows)
    tasks = session.scalars(
        select(Task).where(Task.project_id == copy.project_id, Task.node_id.in_(list(ids)))
    ).all()
    session.execute(
        insert(Task),
        [
            {
                **_columns(task),
                "node_id": ids[task.node_id],
                "structure_id": ids[task.structure_id],
            }
            for task in tasks
        ],
    )
    links = session.scalars(
        select(TaskLink).where(
            TaskLink.project_id == copy.project_id, TaskLink.revision_id == copy.source
        )
    ).all()
    copied_links = [
        {
            **_columns(link),
            "id": new_id(),
            "revision_id": copy.target,
            "structure_id": ids[link.structure_id],
            "predecessor_id": ids[link.predecessor_id],
            "successor_id": ids[link.successor_id],
        }
        for link in links
        if link.structure_id in ids
    ]
    if copied_links:
        session.execute(insert(TaskLink), copied_links)
    for hooks in facets().values():
        hooks.copy(copy)


def _reading(
    session: Session, place: Place, tree: Tree, scheduled: tuple[datetime, bool]
) -> Reading:
    """Read what a reading of a structure derives: its links, its calendars, its states."""
    links = read_links(session, place.project_id, place.structure_id)
    calendars = calendars_of(session, place.project_id, tree.tasks)
    return Reading(session, (place.project_id, *scheduled), tree, links, calendars)


def list_nodes(session: Session, place: Place, filters: NodeFilters) -> NodeList:
    """Read the nodes of a structure, depth first, numbered and filtered (``listNodes``).

    The whole structure is numbered, whatever is retained; ``summary_depth`` and ``scheduled_at``
    are the structure's, whatever the filters (WF-PLA-0080, WF-PLA-0110). Refused if the project,
    the revision or the structure is unknown (404).
    """
    facts = facts_of(session, place, lock=False)
    tree = read_tree(session, place.project_id, place.structure_id)
    reading = _reading(session, place, tree, (facts.scheduled_at, facts.is_main))
    structure = (place.project_id, place.structure_id)
    order, count = retained(session, structure, reading, filters, constants_of(session))
    return NodeList(
        tuple(reading.node(each) for each in order),
        count,
        reading.summary_depth(),
        facts.scheduled_at,
    )


def _rank(tree: Tree, creation: NodeCreation) -> int:
    """Give the rank of a task created among the subtasks of its parent (#1183, #1187).

    After the last of them by default, at their head after ``null`` or after a line of the same
    parent; after its sibling otherwise. Another node is refused (``NODE_NOT_SIBLING``).
    """
    parent = creation.parent_id
    siblings = tree.subtasks(parent)
    if not creation.after_given:
        return len(siblings) + 1
    after = creation.after_node_id
    if after is None:
        return 1
    if after in siblings:
        return tree.nodes[after].rank + 1
    if after in tree.nodes and after not in tree.tasks and tree.nodes[after].parent_id == parent:
        return 1
    raise UnprocessableError(
        VALIDATION_FAILED, fields=(FieldError("/after_node_id", NODE_NOT_SIBLING),)
    )


def _judge_parent(tree: Tree, parent: UUID | None) -> None:
    """Refuse a parent that is no task of the structure, or a milestone (WF-PLA-0050)."""
    if parent is None:
        return
    if parent not in tree.tasks:
        fault = FieldError("/parent_id", UNKNOWN_TASK)
    elif tree.is_milestone(parent):
        named = {"node_id": str(parent), "label": tree.tasks[parent].label}
        fault = FieldError("/parent_id", MILESTONE_HAS_NO_SUBTASK, named)
    else:
        return
    raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))


def _stamp(node: Node, act: Act) -> None:
    """Count a write of a node: its version advanced, its author and its instant."""
    node.lock_version += 1
    node.updated_at = act.at
    node.updated_by = act.author


def _insert(write: Write, creation: NodeCreation, node_id: UUID, facet: Facet) -> None:
    """Write the node and the facet of a task created, its younger siblings moved down by one.

    The ranks of the subtasks of a parent run from 1 without a gap: every write keeps them so.
    """
    session, place, act = write.session, write.place, write.writer.act
    rank = _rank(write.tree, creation)
    parent = creation.parent_id
    session.execute(
        update(Node)
        .where(
            Node.project_id == place.project_id,
            Node.structure_id == place.structure_id,
            Node.kind == TASK,
            Node.parent_id.is_(None) if parent is None else Node.parent_id == parent,
            Node.rank >= rank,
        )
        .values(rank=Node.rank + 1)
        .execution_options(synchronize_session=False)
    )
    session.add(
        Node(
            project_id=place.project_id,
            id=node_id,
            revision_id=place.revision_id,
            structure_id=place.structure_id,
            lineage_id=node_id,
            kind=TASK,
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
    # An automatic task is placed by the engine; it stands at the planning start meanwhile.
    start = facet.start or WorkInstant(write.facts.planning_start_on)
    finish = facet.finish or start
    entry = creation.task
    session.add(
        Task(
            project_id=place.project_id,
            node_id=node_id,
            structure_id=place.structure_id,
            kind=TASK,
            label=entry.label,
            description=entry.description,
            scheduling_mode=facet.scheduling_mode,
            duration_value=facet.duration.value,
            duration_unit=facet.duration.unit,
            start_date=start.day,
            start_hours=start.hours,
            finish_date=finish.day,
            finish_hours=finish.hours,
            progress=NOT_STARTED,
            total_float_days=None,
            is_critical=False,
        )
    )


def create_node(
    session: Session, place: Place, creation: NodeCreation, writer: Writer
) -> NodesWritten:
    """Create a task of a structure, and give the nodes written (``createNode``).

    Judged under the lock of the structure: its parent, a task of the structure and no milestone
    (``MILESTONE_HAS_NO_SUBTASK``, WF-PLA-0050), its place (``NODE_NOT_SIBLING``), its facet — an
    automatic task of a day by default, a manual one at the dates sent, their hours completed on
    its calendar (#1769, WF-PLA-0020). A manual leaf that receives it becomes a summary, always
    automatic (WF-PLA-0040), and is written with it. Beyond fifteen years, refused naming the task
    by its label (WF-PLA-0150); nothing is created.
    """
    node_id = new_id()
    with writing(session, place, writer, ("node_create", (node_id,))) as write:
        tree = write.tree
        parent = creation.parent_id
        _judge_parent(tree, parent)
        applicable = calendar_of(session, place.project_id, node_id).calendar
        facet = judged_creation(creation.task, applicable, constants_of(session))
        _rank(tree, creation)
        made_summary = (
            parent is not None
            and not tree.is_summary(parent)
            and tree.tasks[parent].scheduling_mode == MANUAL
        )
        touched = (node_id, parent) if parent is not None and made_summary else (node_id,)
        write.before(touched)
        if parent is not None and made_summary:
            tree.tasks[parent].scheduling_mode = AUTOMATIC
            _stamp(tree.nodes[parent], writer.act)
        _insert(write, creation, node_id, facet)
        redated = write.redate((None, creation.task.label or ""))
        write.after(touched)
        return redated.written((node_id,))


def update_task_facet(
    session: Session,
    place: Place,
    node_id: UUID,
    entry: TaskEntry,
    writer: Writer,
) -> NodesWritten:
    """Write what is sent of the facet of a task, at the counter read (``updateTaskFacet``).

    Under the lock of the structure: refused if the node is no task of it (404), at another
    version (412), or for what it computes or does not accept (422, ``entries``). Beyond fifteen
    years, refused naming the task (WF-PLA-0150); nothing is written.
    """
    with writing(session, place, writer, ("cell", (node_id,))) as write:
        tree = write.tree
        if node_id not in tree.tasks:
            raise NotFoundError(NOT_FOUND)
        node, task = tree.nodes[node_id], tree.tasks[node_id]
        if node.lock_version != entry.lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": node.lock_version}
            )
        applicable = calendar_of(session, place.project_id, node_id).calendar
        facet = judged_change(tree, task, entry, applicable, constants_of(session))
        write.before((node_id,))
        if "label" in entry.sent and entry.label is not None:
            task.label = entry.label
        if "description" in entry.sent:
            task.description = entry.description
        task.scheduling_mode = facet.scheduling_mode
        task.duration_value = facet.duration.value
        task.duration_unit = facet.duration.unit
        if facet.start is not None and facet.finish is not None:
            task.start_date, task.start_hours = facet.start.day, facet.start.hours
            task.finish_date, task.finish_hours = facet.finish.day, facet.finish.hours
        _stamp(node, writer.act)
        redated = write.redate((node_id, task.label))
        write.after((node_id,))
        return redated.written((node_id,))


# The rule a computed field of a summary follows (WF-IHM-0030, WF-PLA-0040, WF-PLA-0100): a field
# absent is entered for it. The amounts of any task follow its lines and its subordinates.
_SUMMARY_RULES = {
    "task.scheduling_mode": "subordinates",
    "task.duration": "subordinates",
    "task.start": "subordinates",
    "task.finish": "subordinates",
    "task.progress": "subordinates",
    "task.total_float": "subordinates",
    "task.physical_progress": "lines_and_subordinates",
}
_AMOUNTS = ("task.base_amount", "task.budgeted_amount", "task.reestimated_amount")
_DATES = ("task.start", "task.finish")


def _rule(tree: Tree, node_id: UUID, field: str) -> tuple[str, list[UUID]] | None:
    """Give the rule a computed field of a task follows and the rows it reads; none if entered."""
    if field in _AMOUNTS:
        return "lines_and_subordinates", [*tree.lines(node_id), *tree.subtasks(node_id)]
    if tree.is_summary(node_id):
        rule = _SUMMARY_RULES.get(field)
        if rule is None:
            return None
        lines = tree.lines(node_id) if rule == "lines_and_subordinates" else []
        return rule, [*lines, *tree.subtasks(node_id)]
    manual = tree.tasks[node_id].scheduling_mode == MANUAL
    if field == "task.total_float":
        return ("manual_mode" if manual else "float_dates"), []
    if field in _DATES and not manual:
        return "scheduling", []
    return None


def computed_value_dependencies(
    session: Session, place: Place, node_id: UUID, field: str
) -> Dependencies:
    """Name what a computed value of a node depends on (``getComputedValueDependencies``).

    The rule, and the rows it reads — the direct subordinates of a summary, the lines and the
    direct subordinates of a task — in the order of the plan, whatever a reading retains. A field
    the server does not compute for the node is refused (422, ``params.field``); a node the
    structure does not hold is not found (404).
    """
    facts_of(session, place, lock=False)
    tree = read_tree(session, place.project_id, place.structure_id)
    if node_id not in tree.nodes:
        raise NotFoundError(NOT_FOUND)
    found = _rule(tree, node_id, field) if node_id in tree.tasks else None
    if found is None:
        raise UnprocessableError(VALIDATION_FAILED, {"field": field})
    rule, rows = found
    return Dependencies(
        node_id,
        field,
        (rule,),
        tuple(DependencyRow(each, tree.row_number[each], _label(tree, each)) for each in rows),
    )


def _label(tree: Tree, node_id: UUID) -> str:
    """Give the label of a node: its task's; a line's is EP-07's facet."""
    task = tree.tasks.get(node_id)
    return "" if task is None else task.label


def resolve_row_number(session: Session, place: Place, row_number: int) -> RowResolution:
    """Give the node of a number of row of a structure (``resolveRowNumber``).

    In the numbering of the whole structure, whatever a grid retains; beyond its last row, not
    found (404), as an unknown structure is.
    """
    facts_of(session, place, lock=False)
    tree = read_tree(session, place.project_id, place.structure_id)
    if not 1 <= row_number <= len(tree.order):
        raise NotFoundError(NOT_FOUND)
    node_id = tree.order[row_number - 1]
    return RowResolution(node_id, row_number, _label(tree, node_id), tree.nodes[node_id].kind)


def delete_node(session: Session, project_id: UUID, node_id: UUID, act: Act) -> None:
    """Delete a node and its subtree, and give the nodes written (``deleteNode``)."""
    msg = "delete_node is filled by US-1380/L3"
    raise NotImplementedError(msg)


def move_nodes(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Move a selection of nodes under a parent, and give the nodes written (``moveNodes``)."""
    msg = "move_nodes is filled by US-1380/L3"
    raise NotImplementedError(msg)


def load_task(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Write a task of the witness, at the identifiers and the instant it imposes."""
    msg = "load_task is filled by US-1480/L2"
    raise NotImplementedError(msg)
