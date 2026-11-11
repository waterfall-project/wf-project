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
"""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.estimate.reading import LineView
from waterfall.core.planning.interface import NodeView

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from waterfall.core.planning.interface import PredecessorView

TASK = "task"
ADDED = "added"
REMOVED = "removed"
MODIFIED = "modified"
UNCHANGED = "unchanged"
PARENT = "parent"


@dataclass(slots=True)
class Union:
    """The tree of a comparison: its nodes by identifier, in order, each with its mark.

    ``views`` each node as it is returned, renumbered in the union; ``base`` the node of the same
    lineage in the base structure, the removed node itself for a removed one; ``removed`` the
    removed nodes, by their identifier in the base structure.
    """

    views: dict[UUID, NodeView] = field(default_factory=dict[UUID, NodeView])
    order: list[UUID] = field(default_factory=list[UUID])
    parent: dict[UUID, UUID | None] = field(default_factory=dict[UUID, UUID | None])
    children: dict[UUID | None, list[UUID]] = field(default_factory=dict[UUID | None, list[UUID]])
    base: dict[UUID, NodeView] = field(default_factory=dict[UUID, NodeView])
    removed: frozenset[UUID] = frozenset()
    difference: dict[UUID, str] = field(default_factory=dict[UUID, str])
    changes: dict[UUID, tuple[str, ...]] = field(default_factory=dict[UUID, tuple[str, ...]])

    def ancestors(self, node_id: UUID) -> Iterator[UUID]:
        """Give the ancestors of a node of the union, its parent first."""
        parent = self.parent.get(node_id)
        while parent is not None:
            yield parent
            parent = self.parent.get(parent)

    def subtree(self, node_id: UUID) -> Iterator[UUID]:
        """Give a node of the union and every node under it, in the order of the plan."""
        if node_id not in self.views:
            return
        pending = [node_id]
        while pending:
            current = pending.pop()
            yield current
            pending.extend(reversed(self.children.get(current, [])))


def _task_changes(base: NodeView, compared: NodeView) -> list[str]:
    """Name what changes of a task itself: its dates, its duration, its state."""
    before, after = base.task, compared.task
    if before is None or after is None:
        return []
    found: list[str] = []
    if (before.start, before.finish) != (after.start, after.finish):
        found.append("dates")
    if (before.duration_value, before.duration_unit) != (after.duration_value, after.duration_unit):
        found.append("duration")
    if before.progress != after.progress:
        found.append("progress")
    return found


def _line_changes(base: NodeView, compared: NodeView) -> list[str]:
    """Name what changes of a line itself: its amounts, its delay, its subproject, its category."""
    before = None if base.facet is None else base.facet.view
    after = None if compared.facet is None else compared.facet.view
    if not isinstance(before, LineView) or not isinstance(after, LineView):
        return []
    pairs = (
        ("budgeted_amount", before.budgeted_amount, after.budgeted_amount),
        ("reestimated_amount", before.reestimated_amount, after.reestimated_amount),
        ("payment_delay_days", before.payment_delay_days, after.payment_delay_days),
        ("subproject", before.subproject_id, after.subproject_id),
        ("cost_category", before.cost_category_id, after.cost_category_id),
    )
    return [name for name, old, new in pairs if old != new]


class _Matching:
    """The two structures matched by lineage, each node by its identifier."""

    def __init__(self, base: Sequence[NodeView], compared: Sequence[NodeView]) -> None:
        self.base = {each.node_id: each for each in base}
        self.compared = {each.node_id: each for each in compared}
        self.base_of = {each.lineage_id: each for each in base}
        self.compared_of = {each.lineage_id: each for each in compared}

    def united(self, base_id: UUID) -> UUID:
        """Give the node of the union a node of the base structure is: the compared one, or it."""
        node = self.compared_of.get(self.base[base_id].lineage_id)
        return base_id if node is None else node.node_id

    def united_parent(self, parent_id: UUID | None) -> UUID | None:
        """Give the parent in the union of a node whose parent is named in the base structure."""
        return None if parent_id is None else self.united(parent_id)

    def parent_lineage(self, view: NodeView, nodes: dict[UUID, NodeView]) -> UUID | None:
        """Give the lineage of the parent of a node, none at the first level."""
        return None if view.parent_id is None else nodes[view.parent_id].lineage_id

    def changes(self, base: NodeView, compared: NodeView) -> tuple[str, ...]:
        """Name what changes of a node present on both sides, in the order of ``NodeChange``."""
        found = (
            _task_changes(base, compared)
            if compared.kind == TASK
            else _line_changes(base, compared)
        )
        if self.parent_lineage(base, self.base) != self.parent_lineage(compared, self.compared):
            found.append(PARENT)
        return tuple(found)


def _grouped(
    views: Sequence[NodeView], parent_of: dict[UUID, UUID | None]
) -> dict[tuple[UUID | None, bool], list[UUID]]:
    """Give the children of each parent, the lines and the tasks apart, in the order given."""
    groups: dict[tuple[UUID | None, bool], list[UUID]] = {}
    for each in views:
        groups.setdefault((parent_of[each.node_id], each.kind == TASK), []).append(each.node_id)
    return groups


def _place_removed(
    matching: _Matching, base: Sequence[NodeView], union: Union, removed: list[NodeView]
) -> dict[tuple[UUID | None, bool], list[UUID]]:
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


def _numbered(union: Union, groups: dict[tuple[UUID | None, bool], list[UUID]]) -> None:
    """Order the union depth first, the lines of each parent before its tasks; number it."""
    for parent in {parent for parent, _ in groups}:
        lines, tasks = groups.get((parent, False), []), groups.get((parent, True), [])
        union.children[parent] = [*lines, *tasks]
    rows: dict[UUID, tuple[int, int, int]] = {}
    pending = [(each, 1, place) for place, each in enumerate(union.children.get(None, []), 1)]
    pending.reverse()
    while pending:
        node_id, level, position = pending.pop()
        union.order.append(node_id)
        rows[node_id] = (len(union.order), level, position)
        below = union.children.get(node_id, [])
        pending.extend(
            (child, level + 1, place) for place, child in reversed(list(enumerate(below, 1)))
        )
    for node_id, view in list(union.views.items()):
        row, level, position = rows[node_id]
        union.views[node_id] = replace(
            view,
            parent_id=union.parent[node_id],
            row_number=row,
            level=level,
            position=position,
        )


def _renamed_predecessors(union: Union, matching: _Matching) -> None:
    """Name each predecessor by its node in the union and its number there."""
    for node_id, view in list(union.views.items()):
        if not view.predecessors:
            continue
        removed = node_id in union.removed
        named: list[PredecessorView] = []
        for each in view.predecessors:
            target = matching.united(each.predecessor_id) if removed else each.predecessor_id
            if target not in union.views:
                named.append(each)
                continue
            row = union.views[target].row_number
            named.append(replace(each, predecessor_id=target, row_number=row))
        union.views[node_id] = replace(view, predecessors=tuple(named))


def _mark(union: Union, matching: _Matching, removed: list[NodeView]) -> None:
    """Mark each node, then the tasks whose content changes: modified, their changes unchanged."""
    for node_id, view in matching.compared.items():
        base = matching.base_of.get(view.lineage_id)
        if base is None:
            union.difference[node_id], union.changes[node_id] = ADDED, ()
            continue
        union.base[node_id] = base
        changes = matching.changes(base, view)
        union.changes[node_id] = changes
        union.difference[node_id] = MODIFIED if changes else UNCHANGED
    for node in removed:
        union.base[node.node_id] = node
        union.difference[node.node_id], union.changes[node.node_id] = REMOVED, ()
    holding: set[UUID] = set()
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


def unite(base: Sequence[NodeView], compared: Sequence[NodeView]) -> Union:
    """Unite two structures read whole, each in the order of its plan, and mark each node."""
    matching = _Matching(base, compared)
    removed = [each for each in base if each.lineage_id not in matching.compared_of]
    union = Union(removed=frozenset(each.node_id for each in removed))
    union.views = {each.node_id: each for each in compared}
    union.parent = {each.node_id: each.parent_id for each in compared}
    for node in removed:
        union.views[node.node_id] = replace(node, editable_fields=())
        union.parent[node.node_id] = matching.united_parent(node.parent_id)
    _numbered(union, _place_removed(matching, base, union, removed))
    _renamed_predecessors(union, matching)
    _mark(union, matching, removed)
    return union
