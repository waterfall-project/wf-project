# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The links the hierarchy refuses: a summary bound to its subordinate, a loop through a summary.

``mockcore.schedule`` dates no structure the server would refuse (WF-PLA-0030, WF-PLA-0040): the
loops among links alone are found as it orders the tasks (``mockcore.in_link_order``), those that
pass through a summary here, with the links that bind a summary to its subordinate, which a move
or an indentation makes under a task already linked to what it receives (#1164).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from wftools.mockwitness import Task


def _below(children: Iterable[Task]) -> list[Task]:
    """Return the subordinates of a summary, at every level."""
    found: list[Task] = []
    for child in children:
        found.append(child)
        found.extend(_below(child.children))
    return found


def refuse_through_summaries(tasks: list[Task]) -> None:
    """Refuse a link that binds a summary to its subordinate, or closes a loop through a summary.

    A summary spans its subordinates (WF-PLA-0040): what precedes it precedes each of them, what
    follows it follows each of them. A link between a summary and one of its subordinates is
    refused (WF-PLA-0030), and so is a chain of links that leads from a summary to one of its
    subordinates, or back: a move or an indentation makes them, under a task already linked to
    what it receives.
    """
    by_number = {task.number: task for task in tasks}
    for summary in (task for task in tasks if task.children):
        below = {each.number for each in _below(summary.children)}
        bound = [link.predecessor for link in summary.links if link.predecessor in below]
        bound += [
            number
            for number in below
            if any(link.predecessor == summary.number for link in by_number[number].links)
        ]
        if bound:
            message = (
                f"a link binds the summary {summary.label} to its subordinate "
                f"{by_number[bound[0]].label}"
            )
            raise ValueError(message)
    left = _undated(tasks)
    if left:
        names = ", ".join(task.label for task in tasks if task.number in left)
        message = f"the links close a loop through a summary among the tasks left undated: {names}"
        raise ValueError(message)


START, FINISH = 0, 1


def _undated(tasks: list[Task]) -> set[int]:
    """Return the tasks a loop through the hierarchy leaves undated: none when there is no loop.

    Each leaf is dated from its start to its finish, a summary from the start of its
    subordinates to their finish, each link from the finish of its predecessor to the start of
    its successor, whatever its kind, as ``in_link_order`` counts it.
    """
    edges: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for task in tasks:
        for child in task.children:
            edges.setdefault((task.number, START), []).append((child.number, START))
            edges.setdefault((child.number, FINISH), []).append((task.number, FINISH))
        if not task.children:
            edges.setdefault((task.number, START), []).append((task.number, FINISH))
        for link in task.links:
            edges.setdefault((link.predecessor, FINISH), []).append((task.number, START))
    waits = {(task.number, end): 0 for task in tasks for end in (START, FINISH)}
    for target in (each for targets in edges.values() for each in targets):
        waits[target] += 1
    ready = [point for point, count in waits.items() if count == 0]
    while ready:
        for target in edges.get(ready.pop(), []):
            waits[target] -= 1
            if waits[target] == 0:
                ready.append(target)
    return {number for (number, _), count in waits.items() if count}
