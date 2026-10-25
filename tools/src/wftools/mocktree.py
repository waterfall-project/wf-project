# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rules of the tree the gestures of the structure follow (EP-15/US-0460, #1183, #1169).

Where a node created or moved goes among the siblings of its parent — the lines of a task before
its subordinates —, and the loop a link or a move would close, a chain of links that may cross
the hierarchy: the fake back says them as the server does, and ``wftools.mockgestures`` writes its
answers by them. ``mockdating.schedule`` refuses the structures a loop would leave.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from wftools import mockdating
from wftools.mockwitness import CORE

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence

    from wftools.mockwitness import Link, Task

LINE, TASK = "estimate_line", "task"
AT_END: Literal["end"] = "end"
"""``after_node_id`` absent: the node goes after the last of its kind (#1183)."""

type After = int | Literal["end"] | None
"""Where a creation or a move names its place: after a sibling, at the end, or nil, first."""


def placed(
    lines: Sequence[int], tasks: Sequence[int], sent: Sequence[tuple[int, str]], after: After
) -> tuple[list[int], list[int]]:
    """Return the lines and the subordinates of a task once nodes are placed under it, in order.

    The rule of ``NodeCreate`` and ``NodeMove`` (#1183, #1187): the lines of a task precede its
    subordinates. Nil, a line goes first of the lines, a task first of the subordinates; absent, a
    line after the last line, a task after the last subordinate, the nodes moved left out; after a
    sibling of its kind, right after it; after a sibling of the other kind, on the boundary — a
    line after the last line, a task first of the subordinates. The nodes sent are placed in their
    order: the first of each kind where the rule puts it, each next one after the previous one of
    its kind. A node to follow that is not a sibling, or is one of the nodes moved, is refused
    (``NODE_NOT_SIBLING``).
    """
    moved = {number for number, _ in sent}
    kept = {
        LINE: [number for number in lines if number not in moved],
        TASK: [number for number in tasks if number not in moved],
    }
    if after not in {None, AT_END, *kept[LINE], *kept[TASK]}:
        message = f"the node {after} is not a sibling of the nodes placed"
        raise ValueError(message)
    previous: dict[str, int] = {}
    for number, kind in sent:
        own = kept[kind]
        if kind in previous:
            index = own.index(previous[kind]) + 1
        elif after == AT_END:
            index = len(own)
        elif after is None:
            index = 0
        elif after in own:
            index = own.index(after) + 1
        else:
            index = len(own) if kind == LINE else 0
        own.insert(index, number)
        previous[kind] = number
    return kept[LINE], kept[TASK]


START, FINISH = "start", "finish"
"""The end of a task a chain enters it by: by a link, or down from its summary, at its start; up
from a subordinate, at its finish."""


@dataclass(frozen=True, slots=True)
class Plan:
    """What a chain of a structure follows: its links, and its hierarchy, both in plan order."""

    followers: dict[int, list[int]]
    children: dict[int, list[int]]
    parents: dict[int, int]

    def moved(self, number: int, parent: int) -> Plan:
        """Return the plan a task moved, with its subordinates, under another leaves."""
        children = {
            task: [child for child in kids if child != number]
            for task, kids in self.children.items()
        }
        children.setdefault(parent, []).append(number)
        return Plan(self.followers, children, {**self.parents, number: parent})

    def above(self, number: int) -> list[int]:
        """Return a task and its summaries, from the nearest up."""
        found = [number]
        while found[-1] in self.parents:
            found.append(self.parents[found[-1]])
        return found

    def below(self, number: int) -> list[int]:
        """Return a task and its subordinates, in the order of the plan."""
        return [number] + [
            each for child in self.children.get(number, []) for each in self.below(child)
        ]


def plan_of(roots: Iterable[Task]) -> Plan:
    """Return the links and the hierarchy of a structure, in the order of the plan."""
    tasks = mockdating.tasks_in_order(roots)
    followers: dict[int, list[int]] = {}
    for each in tasks:
        for link in each.links:
            followers.setdefault(link.predecessor, []).append(each.number)
    children = {each.number: [child.number for child in each.children] for each in tasks}
    parents = {child: task for task, kids in children.items() for child in kids}
    return Plan(followers, children, parents)


