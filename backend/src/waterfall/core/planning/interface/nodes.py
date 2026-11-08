# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The nodes of a structure: the tree read and written, what the revisions ask of it, its copy.

The planning registers, at the import of its interface, the copy of the nodes of a revision opened
from a marked one (``copy_nodes``, after the structures', whose copies it finds in
``RevisionCopy.identifiers``) and the question the designation of the reference asks of its tasks
(``revision_has_tasks``, WF-CYC-0030). The reading and the writes of the tree — ``listNodes``,
``createNode``, ``updateTaskFacet``, ``getComputedValueDependencies``, ``resolveRowNumber`` — are
US-1380/L2's, the deletion, the move and the attachment to the work breakdown (``deleteNode``,
``moveNodes``, ``work_package_id`` and ``order_item_id`` of a creation and a modification)
US-1380/L3's; each write judges its revision, opens its entry of the history, locks its structure,
replays the engine on it and gives back what it wrote (``writing``). A marked revision reads as the
current one. The copy leaves null the attachment to an element marked deleted (WF-PLA-0170).
``load_task`` writes a task of the witness at the identifiers and the instant it imposes
(US-1480/L2).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import exists, insert, inspect, select, update

from waterfall.core.planning.attachments import (
    ORDER_ITEM_ID,
    WORK_PACKAGE_ID,
    Attached,
    Bearer,
    carriers,
    judged_attachment,
    stray_fault,
    strays,
)
from waterfall.core.planning.dating import constants_of
from waterfall.core.planning.entries import (
    AUTOMATIC,
    MANUAL,
    judged_change,
    judged_creation,
)
from waterfall.core.planning.filters import NodeFilters, retained
from waterfall.core.planning.interface.facets import calendar_of, calendars_of, facets
from waterfall.core.planning.scheduling import Move, WorkInstant
from waterfall.core.planning.shaping import (
    Placing,
    deleted,
    emptied,
    judge_place,
    place,
    placed,
    stamp,
)
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import TASK, Tree, read_links, read_tree
from waterfall.core.planning.views import NodeView, Reading, state_of
from waterfall.core.planning.writing import (
    NodesWritten,
    Place,
    Write,
    Writer,
    facts_of,
    writing,
)
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.entries import Facet
    from waterfall.core.planning.scheduling import Duration
    from waterfall.core.planning.writing import Write
    from waterfall.core.revisions.interface import RevisionCopy
    from waterfall.platform.audit import Act

