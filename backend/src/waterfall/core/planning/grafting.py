# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks of a structure grafted into another, private to the module (US-2620/L1).

What the occurrence of a risk does to the main structure (WF-RIS-0060; EP-08, "La fusion et la
survenance"): the tasks of its own estimate, with the nodes they bear, copied under a task of the
main structure — the task that bears its provision line —, and its report. One computation serves
both (``plan_graft``): the report reads it and writes nothing, the application writes what it
found, under the lock of the two structures, so that what the report presented is what is written.

- **The place.** The tasks of the first level of the structure grafted come, in their order, last
  under the task named; when it is a milestone, immediately after it, under its parent or at the
  first level, the siblings after it moved down: a milestone bears no subtask (WF-PLA-0050).
- **The copies.** Each node of the structure grafted is copied under a node of its own, its lineage
  its own — a node created, which no revision held (WF-DAT-0030) —, at its rank under the copy of
  its parent, marked with the risk it comes from (``origin_risk_id``); its facet task keeps its
  label, its description, its duration and its mode, without attachment to the work breakdown,
  which the main structure alone carries (WF-PLA-0170), nor identifier of MS Project, which would
  match another task of the main structure at an import. The links between its tasks come with
  them. A leaf without predecessor in the structure grafted is in manual mode at the dates it had
  there, so that the planning start of the structure grafted into does not move it. The facets of
  the other kinds are the hooks' (``FacetHooks.graft``): the estimate's at a budgeted amount of
  nought (WF-RIS-0060).
- **The nodes removed.** Lines of the structure grafted into that go with the graft — the
  provision line of the risk —, which move no date: their facet names no role.
- **The report.** The differences in the form of the contract (``ImportDifference``): each node
  copied, added, in the order of the plan of the structure grafted; the task named, updated by the
  fields that change of it — the summary of the tasks grafted, its dates and its duration now
  spanning theirs (WF-PLA-0040), its mode automatic —, a milestone being left as it is; each task
  of the structure grafted into whose dates the engine moves, updated by its dates, after it, in
  the order of the plan (#4134); each node removed. The reasons that refuse the whole graft
  (``ReportRefusal``): those the facets give (``FacetHooks.judge_graft``), then a planning beyond
  fifteen years
  (``PROJECT_HORIZON_EXCEEDED``, WF-PLA-0150), the engine replayed on the structure the graft
  leaves.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import insert, update

from waterfall.core.planning.dating import (
    AUTOMATIC,
    DAYS,
    LINK_CYCLE,
    LINK_FORBIDDEN,
    MANUAL,
    PROJECT_HORIZON_EXCEEDED,
    conflicts_of,
    constants_of,
    duration_of,
    in_days,
)
from waterfall.core.planning.interface.facets import (
    BearingTask,
    FacetGraft,
    calendars_of,
    facets,
)
from waterfall.core.planning.rescheduling import Holding, replayed
from waterfall.core.planning.scheduling import (
    Duration,
    Lag,
    Link,
    LinkCycleError,
    LinkForbiddenError,
    Schedule,
    Structure,
    TaskWithoutWorkingHoursError,
    WorkInstant,
    schedule,
)
from waterfall.core.planning.scheduling import Task as Planned
from waterfall.core.planning.shaping import closed_above, deleted, reopened, stamp
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.planning.tree import TASK, read_links, read_tree
from waterfall.core.planning.views import NOT_STARTED, state_of
from waterfall.core.revisions.interface import structure_facts
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import LagUnit, LinkType, UnitConstants
    from waterfall.core.planning.tree import Tree
    from waterfall.core.revisions.interface import StructureFacts
    from waterfall.platform.audit import Act

type Json = dict[str, Any]
# The fields of the task named a graft changes, in the order of ``NodeColumn``.
FIELDS = ("scheduling_mode", "duration", "start", "finish")
# The dates of another task of the structure grafted into, which the graft moves, in the same order.
DATE_FIELDS = ("start", "finish")


@dataclass(frozen=True, slots=True)
class GraftAsked:
    """A graft as the planning computes it: the structures, the task, what goes with it.

    ``source_id`` the structure grafted, ``target_id`` the one grafted into, ``bearer_id`` the task
    of the latter its tasks go under — or after, for a milestone —, ``removed`` the lines of the
    latter that go with the graft, ``origin_risk_id`` the risk each node copied comes from.
    """

    project_id: UUID
    source_id: UUID
    target_id: UUID
    bearer_id: UUID
    removed: tuple[UUID, ...]
    origin_risk_id: UUID | None


@dataclass(frozen=True, slots=True)
class Read:
    """The two structures of a graft as read: the one grafted into, its tree and its links."""

    facts: StructureFacts
    source: Tree
    target: Tree
    source_links: list[TaskLink]
    target_links: list[TaskLink]
    constants: UnitConstants


@dataclass(slots=True)
class GraftPlan:
    """What a graft writes, and what its report says of it.

    ``copies`` the node of the structure grafted into each node grafted is copied under, in the
    order of the plan of the structure grafted; ``parent`` and ``first_rank`` where its tasks of the
    first level go; ``shifted`` the siblings after a milestone, moved down by their number;
    ``manual`` the leaves without predecessor, in manual mode at their dates.
    """

    asked: GraftAsked
    read: Read
    copies: dict[UUID, UUID]
    parent: UUID | None
    first_rank: int
    shifted: tuple[UUID, ...]
    manual: frozenset[UUID]
    differences: list[Json] = field(default_factory=list[Json])
    refusals: list[Json] = field(default_factory=list[Json])

    @property
    def source(self) -> Tree:
        """Give the tree of the structure grafted."""
        return self.read.source

    @property
    def target(self) -> Tree:
        """Give the tree of the structure grafted into."""
        return self.read.target

    @property
    def onto_milestone(self) -> bool:
        """Tell whether the task named is a milestone, which the tasks follow instead."""
        return self.parent != self.asked.bearer_id

    @property
    def roots(self) -> list[UUID]:
        """Give the tasks of the first level of the structure grafted, in their order."""
        return self.source.subtasks(None)

    def grafted_parent(self, node_id: UUID) -> UUID | None:
        """Give the parent a node of the structure grafted has once copied."""
        parent = self.source.nodes[node_id].parent_id
        return self.parent if parent is None else self.copies[parent]

    def grafted_rank(self, node_id: UUID) -> int:
        """Give the rank a node of the structure grafted has once copied."""
        roots = self.roots
        if node_id in roots:
            return self.first_rank + roots.index(node_id)
        return self.source.nodes[node_id].rank


def _read(session: Session, asked: GraftAsked, *, lock: bool) -> Read:
    """Read the two structures, under their lock for the application: the one grafted into first."""
    project_id = asked.project_id
    facts = structure_facts(session, project_id, asked.target_id, lock=lock)
    structure_facts(session, project_id, asked.source_id, lock=lock)
    return Read(
        facts,
        read_tree(session, project_id, asked.source_id),
        read_tree(session, project_id, asked.target_id),
        read_links(session, project_id, asked.source_id),
        read_links(session, project_id, asked.target_id),
        constants_of(session),
    )


def _placed(read: Read, asked: GraftAsked) -> tuple[UUID | None, int, tuple[UUID, ...]]:
    """Give the parent and the first rank of the tasks grafted, and the siblings they move down.

    Last under the task; immediately after a milestone, under its parent (WF-RIS-0060).
    """
    target, bearer_id = read.target, asked.bearer_id
    if bearer_id not in target.tasks:
        msg = "a graft goes under a task of the structure grafted into"
        raise ValueError(msg)
    if not target.is_milestone(bearer_id):
        last = max((target.nodes[each].rank for each in target.subtasks(bearer_id)), default=0)
        return bearer_id, last + 1, ()
    node = target.nodes[bearer_id]
    after = tuple(
        each for each in target.subtasks(node.parent_id) if target.nodes[each].rank > node.rank
    )
    return node.parent_id, node.rank + 1, after


def _manual(read: Read) -> frozenset[UUID]:
    """Give the leaves of the structure grafted that no link of it follows (WF-RIS-0060)."""
    source = read.source
    followed = {link.successor_id for link in read.source_links}
    return frozenset(
        each for each in source.tasks if not source.is_summary(each) and each not in followed
    )


def _planned_target(
    plan: GraftPlan, node_id: UUID, calendars: Mapping[UUID, Applicable]
) -> Planned:
    """Give a task of the structure grafted into as the engine reads it once the graft is made."""
    target = plan.target
    task = target.tasks[node_id]
    becomes = node_id == plan.asked.bearer_id and not plan.onto_milestone and bool(plan.roots)
    manual = task.scheduling_mode == MANUAL and not (target.is_summary(node_id) or becomes)
    return Planned(
        node_id,
        target.nodes[node_id].parent_id,
        MANUAL if manual else AUTOMATIC,
        duration_of(task),
        calendars[node_id].calendar,
        WorkInstant(task.start_date, task.start_hours) if manual else None,
        WorkInstant(task.finish_date, task.finish_hours) if manual else None,
    )


def _is_manual(plan: GraftPlan, node_id: UUID) -> bool:
    """Tell whether a task grafted is in manual mode once copied: a leaf manual or unfollowed."""
    if plan.source.is_summary(node_id):
        return False
    return node_id in plan.manual or plan.source.tasks[node_id].scheduling_mode == MANUAL


def _planned_source(
    plan: GraftPlan, node_id: UUID, calendars: Mapping[UUID, Applicable]
) -> Planned:
    """Give a task grafted as the engine reads it: its copy, in manual mode at its dates or not."""
    task = plan.source.tasks[node_id]
    manual = _is_manual(plan, node_id)
    return Planned(
        plan.copies[node_id],
        plan.grafted_parent(node_id),
        MANUAL if manual else AUTOMATIC,
        duration_of(task),
        calendars[node_id].calendar,
        WorkInstant(task.start_date, task.start_hours) if manual else None,
        WorkInstant(task.finish_date, task.finish_hours) if manual else None,
    )


def _ordered(plan: GraftPlan) -> Iterator[tuple[bool, UUID]]:
    """Give the tasks of the structure the graft leaves in the order of its plan, each by its tree.

    The tasks grafted follow the last task of the subtree of the task named — the task itself for a
    milestone, a leaf —; ``True`` names a task of the structure grafted.
    """
    target, source = plan.target, plan.source
    anchor = [each for each in target.subtree(plan.asked.bearer_id) if each in target.tasks][-1]
    for node_id in target.order:
        if node_id not in target.tasks:
            continue
        yield False, node_id
        if node_id == anchor:
            yield from ((True, each) for each in source.order if each in source.tasks)


def _links(plan: GraftPlan) -> tuple[Link, ...]:
    """Give the links of the structure the graft leaves: its own, and those grafted."""
    copies = plan.copies
    ends = [(link, link.predecessor_id, link.successor_id) for link in plan.read.target_links]
    ends += [
        (link, copies[link.predecessor_id], copies[link.successor_id])
        for link in plan.read.source_links
    ]
    return tuple(
        Link(
            predecessor,
            successor,
            cast("LinkType", link.link_type),
            Lag(link.lag_value, cast("LagUnit", link.lag_unit)),
        )
        for link, predecessor, successor in ends
    )


def _replayed(session: Session, plan: GraftPlan) -> Schedule:
    """Replay the engine on the structure the graft would leave, nothing written.

    A loop of links or a link across the hierarchy, which the links grafted, internal to the
    structure grafted, cannot close, is refused as any write refuses it. A task left without an
    hour of work, which the facets refused already (``judge_graft``), leaves the dates without a
    calculation, as a refused import does not compare them.
    """
    project_id = plan.asked.project_id
    target_calendars = calendars_of(session, project_id, plan.target.tasks)
    source_calendars = calendars_of(session, project_id, plan.source.tasks)
    tasks = tuple(
        _planned_source(plan, node_id, source_calendars)
        if grafted
        else _planned_target(plan, node_id, target_calendars)
        for grafted, node_id in _ordered(plan)
    )
    read = plan.read
    structure = Structure(tasks, _links(plan), read.facts.planning_start_on, read.constants)
    try:
        return schedule(structure)
    except TaskWithoutWorkingHoursError:
        if not plan.refusals:
            raise
        return Schedule({}, ())
    except LinkCycleError:
        raise UnprocessableError(LINK_CYCLE) from None
    except LinkForbiddenError:
        raise UnprocessableError(LINK_FORBIDDEN) from None


def _labels(
    session: Session, project_id: UUID, tree: Tree, node_ids: list[UUID]
) -> dict[UUID, str]:
    """Give the label of each node named: its task's, or its facet's, read by its kind's hooks."""
    labels = {each: tree.tasks[each].label for each in node_ids if each in tree.tasks}
    for kind, hooks in facets().items():
        held = [each for each in node_ids if tree.nodes[each].kind == kind]
        if held:
            states = hooks.snapshot(session, project_id, held)
            labels.update({node: state.label for node, state in states.items()})
    return labels


def _difference(change: str, kind: str, named: tuple[UUID | None, str], fields: list[str]) -> Json:
    """Give a difference of the graft with the structure grafted into (``ImportDifference``)."""
    lineage, label = named
    return {
        "change": change,
        "target": kind,
        "lineage_id": None if lineage is None else str(lineage),
        "label": label,
        "predecessor_label": None,
        "fields": fields,
    }


def _bearer_fields(plan: GraftPlan, computed: Schedule) -> list[str]:
    """Name what changes of the task named, become the summary of the tasks grafted.

    Its mode, a summary being automatic, then its duration — the work between its dates, in days —
    and its dates, as the engine computes them; none for a milestone, left as it is, nor the dates
    of a planning refused beyond the horizon, which the engine does not give.
    """
    bearer = plan.asked.bearer_id
    if plan.onto_milestone or not plan.roots:
        return []
    task = plan.target.tasks[bearer]
    changed = {"scheduling_mode": task.scheduling_mode != AUTOMATIC}
    placed = computed.tasks.get(bearer)
    if placed is not None:
        summary = Duration(in_days(placed.work_hours, plan.read.constants), DAYS)
        changed["duration"] = duration_of(task) != summary
        changed["start"] = WorkInstant(task.start_date, task.start_hours) != placed.start
        changed["finish"] = WorkInstant(task.finish_date, task.finish_hours) != placed.finish
    return [each for each in FIELDS if changed.get(each)]


def _redated(plan: GraftPlan, computed: Schedule) -> list[Json]:
    """Name the tasks of the structure grafted into, but the one named, that the graft redates.

    Each task whose dates the engine, replayed on the structure the graft leaves, gives otherwise
    than it carries, in the order of the plan, as an ``updated`` difference whose fields name its
    dates by the columns of the grid (``start``, ``finish``; #4134). The dates of a planning refused
    beyond the horizon are not given: none then.
    """
    target, bearer = plan.target, plan.asked.bearer_id
    named: list[Json] = []
    for node_id in target.order:
        placed = computed.tasks.get(node_id)
        if node_id not in target.tasks or node_id == bearer or placed is None:
            continue
        task = target.tasks[node_id]
        changed = {
            "start": WorkInstant(task.start_date, task.start_hours) != placed.start,
            "finish": WorkInstant(task.finish_date, task.finish_hours) != placed.finish,
        }
        fields = [each for each in DATE_FIELDS if changed[each]]
        if fields:
            named.append(
                _difference("updated", TASK, (target.nodes[node_id].lineage_id, task.label), fields)
            )
    return named


def _bearers(session: Session, plan: GraftPlan) -> dict[UUID, BearingTask]:
    """Give the task that bears each line of the structure grafted, as it stands there."""
    source = plan.source
    project_id = plan.asked.project_id
    calendars = calendars_of(session, project_id, source.tasks)
    found: dict[UUID, BearingTask] = {}
    for node_id in source.order:
        parent = source.nodes[node_id].parent_id
        if node_id in source.tasks or parent is None:
            continue
        task = source.tasks[parent]
        found[node_id] = BearingTask(
            parent,
            source.nodes[parent].revision_id,
            task.label,
            WorkInstant(task.start_date, task.start_hours),
            WorkInstant(task.finish_date, task.finish_hours),
            calendars[parent].calendar.week,
            state_of(source, parent).progress,
            is_main=False,
        )
    return found


def _judged(session: Session, plan: GraftPlan) -> list[Json]:
    """Give the reasons the facets of the other kinds give against the nodes grafted."""
    bearers = _bearers(session, plan)
    refusals: list[Json] = []
    for kind, hooks in facets().items():
        held = {
            node: bearer for node, bearer in bearers.items() if plan.source.nodes[node].kind == kind
        }
        if held:
            refusals.extend(
                dict(each) for each in hooks.judge_graft(session, plan.asked.project_id, held)
            )
    return refusals


def _report(session: Session, plan: GraftPlan) -> None:
    """Write the differences and the refusals of a graft on its plan (``ImportDifference``).

    The facets judged first, then the engine replayed on the structure the graft leaves.
    """
    asked, source, target = plan.asked, plan.source, plan.target
    plan.refusals = _judged(session, plan)
    computed = _replayed(session, plan)
    labels = _labels(session, asked.project_id, source, source.order)
    plan.differences = [
        _difference("added", source.nodes[each].kind, (None, labels[each]), [])
        for each in source.order
    ]
    fields = _bearer_fields(plan, computed)
    if fields:
        named = (target.nodes[asked.bearer_id].lineage_id, target.tasks[asked.bearer_id].label)
        plan.differences.append(_difference("updated", TASK, named, fields))
    plan.differences.extend(_redated(plan, computed))
    removed = _labels(session, asked.project_id, target, list(asked.removed))
    plan.differences.extend(
        _difference(
            "removed", target.nodes[each].kind, (target.nodes[each].lineage_id, removed[each]), []
        )
        for each in asked.removed
    )
    beyond = computed.horizon_exceeded_by
    if beyond is not None:
        sources = {copy: node for node, copy in plan.copies.items()}
        node = sources.get(beyond)
        # A task grafted is named by its node of the own estimate, as ``TASK_WITHOUT_WORKING_HOURS``
        # names it (``ProblemTask`` forbids a null node; #4151).
        named_node = beyond if node is None else node
        named = {
            "node_id": str(named_node),
            "label": (source.tasks[node] if node is not None else target.tasks[beyond]).label,
        }
        plan.refusals.append({"code": PROJECT_HORIZON_EXCEEDED, "params": {"task": named}})


def plan_graft(session: Session, asked: GraftAsked, *, lock: bool) -> GraftPlan:
    """Compute a graft and its report, nothing written; under the locks for the application."""
    read = _read(session, asked, lock=lock)
    target = read.target
    for each in asked.removed:
        if each not in target.nodes or each in target.tasks:
            msg = "a graft removes lines of the structure grafted into"
            raise ValueError(msg)
    parent, first_rank, shifted = _placed(read, asked)
    plan = GraftPlan(
        asked,
        read,
        {each: new_id() for each in read.source.order},
        parent,
        first_rank,
        shifted if read.source.subtasks(None) else (),
        _manual(read),
    )
    _report(session, plan)
    return plan


def _node(plan: GraftPlan, node_id: UUID, act: Act) -> Json:
    """Give the node a node grafted is copied under: created, its lineage its own, its risk."""
    copy = plan.copies[node_id]
    facts = plan.read.facts
    return {
        "project_id": plan.asked.project_id,
        "id": copy,
        "revision_id": facts.revision_id,
        "structure_id": facts.structure_id,
        "lineage_id": copy,
        "kind": plan.source.nodes[node_id].kind,
        "parent_id": plan.grafted_parent(node_id),
        "rank": plan.grafted_rank(node_id),
        "origin_risk_id": plan.asked.origin_risk_id,
        "lock_version": 1,
        "created_at": act.at,
        "created_by": act.author,
        "updated_at": act.at,
        "updated_by": act.author,
    }


def _task(plan: GraftPlan, node_id: UUID) -> Json:
    """Give the facet of a task grafted: its own, unattached, manual without predecessor.

    Its dates are those it had, which the engine keeps in manual mode and computes otherwise. Its
    progress is not started: the tasks grafted are created in the structure grafted into.
    """
    task = plan.source.tasks[node_id]
    return {
        "project_id": plan.asked.project_id,
        "node_id": plan.copies[node_id],
        "structure_id": plan.asked.target_id,
        "kind": TASK,
        "label": task.label,
        "description": task.description,
        "scheduling_mode": MANUAL if _is_manual(plan, node_id) else AUTOMATIC,
        "duration_value": task.duration_value,
        "duration_unit": task.duration_unit,
        "start_date": task.start_date,
        "start_hours": task.start_hours,
        "finish_date": task.finish_date,
        "finish_hours": task.finish_hours,
        "progress": NOT_STARTED,
        "started_on": None,
        "completed_on": None,
        "external_id": None,
        "order_item_id": None,
        "work_package_id": None,
        "total_float_days": None,
        "is_critical": False,
    }


def _link(plan: GraftPlan, link: TaskLink) -> Json:
    """Give a link grafted, between the copies of its two tasks, under an identifier of its own."""
    facts = plan.read.facts
    return {
        "project_id": plan.asked.project_id,
        "id": new_id(),
        "revision_id": facts.revision_id,
        "structure_id": facts.structure_id,
        "predecessor_id": plan.copies[link.predecessor_id],
        "successor_id": plan.copies[link.successor_id],
        "link_type": link.link_type,
        "lag_value": link.lag_value,
        "lag_unit": link.lag_unit,
        "in_conflict": False,
    }


def _reshaped(session: Session, plan: GraftPlan, act: Act) -> None:
    """Make room for the tasks grafted: the nodes removed, the siblings moved, the task named.

    The lines removed go first; the siblings after a milestone move down by the number of tasks
    grafted in one statement, which advances their counter; the task named, a leaf become summary,
    is automatic (WF-PLA-0040); the tasks above the tasks grafted whose facet keeps a completion are
    put back to started, the tasks grafted not being completed (``closed_above``, #2769).
    """
    asked, target = plan.asked, plan.target
    if asked.removed:
        deleted(session, asked.project_id, target, list(asked.removed))
    if plan.shifted:
        session.execute(
            update(Node)
            .where(Node.project_id == asked.project_id, Node.id.in_(plan.shifted))
            .values(
                rank=Node.rank + len(plan.roots),
                lock_version=Node.lock_version + 1,
                updated_at=act.at,
                updated_by=act.author,
            )
            .execution_options(synchronize_session=False)
        )
    bearer = asked.bearer_id
    if plan.roots and not plan.onto_milestone and not target.is_summary(bearer):
        target.tasks[bearer].scheduling_mode = AUTOMATIC
        stamp(target.nodes[bearer], act)
    if plan.roots:
        reopened(target, closed_above(target, plan.parent), act)
    session.flush()


def write_graft(session: Session, plan: GraftPlan, act: Act) -> None:
    """Write a graft computed under the locks of its structures, and redate the structure.

    Refused by the first reason of its report, nothing written (422). The nodes go in the order of
    the plan, each after its parent, then their facets task, the links grafted and the facets of
    the other kinds; the engine is replayed on the structure, which prices again the lines of the
    tasks grafted on their dates there, moves the instant of its dates on and advances its counter.
    """
    if plan.refusals:
        first = plan.refusals[0]
        raise UnprocessableError(first["code"], first["params"])
    asked, source = plan.asked, plan.source
    conflicts = conflicts_of(plan.read.target_links)
    _reshaped(session, plan, act)
    if source.order:
        session.execute(insert(Node), [_node(plan, each, act) for each in source.order])
    tasks = [_task(plan, each) for each in source.order if each in source.tasks]
    if tasks:
        session.execute(insert(Task), tasks)
    if plan.read.source_links:
        session.execute(insert(TaskLink), [_link(plan, each) for each in plan.read.source_links])
    for kind, hooks in facets().items():
        held = {node: copy for node, copy in plan.copies.items() if source.nodes[node].kind == kind}
        if held:
            hooks.graft(FacetGraft(session, asked.project_id, held, act))
    repriced = tuple(plan.copies[each] for each in source.order if each in source.tasks)
    holding = Holding(plan.read.facts, None, conflicts, repriced)
    replayed(session, asked.project_id, asked.target_id, act.at, holding)
