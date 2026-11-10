# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the paste that creates the tasks past the last row, and of the undo and the redo.

The paste cites the Vérif of WF-IHM-0050-A it tries on the examples (confirmed, the other rows
written and not the refused one); the tasks it creates, the undo and the redo try the
simplifications of the fake back — the values a creation gives, the renaming undone and redone, the
history left behind them —, not a Vérif (the fifty successive undos of WF-IHM-0110-A are not tried
here), and cite none (WF-QUA-0010).
"""

import json
from typing import Any, cast

import pytest

from wftools import mockcore, mockundoable, mockwitness, mockwrites
from wftools.mockids import universe
from wftools.mockwitness import WIRING, fixture

type Node = dict[str, Any]

REFUSED = {"row": 3, "column": "label", "code": "VALIDATION_FAILED"}
"""The refusal of the row past the last node that brings no label (`PastePreview`, #2559)."""

PLANS = {
    "paste_plan",
    "paste_plan_amendment",
    "paste_plan_amendment_skipping",
    "paste_plan_amendment_target_removed",
    "paste_plan_creating",
    "paste_plan_subproject_held",
    "paste_plan_unknown_category",
    "paste_plan_without_hours",
}
"""The plans the fake back serves: each one says how many of its rows create."""


@pytest.mark.requirement("WF-IHM-0050-A")
def test_the_rows_past_the_last_node_create_tasks_and_the_one_without_a_label_is_refused() -> None:
    # « confirmé, il écrit les autres lignes et non celle-ci » : the plan says what will be written,
    # created and refused, nothing written; the row without a label is the one not written.
    assert fixture("paste_plan_creating") == {
        "paste_id": universe(993),
        "accepted": 3,
        "created": 2,
        "rejected": [REFUSED],
    }
    applied = fixture("paste_applied_creating")
    anchor, *created = cast("list[Node]", applied["nodes"])
    last = cast("Node", mockcore.current()[-1].node)
    assert anchor["node_id"] == last["node_id"]
    assert anchor["lock_version"] == last["lock_version"] + 1
    assert anchor["task"]["description"] == mockundoable.CREATING_BLOCK[0][1]
    assert [node["task"]["label"] for node in created] == [
        row[0] for row in mockundoable.CREATING_BLOCK[1:3]
    ]
    assert applied["rejected"] == [REFUSED]


def test_the_tasks_created_are_siblings_of_the_last_node_after_it_as_a_creation_gives_them() -> (
    None
):
    # The anchor is the last node of the structure the fake back serves first; the tasks created
    # share its parent, ranked after it in the order of the block, at their first version, each a
    # leaf in automatic mode of one day without a predecessor, not started, as `createNode` gives
    # it.
    served = json.loads((mockwitness.FIXTURES / "volume" / "nodes_thousand.json").read_text())
    [last] = served["value"]["items"][-1:]
    assert last["task"]["label"] == mockundoable.CREATING_BLOCK[0][0]
    anchor, *created = cast("list[Node]", fixture("paste_applied_creating")["nodes"])
    assert anchor["node_id"] == last["node_id"]
    assert [
        (node["parent_id"], node["position"], node["row_number"], node["lock_version"])
        for node in created
    ] == [
        (last["parent_id"], last["position"] + rank, last["row_number"] + rank, 1)
        for rank in (1, 2)
    ]
    for node in created:
        task = node["task"]
        assert (task["scheduling_mode"], task["duration"], task["progress"]) == (
            "automatic",
            {"value": "1", "unit": "d"},
            "not_started",
        )
        assert node.get("predecessors", []) == []
    assert fixture("paste_applied_creating")["structure_lock_version"] == 2


def test_every_plan_counts_its_rows_that_create_among_those_it_accepts() -> None:
    # `PastePlan.created` is required, `0` where no row falls past the last node.
    plans = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))["value"]
        for path in mockwitness.FIXTURES.glob("paste_plan*.json")
    }
    assert set(plans) == PLANS
    assert {name: plan["created"] for name, plan in plans.items() if plan["created"]} == {
        "paste_plan_creating": 2
    }
    assert all(plan["created"] <= plan["accepted"] for plan in plans.values())


def test_a_row_past_the_last_node_without_a_label_creates_nothing() -> None:
    block = (("Fin du lot 9.3", ""), ("", "Sans libellé"), ("Libellé", ""))
    assert mockundoable.creating_refusals(block) == [{**REFUSED, "row": 1}]
    assert mockundoable.created_numbers(block) == [mockcore.current()[-1].number + 1]


def test_an_undo_gives_the_label_back_one_version_further_than_the_renaming() -> None:
    renamed = mockwrites.task_renamed()
    [written] = cast("list[Node]", renamed["nodes"])
    undone = fixture("undo_task_renamed")
    assert undone["undone"] == {"kind": "cell", "node_ids": [universe(WIRING)], "risk_ids": []}
    assert undone["remaining_depth"] == 0
    [node] = undone["written"]["nodes"]
    items = cast("list[Node]", mockcore.whole(mockcore.current())["items"])
    read = {each["node_id"]: each for each in items}[universe(WIRING)]
    assert node == {**read, "lock_version": written["lock_version"] + 1}
    version = cast("int", renamed["structure_lock_version"])
    assert undone["written"]["structure_lock_version"] == version + 1


def test_a_redo_renames_again_one_version_further_than_the_undo() -> None:
    undone, redone = fixture("undo_task_renamed"), fixture("redo_task_renamed")
    assert redone["undone"] == undone["undone"]
    assert redone["remaining_depth"] == 0
    [before], [node] = undone["written"]["nodes"], redone["written"]["nodes"]
    [renamed] = cast("list[Node]", mockwrites.task_renamed()["nodes"])
    assert node == {**renamed, "lock_version": before["lock_version"] + 1}
    assert node["task"]["label"] == mockwrites.RENAMED
    assert redone["written"]["structure_lock_version"] == 4


def test_the_variants_of_the_undo_and_the_redo_differ_by_the_history_left_alone() -> None:
    # The forms `one` and `other` of the announcement of the front (#2626): the changes left are
    # in the estimate of the amendment 2, and write nothing of the main structure.
    for variant, base, left in (
        ("undo_task_renamed_one_left", "undo_task_renamed", 1),
        ("redo_task_renamed_two_left", "redo_task_renamed", 2),
    ):
        served = fixture(variant)
        assert served["remaining_depth"] == left
        assert {**served, "remaining_depth": 0} == fixture(base)
