# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The differential an update leaves, as the planning finds it, private to the module (US-3050/L3).

Three structures are read whole and matched by the lineage of their tasks (WF-DAT-0030): the main
structure, a differential and its base (EP-08, "La base d'un différentiel et sa mise à jour").

- **What a structure designates** (``designated``) is its gap to its base: the tasks it adds, those
  it removes, and for those of both the columns that differ — those the report of a merge names,
  its label, its description, its mode, its duration, its dates in manual mode, its parent
  (US-2560/L1) —; the links it adds, removes, or whose type or lag it changes. It names no nature
  of structure: the main structure's gap to the same base is computed likewise, which is what it
  has received since.
- **The update** (``RebasePlan``) carries what the main structure has received into the
  differential, without changing what the differential designates: a task the main structure adds
  enters it under its lineage, at its place — after the sibling that precedes it there —; a column
  it changes is changed; a task it removes leaves it. Four rules say what it does not carry, each
  signalled by a ``kept`` difference: a column both change keeps the differential's, the columns
  named (1) — a parent the main structure gives a task under one the differential moved under it,
  which would close a loop, among them —; a task the differential modifies and the main structure
  removes stays, as an addition (2); a task the differential adds under a task that leaves stays,
  under the nearest ancestor that remains, or at the first level, and one it moves there goes
  likewise, its parent named (3); a link the differential adds to a task that leaves goes (4),
  judged on the differential the update leaves. A task the differential removes and the main
  structure no longer has is not signalled.
- **What refuses it** is judged once on the differential it leaves, the engine replayed: a loop, a
  link across the hierarchy, the horizon (WF-PLA-0030, WF-PLA-0150), each task named by its node in
  the differential and its label, null for a task the main structure adds.

The plan is keyed by lineage, which every structure of the three holds once for a task: the
application (``rebasing_writing``, US-3050/L4) writes it as the report presents it.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from waterfall.core.planning.calendars import applicable_calendars
from waterfall.core.planning.dating import (
    AUTOMATIC,
    LINK_CYCLE,
    LINK_FORBIDDEN,
    MANUAL,
    PROJECT_HORIZON_EXCEEDED,
    constants_of,
    duration_of,
)
from waterfall.core.planning.interface.facets import named_calendars
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
from waterfall.core.revisions.interface import structure_facts

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping
    from datetime import date

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import LagUnit, LinkType
    from waterfall.core.planning.tree import Conflict, NodeRow, TaskRow, Tree
    from waterfall.core.revisions.interface import StructureRebasing

type Json = dict[str, Any]
# A link by the lineages of its predecessor and of its successor.
type Pair = tuple[UUID, UUID]
# Where the plan of an update is kept for the parts after the planning's and for the end.
SHARED = "planning.rebase_plan"
PREDECESSORS = "predecessors"
PARENT = "parent"
# The columns of a task a structure designates, in the order of the grid, then its parent.
FIELDS = ("label", "description", "scheduling_mode", "duration", "start", "finish", PARENT)
# The columns of the facet each field writes.
COLUMNS: Mapping[str, tuple[str, ...]] = {
    "label": ("label",),
    "description": ("description",),
    "scheduling_mode": ("scheduling_mode",),
    "duration": ("duration_value", "duration_unit"),
    "start": ("start_date", "start_hours"),
    "finish": ("finish_date", "finish_hours"),
}


@dataclass(frozen=True, slots=True)
class Side:
    """A structure read whole, by lineage: its tree, its tasks, its links."""

    tree: Tree[NodeRow, TaskRow]
    tasks: dict[UUID, UUID]
    links: dict[Pair, LinkRow]

    def has(self, lineage: UUID) -> bool:
        """Tell whether the structure holds a task of the lineage."""
        return lineage in self.tasks

    def task(self, lineage: UUID) -> TaskRow:
        """Give the facet of the task of a lineage."""
        return self.tree.tasks[self.tasks[lineage]]

    def parent(self, lineage: UUID) -> UUID | None:
        """Give the lineage of the parent of a task, none at the first level."""
        parent = self.tree.nodes[self.tasks[lineage]].parent_id
        return None if parent is None else self.tree.nodes[parent].lineage_id

    def is_summary(self, lineage: UUID) -> bool:
        """Tell whether the task of a lineage bears a subtask in the structure."""
        return self.tree.is_summary(self.tasks[lineage])

    def order(self) -> list[UUID]:
        """Give the lineages of the tasks in the order of the plan."""
        return [
            self.tree.nodes[each].lineage_id for each in self.tree.order if each in self.tree.tasks
        ]

    def children(self, lineage: UUID | None) -> list[UUID]:
        """Give the lineages of the subtasks of a task — of the first level for none —, in order."""
        node = None if lineage is None else self.tasks[lineage]
        return [self.tree.nodes[each].lineage_id for each in self.tree.subtasks(node)]


