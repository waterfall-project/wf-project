# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the tree of a structure read against another, each node marked (C-361).

They try the places the marked tree gives its nodes, not the Vérif of a requirement: none cites
one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from typing import TYPE_CHECKING

from wftools import mockcore, mockdiff
from wftools.mockids import universe

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
