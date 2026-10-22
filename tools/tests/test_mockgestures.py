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
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import (
    REPOSITORY,
    mockamendmentwrites,
    mockcore,
    mockdata,
    mockdating,
    mockgestures,
    mocktree,
    mockwitness,
    mockwrites,
)
from wftools.mockids import universe
from wftools.mockstructure import described
from wftools.mocktree import AT_END, LINE, TASK, After
from wftools.mockwitness import CORE, CUSTOMER, Link, N, Task, node_id

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


def moved_under(roots: tuple[Task, ...], number: int, parent: int) -> tuple[Task, ...]:
    """Return a structure with a task, not a root, moved with its subordinates under another.

    Last under it, as an indentation puts it under the task above it at its level (WF-PLA-0040):
    the structure a refused move would leave, which ``mockdating.schedule`` refuses too.
    """
    [task] = [each for each in mockdating.tasks_in_order(roots) if each.number == number]

    def move(each: Task) -> Task:
        children = tuple(child for child in each.children if child.number != number)
        if each.number == parent:
            children = (*children, task)
        return each if children == each.children else replace(each, children=children)

    return mockwrites.amended(roots, move)


# --- The contract cites each example under its operation ----------------------------------------


OPERATIONS = {
    "createNode": (
        "201",
        [
            "node_created",
            "node_created_child",
            "estimate_line_created",
            "estimate_line_created_after_subtask",
        ],
    ),
    "deleteNode": ("200", ["node_summary_deleted"]),
    "moveNodes": ("200", ["nodes_moved", "nodes_indented"]),
    "setNodeTracking": ("200", ["node_tracked"]),
    "updateEstimateLine": ("200", ["estimate_line_updated_amendment"]),
    "previewPaste": ("200", ["paste_plan_amendment"]),
    "applyPaste": ("200", ["paste_applied_amendment"]),
}
REFUSALS = {
    "createNode": [
        "estimate_line_completed_refused",
        "node_create_horizon_exceeded",
        "node_create_after_not_sibling",
    ],
    "updateTaskFacet": [
        "task_date_computed_refused",
        "task_horizon_exceeded",
        "task_hours_beyond_day",
        "task_hours_below_zero",
    ],
    "setPredecessors": [
        "predecessors_cycle_refused",
        "predecessors_forbidden",
        "predecessors_horizon_exceeded",
    ],
    "moveNodes": [
        "nodes_move_after_not_sibling",
        "nodes_indent_forbidden",
        "nodes_move_cycle_refused",
        "nodes_move_completed_refused",
    ],
    "setNodeTracking": ["node_tracking_milestone_refused"],
    "deleteNode": ["node_delete_stale"],
}
REQUESTS = {"moveNodes": ["nodes_move_mixed"], "updateTaskFacet": ["task_dates_sent"]}


def _operation(name: str) -> str:
    text = (REPOSITORY / "docs" / "api" / "paths" / "revisions.yaml").read_text(encoding="utf-8")
    operation = text[text.index(f"operationId: {name}") :]
    return operation[: operation.index("operationId:", len("operationId:"))]


def _cited(text: str) -> list[str]:
    return re.findall(r"fixtures/api/(\w+)\.json", text)


def test_every_gesture_is_an_example_the_contract_cites_under_its_answer() -> None:
    # The gestures of the estimate on the amendment 2 are said with them (#1214).
    examples = {**mockgestures.examples(), **mockamendmentwrites.examples()}
    cited: set[str] = set()
    for operation, (status, names) in OPERATIONS.items():
        text = _operation(operation)
        success = text[text.index(f"'{status}':") : text.index("'401':")]
        assert set(names) <= set(_cited(success)), operation
        cited |= set(names)
    for operation, names in REFUSALS.items():
        text = _operation(operation)
        assert set(names) <= set(_cited(text[text.index("'401':") :])), operation
        cited |= set(names)
    for operation, names in REQUESTS.items():
        text = _operation(operation)
        assert set(names) <= set(_cited(text[: text.index("responses:")])), operation
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
    station_children = mockwitness.CONTROL_STATION.lines + mockwitness.CONTROL_STATION.children
    assert task["position"] == len(station_children) + 1
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