def read_side(session: Session, project_id: UUID, structure_id: UUID) -> Side:
    """Read a structure whole, its tasks and its links by lineage."""
    tree = read_rows(session, project_id, structure_id)
    tasks = {tree.nodes[each].lineage_id: each for each in tree.tasks}
    links = {
        (tree.nodes[link.predecessor_id].lineage_id, tree.nodes[link.successor_id].lineage_id): link
        for link in read_link_rows(session, project_id, structure_id)
    }
    return Side(tree, tasks, links)


def value_of(side: Side, lineage: UUID, name: str) -> object:
    """Give the value of a field of a task, as a gap compares it."""
    if name == PARENT:
        return side.parent(lineage)
    task = side.task(lineage)
    if name == "duration":
        return duration_of(task)
    return tuple(getattr(task, column) for column in COLUMNS[name])


def _named_fields(base: Side, structure: Side, lineage: UUID) -> frozenset[str]:
    """Name the fields a structure changes of a task of its base.

    A summary's mode, duration and dates are derived; an automatic task's dates are computed.
    """
    task = structure.task(lineage)
    derived = structure.is_summary(lineage)
    names = [
        name
        for name in FIELDS
        if not (derived and name in {"scheduling_mode", "duration", "start", "finish"})
        and not (name in {"start", "finish"} and task.scheduling_mode != MANUAL)
    ]
    return frozenset(
        name
        for name in names
        if value_of(base, lineage, name) != value_of(structure, lineage, name)
    )


def _link_values(link: LinkRow) -> tuple[object, ...]:
    """Give what a link designates: its type and its lag."""
    return (link.link_type, link.lag_value, link.lag_unit)


@dataclass(frozen=True, slots=True)
class Gap:
    """What a structure designates against its base, by lineage (EP-08, US-3050).

    ``added`` and ``removed`` its tasks, ``changed`` the fields of each task of both that differ,
    ``links_added``, ``links_removed`` and ``links_changed`` its links by their two lineages.
    """

    added: frozenset[UUID]
    removed: frozenset[UUID]
    changed: Mapping[UUID, frozenset[str]]
    links_added: frozenset[Pair]
    links_removed: frozenset[Pair]
    links_changed: frozenset[Pair]


def designated(base: Side, structure: Side) -> Gap:
    """Give what a structure designates: its gap to its base, by the lineage (WF-REV-0100).

    Computed on demand, never kept; the same for a differential and for the main structure, whose
    gap to the base of a differential is what it has received since.
    """
    changed = {
        lineage: found
        for lineage in structure.tasks
        if base.has(lineage) and (found := _named_fields(base, structure, lineage))
    }
    return Gap(
        added=frozenset(each for each in structure.tasks if not base.has(each)),
        removed=frozenset(each for each in base.tasks if not structure.has(each)),
        changed=changed,
        links_added=frozenset(each for each in structure.links if each not in base.links),
        links_removed=frozenset(each for each in base.links if each not in structure.links),
        links_changed=frozenset(
            pair
            for pair, link in structure.links.items()
            if pair in base.links and _link_values(base.links[pair]) != _link_values(link)
        ),
    )


