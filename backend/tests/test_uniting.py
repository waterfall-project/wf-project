# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the union of a comparison compares of a node, without a base (US-2320/L3, WF-REV-0080).

The union is pure (``core/estimate/uniting.py``): two structures given as the API writes their
nodes, each pair of the same lineage judged on every value it carries but those that change from
one revision to the other without anything of the node changing, listed once beside it. The cases
the service reaches with difficulty are proved here: a label that follows its identifier, a node a
facet names, compared by its lineage, a predecessor by its lineage, its type and its lag, and what
is not compared.
"""

from decimal import Decimal
from typing import Any

import pytest

from waterfall.core.estimate.interface import PlacedNode, UnitedNode
from waterfall.core.estimate.uniting import changes_of, unite
from waterfall.core.planning.interface import UnitConstants

REQUIREMENT = "WF-REV-0080-A"
# The constants of the units by default: eight hours a day, forty a week, twenty days a month.
CONSTANTS = UnitConstants(Decimal(8), Decimal(40), Decimal(20))


def line(node_id: str, lineage: str, parent: str, **facet: Any) -> UnitedNode[str]:
    """Give a line as the union reads it, under a task, its facet written with ``facet``."""
    values: dict[str, Any] = {
        "node_id": node_id,
        "lineage_id": lineage,
        "kind": "estimate_line",
        "parent_id": parent,
        "position": 1,
        "row_number": 2,
        "level": 2,
        "origin_risk_id": facet.pop("origin_risk_id", None),
        "lock_version": 1,
        "task": None,
        "estimate_line": {
            "label": "Câbles",
            "subproject_id": "s-1",
            "subproject_label": "Poste de commande",
            "bearing_task_node_id": None,
            "bearing_task_label": None,
            "remaining_entry": {"is_available": True, "missing_conditions": []},
            **facet,
        },
        "predecessors": [],
        "computed_fields": [],
        "editable_fields": ["estimate_line.label"],
    }
    return UnitedNode(node_id, lineage, "estimate_line", parent, (), values, None)


def task(
    node_id: str,
    lineage: str,
    links: tuple[tuple[str, str, str], ...] = (),
    node: dict[str, Any] | None = None,
    **facet: Any,
) -> UnitedNode[str]:
    """Give a task at the first level as the union reads it; ``links`` its predecessors.

    ``node`` what its properties are besides, ``facet`` what its facet is.
    """
    values: dict[str, Any] = {
        "node_id": node_id,
        "lineage_id": lineage,
        "kind": "task",
        "parent_id": None,
        "position": 1,
        "row_number": 1,
        "level": 1,
        "origin_risk_id": None,
        "lock_version": 1,
        "task": {"label": "Câblage", "finish_overdue": False, **facet},
        "estimate_line": None,
        "predecessors": [
            {
                "predecessor_node_id": each,
                "predecessor_row_number": 9,
                "link_type": kind,
                "lag": {"value": lag, "unit": "d"},
            }
            for each, kind, lag in links
        ],
        "computed_fields": ["task.finish"],
        "editable_fields": ["task.label"],
        **(node or {}),
    }
    named = tuple(each for each, _, _ in links)
    return UnitedNode(node_id, lineage, "task", None, named, values, None)


def placed(
    base: list[UnitedNode[str]], compared: list[UnitedNode[str]]
) -> dict[str, PlacedNode[str]]:
    """Unite two structures; give each node of the union as it is returned, by its lineage."""
    union = unite(base, compared, CONSTANTS)
    return {union.nodes[each].lineage_id: union.placed(each) for each in union.order}


@pytest.mark.requirement(REQUIREMENT)
def test_what_changes_without_the_node_changing_is_not_compared() -> None:
    # The identifiers, the counter, the row, the rank, the level, the lists of what is computed
    # or enterable, the overdue finish and whether a line accepts a re-estimate: a node of another
    # identifier in each revision, each of them other, is unchanged.
    before = [task("a-1", "t"), line("a-2", "l", "a-1")]
    beside: dict[str, Any] = {"lock_version": 4, "row_number": 3, "position": 2, "level": 2}
    beside |= {"computed_fields": [], "editable_fields": []}
    after_task = task("b-1", "t", node=beside, finish_overdue=True)
    after_line = line(
        "b-2", "l", "b-1", remaining_entry={"is_available": False, "missing_conditions": ["x"]}
    )
    found = placed(before, [after_task, after_line])
    assert {(each.difference, each.changes, each.base) for each in found.values()} == {
        ("unchanged", (), None)
    }


@pytest.mark.requirement(REQUIREMENT)
def test_a_label_follows_its_identifier_and_never_marks_alone() -> None:
    # A subproject renamed, its identifier kept, changes nothing of the line; another subproject
    # changes it by ``subproject``, its label with it in the base.
    base = [task("a-1", "t"), line("a-2", "l", "a-1")]
    renamed = placed(base, [task("b-1", "t"), line("b-2", "l", "b-1", subproject_label="Armoires")])
    assert renamed["l"].difference == "unchanged"
    moved = placed(
        base,
        [
            task("b-1", "t"),
            line("b-2", "l", "b-1", subproject_id="s-2", subproject_label="Armoires"),
        ],
    )
    assert (moved["l"].changes, moved["l"].base) == (
        ("subproject",),
        {
            "estimate_line.subproject_id": "s-1",
            "estimate_line.subproject_label": "Poste de commande",
        },
    )
    assert (moved["t"].difference, moved["t"].changes, moved["t"].base) == ("modified", (), {})


@pytest.mark.requirement(REQUIREMENT)
def test_the_bearing_task_of_a_line_is_compared_by_its_lineage_and_named_as_returned() -> None:
    # The same task bears the line in each revision under two identifiers: unchanged. Another
    # one: ``other``, the base naming the node the union returns for it, its label with it.
    base = [
        task("a-1", "t"),
        task("a-3", "u"),
        line("a-2", "l", "a-1", bearing_task_node_id="a-1", bearing_task_label="Câblage"),
    ]
    same = placed(
        base,
        [
            task("b-1", "t"),
            task("b-3", "u"),
            line("b-2", "l", "b-1", bearing_task_node_id="b-1", bearing_task_label="Câblage"),
        ],
    )
    assert same["l"].difference == "unchanged"
    other = placed(
        base,
        [
            task("b-1", "t"),
            task("b-3", "u"),
            line("b-2", "l", "b-1", bearing_task_node_id="b-3", bearing_task_label="Essais"),
        ],
    )
    assert (other["l"].changes, other["l"].base) == (
        ("other",),
        {
            "estimate_line.bearing_task_node_id": "b-1",
            "estimate_line.bearing_task_label": "Câblage",
        },
    )


@pytest.mark.requirement(REQUIREMENT)
def test_a_predecessor_is_compared_by_its_lineage_its_type_and_its_lag() -> None:
    # The same predecessor under another identifier and another row: unchanged. Its lag changed:
    # ``other``, the base naming the node the union returns for it, at its number in the union.
    base = [task("a-1", "p"), task("a-2", "s", (("a-1", "finish_to_start", "0"),))]
    same = placed(base, [task("b-1", "p"), task("b-2", "s", (("b-1", "finish_to_start", "0"),))])
    assert same["s"].difference == "unchanged"
    lagged = placed(base, [task("b-1", "p"), task("b-2", "s", (("b-1", "finish_to_start", "2"),))])
    assert (lagged["s"].changes, lagged["s"].base) == (
        ("other",),
        {
            "predecessors": [
                {
                    "predecessor_node_id": "b-1",
                    "predecessor_row_number": 1,
                    "link_type": "finish_to_start",
                    "lag": {"value": "0", "unit": "d"},
                }
            ]
        },
    )


@pytest.mark.requirement(REQUIREMENT)
def test_the_risk_a_node_comes_from_is_compared_as_it_is() -> None:
    # A risk keeps its identifier in every revision (WF-RIS-0020): another one is ``other``.
    base = [task("a-1", "t"), line("a-2", "l", "a-1", origin_risk_id="r-1")]
    found = placed(base, [task("b-1", "t"), line("b-2", "l", "b-1", origin_risk_id="r-2")])
    assert (found["l"].changes, found["l"].base) == (("other",), {"origin_risk_id": "r-1"})


@pytest.mark.requirement(REQUIREMENT)
def test_each_value_is_named_by_the_change_it_makes_other_last() -> None:
    # The values WF-REV-0080 names, by kind, in the order of ``NodeChange``, any other ``other``; a
    # node of another kind by its parent alone.
    assert changes_of("task", ["task.label", "parent_id", "task.finish"]) == (
        "dates",
        "parent",
        "other",
    )
    assert changes_of("estimate_line", ["estimate_line.cost_category_label"]) == ("cost_category",)
    assert changes_of("risk", ["parent_id"]) == ("parent",)
    assert changes_of("risk", ["label"]) == ("other",)
