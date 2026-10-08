# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the answers of the writes of the grids, generated from what each write changes.

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockcore, mockdata, mockstructure, mockwitness, mockwrites
from wftools.mockwitness import CABLE_FITTER, CORE, universe

type Node = dict[str, Any]

STUDIES, REVIEW, ACCEPTANCE, DESIGN_FILE = 521, 524, 525, 526
VOLUME_WRITES = {"estimate_line_entered.json", "paste_applied.json"}
CONTROL_STATION, WIRING, LABOUR, BLOCKS, MILESTONE = 551, 552, 553, 554, 556
INSTALLATION, MOUNTING, ON_SITE, TESTS, COMMISSIONING, COMMISSIONING_LINE = (
    561,
    562,
    563,
    564,
    565,
    566,
)


def _json(value: Any) -> Any:
    """Read a value back from the text the generator writes."""
    return json.loads(json.dumps(value))


@pytest.fixture(scope="module")
def whole() -> dict[str, Any]:
    """Read the whole core today, as an unfiltered reading of the structure gives it."""
    return cast("dict[str, Any]", _json(mockcore.whole(mockcore.current())))


@pytest.fixture(scope="module")
def answer() -> dict[str, Any]:
    """Make the structure of a thousand tasks once, as the JSON the fake back serves."""
    return cast("dict[str, Any]", _json(mockstructure.structure().nodes))


@pytest.fixture(scope="module")
def items(answer: dict[str, Any]) -> list[Node]:
    return cast("list[Node]", answer["items"])


def by_id(items: list[Node]) -> dict[str, Node]:
    return {node["node_id"]: node for node in items}


def numbered(nodes: list[Node]) -> dict[int, Node]:
    """Return the nodes of the core an answer gives, by the number of their identifier."""
    return {int(node["node_id"][-3:]): node for node in nodes}


def facet(node: Node) -> Node:
    return cast("Node", node[node["kind"]])


def write(name: str) -> dict[str, Any]:
    """Return the answer of a write of the core, read back from the text the generator writes."""
    return cast("dict[str, Any]", _json(getattr(mockwrites, name)()))


def money(value: str) -> Decimal:
    return Decimal(value)


def test_a_duration_lengthened_pushes_a_successor_into_the_next_year(
    answer: dict[str, Any], items: list[Node]
) -> None:
    # What updateTaskFacet answers (task_lengthened.json): the task written, its successor moved
    # into 2027 and its lines corrected anew, the summaries above and the totals summed again
    # from the same lines, the amounts at the year of reference unchanged (WF-DEV-0040).
    written = cast("dict[str, Any]", json.loads(json.dumps(mockwrites.task_lengthened())))
    before = by_id(items)
    [task] = written["nodes"]
    old = before[task["node_id"]]["task"]
    assert task["task"]["label"] == mockwrites.LENGTHENED
    assert int(task["task"]["duration"]["value"]) == (
        int(old["duration"]["value"]) + mockwrites.LENGTHENED_BY
    )
    assert task["task"]["finish"]["date"] == "2026-12-31"
    assert task["lock_version"] == 2
    moved = {entry["node_id"]: entry for entry in written["rescheduled"]}
    [successor] = [entry for entry in moved.values() if entry["start"]["date"] >= "2027"]
    assert before[successor["node_id"]]["task"]["start"]["date"] == "2026-12-30"
    # Within the float: the dates of no other task move, their float alone.
    for node_id, entry in moved.items():
        if node_id != successor["node_id"]:
            assert entry["start"] == before[node_id]["task"]["start"]
            assert entry["finish"] == before[node_id]["task"]["finish"]
    # The lines of the successor, consumed in 2027, and the successor itself, which sums them.
    lines_of = [node for node in items if node["parent_id"] == successor["node_id"]]
    amounts = {entry["node_id"]: entry for entry in written["reinflated"]}
    assert list(amounts) == [successor["node_id"], *(node["node_id"] for node in lines_of)]
    delta = Decimal(0)
    for node in lines_of:
        line = node["estimate_line"]
        entry = amounts[node["node_id"]]
        assert entry["consumption_year"] == 2027
        assert Decimal(entry["inflated_amount"]) == mockstructure.inflated(
            Decimal(line["base_amount"]), 2027
        )
        delta += Decimal(entry["inflated_amount"]) - Decimal(line["inflated_amount"])
    total = sum(Decimal(amounts[node["node_id"]]["inflated_amount"]) for node in lines_of)
    assert amounts[successor["node_id"]]["consumption_year"] is None
    assert Decimal(amounts[successor["node_id"]]["inflated_amount"]) == total
    # The summaries above, whole, and the totals: the corrected amounts move by the same delta.
    assert [node["task"]["is_summary"] for node in written["ancestors"]] == [True, True]
    for node in written["ancestors"]:
        was = before[node["node_id"]]["task"]
        assert Decimal(node["task"]["inflated_amount"]) == Decimal(was["inflated_amount"]) + delta
        assert node["task"]["base_amount"] == was["base_amount"]
    totals = answer["totals"]
    assert Decimal(written["totals"]["inflated_amount"]) == (
        Decimal(totals["inflated_amount"]) + delta
    )
    assert written["totals"]["base_amount"] == totals["base_amount"]