@dataclass(slots=True)
class RebasePlan:
    """The differential an update leaves: the three structures read, and the tasks it holds.

    Every task is named by its lineage. ``parents`` and ``order`` place the tasks the update
    leaves; ``carried`` the fields of each task of both that the main structure changes and the
    differential takes; ``kept_fields`` those it keeps against it (rule 1); ``added`` the tasks
    the main structure adds, ``removed`` those that leave the differential, in its order;
    ``kept`` the tasks the rules 2 and 3 keep, signalled; ``links`` the links the update leaves,
    and ``link_changes`` what it does of each — its change, its pair, its fields. ``nodes`` the
    node of each task in the differential, given by the application as it writes (a task the main
    structure adds takes a new one), empty while the report reads; ``conflicts`` those of the
    differential before the application wrote its links (``kept``), read as it starts to write.
    """

    base: Side
    structure: Side
    main: Side
    start: date
    designated: Gap
    received: Gap
    parents: dict[UUID, UUID | None] = field(default_factory=dict[UUID, UUID | None])
    order: list[UUID] = field(default_factory=list[UUID])
    carried: dict[UUID, frozenset[str]] = field(default_factory=dict[UUID, frozenset[str]])
    kept_fields: dict[UUID, frozenset[str]] = field(default_factory=dict[UUID, frozenset[str]])
    added: list[UUID] = field(default_factory=list[UUID])
    removed: list[UUID] = field(default_factory=list[UUID])
    kept: list[UUID] = field(default_factory=list[UUID])
    links: dict[Pair, LinkRow] = field(default_factory=dict[Pair, LinkRow])
    link_changes: list[tuple[str, Pair, list[str]]] = field(
        default_factory=list[tuple[str, Pair, list[str]]]
    )
    summaries: set[UUID] = field(default_factory=set[UUID])
    nodes: dict[UUID, UUID] = field(default_factory=dict[UUID, UUID])
    conflicts: frozenset[Conflict] = frozenset()

    def holds(self, lineage: UUID | None) -> bool:
        """Tell whether the update leaves a task of the lineage — the first level always."""
        return lineage is None or lineage in self.parents

    def facet(self, lineage: UUID) -> TaskRow:
        """Give the facet a task has once updated: the differential's, the columns carried taken."""
        if not self.structure.has(lineage):
            return self.main.task(lineage)
        task = self.structure.task(lineage)
        carried = self.carried.get(lineage, frozenset())
        if not carried:
            return task
        taken = self.main.task(lineage)
        columns = [column for name in carried if name != PARENT for column in COLUMNS[name]]
        return task._replace(**{column: getattr(taken, column) for column in columns})

    def label_of(self, lineage: UUID) -> str:
        """Give the label of a task: as updated, or in the differential for one that leaves it."""
        if self.holds(lineage):
            return self.facet(lineage).label
        side = self.structure if self.structure.has(lineage) else self.main
        return side.task(lineage).label

    def named(self, lineage: UUID) -> Json:
        """Name a task as a refusal does: its node in the differential, null for one it lacks."""
        held = self.structure.tasks.get(lineage)
        return {"node_id": None if held is None else str(held), "label": self.label_of(lineage)}

    def above(self, lineage: UUID) -> UUID | None:
        """Give the parent a task has where it is read: the differential, the main, the base."""
        for side in (self.structure, self.main, self.base):
            if side.has(lineage):
                return side.parent(lineage)
        return None

    def staying(self, lineage: UUID | None) -> UUID | None:
        """Give the nearest task the update leaves, from a task and up; none at the first level."""
        while not self.holds(lineage):
            lineage = self.above(cast("UUID", lineage))
        return lineage


def _kept_tasks(plan: RebasePlan) -> list[UUID]:
    """Give the tasks the update leaves, the differential's then the main's; name the removed.

    A task the main structure removes stays if the differential modifies it (rule 2), signalled.
    """
    structure, designates, received = plan.structure, plan.designated, plan.received
    left: list[UUID] = []
    for lineage in structure.order():
        if lineage not in received.removed:
            left.append(lineage)
        elif lineage in designates.changed:
            left.append(lineage)
            plan.kept.append(lineage)
        else:
            plan.removed.append(lineage)
    left += [each for each in plan.main.order() if each in received.added]
    return left


def _intended(plan: RebasePlan, lineage: UUID) -> UUID | None:
    """Give the parent a task would have once updated, before what leaves is accounted for."""
    if not plan.structure.has(lineage):
        return plan.main.parent(lineage)
    if PARENT in plan.carried.get(lineage, frozenset()):
        return plan.main.parent(lineage)
    return plan.structure.parent(lineage)


