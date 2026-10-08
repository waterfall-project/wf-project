# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the sort of a grid of the tree in the fake back, and of the examples it orders (#526).

They try the simplification of the fake back against the convention the contract writes, not the
Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from dataclasses import replace
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockcore, mockdata
from wftools.mockids import universe
from wftools.mocksort import LINE_COLUMNS, LineSort

type Node = dict[str, Any]

CONTROL_STATION, WIRING, LABOUR, BLOCKS, PROVISION, MILESTONE = 551, 552, 553, 554, 555, 556
OCCURRED = 541


@pytest.fixture(scope="module")
def readings() -> dict[str, Any]:
    """Read the named examples back from the text the generator writes."""
    return {
        name: json.loads(mockdata.render(example))["value"]
        for name, example in mockdata.readings().items()
    }


def _number(node: Node) -> int:
    return int(node["node_id"][-4:])


def _facet(node: Node) -> Node:
    return cast("Node", node[node["kind"]])


def _under(items: list[Node], parent: int) -> list[int]:
    return [_number(node) for node in items if node["parent_id"] == universe(parent)]


def _in_place(plan: Node, read: Node) -> None:
    """Assert that a sorted reading moves no task, and each line among those of its task only."""
    assert (read["totals"], read["meta"]) == (plan["totals"], plan["meta"])
    planned, sorted_ = plan["items"], read["items"]
    assert sorted(map(_number, sorted_)) == sorted(map(_number, planned))
    for at, node in enumerate(planned):
        if node["kind"] == "task":
            assert sorted_[at] == node
        else:
            assert sorted_[at]["kind"] == "estimate_line"
            assert sorted_[at]["parent_id"] == node["parent_id"]


def test_a_sort_moves_the_lines_under_each_task_and_never_a_task(
    readings: dict[str, Any],
) -> None:
    # A grid of a tree does not sort; its sort is but a sort of the lines under each task.
    read = readings["nodes_estimate_sorted.json"]
    _in_place(readings["nodes_estimate.json"], read)
    assert _under(read["items"], WIRING) == [PROVISION, LABOUR, BLOCKS]
    # The milestone, of no amount, stays last: a sort of the siblings would have put it first.
    siblings = [node for node in read["items"] if node["parent_id"] == universe(CONTROL_STATION)]
    assert [_number(node) for node in siblings] == [WIRING, OCCURRED, MILESTONE]
    assert _facet(siblings[-1])["base_amount"] == "0.00"


def test_a_line_without_a_value_comes_first_in_the_descending_order_in_plan_order(
    readings: dict[str, Any],
) -> None:
    read = readings["nodes_estimate_hours.json"]
    _in_place(readings["nodes_estimate.json"], read)
    lines = {_number(node): _facet(node) for node in read["items"]}
    # The disbursement and the provision have no hours: before the labour, in the order of the plan.
    assert _under(read["items"], WIRING) == [BLOCKS, PROVISION, LABOUR]
    assert [lines[n]["hours"] for n in (BLOCKS, PROVISION, LABOUR)] == [None, None, "12.5"]


def _line(row: mockcore.Row, **values: object) -> mockcore.Row:
    return replace(row, node={**row.node, "estimate_line": {**_facet(row.node), **values}})


@pytest.fixture(scope="module")
def lines() -> list[mockcore.Row]:
    """Four lines of the core, in the order of the plan."""
    return [row for row in mockcore.core() if row.kind == mockcore.ESTIMATE_LINE][:4]


def test_a_line_without_a_value_comes_after_the_others_ascending_before_them_descending(
    lines: list[mockcore.Row],
) -> None:
    first, second, third, fourth = (
        _line(lines[0], hours=None),
        _line(lines[1], hours="8"),
        _line(lines[2], hours=None),
        _line(lines[3], hours="12.5"),
    )
    given = [first, second, third, fourth]
    assert LineSort("hours").ordered(given) == [second, fourth, first, third]
    assert LineSort("hours", descending=True).ordered(given) == [first, third, fourth, second]


def test_texts_and_references_compare_by_their_code_points(lines: list[mockcore.Row]) -> None:
    # « Z » before « É », « 100 » before « 20 », as every text of the contract (#292).
    labels = ["É", "Z", "20", "100"]
    given = [_line(row, label=text) for row, text in zip(lines, labels, strict=True)]
    ordered = LineSort("label").ordered(given)
    assert [_facet(row.node)["label"] for row in ordered] == ["100", "20", "Z", "É"]
    # A reference by its label, not by its identifier; one without after the others.
    roles = [
        _line(row, resource_role_label=label)
        for row, label in zip(lines, [*labels[:3], None], strict=True)
    ]
    ordered = LineSort("resource_role").ordered(roles)
    assert [_facet(row.node)["resource_role_label"] for row in ordered] == ["20", "Z", "É", None]


def test_lines_of_one_value_keep_the_order_of_the_plan_in_both_directions(
    lines: list[mockcore.Row],
) -> None:
    # As any sort at equality (DECISIONS, « Un tri à égalité se départage »).
    same = [_line(row, base_amount="1.00") for row in lines]
    for descending in (False, True):
        assert LineSort("base_amount", descending).ordered(same) == same


def test_the_columns_a_line_sorts_by_are_those_of_the_contract() -> None:
    # `label`, then from `cost_category` to `previous_reestimated_amount` (`NodeColumn`).
    schema = (REPOSITORY / "docs/api/components/schemas/revisions.yaml").read_text(encoding="utf-8")
    block = schema[schema.index("\nNodeColumn:") :]
    block = block[block.index("  enum:") : block.index("\n\n")]
    columns = re.findall(r"^    - (\w+)$", block, re.MULTILINE)
    assert ("label", *columns[columns.index("cost_category") :]) == LINE_COLUMNS
