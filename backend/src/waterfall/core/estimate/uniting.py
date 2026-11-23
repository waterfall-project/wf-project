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
``modified`` when one of its values differs, entered or computed, of either facet, whatever a
reading returns of it (EP-27, « Ce qui fait un nœud modifié ») — save the total float and the
membership of the critical path of a task, which the planning engine computes (WF-REV-0080, #4312)
—, or when a node under it is added,
removed or modified, or moved from under it, the content of a summary task changing
(``NodeDifference``); ``unchanged`` otherwise. What differs is named by the change it makes
(``NodeChange``, #1751): a task by its dates, its duration, its state or its parent, a line by its
amounts, its delay of payment, its subproject, its category or its parent, and any other value by
``other``. A modified node gives the values its base carried of what differs (``base``), a node
they name — its parent, a predecessor, the bearing task of a line — named by its node in the union,
and the difference of each date, duration and amount among them (``deltas``, ``subtracting``, at
the constants of the units of the installation); one modified by its content alone gives none.
What is not compared, because it changes from one revision to the other without anything of the
node changing, is listed once, here (``NOT_COMPARED``, ``FACET_NOT_COMPARED``), and the contract
says it (``ComparedNodeBase``).

The union reads of each node what it unites and marks by (``UnitedNode``), not the node: its
identifiers and its place, as the views of a reading of the rows or the nodes of a document give
them, and the node written whole as the API writes it, whose values it compares. The identifiers of
a document stay the texts it reads — read as identifiers and written back, the some forty thousand
of a comparison of PRJ-001 would cost it thirty milliseconds (EP-26, "La comparaison", US-2270). It
gives each node of the union its place, its predecessors renamed, its mark and its base
(``PlacedNode``), which the reader applies to what it read.
"""

from dataclasses import dataclass, field
from functools import cached_property
from typing import TYPE_CHECKING, Any, NamedTuple

from waterfall.core.estimate.subtracting import deltas_of

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence
    from decimal import Decimal
    from uuid import UUID

    from waterfall.core.planning.interface import UnitConstants

TASK = "task"
LINE = "estimate_line"
ADDED = "added"
REMOVED = "removed"
MODIFIED = "modified"
UNCHANGED = "unchanged"
PARENT = "parent"
OTHER = "other"
PARENT_ID = "parent_id"
PREDECESSORS = "predecessors"
FACETS = frozenset({TASK, LINE})

# What a comparison does not compare of a node, because it changes from one revision to the other
# without anything of the node changing (EP-27, « Ce qui fait un nœud modifié »; the contract,
# ``ComparedNodeBase``): its identifiers, its counter, its row, its rank and its level — the
# level follows the rank —, and the lists of what the server computes or accepts of it. The parent
# and the predecessors are compared, by the lineage of the nodes they name (``PARENT_ID``,
# ``PREDECESSORS``).
NOT_COMPARED = frozenset(
    {
        "node_id",
        "lineage_id",
        "kind",
        "lock_version",
        "row_number",
        "position",
        "level",
        "computed_fields",
        "editable_fields",
    }
)
# What a facet carries that is no value of the node: the overdue finish of a task, a flag of the day
# it is computed on, and whether a line accepts a re-estimate, what is enterable. The total float
# and the membership of the critical path of a task are not either: the planning engine computes
# them from the whole structure, and they change when another task does, the task itself unchanged
# — WF-REV-0080 modifies a task by « ses dates, sa durée, son état et son parent » (#4312).
FACET_NOT_COMPARED = {
    TASK: frozenset({"finish_overdue", "total_float", "is_critical"}),
    LINE: frozenset({"remaining_entry"}),
}
# The identifiers of a facet that name a node, compared by the lineage of that node, as the parent
# and a predecessor are: the same node bears another identifier in each revision. ``origin_risk_id``
# is compared as it is: a risk keeps its identifier in every revision (WF-RIS-0020).
BY_LINEAGE = frozenset({"estimate_line.bearing_task_node_id"})
# The labels resolved on reading, each compared with the identifier it follows, never alone: the
# object it names renamed changes nothing of the node; it goes with its identifier when it differs.
FOLLOWING = {
    "estimate_line.subproject_label": "estimate_line.subproject_id",
    "estimate_line.cost_category_label": "estimate_line.cost_category_id",
    "estimate_line.resource_role_label": "estimate_line.resource_role_id",
    "estimate_line.bearing_task_label": "estimate_line.bearing_task_node_id",
}
# The values each change of ``NodeChange`` names, by kind, in the order of the enum; any other value
# that differs is ``other``. A node of another kind changes by its parent alone.
_BY_PARENT = ((PARENT, (PARENT_ID,)),)
NAMED: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    TASK: (
        ("dates", ("task.start", "task.finish")),
        ("duration", ("task.duration",)),
        ("progress", ("task.progress",)),
        *_BY_PARENT,
    ),
    LINE: (
        ("budgeted_amount", ("estimate_line.budgeted_amount",)),
        ("reestimated_amount", ("estimate_line.reestimated_amount",)),
        ("payment_delay_days", ("estimate_line.payment_delay_days",)),
        ("subproject", ("estimate_line.subproject_id", "estimate_line.subproject_label")),
        ("cost_category", ("estimate_line.cost_category_id", "estimate_line.cost_category_label")),
        *_BY_PARENT,
    ),
}


def changes_of(kind: str, differing: Sequence[str]) -> tuple[str, ...]:
    """Name what changes of a node by the values that differ, in the order of ``NodeChange``."""
    named = NAMED.get(kind, _BY_PARENT)
    found = [change for change, names in named if any(name in differing for name in names)]
    covered = {name for _, names in named for name in names}
    if any(name not in covered for name in differing):
        found.append(OTHER)
    return tuple(found)


class LineAmounts(NamedTuple):
    """What a line counts in the differences of amounts and in the totals: its keys, its figures.

    ``hours`` none counted as nought, as the totals of a reading count them (``NodeTotals``).
    """

    cost_category_id: UUID
    subproject_id: UUID | None
    budgeted: Decimal
    reestimated: Decimal
    hours: Decimal
    base: Decimal


class UnitedNode[K](NamedTuple):
    """A node as the union reads it: its identifiers, its place, its predecessors, its values.

    ``K`` the identifiers as its reader has them; ``values`` the node written whole, as the API
    writes it (``Node``) — its properties, its facets as mappings, the nodes it names by their
    identifiers written as texts —, what the union compares of it; ``line`` what a line counts in
    the differences of amounts. A tuple, as the records of a reading (``TaskRecord``): some twelve
    thousand are made by comparison.
    """

    node_id: K
    lineage_id: K
    kind: str
    parent_id: K | None
    predecessors: tuple[K, ...]
    values: Mapping[str, Any]
    line: LineAmounts | None


class PlacedNode[K](NamedTuple):
    """A node of the union as it is returned: its place, its predecessors, its mark, its base.

    ``predecessors`` each predecessor of the node, in its order, renamed to its node in the union
    and its number there, or none when it is kept as read; empty for a node without one. ``base``
    what the base carried of the values that differ, by their name in the node (``parent_id``,
    ``predecessors``, ``task.finish``), written as the node writes them, a node they name by its
    node in the union and its number there: of a node modified present on both sides, empty when
    it is modified by its content alone; none for any other. ``deltas`` the difference of each date,
    duration and amount of ``base``, the revision read less the base, written likewise; empty or
    none as ``base`` is.
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
    base: dict[str, Any] | None
    deltas: dict[str, Any] | None


@dataclass(slots=True)
class Union[K]:
    """The tree of a comparison: its nodes by identifier, in order, each with its mark.

    ``nodes`` each node as it is read, the removed ones from the base structure; ``numbers`` its
    number, its level and its place in the union; ``base`` the node of the same lineage in the base
    structure, the removed node itself for a removed one; ``removed`` the removed nodes, by their
    identifier in the base structure; ``renamed`` the predecessors of each node that has some;
    ``base_values`` what the base carried of what differs of each modified node of both sides, and
    ``deltas`` the differences among them.
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
    base_values: dict[K, dict[str, Any]] = field(default_factory=dict[K, dict[str, Any]])
    deltas: dict[K, dict[str, Any]] = field(default_factory=dict[K, dict[str, Any]])

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
        """Give a node of the union as it is returned, placed, renamed, marked, with its base."""
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
            self.base_values.get(node_id),
            self.deltas.get(node_id),
        )


class _Matching[K]:
    """The two structures matched by lineage, each node by its identifier."""

    def __init__(self, base: Sequence[UnitedNode[K]], compared: Sequence[UnitedNode[K]]) -> None:
        self.base = {each.node_id: each for each in base}
        self.compared = {each.node_id: each for each in compared}
        self.base_of = {each.lineage_id: each for each in base}
        self.compared_of = {each.lineage_id: each for each in compared}

    @cached_property
    def base_texts(self) -> dict[str, UnitedNode[K]]:
        """Give the nodes of the base structure by their identifier written as a text."""
        return {str(key): each for key, each in self.base.items()}

    @cached_property
    def compared_texts(self) -> dict[str, UnitedNode[K]]:
        """Give the nodes of the compared structure by their identifier written as a text."""
        return {str(key): each for key, each in self.compared.items()}

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

    def links(self, node: UnitedNode[K], nodes: dict[K, UnitedNode[K]]) -> list[tuple[Any, ...]]:
        """Give the predecessors of a node by the lineage they name, their type and their lag.

        Never by their row, which the nodes around them move.
        """
        written = node.values.get(PREDECESSORS) or ()
        return [
            (nodes[each].lineage_id, link["link_type"], link["lag"])
            for each, link in zip(node.predecessors, written, strict=True)
        ]

    def differing(self, base: UnitedNode[K], compared: UnitedNode[K]) -> list[str]:
        """Name the values of a node present on both sides that differ, in the order of the node.

        Its facet's as ``task.label``; a label that follows an identifier only with it.
        """
        now, then = compared.values, base.values
        found: list[str] = []
        for key in (*now, *(each for each in then if each not in now)):
            if key in NOT_COMPARED:
                continue
            if key in FACETS:
                found += self._facet(key, then.get(key), now.get(key))
                continue
            if key == PARENT_ID:
                differs = self.parent_lineage(base, self.base) != self.parent_lineage(
                    compared, self.compared
                )
            elif key == PREDECESSORS:
                differs = self.links(base, self.base) != self.links(compared, self.compared)
            else:
                differs = now.get(key) != then.get(key)
            if differs:
                found.append(key)
        return [name for name in found if name not in FOLLOWING or FOLLOWING[name] in found]

    def _facet(
        self, facet: str, was: Mapping[str, Any] | None, now: Mapping[str, Any] | None
    ) -> list[str]:
        """Name the values of a facet that differ, as ``task.label``; none when it is the same."""
        if was == now:
            return []
        excluded = FACET_NOT_COMPARED[facet]
        old: Mapping[str, Any] = was or {}
        new: Mapping[str, Any] = now or {}
        found: list[str] = []
        for key in (*new, *(each for each in old if each not in new)):
            if key in excluded:
                continue
            name = f"{facet}.{key}"
            if name in BY_LINEAGE:
                differs = self._lineage(new.get(key), self.compared_texts) != self._lineage(
                    old.get(key), self.base_texts
                )
            else:
                differs = new.get(key) != old.get(key)
            if differs:
                found.append(name)
        return found

    @staticmethod
    def _lineage(text: object, nodes: dict[str, UnitedNode[K]]) -> object:
        """Give the lineage of the node an identifier written in a value names, or the value."""
        node = None if text is None else nodes.get(str(text))
        return text if node is None else node.lineage_id

    def base_values(
        self, base: UnitedNode[K], names: Sequence[str], numbers: dict[K, tuple[int, int, int]]
    ) -> dict[str, Any]:
        """Give what the base carried of the values named, a node named by its node in the union.

        A predecessor at its number in the union (``numbers``), as those of the node returned.
        """
        then = base.values
        found: dict[str, Any] = {}
        for name in names:
            facet, _, key = name.partition(".")
            if name == PARENT_ID:
                parent = self.united_parent(base.parent_id)
                found[name] = None if parent is None else str(parent)
            elif name == PREDECESSORS:
                found[name] = [
                    {
                        **link,
                        "predecessor_node_id": str(united := self.united(each)),
                        "predecessor_row_number": numbers[united][0],
                    }
                    for each, link in zip(base.predecessors, then[PREDECESSORS], strict=True)
                ]
            elif key:
                held: Mapping[str, Any] = then.get(facet) or {}
                value = held.get(key)
                node = self.base_texts.get(str(value)) if name in BY_LINEAGE else None
                found[name] = value if node is None else str(self.united(node.node_id))
            else:
                found[name] = then.get(name)
        return found


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


def _mark[K](
    union: Union[K],
    matching: _Matching[K],
    removed: list[UnitedNode[K]],
    constants: UnitConstants,
) -> None:
    """Mark each node, then the tasks whose content changes: modified, their changes unchanged.

    Each node modified present on both sides is given what its base carried of what differs, and
    the differences among them.
    """
    differing: dict[K, list[str]] = {}
    for node_id, node in matching.compared.items():
        base = matching.base_of.get(node.lineage_id)
        if base is None:
            union.difference[node_id], union.changes[node_id] = ADDED, ()
            continue
        union.base[node_id] = base
        differing[node_id] = matching.differing(base, node)
        changes = changes_of(node.kind, differing[node_id])
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
    for node_id, names in differing.items():
        if union.difference[node_id] == MODIFIED:
            base = union.base[node_id]
            union.base_values[node_id] = matching.base_values(base, names, union.numbers)
            union.deltas[node_id] = deltas_of(
                names, base.values, union.nodes[node_id].values, constants
            )


def unite[K](
    base: Sequence[UnitedNode[K]], compared: Sequence[UnitedNode[K]], constants: UnitConstants
) -> Union[K]:
    """Unite two structures read whole, each in the order of its plan, and mark each node.

    ``constants`` those of the units of the installation, which the difference of two durations
    of different units is counted by.
    """
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
    _mark(union, matching, removed, constants)
    return union
