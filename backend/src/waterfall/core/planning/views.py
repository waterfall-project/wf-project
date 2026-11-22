# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The nodes of a structure as the planning gives them to read, private to the module.

What ``listNodes`` and every write of the tree give back (``Node``, ``NodesWritten``): each node
with what is computed on the whole structure — its number, its level, its place —, its facet task
with what the planning derives at the reading — the state of a summary from its subordinates and
its own lines (WF-PLA-0040), whether it awaits only these (``awaiting_own_lines``, #1775; US-1590),
the finish overdue of a started task (WF-RAE-0040), its calendar (WF-PLA-0010), its
links in conflict (WF-PLA-0020) —, its predecessors named by their number (WF-PLA-0080), and the
fields it computes and accepts (``computed_fields``, ``editable_fields``, WF-IHM-0030, WF-IHM-0040).
A node of another kind — an estimate line, EP-07 — is read by the hooks of its facet
(``FacetHooks.read``), opaque here, which say its fields; the amounts of a task are the sum of the
figures of its lines and of its subordinates (``FacetHooks.totals``), computed at the reading and
never kept (EP-07, "Le calcul des montants"). The physical progress of a summary is the
indicators' (``register_physical_progress``, US-1680): a reading asks it once, for the summaries it
gives — every summary for one that gives views, a write or a comparison, which gives them one by
one —, from the tasks it holds and their states. The interface re-exports the views; the API
writes them as the contract does.

A reading that writes nothing — ``listNodes`` — gives the same values without the views: a record
by node, flat (``TaskRecord``, ``FacetRecord``), whose body the API writes; a view is made a record
(``record_of``) for what a write gives back, written alike (US-2220, EP-26, "La lecture d'une
structure").
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, NamedTuple

from waterfall.core.planning.interface.facets import Amounts, BearingTask, facets
from waterfall.core.planning.interface.physical_progress import (
    ProgressTask,
    SummariesAsked,
    physical_progress_of,
)
from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.tree import TASK, NodeRow, TaskRow, tracking_of
from waterfall.core.projects.interface import work_breakdown_items

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping, Sequence
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.interface.facets import FacetColumns, FacetRead, Tally
    from waterfall.core.planning.interface.physical_progress import PhysicalShare
    from waterfall.core.planning.tables import Node, Task
    from waterfall.core.planning.tree import LinkColumns, NodeColumns, TaskColumns, Tree
    from waterfall.core.planning.writing import Place

MANUAL = "manual"
NOT_STARTED = "not_started"
STARTED = "started"
COMPLETED = "completed"
# What the planning computes and accepts of a task, in the orders of ``ComputedField`` and
# ``EditableField``.
SUMMARY_COMPUTED = ("task.scheduling_mode", "task.duration", "task.start", "task.finish")
DATES = ("task.start", "task.finish")
PROGRESS = "task.progress"
ATTACHMENT_AND_TRACKING = ("task.order_item_id", "task.work_package_id", "task.tracking")


@dataclass(frozen=True, slots=True)
class ConflictView:
    """A link in conflict, named by its two tasks and its type (``LinkConflict``)."""

    predecessor_id: UUID
    successor_id: UUID
    link_type: str


@dataclass(frozen=True, slots=True)
class PredecessorView:
    """A predecessor of a task: its node, its number in the structure, its type and its lag."""

    predecessor_id: UUID
    row_number: int
    link_type: str
    lag_value: Decimal
    lag_unit: str


@dataclass(frozen=True, slots=True)
class TrackingView:
    """An inscription of a task: to a timeline, or to the time/time tracking (no timeline)."""

    kind: str
    timeline_id: UUID | None


@dataclass(frozen=True, slots=True)
class TaskView:
    """The facet task of a node as it is read (``TaskFacet``), its derived values computed.

    ``awaiting_own_lines`` tells a summary started whose subordinates are all completed, which an
    own line holds open (WF-PLA-0040); ``calendar_hours`` are the hours of the applicable calendar,
    Monday first; ``total_float`` is in days, none for a task in manual mode and for a summary none
    of whose subordinates has one; ``physical_progress`` a summary's, as the indicators answer it
    (``register_physical_progress``), none for a task that is no summary or while none answers.
    """

    label: str
    description: str | None
    scheduling_mode: str
    duration_value: Decimal
    duration_unit: str
    start: WorkInstant
    finish: WorkInstant
    progress: str
    started_on: date | None
    completed_on: date | None
    finish_overdue: bool
    awaiting_own_lines: bool
    is_summary: bool
    is_milestone: bool
    calendar_id: UUID | None
    calendar_hours: tuple[Decimal, ...]
    total_float: Decimal | None
    is_critical: bool
    link_conflicts: tuple[ConflictView, ...]
    tracking: tuple[TrackingView, ...]
    order_item_id: UUID | None
    work_package_id: UUID | None
    work_breakdown_label: str | None
    external_id: str | None
    amounts: Amounts
    physical_progress: PhysicalShare | None


@dataclass(frozen=True, slots=True)
class NodeView:
    """A node of a structure as it is read (``Node``): a task, or a node of another kind.

    ``facet`` is the facet of a node of another kind, as its hooks read it; none for a task.
    """

    node_id: UUID
    lineage_id: UUID
    kind: str
    parent_id: UUID | None
    position: int
    row_number: int
    level: int
    origin_risk_id: UUID | None
    lock_version: int
    task: TaskView | None
    facet: FacetRead | None
    predecessors: tuple[PredecessorView, ...]
    computed_fields: tuple[str, ...]
    editable_fields: tuple[str, ...]


class TaskRecord(NamedTuple):
    """A task as a reading that writes nothing returns it: its view and its facet's, flat.

    What ``NodeView`` and its ``TaskView`` hold, in one record (US-2220, EP-26, "La lecture d'une
    structure"). ``listNodes`` builds one for each task it returns, without the views; the API
    writes the body of the contract from it. A view is made a record by ``record_of``.
    """

    node_id: UUID
    lineage_id: UUID
    parent_id: UUID | None
    position: int
    row_number: int
    level: int
    origin_risk_id: UUID | None
    lock_version: int
    predecessors: tuple[PredecessorView, ...]
    computed_fields: tuple[str, ...]
    editable_fields: tuple[str, ...]
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
    finish_overdue: bool
    awaiting_own_lines: bool
    is_summary: bool
    is_milestone: bool
    calendar_id: UUID | None
    calendar_hours: tuple[Decimal, ...]
    total_float: Decimal | None
    is_critical: bool
    link_conflicts: tuple[ConflictView, ...]
    tracking: tuple[TrackingView, ...]
    order_item_id: UUID | None
    work_package_id: UUID | None
    work_breakdown_label: str | None
    external_id: str | None
    amounts: Amounts
    physical_progress: PhysicalShare | None


class FacetRecord(NamedTuple):
    """A node of another kind as a reading that writes nothing returns it, flat (US-2220).

    ``facet`` is its facet as its hooks read it, opaque here; none for a node its facet does not
    read, which names no field. The fields it computes and accepts are its facet's, but those of a
    view made a record, which its reader may have changed (a comparison accepts none).
    """

    node_id: UUID
    lineage_id: UUID
    kind: str
    parent_id: UUID | None
    position: int
    row_number: int
    level: int
    origin_risk_id: UUID | None
    lock_version: int
    predecessors: tuple[PredecessorView, ...]
    computed_fields: tuple[str, ...]
    editable_fields: tuple[str, ...]
    facet: FacetRead | None


# A node as a reading that writes nothing returns it: a task, or a node of another kind.
type NodeRecord = TaskRecord | FacetRecord


def record_of(view: NodeView) -> NodeRecord:
    """Make a node as it is read, whole, a record: what a write gives back is written alike."""
    task = view.task
    if task is None:
        return FacetRecord(
            view.node_id,
            view.lineage_id,
            view.kind,
            view.parent_id,
            view.position,
            view.row_number,
            view.level,
            view.origin_risk_id,
            view.lock_version,
            view.predecessors,
            view.computed_fields,
            view.editable_fields,
            view.facet,
        )
    return TaskRecord(
        node_id=view.node_id,
        lineage_id=view.lineage_id,
        parent_id=view.parent_id,
        position=view.position,
        row_number=view.row_number,
        level=view.level,
        origin_risk_id=view.origin_risk_id,
        lock_version=view.lock_version,
        predecessors=view.predecessors,
        computed_fields=view.computed_fields,
        editable_fields=view.editable_fields,
        label=task.label,
        description=task.description,
        scheduling_mode=task.scheduling_mode,
        duration_value=task.duration_value,
        duration_unit=task.duration_unit,
        start_date=task.start.day,
        start_hours=task.start.hours,
        finish_date=task.finish.day,
        finish_hours=task.finish.hours,
        progress=task.progress,
        started_on=task.started_on,
        completed_on=task.completed_on,
        finish_overdue=task.finish_overdue,
        awaiting_own_lines=task.awaiting_own_lines,
        is_summary=task.is_summary,
        is_milestone=task.is_milestone,
        calendar_id=task.calendar_id,
        calendar_hours=task.calendar_hours,
        total_float=task.total_float,
        is_critical=task.is_critical,
        link_conflicts=task.link_conflicts,
        tracking=task.tracking,
        order_item_id=task.order_item_id,
        work_package_id=task.work_package_id,
        work_breakdown_label=task.work_breakdown_label,
        external_id=task.external_id,
        amounts=task.amounts,
        physical_progress=task.physical_progress,
    )


@dataclass(frozen=True, slots=True)
class ScheduleView:
    """The schedule of a task a write redated without writing it (``NodeSchedule``)."""

    node_id: UUID
    start: WorkInstant
    finish: WorkInstant
    total_float: Decimal | None
    is_critical: bool
    link_conflicts: tuple[ConflictView, ...]
    finish_overdue: bool


@dataclass(frozen=True, slots=True)
class State:
    """The state of a task and its two dates, a summary's derived from its subordinates."""

    progress: str
    started_on: date | None
    completed_on: date | None


def _derived(states: list[State], own: tuple[bool, date | None] = (False, None)) -> State:
    """Give the state of a summary: started as soon as one is, completed when all are (0040).

    ``own`` is what its own lines tell: whether one holds it open, and the day they were set to
    nought, if that completed it. Held, it stays started when all its subordinates are completed.
    Its start date is the first of its subordinates', its completion date the last of theirs and
    of that day (WF-PLA-0130).
    """
    held, closed_on = own
    started = [state.started_on for state in states if state.started_on is not None]
    first = min(started, default=None)
    if not held and all(state.progress == COMPLETED for state in states):
        completed = [state.completed_on for state in states if state.completed_on is not None]
        completed += [closed_on] if closed_on is not None else []
        return State(COMPLETED, first, max(completed, default=None))
    if any(state.progress != NOT_STARTED for state in states):
        return State(STARTED, first, None)
    return State(NOT_STARTED, None, None)


def own_lines[N: NodeColumns, T: TaskColumns](
    tree: Tree[N, T], node_id: UUID
) -> tuple[bool, date | None]:
    """Tell what the own lines of a summary tell its state: held open, and the day they closed.

    Held, as the tree was read (``Tree.held``). The day is the one the entry that set the last of
    them to nought completed the summary at (``write_remaining``), kept on its facet; a summary
    that bears no line besides the provisions has none.
    """
    task = tree.tasks[node_id]
    lines = bool(tree.own_lines(node_id))
    closed = task.completed_on if lines and task.progress == COMPLETED else None
    return node_id in tree.held, closed


def state_of[N: NodeColumns, T: TaskColumns](tree: Tree[N, T], node_id: UUID) -> State:
    """Give the state of a task of a tree: its own for a leaf, derived for a summary (0040).

    A summary's, from its subordinates and from its own lines (``own_lines``).
    """
    below = tree.subtasks(node_id)
    if below:
        return _derived([state_of(tree, child) for child in below], own_lines(tree, node_id))
    task = tree.tasks[node_id]
    return State(task.progress, task.started_on, task.completed_on)


def states_without(
    tree: Tree, gone: Collection[UUID], own: Mapping[UUID, tuple[bool, date | None]]
) -> dict[UUID, State]:
    """Give the state each ancestor of tasks will have once they and their subtrees are gone.

    Derived from the subordinates left (WF-PLA-0040), and from what ``own`` tells of the own lines
    of a summary — held open, and the day they closed it —, ``own_lines`` for one it does not name.
    A summary left without subordinate becomes a leaf in the state it had (``emptied``). The
    deepest first, so that a summary reads the state its subordinates will have.
    """
    left = set(gone)
    above = {each for node_id in left for each in tree.ancestors(node_id)}
    found: dict[UUID, State] = {}
    for each in sorted(above, key=tree.level.__getitem__, reverse=True):
        below = [sub for sub in tree.subtasks(each) if sub not in left]
        if not below:
            found[each] = state_of(tree, each)
            continue
        states = [found[sub] if sub in found else state_of(tree, sub) for sub in below]
        found[each] = _derived(states, own.get(each, own_lines(tree, each)))
    return found


def awaits[N: NodeColumns, T: TaskColumns](
    tree: Tree[N, T], node_id: UUID, states: list[State]
) -> bool:
    """Tell whether a summary awaits only its own lines: its subordinates' ``states`` completed.

    An own line holds it open (``Tree.held``); a leaf never awaits, whatever its lines (#1775).
    """
    return (
        bool(states)
        and node_id in tree.held
        and all(state.progress == COMPLETED for state in states)
    )


def derived_states[N: NodeColumns, T: TaskColumns](
    tree: Tree[N, T], own: Callable[[UUID], tuple[bool, date | None]]
) -> dict[UUID, State]:
    """Give the state of each task of a tree: its own for a leaf, derived for a summary (0040).

    The deepest first, each summary from its subordinates and from what ``own`` tells of its own
    lines (``own_lines``, ``tallied_own_lines``): what a reading derives, and what the indicators
    read of the tasks alone (#3902).
    """
    states: dict[UUID, State] = {}
    for node_id in reversed(tree.order):
        if node_id not in tree.tasks:
            continue
        below = tree.subtasks(node_id)
        if below:
            states[node_id] = _derived([states[child] for child in below], own(node_id))
        else:
            task = tree.tasks[node_id]
            states[node_id] = State(task.progress, task.started_on, task.completed_on)
    return states


def tallied_own_lines[N: NodeColumns, T: TaskColumns](
    tree: Tree[N, T], tallies: Mapping[UUID, Tally], node_id: UUID
) -> tuple[bool, date | None]:
    """Tell what the own lines of a summary tell its state, from its tallies (``own_lines``).

    For a tree of the tasks alone, none of their lines read (US-2280).
    """
    tally = tallies.get(node_id)
    task = tree.tasks[node_id]
    own = tally is not None and tally.own
    closed = task.completed_on if own and task.progress == COMPLETED else None
    return node_id in tree.held, closed


class Reading[N: NodeColumns = Node, T: TaskColumns = Task]:
    """What a reading derives of a structure, once for all its nodes.

    Of a tree of objects of the session, as a write reads it, or of rows, as a reading that writes
    nothing reads it (``read_rows``, US-2220): the same views of the same columns. A write reads
    the facets of the other kinds by ``FacetHooks.totals`` and ``FacetHooks.read``; a reading that
    writes nothing reads them as rows too (``RowsReading``).
    """

    # Whether the facets of the other kinds are read once as rows (``FacetHooks.columns``).
    read_only: ClassVar[bool] = False

    def __init__(
        self,
        session: Session,
        structure: tuple[Place, datetime, bool],
        tree: Tree[N, T],
        links: Sequence[LinkColumns],
        calendars: dict[UUID, Applicable],
    ) -> None:
        """Read the inscriptions of the tasks and the labels of what they bear; derive the states.

        ``structure`` is the structure, the instant of its dates, and whether it is the main one.
        """
        self.place, scheduled_at, self.is_main = structure
        project_id = self.place.project_id
        self.tree = tree
        self.calendars = calendars
        self.scheduled_on = scheduled_at.date()
        self.links = links
        # The links by their successor, and by each end, built once: a node asks for its own.
        self._incoming: dict[UUID, list[LinkColumns]] = {}
        self._ends: dict[UUID, list[LinkColumns]] = {}
        for link in links:
            self._incoming.setdefault(link.successor_id, []).append(link)
            for end in {link.predecessor_id, link.successor_id}:
                self._ends.setdefault(end, []).append(link)
        lineages = {tree.nodes[node_id].lineage_id for node_id in tree.tasks}
        self.tracking = tracking_of(session, project_id, lineages)
        # The label of a work package or an order item borne, one marked deleted included, which
        # a marked revision still shows (WF-PLA-0170).
        borne = any(task.work_package_id or task.order_item_id for task in tree.tasks.values())
        self.items = work_breakdown_items(session, project_id) if borne else {}
        self._session, self._project_id = session, project_id
        # The figures of each node of another kind, read once by the hooks of its facet; the
        # facets as read, asked for the nodes a reading returns (``prefetch``).
        self.figures: dict[UUID, Amounts] = {}
        self._columns: dict[str, FacetColumns] = {}
        for kind, hooks in facets().items():
            held = [each for each, node in tree.nodes.items() if node.kind == kind]
            if not held:
                continue
            if self.read_only:
                self._columns[kind] = hooks.columns(session, project_id, held)
                self.figures.update(self._columns[kind].figures)
            else:
                self.figures.update(hooks.totals(session, project_id, held))
        self._facets: dict[UUID, FacetRead] = {}
        # The physical progress of the summaries asked already, and those asked (``progress``).
        self._shares: dict[UUID, PhysicalShare] = {}
        self._asked: set[UUID] = set()
        self.states = derived_states(tree, self._own_lines)
        self.awaiting: set[UUID] = set()
        self.summaries: set[UUID] = set()
        self.sums: dict[UUID, Amounts] = {}
        for node_id in reversed(tree.order):
            if node_id not in tree.tasks:
                continue
            below = tree.subtasks(node_id)
            if below:
                self.summaries.add(node_id)
                if awaits(tree, node_id, [self.states[child] for child in below]):
                    self.awaiting.add(node_id)
            total = self._lines_total(node_id)
            for each in below:
                total += self.sums[each]
            self.sums[node_id] = total

    def _own_lines(self, node_id: UUID) -> tuple[bool, date | None]:
        """Tell what the own lines of a summary tell its state (``own_lines``)."""
        return own_lines(self.tree, node_id)

    def _lines_total(self, node_id: UUID) -> Amounts:
        """Give the sum of the figures of the lines a task bears, read once (``figures``)."""
        total = Amounts()
        for each in self.tree.lines(node_id):
            total += self.figures.get(each, Amounts())
        return total

    def _tallies(self) -> Mapping[UUID, Tally] | None:
        """Give what the reading counted already under each task, none if it counted nothing."""
        return None

    def progress(self, node_ids: Collection[UUID]) -> None:
        """Ask the physical progress of the summaries among the nodes named not asked yet.

        Once for them all (``register_physical_progress``), from every task of the tree and its
        state: what a reading gives is asked before it is given, so that it asks once.
        """
        asked = frozenset(
            each for each in node_ids if each in self.summaries and each not in self._asked
        )
        if not asked:
            return
        tree = self.tree
        tasks = {
            each: ProgressTask(tree.nodes[each].parent_id, self.states[each].progress == COMPLETED)
            for each in tree.tasks
        }
        summaries = SummariesAsked(self.place, asked, tasks, self._tallies())
        self._shares.update(physical_progress_of(self._session, summaries))
        self._asked |= asked

    def physical_progress(self, node_id: UUID) -> PhysicalShare | None:
        """Give the physical progress of a summary asked, none for another task or none answered."""
        return self._shares.get(node_id)

    def bearer(self, task_id: UUID) -> BearingTask:
        """Give a task as the facet of a node it bears is told of it."""
        task = self.tree.tasks[task_id]
        return BearingTask(
            task_id,
            self.tree.nodes[task_id].revision_id,
            task.label,
            WorkInstant(task.start_date, task.start_hours),
            WorkInstant(task.finish_date, task.finish_hours),
            self.calendars[task_id].calendar.week,
            self.states[task_id].progress,
            self.is_main,
        )

    def prefetch(self, node_ids: Collection[UUID]) -> None:
        """Read once the facets of the nodes of another kind among those named.

        Each task told once, however many nodes it bears: a structure read whole bears thousands.
        """
        tree = self.tree
        bearers: dict[UUID, BearingTask] = {}
        for kind, hooks in facets().items():
            held = {
                each: bearers.get(parent) or bearers.setdefault(parent, self.bearer(parent))
                for each in node_ids
                if each not in self._facets
                and tree.nodes[each].kind == kind
                and (parent := tree.nodes[each].parent_id) is not None
            }
            if not held:
                continue
            columns = self._columns.get(kind)
            if columns is None:
                self._facets.update(hooks.read(self._session, self._project_id, held))
            else:
                self._facets.update(columns.read(held))

    def totals(self, node_ids: Collection[UUID]) -> Amounts:
        """Give the sum of the figures of the nodes of another kind among those named."""
        total = Amounts()
        for each in node_ids:
            if each in self.figures:
                total += self.figures[each]
        return total

    def conflicts(self, node_id: UUID) -> tuple[ConflictView, ...]:
        """Give the links in conflict a task is an end of, in the order of the plan (0020)."""
        return () if self.tree.is_summary(node_id) else self._conflicts(node_id)

    def _conflicts(self, node_id: UUID) -> tuple[ConflictView, ...]:
        """Give the links in conflict a task that is no summary is an end of (0020)."""
        row = self.tree.row_number
        held = sorted(
            (link for link in self._ends.get(node_id, []) if link.in_conflict),
            key=lambda link: (row[link.predecessor_id], row[link.successor_id]),
        )
        return tuple(
            ConflictView(link.predecessor_id, link.successor_id, link.link_type) for link in held
        )

    def _overdue(self, node_id: UUID) -> bool:
        task = self.tree.tasks[node_id]
        state = self.states[node_id]
        return state.progress == STARTED and task.finish_date < self.scheduled_on

    def schedule(self, node_id: UUID) -> ScheduleView:
        """Give the schedule of a task, as a write that redated it gives it."""
        task = self.tree.tasks[node_id]
        return ScheduleView(
            node_id,
            WorkInstant(task.start_date, task.start_hours),
            WorkInstant(task.finish_date, task.finish_hours),
            task.total_float_days,
            task.is_critical,
            self.conflicts(node_id),
            self._overdue(node_id),
        )

    def _fields(
        self, task: TaskColumns, *, summary: bool, milestone: bool
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Give what the server computes of a task, and what it accepts (WF-IHM-0030, 0040)."""
        attached = ATTACHMENT_AND_TRACKING if self.is_main else ()
        if summary:
            computed = (*SUMMARY_COMPUTED, PROGRESS)
            editable = ("task.label", "task.description", "task.predecessors", *attached)
            return computed, editable
        manual = task.scheduling_mode == MANUAL
        duration = () if milestone else ("task.duration",)
        editable = (
            "task.label",
            "task.description",
            "task.scheduling_mode",
            *duration,
            *(DATES if manual else ()),
            PROGRESS,
            "task.predecessors",
            *attached,
        )
        return (() if manual else DATES), editable

    def _task(self, node_id: UUID) -> TaskView:
        tree = self.tree
        task = tree.tasks[node_id]
        state = self.states[node_id]
        applicable = self.calendars[node_id]
        lineage = tree.nodes[node_id].lineage_id
        # A view is given one by one: the first summary asks for every summary of the structure.
        if node_id in self.summaries:
            self.progress(self.summaries)
        return TaskView(
            label=task.label,
            description=task.description,
            scheduling_mode=task.scheduling_mode,
            duration_value=task.duration_value,
            duration_unit=task.duration_unit,
            start=WorkInstant(task.start_date, task.start_hours),
            finish=WorkInstant(task.finish_date, task.finish_hours),
            progress=state.progress,
            started_on=state.started_on,
            completed_on=state.completed_on,
            finish_overdue=self._overdue(node_id),
            awaiting_own_lines=node_id in self.awaiting,
            is_summary=tree.is_summary(node_id),
            is_milestone=tree.is_milestone(node_id),
            calendar_id=applicable.calendar_id,
            calendar_hours=applicable.calendar.week,
            total_float=task.total_float_days,
            is_critical=task.is_critical,
            link_conflicts=self.conflicts(node_id),
            tracking=tuple(
                TrackingView(entry.kind, entry.timeline_id)
                for entry in self.tracking.get(lineage, [])
            ),
            order_item_id=task.order_item_id,
            work_package_id=task.work_package_id,
            work_breakdown_label=self._borne(task.work_package_id or task.order_item_id),
            external_id=task.external_id,
            amounts=self.sums[node_id],
            physical_progress=self.physical_progress(node_id),
        )

    def _borne(self, item_id: UUID | None) -> str | None:
        item = None if item_id is None else self.items.get(item_id)
        return None if item is None else item.label

    def _predecessors(self, node_id: UUID) -> tuple[PredecessorView, ...]:
        """Give the predecessors of a node, in the order of the plan (WF-PLA-0080)."""
        incoming = self._incoming.get(node_id)
        if not incoming:
            return ()
        row = self.tree.row_number
        return tuple(
            PredecessorView(
                link.predecessor_id,
                row[link.predecessor_id],
                link.link_type,
                link.lag_value,
                link.lag_unit,
            )
            for link in sorted(incoming, key=lambda link: row[link.predecessor_id])
        )

    def node(self, node_id: UUID) -> NodeView:
        """Give a node as it is read, whole."""
        tree = self.tree
        node = tree.nodes[node_id]
        facet = None
        computed: tuple[str, ...] = ()
        editable: tuple[str, ...] = ()
        if node.kind == TASK:
            computed, editable = self._fields(
                tree.tasks[node_id],
                summary=tree.is_summary(node_id),
                milestone=tree.is_milestone(node_id),
            )
        else:
            if node_id not in self._facets:
                self.prefetch((node_id,))
            # A node its facet does not read — written around the service — names no field.
            facet = self._facets.get(node_id)
            if facet is not None:
                computed, editable = facet.computed_fields, facet.editable_fields
        return NodeView(
            node_id=node_id,
            lineage_id=node.lineage_id,
            kind=node.kind,
            parent_id=node.parent_id,
            position=tree.position[node_id],
            row_number=tree.row_number[node_id],
            level=tree.level[node_id],
            origin_risk_id=node.origin_risk_id,
            lock_version=node.lock_version,
            task=self._task(node_id) if node.kind == TASK else None,
            facet=facet,
            predecessors=self._predecessors(node_id),
            computed_fields=computed,
            editable_fields=editable,
        )

    def records(self, node_ids: Sequence[UUID], *, progress: bool = True) -> list[NodeRecord]:
        """Give the nodes named as records, in their order: what ``node`` gives, without its views.

        Each node's columns and derived values looked up once, the facets of the other kinds read
        once for them all (``prefetch``): a structure read whole returns six thousand nodes, which
        the API writes from these records (US-2220). The physical progress of the summaries among
        them is asked once too (``progress``), unless the reading says it gives none: a projection
        that names no physical progress asks nothing of the tallies of the structure.
        """
        self.prefetch(node_ids)
        if progress:
            self.progress(node_ids)
        nodes, tasks = self.tree.nodes, self.tree.tasks
        return [
            self._task_record(node_id, node, tasks[node_id])
            if (node := nodes[node_id]).kind == TASK
            else self._facet_record(node_id, node)
            for node_id in node_ids
        ]

    def _facet_record(self, node_id: UUID, node: N) -> FacetRecord:
        """Give a node of another kind as a record, its facet read already (``prefetch``)."""
        tree = self.tree
        # A node its facet does not read — written around the service — names no field.
        facet = self._facets.get(node_id)
        return FacetRecord(
            node_id,
            node.lineage_id,
            node.kind,
            node.parent_id,
            tree.position[node_id],
            tree.row_number[node_id],
            tree.level[node_id],
            node.origin_risk_id,
            node.lock_version,
            self._predecessors(node_id),
            () if facet is None else facet.computed_fields,
            () if facet is None else facet.editable_fields,
            facet,
        )

    def _task_record(self, node_id: UUID, node: N, task: T) -> TaskRecord:
        """Give a task as a record: its columns, and what the reading derives of it once.

        The fields are given in the order of ``TaskRecord``, by position: by name, the 39 of them
        cost three times as much to build (1.0 against 0.3 us), six thousand times a reading.
        """
        tree = self.tree
        summary = node_id in self.summaries
        milestone = not summary and task.duration_value == 0
        state = self.states[node_id]
        applicable = self.calendars[node_id]
        computed, editable = self._fields(task, summary=summary, milestone=milestone)
        tracked = self.tracking.get(node.lineage_id)
        return TaskRecord(
            node_id,
            node.lineage_id,
            node.parent_id,
            tree.position[node_id],
            tree.row_number[node_id],
            tree.level[node_id],
            node.origin_risk_id,
            node.lock_version,
            self._predecessors(node_id),
            computed,
            editable,
            task.label,
            task.description,
            task.scheduling_mode,
            task.duration_value,
            task.duration_unit,
            task.start_date,
            task.start_hours,
            task.finish_date,
            task.finish_hours,
            state.progress,
            state.started_on,
            state.completed_on,
            state.progress == STARTED and task.finish_date < self.scheduled_on,
            node_id in self.awaiting,
            summary,
            milestone,
            applicable.calendar_id,
            applicable.calendar.week,
            task.total_float_days,
            task.is_critical,
            () if summary else self._conflicts(node_id),
            ()
            if not tracked
            else tuple(TrackingView(entry.kind, entry.timeline_id) for entry in tracked),
            task.order_item_id,
            task.work_package_id,
            self._borne(task.work_package_id or task.order_item_id),
            task.external_id,
            self.sums[node_id],
            self._shares.get(node_id),
        )

    def summary_depth(self) -> int:
        """Give the level of the deepest summary of the structure, nought without any (0110)."""
        tree = self.tree
        return max((tree.level[each] for each in tree.tasks if tree.is_summary(each)), default=0)


class RowsReading(Reading[NodeRow, TaskRow]):
    """What a reading that writes nothing derives of a structure read as rows (US-2220).

    ``listNodes`` and ``compareRevisions``: the facets of the other kinds are read as rows too, once
    for their figures and their views (``FacetHooks.columns``).
    """

    read_only = True


class TasksReading(RowsReading):
    """What a reading of the tasks alone derives, none of the nodes they bear read (US-2280).

    ``listNodes`` with ``kinds=task``: the tree holds the tasks alone, numbered from how many nodes
    each bears (``numbered``); what the reading derives of their lines — the sums, whether an own
    line holds a summary open or dated its completion — comes from what the hooks of each kind
    count under each task (``Tally``, ``FacetHooks.tally``; EP-26, "L'agrégat d'abord").
    """

    def __init__(
        self,
        session: Session,
        structure: tuple[Place, datetime, bool],
        read: tuple[Tree[NodeRow, TaskRow], Sequence[LinkColumns], Mapping[UUID, Tally]],
        calendars: dict[UUID, Applicable],
    ) -> None:
        """Derive the states and the sums of the tasks from the tallies of what they bear."""
        tree, links, tallies = read
        self.tallies = tallies
        super().__init__(session, structure, tree, links, calendars)

    def _own_lines(self, node_id: UUID) -> tuple[bool, date | None]:
        """Tell what the own lines of a summary tell its state, from its tallies."""
        return tallied_own_lines(self.tree, self.tallies, node_id)

    def _lines_total(self, node_id: UUID) -> Amounts:
        """Give the sum of the figures of the lines a task bears, as its tallies counted them."""
        tally = self.tallies.get(node_id)
        return Amounts() if tally is None else Amounts() + tally.amounts

    def _tallies(self) -> Mapping[UUID, Tally] | None:
        """Give the tallies the reading read: the physical progress does not read them again."""
        return self.tallies

    def borne(self, task_ids: Collection[UUID]) -> tuple[int, Amounts]:
        """Give how many nodes the tasks named bear, and the sum of their figures."""
        count, total = 0, Amounts()
        for each in task_ids:
            tally = self.tallies.get(each)
            if tally is not None:
                count += tally.count
                total += tally.amounts
        return count, total