def test_a_write_of_the_core_answers_the_node_written_its_summaries_and_the_whole_totals(
    whole: dict[str, Any],
) -> None:
    # The label of the wiring renamed: the task, one version further; its summary, as the
    # readings give it — its order item named by the generator, not by hand (WF-PLA-0130) —;
    # nothing redated nor moved in time; the totals of the whole structure, unchanged.
    renamed = write("task_renamed")
    read = by_id(whole["items"])
    [task] = renamed["nodes"]
    assert (task["node_id"], task["lock_version"]) == (universe(WIRING), 2)
    assert task["task"]["label"] == mockwrites.RENAMED
    assert {
        **task,
        "lock_version": 1,
        "task": {**task["task"], "label": "Câblage des armoires"},
    } == (read[universe(WIRING)])
    [summary] = renamed["ancestors"]
    assert summary == read[universe(CONTROL_STATION)]
    assert summary["task"]["order_item_id"] == mockwitness.ASSEMBLY.identifier
    assert summary["task"]["work_breakdown_label"] == mockwitness.ASSEMBLY.label
    assert (renamed["rescheduled"], renamed["reinflated"]) == ([], [])
    assert renamed["totals"] == whole["totals"]
    assert renamed["totals"]["task_count"] == 15
    assert renamed["structure_lock_version"] == 2
    # The same summary, rendered by every write of the wiring, is the reading's node, recalculated.
    estimate = numbered(mockwitness.fixture("nodes_estimate")["items"])
    assert estimate[CONTROL_STATION] == summary


def test_hours_entered_reestimate_a_line_and_leave_its_budget(whole: dict[str, Any]) -> None:
    # 12.5 hours become 14: the re-estimate follows the quantities, 14 x 80; the budget is the
    # reference's (WF-DEV-0020); the task and the summary above follow, and the totals.
    updated = write("estimate_line_updated")
    [line] = updated["nodes"]
    assert line["estimate_line"]["hours"] == "14"
    assert line["estimate_line"]["base_amount"] == "1120.00"
    assert line["estimate_line"]["reestimated_amount"] == "1120.00"
    assert line["estimate_line"]["budgeted_amount"] == "1000.00"
    read = numbered(whole["items"])
    above = numbered(updated["ancestors"])
    assert sorted(above) == [CONTROL_STATION, WIRING]
    for number, node in above.items():
        was = read[number]["task"]
        assert money(node["task"]["base_amount"]) == money(was["base_amount"]) + 120
        assert node["task"]["budgeted_amount"] == was["budgeted_amount"]
    totals = updated["totals"]
    assert money(totals["reestimated_amount"]) == money(whole["totals"]["reestimated_amount"]) + 120
    assert totals["budgeted_amount"] == whole["totals"]["budgeted_amount"]
    assert money(totals["hours"]) == money(whole["totals"]["hours"]) + Decimal("1.5")


def test_a_line_deleted_leaves_its_ancestors_and_the_totals_to_render(
    whole: dict[str, Any],
) -> None:
    deleted = write("node_deleted")
    assert deleted["nodes"] == []
    above = numbered(deleted["ancestors"])
    assert sorted(above) == [CONTROL_STATION, WIRING]
    assert above[WIRING]["task"]["base_amount"] == "1500.00"
    assert above[CONTROL_STATION]["task"]["base_amount"] == "1700.00"
    totals = deleted["totals"]
    assert totals["estimate_line_count"] == whole["totals"]["estimate_line_count"] - 1
    assert money(totals["base_amount"]) == money(whole["totals"]["base_amount"]) - money("1234.56")
    assert (deleted["rescheduled"], deleted["reinflated"]) == ([], [])