NOT_FOUND = "NOT_FOUND"
VALIDATION_FAILED = "VALIDATION_FAILED"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
UNKNOWN_TASK = "UNKNOWN_TASK"
NODE_NOT_SIBLING = "NODE_NOT_SIBLING"
MILESTONE_HAS_NO_SUBTASK = "MILESTONE_HAS_NO_SUBTASK"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
TASK_NOT_STARTED = "task_not_started"
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
    counter a modification read — is read. ``work_package_id`` and ``order_item_id`` attach the
    task to the work breakdown; sent ``None`` at a modification, they remove its attachment.
    """

    label: str | None = None
    description: str | None = None
    scheduling_mode: str | None = None
    duration: Duration | None = None
    start: InstantSent | None = None
    finish: InstantSent | None = None
    sent: frozenset[str] = frozenset()
    lock_version: int | None = None
    work_package_id: UUID | None = None
    order_item_id: UUID | None = None

    def attachment(self, *, creation: bool) -> dict[str, UUID | None]:
        """Give the fields of the attachment sent: those not null at a creation."""
        values = {WORK_PACKAGE_ID: self.work_package_id, ORDER_ITEM_ID: self.order_item_id}
        if creation:
            return {name: value for name, value in values.items() if value is not None}
        return {name: value for name, value in values.items() if name in self.sent}


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
    place, at their first version, their dates as computed, their attachment to the work breakdown
    but to an element marked deleted, which the revision opened does not take up (WF-PLA-0170); the
    facets the later modules register after them (``register_facet``). The inscriptions follow the
    lineage, and stay.
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
    gone = {
        item.item_id
        for item in work_breakdown_items(session, copy.project_id).values()
        if item.deleted
    }
    session.execute(
        insert(Task),
        [
            {
                **_columns(task),
                "node_id": ids[task.node_id],
                "structure_id": ids[task.structure_id],
                "work_package_id": None if task.work_package_id in gone else task.work_package_id,
                "order_item_id": None if task.order_item_id in gone else task.order_item_id,
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
    """Read what a reading of a structure derives: its links, its calendars, its states.

    The links are read after the tree, in their own statement: one whose ends a write committed
    in between is of a later state than the tree, and left out.
    """
    links = [
        link
        for link in read_links(session, place.project_id, place.structure_id)
        if {link.predecessor_id, link.successor_id} <= tree.tasks.keys()
    ]
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
        return max((tree.nodes[each].rank for each in siblings), default=0) + 1
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


def _attached(
    write: Write, bearer: Bearer, sent: Mapping[str, UUID | None], prefix: str
) -> Attached:
    """Judge the attachment a write sends for a task, on the tree read under the lock."""
    held = (write.place.project_id, write.tree, write.facts.is_main)
    return judged_attachment(write.session, held, bearer, sent, prefix)


def _together[Judged](judge: Callable[[], Judged], attached: Attached) -> Judged:
    """Judge a facet sent, its refusals named with those of its attachment, all at once."""
    try:
        judged = judge()
    except UnprocessableError as refused:
        if refused.code != VALIDATION_FAILED or not attached.faults:
            raise
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(*refused.fields, *attached.faults)
        ) from None
    if attached.faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=attached.faults)
    return judged


def _insert(
    write: Write,
    creation: NodeCreation,
    node_id: UUID,
    judged: tuple[Facet, Attached],
    placed: tuple[int, list[UUID]],
) -> None:
    """Write the node and the facet of a task created at its rank, the siblings after it moved.

    ``judged`` is its facet and its attachment as judged. The siblings at that rank or after
    (``placed``) are moved down by one in one statement — the rank is unique, checked at its end —
    and counted as any write of a node is.
    """
    session, place, act = write.session, write.place, write.writer.act
    rank, shifted = placed
    facet, attached = judged
    parent = creation.parent_id
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
            work_package_id=attached.work_package_id,
            order_item_id=attached.order_item_id,
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
    its calendar (#1769, WF-PLA-0020), its attachment to the work breakdown under its parent
    (WF-PLA-0170). A manual leaf that receives it becomes a summary, always automatic
    (WF-PLA-0040), and is written with it. Beyond fifteen years, refused naming the task by its
    label (WF-PLA-0150); nothing is created.
    """
    node_id = new_id()
    with writing(session, place, writer, ("node_create", (node_id,))) as write:
        tree = write.tree
        parent = creation.parent_id
        _judge_parent(tree, parent)
        applicable = calendar_of(session, place.project_id, node_id).calendar
        lineage = () if parent is None else (parent, *tree.ancestors(parent))
        bearer = Bearer(node_id, creation.task.label or "", lineage, created=True)
        attached = _attached(write, bearer, creation.task.attachment(creation=True), "/task")
        facet = _together(
            lambda: judged_creation(creation.task, applicable, constants_of(session)), attached
        )
        rank = _rank(tree, creation)
        shifted = [each for each in tree.subtasks(parent) if tree.nodes[each].rank >= rank]
        made_summary = (
            parent is not None
            and not tree.is_summary(parent)
            and tree.tasks[parent].scheduling_mode == MANUAL
        )
        above = (parent,) if parent is not None and made_summary else ()
        touched = (node_id, *above, *shifted)
        write.before(touched)
        if parent is not None and made_summary:
            tree.tasks[parent].scheduling_mode = AUTOMATIC
            stamp(tree.nodes[parent], writer.act)
        _insert(write, creation, node_id, (facet, attached), (rank, shifted))
        redated = write.redate((None, creation.task.label or ""))
        write.after(touched)
        return redated.written((node_id,))


@dataclass(frozen=True, slots=True)
class Ground:
    """What a cell is judged on: the tree of its structure as read, under its lock or not.

    ``is_main`` tells whether the structure is the main one, the only to bear an attachment.
    """

    session: Session
    project_id: UUID
    tree: Tree
    is_main: bool


def judge_cell(ground: Ground, node_id: UUID, entry: TaskEntry) -> tuple[Facet, Attached]:
    """Judge what is sent of the facet of a task, and of its attachment, all refusals at once.

    The rules of the entry of a cell, which the paste of a block applies to each of its rows
    (``UnprocessableError`` when the entry is refused); nothing is written.
    """
    session, tree = ground.session, ground.tree
    task = tree.tasks[node_id]
    applicable = calendar_of(session, ground.project_id, node_id).calendar
    carried = (task.work_package_id, task.order_item_id)
    bearer = Bearer(node_id, task.label, tuple(tree.ancestors(node_id)), carried)
    held = (ground.project_id, tree, ground.is_main)
    attached = judged_attachment(session, held, bearer, entry.attachment(creation=False), "")
    facet = _together(
        lambda: judged_change(tree, task, entry, applicable, constants_of(session)), attached
    )
    return facet, attached


