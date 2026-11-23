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

A comparison of two revisions (``compareRevisions``, EP-27) judges a node on every value it
carries, not on those alone (the total float and the membership of the critical path of a task,
which the planning engine computes, are left out, #4312): a value that differs and that none of the
changes names is ``other``,
and each node modified renders the values its base carried (``base``) and the delta of each date,
duration and amount among them (``deltas``), the revision read less the base (``compared``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from wftools import mockcore
from wftools.mockstructure import decimal, money

if TYPE_CHECKING:
    from collections.abc import Collection

    from wftools.mockstructure import JsonObject, JsonValue

ADDED, REMOVED, MODIFIED, UNCHANGED = "added", "removed", "modified", "unchanged"
OTHER = "other"

ALWAYS = (*mockcore.ALWAYS, "difference", "changes")
"""What a marked tree renders of each node whatever `fields` names: its mark with the four."""

COMPARED_ALWAYS = (*ALWAYS, "base", "deltas")
"""What a comparison renders of each node whatever `fields` names: the base and the deltas too,
each reduced to the fields read (``read_with_fields``)."""

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
        "difference",
        "changes",
        "base",
        "deltas",
    }
)
"""What changes of a node from one revision to the other without anything of it changing: its
identifiers and its counter, its row, its rank and its level — a parent is compared, by lineage —,
and what it says is enterable or computed (EP-27, « Ce qui fait un nœud modifié »)."""

FACET_NOT_COMPARED = {
    mockcore.TASK: frozenset({"finish_overdue", "total_float", "is_critical"}),
    mockcore.ESTIMATE_LINE: frozenset({"remaining_entry"}),
}
"""What a facet carries without it being a value of the node: the overdue finish, a flag of the
day it is computed on, and whether a line accepts a re-estimate, what is enterable; the total float
and the membership of the critical path of a task, which the planning engine computes from the
whole structure and which change when another task does (WF-REV-0080, #4312)."""

_NAMED = {
    mockcore.TASK: (
        ("dates", ("task.start", "task.finish")),
        ("duration", ("task.duration",)),
        ("progress", ("task.progress",)),
        ("parent", ("parent_id",)),
    ),
    mockcore.ESTIMATE_LINE: (
        ("budgeted_amount", ("estimate_line.budgeted_amount",)),
        ("reestimated_amount", ("estimate_line.reestimated_amount",)),
        ("payment_delay_days", ("estimate_line.payment_delay_days",)),
        ("subproject", ("estimate_line.subproject_id", "estimate_line.subproject_label")),
        ("cost_category", ("estimate_line.cost_category_id", "estimate_line.cost_category_label")),
        ("parent", ("parent_id",)),
    ),
}
"""The values each change of `NodeChange` names, in the order of the enum, the labels resolved
with the identifiers they name; any other that differs is ``other``."""

FOLLOWING = {
    "estimate_line.subproject_label": "estimate_line.subproject_id",
    "estimate_line.cost_category_label": "estimate_line.cost_category_id",
    "estimate_line.resource_role_label": "estimate_line.resource_role_id",
    "estimate_line.bearing_task_label": "estimate_line.bearing_task_node_id",
}
"""The labels resolved on read, each compared with the identifier it follows, never alone: the
object it names — a subproject, a cost category, a role, the bearing task — is renamed outside the
node, which changes nothing of it (EP-27, « Ce qui fait un nœud modifié »); the label goes with its
identifier in ``base`` when that identifier differs."""

BY_LINEAGE = frozenset({"estimate_line.bearing_task_node_id"})
"""The identifiers of a facet that name a node, compared by the lineage of that node, as the parent
and a predecessor: the node of the base and that of the revision read differ by their identifier,
the same by their lineage (EP-27). `origin_risk_id` is compared as it is: a risk belongs to the
project and keeps its identifier in every revision (WF-RIS-0020), so that it changes only with
the origin of the node."""

_NEVER_NULL = frozenset(
    f"{facet}.{key}"
    for facet in (mockcore.TASK, mockcore.ESTIMATE_LINE)
    for key in ("base_amount", "budgeted_amount", "reestimated_amount")
)
"""The amounts a facet always carries (`TaskFacet`, `EstimateLineFacet`): their delta is never
null, absent when they do not differ (`TaskDeltas`, `EstimateLineDeltas`)."""

_DATES = frozenset({"task.start", "task.finish", "task.started_on", "task.completed_on"})
_DURATIONS = frozenset({"task.duration"})
_AMOUNTS = _NEVER_NULL | {
    "estimate_line.unit_disbursement",
    "estimate_line.previous_unit_disbursement",
    "estimate_line.previous_reestimated_amount",
}
"""The values that bear a delta: a date, a duration, an amount (`NodeDeltas`)."""


