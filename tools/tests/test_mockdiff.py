# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the tree of a structure read against another, each node marked (C-361).

They try the places the marked tree gives its nodes, not the Vérif of a requirement: none cites
one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools import mockcore, mockdiff, mockwrites
from wftools.mockids import universe
from wftools.mocksort import LineSort
from wftools.mockstructure import described
from wftools.mockwitness import N, Task

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject


def _row(number: int, parent: int | None, row: int, kind: str = mockcore.TASK) -> mockcore.Row:
    node: JsonObject = {
        "node_id": universe(number),
        "kind": kind,
        "editable_fields": ["label"],
        kind: {"label": f"Nœud {number}", "start": "2026-06-01", "finish": "2026-06-05"},
    }
    return mockcore.Row(number, parent, row, kind, f"Nœud {number}", node)


def test_a_sibling_kept_after_a_node_removed_counts_it_in_its_rank_and_its_row() -> None:
    # A task bearing a line and three subtasks; the line and the second subtask are removed. Each
    # is rendered at the place it had, read only, and the siblings kept after it count it: their
    # rank and their row are those of the tree rendered (`NodeDifference`, `Node.position`).
    line, first, second, third = 521, 522, 523, 524
    before = [
        _row(520, None, 1),
        _row(line, 520, 2, mockcore.ESTIMATE_LINE),
        _row(first, 520, 3),
        _row(second, 520, 4),
        _row(third, 520, 5),
    ]
    after = [_row(520, None, 1), _row(first, 520, 2), _row(third, 520, 3)]
    nodes = mockdiff.marked(before, after)
    placed = {
        node["node_id"]: (node["difference"], node["position"], node["row_number"])
        for node in nodes
    }
    assert [node["node_id"] for node in nodes] == [
        universe(n) for n in (520, line, first, second, third)
    ]
    assert placed == {
        universe(520): (mockdiff.MODIFIED, 1, 1),
        universe(line): (mockdiff.REMOVED, 1, 2),
        universe(first): (mockdiff.UNCHANGED, 2, 3),
        universe(second): (mockdiff.REMOVED, 3, 4),
        universe(third): (mockdiff.UNCHANGED, 4, 5),
    }
    removed = [node for node in nodes if node["difference"] == mockdiff.REMOVED]
    assert all(node["editable_fields"] == [] for node in removed)
    # The summary is modified by its content alone: its own values are unchanged.
    assert nodes[0]["changes"] == []


def test_a_line_removed_is_sorted_by_its_base_values_and_unsorted_stays_in_place() -> None:
    # #1205: a node removed from a differential has only the values of the base; a sort judges it
    # on them, as any other node on its own, and without a sort it stays at the place it had. The
    # first line of the wiring removed: first unsorted, last by the amount descending.
    before = mockcore.current()
    gone = N.LABOUR

    def removed(each: Task) -> Task:
        if each.number != N.WIRING:
            return each
        return replace(each, lines=tuple(line for line in each.lines if line.number != gone))

    after = mockcore.current(mockwrites.amended(described(), removed))
    nodes = cast("list[dict[str, Any]]", mockdiff.marked(before, after))
    wiring = universe(N.WIRING)
    lines = [
        node for node in nodes if node["parent_id"] == wiring and node["kind"] == "estimate_line"
    ]
    [line] = [node for node in lines if node["difference"] == "removed"]
    [was] = [
        cast("dict[str, Any]", row.node["estimate_line"]) for row in before if row.number == gone
    ]
    assert line["estimate_line"] == was
    assert (lines.index(line), line["position"]) == (0, 1)
    # Sorted by the sort of the fake back (#1216): the lines of the differential, the one removed
    # read on its base values — those it had before —, the others on their own.
    rows = {cast("str", row.node["node_id"]): row for row in [*before, *after]}
    by_amount = LineSort("base_amount", descending=True)
    ordered = by_amount.ordered([rows[node["node_id"]] for node in lines])
    amount = Decimal(was["base_amount"])
    others = [Decimal(node["estimate_line"]["base_amount"]) for node in lines if node is not line]
    assert all(other > amount for other in others)
    assert [row.number for row in ordered][-1] == gone
    assert len(ordered) == len(lines)
