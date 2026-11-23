# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure a merge leaves, as the planning finds it, private to the module (WF-REV-0050).

A differential is matched with the main structure of its revision by the lineage of its tasks
(WF-DAT-0030, C-361), as an import of a planning is with its file (``importing``): the plan of the
merge (``MergePlan``) is the tree of the differential, each task under the node of its lineage in
the main structure — a task the differential adds keeps its node in it —, and each task of the main
structure the differential no longer carries is removed, or kept when it is started or completed,
under its parent after the tasks of the differential (WF-REV-0050); that parent is never removed
either, being started. The links are the differential's; the attachments to the work breakdown the
main structure's, a differential bearing none (WF-PLA-0170).

The occurrence of a risk merges its own estimate in a mode of its own (``OCCURRENCE_MERGE``; EP-30,
"La survenance"): every task it no longer carries is kept and completed, whatever its state — the
rule an amendment applies to a started task (WF-REV-0050; decision of the author of 2026-11-19) —,
the tasks and the lines it adds bear the trace of the risk (``origin_risk_id``), and the completed
tasks of the main structure it reopens are named (``reopening``): each that bears a line the
merge adds or designates (``MergePlan.worked``, which the estimate tells), and each under which a
task not completed comes — added, or moved there —, with the completed summaries above them. The
report names them without refusing, as EP-08 named a graft under a completed task (#4240).

What the report gives of it, in the forms of the contract (``ImportDifference``): each task added
or updated — by its label, its description, its mode, its duration, its dates in manual mode and
its parent, what the differential designates: the dates of an automatic task are computed, not
designated —, each link added, updated or removed, named by its successor, each task removed — the
work package or order item it bore named — or kept; the started tasks kept, which the merge
completes (``ImportCompletedTask``, on the day it is applied). And what refuses it, judged on the
structure every part leaves (``ReportRefusal``): an order item taken out of the subtree of its
work package, then the engine replayed once — a loop, a link across the hierarchy, the horizon —,
each task named by its node in the main structure and its label, a node null for a task added. A
task left without a working hour the estimate names, its lines' roles being its own.

Written by US-2560/L1; what the application writes of it, by US-2560/L2 (``merging_writing``);
the mode of an occurrence by US-3100/L1.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from waterfall.core.planning.attachments import OUTSIDE, carriers, strays
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
from waterfall.core.planning.scheduling import (
    Lag,
    Link,
    LinkCycleError,
    LinkForbiddenError,
    Structure,
    TaskWithoutWorkingHoursError,
    WorkInstant,
    schedule,
)
from waterfall.core.planning.scheduling import Task as Planned
from waterfall.core.planning.tree import LinkRow, read_link_rows, read_rows
from waterfall.core.planning.views import COMPLETED, NOT_STARTED, STARTED, state_of
from waterfall.core.projects.interface import current_day, work_breakdown_items
from waterfall.core.revisions.interface import OCCURRENCE_MERGE, structure_facts

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from datetime import date

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import LagUnit, LinkType
    from waterfall.core.planning.tree import NodeRow, TaskRow, Tree
    from waterfall.core.projects.interface import WorkBreakdownItem
    from waterfall.core.revisions.interface import StructureMerging

type Json = dict[str, Any]
type Pair = tuple[UUID, UUID]
# Where the plan of a merge is kept for the parts after the planning's and for the end.
SHARED = "planning.merge_plan"
PREDECESSORS = "predecessors"


@dataclass(slots=True)
class MergePlan:
    """The structure a merge leaves: the two trees read, and the tasks merged.

    A task merged is named by its node in the main structure, or in the differential for a task it
    adds; ``sources`` the node of the differential each task of it is merged from. ``parents`` and
    ``order`` place them; ``kept`` and ``removed`` are the tasks of the main structure the
    differential no longer carries; ``links`` its links, between tasks merged. ``occurrence``
    whether the merge is the occurrence of a risk, ``risk_id`` that risk, whose trace the nodes
    it adds bear; ``worked`` the lineages of the tasks whose lines the merge adds or designates,
    which the estimate tells (``merge_lines_worked``).
    """

    main: Tree[NodeRow, TaskRow]
    amendment: Tree[NodeRow, TaskRow]
    main_links: list[LinkRow]
    start: date
    sources: dict[UUID, UUID] = field(default_factory=dict[UUID, UUID])
    parents: dict[UUID, UUID | None] = field(default_factory=dict[UUID, UUID | None])
    order: list[UUID] = field(default_factory=list[UUID])
    kept: list[UUID] = field(default_factory=list[UUID])
    removed: list[UUID] = field(default_factory=list[UUID])
    links: dict[Pair, LinkRow] = field(default_factory=dict[Pair, LinkRow])
    summaries: set[UUID] = field(default_factory=set[UUID])
    occurrence: bool = False
    risk_id: UUID | None = None
    worked: set[UUID] = field(default_factory=set[UUID])

    def completes(self, task_id: UUID) -> bool:
        """Tell whether the merge completes a task of the main structure it keeps.

        A started one; in the mode of an occurrence, every one not completed, started or not.
        """
        progress = state_of(self.main, task_id).progress
        return progress != COMPLETED if self.occurrence else progress == STARTED

    def facet(self, task_id: UUID) -> TaskRow:
        """Give the facet of a task: the differential's for a task merged from it, else its own."""
        source = self.sources.get(task_id)
        return self.main.tasks[task_id] if source is None else self.amendment.tasks[source]

    def label_of(self, task_id: UUID) -> str:
        """Give the label of a task merged, or of a task of the main structure removed."""
        return self.facet(task_id).label

    def lineage_of(self, task_id: UUID) -> UUID | None:
        """Give the lineage a task has in the main structure; none for a task added."""
        node = self.main.nodes.get(task_id)
        return None if node is None else node.lineage_id

    def named(self, task_id: UUID) -> Json:
        """Name a task merged as a refusal does: its node in the main structure, its label."""
        node = str(task_id) if task_id in self.main.nodes else None
        return {"node_id": node, "label": self.label_of(task_id)}

    def is_summary(self, task_id: UUID) -> bool:
        """Tell whether a task merged bears a subtask in the structure the merge leaves."""
        return task_id in self.summaries

    def staying(self, task_id: UUID) -> UUID | None:
        """Give the nearest ancestor of a task removed that the merge leaves; none at the top."""
        parent = self.main.nodes[task_id].parent_id
        while parent is not None and parent not in self.parents:
            parent = self.main.nodes[parent].parent_id
        return parent


def _placed(plan: MergePlan, amendment_links: list[LinkRow]) -> None:
    """Place the tasks merged: the differential's in its order, then the kept under their parent.

    An occurrence keeps every task the differential no longer carries, an amendment the started
    and the completed ones.
    """
    main, amendment = plan.main, plan.amendment
    by_lineage = {main.nodes[each].lineage_id: each for each in main.tasks}
    for node_id in amendment.order:
        if node_id in amendment.tasks:
            plan.sources[by_lineage.get(amendment.nodes[node_id].lineage_id, node_id)] = node_id
    merged = {source: task_id for task_id, source in plan.sources.items()}
    for task_id, source in plan.sources.items():
        parent = amendment.nodes[source].parent_id
        plan.parents[task_id] = None if parent is None else merged[parent]
    for task_id in main.order:
        if task_id in main.tasks and task_id not in plan.sources:
            started = state_of(main, task_id).progress != NOT_STARTED
            (plan.kept if started or plan.occurrence else plan.removed).append(task_id)
    staying = {*plan.sources, *plan.kept}
    for task_id in plan.kept:
        # A started task's parent is started too: merged from the differential, or kept; in an
        # occurrence, every task absent is kept, its parent among them.
        parent = main.nodes[task_id].parent_id
        plan.parents[task_id] = parent if parent in staying else None
    children: dict[UUID | None, list[UUID]] = {}
    for task_id, parent in plan.parents.items():
        children.setdefault(parent, []).append(task_id)
    plan.summaries.update(each for each in children if each is not None)
    pending = list(reversed(children.get(None, [])))
    while pending:
        task_id = pending.pop()
        plan.order.append(task_id)
        pending.extend(reversed(children.get(task_id, [])))
    for link in amendment_links:
        plan.links[merged[link.predecessor_id], merged[link.successor_id]] = link


def merge_plan(merging: StructureMerging) -> MergePlan:
    """Give the plan of a merge, built once for its parts and its end; writes nothing."""
    held = merging.shared.get(SHARED)
    if isinstance(held, MergePlan):
        return held
    session, project_id = merging.session, merging.project_id
    main_id, amendment_id = merging.main_structure_id, merging.amendment_id
    start = structure_facts(session, project_id, main_id, lock=False).planning_start_on
    plan = MergePlan(
        read_rows(session, project_id, main_id),
        read_rows(session, project_id, amendment_id),
        read_link_rows(session, project_id, main_id),
        start,
    )
    if merging.mode == OCCURRENCE_MERGE:
        plan.occurrence = True
        plan.risk_id = structure_facts(session, project_id, amendment_id, lock=False).risk_id
        if plan.risk_id is None:
            # Everything the merge adds bears the trace of the risk: none, it would leave without.
            msg = "The own estimate merged as an occurrence belongs to no risk"
            raise RuntimeError(msg)
    _placed(plan, read_link_rows(session, project_id, amendment_id))
    merging.shared[SHARED] = plan
    return plan


# --- The differences ------------------------------------------------------------------------------


def _difference(
    change: str, target: str, named: tuple[UUID | None, str], fields: list[str]
) -> Json:
    """Give a difference of the differential with the main structure (``ImportDifference``)."""
    lineage, label = named
    return {
        "change": change,
        "target": target,
        "lineage_id": None if lineage is None else str(lineage),
        "label": label,
        "predecessor_label": None,
        "fields": fields,
    }


def task_fields(plan: MergePlan, task_id: UUID) -> list[str]:
    """Name the columns the differential changes of a task, in the order of the grid, then parent.

    A summary's mode, duration and dates are derived; an automatic task's dates are computed.
    """
    old, new = plan.main.tasks[task_id], plan.facet(task_id)
    fields = [name for name in ("label", "description") if getattr(old, name) != getattr(new, name)]
    if not plan.is_summary(task_id):
        if old.scheduling_mode != new.scheduling_mode:
            fields.append("scheduling_mode")
        if duration_of(old) != duration_of(new):
            fields.append("duration")
        if new.scheduling_mode == MANUAL:
            if (old.start_date, old.start_hours) != (new.start_date, new.start_hours):
                fields.append("start")
            if (old.finish_date, old.finish_hours) != (new.finish_date, new.finish_hours):
                fields.append("finish")
    if plan.main.nodes[task_id].parent_id != plan.parents[task_id]:
        fields.append("parent")
    return fields


def _link(plan: MergePlan, change: str, pair: Pair, fields: list[str]) -> Json:
    """Give a difference of a link, named by its successor, its predecessor's label beside."""
    predecessor, successor = pair
    found = _difference(
        change, "link", (plan.lineage_of(successor), plan.label_of(successor)), fields
    )
    found["predecessor_label"] = plan.label_of(predecessor)
    return found


def _links(plan: MergePlan) -> Iterator[Json]:
    """Give the links added, updated — by their type or their lag — or removed."""
    held = {(each.predecessor_id, each.successor_id): each for each in plan.main_links}
    for pair, link in plan.links.items():
        old = held.get(pair)
        if old is None:
            yield _link(plan, "added", pair, [])
        elif (old.link_type, old.lag_value, old.lag_unit) != (
            link.link_type,
            link.lag_value,
            link.lag_unit,
        ):
            yield _link(plan, "updated", pair, [PREDECESSORS])
    for pair in held:
        if pair not in plan.links:
            yield _link(plan, "removed", pair, [])


def _absent(plan: MergePlan, items: Mapping[UUID, WorkBreakdownItem]) -> Iterator[Json]:
    """Give the tasks the differential no longer carries: kept, or removed with what they bore."""
    kept = set(plan.kept)
    for task_id in plan.main.order:
        if task_id not in kept and task_id not in plan.removed:
            continue
        named = (plan.lineage_of(task_id), plan.label_of(task_id))
        if task_id in kept:
            yield _difference("kept", "task", named, [])
            continue
        found = _difference("removed", "task", named, [])
        task = plan.main.tasks[task_id]
        item_id = task.work_package_id or task.order_item_id
        item = None if item_id is None else items.get(item_id)
        if item is not None:
            found["work_breakdown_label"] = item.label
        yield found


def task_differences(
    merging: StructureMerging,
) -> tuple[tuple[Json, ...], tuple[Json, ...]]:
    """Give what the planning finds of a merge: its differences, and the tasks it completes.

    A task the merge completes (``MergePlan.completes``) takes the day it is applied; none in the
    report.
    """
    plan = merge_plan(merging)
    differences: list[Json] = []
    for task_id in plan.order:
        if task_id not in plan.sources:
            continue
        if task_id not in plan.main.nodes:
            differences.append(_difference("added", "task", (None, plan.label_of(task_id)), []))
            continue
        fields = task_fields(plan, task_id)
        if fields:
            named = (plan.lineage_of(task_id), plan.label_of(task_id))
            differences.append(_difference("updated", "task", named, fields))
    differences += _links(plan)
    differences += _absent(plan, work_breakdown_items(merging.session, merging.project_id))
    day = current_day(merging.act.at).isoformat() if merging.applying else None
    completed = tuple(
        {
            "lineage_id": str(plan.lineage_of(task_id)),
            "label": plan.label_of(task_id),
            "completed_on": day,
        }
        for task_id in plan.kept
        if plan.completes(task_id)
    )
    return tuple(differences), completed


def reopening(plan: MergePlan) -> list[UUID]:
    """Give the completed tasks of the main structure an occurrence reopens, in the plan's order.

    Each that bears a line the merge adds or designates (``MergePlan.worked``), each under which a
    task not completed comes — added, or moved there from another parent —, and the summaries
    above them, each one completed before the merge; none for an amendment, whose rule is
    unchanged.
    """
    if not plan.occurrence:
        return []
    main = plan.main
    by_lineage = {main.nodes[each].lineage_id: each for each in plan.order if each in main.nodes}
    starts = {by_lineage[each] for each in plan.worked if each in by_lineage}
    for task_id in plan.order:
        parent = plan.parents[task_id]
        if parent is None or task_id in plan.kept:
            continue
        held = main.nodes.get(task_id)
        if held is None or (
            held.parent_id != parent and state_of(main, task_id).progress != COMPLETED
        ):
            starts.add(parent)
    reached: set[UUID] = set()
    for each in starts:
        above: UUID | None = each
        while above is not None and above not in reached:
            reached.add(above)
            above = plan.parents[above]
    return [
        each
        for each in plan.order
        if each in reached and each in main.nodes and state_of(main, each).progress == COMPLETED
    ]


def reopened_named(plan: MergePlan) -> tuple[Json, ...]:
    """Name the tasks an occurrence reopens by their node in the main structure and their label."""
    return tuple(plan.named(each) for each in reopening(plan))


# --- The refusals ---------------------------------------------------------------------------------


def _strays(plan: MergePlan, items: Mapping[UUID, WorkBreakdownItem]) -> list[Json]:
    """Refuse a merge that takes the task of an order item out of that of its work package."""
    borne = {item: task for item, task in carriers(plan.main).items() if task in plan.parents}

    def is_under(task_id: UUID, summary: UUID) -> bool:
        above = plan.parents[task_id]
        while above is not None and above != summary:
            above = plan.parents[above]
        return above == summary

    rank = {task_id: index for index, task_id in enumerate(plan.order)}
    return [
        {
            "code": OUTSIDE,
            "params": {
                "work_package_task": plan.named(package_task),
                "order_item_tasks": [
                    plan.named(each) for each in sorted(item_tasks, key=rank.__getitem__)
                ],
            },
        }
        for package_task, item_tasks in strays(items, borne, is_under)
    ]


def _planned(plan: MergePlan, task_id: UUID, calendars: Mapping[UUID, Applicable]) -> Planned:
    """Give a task merged as the engine reads it, on the calendar of the node it is merged from."""
    task = plan.facet(task_id)
    manual = task.scheduling_mode == MANUAL and not plan.is_summary(task_id)
    return Planned(
        task_id,
        plan.parents[task_id],
        MANUAL if manual else AUTOMATIC,
        duration_of(task),
        calendars[plan.sources.get(task_id, task_id)].calendar,
        WorkInstant(task.start_date, task.start_hours) if manual else None,
        WorkInstant(task.finish_date, task.finish_hours) if manual else None,
    )


def _replayed(merging: StructureMerging, plan: MergePlan) -> list[Json]:
    """Replay the engine once on the structure the merge leaves; give what refuses it.

    A loop, named from the first of its tasks in the order of the plan, or a link between a summary
    and its subordinate, the summary first, leave the dates without a calculation: the horizon is
    then not judged (#788), nor when a task has no working hour, which the estimate names. Beyond
    fifteen years, the task that finishes last is named.
    """
    if not plan.order:
        return []
    session = merging.session
    calendars = calendars_of(
        session, merging.project_id, [plan.sources.get(each, each) for each in plan.order]
    )
    links = tuple(
        Link(
            pair[0],
            pair[1],
            cast("LinkType", link.link_type),
            Lag(link.lag_value, cast("LagUnit", link.lag_unit)),
        )
        for pair, link in plan.links.items()
    )
    tasks = tuple(_planned(plan, each, calendars) for each in plan.order)
    try:
        computed = schedule(Structure(tasks, links, plan.start, constants_of(session)))
    except LinkCycleError as loop:
        return [
            {"code": LINK_CYCLE, "params": {"cycle": [plan.named(each) for each in loop.cycle]}}
        ]
    except LinkForbiddenError as forbidden:
        ends = (forbidden.summary_id, forbidden.subordinate_id)
        return [{"code": LINK_FORBIDDEN, "params": {"link": [plan.named(each) for each in ends]}}]
    except TaskWithoutWorkingHoursError:
        # The estimate names the task and its roles (``TASK_WITHOUT_WORKING_HOURS``), as for an
        # update; the dates are not computed, and the horizon is not judged.
        return []
    beyond = computed.horizon_exceeded_by
    if beyond is None:
        return []
    return [{"code": PROJECT_HORIZON_EXCEEDED, "params": {"task": plan.named(beyond)}}]


def merge_refusals(merging: StructureMerging) -> tuple[Json, ...]:
    """Judge the structure a merge leaves, once every part is given; give what refuses it."""
    plan = merge_plan(merging)
    items = work_breakdown_items(merging.session, merging.project_id)
    return (*_strays(plan, items), *_replayed(merging, plan))