def _fields(plan: RebasePlan) -> None:
    """Give each task of the three the fields carried, and those kept against the main (rule 1).

    The dates of a task are its own in manual mode only: neither carried nor kept when the task is
    automatic once updated — the mode carried if the main structure changes it alone.
    """
    designates, received = plan.designated.changed, plan.received.changed
    for lineage, changed in received.items():
        if not plan.structure.has(lineage):
            continue
        own = designates.get(lineage, frozenset())
        carried = changed - own
        mode = plan.main if "scheduling_mode" in carried else plan.structure
        named = changed
        if mode.task(lineage).scheduling_mode != MANUAL:
            named = changed - {"start", "finish"}
        plan.carried[lineage] = named - own
        plan.kept_fields[lineage] = frozenset(
            name
            for name in named & own
            if value_of(plan.main, lineage, name) != value_of(plan.structure, lineage, name)
        )


def _insert(plan: RebasePlan, children: list[UUID], lineage: UUID, parent: UUID | None) -> None:
    """Insert a task the main structure places among the children of its parent, at its place.

    After the nearest sibling that precedes it in the main structure and that is there; first if
    none and its parent is the main structure's; last under another parent.
    """
    if parent == plan.main.parent(lineage):
        siblings = plan.main.children(parent)
        before = siblings[: siblings.index(lineage)]
        for sibling in reversed(before):
            if sibling in children:
                children.insert(children.index(sibling) + 1, lineage)
                return
        children.insert(0, lineage)
        return
    children.append(lineage)


def _closes(plan: RebasePlan, lineage: UUID) -> bool:
    """Tell whether the parent a task would have once updated has it among its ancestors."""
    seen: set[UUID] = set()
    above = plan.staying(_intended(plan, lineage))
    while above is not None and above not in seen:
        if above == lineage:
            return True
        seen.add(above)
        above = plan.staying(_intended(plan, above))
    return False


def _unlooped(plan: RebasePlan, left: list[UUID]) -> None:
    """Keep off each parent the main structure carries that would close a loop of the hierarchy.

    Two moves make it — the differential moves a task under another, the main structure that one
    under the first —: the differential's wins. The task the main structure moves stays where the
    differential has it, its parent kept against the main structure, as rule 1 keeps a value. Until
    no carried parent closes a loop: one kept off may leave another closing.
    """
    looping = True
    while looping:
        looping = False
        for lineage in left:
            if PARENT in plan.carried.get(lineage, frozenset()) and _closes(plan, lineage):
                plan.carried[lineage] -= {PARENT}
                plan.kept_fields[lineage] |= {PARENT}
                looping = True


def _placed(plan: RebasePlan) -> None:
    """Place the tasks the update leaves: parents, order, summaries; signal the rule 3.

    The differential's tasks stay in its order under their parent; those the main structure places
    — added, or moved by a parent carried — take their place there; those whose parent leaves go
    under the nearest ancestor that remains, in the differential's order among its children: at the
    place the task that leaves held there. A task of the base the differential moves under a task
    that leaves goes there likewise, its parent kept, signalled as rule 3 signals a task it adds.
    """
    left = _kept_tasks(plan)
    _fields(plan)
    plan.parents.update(dict.fromkeys(left))
    _unlooped(plan, left)
    for lineage in left:
        intended = _intended(plan, lineage)
        plan.parents[lineage] = plan.staying(intended)
        if plan.parents[lineage] == intended or not plan.structure.has(lineage):
            continue
        if not plan.base.has(lineage):
            # Rule 3: a task the differential adds under a task that leaves.
            plan.kept.append(lineage)
        elif PARENT in plan.designated.changed.get(lineage, frozenset()):
            # Rule 3, for a task the differential moves under a task that leaves.
            kept = plan.kept_fields.get(lineage, frozenset())
            plan.kept_fields[lineage] = kept | {PARENT}
    children: dict[UUID | None, list[UUID]] = {}
    placed_by_main: list[UUID] = []
    held = set(left)
    for lineage in plan.structure.order():
        if lineage not in held:
            continue
        parent = plan.parents[lineage]
        if parent == plan.structure.parent(lineage):
            children.setdefault(parent, []).append(lineage)
        elif _intended(plan, lineage) == parent:
            placed_by_main.append(lineage)
        else:
            children.setdefault(parent, []).append(lineage)
    added = [each for each in left if not plan.structure.has(each)]
    plan.added.extend(added)
    placed_by_main += added
    for lineage in placed_by_main:
        parent = plan.parents[lineage]
        _insert(plan, children.setdefault(parent, []), lineage, parent)
    plan.summaries.update(each for each, below in children.items() if each is not None and below)
    pending = list(reversed(children.get(None, [])))
    while pending:
        lineage = pending.pop()
        plan.order.append(lineage)
        pending.extend(reversed(children.get(lineage, [])))