def manual_on(first: date, last: date, role: str | None = None) -> mockdating.Dated:
    """Return the commissioning, in manual mode, dated at two days entered without hours.

    Its labour line is given to another role when one is said, and the task its calendar.
    """
    roots = mockwrites.amended(CORE, mockwrites.on_task(N.COMMISSIONING, manual=(first, last)))
    if role is not None:
        roots = mockwrites.amended(roots, line=mockwrites.on_line(N.COMMISSIONING_LINE, role=role))
    return mockdating.schedule(roots)[N.COMMISSIONING]


def test_dates_sent_without_their_hours_are_completed_on_the_calendar_of_the_task() -> None:
    # #1244 (WF-PLA-0020, WF-DAT-0100): the front sends the days alone, with the counter the
    # mode changed left; the answer carries the hours the server completed, the start at the
    # start of its day, the finish at the end of that day's hours on the applicable calendar.
    sent = gesture("task_dates_sent")
    first, last = mockgestures.ENTERED_DATES
    assert sent["start"] == {"date": first.isoformat()}
    assert sent["finish"] == {"date": last.isoformat()}
    [manual] = gesture("task_mode_changed")["nodes"]
    assert sent["lock_version"] == manual["lock_version"]
    hours = manual_on(first, last).calendar.hours_on(last)
    assert hours > 0
    [task] = gesture("task_dates_entered")["nodes"]
    assert task["task"]["start"] == {"date": first.isoformat(), "hours": "0"}
    assert task["task"]["finish"] == {"date": last.isoformat(), "hours": str(hours)}


def test_the_hours_completed_are_those_of_the_calendar_of_the_role_of_the_task() -> None:
    # #1244 (WF-PLA-0010, WF-PLA-0020): the commissioning given to the cable fitter, on the week
    # of four days of ten hours, ends a Thursday entered at ten hours, not at the eight of the
    # default calendar; it starts the Monday at no hour.
    monday, thursday = date(2027, 1, 11), date(2027, 1, 14)
    placed = manual_on(monday, thursday, mockwitness.CABLE_FITTER)
    calendar = mockwitness.role_calendars()[mockwitness.CABLE_FITTER]
    assert placed.calendar == calendar
    assert calendar != mockwitness.default_calendar()
    assert calendar.hours_on(thursday) != mockwitness.default_calendar().hours_on(thursday)
    assert (placed.start.day, placed.start.hours) == (monday, 0)
    assert (placed.finish.day, placed.finish.hours) == (thursday, calendar.hours_on(thursday))


def test_hours_sent_past_those_of_their_day_are_refused_on_their_field() -> None:
    # #1244 (WF-PLA-0010, WF-DAT-0100): hours sent are taken as they are, never bounded; past
    # those the calendar of the task grants that day, they are refused, the bound crossed named.
    # A day without hours is refused by its date (#1271): the bound is said on a day of work,
    # never none.
    day, hours = mockgestures.HOURS_BEYOND_DAY
    first, _ = mockgestures.ENTERED_DATES
    granted = manual_on(first, day).calendar.hours_on(day)
    assert hours > granted > 0
    refused = gesture("task_hours_beyond_day")
    assert refused["code"] == "VALIDATION_FAILED"
    assert refused["fields"] == [
        {"pointer": "/finish/hours", "code": "VALUE_OUT_OF_RANGE", "params": {"maximum": "8"}}
    ]


def test_a_manual_date_imported_on_a_day_without_hours_is_kept_at_no_hour() -> None:
    # #1271: entered, such a day is refused (``mocknonworking``); imported from MS Project, it is
    # kept as the file carries it, never moved (WF-PLA-0020), its start and its finish at no hour.
    saturday, sunday = date(2027, 1, 16), date(2027, 1, 17)
    placed = manual_on(saturday, sunday)
    assert placed.calendar.hours_on(saturday) == placed.calendar.hours_on(sunday) == 0
    assert (placed.start.day, placed.start.hours) == (saturday, 0)
    assert (placed.finish.day, placed.finish.hours) == (sunday, 0)


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
        mockdating.schedule(looped)


def test_no_loop_is_found_when_no_predecessor_sent_follows_the_task() -> None:
    assert mocktree.cycle(N.COMMISSIONING, (Link(N.MOUNTING),)) == []