def test_a_link_set_on_a_task_not_started_redates_what_follows_and_nothing_past(
    whole: dict[str, Any],
) -> None:
    # The mounting on site, not started, two days after the factory acceptance: it and the
    # commissioning move, the commissioning still starts in 2026 — nothing is moved in time —,
    # and the tasks without a successor gain float; the acceptance stays on 30 June (C13).
    linked = write("predecessor_set")
    read = numbered(whole["items"])
    [mounting] = linked["nodes"]
    assert mounting["predecessors"] == [
        {
            "predecessor_node_id": universe(MILESTONE),
            "predecessor_row_number": 18,
            "link_type": "finish_to_start",
            "lag": {"value": "2", "unit": "d"},
        }
    ]
    assert (mounting["task"]["start"]["date"], mounting["task"]["finish"]["date"]) == (
        "2026-07-03",
        "2026-12-22",
    )
    moved = numbered(linked["rescheduled"])
    assert list(moved) == [DESIGN_FILE, 542, 544, COMMISSIONING]
    for number in (DESIGN_FILE, 542, 544):
        assert moved[number]["start"] == read[number]["task"]["start"]
        assert moved[number]["finish"] == read[number]["task"]["finish"]
    assert moved[COMMISSIONING]["start"]["date"] == "2026-12-23"
    assert linked["reinflated"] == []
    assert sorted(numbered(linked["ancestors"])) == [STUDIES, 541, CONTROL_STATION, INSTALLATION]
    assert linked["totals"] == whole["totals"]


def test_no_write_moves_a_fact_already_recorded(
    whole: dict[str, Any], answer: dict[str, Any]
) -> None:
    # The progress of a task and the days it started and completed are facts (WF-PLA-0130): no
    # node a write renders, whole or by its schedule, says them otherwise than the reading.
    facts = ("progress", "started_on", "completed_on")
    for name, example in mockwrites.writes().items():
        value = _json(example["value"])
        if "nodes" not in value:
            continue
        read = by_id(answer["items"] if name in VOLUME_WRITES else whole["items"])
        for node in [*value["nodes"], *value["ancestors"]]:
            if node["kind"] == "task":
                was = read[node["node_id"]]["task"]
                assert [node["task"].get(key) for key in facts] == [
                    was.get(key) for key in facts
                ], (name, node["node_id"])
        for entry in value["rescheduled"]:
            was = read[entry["node_id"]]["task"]
            if was["progress"] != "not_started":
                assert (entry["start"], entry["finish"]) == (was["start"], was["finish"]), (
                    name,
                    entry["node_id"],
                )