def _linked(plan: RebasePlan) -> None:
    """Give the links the update leaves, and what it does of each, by their two lineages."""
    base, structure, main = plan.base.links, plan.structure.links, plan.main.links
    designates, received = plan.designated, plan.received
    pairs = list(dict.fromkeys([*structure, *main, *base]))
    for pair in pairs:
        both = plan.holds(pair[0]) and plan.holds(pair[1])
        if pair in base:
            if pair in received.links_removed and pair not in designates.links_removed:
                _received_removed(plan, pair, both=both)
            elif pair in structure and pair in main:
                _both_held(plan, pair)
            continue
        if pair in structure and pair in main:
            plan.links[pair] = structure[pair]
            if _link_values(structure[pair]) != _link_values(main[pair]):
                plan.link_changes.append(("kept", pair, [PREDECESSORS]))
        elif pair in structure:
            if both:
                plan.links[pair] = structure[pair]
            else:
                # Rule 4: a link the differential adds to a task that leaves goes.
                plan.link_changes.append(("kept", pair, []))
        elif both:
            plan.links[pair] = main[pair]
            plan.link_changes.append(("added", pair, []))


def _received_removed(plan: RebasePlan, pair: Pair, *, both: bool) -> None:
    """Remove a link the main structure removed, or keep it if the differential changed it."""
    if both and pair in plan.designated.links_changed:
        plan.links[pair] = plan.structure.links[pair]
        plan.link_changes.append(("kept", pair, []))
        return
    plan.link_changes.append(("removed", pair, []))


def _both_held(plan: RebasePlan, pair: Pair) -> None:
    """Carry a link the main structure changed, or keep the differential's if it changed it too."""
    own, taken = plan.structure.links[pair], plan.main.links[pair]
    if pair not in plan.received.links_changed:
        plan.links[pair] = own
    elif pair not in plan.designated.links_changed:
        plan.links[pair] = taken
        plan.link_changes.append(("updated", pair, [PREDECESSORS]))
    else:
        plan.links[pair] = own
        if _link_values(own) != _link_values(taken):
            plan.link_changes.append(("kept", pair, [PREDECESSORS]))


def rebase_plan(rebasing: StructureRebasing) -> RebasePlan:
    """Give the plan of an update, built once for its parts and its end; writes nothing."""
    held = rebasing.shared.get(SHARED)
    if isinstance(held, RebasePlan):
        return held
    session, project_id = rebasing.session, rebasing.project_id
    base = read_side(session, project_id, rebasing.base_id)
    structure = read_side(session, project_id, rebasing.structure_id)
    main = read_side(session, project_id, rebasing.main_structure_id)
    start = structure_facts(
        session, project_id, rebasing.structure_id, lock=False
    ).planning_start_on
    plan = RebasePlan(
        base, structure, main, start, designated(base, structure), designated(base, main)
    )
    _placed(plan)
    _linked(plan)
    rebasing.shared[SHARED] = plan
    return plan


# --- The differences ------------------------------------------------------------------------------


def _difference(change: str, target: str, named: tuple[UUID, str], fields: list[str]) -> Json:
    """Give a difference the update carries or keeps (``ImportDifference``)."""
    lineage, label = named
    return {
        "change": change,
        "target": target,
        "lineage_id": str(lineage),
        "label": label,
        "predecessor_label": None,
        "fields": fields,
    }


def _ordered(names: Collection[str]) -> list[str]:
    """Give fields in the order of the grid, then the parent."""
    return [name for name in FIELDS if name in names]


