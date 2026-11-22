# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A write that can move no date nor change an amount takes the short path (EP-26, US-2250).

The criteria of US-2250, its own — the story has no requirement of its own, its gain being read in
the report of WF-QUA-0060 (US-2300) —, on the witness, the main structure of its current revision
of PRJ-001 (#3169):

- the inert columns are those of the declarations, the task's in the planning
  (``INERT_TASK_FIELDS``), the line's by its hooks (``FacetHooks.inert``); each column a grid
  accepts (``editable_fields``) has its write here, and the write of an inert one gives back no task
  redated and no amount moved;
- the inert ones, and they alone, take the short path: the engine not replayed, the instant of the
  structure's dates left as it is, its counter advanced; their answer is the one the whole path
  gives, and their entry of the history is undone as any;
- every write of the whole path reads the tree once — one that creates, deletes or moves nodes, a
  write of the structure itself, an undoing and a redoing included: the replay is handed the tree
  read under the lock, brought to what the write made of it (``reshaped``), and gives back what it
  gave reading the tree a second time, the structure as stored the same, the nodes it read again
  only those a statement wrote past their objects; the short path reads none as objects of the
  session, its structure read as rows but the nodes it writes (``read_inert``, US-2250/L2, #3540);
- what ``reshaped`` rests on holds on every write: a statement that writes a node advances its
  counter, and no statement writes a facet task, which only the objects of the session write
  (``unkept``; the withdrawal of an element of the work breakdown, ``test_inert_reading.py``).
"""

import re
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import timedelta
from decimal import Decimal
from itertools import count
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from sqlalchemy import Engine, event, select
from sqlalchemy.orm import Session
from test_witness_projects import PRJ_001, REVISION_102
from test_witness_tasks import structure_of

from measure.writing import entered_leaf
from waterfall.core.estimate.interface import (
    LineEntry,
    LineRemaining,
    LineView,
    set_line_remaining,
    update_line,
)
from waterfall.core.estimate.interface.facet import LINE_INERT
from waterfall.core.planning import rescheduling, restoring, writing
from waterfall.core.planning import tree as trees
from waterfall.core.planning.entries import INERT_TASK_FIELDS
from waterfall.core.planning.interface import (
    ENTRIES,
    Duration,
    InstantSent,
    LinesWrite,
    NodeCreation,
    NodeFilters,
    NodeMoving,
    Place,
    PredecessorSent,
    PredecessorsEntry,
    ProgressEntry,
    StructureChange,
    TaskEntry,
    TrackingChange,
    Writer,
    create_node,
    delete_node,
    list_nodes,
    move_nodes,
    redo_last_undo,
    set_node_tracking,
    set_predecessors,
    set_task_progress,
    undo_last_change,
    update_cost_structure,
    update_task_facet,
    write_lines,
)
from waterfall.core.planning.interface import lines as line_writes
from waterfall.core.planning.interface import nodes as node_writes
from waterfall.core.planning.interface.facets import facets
from waterfall.core.planning.tables import Node, Task
from waterfall.core.planning.writing import Write
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.core.revisions.interface import structure_facts
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable
    from datetime import datetime
    from types import ModuleType

    from waterfall.core.planning.interface import NodeList, NodesWritten, NodeView
    from waterfall.core.planning.tree import Tree
    from waterfall.core.revisions.interface import StructureFacts
    from waterfall.platform.database import Database

LINE = "estimate_line"
INERT = INERT_TASK_FIELDS | set(LINE_INERT)


@dataclass(frozen=True, slots=True)
class Read:
    """The structure as it stands before a write: its place, its nodes read whole."""

    place: Place
    listed: NodeList

    @property
    def nodes(self) -> tuple[NodeView, ...]:
        return self.listed.items

    def first(self, keep: Callable[[NodeView], bool]) -> NodeView:
        """Give the first node in the order of the plan that ``keep`` retains."""
        return next(each for each in self.nodes if keep(each))

    def line(
        self, field: str, keep: Callable[[LineView], bool] = lambda _: True
    ) -> tuple[NodeView, LineView]:
        """Give the first line whose grid accepts ``field`` and whose facet ``keep`` retains."""
        node = self.first(
            lambda each: each.kind == LINE and field in each.editable_fields and keep(view_of(each))
        )
        return node, view_of(node)

    def leaf(self) -> NodeView:
        """Give the leaf the measure enters a cell in: scheduled in days, followed by many."""
        return entered_leaf(tuple(each for each in self.nodes if each.task is not None))


type Writing = Callable[[Session, Read, Writer], NodesWritten]


def view_of(node: NodeView) -> LineView:
    """Give the facet of a line as the estimate reads it."""
    assert node.facet is not None
    view = node.facet.view
    assert isinstance(view, LineView)
    return view


def _task(
    session: Session, read: Read, node: NodeView, writer: Writer, **sent: Any
) -> NodesWritten:
    entry = TaskEntry(**sent, sent=frozenset(sent), lock_version=node.lock_version)
    return update_task_facet(session, read.place, node.node_id, entry, writer)


def _line(
    session: Session, read: Read, node: NodeView, writer: Writer, **sent: Any
) -> NodesWritten:
    entry = LineEntry(**sent, sent=frozenset(sent), lock_version=node.lock_version)
    return update_line(session, read.place, node.node_id, entry, writer)


def label(session: Session, read: Read, writer: Writer) -> NodesWritten:
    leaf = read.leaf()
    assert leaf.task is not None
    return _task(session, read, leaf, writer, label=f"{leaf.task.label} x")


def description(session: Session, read: Read, writer: Writer) -> NodesWritten:
    return _task(session, read, read.leaf(), writer, description="noted")


def _package(read: Read) -> NodeView:
    """Give the task that bears a work package: on the witness, a summary."""
    return read.first(lambda each: each.task is not None and each.task.work_package_id is not None)


def order_item(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # An order item of the work package a summary bears, given to a leaf under that summary.
    package = _package(read)
    assert package.task is not None
    items = work_breakdown_items(session, read.place.project_id).values()
    item = min(
        each.item_id
        for each in items
        if each.work_package_id == package.task.work_package_id and not each.deleted
    )
    parents = {each.node_id: each.parent_id for each in read.nodes}

    def under(node_id: UUID) -> bool:
        above = parents[node_id]
        while above is not None and above != package.node_id:
            above = parents[above]
        return above == package.node_id

    leaf = read.first(
        lambda each: (
            each.task is not None
            and not each.task.is_summary
            and "task.order_item_id" in each.editable_fields
            and under(each.node_id)
        )
    )
    return _task(session, read, leaf, writer, order_item_id=item)


def work_package(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The work package taken from the summary that bears it.
    return _task(session, read, _package(read), writer, work_package_id=None)


def tracking(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The inscriptions of a task withdrawn.
    node = read.first(lambda each: each.task is not None and bool(each.task.tracking))
    change = TrackingChange((), node.lock_version)
    return set_node_tracking(session, read.place, node.node_id, change, writer)


def scheduling_mode(session: Session, read: Read, writer: Writer) -> NodesWritten:
    return _task(session, read, read.leaf(), writer, scheduling_mode="manual")


def duration(session: Session, read: Read, writer: Writer) -> NodesWritten:
    leaf = read.leaf()
    assert leaf.task is not None
    longer = Duration(leaf.task.duration_value + 3, "d")
    return _task(session, read, leaf, writer, duration=longer)


def start(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The dates of a task are entered in manual mode: the leaf is made manual by the same write.
    leaf = read.leaf()
    assert leaf.task is not None
    day = InstantSent(leaf.task.start.day)
    return _task(session, read, leaf, writer, scheduling_mode="manual", start=day)


def finish(session: Session, read: Read, writer: Writer) -> NodesWritten:
    leaf = read.leaf()
    assert leaf.task is not None
    day = InstantSent(leaf.task.finish.day)
    return _task(session, read, leaf, writer, scheduling_mode="manual", finish=day)


def progress(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A leaf not started, no milestone, started on its first day.
    leaf = read.first(
        lambda each: (
            each.task is not None
            and each.task.progress == "not_started"
            and not each.task.is_milestone
            and "task.progress" in each.editable_fields
        )
    )
    assert leaf.task is not None
    entry = ProgressEntry("started", leaf.lock_version, leaf.task.start.day)
    return set_task_progress(session, read.place, leaf.node_id, entry, writer)


def predecessors(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The predecessors of a task sent again as they are.
    node = read.first(lambda each: each.task is not None and bool(each.predecessors))
    sent = tuple(
        PredecessorSent(each.predecessor_id, each.link_type, each.lag_value, each.lag_unit)
        for each in node.predecessors
    )
    entry = PredecessorsEntry(sent, node.lock_version)
    return set_predecessors(session, read.place, node.node_id, entry, writer)


def line_label(session: Session, read: Read, writer: Writer) -> NodesWritten:
    node, _ = read.line(f"{LINE}.label")
    return _line(session, read, node, writer, label="entered")


def payment_delay(session: Session, read: Read, writer: Writer) -> NodesWritten:
    node, view = read.line(f"{LINE}.payment_delay_days")
    # A line that accepts a payment delay carries one: a provision line alone has none (#4274).
    held = view.payment_delay_days
    assert held is not None
    later = held + 30
    return _line(session, read, node, writer, payment_delay_days=later)


def subproject(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A line taken from its subproject.
    node, _ = read.line(f"{LINE}.subproject_id", lambda view: view.subproject_id is not None)
    return _line(session, read, node, writer, subproject_id=None)


def quantity(session: Session, read: Read, writer: Writer) -> NodesWritten:
    node, view = read.line(f"{LINE}.quantity")
    return _line(session, read, node, writer, quantity=view.quantity + 1)


def hours(session: Session, read: Read, writer: Writer) -> NodesWritten:
    node, view = read.line(f"{LINE}.hours")
    assert view.hours is not None
    return _line(session, read, node, writer, hours=view.hours + 1)


def disbursement(session: Session, read: Read, writer: Writer) -> NodesWritten:
    node, view = read.line(f"{LINE}.unit_disbursement")
    assert view.unit_disbursement is not None
    more = view.unit_disbursement + 1
    return _line(session, read, node, writer, unit_disbursement=more)


def category(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The category of a line sent again as it is: a category is priced, inert or not.
    node, view = read.line(f"{LINE}.cost_category_id")
    return _line(session, read, node, writer, cost_category_id=view.cost_category_id)


def role(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The role of a line sent again as it is: a role names a calendar, inert or not.
    node, view = read.line(f"{LINE}.resource_role_id")
    return _line(session, read, node, writer, resource_role_id=view.resource_role_id)


def remaining(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A re-estimate (``setLineRemaining``), which no grid names a field of: never inert.
    node, view = read.line(f"{LINE}.quantity")
    figures = LineEntry(
        quantity=view.quantity + 1,
        sent=frozenset({"quantity"}),
        lock_version=node.lock_version,
    )
    entry = LineRemaining(figures, "entered", None)
    return set_line_remaining(session, read.place, node.node_id, entry, writer)


# Each column a grid accepts, with a write of it on the witness; ``True`` for one whose write moves
# a date or an amount there, which shows why it is not inert, ``None`` for one sent as it is.
COLUMNS: dict[str, tuple[Writing, bool | None]] = {
    "task.label": (label, False),
    "task.description": (description, False),
    "task.order_item_id": (order_item, False),
    "task.work_package_id": (work_package, False),
    "task.tracking": (tracking, False),
    "task.scheduling_mode": (scheduling_mode, None),
    "task.duration": (duration, True),
    "task.start": (start, None),
    "task.finish": (finish, None),
    "task.progress": (progress, None),
    "task.predecessors": (predecessors, None),
    f"{LINE}.label": (line_label, False),
    f"{LINE}.payment_delay_days": (payment_delay, False),
    f"{LINE}.subproject_id": (subproject, False),
    f"{LINE}.quantity": (quantity, True),
    f"{LINE}.hours": (hours, True),
    f"{LINE}.unit_disbursement": (disbursement, True),
    f"{LINE}.cost_category_id": (category, None),
    f"{LINE}.resource_role_id": (role, None),
}


def read_of(witness: Database) -> Read:
    """Read the main structure of the current revision of PRJ-001 whole."""
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        return Read(place, list_nodes(session, place, NodeFilters()))


@dataclass(frozen=True, slots=True)
class Statement:
    """A statement a write sent to the base, and whether the flush of the session sent it."""

    text: str
    flushed: bool


@contextmanager
def listened() -> Generator[list[Statement]]:
    """Keep every statement sent to the base meanwhile, by any engine and any session.

    Those of a route and of the worker too, which open their own: the guard of ``reshaped`` holds
    on the paste, the import of an estimate and the skeleton as on the writes here (#3563).
    The flush flag is one for all the sessions: a statement sent by a session while another
    flushes, in the same thread of the test or not, would be told flushed. The writes here open
    one session at a time, and a route or a worker that runs alone.
    """
    sent: list[Statement] = []
    flushing = [False]

    def flush_starts(*_: object) -> None:
        flushing[0] = True

    def flush_ends(*_: object) -> None:
        flushing[0] = False

    def executing(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        sent.append(Statement(statement, flushing[0]))

    listeners = (
        (Engine, "before_cursor_execute", executing),
        (Session, "before_flush", flush_starts),
        (Session, "after_flush", flush_ends),
    )
    for target, name, listener in listeners:
        event.listen(target, name, listener)
    try:
        yield sent
    finally:
        for target, name, listener in listeners:
            event.remove(target, name, listener)


@dataclass(frozen=True, slots=True)
class Done:
    """What a write gave back, the structure after it, what it read and ran, and what it stored.

    ``reread`` the nodes the replay read again past their objects (``reshaped``), ``stored`` the
    rows of the nodes and of the tasks of the structure once the write is flushed, by key.
    """

    written: NodesWritten
    scheduled_at: datetime
    lock_version: int
    trees_read: int
    engines_run: int
    reread: int = 0
    statements: tuple[Statement, ...] = ()
    stored: tuple[dict[UUID, tuple[Any, ...]], dict[UUID, tuple[Any, ...]]] = ({}, {})


@dataclass(slots=True)
class Counted:
    """How many times a function was called since it was counted."""

    count: int = 0


def counting(
    monkeypatch: pytest.MonkeyPatch, modules: tuple[ModuleType, ...], name: str
) -> Counted:
    """Count the calls of a function by the modules that name it, from now on."""
    counted = Counted()

    def wrapping[**P, R](real: Callable[P, R]) -> Callable[P, R]:
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            counted.count += 1
            return real(*args, **kwargs)

        return wrapped

    for module in modules:
        monkeypatch.setattr(module, name, wrapping(getattr(module, name)))
    return counted


def trees_read(monkeypatch: pytest.MonkeyPatch) -> Counted:
    """Count the trees the writes read whole, as objects of the session, from now on.

    The readings of a write of the tree, under the lock (``writing``), of a replay
    (``rescheduling``), and of an undoing or a redoing (``restoring``): one per write, its replay
    reading none (US-2250). Named by the tests of the writes that create, delete or move nodes.
    """
    return counting(monkeypatch, (writing, rescheduling, restoring), "read_tree")


def stored(session: Session, place: Place) -> tuple[dict[UUID, tuple[Any, ...]], ...]:
    """Give the rows of the nodes and of the tasks of a structure, by key, as stored."""
    session.flush()
    in_structure = select(Node.id).where(
        Node.project_id == place.project_id, Node.structure_id == place.structure_id
    )
    nodes = session.execute(select(Node.__table__).where(Node.id.in_(in_structure))).all()
    tasks = session.execute(select(Task.__table__).where(Task.node_id.in_(in_structure))).all()
    return {each.id: tuple(each) for each in nodes}, {each.node_id: tuple(each) for each in tasks}


def write_counted(
    witness: Database,
    monkeypatch: pytest.MonkeyPatch,
    write: Writing,
    writer: Writer | None = None,
) -> tuple[Read, Done]:
    """Write on the witness, counting what it reads and runs and listening to its statements.

    The trees read, the engines run, the nodes the replay reads again, every statement sent to the
    base and the rows stored once flushed are kept; then it is rolled back.
    """
    read = read_of(witness)
    trees_counted = trees_read(monkeypatch)
    engines = counting(monkeypatch, (rescheduling,), "dated")
    reread: list[int] = []
    real_among = trees.among

    def among_counted(column: Any, values: Any) -> Any:
        if column is Node.id:
            reread.append(len(values))
        return real_among(column, values)

    monkeypatch.setattr(trees, "among", among_counted)
    # The nodes a write creates are named alike from one write to the next, to compare them.
    made = (UUID(int=(1 << 64) + each) for each in count())
    for module in (node_writes, line_writes):
        monkeypatch.setattr(module, "new_id", lambda: next(made))
    place = read.place
    with listened() as sent, Session(witness.engine) as session:
        try:
            held = writer or Writer(Act(None, read.listed.scheduled_at), None)
            written = write(session, read, held)
            facts = structure_facts(session, place.project_id, place.structure_id, lock=False)
            stored_rows = stored(session, place)
        finally:
            session.rollback()
    done = Done(
        written,
        facts.scheduled_at,
        facts.lock_version,
        trees_counted.count,
        engines.count,
        sum(reread),
        tuple(sent),
        (stored_rows[0], stored_rows[1]),
    )
    return read, done


def moved(read: Read, written: NodesWritten) -> bool:
    """Tell whether a write gave back a task redated or an amount moved.

    A task redated, a node priced again, the totals of the structure, or the dates or the amounts
    of the summaries above the nodes written.
    """
    before = {each.node_id: each for each in read.nodes}
    summaries = [
        (each.task.start, each.task.finish, each.task.amounts)
        for each in written.ancestors
        if each.task is not None
    ]
    former = [
        (task.start, task.finish, task.amounts)
        for each in written.ancestors
        if (task := before[each.node_id].task) is not None
    ]
    return (
        bool(written.rescheduled)
        or bool(written.reinflated)
        or written.totals != read.listed.totals
        or summaries != former
    )


def test_every_column_a_grid_accepts_has_its_write_and_the_inert_are_among_them(
    witness: Database,
) -> None:
    read = read_of(witness)
    accepted = {field for each in read.nodes for field in each.editable_fields}
    assert set(COLUMNS) == accepted
    assert accepted >= INERT
    assert set(facets()[LINE].inert) == set(LINE_INERT)
    # A column that moves is declared nowhere inert.
    assert not {field for field, (_, moves) in COLUMNS.items() if moves} & INERT


@pytest.mark.parametrize("field", list(COLUMNS))
def test_a_column_entered_on_the_witness_takes_the_short_path_only_when_inert(
    witness: Database, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    write, moves = COLUMNS[field]
    read, done = write_counted(witness, monkeypatch, write)
    # Every write of the whole path reads the tree once (#3169): under the lock, never again for
    # the replay; the short path none as objects, its structure as rows (US-2250/L2, #3540).
    assert done.trees_read == (0 if field in INERT else 1)
    assert done.lock_version == done.written.structure_lock_version
    if field in INERT:
        # Neither a task redated nor an amount moved; no engine, the instant of the dates kept.
        assert not moved(read, done.written)
        assert done.engines_run == 0
        assert done.scheduled_at == read.listed.scheduled_at
    else:
        assert done.engines_run == 1
    if moves:
        assert moved(read, done.written)


def test_the_counter_advances_by_one_and_the_instant_stays_on_the_short_path(
    witness: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    read = read_of(witness)
    with witness.transaction() as session:
        place = read.place
        before = structure_facts(session, place.project_id, place.structure_id, lock=False)
    later = Writer(Act(None, before.scheduled_at + timedelta(days=3)), None)
    _, short = write_counted(witness, monkeypatch, label, later)
    _, whole = write_counted(witness, monkeypatch, duration, later)
    assert short.lock_version == before.lock_version + 1
    assert short.scheduled_at == before.scheduled_at
    assert whole.lock_version == before.lock_version + 1
    assert whole.scheduled_at == later.act.at


@pytest.mark.parametrize("field", sorted(INERT))
def test_the_short_path_gives_back_what_the_whole_path_does(
    witness: Database, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    write, _ = COLUMNS[field]
    _, short = write_counted(witness, monkeypatch, write)

    def whole(self: Write) -> writing.Redated:
        return self.redate(None)

    monkeypatch.setattr(Write, "count", whole)
    _, replayed = write_counted(witness, monkeypatch, write)
    assert replayed.engines_run == 1
    # The instant of the writes is the structure's: the overdue finishes are judged alike.
    assert short.written == replayed.written
    assert short.written.nodes
    assert short.written.totals is not None


def stacked(witness: Database, read: Read) -> Writer:
    """Give a writer that keeps a stack of the history: an account, a session of sign-in."""
    with witness.transaction() as session:
        author = session.scalars(select(UserAccount.id).order_by(UserAccount.id)).first()
    assert author is not None
    return Writer(Act(author, read.listed.scheduled_at), "inert-session")


@pytest.mark.parametrize("field", sorted(INERT))
def test_a_write_on_the_short_path_is_undone_as_any(witness: Database, field: str) -> None:
    write, _ = COLUMNS[field]
    read = read_of(witness)
    writer = stacked(witness, read)
    place = read.place
    with Session(witness.engine) as session:
        try:
            written = write(session, read, writer)
            node_id = written.nodes[0].node_id
            undone = undo_last_change(session, place.project_id, place.revision_id, writer, ENTRIES)
            again = list_nodes(session, place, NodeFilters())
        finally:
            session.rollback()
    before = next(each for each in read.nodes if each.node_id == node_id)
    after = next(each for each in again.items if each.node_id == node_id)
    assert undone.node_ids == (node_id,)
    # The node is back as it was, but its counter, which the undoing advances again.
    assert replace(after, lock_version=before.lock_version) == before
    assert after.lock_version > written.nodes[0].lock_version


def both(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A label sent with a quantity: one field that is not inert is enough for the whole path.
    node, view = read.line(f"{LINE}.quantity")
    more = view.quantity + Decimal(1)
    return _line(session, read, node, writer, label="entered", quantity=more)


def _children(read: Read) -> dict[UUID | None, list[NodeView]]:
    """Give the children of each node, in the order of the plan, the roots under ``None``."""
    found: dict[UUID | None, list[NodeView]] = {}
    for each in read.nodes:
        found.setdefault(each.parent_id, []).append(each)
    return found


def _untouched(read: Read) -> NodeView:
    """Give the first summary none of whose tasks has started: it may be deleted, or receive."""
    below = _children(read)

    def not_started(node: NodeView) -> bool:
        return (node.task is None or node.task.progress == "not_started") and all(
            not_started(each) for each in below.get(node.node_id, [])
        )

    return read.first(
        lambda each: each.task is not None and each.task.is_summary and not_started(each)
    )


def _facts(session: Session, read: Read) -> StructureFacts:
    place = read.place
    return structure_facts(session, place.project_id, place.structure_id, lock=False)


def create_task(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # At the head of the subtasks of a summary: its subtasks move down by one, in one statement.
    entry = TaskEntry(label="Créée")
    creation = NodeCreation(_untouched(read).node_id, None, after_given=True, task=entry)
    return create_node(session, read.place, creation, writer)


def _head_line(read: Read) -> NodeView:
    """Give the first line of a task not started, at the head of the lines of the task."""
    below = _children(read)
    return read.first(
        lambda each: (
            each.kind == LINE
            and (task := read.first(lambda one: one.node_id == each.parent_id).task) is not None
            and task.progress == "not_started"
            and below[each.parent_id][0].node_id == each.node_id
        )
    )


def create_line(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A line as the first one of a task not started, at the head of its lines, which move down.
    node = _head_line(read)
    view = view_of(node)
    entry = LineEntry(
        label="Créée",
        cost_category_id=view.cost_category_id,
        quantity=view.quantity,
        resource_role_id=view.resource_role_id,
        hours=view.hours,
        unit_disbursement=view.unit_disbursement,
        payment_delay_days=view.payment_delay_days,
        sent=frozenset(
            {
                "label",
                "cost_category_id",
                "quantity",
                "resource_role_id",
                "hours",
                "unit_disbursement",
                "payment_delay_days",
            }
        ),
    )
    creation = NodeCreation(node.parent_id, None, after_given=True, kind=LINE, facet=entry)
    return create_node(session, read.place, creation, writer)


def delete(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A summary deleted with its subtree, which follows it by the keys of the base.
    node = _untouched(read)
    return delete_node(session, read.place, node.node_id, node.lock_version, writer)


def move(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A summary moved at the head of the tasks of the first level: its siblings there move down.
    node = _untouched(read)
    counter = _facts(session, read).lock_version
    moving = NodeMoving((node.node_id,), None, None, after_given=True, lock_version=counter)
    return move_nodes(session, read.place, moving, writer)


def structure(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The start of the structure moved a week on: its automatic tasks are redated.
    facts = _facts(session, read)
    later = facts.planning_start_on + timedelta(days=7)
    change = StructureChange(later, None, facts.lock_version)
    return update_cost_structure(session, read.place, change, writer)


def _undone(session: Session, read: Read, writer: Writer, turn: Any = undo_last_change) -> Any:
    place = read.place
    return turn(session, place.project_id, place.revision_id, writer, ENTRIES).written


def undo_deletion(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The subtree deleted created again.
    delete(session, read, writer)
    return _undone(session, read, writer)


def redo_deletion(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The subtree created again deleted again.
    undo_deletion(session, read, writer)
    return _undone(session, read, writer, redo_last_undo)


def undo_creation(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The task created deleted, its siblings moved back up.
    create_task(session, read, writer)
    return _undone(session, read, writer)


def _leaf_tasks(read: Read, keep: Callable[[NodeView], bool]) -> list[NodeView]:
    """Give the tasks not started and not summaries that ``keep`` retains, in plan order."""
    return [
        each
        for each in read.nodes
        if each.task is not None
        and not each.task.is_summary
        and each.task.progress == "not_started"
        and keep(each)
    ]


def _not_a_milestone(node: NodeView) -> bool:
    return node.task is not None and not node.task.is_milestone


def move_between_parents(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A task moved from its summary to the end of another one, with its lines and its links.
    node = _leaf_tasks(read, _not_a_milestone)[0]
    target = read.first(
        lambda each: (
            each.task is not None
            and each.task.is_summary
            and each.node_id not in (node.node_id, node.parent_id)
            and _is_untouched(read, each)
        )
    )
    counter = _facts(session, read).lock_version
    moving = NodeMoving(
        (node.node_id,), target.node_id, None, after_given=False, lock_version=counter
    )
    return move_nodes(session, read.place, moving, writer)


def move_line(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A line given to another task, by the write of the lines of an import (``write_lines``).
    tasks = _leaf_tasks(read, lambda each: any(one.kind == LINE for one in _under(read, each)))
    giver, receiver = tasks[0], tasks[1]
    line = next(one for one in _under(read, giver) if one.kind == LINE)
    lines = LinesWrite({receiver.node_id: (line.node_id,)}, {}, ())
    return write_lines(session, read.place, lines, writer)


def _under(read: Read, node: NodeView) -> list[NodeView]:
    return _children(read).get(node.node_id, [])


def _is_untouched(read: Read, node: NodeView) -> bool:
    below = _children(read)

    def not_started(one: NodeView) -> bool:
        return (one.task is None or one.task.progress == "not_started") and all(
            not_started(each) for each in below.get(one.node_id, [])
        )

    return not_started(node)


def _made_summary(session: Session, read: Read, writer: Writer) -> tuple[NodeView, NodesWritten]:
    """Make a leaf manual, then give it a subtask: it becomes an automatic summary."""
    leaf = _leaf_tasks(read, _not_a_milestone)[0]
    manual = TaskEntry(
        scheduling_mode="manual",
        sent=frozenset({"scheduling_mode"}),
        lock_version=leaf.lock_version,
    )
    update_task_facet(session, read.place, leaf.node_id, manual, writer)
    creation = NodeCreation(leaf.node_id, None, after_given=True, task=TaskEntry(label="Créée"))
    return leaf, create_node(session, read.place, creation, writer)


def create_under_leaf(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # A manual leaf receives a subtask and becomes an automatic summary.
    return _made_summary(session, read, writer)[1]


def delete_only_child(session: Session, read: Read, writer: Writer) -> NodesWritten:
    # The only subtask of a summary deleted: the summary is a leaf again, with its own dates.
    leaf, created = _made_summary(session, read, writer)
    child = next(each for each in created.nodes if each.parent_id == leaf.node_id)
    return delete_node(session, read.place, child.node_id, child.lock_version, writer)


# The writes of the whole path, with how many writes each makes: each column that is not inert, a
# line sent with an inert field and another, a re-estimate; then the writes that create, delete or
# move nodes, a write of the structure itself, an undoing and a redoing (US-2250).
WHOLE: dict[str, tuple[Writing, int]] = {
    **{field: (write, 1) for field, (write, _) in COLUMNS.items() if field not in INERT},
    "line label and quantity": (both, 1),
    "remaining": (remaining, 1),
    "createNode task": (create_task, 1),
    "createNode line": (create_line, 1),
    "deleteNode": (delete, 1),
    "moveNodes": (move, 1),
    "updateCostStructure": (structure, 1),
    "undoLastChange deletion": (undo_deletion, 2),
    "redoLastUndo deletion": (redo_deletion, 3),
    "undoLastChange creation": (undo_creation, 2),
    "moveNodes between two parents": (move_between_parents, 1),
    "write_lines moving a line": (move_line, 1),
    "deleteNode giving a leaf back": (delete_only_child, 3),
    "createNode under a leaf": (create_under_leaf, 2),
}


def _shifted_by_task(read: Read) -> int:
    """Count the subtasks a task created at the head of those of a summary moves down."""
    return len(_children(read)[_untouched(read).node_id])


def _shifted_by_line(read: Read) -> int:
    """Count the lines a line created at the head of those of a task moves down."""
    return len(_children(read)[_head_line(read).parent_id])


def _subtree(read: Read) -> int:
    """Count the nodes of the subtree of the summary a deletion takes, itself included."""
    below = _children(read)

    def size(node: UUID) -> int:
        return 1 + sum(size(each.node_id) for each in below.get(node, []))

    return size(_untouched(read).node_id)


# The nodes ``reshaped`` reads again, where a write has nodes past its objects: the node it
# creates, read with its facet, and the siblings it moves down by one in one statement; the nodes
# an undoing creates again, the subtree a deletion took. The others read none: a duration, a
# deletion, a move through the objects, a write of the lines; the redoing of a deletion is held
# by the undoing it follows.
REREAD: dict[str, Callable[[Read], int]] = {
    "createNode task": lambda read: _shifted_by_task(read) + 1,
    "createNode line": lambda read: _shifted_by_line(read) + 1,
    "undoLastChange deletion": _subtree,
    "redoLastUndo deletion": _subtree,
    "undoLastChange creation": lambda read: _shifted_by_task(read) + 1,
    "deleteNode giving a leaf back": lambda _: 1,
    "createNode under a leaf": lambda _: 1,
}


@pytest.mark.parametrize("name", list(WHOLE))
def test_the_whole_path_reads_the_tree_once_and_gives_back_what_it_did_reading_it_twice(
    witness: Database, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    write, writes = WHOLE[name]
    writer = stacked(witness, read_of(witness))
    read, once = write_counted(witness, monkeypatch, write, writer)

    def read_again(session: Session, project_id: UUID, structure_id: UUID, _: object) -> Tree:
        return rescheduling.read_tree(session, project_id, structure_id)

    monkeypatch.setattr(rescheduling, "reshaped", read_again)
    _, twice = write_counted(witness, monkeypatch, write, writer)
    assert once.engines_run == writes
    # Once per write, under the lock: the replay brings that tree to the write (``reshaped``).
    assert once.trees_read == writes
    assert twice.trees_read == 2 * writes
    assert once.written == twice.written
    # The structure as stored is the same: dates, ranks, parents, flags, counters.
    assert once.stored[0] == twice.stored[0]
    assert once.stored[1] == twice.stored[1]
    # The nodes read again are those a statement wrote past their objects, and no others.
    assert once.reread == REREAD.get(name, lambda _: 0)(read)


# The statements of every write, short or whole, as the base received them. The paste, the
# application of an import of an estimate and the skeleton are held where their tests write them,
# through the routes and the worker (``listened``, #3563).
EVERY = {
    **{field: write for field, (write, _) in COLUMNS.items()},
    **{k: w for k, (w, _) in WHOLE.items()},
}


def _set_of(statement: str) -> str:
    return statement.split(" WHERE", maxsplit=1)[0]


# The counter of a node advanced by a statement, not only named in its ``SET`` (#3563); SQLAlchemy
# writes the sum between parentheses.
_ADVANCED = re.compile(r"lock_version\s*=\s*\(?\s*node\.lock_version\s*\+")


def unkept(statements: Iterable[Statement]) -> list[str]:
    """Give the statements that break what ``reshaped`` rests on.

    A statement of an instruction that writes a node without advancing its counter, and one that
    writes a facet task. The flush of the objects of the session is left out: a node it writes is
    one whose object holds the counter, which ``reshaped`` compares with the row. The ``UPDATE``
    alone: a node an ``INSERT`` creates or a ``DELETE`` takes is told by its row (``reshaped``).
    """
    return [
        each.text
        for each in statements
        if not each.flushed
        and each.text.startswith(("UPDATE node ", "UPDATE task "))
        and not (each.text.startswith("UPDATE node ") and _ADVANCED.search(_set_of(each.text)))
    ]


@pytest.mark.parametrize("name", list(EVERY))
def test_no_statement_writes_a_node_without_advancing_its_counter_nor_a_task(
    witness: Database, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    writer = stacked(witness, read_of(witness))
    _, done = write_counted(witness, monkeypatch, EVERY[name], writer)
    assert any(each.text.startswith(("UPDATE", "INSERT", "DELETE")) for each in done.statements)
    assert unkept(done.statements) == []


def test_the_statements_that_break_what_reshaped_rests_on_are_told() -> None:
    advancing = (
        "UPDATE node SET rank=node.rank + %(rank_1)s, lock_version=node.lock_version + 1 "
        "WHERE node.id IN (1)"
    )
    assert unkept((Statement(advancing, flushed=False),)) == []
    forgetting = "UPDATE node SET rank=node.rank + %(rank_1)s WHERE node.id IN (1)"
    assert unkept((Statement(forgetting, flushed=False),)) == [forgetting]
    # As SQLAlchemy writes it; named, not advanced, the counter set to itself is told (#3563).
    rendered = "UPDATE node SET lock_version=(node.lock_version + %(lv_1)s::INTEGER) WHERE true"
    assert unkept((Statement(rendered, flushed=False),)) == []
    naming = "UPDATE node SET lock_version=node.lock_version WHERE node.id IN (1)"
    assert unkept((Statement(naming, flushed=False),)) == [naming]
    flushed = "UPDATE node SET rank=%(rank)s::INTEGER WHERE node.id = %(node_id)s::UUID"
    assert unkept((Statement(flushed, flushed=True),)) == []
    by_objects = "UPDATE task SET label=%(label)s WHERE task.node_id = %(task_node_id)s"
    assert unkept((Statement(by_objects, flushed=True),)) == []
    by_statement = "UPDATE task SET label=%(label)s WHERE task.node_id IN (1)"
    assert unkept((Statement(by_statement, flushed=False),)) == [by_statement]