def test_a_role_on_another_calendar_redates_its_task_and_moves_its_successor_in_time(
    whole: dict[str, Any],
) -> None:
    # The wiring on site given to the cable fitter, on the week of four days: the mounting works
    # the days both its roles work, four of eight hours (WF-PLA-0010), and finishes in 2027.
    roots = mockwrites.amended(CORE, line=mockwrites.on_line(ON_SITE, role=CABLE_FITTER))
    calendar = mockcore.schedule(roots)[MOUNTING].calendar
    assert calendar.week == tuple(Decimal(hours) for hours in (8, 8, 8, 8, 0, 0, 0))
    redated = write("estimate_line_redated")
    read = numbered(whole["items"])
    [line] = redated["nodes"]
    assert line["estimate_line"]["resource_role_id"] == CABLE_FITTER
    assert line["estimate_line"]["resource_role_label"] == "Monteur câbleur"
    assert {**line["estimate_line"], "resource_role_id": None, "resource_role_label": None} == {
        **read[ON_SITE]["estimate_line"],
        "resource_role_id": None,
        "resource_role_label": None,
    }
    # The task and its successor redated; the tasks without a successor, their float alone.
    above = numbered(redated["ancestors"])
    moved = numbered(redated["rescheduled"])
    assert read[MOUNTING]["task"]["finish"]["date"] == "2026-12-18"
    assert above[MOUNTING]["task"]["finish"]["date"] >= "2027"
    assert moved[MOUNTING]["finish"] == above[MOUNTING]["task"]["finish"]
    assert read[COMMISSIONING]["task"]["start"]["date"] < "2027"
    assert moved[COMMISSIONING]["start"]["date"] >= "2027"
    for number in (DESIGN_FILE, 542, 544):
        assert moved[number]["start"] == read[number]["task"]["start"]
    # Its line consumed a year later, corrected anew at the inflation of the witness, and the
    # commissioning, which sums it; the mounting, still started in 2026, keeps its lines' year.
    amounts = {int(entry["node_id"][-3:]): entry for entry in redated["reinflated"]}
    assert list(amounts) == [COMMISSIONING, COMMISSIONING_LINE]
    was = read[COMMISSIONING_LINE]["estimate_line"]
    assert amounts[COMMISSIONING_LINE]["consumption_year"] == 2027
    assert money(amounts[COMMISSIONING_LINE]["inflated_amount"]) == mockstructure.inflated(
        money(was["base_amount"]), 2027
    )
    assert amounts[COMMISSIONING]["consumption_year"] is None
    assert (
        amounts[COMMISSIONING]["inflated_amount"] == amounts[COMMISSIONING_LINE]["inflated_amount"]
    )
    delta = money(amounts[COMMISSIONING_LINE]["inflated_amount"]) - money(was["inflated_amount"])
    assert money(above[INSTALLATION]["task"]["inflated_amount"]) == (
        money(read[INSTALLATION]["task"]["inflated_amount"]) + delta
    )
    assert money(redated["totals"]["inflated_amount"]) == (
        money(whole["totals"]["inflated_amount"]) + delta
    )
    assert redated["totals"]["base_amount"] == whole["totals"]["base_amount"]


def test_a_label_entered_on_the_volume_changes_nothing_else(answer: dict[str, Any]) -> None:
    entered = write("estimate_line_entered")
    read = by_id(answer["items"])
    [line] = entered["nodes"]
    assert line["estimate_line"]["label"] == mockwrites.ENTERED
    assert {
        **line,
        "lock_version": 1,
        "estimate_line": {**line["estimate_line"], "label": "x"},
    } == {
        **read[mockwrites.LINE_4],
        "estimate_line": {**read[mockwrites.LINE_4]["estimate_line"], "label": "x"},
    }
    assert [node["row_number"] for node in entered["ancestors"]] == [1, 2, 3]
    assert all(node == read[node["node_id"]] for node in entered["ancestors"])
    assert entered["totals"] == answer["totals"]
    assert entered["structure_lock_version"] == 3


def test_a_block_is_planned_by_the_categories_and_roles_the_reference_names() -> None:
    assert mockwrites.paste_plan(mockwrites.BLOCK, universe(971)) == {
        "paste_id": universe(971),
        "accepted": 3,
        "rejected": [],
    }
    assert mockwrites.paste_plan(mockwrites.UNKNOWN_CATEGORY, universe(972))["rejected"] == [
        {"row": 1, "column": "cost_category", "code": "UNKNOWN_COST_CATEGORY"}
    ]
    unknown_role = [("Heures", "Ingénierie électrique", "Soudeur", "1")]
    assert mockwrites.paste_plan(unknown_role, universe(972)) == {
        "paste_id": universe(972),
        "accepted": 0,
        "rejected": [{"row": 0, "column": "resource_role", "code": "UNKNOWN_RESOURCE_ROLE"}],
    }


def test_a_block_applied_writes_its_rows_and_their_amounts_climb_to_the_totals(
    answer: dict[str, Any],
) -> None:
    applied = write("paste_applied")
    read = by_id(answer["items"])
    rows = applied["nodes"]
    assert [node["row_number"] for node in rows] == [4, 5, 6]
    assert [node["estimate_line"]["label"] for node in rows] == [row[0] for row in mockwrites.BLOCK]
    third = rows[2]["estimate_line"]
    was = read[rows[2]["node_id"]]["estimate_line"]
    assert (was["quantity"], third["quantity"]) == ("16", "24")
    assert money(third["base_amount"]) == 24 * money(third["unit_disbursement"])
    assert third["reestimated_amount"] == third["base_amount"]
    assert third["budgeted_amount"] == was["budgeted_amount"]
    delta = money(third["base_amount"]) - money(was["base_amount"])
    for node in applied["ancestors"]:
        old = read[node["node_id"]]["task"]
        assert money(node["task"]["reestimated_amount"]) == money(old["reestimated_amount"]) + delta
        assert node["task"]["budgeted_amount"] == old["budgeted_amount"]
    assert money(applied["totals"]["base_amount"]) == money(answer["totals"]["base_amount"]) + delta
    assert applied["totals"]["budgeted_amount"] == answer["totals"]["budgeted_amount"]