def chain(origin: tuple[int, str], reached: Callable[[int, str], bool], plan: Plan) -> list[int]:
    """Return the shortest chain from a task to one ``reached`` accepts, each preceding the next.

    A chain follows the links, from a predecessor to its successor, which it enters at its start;
    and it crosses the hierarchy, a summary spanning its subordinates (WF-PLA-0040): from a task
    entered at its start down to its subordinates — what precedes the summary precedes them —, and
    from a task up to its summary, which finishes after it — what follows the summary follows it.
    A task entered at its start reaches its finish through its subordinates; one entered at its
    finish, from below, does not reach its start. The first found, links before the hierarchy,
    when several are as short; none when no chain leads there.
    """
    paths = [([origin[0]], origin[1])]
    seen = {origin}
    while paths:
        path, end = paths.pop(0)
        here = path[-1]
        steps = [(each, START) for each in plan.followers.get(here, [])]
        if end == START:
            steps += [(each, START) for each in plan.children.get(here, [])]
        if here in plan.parents:
            steps.append((plan.parents[here], FINISH))
        for task, entered in steps:
            if reached(task, entered):
                return [*path, task]
            if (task, entered) not in seen and (task, START) not in seen:
                seen.add((task, entered))
                paths.append(([*path, task], entered))
    return []


def cycle(task: int, links: Iterable[Link], roots: Iterable[Task] = CORE) -> list[int]:
    """Return the tasks of the loop that predecessors sent for a task would close, in link order.

    From the task to the predecessor sent that already follows it, each preceding the next, the
    chain crossing the hierarchy as a move's does (``chain``): the shortest; at equal length, the
    first ``chain`` finds — at each task, its links before the hierarchy, its subordinates before
    its summary, and the links in the order of the plan —, which is the first in the order of the
    links when several predecessors sent close a loop as short; the task alone when it is sent as
    its own predecessor; none when no predecessor sent follows it.
    """
    sent = {link.predecessor for link in links}
    if task in sent:
        return [task]
    return chain((task, START), lambda each, _: each in sent, plan_of(roots))


def move_loop(numbers: Sequence[int], parent: int, roots: Iterable[Task]) -> list[int]:
    """Return the chain a move of tasks would close into a loop through the summary they receive.

    The tasks moved go under the parent, which spans them with its own ancestors (WF-PLA-0040). A
    selection is judged on the structure the move would leave, all its tasks moved (#1169): the
    loop is the one the first in cause closes, in the order of the plan of the structure read —
    not in the order of ``numbers``, which only places them. For a task moved, a chain from one of
    the ancestors, left at its finish, to the task or one of its subordinates, or from these, left
    at their finish, to one of the ancestors entered at its start, would be a loop — the chain
    crossing the hierarchy (``chain``). The shortest, each task preceding the next; at equal
    length, from the nearest ancestor first, then from the task moved and its subordinates in the
    order of the plan. Two tasks: a link between a summary and its subordinate. None when the move
    closes no loop. A parent that is one of the tasks moved, or one of their subordinates, is no
    move (``ValueError``): the tree would lose them.
    """
    roots = tuple(roots)
    read = plan_of(roots)
    for number in numbers:
        if parent in read.below(number):
            message = f"the task {number} cannot be moved under {parent}, which it spans"
            raise ValueError(message)
    plan = read
    for number in numbers:
        plan = plan.moved(number, parent)
    order = [each.number for each in mockdating.tasks_in_order(roots)]
    for number in sorted(numbers, key=order.index):
        found = _loop(plan, number, parent)
        if found:
            return found
    return []


def _loop(plan: Plan, number: int, parent: int) -> list[int]:
    """Return the shortest loop a task moved under a parent closes in a plan, or none."""
    above, below = plan.above(parent), plan.below(number)
    chains = [chain((start, FINISH), lambda each, _: each in below, plan) for start in above]
    chains += [
        chain((start, FINISH), lambda each, end: each in above and end == START, plan)
        for start in below
    ]
    found = [each for each in chains if each]
    return min(found, key=len) if found else []
