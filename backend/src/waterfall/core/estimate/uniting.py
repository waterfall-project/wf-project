# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The union of the trees of two revisions and the mark of each node, private to the module.

Pure: two structures read whole, the base one and the compared one, are matched by lineage
(WF-DAT-0030). The tree returned is the compared one, in the order of the plan, each node removed
from it put back at the place it had in the base structure (WF-REV-0080, C-361): under the node
that bears the lineage of its parent there — the compared one, or a node removed too —, after the
sibling of its kind that preceded it there and that the union still holds, the lines of a task
before its subtasks, as the plan orders them. The whole union is numbered — ``row_number``,
``level`` and ``position`` count the removed nodes — and each predecessor named by its number in
it; a removed node is read-only, ``editable_fields`` empty.

A node is ``added``, absent from the base structure; ``removed``, absent from the compared one;
``modified`` when one of its values changes — a task by its dates, its duration, its state or its
parent, a line by its amounts, its delay of payment, its subproject, its category or its parent
(``NodeChange``, #1751) —, or when a node under it is added, removed or modified, or moved from
under it, the content of a summary task changing (``NodeDifference``); ``unchanged`` otherwise.

The union reads of each node what it unites and marks by (``UnitedNode``), not the node: the views
of a reading of the rows, or the nodes of two readings kept, written as the API writes them, whose
identifiers stay the texts it reads — read as identifiers and written back, the some forty thousand
of a comparison of PRJ-001 would cost it thirty milliseconds (EP-26, "La comparaison", US-2270).
It gives each node of the union its place, its predecessors renamed and its mark (``PlacedNode``),
which the reader applies to what it read.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from decimal import Decimal
    from uuid import UUID

TASK = "task"
ADDED = "added"
REMOVED = "removed"
MODIFIED = "modified"
UNCHANGED = "unchanged"
PARENT = "parent"

# What a node compares, each value named by the change it makes (``NodeChange``), in its order.
type Compared = tuple[tuple[str, object], ...]


def task_compared(dates: object, duration: object, progress: object) -> Compared:
    """Name what a task compares of itself: its dates, its duration, its state."""
    return (("dates", dates), ("duration", duration), ("progress", progress))


def line_compared(
    budgeted: object, reestimated: object, delay: object, subproject: object, category: object
) -> Compared:
    """Name what a line compares of itself: its amounts, its delay, its subproject, its category."""
    return (
        ("budgeted_amount", budgeted),
        ("reestimated_amount", reestimated),
        ("payment_delay_days", delay),
        ("subproject", subproject),
        ("cost_category", category),
    )


class LineAmounts(NamedTuple):
    """What a line counts in the differences of amounts: its keys, its two amounts."""

    cost_category_id: UUID
    subproject_id: UUID | None
    budgeted: Decimal
    reestimated: Decimal


class UnitedNode[K](NamedTuple):
    """A node as the union reads it: its identifiers, its place, its predecessors, its values.

    ``K`` the identifiers as its reader has them; ``compared`` what its changes compare, the same
    values for the same node whichever side reads it (``task_compared``, ``line_compared``), empty
    for a node of neither kind; ``line`` what a line counts in the differences of amounts. A tuple,
    as the records of a reading (``TaskRecord``): some twelve thousand are made by comparison.
    """

    node_id: K
    lineage_id: K
    kind: str
    parent_id: K | None
    predecessors: tuple[K, ...]
    compared: Compared
    line: LineAmounts | None


class PlacedNode[K](NamedTuple):
    """A node of the union as it is returned: its place in the union, its predecessors, its mark.

    ``predecessors`` each predecessor of the node, in its order, renamed to its node in the union
    and its number there, or none when it is kept as read; empty for a node without one.
    """

    node_id: K
    parent_id: K | None
    row_number: int
    level: int
    position: int
    predecessors: tuple[tuple[K, int] | None, ...]
    removed: bool
    difference: str
    changes: tuple[str, ...]


@dataclass(slots=True)
class Union[K]:
    """The tree of a comparison: its nodes by identifier, in order, each with its mark.

    ``nodes`` each node as it is read, the removed ones from the base structure; ``numbers`` its
    number, its level and its place in the union; ``base`` the node of the same lineage in the base
    structure, the removed node itself for a removed one; ``removed`` the removed nodes, by their
    identifier in the base structure; ``renamed`` the predecessors of each node that has some.
    """

    nodes: dict[K, UnitedNode[K]] = field(default_factory=dict[K, UnitedNode[K]])
    order: list[K] = field(default_factory=list[K])
    parent: dict[K, K | None] = field(default_factory=dict[K, K | None])
    children: dict[K | None, list[K]] = field(default_factory=dict[K | None, list[K]])
    numbers: dict[K, tuple[int, int, int]] = field(default_factory=dict[K, tuple[int, int, int]])
    base: dict[K, UnitedNode[K]] = field(default_factory=dict[K, UnitedNode[K]])
    removed: frozenset[K] = frozenset()
    difference: dict[K, str] = field(default_factory=dict[K, str])
    changes: dict[K, tuple[str, ...]] = field(default_factory=dict[K, tuple[str, ...]])
    renamed: dict[K, tuple[tuple[K, int] | None, ...]] = field(
        default_factory=dict[K, tuple[tuple[K, int] | None, ...]]
    )

    def ancestors(self, node_id: K) -> Iterator[K]:
        """Give the ancestors of a node of the union, its parent first."""
        parent = self.parent.get(node_id)
        while parent is not None:
            yield parent
            parent = self.parent.get(parent)

    def subtree(self, node_id: K) -> Iterator[K]:
        """Give a node of the union and every node under it, in the order of the plan."""
        if node_id not in self.nodes:
            return
        pending = [node_id]
        while pending:
            current = pending.pop()
            yield current
            pending.extend(reversed(self.children.get(current, [])))

    def placed(self, node_id: K) -> PlacedNode[K]:
        """Give a node of the union as it is returned, placed, renamed and marked."""
        row, level, position = self.numbers[node_id]
        return PlacedNode(
            node_id,
            self.parent[node_id],
            row,
            level,
            position,
            self.renamed.get(node_id, ()),
            node_id in self.removed,
            self.difference[node_id],
            self.changes[node_id],
        )


class _Matching[K]:
    """The two structures matched by lineage, each node by its identifier."""

    def __init__(self, base: Sequence[UnitedNode[K]], compared: Sequence[UnitedNode[K]]) -> None:
        self.base = {each.node_id: each for each in base}
        self.compared = {each.node_id: each for each in compared}
        self.base_of = {each.lineage_id: each for each in base}
        self.compared_of = {each.lineage_id: each for each in compared}

    def united(self, base_id: K) -> K:
        """Give the node of the union a node of the base structure is: the compared one, or it."""
        node = self.compared_of.get(self.base[base_id].lineage_id)
        return base_id if node is None else node.node_id

    def united_parent(self, parent_id: K | None) -> K | None:
        """Give the parent in the union of a node whose parent is named in the base structure."""
        return None if parent_id is None else self.united(parent_id)

    def parent_lineage(self, node: UnitedNode[K], nodes: dict[K, UnitedNode[K]]) -> K | None:
        """Give the lineage of the parent of a node, none at the first level."""
        return None if node.parent_id is None else nodes[node.parent_id].lineage_id

    def changes(self, base: UnitedNode[K], compared: UnitedNode[K]) -> tuple[str, ...]:
        """Name what changes of a node present on both sides, in the order of ``NodeChange``.

        Its own values, a task's or a line's, when both sides read them; then its parent.
        """
        found = (
            [
                name
                for (name, old), (_, new) in zip(base.compared, compared.compared, strict=True)
                if old != new
            ]
            if base.kind == compared.kind and len(base.compared) == len(compared.compared)
            else []
        )
        if self.parent_lineage(base, self.base) != self.parent_lineage(compared, self.compared):
            found.append(PARENT)
        return tuple(found)


def _grouped[K](
    nodes: Sequence[UnitedNode[K]], parent_of: dict[K, K | None]
) -> dict[tuple[K | None, bool], list[K]]:
    """Give the children of each parent, the lines and the tasks apart, in the order given."""
    groups: dict[tuple[K | None, bool], list[K]] = {}
    for each in nodes:
        groups.setdefault((parent_of[each.node_id], each.kind == TASK), []).append(each.node_id)
    return groups


def _place_removed[K](
    matching: _Matching[K],
    base: Sequence[UnitedNode[K]],
    union: Union[K],
    removed: list[UnitedNode[K]],
) -> dict[tuple[K | None, bool], list[K]]:
    """Give the children of each parent of the union, each removed node at the place it had."""
    groups = _grouped(list(matching.compared.values()), union.parent)
    before = _grouped(base, {each.node_id: each.parent_id for each in base})
    for node in removed:
        is_task = node.kind == TASK
        siblings = groups.setdefault((union.parent[node.node_id], is_task), [])
        earlier = before[(node.parent_id, is_task)]
        rank = 0
        for sibling in reversed(earlier[: earlier.index(node.node_id)]):
            united = matching.united(sibling)
            if united in siblings:
                rank = siblings.index(united) + 1
                break
        siblings.insert(rank, node.node_id)
    return groups


def _numbered[K](union: Union[K], groups: dict[tuple[K | None, bool], list[K]]) -> None:
    """Order the union depth first, the lines of each parent before its tasks; number it."""
    for parent in {parent for parent, _ in groups}:
        lines, tasks = groups.get((parent, False), []), groups.get((parent, True), [])
        union.children[parent] = [*lines, *tasks]
    pending = [(each, 1, place) for place, each in enumerate(union.children.get(None, []), 1)]
    pending.reverse()
    while pending:
        node_id, level, position = pending.pop()
        union.order.append(node_id)
        union.numbers[node_id] = (len(union.order), level, position)
        below = union.children.get(node_id, [])
        pending.extend(
            (child, level + 1, place) for place, child in reversed(list(enumerate(below, 1)))
        )


def _renamed_predecessors[K](union: Union[K], matching: _Matching[K]) -> None:
    """Name each predecessor by its node in the union and its number there."""
    for node_id, node in union.nodes.items():
        if not node.predecessors:
            continue
        removed = node_id in union.removed
        named: list[tuple[K, int] | None] = []
        for each in node.predecessors:
            target = matching.united(each) if removed else each
            numbers = union.numbers.get(target)
            named.append(None if numbers is None else (target, numbers[0]))
        union.renamed[node_id] = tuple(named)


def _mark[K](union: Union[K], matching: _Matching[K], removed: list[UnitedNode[K]]) -> None:
    """Mark each node, then the tasks whose content changes: modified, their changes unchanged."""
    for node_id, node in matching.compared.items():
        base = matching.base_of.get(node.lineage_id)
        if base is None:
            union.difference[node_id], union.changes[node_id] = ADDED, ()
            continue
        union.base[node_id] = base
        changes = matching.changes(base, node)
        union.changes[node_id] = changes
        union.difference[node_id] = MODIFIED if changes else UNCHANGED
    for node in removed:
        union.base[node.node_id] = node
        union.difference[node.node_id], union.changes[node.node_id] = REMOVED, ()
    holding: set[K] = set()
    for node_id, difference in union.difference.items():
        if difference == UNCHANGED:
            continue
        holding.update(union.ancestors(node_id))
        if PARENT in union.changes[node_id]:
            # The task it moved from: its content changes too, and that of its ancestors.
            former = matching.united_parent(union.base[node_id].parent_id)
            if former is not None:
                holding.add(former)
                holding.update(union.ancestors(former))
    for node_id in holding:
        if union.difference[node_id] == UNCHANGED:
            union.difference[node_id] = MODIFIED


def unite[K](base: Sequence[UnitedNode[K]], compared: Sequence[UnitedNode[K]]) -> Union[K]:
    """Unite two structures read whole, each in the order of its plan, and mark each node."""
    matching = _Matching(base, compared)
    removed = [each for each in base if each.lineage_id not in matching.compared_of]
    union = Union[K](removed=frozenset(each.node_id for each in removed))
    union.nodes = {each.node_id: each for each in compared}
    union.parent = {each.node_id: each.parent_id for each in compared}
    for node in removed:
        union.nodes[node.node_id] = node
        union.parent[node.node_id] = matching.united_parent(node.parent_id)
    _numbered(union, _place_removed(matching, base, union, removed))
    _renamed_predecessors(union, matching)
    _mark(union, matching, removed)
    return union
