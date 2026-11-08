# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a planning of MS Project brings to a structure, and its report, private to the module.

The analysis of an import and its application (US-1430/L3) build the same plan, the second under
the lock of the structure, so that the application judges again what the analysis accepted
(EP-06, "Le format MS Project"; WF-INTF-0040):

- **The matching.** A task of the file is the task of the structure whose lineage it carries —
  the one the export writes —, else the one whose external identifier is its ``UID``, else a task
  created, which keeps that ``UID`` as its external identifier; a task of the structure is matched
  once, by the first row of the file that names it. A task matched keeps its lineage, its state,
  its attachment and its external identifier; the file gives it its label, its description — its
  notes (#1339) —, its place, its duration and its mode, and its dates in manual mode.
- **The tree.** The tree of the file, in its order; a task of the structure the file no longer
  carries is removed (WF-PLA-0070) — or kept, started or completed, under its parent after the
  tasks of the file, and signalled (``kept``). Its ancestors are started too, hence never removed.
- **A row rejected** (``rejected``, by its row in the file, counted from 1): a label empty or too
  long (``VALUE_REQUIRED``, ``VALUE_TOO_LONG``), a task the file creates is then not created, its
  subtasks rising to its parent; and a task the file makes a milestone — a leaf of nought
  duration — while the import keeps a started subtask under it (``MILESTONE_HAS_NO_SUBTASK``,
  WF-PLA-0050, #1772): the only site the file leaves the refusal, an MS Project file carrying no
  subtask under a leaf. A task matched and rejected stays as it stands, at the place the file
  gives it.
- **The mode.** A summary is automatic: one the file carries in manual mode is signalled
  (``SUMMARY_TASK_DERIVED``, its dates of the file). A leaf is manual when the file says so, or
  when it bears a date constraint, which ``ignored`` names (WF-INTF-0040); its dates are those of
  the file, read on the calendar of the task in the file, their hours bounded by the day of its
  calendar in Waterfall, and a day without hours there is kept at hour nought and signalled
  (``NON_WORKING_DAY``, WF-PLA-0020).
- **The units.** A duration and a lag keep their hours and their unit, their value the hours over
  those of the unit at the constants of the installation (WF-PLA-0160): the constants of the file
  are not imported, the report says their difference by its own words, the durations.
- **The report.** The differences — the start of the structure (``planning_start_on``), each task
  added, updated (``label``, ``description``, ``scheduling_mode``, ``duration``, ``start``,
  ``finish`` for a manual leaf, ``parent``), removed — the work package or order item it bore
  named — or kept, each link added, updated or removed —, the engine replayed on the structure the
  import leaves for ``date_mismatches`` — the start and the finish of each task of the file read
  on its calendar in the file, the duration of a summary — and the refusals of the whole file:
  the task of an order item outside the subtree of that of its work package
  (``ORDER_ITEM_OUTSIDE_WORK_PACKAGE``, the main structure alone), and a planning beyond fifteen
  years (``PROJECT_HORIZON_EXCEEDED``, WF-PLA-0150), whose dates are then not compared.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from waterfall.core.planning.attachments import OUTSIDE, carriers, strays
from waterfall.core.planning.calendars import default_calendar
from waterfall.core.planning.dating import (
    AUTOMATIC,
    LINK_CYCLE,
    LINK_FORBIDDEN,
    MANUAL,
    PROJECT_HORIZON_EXCEEDED,
    constants_of,
    duration_of,
)
from waterfall.core.planning.interface.facets import calendars_of
from waterfall.core.planning.msproject import (
    FileCalendar,
    calendar_of,
    hours_of,
    lag_of,
)
from waterfall.core.planning.msproject import (
    calendars_of as file_calendars_of,
)
from waterfall.core.planning.msproject import (
    duration_of as file_duration_of,
)
from waterfall.core.planning.msproject.model import DATE_CONSTRAINTS
from waterfall.core.planning.scheduling import (
    Duration,
    Lag,
    Link,
    LinkCycleError,
    LinkForbiddenError,
    Schedule,
    Structure,
    WorkInstant,
    decimal_of,
    schedule,
)
from waterfall.core.planning.scheduling import Task as Planned
from waterfall.core.planning.tables import LABEL_LENGTH
from waterfall.core.planning.tree import Tree, read_links, read_tree
from waterfall.core.planning.views import NOT_STARTED, state_of
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.core.revisions.interface import structure_facts
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.exchanges.interface import ImportTarget
    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.msproject.model import MsProject, MsTask, ReadProject
    from waterfall.core.planning.scheduling import (
        Calendar,
        DurationUnit,
        LagUnit,
        LinkType,
        UnitConstants,
    )
    from waterfall.core.planning.tables import Task, TaskLink
    from waterfall.core.projects.interface import WorkBreakdownItem
    from waterfall.core.revisions.interface import StructureFacts

VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_TOO_LONG = "VALUE_TOO_LONG"
MILESTONE_HAS_NO_SUBTASK = "MILESTONE_HAS_NO_SUBTASK"
NON_WORKING_DAY = "NON_WORKING_DAY"
SUMMARY_TASK_DERIVED = "SUMMARY_TASK_DERIVED"
PREDECESSORS = "predecessors"

type Json = dict[str, Any]
type Pair = tuple[UUID, UUID]


@dataclass(frozen=True, slots=True)
class Aimed:
    """The structure an import writes in as it stands: none yet for a project without revision."""

    project_id: UUID
    facts: StructureFacts | None
    tree: Tree
    links: list[TaskLink]

    @property
    def planning_start_on(self) -> date | None:
        """Give the start of the structure, none without one."""
        return None if self.facts is None else self.facts.planning_start_on

    @property
    def is_main(self) -> bool:
        """Tell whether the structure is the main one: the one a revision created holds."""
        return self.facts is None or self.facts.is_main


def aimed_of(session: Session, target: ImportTarget, *, lock: bool) -> Aimed:
    """Read the structure an import aims at, under its lock for the application."""
    project_id, structure_id = target.project_id, target.structure_id
    if structure_id is None:
        return Aimed(project_id, None, Tree({}, {}), [])
    facts = structure_facts(session, project_id, structure_id, lock=lock)
    tree = read_tree(session, project_id, structure_id)
    return Aimed(project_id, facts, tree, read_links(session, project_id, structure_id))


@dataclass(frozen=True, slots=True)
class Facet:
    """The facet the file gives a task: a summary's mode and duration are derived."""

    label: str
    description: str | None
    mode: str
    duration: Duration
    start: WorkInstant | None = None
    finish: WorkInstant | None = None


@dataclass(slots=True)
class Row:
    """A task of the file: its row, the node it writes, the facet it gives — none if rejected."""

    number: int
    task: MsTask
    node_id: UUID
    old: Task | None
    lineage_id: UUID | None
    parent_id: UUID | None = None
    facet: Facet | None = None
    dropped: bool = False
    file_dates: tuple[WorkInstant, WorkInstant] | None = None


@dataclass(slots=True)
class Plan:
    """The structure an import leaves, and what its report says of it.

    ``by_node`` the rows the import writes, by their node; ``children`` and ``order`` the tree it
    leaves, the order of the plan depth first; ``links`` the links of the file by their two tasks.
    """

    aimed: Aimed
    rows: list[Row]
    kept: list[UUID]
    removed: list[UUID]
    start: date | None
    by_node: dict[UUID, Row]
    children: dict[UUID | None, list[UUID]]
    order: list[UUID]
    links: dict[Pair, tuple[LinkType, Lag]]
    calendars: dict[UUID, Calendar]
    rejected: list[Json]
    signals: list[Json]
    refusals: list[Json]
    schedule: Schedule | None = None

    def parent_of(self, node_id: UUID) -> UUID | None:
        """Give the parent a task has in the structure the import leaves."""
        row = self.by_node.get(node_id)
        return row.parent_id if row is not None else self.aimed.tree.nodes[node_id].parent_id

    def is_summary(self, node_id: UUID) -> bool:
        """Tell whether a task bears a subtask in the structure the import leaves."""
        return bool(self.children.get(node_id))

    def label_of(self, node_id: UUID) -> str:
        """Give the label a task has once imported: the file's, or its own if not written."""
        row = self.by_node.get(node_id)
        if row is not None and row.facet is not None:
            return row.facet.label
        return self.aimed.tree.tasks[node_id].label

    def lineage_of(self, node_id: UUID) -> UUID | None:
        """Give the lineage of a task, none for a task the import creates."""
        node = self.aimed.tree.nodes.get(node_id)
        return None if node is None else node.lineage_id


def _matched(project: MsProject, tree: Tree) -> list[Row]:
    """Match each task of the file: by its lineage, then by its ``UID``, else created."""
    by_lineage = {tree.nodes[each].lineage_id: each for each in tree.order if each in tree.tasks}
    by_external: dict[str, UUID] = {}
    for each in tree.order:
        external = tree.tasks[each].external_id if each in tree.tasks else None
        if external is not None:
            by_external.setdefault(external, each)
    taken: set[UUID] = set()
    rows: list[Row] = []
    for number, task in enumerate(project.tasks, start=1):
        found = None if task.lineage is None else by_lineage.get(task.lineage)
        if found is None or found in taken:
            found = by_external.get(str(task.uid))
        if found is not None and found not in taken:
            taken.add(found)
            old = tree.tasks[found]
            rows.append(Row(number, task, found, old, tree.nodes[found].lineage_id))
        else:
            rows.append(Row(number, task, new_id(), None, None))
    return rows


def _rejection(row: Row, code: str, params: Json) -> Json:
    """Give a row rejected, by its row in the file, which has a single sheet."""
    return {"sheet": None, "row": row.number, "code": code, "params": params}


def _judge_labels(plan: Plan) -> None:
    """Reject a row whose label is empty or too long; a task created then is not."""
    for row in plan.rows:
        name = row.task.name
        if not name.strip():
            plan.rejected.append(_rejection(row, VALUE_REQUIRED, {}))
        elif len(name) > LABEL_LENGTH:
            plan.rejected.append(_rejection(row, VALUE_TOO_LONG, {"max_length": LABEL_LENGTH}))
        else:
            continue
        row.dropped = row.old is None


def _place(plan: Plan, project: MsProject) -> None:
    """Give each task its parent and the tree its order: the file's, the tasks kept after."""
    tree = plan.aimed.tree
    by_uid = {row.task.uid: row for row in plan.rows}
    parents = project.parents()
    for row in plan.rows:
        above = parents[row.task.uid]
        while above is not None and by_uid[above].dropped:
            above = parents[above]
        row.parent_id = None if above is None else by_uid[above].node_id
        if not row.dropped:
            plan.by_node[row.node_id] = row
            plan.children.setdefault(row.parent_id, []).append(row.node_id)
    gone = set(plan.removed)
    for node_id in plan.kept:
        parent = tree.nodes[node_id].parent_id
        while parent is not None and parent in gone:
            parent = tree.nodes[parent].parent_id
        plan.children.setdefault(parent, []).append(node_id)
    pending = list(reversed(plan.children.get(None, [])))
    while pending:
        node_id = pending.pop()
        plan.order.append(node_id)
        pending.extend(reversed(plan.children.get(node_id, [])))


def _judge_milestones(plan: Plan, file_children: set[int]) -> None:
    """Reject a task the file makes a milestone while a task kept stays under it (#1772)."""
    kept = set(plan.kept)
    for row in plan.rows:
        if row.old is None or row.dropped or row.task.uid in file_children:
            continue
        below = plan.children.get(row.node_id, [])
        nought = row.task.duration is None or not row.task.duration
        if nought and any(each in kept for each in below) and not _rejected(plan, row):
            named = {"lineage_id": str(row.lineage_id), "label": row.task.name}
            plan.rejected.append(_rejection(row, MILESTONE_HAS_NO_SUBTASK, named))


def _rejected(plan: Plan, row: Row) -> bool:
    """Tell whether a row is rejected already."""
    return any(each["row"] == row.number for each in plan.rejected)


def _signal(row: Row, column: str, code: str, params: Json) -> Json:
    """Give a value of the file kept and signalled, the task by its lineage and its label."""
    lineage = None if row.lineage_id is None else str(row.lineage_id)
    return {
        "lineage_id": lineage,
        "label": row.task.name,
        "column": column,
        "code": code,
        "params": params,
    }


def _kept_day(plan: Plan, row: Row, column: str, at: tuple[WorkInstant, Calendar]) -> WorkInstant:
    """Give a date of a manual task on its calendar; a day without hours kept and signalled.

    Its hours are bounded by those of its day: the calendar of the file may grant more.
    """
    instant, calendar = at
    hours = calendar.hours_on(instant.day)
    if hours > 0:
        return WorkInstant(instant.day, min(instant.hours, hours))
    try:
        following: str | None = calendar.next_working_day(instant.day).isoformat()
    except ValueError:
        following = None
    params = {"date": instant.day.isoformat(), "next_working_day": following}
    plan.signals.append(_signal(row, column, NON_WORKING_DAY, params))
    return WorkInstant(instant.day)


def _description(notes: str | None) -> str | None:
    """Give the description of a task from its notes (C-375, #1339): none for blank notes."""
    if notes is None or not notes.strip():
        return None
    return notes.replace("\r\n", "\n")


def _facets(
    plan: Plan, project: MsProject, constants: UnitConstants, file_children: set[int]
) -> None:
    """Give each row not rejected the facet the file gives it, and its dates of the file."""
    calendars = file_calendars_of(project)
    for row in plan.rows:
        task = row.task
        dated_on = calendar_of(project, calendars, task)
        if dated_on is not None and task.start is not None and task.finish is not None:
            row.file_dates = (dated_on.instant(task.start), dated_on.instant(task.finish))
        if row.dropped or _rejected(plan, row):
            continue
        row.facet = _facet(plan, row, (constants, dated_on), file_children)


def _facet(
    plan: Plan,
    row: Row,
    read: tuple[UnitConstants, FileCalendar | None],
    file_children: set[int],
) -> Facet:
    """Give the facet of a row: a summary automatic, a leaf in its mode and its unit."""
    constants, dated_on = read
    task = row.task
    description = _description(task.notes)
    if plan.is_summary(row.node_id):
        if task.manual and task.uid in file_children and task.start and task.finish:
            dates = {
                "start": task.start.date().isoformat(),
                "finish": task.finish.date().isoformat(),
            }
            plan.signals.append(_signal(row, "scheduling_mode", SUMMARY_TASK_DERIVED, dates))
        duration = Duration(Decimal(0), "d") if row.old is None else duration_of(row.old)
        return Facet(task.name, description, AUTOMATIC, duration)
    duration = file_duration_of(task, constants)
    manual = task.manual or task.constraint in DATE_CONSTRAINTS
    if not manual or row.file_dates is None or dated_on is None:
        return Facet(task.name, description, AUTOMATIC, duration)
    calendar = plan.calendars[row.node_id]
    start, finish = row.file_dates
    start = _kept_day(plan, row, "start", (start, calendar))
    finish = _kept_day(plan, row, "finish", (finish, calendar))
    return Facet(task.name, description, MANUAL, duration, start, finish)


def _links(plan: Plan, constants: UnitConstants) -> None:
    """Give the links of the file between the tasks it writes, by their two tasks."""
    by_uid = {row.task.uid: row for row in plan.rows}
    for row in plan.rows:
        for link in row.task.predecessors:
            predecessor = by_uid[link.predecessor_uid]
            if row.dropped or predecessor.dropped:
                continue
            pair = (predecessor.node_id, row.node_id)
            plan.links[pair] = (link.link_type, lag_of(link, constants))


def _planned(plan: Plan, node_id: UUID) -> Planned:
    """Give a task of the structure the import leaves as the engine reads it."""
    row = plan.by_node.get(node_id)
    calendar = plan.calendars[node_id]
    parent = plan.parent_of(node_id)
    summary = plan.is_summary(node_id)
    if row is not None and row.facet is not None:
        facet = row.facet
        manual = facet.mode == MANUAL and not summary
        return Planned(
            node_id,
            parent,
            MANUAL if manual else AUTOMATIC,
            facet.duration,
            calendar,
            facet.start if manual else None,
            facet.finish if manual else None,
        )
    task = plan.aimed.tree.tasks[node_id]
    manual = task.scheduling_mode == MANUAL and not summary
    return Planned(
        node_id,
        parent,
        MANUAL if manual else AUTOMATIC,
        duration_of(task),
        calendar,
        WorkInstant(task.start_date, task.start_hours) if manual else None,
        WorkInstant(task.finish_date, task.finish_hours) if manual else None,
    )


def _first_start(project: MsProject) -> date | None:
    """Give the first day a task of the file starts on, for a file that says no start."""
    starts = [task.start.date() for task in project.tasks if task.start is not None]
    return min(starts, default=None)


def _replayed(plan: Plan, constants: UnitConstants) -> None:
    """Replay the engine on the structure the import leaves; refuse it beyond the horizon.

    A loop of links, or a link between a summary and its subordinate, which MS Project refuses
    too, fails the analysis by the engine's code, the tasks named by their label.
    """
    if not plan.order or plan.start is None:
        return
    tasks = tuple(_planned(plan, each) for each in plan.order)
    links = tuple(
        Link(pair[0], pair[1], link_type, lag) for pair, (link_type, lag) in plan.links.items()
    )
    try:
        plan.schedule = schedule(Structure(tasks, links, plan.start, constants))
    except LinkCycleError as loop:
        cycle = [{"node_id": None, "label": plan.label_of(each)} for each in loop.cycle]
        raise UnprocessableError(LINK_CYCLE, {"cycle": cycle}) from None
    except LinkForbiddenError:
        raise UnprocessableError(LINK_FORBIDDEN) from None
    beyond = plan.schedule.horizon_exceeded_by
    if beyond is not None:
        node = None if beyond not in plan.aimed.tree.nodes else str(beyond)
        named = {"node_id": node, "label": plan.label_of(beyond)}
        plan.refusals.append({"code": PROJECT_HORIZON_EXCEEDED, "params": {"task": named}})


def _named(plan: Plan, node_id: UUID) -> Json:
    """Name a task of the structure by its node and its label, as a refusal does."""
    return {"node_id": str(node_id), "label": plan.label_of(node_id)}


def _strays(plan: Plan, items: Mapping[UUID, WorkBreakdownItem]) -> None:
    """Refuse a file that takes the task of an order item out of that of its work package.

    The main structure alone bears an attachment (WF-PLA-0170); a task keeps its own.
    """
    if not plan.aimed.is_main:
        return
    tree = plan.aimed.tree
    staying = {each for each in plan.order if each in tree.tasks}
    borne = {item: task for item, task in carriers(tree).items() if task in staying}

    def is_under(task_id: UUID, summary: UUID) -> bool:
        above = plan.parent_of(task_id)
        while above is not None and above != summary:
            above = plan.parent_of(above)
        return above == summary

    rank = {node_id: index for index, node_id in enumerate(plan.order)}
    for package_task, item_tasks in strays(items, borne, is_under):
        ordered = sorted(item_tasks, key=rank.__getitem__)
        params = {
            "work_package_task": _named(plan, package_task),
            "order_item_tasks": [_named(plan, each) for each in ordered],
        }
        plan.refusals.append({"code": OUTSIDE, "params": params})


def plan_import(
    session: Session, target: ImportTarget, read: ReadProject, *, lock: bool
) -> tuple[Plan, Mapping[UUID, WorkBreakdownItem]]:
    """Build what a planning of MS Project brings to the structure an import aims at.

    Reads the structure — under its lock for the application —, its calendars, the constants of
    the installation and the work breakdown of its project; writes nothing.
    """
    project = read.project
    aimed = aimed_of(session, target, lock=lock)
    tree = aimed.tree
    rows = _matched(project, tree)
    written = {row.node_id for row in rows if row.old is not None}
    absent = [each for each in tree.order if each in tree.tasks and each not in written]
    kept = [each for each in absent if state_of(tree, each).progress != NOT_STARTED]
    removed = [each for each in absent if each not in set(kept)]
    start = (
        project.start.date()
        if project.start is not None
        else aimed.planning_start_on or _first_start(project)
    )
    plan = Plan(aimed, rows, kept, removed, start, {}, {}, [], {}, {}, [], [], [])
    file_children = {uid for uid in project.parents().values() if uid is not None}
    _judge_labels(plan)
    _place(plan, project)
    _judge_milestones(plan, file_children)
    constants = constants_of(session)
    default = default_calendar(session)
    held: Mapping[UUID, Applicable] = (
        calendars_of(session, aimed.project_id, list(tree.tasks)) if tree.tasks else {}
    )
    plan.calendars = {each: held.get(each, default).calendar for each in [*plan.order, *removed]}
    _facets(plan, project, constants, file_children)
    _links(plan, constants)
    items = work_breakdown_items(session, aimed.project_id)
    _strays(plan, items)
    _replayed(plan, constants)
    return plan, items


def _lag_unit(unit: str) -> LagUnit:
    """Give the unit of a lag read from its row."""
    return cast("LagUnit", unit)


def _duration_unit(unit: str) -> DurationUnit:
    """Give the unit of a duration read from its row."""
    return cast("DurationUnit", unit)


def task_fields(plan: Plan, row: Row) -> list[str]:
    """Name the columns the file changes of a task matched, in the order of the grid."""
    old, facet = row.old, row.facet
    if old is None or facet is None:
        return []
    fields: list[str] = []
    if old.label != facet.label:
        fields.append("label")
    if (old.description or None) != facet.description:
        fields.append("description")
    if not plan.is_summary(row.node_id):
        if old.scheduling_mode != facet.mode:
            fields.append("scheduling_mode")
        duration = Duration(old.duration_value, _duration_unit(old.duration_unit))
        if duration != facet.duration:
            fields.append("duration")
        if facet.mode == MANUAL:
            if WorkInstant(old.start_date, old.start_hours) != facet.start:
                fields.append("start")
            if WorkInstant(old.finish_date, old.finish_hours) != facet.finish:
                fields.append("finish")
    if plan.aimed.tree.nodes[row.node_id].parent_id != row.parent_id:
        fields.append("parent")
    return fields


def _difference(
    change: str, target: str, named: tuple[UUID | None, str | None], fields: list[str]
) -> Json:
    """Give a difference of the import with the structure."""
    lineage, label = named
    return {
        "change": change,
        "target": target,
        "lineage_id": None if lineage is None else str(lineage),
        "label": label,
        "predecessor_label": None,
        "fields": fields,
    }


def _task_differences(plan: Plan) -> Iterator[Json]:
    """Give the tasks of the file added or updated, in the order of the file."""
    for row in plan.rows:
        if row.dropped or row.facet is None:
            continue
        if row.old is None:
            yield _difference("added", "task", (None, row.facet.label), [])
            continue
        fields = task_fields(plan, row)
        if fields:
            yield _difference("updated", "task", (row.lineage_id, row.facet.label), fields)


def _link_differences(plan: Plan) -> Iterator[Json]:
    """Give the links added, updated or removed, each carried by its successor (WF-PLA-0080)."""
    held = {(link.predecessor_id, link.successor_id): link for link in plan.aimed.links}
    tree = plan.aimed.tree

    def named(change: str, pair: Pair, fields: list[str]) -> Json:
        predecessor, successor = pair
        found = _difference(
            change, "link", (plan.lineage_of(successor), plan.label_of(successor)), fields
        )
        found["predecessor_label"] = plan.label_of(predecessor)
        return found

    for pair, (link_type, lag) in plan.links.items():
        link = held.get(pair)
        if link is None:
            yield named("added", pair, [])
        elif (link.link_type, Lag(link.lag_value, _lag_unit(link.lag_unit))) != (link_type, lag):
            yield named("updated", pair, [PREDECESSORS])
    for pair in held:
        if pair not in plan.links:
            predecessor, successor = pair
            found = _difference(
                "removed",
                "link",
                (tree.nodes[successor].lineage_id, tree.tasks[successor].label),
                [],
            )
            found["predecessor_label"] = tree.tasks[predecessor].label
            yield found


def _absent_differences(plan: Plan, items: Mapping[UUID, WorkBreakdownItem]) -> Iterator[Json]:
    """Give the tasks the file no longer carries: removed, the element they bore named, or kept."""
    tree = plan.aimed.tree
    kept, removed = set(plan.kept), set(plan.removed)
    for node_id in tree.order:
        if node_id not in kept and node_id not in removed:
            continue
        task = tree.tasks[node_id]
        named = (tree.nodes[node_id].lineage_id, task.label)
        if node_id in kept:
            yield _difference("kept", "task", named, [])
            continue
        found = _difference("removed", "task", named, [])
        item_id = task.work_package_id or task.order_item_id
        item = None if item_id is None else items.get(item_id)
        if item is not None:
            found["work_breakdown_label"] = item.label
        yield found


def _mismatches(plan: Plan) -> list[Json]:
    """Name the tasks whose duration or dates in the file differ from the engine's (0040).

    The dates of the file are read on the calendar of the task in the file; the duration is a
    summary's, its work between its dates, a leaf keeping the hours of the file.
    """
    computed = plan.schedule
    if computed is None or plan.refusals:
        return []
    found: list[Json] = []
    for row in plan.rows:
        if row.dropped or row.file_dates is None or row.node_id not in computed.tasks:
            continue
        placed = computed.tasks[row.node_id]
        fields: list[str] = []
        span = row.task.duration
        hours = None if span is None else decimal_of(hours_of(span))
        if plan.is_summary(row.node_id) and hours not in {None, placed.work_hours}:
            fields.append("duration")
        start, finish = row.file_dates
        if start != placed.start:
            fields.append("start")
        if finish != placed.finish:
            fields.append("finish")
        if fields:
            lineage = None if row.lineage_id is None else str(row.lineage_id)
            found.append(
                {"lineage_id": lineage, "label": plan.label_of(row.node_id), "fields": fields}
            )
    return found


def _label(aimed: Aimed) -> str | None:
    """Give the label of the structure an import aims at."""
    return None if aimed.facts is None else aimed.facts.label


def report_of(plan: Plan, read: ReadProject, items: Mapping[UUID, WorkBreakdownItem]) -> Json:
    """Give the report of an import (``ImportReport``), in codes and parameters."""
    aimed = plan.aimed
    differences: list[Json] = []
    if aimed.planning_start_on is not None and plan.start not in {None, aimed.planning_start_on}:
        differences.append(
            _difference("updated", "cost_structure", (None, _label(aimed)), ["planning_start_on"])
        )
    tasks = list(_task_differences(plan))
    differences += [*tasks, *_link_differences(plan), *_absent_differences(plan, items)]
    read_count = len(read.project.tasks)
    ignored = [
        {"kind": each.kind, "count": each.count, "labels": list(each.labels)}
        for each in read.ignored
    ]
    return {
        "format_version": None,
        "read_count": read_count,
        "unchanged_count": read_count - len(plan.rejected) - len(tasks),
        "rejected": sorted(plan.rejected, key=lambda each: each["row"]),
        "refusals": plan.refusals,
        "differences": differences,
        "ignored": ignored,
        "completed_tasks": [],
        "date_mismatches": _mismatches(plan),
        "signals": plan.signals,
        "requires_confirmation_reasons": [],
    }