def write_cell(
    ground: Ground, node_id: UUID, entry: TaskEntry, judged: tuple[Facet, Attached], act: Act
) -> None:
    """Write what ``judge_cell`` accepted on the facet of a task; count the write of its node."""
    facet, attached = judged
    node, task = ground.tree.nodes[node_id], ground.tree.tasks[node_id]
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
    task.work_package_id = attached.work_package_id
    task.order_item_id = attached.order_item_id
    stamp(node, act)


def update_task_facet(
    session: Session,
    place: Place,
    node_id: UUID,
    entry: TaskEntry,
    writer: Writer,
) -> NodesWritten:
    """Write what is sent of the facet of a task, at the counter read (``updateTaskFacet``).

    Under the lock of the structure: refused if the node is no task of it (404), at another
    version (412), or for what it computes or does not accept (422, ``entries``), its attachment
    to the work breakdown with it (``attachments``, WF-PLA-0170). Beyond fifteen years, refused
    naming the task (WF-PLA-0150); nothing is written.
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
        ground = Ground(session, place.project_id, tree, write.facts.is_main)
        judged = judge_cell(ground, node_id, entry)
        write.before((node_id,))
        write_cell(ground, node_id, entry, judged, writer.act)
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


@dataclass(frozen=True, slots=True)
class NodeMoving:
    """A selection of nodes moved under a parent (``NodeMove``), at the counter of the structure.

    ``after_given`` false places each kind after its last sibling; given, ``after_node_id`` null
    places them at the head of their siblings.
    """

    node_ids: tuple[UUID, ...]
    parent_id: UUID | None
    after_node_id: UUID | None
    after_given: bool
    lock_version: int


def delete_node(
    session: Session, place: Place, node_id: UUID, lock_version: int, writer: Writer
) -> NodesWritten:
    """Delete a node and its subtree, and give the nodes written (``deleteNode``).

    Under the lock of the structure: refused if the structure does not hold the node (404), at
    another version than the one read (412), for a task started or completed, or a summary one of
    whose subordinates is (409 ``task_not_started``, WF-PLA-0070). The subtree goes, its links and
    the inscriptions of its lineages with it; a summary left without subordinate becomes a leaf in
    its state (WF-PLA-0040) and is given back among the ancestors, with the tasks the links taken
    away redate. No provision line moves before EP-08: ``nodes`` is empty.
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
        if node_id in tree.tasks and state_of(tree, node_id).progress != NOT_STARTED:
            raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": TASK_NOT_STARTED})
        parent = node.parent_id
        former = () if parent is None else (parent, *tree.ancestors(parent))
        subtree = list(tree.subtree(node_id))
        left_bare = parent is not None and tree.subtasks(parent) == [node_id]
        touched = (*subtree, *((parent,) if left_bare and parent is not None else ()))
        write.before(touched)
        if left_bare and parent is not None:
            emptied(tree, parent)
            stamp(tree.nodes[parent], writer.act)
        deleted(session, place.project_id, tree, subtree)
        redated = write.redate(None)
        write.after(touched)
        return redated.written((), former)


def _judge_move(tree: Tree, placing: Placing) -> None:
    """Refuse a move the tree forbids: a parent that is no task, in the selection, a milestone.

    A parent among the nodes moved or under one of them would leave no tree (WF-PLA-0040); a
    line goes under a task; a task moved under a milestone is refused, the milestone named
    (WF-PLA-0050, #1771); the sibling named is one under the parent (``NODE_NOT_SIBLING``).
    """
    parent = placing.parent_id
    moved = placing.node_ids
    tasks_moved = any(each in tree.tasks for each in moved)
    inside = {each for node_id in moved for each in tree.subtree(node_id)}
    lines_moved = len(moved) > sum(each in tree.tasks for each in moved)
    if (parent is None and lines_moved) or (
        parent is not None and (parent not in tree.tasks or parent in inside)
    ):
        # 422 ``UNKNOWN_TASK`` on /parent_id for a parent taken in the selection: the contract does
        # not say it yet (#2500, to settle).
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(FieldError("/parent_id", UNKNOWN_TASK),)
        )
    if parent is not None and tasks_moved and tree.is_milestone(parent):
        named = {"node_id": str(parent), "label": tree.tasks[parent].label}
        fault = FieldError("/parent_id", MILESTONE_HAS_NO_SUBTASK, named)
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    judge_place(tree, placing)


