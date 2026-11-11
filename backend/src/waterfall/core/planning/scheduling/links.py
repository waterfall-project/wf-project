# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The order the links date a structure in, and the links it refuses (WF-PLA-0030, WF-PLA-0040).

Each task has two ends, its start and its finish. A task without subordinates reaches its finish
from its start; a summary spans its subordinates — what precedes it precedes them, what follows it
follows them —, its start leading to theirs and their finishes to its own; a link leads from the
finish of its predecessor to the start of its successor, whatever its type, as MS Project refuses
any loop. The ends are dated in an order where each comes after those that lead to it; when there
is none, the links close a loop, and the engine refuses it by naming the shortest chain that
closes it (`LINK_CYCLE`). A link between a summary and one of its subordinates closes such a loop
too, but the most precise code wins: it is refused first, as `LINK_FORBIDDEN`.
"""

from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from waterfall.core.planning.scheduling.structure import (
    Entry,
    LinkCycleError,
    LinkForbiddenError,
    Move,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from waterfall.core.planning.scheduling.structure import Link, Origin, Structure

type End = Literal["start", "finish"]
type Point = tuple[UUID, End]
START: End = "start"
FINISH: End = "finish"
ENDS: tuple[End, End] = (START, FINISH)


@dataclass(frozen=True, slots=True)
class Plan:
    """The hierarchy and the links of a structure, each list in the order of the plan."""

    rank: dict[UUID, int]
    children: dict[UUID, list[UUID]]
    parents: dict[UUID, UUID]
    incoming: dict[UUID, list[Link]]
    outgoing: dict[UUID, list[Link]]

    def ancestors(self, task_id: UUID) -> list[UUID]:
        """Return the summaries of a task, from the nearest up."""
        found: list[UUID] = []
        while task_id in self.parents:
            task_id = self.parents[task_id]
            found.append(task_id)
        return found

    def below(self, task_id: UUID) -> list[UUID]:
        """Return a task and its subordinates at every level, in the order of the plan."""
        found = [task_id]
        for child in self.children.get(task_id, []):
            found.extend(self.below(child))
        return found

    def leaves(self, task_id: UUID) -> list[UUID]:
        """Return the tasks without subordinates a task spans: itself when it has none."""
        return [each for each in self.below(task_id) if each not in self.children]


def plan_of(structure: Structure) -> Plan:
    """Return the plan of a structure: its tasks ranked, its hierarchy, its links by task.

    The links leaving a task are ranked by their successor in the order of the plan, so that a
    chain explores them as the plan reads.
    """
    rank = {task.task_id: index for index, task in enumerate(structure.tasks)}
    children: dict[UUID, list[UUID]] = {}
    parents: dict[UUID, UUID] = {}
    for task in structure.tasks:
        if task.parent_id is not None:
            children.setdefault(task.parent_id, []).append(task.task_id)
            parents[task.task_id] = task.parent_id
    incoming: dict[UUID, list[Link]] = {}
    outgoing: dict[UUID, list[Link]] = {}
    for link in sorted(structure.links, key=lambda each: rank[each.successor_id]):
        incoming.setdefault(link.successor_id, []).append(link)
        outgoing.setdefault(link.predecessor_id, []).append(link)
    return Plan(rank, children, parents, incoming, outgoing)


def dating_order(structure: Structure, plan: Plan, origin: Origin) -> list[Point]:
    """Return the ends of the tasks in an order where each follows those that lead to it.

    Refuses first a link between a summary and its subordinate, in the order of the links
    (`LinkForbiddenError`), then a loop (`LinkCycleError`), named from the origin when it closes
    one.
    """
    for link in structure.links:
        if link.predecessor_id in plan.ancestors(link.successor_id):
            raise LinkForbiddenError(link.predecessor_id, link.successor_id)
        if link.successor_id in plan.ancestors(link.predecessor_id):
            raise LinkForbiddenError(link.successor_id, link.predecessor_id)
    leads: dict[Point, list[Point]] = {}
    for task in structure.tasks:
        task_id = task.task_id
        if task_id in plan.children:
            for child in plan.children[task_id]:
                leads.setdefault((task_id, START), []).append((child, START))
                leads.setdefault((child, FINISH), []).append((task_id, FINISH))
        else:
            leads.setdefault((task_id, START), []).append((task_id, FINISH))
    for link in structure.links:
        leads.setdefault((link.predecessor_id, FINISH), []).append((link.successor_id, START))
    waits: dict[Point, int] = {(task.task_id, end): 0 for task in structure.tasks for end in ENDS}
    for target in (each for targets in leads.values() for each in targets):
        waits[target] += 1
    ready: deque[Point] = deque(point for point, count in waits.items() if count == 0)
    order: list[Point] = []
    while ready:
        point = ready.popleft()
        order.append(point)
        for target in leads.get(point, []):
            waits[target] -= 1
            if waits[target] == 0:
                ready.append(target)
    if len(order) < len(waits):
        left = {task_id for (task_id, _), count in waits.items() if count}
        raise LinkCycleError(_loop(plan, origin, left))
    return order


def chain(plan: Plan, origin: Point, reached: Callable[[UUID, End], bool]) -> list[UUID]:
    """Return the shortest chain from an end of a task to a task ``reached`` accepts.

    The chain follows the links, entering a successor at its start, and crosses the hierarchy: from
    a task entered at its start down to its subordinates, and from a task up to its summary, which
    it enters at its finish. A task entered at its start reaches its finish; one entered at its
    finish, from below, does not reach its start. Among chains as short, the first found: at each
    task, its links before the hierarchy, its subordinates before its summary, each in the order of
    the plan (`params.cycle`, docs/api/DECISIONS.md, #1169). None when no chain leads there.
    """
    came: dict[Point, Point | None] = {origin: None}
    queue = deque([origin])
    while queue:
        here, end = point = queue.popleft()
        steps: list[Point] = [(link.successor_id, START) for link in plan.outgoing.get(here, [])]
        if end == START:
            below: list[Point] = [(child, START) for child in plan.children.get(here, [])]
            steps += below
        if here in plan.parents:
            steps.append((plan.parents[here], FINISH))
        for step in steps:
            if reached(*step):
                return [*_path(came, point), step[0]]
            if step not in came and (step[0], START) not in came:
                came[step] = point
                queue.append(step)
    return []


def _path(came: dict[Point, Point | None], point: Point) -> list[UUID]:
    """Return the tasks of the chain that led to an end, from its origin."""
    found: list[UUID] = []
    step: Point | None = point
    while step is not None:
        found.append(step[0])
        step = came[step]
    return found[::-1]


def _loop(plan: Plan, origin: Origin, left: set[UUID]) -> tuple[UUID, ...]:
    """Return the loop to name: from the origin when it closes one, else the structure's."""
    if isinstance(origin, Entry):
        found = _entry_loop(plan, origin)
    elif isinstance(origin, Move):
        found = _move_loop(plan, origin)
    else:
        found = []
    return tuple(found or _structure_loop(plan, left))


def _entry_loop(plan: Plan, entry: Entry) -> list[UUID]:
    """Return the loop the predecessors of a task close, from it to the predecessor sent.

    The task alone when it is its own predecessor; at equal length, the first in the order of the
    links that ``chain`` finds (`setPredecessors`).
    """
    sent = {link.predecessor_id for link in plan.incoming.get(entry.task_id, [])}
    if entry.task_id in sent:
        return [entry.task_id]
    return chain(plan, (entry.task_id, START), _among(sent))


def _move_loop(plan: Plan, move: Move) -> list[UUID]:
    """Return the loop a move closes through the summary that receives the tasks (`moveNodes`).

    For each task moved, in the order of the plan of the structure read: a chain from the parent
    or one of its ancestors, left at its finish, to the task or one of its subordinates; or from
    these, left at their finish, to the parent or an ancestor entered at its start. The shortest;
    at equal length, from the nearest ancestor first, then from the task and its subordinates.
    """
    above = [move.parent_id, *plan.ancestors(move.parent_id)]
    for task_id in move.task_ids:
        below = plan.below(task_id)
        chains = [chain(plan, (summary, FINISH), _among(set(below))) for summary in above]
        chains += [chain(plan, (each, FINISH), _started(set(above))) for each in below]
        found = [each for each in chains if each]
        if found:
            return min(found, key=len)
    return []


def _among(tasks: set[UUID]) -> Callable[[UUID, End], bool]:
    """Return what reaches one of some tasks, by either end."""
    return lambda task_id, _: task_id in tasks


def _started(tasks: set[UUID]) -> Callable[[UUID, End], bool]:
    """Return what reaches one of some tasks at its start."""
    return lambda task_id, end: task_id in tasks and end == START


def _structure_loop(plan: Plan, left: set[UUID]) -> list[UUID]:
    """Return the shortest loop of a structure, from its first task in the order of the plan.

    Each task it passes precedes the next, the last preceding the first; among loops as short, the
    one whose first task comes first (`mergeCostStructure`, docs/api/DECISIONS.md). A loop passes
    the finish of one of its tasks, or the start alone of a summary it enters and leaves by its
    subordinates: both are sought from each task.
    """
    best: list[UUID] = []
    for task_id in sorted(left, key=lambda each: plan.rank[each]):
        loops = (
            chain(plan, (task_id, START), _started({task_id})),
            chain(plan, (task_id, FINISH), _among({task_id})),
        )
        for found in loops:
            if found and (not best or len(found) - 1 < len(best)):
                best = found[:-1]
    return best
