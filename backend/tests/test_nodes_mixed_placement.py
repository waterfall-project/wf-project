# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tasks and lines placed among each other, and a total read in any order (US-2260/L1).

``createNode`` and ``moveNodes`` place a task among the subtasks of its parent and a line among its
lines, each kind by its own rank; the reading gives the lines first, then the subtasks (#2502, the
rank itself being right on ``main`` and only unproved). The total the indicators give is the sum of
the lines the service reads, which must not depend on the order it reads them in (#2892): the test
reads it on the path the service takes (``estimate_indicators_of``), not on ``sum_amounts``, which
the service does not call.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, opened
from projects_support import scene as make_scene
from sqlalchemy import select

from waterfall.core.estimate import indicating
from waterfall.core.estimate.indicating import IndicatorsAsked, estimate_indicators_of
from waterfall.core.estimate.pricing import sum_amounts
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, the engineering rated this year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def material(costs: Costing, label: str, amount: str = "10.00") -> dict[str, Any]:
    """Give a line of material: one at ``amount``."""
    return {
        "label": label,
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": amount,
    }


def labelled(item: dict[str, Any]) -> str:
    """Give the label of a node read, a line's or a task's."""
    return (item["estimate_line"] if item["kind"] == "estimate_line" else item["task"])["label"]


def positions_hold(tree: Tree) -> bool:
    """Tell whether the positions read are, under each parent, those of the order read, from one."""
    under: dict[str | None, list[int]] = {}
    for item in tree.items():
        under.setdefault(item["parent_id"], []).append(item["position"])
    return all(each == list(range(1, len(each) + 1)) for each in under.values())


def order(tree: Tree) -> list[str]:
    """Read the labels of the nodes of the structure in the order read, the positions holding."""
    assert positions_hold(tree)
    return [labelled(item) for item in tree.items()]


def move(tree: Tree, nodes: list[dict[str, Any]], parent: dict[str, Any], **body: Any) -> list[str]:
    """Move nodes under a parent at the counter read, as the manager does; give the order then."""
    headers = tree.stage.manager.headers
    with tree.stage.database.transaction() as session:
        counter = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    sent = {
        "node_ids": [each["node_id"] for each in nodes],
        "parent_id": parent["node_id"],
        "lock_version": counter,
        **body,
    }
    answer = tree.api.post(f"{tree.path}/nodes/move", headers=headers, json=sent)
    assert answer.status_code == 200, answer.text
    return order(tree)


def read_all(tree: Tree, *labels: str) -> list[dict[str, Any]]:
    """Read the nodes of the labels, in the order of the labels."""
    found = {labelled(item): item for item in tree.items()}
    return [found[each] for each in labels]


def bearing(tree: Tree, lines: Lines, costs: Costing) -> dict[str, dict[str, Any]]:
    """Give a task P of two lines (L1, L2) and of two subtasks (S1, S2), each by its label."""
    task = tree.made("P")
    held = {"P": task}
    for label in ("L1", "L2"):
        held[label] = lines.made(task, **material(costs, label))["nodes"][0]
    for label in ("S1", "S2"):
        held[label] = tree.made(label, parent_id=task["node_id"])
    return held


def test_a_task_created_after_a_line_heads_the_subtasks_and_after_a_subtask_follows_it(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # La grille de devis « permet de créer […] des tâches » : a line named as the sibling of a task
    # is no subtask, so the task goes to the head of the subtasks, after the last line, whichever
    # line is named; a subtask named, after it; none, after the last subtask.
    held = bearing(tree, lines, costs)
    parent = held["P"]["node_id"]
    tree.made("X1", parent_id=parent, after_node_id=held["L1"]["node_id"])
    assert order(tree) == ["P", "L1", "L2", "X1", "S1", "S2"]
    tree.made("X2", parent_id=parent, after_node_id=held["L2"]["node_id"])
    assert order(tree) == ["P", "L1", "L2", "X2", "X1", "S1", "S2"]
    tree.made("X3", parent_id=parent, after_node_id=held["S1"]["node_id"])
    assert order(tree) == ["P", "L1", "L2", "X2", "X1", "S1", "X3", "S2"]
    tree.made("X4", parent_id=parent)
    assert order(tree) == ["P", "L1", "L2", "X2", "X1", "S1", "X3", "S2", "X4"]


def test_a_task_created_after_a_line_of_a_task_without_subtask_is_the_first_of_them(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # The task bears lines only: a task created after one of them is its first subtask, the lines
    # staying before it.
    task = tree.made("P")
    first = lines.made(task, **material(costs, "L1"))["nodes"][0]
    lines.made(task, **material(costs, "L2"))
    tree.made("X", parent_id=task["node_id"], after_node_id=first["node_id"])
    tree.made("R")
    assert order(tree) == ["P", "L1", "L2", "X", "R"]


def test_a_task_moved_after_a_line_heads_the_subtasks_of_the_parent_it_joins(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # ``moveNodes``: a task sent after a line of the new parent goes at the head of its subtasks, as
    # a task created there does; a subtask of the parent too, within its own parent.
    held = bearing(tree, lines, costs)
    stray = tree.made("Z")
    after = held["L1"]["node_id"]
    assert move(tree, [stray], held["P"], after_node_id=after) == [
        *("P", "L1", "L2", "Z", "S1", "S2")
    ]
    assert move(tree, read_all(tree, "S2"), held["P"], after_node_id=after) == [
        *("P", "L1", "L2", "S2", "Z", "S1")
    ]


def test_a_line_moved_after_a_subtask_ends_the_lines_before_the_subtasks(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # A line sent after a subtask goes after the last line, never among the subtasks: a line of
    # another task, then a line of its own.
    held = bearing(tree, lines, costs)
    other = tree.made("Q")
    guest = lines.made(other, **material(costs, "L3"))["nodes"][0]
    after = held["S1"]["node_id"]
    assert move(tree, [guest], held["P"], after_node_id=after) == [
        *("P", "L1", "L2", "L3", "S1", "S2", "Q")
    ]
    assert move(tree, read_all(tree, "L1"), held["P"], after_node_id=after) == [
        *("P", "L2", "L3", "L1", "S1", "S2", "Q")
    ]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_mixed_selection_is_placed_each_kind_by_its_own_rank_in_the_order_sent(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # A selection of tasks and lines sent in a mixed order: each kind is placed apart, in the order
    # sent among its own, after the sibling of its kind named or at the boundary of the other.
    held = bearing(tree, lines, costs)
    source = tree.made("Q")
    lines.made(source, **material(costs, "A"))
    lines.made(source, **material(costs, "B"))
    tree.made("T1", parent_id=source["node_id"])
    tree.made("T2", parent_id=source["node_id"])
    placed = move(
        tree,
        read_all(tree, "T2", "B", "T1", "A"),
        held["P"],
        after_node_id=held["L1"]["node_id"],
    )
    # Lines after L1, tasks at the head of the subtasks.
    assert placed == ["P", "L1", "B", "A", "L2", "T2", "T1", "S1", "S2", "Q"]
    placed = move(
        tree,
        read_all(tree, "A", "T1", "B", "T2"),
        held["P"],
        after_node_id=held["S1"]["node_id"],
    )
    # Lines after the last line, tasks after S1.
    assert placed == ["P", "L1", "L2", "A", "B", "S1", "T1", "T2", "S2", "Q"]
    placed = move(tree, read_all(tree, "T2", "B"), held["P"], after_node_id=None)
    # Each kind at the head of its own.
    assert placed == ["P", "B", "L1", "L2", "A", "T2", "S1", "T1", "S2", "Q"]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_selection_of_a_summary_task_and_one_of_its_subtasks_moves_the_group_whole(
    tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Le déplacement d'une sélection qui contient une récapitulative et l'une de ses
    # subordonnées laisse la subordonnée sous la récapitulative » : the group is moved entire, not
    # flattened, its lines and its other subtask with it.
    held = bearing(tree, lines, costs)
    target = tree.made("D")
    placed = move(tree, [held["P"], held["S1"]], target)
    assert placed == ["D", "P", "L1", "L2", "S1", "S2"]
    parents = {labelled(item): item["parent_id"] for item in tree.items()}
    assert parents["S1"] == parents["S2"] == held["P"]["node_id"]
    assert parents["P"] == target["node_id"]


@pytest.mark.requirement("WF-DAT-0100-A")
def test_the_total_of_a_revision_is_the_same_with_its_lines_read_in_the_reverse_order(
    stage: Scene,
    tree: Tree,
    lines: Lines,
    costs: Costing,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « La somme des montants budgétés d'une révision est identique quel que soit l'ordre de
    # sommation » : without a reference revision, budgeted and reestimated amounts are the same, so
    # the total of the indicators stands for the budgeted sum. The sum in ``Decimal`` is exact to 28
    # digits, so this test characterises the path of the service (``estimate_indicators_of``, which
    # sums by its own ``_amount``, not by ``sum_amounts``) and would pass on the original code: it
    # proves no defect, it guards the property against a sum that would turn inexact.
    amounts = (
        *("999999999999.99", "0.01", "19.99", "123456789.10"),
        *("0.07", "7.07", "999999999999.98"),
    )
    task = tree.made("Câblage")
    for index, amount in enumerate(amounts):
        lines.made(task, **material(costs, f"L{index}", amount))
    kept = [
        Decimal(item["estimate_line"]["reestimated_amount"])
        for item in tree.items()
        if item["kind"] == "estimate_line"
    ]
    assert len(kept) == len(amounts)
    expected = sum_amounts(kept)
    asked = IndicatorsAsked(None, "project", utc_now())
    project = UUID(stage.project["project_id"])

    def read() -> indicating.EstimateIndicators:
        with stage.database.transaction() as session:
            return estimate_indicators_of(session, project, asked)

    forward = read()
    reading = indicating.rows_of
    seen: list[list[UUID]] = []

    def reversed_rows(*args: Any) -> list[indicating.Row]:
        rows = reading(*args)
        seen.append([each.node_id for each in rows])
        return list(reversed(rows))

    monkeypatch.setattr(indicating, "rows_of", reversed_rows)
    backward = read()
    assert len(seen[0]) == len(amounts)
    assert forward.total.value == expected
    assert backward.total.value == expected
    for grouping in ("by_cost_type", "by_subproject", "by_work_package"):
        assert [each.amount.value for each in getattr(backward, grouping)] == [
            each.amount.value for each in getattr(forward, grouping)
        ], grouping