def _tasks(plan: RebasePlan) -> Iterator[Json]:
    """Give the tasks added, updated or kept, in the order of the plan, then those removed."""
    added, kept = set(plan.added), set(plan.kept)
    for lineage in plan.order:
        named = (lineage, plan.label_of(lineage))
        if lineage in added:
            yield _difference("added", "task", named, [])
            continue
        carried = plan.carried.get(lineage, frozenset())
        if carried:
            yield _difference("updated", "task", named, _ordered(carried))
        kept_fields = plan.kept_fields.get(lineage, frozenset())
        if kept_fields or lineage in kept:
            yield _difference("kept", "task", named, _ordered(kept_fields))
    for lineage in plan.removed:
        yield _difference("removed", "task", (lineage, plan.label_of(lineage)), [])


def _links(plan: RebasePlan) -> Iterator[Json]:
    """Give the links the update carries or keeps, named by their successor."""
    for change, (predecessor, successor), fields in plan.link_changes:
        found = _difference(change, "link", (successor, plan.label_of(successor)), fields)
        found["predecessor_label"] = plan.label_of(predecessor)
        yield found


def task_differences(rebasing: StructureRebasing) -> tuple[Json, ...]:
    """Give what the planning finds of an update: its tasks, then its links."""
    plan = rebase_plan(rebasing)
    return (*_tasks(plan), *_links(plan))


# --- The refusals ---------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RebasedCalendars:
    """The calendars the facets of the kinds name under each task the update leaves, by lineage.

    Given by the estimate, whose lines the update changes too (``shared``, ``CALENDARS``): the
    engine replayed reads the calendar of each task as its lines will name it.
    """

    by_task: Mapping[UUID, Collection[UUID]]


# Where the estimate hands the calendars of the tasks of an update to the end of the planning.
CALENDARS = "planning.rebase_calendars"


def _calendars(rebasing: StructureRebasing, plan: RebasePlan) -> Mapping[UUID, Applicable]:
    """Give the calendar applicable to each task the update leaves, by lineage.

    As the estimate names them, if it does; else as the nodes the tasks come from name them.
    """
    session = rebasing.session
    given = rebasing.shared.get(CALENDARS)
    if isinstance(given, RebasedCalendars):
        named = {each: set(given.by_task.get(each, ())) for each in plan.order}
        return applicable_calendars(session, named)
    sources = {
        (plan.structure if plan.structure.has(each) else plan.main).tasks[each]: each
        for each in plan.order
    }
    found = named_calendars(session, rebasing.project_id, list(sources))
    return applicable_calendars(session, {sources[node]: held for node, held in found.items()})


def _planned(plan: RebasePlan, lineage: UUID, calendars: Mapping[UUID, Applicable]) -> Planned:
    """Give a task the update leaves as the engine reads it."""
    task = plan.facet(lineage)
    manual = task.scheduling_mode == MANUAL and lineage not in plan.summaries
    return Planned(
        lineage,
        plan.parents[lineage],
        MANUAL if manual else AUTOMATIC,
        duration_of(task),
        calendars[lineage].calendar,
        WorkInstant(task.start_date, task.start_hours) if manual else None,
        WorkInstant(task.finish_date, task.finish_hours) if manual else None,
    )


def rebase_refusals(rebasing: StructureRebasing) -> tuple[Json, ...]:
    """Replay the engine once on the differential the update leaves; give what refuses it.

    A loop, named from the first of its tasks in the order of the plan, or a link between a summary
    and its subordinate, the summary first, leave the dates without a calculation: the horizon is
    then not judged (#788), nor when a task has no working hour, which the estimate names. Beyond
    fifteen years, the task that finishes last is named.
    """
    plan = rebase_plan(rebasing)
    if not plan.order:
        return ()
    session = rebasing.session
    calendars = _calendars(rebasing, plan)
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
        return (
            {"code": LINK_CYCLE, "params": {"cycle": [plan.named(each) for each in loop.cycle]}},
        )
    except LinkForbiddenError as forbidden:
        ends = (forbidden.summary_id, forbidden.subordinate_id)
        return ({"code": LINK_FORBIDDEN, "params": {"link": [plan.named(each) for each in ends]}},)
    except TaskWithoutWorkingHoursError:
        # The estimate names the task and its roles (``TASK_WITHOUT_WORKING_HOURS``); the dates
        # are not computed, and the horizon is not judged.
        return ()
    beyond = computed.horizon_exceeded_by
    if beyond is None:
        return ()
    return ({"code": PROJECT_HORIZON_EXCEEDED, "params": {"task": plan.named(beyond)}},)
