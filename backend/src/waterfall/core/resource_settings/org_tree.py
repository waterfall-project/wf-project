# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tree of the organisation as a pure calculation (WF-REF-0070): levels, order, ancestors.

The depth of a node is never stored: it is resolved here from the parents, at each reading. The
functions take values and give values, with no database: the module reads the rows, these arrange
them. A text compares in the order of the code points, as Python compares a ``str`` and as the
contract orders the labels (``listOrgNodes``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class Branch:
    """What the tree knows of a node: where it hangs, and the label its siblings are ordered by."""

    node_id: UUID
    parent_id: UUID | None
    label: str


def levels_of(branches: Iterable[Branch]) -> dict[UUID, int]:
    """Resolve the depth of every node: 1 for a root, its parent's plus one for the others.

    A node whose parent is not among those given is a root, so is one on a loop, which a tree
    never holds (the service refuses it, under its lock).
    """
    parents = {branch.node_id: branch.parent_id for branch in branches}
    resolved: dict[UUID, int] = {}
    for start in parents:
        path: list[UUID] = []
        node: UUID | None = start
        while node is not None and node in parents and node not in resolved and node not in path:
            path.append(node)
            node = parents[node]
        base = resolved.get(node, 0) if node is not None else 0
        for position, each in enumerate(reversed(path), start=1):
            resolved[each] = base + position
    return resolved


def in_tree_order(branches: Iterable[Branch]) -> list[Branch]:
    """Order the nodes depth first: each followed by its descendants (WF-REF-0070).

    The children of a parent, and the roots among themselves, by label in the order of the code
    points, then by identifier so that two nodes of one label keep a fixed order.
    """
    every = list(branches)
    known = {branch.node_id for branch in every}
    children: dict[UUID | None, list[Branch]] = {}
    for branch in every:
        key = branch.parent_id if branch.parent_id in known else None
        children.setdefault(key, []).append(branch)
    for siblings in children.values():
        siblings.sort(key=lambda each: (each.label, each.node_id))
    ordered: list[Branch] = []
    pending = list(reversed(children.get(None, [])))
    while pending:
        branch = pending.pop()
        ordered.append(branch)
        pending.extend(reversed(children.get(branch.node_id, [])))
    return ordered


def with_ancestors(branches: Iterable[Branch], kept: Collection[UUID]) -> set[UUID]:
    """Give the nodes ``kept`` and all their ancestors, for a tree read without a hole."""
    parents = {branch.node_id: branch.parent_id for branch in branches}
    retained: set[UUID] = set()
    for start in kept:
        node: UUID | None = start
        while node is not None and node in parents and node not in retained:
            retained.add(node)
            node = parents[node]
    return retained


def is_within(parents: Mapping[UUID, UUID | None], node_id: UUID, ancestor: UUID) -> bool:
    """Tell whether a node is the ``ancestor`` itself or one of its descendants."""
    seen: set[UUID] = set()
    node: UUID | None = node_id
    while node is not None and node not in seen:
        if node == ancestor:
            return True
        seen.add(node)
        node = parents.get(node)
    return False
