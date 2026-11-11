# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The nodes of a structure as the planning gives them to read, private to the module.

What ``listNodes`` and every write of the tree give back (``Node``, ``NodesWritten``): each node
with what is computed on the whole structure — its number, its level, its place —, its facet task
with what the planning derives at the reading — the state of a summary from its subordinates
(WF-PLA-0040), the finish overdue of a started task (WF-RAE-0040), its calendar (WF-PLA-0010), its
links in conflict (WF-PLA-0020) —, its predecessors named by their number (WF-PLA-0080), and the
fields it computes and accepts (``computed_fields``, ``editable_fields``, WF-IHM-0030, WF-IHM-0040).
The amounts, the lines and the physical progress are EP-07's: nought, none, and not computable.
The interface re-exports the views; the API writes them as the contract does.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.planning.scheduling import WorkInstant
from waterfall.core.planning.tree import TASK, tracking_of
from waterfall.core.projects.interface import work_breakdown_items

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.tables import TaskLink
    from waterfall.core.planning.tree import Tree

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

    ``calendar_hours`` are the hours of the applicable calendar, Monday first; ``total_float`` is
    in days, none for a task in manual mode and for a summary none of whose subordinates has one.
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


@dataclass(frozen=True, slots=True)
class NodeView:
    """A node of a structure as it is read (``Node``): a task here, its facet with it."""

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
    predecessors: tuple[PredecessorView, ...]
    computed_fields: tuple[str, ...]
    editable_fields: tuple[str, ...]


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


def _derived(states: list[State]) -> State:
    """Give the state of a summary: started as soon as one is, completed when all are (0040).

    Its start date is the first of its subordinates', its completion date the last of theirs.
    """
    started = [state.started_on for state in states if state.started_on is not None]
    first = min(started, default=None)
    if all(state.progress == COMPLETED for state in states):
        completed = [state.completed_on for state in states if state.completed_on is not None]
        return State(COMPLETED, first, max(completed, default=None))
    if any(state.progress != NOT_STARTED for state in states):
        return State(STARTED, first, None)
    return State(NOT_STARTED, None, None)


def state_of(tree: Tree, node_id: UUID) -> State:
    """Give the state of a task of a tree: its own for a leaf, its subordinates' for a summary."""
    below = tree.subtasks(node_id)
    if below:
        return _derived([state_of(tree, child) for child in below])
    task = tree.tasks[node_id]
    return State(task.progress, task.started_on, task.completed_on)


class Reading:
    """What a reading derives of a structure, once for all its nodes."""

    def __init__(
        self,
        session: Session,
        structure: tuple[UUID, datetime, bool],
        tree: Tree,
        links: list[TaskLink],
        calendars: dict[UUID, Applicable],
    ) -> None:
        """Read the inscriptions of the tasks and the labels of what they bear; derive the states.

        ``structure`` is the project of the structure, the instant of its dates, and whether it is
        the main one.
        """
        project_id, scheduled_at, self.is_main = structure
        self.tree = tree
        self.calendars = calendars
        self.scheduled_on = scheduled_at.date()
        self.links = links
        # The links by their successor, and by each end, built once: a node asks for its own.
        self._incoming: dict[UUID, list[TaskLink]] = {}
        self._ends: dict[UUID, list[TaskLink]] = {}
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
        self.states: dict[UUID, State] = {}
        for node_id in reversed(tree.order):
            if node_id not in tree.tasks:
                continue
            below = tree.subtasks(node_id)
            if below:
                self.states[node_id] = _derived([self.states[child] for child in below])
            else:
                task = tree.tasks[node_id]
                self.states[node_id] = State(task.progress, task.started_on, task.completed_on)

    def conflicts(self, node_id: UUID) -> tuple[ConflictView, ...]:
        """Give the links in conflict a task is an end of, in the order of the plan (0020)."""
        if self.tree.is_summary(node_id):
            return ()
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

    def _fields(self, node_id: UUID) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """Give what the server computes of a task, and what it accepts (WF-IHM-0030, 0040)."""
        tree = self.tree
        attached = ATTACHMENT_AND_TRACKING if self.is_main else ()
        if tree.is_summary(node_id):
            computed = (*SUMMARY_COMPUTED, PROGRESS)
            editable = ("task.label", "task.description", "task.predecessors", *attached)
            return computed, editable
        manual = tree.tasks[node_id].scheduling_mode == MANUAL
        duration = () if tree.is_milestone(node_id) else ("task.duration",)
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
        )

    def _borne(self, item_id: UUID | None) -> str | None:
        item = None if item_id is None else self.items.get(item_id)
        return None if item is None else item.label

    def node(self, node_id: UUID) -> NodeView:
        """Give a node as it is read, whole."""
        tree = self.tree
        node = tree.nodes[node_id]
        row = tree.row_number
        incoming = sorted(
            self._incoming.get(node_id, []),
            key=lambda link: row[link.predecessor_id],
        )
        computed, editable = self._fields(node_id) if node.kind == TASK else ((), ())
        return NodeView(
            node_id=node_id,
            lineage_id=node.lineage_id,
            kind=node.kind,
            parent_id=node.parent_id,
            position=tree.position[node_id],
            row_number=row[node_id],
            level=tree.level[node_id],
            origin_risk_id=node.origin_risk_id,
            lock_version=node.lock_version,
            task=self._task(node_id) if node.kind == TASK else None,
            predecessors=tuple(
                PredecessorView(
                    link.predecessor_id,
                    row[link.predecessor_id],
                    link.link_type,
                    link.lag_value,
                    link.lag_unit,
                )
                for link in incoming
            ),
            computed_fields=computed,
            editable_fields=editable,
        )

    def summary_depth(self) -> int:
        """Give the level of the deepest summary of the structure, nought without any (0110)."""
        tree = self.tree
        return max((tree.level[each] for each in tree.tasks if tree.is_summary(each)), default=0)