def test_a_task_sent_as_its_own_predecessor_is_a_loop_of_itself() -> None:
    assert mocktree.cycle(N.MOUNTING, (Link(N.MOUNTING),)) == [N.MOUNTING]


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


def test_a_task_indented_under_its_predecessor_is_refused_as_a_forbidden_link(
    read: dict[str, Node],
) -> None:
    # The task above it at its level would become its summary, the link binding them (#1164).
    refused = gesture("nodes_indent_forbidden")
    assert (refused["code"], refused["status"], "params" in refused) == (
        "LINK_FORBIDDEN",
        422,
        False,
    )
    task = read[universe(mockgestures.INDENTED_FORBIDDEN)]
    above = read[universe(mockgestures.INDENTED_UNDER)]
    assert (task["parent_id"], task["position"]) == (above["parent_id"], above["position"] + 1)
    assert above["node_id"] in {link["predecessor_node_id"] for link in task["predecessors"]}
    indented = moved_under(CORE, mockgestures.INDENTED_FORBIDDEN, mockgestures.INDENTED_UNDER)
    with pytest.raises(ValueError, match="binds the summary"):
        mockdating.schedule(indented)


def test_a_task_moved_under_a_task_it_follows_is_refused_naming_the_loop(
    read: dict[str, Node],
) -> None:
    # From the summary it would receive down to it, each preceding the next (#1164).
    refused = gesture("nodes_move_cycle_refused")
    assert (refused["code"], refused["status"]) == ("LINK_CYCLE", 422)
    loop = refused["params"]["cycle"]
    moved, under = mockgestures.loop_move()
    assert (loop[0]["node_id"], loop[-1]["node_id"], len(loop)) == (
        node_id(under),
        node_id(moved),
        3,
    )
    for before, after in itertools.pairwise(loop):
        links = read[after["node_id"]]["predecessors"]
        assert before["node_id"] in {link["predecessor_node_id"] for link in links}
    for each in loop:
        assert each["label"] == read[each["node_id"]]["task"]["label"]
    assert read[node_id(moved)]["parent_id"] == read[node_id(under)]["parent_id"]
    with pytest.raises(ValueError, match="close a loop through a summary"):
        mockdating.schedule(moved_under(described(), moved, under))


@pytest.mark.parametrize(
    ("name", "parent", "after"),
    [
        ("node_create_after_not_sibling", mockgestures.CREATED_UNDER, mockgestures.CREATED_AFTER),
        ("nodes_move_after_not_sibling", mockgestures.MOVED_UNDER, mockgestures.MOVED_AFTER),
    ],
)
def test_a_place_after_a_node_that_is_not_a_sibling_is_refused_on_its_field(
    read: dict[str, Node], name: str, parent: int, after: int
) -> None:
    # The node to follow is read under another parent (#1183): refused on `/after_node_id`,
    # without a parameter.
    refused = gesture(name)
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    assert refused["fields"] == [{"pointer": "/after_node_id", "code": "NODE_NOT_SIBLING"}]
    assert read[universe(after)]["parent_id"] not in {None, universe(parent)}


def test_a_place_after_a_sibling_is_not_refused() -> None:
    # The node to follow under the parent, and not among the nodes moved, is a place.
    with pytest.raises(ValueError, match="is a sibling"):
        mockgestures.not_sibling(N.STUDIES, N.DESIGN_FILE, universe(1))
    refused = mockgestures.not_sibling(N.WIRING, N.LABOUR, universe(1), moved=(N.LABOUR,))
    assert refused["fields"] == [{"pointer": "/after_node_id", "code": "NODE_NOT_SIBLING"}]


def test_a_move_that_closes_no_loop_is_not_refused() -> None:
    # The indentation the contract shows succeeding (nodes_indented) binds no summary.
    assert mocktree.move_loop((N.INSTALLATION,), N.CONTROL_STATION, CORE) == []
    with pytest.raises(ValueError, match="closes no loop"):
        mockgestures.move_refused(N.INSTALLATION, N.CONTROL_STATION, CORE, universe(1176))