def _judge_package_tasks(write: Write, placing: Placing, sent: tuple[UUID, ...]) -> None:
    """Refuse a move that takes the task of an order item out of that of its work package.

    Judged on the structure the move would leave; the fault is on the first moved node concerned
    in the order of the plan read, at its place among those ``sent``, the tasks named by their node
    and their label (WF-PLA-0170).
    """
    tree = write.tree
    borne = carriers(tree)
    if not borne:
        return
    parents = {node_id: node.parent_id for node_id, node in tree.nodes.items()}
    parents.update(dict.fromkeys(placing.node_ids, placing.parent_id))

    def is_under(task_id: UUID, summary: UUID) -> bool:
        above = parents[task_id]
        while above is not None and above != summary:
            above = parents[above]
        return above == summary

    items = work_breakdown_items(write.session, write.place.project_id)
    found = strays(items, borne, is_under)
    if not found:
        return
    for moved in tree.ordered(placing.node_ids):
        below = set(tree.subtree(moved))
        for stray in found:
            if stray[0] in below or below.intersection(stray[1]):
                pointer = f"/node_ids/{sent.index(moved)}"
                fault = stray_fault(tree, pointer, stray, {})
                raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))


def move_nodes(session: Session, place: Place, moving: NodeMoving, writer: Writer) -> NodesWritten:
    """Move a selection of nodes under a parent, and give the nodes written (``moveNodes``).

    Under the lock of the structure, at its counter (412): a node it does not hold is not found
    (404); the parent and the place are judged (``_judge_move``), then the tasks of the work
    breakdown (WF-PLA-0170). Each node takes its subtree with it, unchanged but for its parent and
    its place (WF-PLA-0040); a manual leaf that receives a task becomes an automatic summary; a
    summary that loses its last subordinate a leaf in its state. The engine refuses a link the
    move would make between a summary and its subordinate, or a loop it would close through the
    parent (``LINK_FORBIDDEN``, ``LINK_CYCLE``, #1169), and a project beyond fifteen years, the
    first task moved named (WF-PLA-0150); nothing is written then. The moved nodes are given back
    with their former and new ancestors.
    """
    node_ids = tuple(dict.fromkeys(moving.node_ids))
    with writing(session, place, writer, ("node_move", node_ids)) as write:
        tree = write.tree
        if write.facts.lock_version != moving.lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": write.facts.lock_version}
            )
        if not all(each in tree.nodes for each in node_ids):
            raise NotFoundError(NOT_FOUND)
        placing = Placing(node_ids, moving.parent_id, moving.after_node_id, moving.after_given)
        _judge_move(tree, placing)
        _judge_package_tasks(write, placing, moving.node_ids)
        return _moved(write, placing)


def _moved(write: Write, placing: Placing) -> NodesWritten:
    """Write a move judged: the places, the summaries made and left, then redate."""
    tree, act = write.tree, write.writer.act
    parent, node_ids = placing.parent_id, placing.node_ids
    tasks_moved = tree.ordered([each for each in node_ids if each in tree.tasks])
    changes = placed(tree, placing)
    former = {above for each in node_ids for above in tree.ancestors(each)}
    left_bare = [
        each
        for each in tree.ordered(former)
        if each != parent and tree.subtasks(each) and set(tree.subtasks(each)) <= set(node_ids)
    ]
    made_summary = (
        parent is not None
        and bool(tasks_moved)
        and not tree.is_summary(parent)
        and tree.tasks[parent].scheduling_mode == MANUAL
    )
    shifted = [each for each in changes if each not in node_ids]
    above = (parent,) if made_summary and parent is not None else ()
    touched = (*node_ids, *shifted, *above, *left_bare)
    write.before(touched)
    for each in left_bare:
        emptied(tree, each)
        stamp(tree.nodes[each], act)
    if made_summary and parent is not None:
        tree.tasks[parent].scheduling_mode = AUTOMATIC
        stamp(tree.nodes[parent], act)
    place(write, changes, (*node_ids, *shifted))
    first = tasks_moved[0] if tasks_moved else None
    blamed = None if first is None else (first, tree.tasks[first].label)
    origin = None if parent is None or first is None else Move(tuple(tasks_moved), parent)
    redated = write.redate(blamed, origin)
    write.after(touched)
    return redated.written(node_ids, former)


def load_task(session: Session, project_id: UUID, structure_id: UUID, act: Act) -> None:
    """Write a task of the witness, at the identifiers and the instant it imposes."""
    msg = "load_task is filled by US-1480/L2"
    raise NotImplementedError(msg)
