# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the answers of the gestures of the structure and of the entries of a task (K3).

As those of the other writes of the grids, they try the simplifications of the fake back against
the readings of the witness, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un
test qui ne couvre aucune exigence »).
"""

import itertools
import json
import re
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockcore, mockdata, mockgestures, mockwitness, mockwrites
from wftools.mockids import universe
from wftools.mockstructure import described
from wftools.mockwitness import CORE, CUSTOMER, Link, N

type Node = dict[str, Any]


def _json(value: Any) -> Any:
    return json.loads(json.dumps(value))


def gesture(name: str) -> dict[str, Any]:
    """Return the answer of a gesture, read back from the text the generator writes."""
    return cast("dict[str, Any]", _json(getattr(mockgestures, name)()))


@pytest.fixture(scope="module")
def read() -> dict[str, Node]:
    """Read the whole structure today, by the identifier of its nodes."""
    whole = _json(mockcore.whole(mockcore.current()))
    return {node["node_id"]: node for node in whole["items"]}


@pytest.fixture(scope="module")
def totals() -> dict[str, Any]:
    return cast("dict[str, Any]", _json(mockcore.whole(mockcore.current()))["totals"])


def by_number(nodes: list[Node]) -> dict[str, Node]:
    return {node["node_id"]: node for node in nodes}


def money(value: str) -> Decimal:
    return Decimal(value)


# --- The contract cites each example under its operation ----------------------------------------


OPERATIONS = {
    "createNode": ("201", ["node_created", "node_created_child", "estimate_line_created"]),
    "deleteNode": ("200", ["node_summary_deleted"]),
    "moveNodes": ("200", ["nodes_moved", "nodes_indented"]),
    "setNodeTracking": ("200", ["node_tracked"]),
}
REFUSALS = {
    "createNode": ["node_create_horizon_exceeded"],
    "updateTaskFacet": ["task_date_computed_refused", "task_horizon_exceeded"],
    "setPredecessors": [
        "predecessors_cycle_refused",
        "predecessors_forbidden",
        "predecessors_horizon_exceeded",
    ],
}


def _operation(name: str) -> str:
    text = (REPOSITORY / "docs" / "api" / "paths" / "revisions.yaml").read_text(encoding="utf-8")
    operation = text[text.index(f"operationId: {name}") :]
    return operation[: operation.index("operationId:", len("operationId:"))]


def _cited(text: str) -> list[str]:
    return re.findall(r"fixtures/api/(\w+)\.json", text)


def test_every_gesture_is_an_example_the_contract_cites_under_its_answer() -> None:
    examples = mockgestures.examples()
    cited: set[str] = set()
    for operation, (status, names) in OPERATIONS.items():
        text = _operation(operation)
        success = text[text.index(f"'{status}':") : text.index("'401':")]
        assert set(names) <= set(_cited(success)), operation
        cited |= set(names)
    for operation, names in REFUSALS.items():
        text = _operation(operation)
        assert set(names) <= set(_cited(text[text.index("'422':") :])), operation
        cited |= set(names)
    facet = _operation("updateTaskFacet")
    entries = _cited(facet[facet.index("'200':") : facet.index("'401':")])
    linked = _operation("setPredecessors")
    cited |= {name for name in entries if f"{name}.json" in examples}
    cited |= {
        name for name in _cited(linked[: linked.index("'401':")]) if f"{name}.json" in examples
    }
    assert {f"{name}.json" for name in cited} == set(examples)
    assert set(examples) <= set(mockdata.named())


# --- The structure created, moved, deleted -----------------------------------------------------


def test_a_task_created_beside_another_is_an_automatic_leaf_of_one_day_not_started(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    # Its label alone sent (WF-DEV-0050): a leaf in automatic mode, of one day, without a
    # predecessor, starting at the planning start, not started; at its first version, last of
    # the studies, after the design file. Its summary renders as the reading gives it.
    created = gesture("node_created")
    [task] = created["nodes"]
    assert (task["node_id"], task["lock_version"]) == (universe(mockgestures.CREATED), 1)
    assert (task["parent_id"], task["position"]) == (
        universe(N.STUDIES),
        read[universe(N.DESIGN_FILE)]["position"] + 1,
    )
    assert task["row_number"] == read[universe(N.DESIGN_FILE)]["row_number"] + 1
    facet = task["task"]
    assert facet["scheduling_mode"] == "automatic"
    assert facet["duration"] == {"value": "1", "unit": "d"}
    assert facet["start"]["date"] == mockgestures.project_start().isoformat()
    assert (facet["progress"], facet["is_summary"]) == ("not_started", False)
    assert "predecessors" not in task
    [summary] = created["ancestors"]
    assert summary == read[universe(N.STUDIES)]
    assert created["totals"]["task_count"] == totals["task_count"] + 1
    assert created["structure_lock_version"] == 2


def test_a_task_created_under_a_leaf_makes_it_its_summary(read: dict[str, Node]) -> None:
    # It follows the creation of the leaf (#421): the leaf becomes a summary, its dates its one
    # subordinate's, and takes neither its mode nor its duration any more (WF-PLA-0040).
    child = gesture("node_created_child")
    [task] = child["nodes"]
    assert (task["lock_version"], task["parent_id"]) == (1, universe(mockgestures.CREATED))
    above = by_number(child["ancestors"])
    leaf = above[universe(mockgestures.CREATED)]
    assert leaf["task"]["is_summary"] is True
    assert (leaf["task"]["start"], leaf["task"]["finish"]) == (
        task["task"]["start"],
        task["task"]["finish"],
    )
    assert {"task.scheduling_mode", "task.duration"}.isdisjoint(leaf["editable_fields"])
    assert "task.duration" in leaf["computed_fields"]
    assert above[universe(N.STUDIES)] == read[universe(N.STUDIES)]
    assert child["structure_lock_version"] == 3
    [created] = gesture("node_created")["nodes"]
    place = ("node_id", "parent_id", "position", "row_number", "level", "lock_version")
    assert [leaf[key] for key in place] == [created[key] for key in place]


def test_a_line_created_after_the_reference_has_no_budget(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    # A line added after the reference has a budget nil (WF-RAE-0050); its amount climbs to its
    # task and its summary, and to the totals; it has no previous review.
    created = gesture("estimate_line_created")
    [line] = created["nodes"]
    facet = line["estimate_line"]
    assert (line["lock_version"], line["parent_id"]) == (1, universe(N.COMMISSIONING))
    assert (facet["base_amount"], facet["budgeted_amount"]) == ("350.00", "0.00")
    assert {key: facet[key] for key in mockcore.PREVIOUS} == dict.fromkeys(mockcore.PREVIOUS)
    for node in created["ancestors"]:
        was = read[node["node_id"]]["task"]
        assert money(node["task"]["base_amount"]) == money(was["base_amount"]) + 350
        assert node["task"]["budgeted_amount"] == was["budgeted_amount"]
    assert created["totals"]["estimate_line_count"] == totals["estimate_line_count"] + 1
    assert money(created["totals"]["base_amount"]) == money(totals["base_amount"]) + 350
    assert created["totals"]["budgeted_amount"] == totals["budgeted_amount"]


def test_a_selection_moved_changes_the_task_that_bears_its_lines_and_nothing_else(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    moved = gesture("nodes_moved")
    source = mockwitness.node_id(mockgestures.network_task(mockgestures.MOVED_FROM).number)
    target = mockwitness.node_id(mockgestures.network_task(mockgestures.MOVED_TO).number)
    lines = moved["nodes"]
    assert [line["estimate_line"]["label"] for line in lines] == list(mockgestures.MOVED_LINES)
    sum_moved = Decimal(0)
    for line in lines:
        was = read[line["node_id"]]
        assert (was["parent_id"], line["parent_id"], line["lock_version"]) == (source, target, 2)
        assert line["estimate_line"] == was["estimate_line"]
        sum_moved += money(line["estimate_line"]["base_amount"])
    above = by_number(moved["ancestors"])
    assert {source, target} <= set(above)
    assert money(above[source]["task"]["base_amount"]) == (
        money(read[source]["task"]["base_amount"]) - sum_moved
    )
    assert money(above[target]["task"]["base_amount"]) == (
        money(read[target]["task"]["base_amount"]) + sum_moved
    )
    assert (moved["rescheduled"], moved["reinflated"]) == ([], [])
    assert moved["totals"] == totals


def test_a_task_indented_goes_under_the_task_above_it_and_nothing_moves(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    indented = gesture("nodes_indented")
    [task] = indented["nodes"]
    was = read[universe(N.INSTALLATION)]
    station = read[universe(N.CONTROL_STATION)]
    assert was["position"] == station["position"] + 1
    assert (task["parent_id"], task["level"], task["row_number"]) == (
        universe(N.CONTROL_STATION),
        was["level"] + 1,
        was["row_number"],
    )
    assert task["position"] == len(mockwitness.CONTROL_STATION.children)
    assert task["task"] == was["task"]
    [summary] = indented["ancestors"]
    assert summary["task"]["start"] == station["task"]["start"]
    assert summary["task"]["finish"] == was["task"]["finish"]
    assert money(summary["task"]["base_amount"]) == (
        money(station["task"]["base_amount"]) + money(was["task"]["base_amount"])
    )
    assert (indented["rescheduled"], indented["reinflated"], indented["totals"]) == (
        [],
        [],
        totals,
    )


def test_a_summary_deleted_takes_its_subordinates_their_lines_and_their_links(
    read: dict[str, Node], totals: dict[str, Any]
) -> None:
    # The installation, not started: the estimate diminishes by its lines (WF-PLA-0070).
    deleted = gesture("node_summary_deleted")
    installation = read[universe(N.INSTALLATION)]
    assert installation["task"]["progress"] == "not_started"
    subtree = {universe(N.INSTALLATION), universe(N.MOUNTING), universe(N.COMMISSIONING)}
    below = [node for node in read.values() if node["parent_id"] in subtree]
    tasks = [node for node in below if node["kind"] == "task"]
    lines = [node for node in below if node["kind"] == "estimate_line"]
    assert (deleted["nodes"], deleted["ancestors"]) == ([], [])
    assert deleted["totals"]["task_count"] == totals["task_count"] - 1 - len(tasks)
    assert deleted["totals"]["estimate_line_count"] == totals["estimate_line_count"] - len(lines)
    removed = sum((money(node["estimate_line"]["base_amount"]) for node in lines), Decimal(0))
    assert removed == Decimal("18600.00")
    assert money(deleted["totals"]["base_amount"]) == money(totals["base_amount"]) - removed
    # A task drawn about the core followed the commissioning: its link goes with it.
    followers = [
        node
        for node in read.values()
        if any(
            link["predecessor_node_id"] == universe(N.COMMISSIONING)
            for link in node.get("predecessors", [])
        )
    ]
    assert followers
    assert deleted["structure_lock_version"] == 2


# --- The entries of a task --------------------------------------------------------------------


def test_a_task_put_in_manual_mode_keeps_its_dates_and_bounds_its_predecessor(
    read: dict[str, Node],
) -> None:
    # The dates it had are now entered (WF-PLA-0020): no float, its dates accepted; the mounting
    # before it is bound by the date imposed, and becomes critical (WF-PLA-0100).
    manual = gesture("task_mode_changed")
    [task] = manual["nodes"]
    was = read[universe(N.COMMISSIONING)]["task"]
    facet = task["task"]
    assert (facet["scheduling_mode"], facet["total_float"], facet["is_critical"]) == (
        "manual",
        None,
        False,
    )
    assert (facet["start"], facet["finish"], facet["duration"]) == (
        was["start"],
        was["finish"],
        was["duration"],
    )
    assert {"task.start", "task.finish"} <= set(task["editable_fields"])
    assert task["computed_fields"] == []
    [mounting] = manual["rescheduled"]
    assert mounting["node_id"] == universe(N.MOUNTING)
    assert (mounting["total_float"]["value"], mounting["is_critical"]) == ("0", True)
    assert read[universe(N.MOUNTING)]["task"]["is_critical"] is False


def test_dates_entered_on_a_manual_task_follow_the_mode_changed(read: dict[str, Node]) -> None:
    dated = gesture("task_dates_entered")
    [task] = dated["nodes"]
    first, last = mockgestures.ENTERED_DATES
    assert (task["task"]["start"]["date"], task["task"]["finish"]["date"]) == (
        first.isoformat(),
        last.isoformat(),
    )
    [manual] = gesture("task_mode_changed")["nodes"]
    assert (task["lock_version"], dated["structure_lock_version"]) == (
        manual["lock_version"] + 1,
        3,
    )
    [line] = dated["reinflated"]
    assert (line["node_id"], line["consumption_year"]) == (universe(N.COMMISSIONING_LINE), 2027)
    assert read[universe(N.COMMISSIONING_LINE)]["estimate_line"]["consumption_year"] == 2026
    [mounting] = dated["rescheduled"]
    assert Decimal(mounting["total_float"]["value"]) > 0


def test_a_duration_entered_in_weeks_is_kept_in_its_unit(read: dict[str, Node]) -> None:
    duration = gesture("task_duration_entered")
    [task] = duration["nodes"]
    was = read[task["node_id"]]["task"]
    days, unit = mockgestures.ENTERED_DURATION
    assert task["task"]["duration"] == {"value": str(days), "unit": unit}
    assert was["duration"] == {"value": "10", "unit": "d"}
    assert task["task"]["finish"]["date"] > was["finish"]["date"]
    assert duration["rescheduled"]
    for entry in duration["rescheduled"]:
        assert read[entry["node_id"]]["task"]["progress"] == "not_started"
    assert mockwitness.Task(1, "", days=days, unit=unit) != mockwitness.Task(1, "", days=days)


def test_a_description_entered_changes_nothing_else(read: dict[str, Node]) -> None:
    entered = gesture("task_description_entered")
    [task] = entered["nodes"]
    was = read[universe(N.DESIGN_FILE)]
    assert "description" not in was["task"]
    assert task == {
        **was,
        "lock_version": 2,
        "task": {**was["task"], "description": mockgestures.DESCRIPTION},
    }


def test_a_date_sent_for_an_automatic_task_is_refused_as_computed(read: dict[str, Node]) -> None:
    refused = gesture("task_date_computed")
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    assert refused["fields"] == [{"pointer": "/finish", "code": "COMPUTED_VALUE"}]
    mounting = read[universe(N.MOUNTING)]
    assert mounting["task"]["scheduling_mode"] == "automatic"
    assert "task.finish" in mounting["computed_fields"]


def test_the_horizon_counts_fifteen_years_from_the_start_and_the_entry_names_its_task(
    read: dict[str, Node],
) -> None:
    # The finish of the desks entered fifteen years and a day after the start (WF-PLA-0150).
    assert mockgestures.project_start() == date(2026, 3, 2)
    assert mockgestures.beyond_horizon() == date(2041, 3, 3)
    refused = gesture("task_horizon_exceeded")
    assert (refused["code"], refused["status"]) == ("PROJECT_HORIZON_EXCEEDED", 422)
    desks = read[universe(N.DESKS)]
    assert desks["task"]["scheduling_mode"] == "manual"
    assert refused["params"] == {
        "task": {"node_id": desks["node_id"], "label": "Pupitres opérateurs"}
    }


# --- The predecessors and the inscriptions -----------------------------------------------------


def test_predecessors_entered_keep_their_kinds_and_the_unit_of_their_lag(
    read: dict[str, Node],
) -> None:
    entered = gesture("predecessors_entered")
    [task] = entered["nodes"]
    after = mockwitness.node_id(mockgestures.network_task(mockgestures.LINKED_AFTER).number)
    assert [
        (link["predecessor_node_id"], link["link_type"], link["lag"])
        for link in task["predecessors"]
    ] == [
        (universe(N.FACTORY_ACCEPTANCE), "finish_to_start", {"value": "0", "unit": "d"}),
        (after, "start_to_start", {"value": "1", "unit": "w"}),
    ]
    assert task["task"]["start"]["date"] > read[task["node_id"]]["task"]["start"]["date"]
    assert entered["rescheduled"]


def test_a_loop_of_links_is_refused_naming_its_tasks_in_the_order_of_the_links(
    read: dict[str, Node],
) -> None:
    refused = gesture("predecessors_cycle_refused")
    assert (refused["code"], refused["status"]) == ("LINK_CYCLE", 422)
    loop = refused["params"]["cycle"]
    assert loop[0]["node_id"] == universe(mockgestures.CYCLE_ON)
    for before, after in itertools.pairwise(loop):
        links = read[after["node_id"]]["predecessors"]
        assert before["node_id"] in {link["predecessor_node_id"] for link in links}
    sent = {universe(link.predecessor) for link in mockgestures.CYCLE_LINKS}
    assert loop[-1]["node_id"] in sent
    for each in loop:
        assert each["label"] == read[each["node_id"]]["task"]["label"]
    looped = mockwrites.amended(
        CORE, mockwrites.on_task(mockgestures.CYCLE_ON, links=mockgestures.CYCLE_LINKS)
    )
    with pytest.raises(ValueError, match="close a loop"):
        mockcore.schedule(looped)


def test_no_loop_is_found_when_no_predecessor_sent_follows_the_task() -> None:
    assert mockgestures.cycle(N.COMMISSIONING, (Link(N.MOUNTING),)) == []


def test_a_link_to_its_own_summary_is_refused_without_a_parameter(read: dict[str, Node]) -> None:
    refused = gesture("predecessors_forbidden")
    assert (refused["code"], refused["status"], "params" in refused) == (
        "LINK_FORBIDDEN",
        422,
        False,
    )
    mounting = read[universe(mockgestures.FORBIDDEN_ON)]
    sent = {universe(link.predecessor) for link in mockgestures.FORBIDDEN_LINKS}
    assert mounting["parent_id"] in sent


def _finish(roots: tuple[mockwitness.Task, ...], number: int) -> date:
    return mockcore.schedule(roots)[number].finish.day


def test_a_lag_or_a_duration_beyond_the_horizon_is_refused_naming_the_task() -> None:
    # Two hundred months of work carry the commissioning, or a task created, past fifteen
    # years from the start of the project (WF-PLA-0150).
    lag, unit = mockgestures.HORIZON_LAG
    lagged = mockwrites.amended(
        CORE,
        mockwrites.on_task(mockgestures.HORIZON_ON, links=(Link(N.MOUNTING, lag=lag, unit=unit),)),
    )
    assert _finish(lagged, mockgestures.HORIZON_ON) > mockgestures.beyond_horizon()
    refused = gesture("predecessors_horizon_exceeded")
    assert refused["params"]["task"]["node_id"] == universe(mockgestures.HORIZON_ON)
    days, unit = mockgestures.CREATED_DURATION
    beyond = mockwitness.Task(599, mockgestures.CREATED_BEYOND, days=days, unit=unit)
    created = mockwrites.amended(CORE, mockgestures.added(N.INSTALLATION, child=beyond))
    assert _finish(created, 599) > mockgestures.beyond_horizon()
    assert gesture("node_create_horizon_exceeded")["params"] == {
        "task": {"node_id": None, "label": mockgestures.CREATED_BEYOND}
    }


def test_a_task_inscribed_to_a_timeline_renders_its_inscriptions(read: dict[str, Node]) -> None:
    tracked = gesture("node_tracked")
    [task] = tracked["nodes"]
    was = read[universe(mockgestures.TRACKED_TASK)]
    assert "tracking" not in was["task"]
    assert task["task"]["tracking"] == [{"kind": "timeline", "timeline_id": CUSTOMER}]
    assert {**task["task"], "tracking": None} == {**was["task"], "tracking": None}
    assert "task.tracking" in task["editable_fields"]


def test_an_inscription_given_by_a_write_replaces_those_of_the_witness() -> None:
    acceptance = mockwrites.amended(
        described(),
        mockwrites.on_task(N.FACTORY_ACCEPTANCE, inscriptions=(mockwitness.MILESTONE_TRACKING,)),
    )
    rows = {row.number: row for row in mockcore.current(acceptance)}
    facet = cast("Node", rows[N.FACTORY_ACCEPTANCE].node["task"])
    assert facet["tracking"] == [{"kind": "milestone_tracking", "timeline_id": None}]


def test_no_gesture_moves_a_fact_already_recorded(read: dict[str, Node]) -> None:
    # The progress of a task and the days it started and completed are facts (WF-PLA-0130).
    facts = ("progress", "started_on", "completed_on")
    for name, example in mockgestures.examples().items():
        value = _json(example["value"])
        if "nodes" not in value:
            continue
        for node in [*value["nodes"], *value["ancestors"]]:
            if node["kind"] == "task" and node["node_id"] in read:
                was = read[node["node_id"]]["task"]
                assert [node["task"].get(key) for key in facts] == [
                    was.get(key) for key in facts
                ], (name, node["node_id"])
        for entry in value["rescheduled"]:
            was = read[entry["node_id"]]["task"]
            if was["progress"] != "not_started":
                assert (entry["start"], entry["finish"]) == (was["start"], was["finish"]), name