def test_a_summary_given_its_own_subordinate_as_predecessor_is_not_dated() -> None:
    bound = mockwrites.amended(CORE, mockwrites.on_task(N.INSTALLATION, links=(Link(N.MOUNTING),)))
    with pytest.raises(ValueError, match="binds the summary"):
        mockdating.schedule(bound)


def _finish(roots: tuple[mockwitness.Task, ...], number: int) -> date:
    return mockdating.schedule(roots)[number].finish.day


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


def test_the_time_time_tracking_of_a_task_that_is_no_milestone_is_refused_on_its_entry(
    read: dict[str, Node],
) -> None:
    # #1159: the time/time tracking follows milestones; the refusal names the kind of the entry
    # that asks for it, by its rank among the entries sent, with a code of its own.
    refused = gesture("node_tracking_milestone_refused")
    task = read[universe(mockgestures.UNTRACKED_TASK)]["task"]
    assert task["is_milestone"] is False
    entries = mockgestures.tracking_entries(mockgestures.UNTRACKED_TASK)
    [rank] = [at for at, entry in enumerate(entries) if entry["kind"] == "milestone_tracking"]
    assert [entry["timeline_id"] for entry in entries[:rank]] == [
        each["timeline_id"] for each in task["tracking"]
    ]
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    assert refused["fields"] == [{"pointer": f"/entries/{rank}/kind", "code": "MILESTONE_REQUIRED"}]


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


# --- The loops that cross the hierarchy (#1169) -------------------------------------------------


def _leaf(number: int, *links: int) -> Task:
    return Task(number, f"Tâche {number}", days=1, links=tuple(Link(each) for each in links))


def test_a_loop_through_the_hierarchy_names_the_summary_and_the_subordinate_it_crosses() -> None:
    # P → W, W the summary of Z, Z → M: M moved under P closes a loop through the hierarchy, the
    # summary W spanning Z — what precedes W precedes Z. No chain of links alone closes it.
    p, w, z, m = 901, 902, 903, 904
    down = (_leaf(p), Task(w, "W", links=(Link(p),), children=(_leaf(z),)), _leaf(m, z))
    assert mocktree.move_loop((m,), p, down) == [p, w, z, m]
    with pytest.raises(ValueError, match="close a loop through a summary"):
        mockdating.schedule(_moved_root(down, m, p))
    # Up: P → Z, Z a subordinate of W, W → M — what follows W follows Z.
    up = (_leaf(p), Task(w, "W", children=(_leaf(z, p),)), _leaf(m, w))
    assert mocktree.move_loop((m,), p, up) == [p, z, w, m]
    with pytest.raises(ValueError, match="close a loop through a summary"):
        mockdating.schedule(_moved_root(up, m, p))
    # Predecessors entered cross it too: W given P as predecessor, Z → M and M under P.
    entered = (Task(p, "P", children=(_leaf(m, z),)), Task(w, "W", children=(_leaf(z),)))
    assert mocktree.cycle(w, (Link(p),), entered) == [w, z, m, p]
    looped = mockwrites.amended(entered, mockwrites.on_task(w, links=(Link(p),)))
    with pytest.raises(ValueError, match="close a loop through a summary"):
        mockdating.schedule(looped)


def test_a_selection_is_judged_with_all_its_tasks_moved() -> None:
    # P → W, W the summary of Z, Z → M: M alone under P closes the loop P, W, Z, M; Z moved with
    # it leaves W without the subordinate the chain crossed, and the selection closes none.
    p, w, z, m = 901, 902, 903, 904
    down = (_leaf(p), Task(w, "W", links=(Link(p),), children=(_leaf(z),)), _leaf(m, z))
    assert mocktree.move_loop((m,), p, down) == [p, w, z, m]
    assert mocktree.move_loop((m, z), p, down) == []


def test_a_selection_names_the_loop_of_the_first_in_cause_in_the_order_of_the_plan() -> None:
    # P → X → A and P → Y → B: A and B each close a loop under P. Sent B first, the selection
    # names the loop of A, first in the order of the plan; `node_ids` only places them.
    p, x, a, y, b = 901, 902, 903, 904, 905
    roots = (_leaf(p), _leaf(x, p), _leaf(a, x), _leaf(y, p), _leaf(b, y))
    assert mocktree.move_loop((b,), p, roots) == [p, y, b]
    assert mocktree.move_loop((b, a), p, roots) == [p, x, a]