def test_a_block_too_wide_is_refused_by_the_width_of_a_line_in_the_contract() -> None:
    columns = mockwrites.node_columns()
    assert (columns[0], columns[-1]) == ("label", "previous_reestimated_amount")
    # Its label and sixteen columns, the quantities of the previous review among them (#424).
    assert mockwrites.line_width(columns) == 17
    assert mockwrites.paste_too_wide()["params"] == {"max_columns": 17}
    text = "Other:\n  enum: [a]\nNodeColumn:\n  type: string\n  enum:\n    - label\n    - work\n"
    text += "    - cost_category\n    - hours\nNext:\n"
    assert mockwrites.node_columns(text) == ["label", "work", "cost_category", "hours"]
    assert mockwrites.line_width(mockwrites.node_columns(text)) == 3


def test_a_re_estimate_that_completes_its_task_undated_is_refused_naming_the_task() -> None:
    # #458: the date of completion the validation asks for, missing; the task named, by field.
    refused = mockwrites.completion_date_required()
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    assert refused["fields"] == [
        {
            "pointer": "/completed_on",
            "code": "COMPLETION_DATE_REQUIRED",
            "params": {"task_node_id": universe(552)},
        }
    ]
    # The task named is the one that bears the labour line set to nothing, the wiring.
    labour = next(row for row in mockcore.core() if row.number == mockwitness.LABOUR)
    assert labour.parent == 552
    assert labour.node["parent_id"] == universe(552)
    # The contract cites the example under the 422 of setLineRemaining.
    paths = (REPOSITORY / "docs" / "api" / "paths" / "revisions.yaml").read_text(encoding="utf-8")
    operation = paths[paths.index("operationId: setLineRemaining") :]
    operation = operation[: operation.index("operationId:", len("operationId:"))]
    refused = operation[operation.index("'422':") :]
    assert "fixtures/api/remaining_completion_date_required.json" in refused


def test_every_write_is_an_example_the_contract_cites() -> None:
    contract = (REPOSITORY / "docs" / "api" / "paths" / "revisions.yaml").read_text(
        encoding="utf-8"
    )
    for name in mockwrites.writes():
        assert f"fixtures/api/{name} }}" in contract, name
    assert set(mockwrites.writes()) <= set(mockdata.named())


def test_a_loop_of_links_cannot_be_dated_and_the_tasks_left_are_named() -> None:
    # A loop down the plan, between the mounting and the commissioning: the studies and the
    # control station are dated, the two tasks of the loop are named, not the first task.
    looped = mockwrites.amended(
        CORE,
        mockwrites.on_task(
            MOUNTING, links=(mockwitness.Link(MILESTONE), mockwitness.Link(COMMISSIONING))
        ),
    )
    with pytest.raises(
        ValueError,
        match=r"among the tasks left undated: Montage des armoires sur site, Mise en service$",
    ):
        mockcore.schedule(looped)


def test_a_reestimation_follows_the_figures_entered_and_leaves_the_budget(
    whole: dict[str, Any],
) -> None:
    # 12.5 hours re-estimated at 10: 10 x 80, the budget the reference's (WF-RAE-0040).
    reestimated = write("remaining_reestimated")
    [line] = reestimated["nodes"]
    assert line["estimate_line"]["hours"] == "10"
    assert line["estimate_line"]["reestimated_amount"] == "800.00"
    assert line["estimate_line"]["budgeted_amount"] == "1000.00"
    assert sorted(numbered(reestimated["ancestors"])) == [CONTROL_STATION, WIRING]
    totals = reestimated["totals"]
    assert money(totals["reestimated_amount"]) == money(whole["totals"]["reestimated_amount"]) - 200
    assert totals["budgeted_amount"] == whole["totals"]["budgeted_amount"]