def _values(row: mockcore.Row, ids: dict[int, str], same: dict[str, str]) -> dict[str, JsonValue]:
    """Return what a node carries that a comparison judges, by name, a facet's as `task.label`.

    The parent by the node it names, found by lineage; a predecessor by the node it names and its
    link, not by the row it is rendered at, which the nodes around it move; the bearing task of a
    line by the node it names (``BY_LINEAGE``). ``same`` renames the node of either side as the
    comparison renders it: the node read for a node of both sides, found by lineage.
    """
    values: dict[str, JsonValue] = {
        key: value
        for key, value in row.node.items()
        if key not in NOT_COMPARED and key not in FACET_NOT_COMPARED
    }
    values["parent_id"] = None if row.parent is None else ids[row.parent]
    if "predecessors" in values:
        values["predecessors"] = [
            {
                **{key: value for key, value in link.items() if key != "predecessor_row_number"},
                "predecessor_node_id": _same(link["predecessor_node_id"], same),
            }
            for link in cast("list[JsonObject]", values["predecessors"])
        ]
    facet = cast("JsonObject | None", row.node.get(row.kind)) or {}
    values.pop(row.kind, None)
    for key, value in facet.items():
        if key not in FACET_NOT_COMPARED[row.kind]:
            name = f"{row.kind}.{key}"
            values[name] = _same(value, same) if name in BY_LINEAGE else value
    return values


def _same(node_id: JsonValue, same: dict[str, str]) -> JsonValue:
    """Return a node named on either side as the comparison renders it, by its lineage."""
    return same.get(cast("str", node_id), node_id) if node_id is not None else None


def differing(
    row: mockcore.Row, was: mockcore.Row, ids: dict[int, str], same: dict[str, str]
) -> list[str]:
    """Return the names of the values of a node that differ from its base, in the node's order.

    A label that follows an identifier differs with it alone (``FOLLOWING``).
    """
    now, then = _values(row, ids, same), _values(was, ids, same)
    names = [*now, *(name for name in then if name not in now)]
    found = [name for name in names if now.get(name) != then.get(name)]
    return [name for name in found if name not in FOLLOWING or FOLLOWING[name] in found]


def named(kind: str, names: Collection[str]) -> list[JsonValue]:
    """Return what changed of a node by the values that differ: `NodeChange`, ``other`` last."""
    found: list[JsonValue] = [
        change for change, keys in _NAMED[kind] if any(key in names for key in keys)
    ]
    covered = {key for _, keys in _NAMED[kind] for key in keys}
    if any(name not in covered for name in names):
        found.append(OTHER)
    return found


def _day(value: JsonValue) -> date:
    """Return the day of a date, or of an instant of work (`WorkInstant`)."""
    text = cast("JsonObject", value)["date"] if isinstance(value, dict) else value
    return date.fromisoformat(cast("str", text))


def _delta(name: str, now: JsonValue, was: JsonValue) -> JsonValue:
    """Return the delta of a value, the revision read less the base; null if one side has none.

    Never null for an amount a facet always carries (``_NEVER_NULL``), which the contract does not
    let be null.

    A date in calendar days; a duration in the unit of the duration read, which the witness never
    changes from one revision to the other; an amount to the cent.
    """
    if now is None or was is None:
        if name in _NEVER_NULL:
            message = f"{name}: an amount the facet always carries is null on one side"
            raise ValueError(message)
        return None
    if name in _DATES:
        return (_day(now) - _day(was)).days
    if name in _DURATIONS:
        read, base = cast("JsonObject", now), cast("JsonObject", was)
        if read["unit"] != base["unit"]:
            message = f"{name}: a duration whose unit changes is not drawn by the witness"
            raise ValueError(message)
        value = Decimal(cast("str", read["value"])) - Decimal(cast("str", base["value"]))
        return {"value": decimal(value), "unit": read["unit"]}
    return money(Decimal(cast("str", now)) - Decimal(cast("str", was)))


def _nested(values: dict[str, JsonValue]) -> JsonObject:
    """Return values named as `task.label` in the shape of a node: `{"task": {"label": …}}`."""
    nested: JsonObject = {}
    for name, value in values.items():
        facet, _, key = name.partition(".")
        if key:
            cast("JsonObject", nested.setdefault(facet, {}))[key] = value
        else:
            nested[name] = value
    return nested