def test_a_task_moved_under_itself_or_its_subordinate_is_no_move() -> None:
    w, z = 902, 903
    roots = (Task(w, "W", children=(_leaf(z),)),)
    with pytest.raises(ValueError, match="which it spans"):
        mocktree.move_loop((w,), w, roots)
    with pytest.raises(ValueError, match="which it spans"):
        mocktree.move_loop((w,), z, roots)


def test_a_chain_as_short_takes_the_links_before_the_hierarchy() -> None:
    # T → A → S and T, the summary of B, B → S: both chains have three tasks; the link first.
    t, a, b, s = 901, 902, 903, 904
    roots = (Task(t, "T", children=(_leaf(b),)), _leaf(a, t), _leaf(s, a, b))
    assert mocktree.cycle(t, (Link(s),), roots) == [t, a, s]


def test_a_chain_as_short_takes_the_subordinates_before_the_summary() -> None:
    # T, the summary of B, B → S, and T a subordinate of U, U → S: down to B before up to U.
    u, t, b, s = 901, 902, 903, 904
    roots = (Task(u, "U", children=(Task(t, "T", children=(_leaf(b),)),)), _leaf(s, u, b))
    assert mocktree.cycle(t, (Link(s),), roots) == [t, b, s]


def _moved_root(roots: tuple[Task, ...], number: int, parent: int) -> tuple[Task, ...]:
    """Return a structure with a root task moved, with its subordinates, last under another."""
    [task] = [each for each in roots if each.number == number]
    kept = tuple(each for each in roots if each.number != number)
    return mockwrites.amended(
        kept,
        lambda each: (
            replace(each, children=(*each.children, task)) if each.number == parent else each
        ),
    )


# --- The rank of a node created or moved (#1183, #1187, #1188) ---------------------------------

LINES, TASKS = (11, 12), (21, 22)
"""The lines and the subordinates of a task, in the order of the plan, that the cases place."""


@pytest.mark.parametrize(
    ("sent", "after", "lines", "tasks"),
    [
        # Nil: a line first of the lines, a task first of the subordinates.
        (((1, LINE),), None, [1, 11, 12], [21, 22]),
        (((1, TASK),), None, [11, 12], [1, 21, 22]),
        # Absent: after the last of its kind.
        (((1, LINE),), AT_END, [11, 12, 1], [21, 22]),
        (((1, TASK),), AT_END, [11, 12], [21, 22, 1]),
        # After a sibling of its kind: right after it.
        (((1, LINE),), 11, [11, 1, 12], [21, 22]),
        (((1, TASK),), 21, [11, 12], [21, 1, 22]),
        # After a sibling of the other kind: on the boundary.
        (((1, LINE),), 22, [11, 12, 1], [21, 22]),
        (((1, TASK),), 11, [11, 12], [1, 21, 22]),
        # A selection that mixes them: each kind after the previous one of its kind.
        (((1, LINE), (2, TASK), (3, LINE)), 21, [11, 12, 1, 3], [21, 2, 22]),
        (((1, TASK), (2, LINE), (3, TASK)), None, [2, 11, 12], [1, 3, 21, 22]),
        # Absent, the nodes moved left out: a sibling moved is not the last to follow.
        (((12, LINE),), AT_END, [11, 12], [21, 22]),
        (((22, TASK), (12, LINE)), AT_END, [11, 12], [21, 22]),
        (((11, LINE),), AT_END, [12, 11], [21, 22]),
    ],
)
def test_the_rank_follows_the_rule_of_the_contract(
    sent: tuple[tuple[int, str], ...], after: After, lines: list[int], tasks: list[int]
) -> None:
    assert mocktree.placed(LINES, TASKS, sent, after) == (lines, tasks)


@pytest.mark.parametrize("after", [99, 11])
def test_a_place_after_a_node_moved_or_not_a_sibling_is_refused(after: int) -> None:
    with pytest.raises(ValueError, match="is not a sibling"):
        mocktree.placed(LINES, TASKS, ((11, LINE),), after)
