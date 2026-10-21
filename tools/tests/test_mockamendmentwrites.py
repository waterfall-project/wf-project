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