def base_and_deltas(
    row: mockcore.Row,
    was: mockcore.Row,
    ids: dict[int, str],
    same: dict[str, str],
    rows: dict[str, int],
) -> tuple[JsonObject, JsonObject]:
    """Return what the base carried of a node modified, and the deltas of what differs of it.

    `ComparedNodeRead.base`, and the delta of each date, duration and amount among them,
    `ComparedNodeRead.deltas`. The values that differ alone; a node the base names — a parent, a
    predecessor, a bearing task — named as the comparison renders it, a predecessor at the row it
    is rendered at (``rows``), as the predecessors of the node read.
    """
    names = differing(row, was, ids, same)
    now, then = _values(row, ids, same), _values(was, ids, same)
    base = {name: then.get(name) for name in names}
    if "predecessors" in base:
        base["predecessors"] = [
            {
                **link,
                "predecessor_node_id": (named := _same(link["predecessor_node_id"], same)),
                "predecessor_row_number": rows[cast("str", named)],
            }
            for link in cast("list[JsonObject]", was.node.get("predecessors") or [])
        ]
    deltas = {
        name: _delta(name, now.get(name), then.get(name))
        for name in names
        if name in _DATES | _DURATIONS | _AMOUNTS
    }
    return _nested(base), _nested(deltas)


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


def marked(
    before: list[mockcore.Row], after: list[mockcore.Row], *, compared: bool = False
) -> list[JsonObject]:
    """Return the nodes of a structure read against its base, marked, in the order of the plan.

    Each node as the structure read renders it, or as the base did for a node removed, with its
    place in the tree rendered, its difference and its changes; a node removed is read only.
    ``compared``, a revision read against a revision (``compareRevisions``): each node judged on
    every value it carries, and with its base and its deltas, null but for a node modified.
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
    ids = {row.number: cast("str", row.node["node_id"]) for row in [*before, *after]}
    # Each node of either side as the comparison renders it, found by its lineage: the base and the
    # revision read name the same node by two identifiers when the service copies a revision.
    lineage = {cast("str", row.node["node_id"]): row.number for row in [*before, *after]}
    same = {node_id: ids[number] for node_id, number in lineage.items()}
    own: dict[int, list[JsonValue]] = {}
    marks: dict[int, str] = {}
    for number, _, _ in reversed(order):
        if number not in was:
            marks[number] = ADDED
        elif number not in now:
            marks[number] = REMOVED
        else:
            own[number] = (
                named(now[number].kind, differing(now[number], was[number], ids, same))
                if compared
                else changes(now[number], was[number])
            )
            below = any(marks[child] != UNCHANGED for child in children.get(number, []))
            marks[number] = MODIFIED if own[number] or below or number in left else UNCHANGED
    source = {number: (now.get(number) or was[number]).node for number, _, _ in order}
    rows = {number: at for at, (number, _, _) in enumerate(order, start=1)}
    rendered = {node_id: rows[number] for node_id, number in lineage.items()}
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
                    "predecessor_row_number": rendered[cast("str", link["predecessor_node_id"])],
                }
                for link in cast("list[JsonObject]", node["predecessors"])
            ]
        if marks[number] == REMOVED:
            node["editable_fields"] = []
        node["difference"] = marks[number]
        node["changes"] = own.get(number, [])
        if compared:
            node["base"], node["deltas"] = None, None
            if marks[number] == MODIFIED:
                node["base"], node["deltas"] = base_and_deltas(
                    now[number], was[number], ids, same, rendered
                )
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


def read_with_fields(nodes: list[JsonObject], names: Collection[str]) -> list[JsonObject]:
    """Return the nodes of a comparison as a reading that names `fields` renders them (#166).

    The node as ``mockcore.with_fields`` reduces it, its mark, its base and its deltas always
    rendered; the base and the deltas reduced to the fields named, a facet of which none is left
    omitted (`ComparedNodeRead.base`).
    """
    properties = {name for name in names if "." not in name}
    facets: dict[str, set[str]] = {}
    for name in names:
        facet, _, key = name.partition(".")
        if key:
            facets.setdefault(facet, set()).add(key)

    def reduced(values: JsonValue) -> JsonValue:
        if values is None:
            return None
        kept: JsonObject = {}
        for key, value in cast("JsonObject", values).items():
            if key in properties:
                kept[key] = value
            elif key in facets:
                part = {
                    each: inner
                    for each, inner in cast("JsonObject", value).items()
                    if each in facets[key]
                }
                if part:
                    kept[key] = part
        return kept

    return [
        {**node, "base": reduced(node["base"]), "deltas": reduced(node["deltas"])}
        for node in mockcore.with_fields(nodes, names, COMPARED_ALWAYS)
    ]
