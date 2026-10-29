# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the gestures of the estimate made on the amendment 2, and of their refusals (#1214).

As those of the other writes of the grids, they try the simplifications of the fake back against
the readings of the witness, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un
test qui ne couvre aucune exigence »).
"""

import json
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockamendment, mockamendmentwrites, mockcore, mockwitness
from wftools.mockgestures import network_task
from wftools.mockwitness import N

type Node = dict[str, Any]

own = mockamendment.own_id
WRITES = ("estimate_line_created", "estimate_line_created_after_subtask", "nodes_moved")


def _json(value: Any) -> Any:
    return json.loads(json.dumps(value))


def gesture(name: str) -> dict[str, Any]:
    """Return the answer of a gesture, read back from the text the generator writes."""
    return cast("dict[str, Any]", _json(getattr(mockamendmentwrites, name)()))


@pytest.fixture(scope="module")
def read() -> dict[str, Node]:
    """Read the whole differential today, marked, by the identifier of its nodes."""
    return {node["node_id"]: node for node in _json(mockamendment.marked())}


@pytest.fixture(scope="module")
def totals() -> dict[str, Any]:
    return cast("dict[str, Any]", _json(mockamendmentwrites.reading())["totals"])


def _summary(name: str) -> str:
    return str(mockamendmentwrites.examples()[f"{name}.json"]["summary"])


def test_the_gestures_of_the_estimate_write_the_amendment_and_not_the_main_structure(
    read: dict[str, Node],
) -> None:
    # #1214: the grid of estimate of the main structure of a project in progress offers no entry
    # (Vérif of WF-DEV-0050, ``structures``): the lines created and moved are the differential's,
    # named by its own identifiers, its counter one version further.
    main = {cast("str", row.node["node_id"]) for row in mockcore.current()}
    amendment = _json(mockamendment.structure("amendment"))
    principal = _json(mockamendment.structure("main"))
    assert {"command": "edit_estimate", "is_available": True, "missing_conditions": []} in (
        amendment["available_commands"]
    )
    assert {"command": "edit_estimate", "is_available": True, "missing_conditions": []} not in (
        principal["available_commands"]
    )
    for name in WRITES:
        written = gesture(name)
        for node in [*written["nodes"], *written["ancestors"]]:
            assert node["node_id"] not in main, (name, node["node_id"])
            assert node["parent_id"] is None or node["parent_id"] in read, name
        assert written["structure_lock_version"] == amendment["lock_version"] + 1, name
        assert str(amendment["label"]) in _summary(name)


def test_a_line_created_on_the_amendment_is_added_and_climbs_to_its_ancestors(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    # Its quantities are the reference ones the amendment bears, its budget its amount, as the
    # rework of the trials; it is added to the main structure, and has no previous review.
    created = gesture("estimate_line_created")
    [line] = created["nodes"]
    facet = line["estimate_line"]
    assert (line["node_id"], line["lock_version"], line["parent_id"]) == (
        own(mockamendmentwrites.CREATED_LINE),
        1,
        own(N.COMMISSIONING),
    )
    assert (line["difference"], line["changes"]) == ("added", [])
    assert facet["base_amount"] == facet["budgeted_amount"] == "350.00"
    assert {key: facet[key] for key in mockcore.PREVIOUS} == dict.fromkeys(mockcore.PREVIOUS)
    above = [node["node_id"] for node in created["ancestors"]]
    assert above == [own(N.INSTALLATION), own(N.SITE_TESTS), own(N.COMMISSIONING)]
    for node in created["ancestors"]:
        was = read[node["node_id"]]["task"]
        assert Decimal(node["task"]["base_amount"]) == Decimal(was["base_amount"]) + 350
    assert created["totals"]["estimate_line_count"] == totals["estimate_line_count"] + 1
    assert Decimal(created["totals"]["base_amount"]) == Decimal(totals["base_amount"]) + 350


def test_a_line_sent_after_a_subordinate_goes_after_the_last_line_of_its_task(
    read: dict[str, Node],
) -> None:
    # The lines of a task precede its subordinates (#1187): a line that names a subordinate to
    # follow falls back on the boundary, after the last line — here the first child of the
    # station, which bears none, and the row right under it, before the wiring of the cabinets.
    after = read[own(mockamendmentwrites.SHARED_AFTER)]
    station = read[own(mockamendmentwrites.SHARED_UNDER)]
    assert (after["parent_id"], after["kind"]) == (station["node_id"], "task")
    assert not mockwitness.CONTROL_STATION.lines
    [line] = gesture("estimate_line_created_after_subtask")["nodes"]
    assert (line["node_id"], line["kind"], line["parent_id"]) == (
        own(mockamendmentwrites.CREATED_SHARED),
        "estimate_line",
        station["node_id"],
    )
    assert (line["position"], line["row_number"]) == (1, station["row_number"] + 1)
    assert line["row_number"] == read[own(N.WIRING)]["row_number"]


def test_a_selection_moved_changes_the_task_that_bears_its_lines_and_nothing_else(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    moved = gesture("nodes_moved")
    source = own(network_task(mockamendmentwrites.MOVED_FROM).number)
    target = own(network_task(mockamendmentwrites.MOVED_TO).number)
    lines = moved["nodes"]
    labels = [line["estimate_line"]["label"] for line in lines]
    assert labels == list(mockamendmentwrites.MOVED_LINES)
    sum_moved = Decimal(0)
    for line in lines:
        was = read[line["node_id"]]
        assert (was["parent_id"], line["parent_id"]) == (source, target)
        assert line["lock_version"] == was["lock_version"] + 1
        assert (line["difference"], line["changes"]) == ("modified", ["parent"])
        assert line["estimate_line"] == was["estimate_line"]
        sum_moved += Decimal(line["estimate_line"]["base_amount"])
    above = {node["node_id"]: node for node in moved["ancestors"]}
    assert {source, target} <= set(above)
    assert Decimal(above[source]["task"]["base_amount"]) == (
        Decimal(read[source]["task"]["base_amount"]) - sum_moved
    )
    assert Decimal(above[target]["task"]["base_amount"]) == (
        Decimal(read[target]["task"]["base_amount"]) + sum_moved
    )
    assert (moved["rescheduled"], moved["reinflated"]) == ([], [])
    assert moved["totals"] == totals


def test_the_mixed_selection_of_the_contract_is_placed_by_the_rule(read: dict[str, Node]) -> None:
    # The body of the example: a line and a task moved under the station after the wiring, on the
    # amendment 2, whose estimate is open; the line goes first of its lines, which it has none,
    # the task right after the wiring (#1188).
    body = gesture("nodes_move_mixed")
    assert body["node_ids"] == [own(number) for number, _ in mockamendmentwrites.MIXED]
    assert (body["parent_id"], body["after_node_id"]) == (
        own(mockamendmentwrites.MIXED_UNDER),
        own(mockamendmentwrites.MIXED_AFTER),
    )
    assert read[body["after_node_id"]]["parent_id"] == body["parent_id"]
    assert [read[each]["kind"] for each in body["node_ids"]] == ["estimate_line", "task"]
    lines, tasks = mockamendmentwrites.mixed_places()
    assert lines == [N.BLOCKS]
    assert tasks[: tasks.index(N.TRANSPORT) + 1] == [N.WIRING, N.TRANSPORT]
    assert body["lock_version"] == mockamendment.structure("amendment")["lock_version"]


REFUSED = ("estimate_line_completed_refused", "nodes_move_completed_refused")


@pytest.mark.parametrize("name", REFUSED)
def test_a_line_written_under_a_completed_task_is_refused_naming_the_condition(
    read: dict[str, Node], name: str
) -> None:
    # WF-DEV-0050, WF-RAE-0030: « La création d'une ligne sous une tâche terminée, ou le
    # déplacement d'une ligne vers elle, est refusé » — a task completed is reopened from the
    # Kanban first (#1184, #1214).
    refused = gesture(name)
    assert (refused["code"], refused["status"]) == ("STATE_FORBIDS_OPERATION", 409)
    assert refused["params"] == {"missing_condition": "task_not_completed"}
    task = read[own(mockamendmentwrites.COMPLETED_UNDER)]["task"]
    assert task["progress"] == "completed"
    assert str(task["label"]) in _summary(name)


def test_the_line_moved_to_a_completed_task_comes_from_a_task_that_is_not(
    read: dict[str, Node],
) -> None:
    # The refusal is the target's: the blocks are under the wiring, not completed.
    line = read[own(mockamendmentwrites.COMPLETED_MOVED)]
    assert line["kind"] == "estimate_line"
    assert read[line["parent_id"]]["task"]["progress"] != "completed"
    correlations = {gesture(name)["correlation_id"] for name in REFUSED}
    assert len(correlations) == len(REFUSED)


def test_a_deletion_sent_with_a_stale_counter_names_the_counter_the_move_left(
    read: dict[str, Node],
) -> None:
    # #1210: a line of the amendment 2, read at its version, then moved with the selection — a
    # write the grid of a differential offers, whatever the state of the project (WF-DEV-0050).
    [line] = [
        node
        for node in gesture("nodes_moved")["nodes"]
        if node["estimate_line"]["label"] == mockamendmentwrites.MOVED_LINES[0]
    ]
    stale = gesture("node_delete_stale")
    assert (stale["code"], stale["status"]) == ("STALE_LOCK_VERSION", 412)
    assert stale["params"] == {"expected_lock_version": line["lock_version"]}
    assert read[line["node_id"]]["lock_version"] < line["lock_version"]
    assert mockamendmentwrites.MOVED_LINES[0] in _summary("node_delete_stale")


def test_the_hours_entered_on_the_amendment_rewrite_its_line_and_climb_to_its_ancestors(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    # #1277: the cell the journeys enter on the amendment answers the line of the amendment, at
    # the address of the differential. Its budget follows its quantities on a differential, which
    # the merge draws its budget from (WF-REV-0050); no date moves.
    updated = gesture("estimate_line_updated_amendment")
    [line] = updated["nodes"]
    was = read[own(mockamendmentwrites.ENTERED_LINE)]
    assert (line["node_id"], line["lock_version"]) == (was["node_id"], was["lock_version"] + 1)
    facet = line["estimate_line"]
    assert Decimal(facet["hours"]) == mockamendmentwrites.ENTERED_HOURS
    grown = Decimal(facet["base_amount"]) - Decimal(was["estimate_line"]["base_amount"])
    assert grown > 0
    assert facet["budgeted_amount"] == facet["base_amount"]
    assert [node["node_id"] for node in updated["ancestors"]] == [
        own(N.INSTALLATION),
        own(N.SITE_TESTS),
        own(N.TESTS_RESUMED),
    ]
    assert (updated["rescheduled"], updated["reinflated"]) == ([], [])
    assert Decimal(updated["totals"]["base_amount"]) == Decimal(totals["base_amount"]) + grown
    amendment = _json(mockamendment.structure("amendment"))
    assert updated["structure_lock_version"] == amendment["lock_version"] + 1


def test_the_payment_delay_entered_on_a_labour_line_changes_neither_amount_nor_date(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    # #785: the payment delay is « saisissable sur toute ligne autre qu'une ligne de provision »
    # (WF-DEV-0020), labour included: the line names it among the fields it accepts, and the
    # entry rewrites the delay alone, one version further, no amount and no date moving.
    delayed = gesture("estimate_line_payment_delay_amendment")
    [line] = delayed["nodes"]
    was = read[own(mockamendmentwrites.DELAYED_LINE)]
    assert was["estimate_line"]["resource_role_id"] is not None
    assert "estimate_line.payment_delay_days" in was["editable_fields"]
    assert (line["node_id"], line["lock_version"]) == (was["node_id"], was["lock_version"] + 1)
    facet, before = line["estimate_line"], was["estimate_line"]
    assert (before["payment_delay_days"], facet["payment_delay_days"]) == (
        0,
        mockamendmentwrites.DELAYED_DAYS,
    )
    assert {key for key in facet if facet[key] != before[key]} == {"payment_delay_days"}
    assert (delayed["rescheduled"], delayed["reinflated"]) == ([], [])
    assert delayed["totals"] == totals
    for name in ("estimate_line_updated_amendment", "paste_applied_amendment"):
        written = {node["node_id"] for node in gesture(name)["nodes"]}
        assert line["node_id"] not in written, name


def test_the_block_pasted_on_the_amendment_writes_the_rows_under_its_line_in_the_grid() -> None:
    # #1277: the rows of the block write the rows of the grid at the same distance under the line
    # pasted on, as the installation is read on the differential (`nodes_amendment`): the rows 7
    # to 9 of its reading, the line the amendment adds, the commissioning and its line.
    items = _json(mockamendment.nodes_amendment())["items"]
    rows = [node["node_id"] for node in items[6:9]]
    assert rows == [own(number) for number in mockamendmentwrites.paste_targets()]
    assert rows[0] == own(mockamendmentwrites.ENTERED_LINE)
    assert [node["kind"] for node in items[6:9]] == ["estimate_line", "task", "estimate_line"]
    plan = gesture("paste_plan_amendment")
    assert (plan["accepted"], plan["rejected"]) == (3, [])
    assert plan["paste_id"] != _json(mockwitness.fixture("paste_plan"))["paste_id"]


def test_a_block_refused_in_part_names_each_cell_and_is_never_applied() -> None:
    # A cell past the label of the task falls on a column it does not accept; on a line, a
    # category, then a role, the reference data does not name (WF-IHM-0050). Such a block is
    # previewed, never applied: the generator refuses to write its answer.
    first, task, last = mockamendmentwrites.AMENDMENT_BLOCK
    block = (
        (first[0], "Catégorie inconnue", first[2], first[3]),
        (task[0], "", "", "4"),
        (last[0], last[1], "Rôle inconnu", last[3]),
    )
    plan = _json(mockamendmentwrites.paste_plan_amendment(block))
    assert plan["rejected"] == [
        {"row": 0, "column": "cost_category", "code": "UNKNOWN_COST_CATEGORY"},
        {"row": 1, "column": "quantity", "code": "FIELD_NOT_ACCEPTED"},
        {"row": 2, "column": "resource_role", "code": "UNKNOWN_RESOURCE_ROLE"},
    ]
    assert plan["accepted"] == 0
    with pytest.raises(ValueError, match="refused in part"):
        mockamendmentwrites.paste_applied_amendment(block)


def test_a_block_of_another_length_writes_as_many_rows_and_is_judged_by_them() -> None:
    # #1296: the nodes written are cut on the block pasted, not on the block of the example; a
    # shorter block is judged and applied, a refused one names its cell, never a bare zip error.
    first, task, _ = mockamendmentwrites.AMENDMENT_BLOCK
    two = mockamendmentwrites.paste_targets(2)
    assert two == mockamendmentwrites.paste_targets()[:2]
    plan = _json(mockamendmentwrites.paste_plan_amendment((first, task)))
    assert (plan["accepted"], plan["rejected"]) == (2, [])
    applied = _json(mockamendmentwrites.paste_applied_amendment((first, task)))
    assert [node["node_id"] for node in applied["nodes"]] == [own(number) for number in two]
    unknown = ((first[0], "Catégorie inconnue", first[2], first[3]),)
    refused = _json(mockamendmentwrites.paste_plan_amendment(unknown))
    assert refused["rejected"] == [
        {"row": 0, "column": "cost_category", "code": "UNKNOWN_COST_CATEGORY"}
    ]
    assert refused["accepted"] == 0


def test_the_block_pasted_on_the_amendment_follows_the_hours_entered() -> None:
    # #421: the paste reads the line at the version the entry left, and leaves the structure one
    # version further still; a node written is not among the ancestors (`NodesWritten`).
    updated = gesture("estimate_line_updated_amendment")
    applied = gesture("paste_applied_amendment")
    versions = {node["node_id"]: node["lock_version"] for node in applied["nodes"]}
    [line] = updated["nodes"]
    assert versions == {
        line["node_id"]: line["lock_version"] + 1,
        own(N.COMMISSIONING): 2,
        own(N.COMMISSIONING_LINE): 2,
    }
    assert applied["structure_lock_version"] == updated["structure_lock_version"] + 1
    assert not set(versions) & {node["node_id"] for node in applied["ancestors"]}
    labels = [node[node["kind"]]["label"] for node in applied["nodes"]]
    assert labels == [row[0] for row in mockamendmentwrites.AMENDMENT_BLOCK]
    pasted = applied["nodes"][0]["estimate_line"]
    assert (pasted["quantity"], pasted["hours"]) == ("2", line["estimate_line"]["hours"])
    assert applied["rejected"] == []


def test_a_block_that_covers_a_line_withdrawn_skips_it_and_writes_the_node_after_it() -> None:
    # #1278, decision of the author: a paste that covers nodes withdrawn from a differential
    # skips them and fills the next ones, without refusal. The wiring on site precedes the line
    # the amendment withdraws, read only at its row; the second row writes the trials on site.
    items = _json(mockamendment.nodes_amendment())["items"]
    ids = [node["node_id"] for node in items]
    start = ids.index(own(mockamendmentwrites.SKIPPING_TARGET))
    covered = items[start : start + 3]
    assert [node["difference"] for node in covered] == ["unchanged", "removed", "added"]
    targets = mockamendmentwrites.paste_targets(2, mockamendmentwrites.SKIPPING_TARGET)
    assert [own(number) for number in targets] == [covered[0]["node_id"], covered[2]["node_id"]]
    plan = gesture("paste_plan_amendment_skipping")
    assert (plan["accepted"], plan["rejected"]) == (2, [])
    assert plan["paste_id"] != gesture("paste_plan_amendment")["paste_id"]
    applied = gesture("paste_applied_amendment_skipping")
    written = [node["node_id"] for node in applied["nodes"]]
    assert written == [covered[0]["node_id"], covered[2]["node_id"]]
    assert covered[1]["node_id"] not in written
    assert covered[1]["node_id"] not in {node["node_id"] for node in applied["ancestors"]}
    labels = [node[node["kind"]]["label"] for node in applied["nodes"]]
    assert labels == [row[0] for row in mockamendmentwrites.SKIPPING_BLOCK]
    assert applied["nodes"][0]["estimate_line"]["quantity"] == "2"
    assert [node["lock_version"] for node in applied["nodes"]] == [2, 2]
    amendment = _json(mockamendment.structure("amendment"))
    assert applied["structure_lock_version"] == amendment["lock_version"] + 1
    assert applied["rejected"] == []
    assert covered[1]["estimate_line"]["label"] in _summary("paste_applied_amendment_skipping")


def test_every_task_read_on_the_amendment_accepts_its_predecessors_but_one_removed() -> None:
    # #1257: the cell of the predecessors follows `editable_fields`, as every other cell; a node
    # removed from a differential is read only.
    for node in _json(mockamendment.nodes_amendment())["items"]:
        accepts = "task.predecessors" in node["editable_fields"]
        assert accepts == (node["kind"] == "task" and node["difference"] != "removed"), node


@pytest.mark.requirement("WF-DEV-0020-A")
def test_the_label_composed_for_a_line_is_cut_at_the_length_of_a_label() -> None:
    # « À la création d'une ligne, Waterfall compose son libellé à partir de celui de la tâche qui
    # la porte et, s'il existe, de celui de son rôle de ressource » : within 300 characters.
    assert mockamendmentwrites.composed_label("Mise en service", "Technicien") == (
        "Mise en service — Technicien"
    )
    assert mockamendmentwrites.composed_label("Mise en service", None) == "Mise en service"
    long = mockamendmentwrites.composed_label("T" * 250, "R" * 100)
    assert len(long) == mockamendmentwrites.LABEL_LENGTH == 300
    assert long == "T" * 250 + " — " + "R" * 47
