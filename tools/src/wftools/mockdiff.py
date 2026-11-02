# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of a structure read against another, each node marked by its difference (C-361).

A differential is read against the main structure of its revision, a marked revision against the
revision it is compared with: the same tree, the structure read, its nodes matched by lineage, each
with its difference — added, removed, modified or unchanged — and what changed of it itself
(`Node.difference`, `Node.changes`, WF-REV-0080). The nodes the structure read no longer bears are
rendered at the place they had, between the nodes that surrounded them, read only; a node moved is
rendered once, at its new place, changed by its parent. A task under which a node is added,
removed or modified, or from under which one is moved, is modified: the mark of a summary says that
its content changes. A node
removed holds its row: the rows and the ranks count the tree rendered, the nodes removed with
them, and a predecessor is named by the row it is rendered at.

A task is changed by its dates, its duration, its progress or its parent; a line by its amounts,
its delay of payment (#1566), its subproject, its cost category (#1751) or its parent: the amount
of a task is its lines', said by them (``wftools.mockhistory``, #287).

A marked tree is read by a window (``window``, ``subtree_of``), or by its differences alone
(``differences``, the filter ``difference``, #1398).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from wftools import mockcore

if TYPE_CHECKING:
    from collections.abc import Collection

    from wftools.mockstructure import JsonObject, JsonValue

ADDED, REMOVED, MODIFIED, UNCHANGED = "added", "removed", "modified", "unchanged"

ALWAYS = (*mockcore.ALWAYS, "difference", "changes")
"""What a marked tree renders of each node whatever `fields` names: its mark with the four."""

_TASK_CHANGES = (
    ("dates", ("start", "finish")),
    ("duration", ("duration",)),
    ("progress", ("progress",)),
)
_LINE_CHANGES = (
    ("budgeted_amount", ("budgeted_amount",)),
    ("reestimated_amount", ("reestimated_amount",)),
    ("payment_delay_days", ("payment_delay_days",)),
    ("subproject", ("subproject_id",)),
    ("cost_category", ("cost_category_id",)),
)


def changes(row: mockcore.Row, was: mockcore.Row) -> list[JsonValue]:
    """Return what changed of a node from one structure to the other, in the order of the enum."""
    facet = cast("dict[str, JsonValue]", row.node[row.kind])
    old = cast("dict[str, JsonValue]", was.node[was.kind])
    kinds = _TASK_CHANGES if row.kind == mockcore.TASK else _LINE_CHANGES
    found: list[JsonValue] = [
        name for name, keys in kinds if any(facet.get(key) != old.get(key) for key in keys)
    ]
    if row.parent != was.parent:
        found.append("parent")
    return found


def _placed(before: list[mockcore.Row], after: list[mockcore.Row]) -> dict[int | None, list[int]]:
    """Return the children of each node of the tree rendered: those read, then those removed.

    A node removed goes after the last of the siblings it followed that the tree rendered holds
    under the same parent, or first if it held none: the parents first, in the order of the plan
    of the base, so that a node removed with its parent goes under it.
    """
    children: dict[int | None, list[int]] = {}
    for row in after:
        children.setdefault(row.parent, []).append(row.number)
    siblings: dict[int | None, list[int]] = {}
    for row in before:
        siblings.setdefault(row.parent, []).append(row.number)
    read = {row.number for row in after}
    for row in before:
        if row.number in read:
            continue
        held = children.setdefault(row.parent, [])
        earlier = siblings[row.parent][: siblings[row.parent].index(row.number)]
        held.insert(
            max((held.index(each) + 1 for each in earlier if each in held), default=0), row.number
        )
    return children


def marked(before: list[mockcore.Row], after: list[mockcore.Row]) -> list[JsonObject]:
    """Return the nodes of a structure read against its base, marked, in the order of the plan.

    Each node as the structure read renders it, or as the base did for a node removed, with its
    place in the tree rendered, its difference and its changes; a node removed is read only.
    """
    was = {row.number: row for row in before}
    now = {row.number: row for row in after}
    children = _placed(before, after)
    order: list[tuple[int, int | None, int]] = []

    def visit(number: int, parent: int | None, level: int) -> None:
        order.append((number, parent, level))
        for child in children.get(number, []):
            visit(child, number, level + 1)

    for root in children.get(None, []):
        visit(root, None, 1)
    # The tasks a node was moved away from: their content changes too.
    left = {
        was[number].parent
        for number in now.keys() & was.keys()
        if was[number].parent != now[number].parent
    }
    own: dict[int, list[JsonValue]] = {}
    marks: dict[int, str] = {}
    for number, _, _ in reversed(order):
        if number not in was:
            marks[number] = ADDED
        elif number not in now:
            marks[number] = REMOVED
        else:
            own[number] = changes(now[number], was[number])
            below = any(marks[child] != UNCHANGED for child in children.get(number, []))
            marks[number] = MODIFIED if own[number] or below or number in left else UNCHANGED
    source = {number: (now.get(number) or was[number]).node for number, _, _ in order}
    rows = {number: at for at, (number, _, _) in enumerate(order, start=1)}
    numbers = {cast("str", node["node_id"]): number for number, node in source.items()}
    nodes: list[JsonObject] = []
    for number, parent, level in order:
        node = dict(source[number])
        node["parent_id"] = None if parent is None else source[parent]["node_id"]
        node["position"] = children[parent].index(number) + 1
        node["row_number"] = rows[number]
        node["level"] = level
        if "predecessors" in node:
            node["predecessors"] = [
                {
                    **link,
                    "predecessor_row_number": rows[
                        numbers[cast("str", link["predecessor_node_id"])]
                    ],
                }
                for link in cast("list[JsonObject]", node["predecessors"])
            ]
        if marks[number] == REMOVED:
            node["editable_fields"] = []
        node["difference"] = marks[number]
        node["changes"] = own.get(number, [])
        nodes.append(node)
    return nodes


def window(nodes: list[JsonObject], root: str) -> list[JsonObject]:
    """Return the nodes of a marked tree under a task, it included, in the order of the plan.

    ``subtree_of`` on a tree marked, as ``listNodes`` reads it (#1193): the nodes removed under
    the task at the place they had, a node moved under its new parent alone, where it is rendered.
    """
    below = {root}
    for node in nodes:
        if node["parent_id"] in below:
            below.add(cast("str", node["node_id"]))
    return [node for node in nodes if node["node_id"] in below]


DIFFERENCES = (ADDED, REMOVED, MODIFIED)
"""What « Écarts seulement » asks of a marked tree: the three marks of a difference (#1398)."""


def differences(nodes: list[JsonObject], asked: Collection[str]) -> list[JsonObject]:
    """Return the nodes of a marked tree whose mark is one of those asked, with their ancestors.

    ``difference`` as ``listNodes`` and ``compareRevisions`` read it (#1398): each node, task or
    line, judged on its own mark, a task retained without its lines unchanged; its ancestors
    rendered, each modified by its content, so that the tree filtered stays a tree.
    """
    parents = {cast("str", node["node_id"]): node["parent_id"] for node in nodes}
    kept: set[str] = set()
    for node in nodes:
        if node["difference"] not in asked:
            continue
        at = cast("str | None", node["node_id"])
        while at is not None and at not in kept:
            kept.add(at)
            at = cast("str | None", parents[at])
    return [node for node in nodes if node["node_id"] in kept]


def grouped(
    nodes: list[JsonObject],
) -> tuple[list[JsonObject], list[JsonObject], list[JsonObject], list[JsonObject]]:
    """Return the nodes of a marked tree added, removed, changed by their values, by their content.

    A task modified with no change of its own is modified by its content alone.
    """
    added = [node for node in nodes if node["difference"] == ADDED]
    removed = [node for node in nodes if node["difference"] == REMOVED]
    modified = [node for node in nodes if node["difference"] == MODIFIED]
    return (
        added,
        removed,
        [node for node in modified if node["changes"]],
        [node for node in modified if not node["changes"]],
    )
