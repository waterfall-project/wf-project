# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the lists of the reference the fake back serves: their pages, sort and commands.

They try the examples against the contract they illustrate and against one another — the pages and
the sort of the generated lists, the commands of the lists written by hand —, not the Vérif of a
requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockdata, mockreference
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]


def _row(code: str, *amounts: str | None) -> Entry:
    return {
        "code": code,
        "cells": [None if amount is None else {"amount": amount} for amount in amounts],
    }


def _codes(rows: list[Entry]) -> list[str]:
    return [row["code"] for row in rows]


GRID: Entry = {
    "years": [2025, 2026],
    "rows": [
        _row("MO-004", "70.00", "90.00"),
        _row("MO-001", "60.00", None),
        _row("MO-003", None, "80.00"),
        _row("MO-002", "50.00", "90.00"),
    ],
}


def test_the_rate_of_a_year_sorts_the_rows_the_empty_ones_last_in_the_increasing_order() -> None:
    assert _codes(mockreference.by_rate(GRID, 2026, descending=False)) == [
        "MO-003",
        "MO-002",
        "MO-004",
        "MO-001",
    ]


def test_in_the_decreasing_order_the_empty_rows_come_first_and_the_ties_keep_their_code() -> None:
    assert _codes(mockreference.by_rate(GRID, 2026, descending=True)) == [
        "MO-001",
        "MO-002",
        "MO-004",
        "MO-003",
    ]


def test_a_year_the_grid_does_not_bear_leaves_the_order_of_the_code() -> None:
    for descending in (False, True):
        assert _codes(mockreference.by_rate(GRID, 2019, descending=descending)) == [
            "MO-001",
            "MO-002",
            "MO-003",
            "MO-004",
        ]
    assert mockreference.rate(GRID["rows"][0], GRID["years"], 2025) == Decimal("70.00")


def test_a_page_holds_its_items_and_says_where_it_stands_in_the_whole() -> None:
    assert mockreference.page(list(range(7)), 3, 3) == {
        "items": [3, 4, 5],
        "meta": {"limit": 3, "offset": 3, "total": 7},
    }
    assert mockreference.page(list(range(7)), 3, 6)["items"] == [6]


def test_the_commands_of_an_object_are_written_before_its_audit() -> None:
    entry = mockreference.commanded(
        {"code": "X", "is_active": True, "audit": {}, "lock_version": 1},
        mockreference.commands("reactivate", ["org_node_active"]),
    )
    assert list(entry) == ["code", "is_active", "available_commands", "audit", "lock_version"]
    assert entry["available_commands"] == [
        {"command": "reactivate", "is_available": False, "missing_conditions": ["org_node_active"]}
    ]


DEACTIVATE: list[Entry] = [
    {"command": "deactivate", "is_available": True, "missing_conditions": []}
]
REACTIVATE: list[Entry] = [
    {"command": "reactivate", "is_available": True, "missing_conditions": []}
]


@pytest.fixture(scope="module")
def volumes() -> dict[str, Any]:
    return {name: example["value"] for name, example in mockdata.volumes().items()}


@pytest.fixture(scope="module")
def named() -> dict[str, Any]:
    return {name: example["value"] for name, example in mockreference.named().items()}


def _items(value: Any) -> list[Entry]:
    """Return the objects of a reading: the items of a page, or the list of the tree."""
    if isinstance(value, dict):
        return cast("list[Entry]", cast("Entry", value)["items"])
    return cast("list[Entry]", value)


def test_the_categories_are_read_whole_by_code_and_their_second_page_follows(
    volumes: dict[str, Any],
) -> None:
    whole, second = volumes["cost_categories.json"], volumes["cost_categories_page.json"]
    codes = [category["code"] for category in whole["items"]]
    assert codes == sorted(codes)
    assert whole["meta"] == {"limit": 500, "offset": 0, "total": 200}
    assert second["meta"] == {"limit": 50, "offset": 50, "total": 200}
    assert second["items"] == whole["items"][50:100]
    for category in whole["items"]:
        # Each active: the deactivation first, its availability tried in test_mockcostsettings.
        assert category["available_commands"][0]["command"] == "deactivate"


def test_the_rows_of_the_grid_come_by_code_every_one_active(volumes: dict[str, Any]) -> None:
    for name in ("hourly_rate_grid.json", "hourly_rate_grid_bounded.json"):
        rows = volumes[name]["rows"]
        assert [row["code"] for row in rows] == sorted(row["code"] for row in rows)
        assert all(row["is_active"] is True for row in rows)


def _rate_2026(row: Entry) -> Decimal:
    cell = row["cells"][-1]
    assert cell is not None, row["code"]
    return Decimal(cell["amount"])


def test_the_grid_sorted_by_a_rate_keeps_the_years_of_the_whole_grid(
    volumes: dict[str, Any],
) -> None:
    whole, ranked = volumes["hourly_rate_grid.json"], volumes["hourly_rate_grid_by_rate.json"]
    assert whole["years"][-1] == 2026
    # Every category bears a rate of 2026: the order of the empty cells is tried above.
    assert all(row["cells"][-1] is not None for row in whole["rows"])
    assert whole["meta"] == {"limit": 500, "offset": 0, "total": 150}
    assert ranked["meta"] == {"limit": 50, "offset": 0, "total": 150}
    assert ranked["years"] == whole["years"]
    amounts = [_rate_2026(row) for row in ranked["rows"]]
    assert amounts == sorted(amounts, reverse=True)
    left_out = [row for row in whole["rows"] if row not in ranked["rows"]]
    assert all(_rate_2026(row) <= amounts[-1] for row in left_out)


def test_two_categories_at_the_same_rate_keep_the_order_of_their_code(
    volumes: dict[str, Any],
) -> None:
    codes = [row["code"] for row in volumes["hourly_rate_grid_by_rate.json"]["rows"]]
    tied = [row["code"] for row in volumes["hourly_rate_grid.json"]["rows"]]
    tied = [code for code in tied if code in {"MO-066", "MO-137"}]
    rates = {
        row["code"]: _rate_2026(row)
        for row in volumes["hourly_rate_grid.json"]["rows"]
        if row["code"] in tied
    }
    assert rates == {"MO-066": Decimal("99.12"), "MO-137": Decimal("99.12")}
    first = codes.index("MO-066")
    assert codes[first + 1] == "MO-137"


def test_a_bounded_grid_keeps_the_rows_whose_rate_reaches_the_bound_and_every_year(
    volumes: dict[str, Any],
) -> None:
    whole, kept = volumes["hourly_rate_grid.json"], volumes["hourly_rate_grid_bounded.json"]
    # The bound is a rate two rows bear: both are retained, the bound included.
    bound = Decimal("99.12")
    expected = [row for row in whole["rows"] if _rate_2026(row) >= bound]
    assert {"MO-066", "MO-137"} <= {row["code"] for row in kept["rows"]}
    assert all(_rate_2026(row) >= bound for row in kept["rows"])
    assert kept["rows"] == expected[:50]
    assert kept["meta"] == {"limit": 50, "offset": 0, "total": len(expected)}
    assert kept["years"] == whole["years"]


def test_each_object_a_reader_reads_is_active_and_bears_no_command(
    volumes: dict[str, Any], named: dict[str, Any]
) -> None:
    readings = {**volumes, **named}
    readers = [name for name in readings if name.endswith("_reader.json")]
    assert sorted(readers) == [
        "calendars_reader.json",
        "cost_categories_reader.json",
        "cost_types_reader.json",
        "org_nodes_reader.json",
        "resource_roles_reader.json",
    ]
    for name in readers:
        entries = _items(readings[name])
        assert entries, name
        for entry in entries:
            assert (entry["is_active"], entry["available_commands"]) == (True, []), name


@pytest.mark.parametrize(
    ("name", "column"),
    [
        ("resource_roles", "label"),
        ("calendars", "label"),
        ("calendars_with_inactive", "label"),
        ("cost_types", "code"),
        ("cost_types_with_inactive", "code"),
    ],
)
def test_the_lists_written_by_hand_come_in_the_order_of_their_list_without_sort(
    name: str, column: str
) -> None:
    # Without `sort_by`, the roles and the calendars come by label, the natures by code, the texts
    # compared by code point, as the categories come by code.
    values = [entry[column] for entry in fixture(name)["items"]]
    assert values == sorted(values)


def test_a_reader_reads_the_active_objects_of_the_list_and_nothing_else(
    named: dict[str, Any],
) -> None:
    for reader, whole in (
        ("resource_roles_reader.json", fixture("resource_roles")["items"]),
        ("calendars_reader.json", fixture("calendars")["items"]),
        ("cost_types_reader.json", fixture("cost_types")["items"]),
        ("org_nodes_reader.json", fixture("org_nodes")),
    ):
        active = [entry for entry in whole if entry["is_active"]]
        read = _items(named[reader])
        ids = [next(v for k, v in entry.items() if k.endswith("_id")) for entry in read]
        assert ids == [next(v for k, v in entry.items() if k.endswith("_id")) for entry in active]


def test_the_bounded_roles_are_those_whose_monthly_hours_reach_the_bound(
    named: dict[str, Any],
) -> None:
    roles = fixture("resource_roles")["items"]
    # The bound is the technician's own hours: the role is retained, the bound included.
    bound = Decimal("485324.00")
    expected = [role for role in roles if Decimal(role["capacity"]["monthly_hours"]) >= bound]
    assert {role["label"] for role in expected} == {
        "Ingénieur électricien",
        "Technicien de mise en service",
    }
    assert named["resource_roles_bounded.json"] == {
        "items": expected,
        "meta": {"limit": 50, "offset": 0, "total": 2},
    }


def test_the_inverted_bounds_name_the_upper_one_and_the_lower_one_given() -> None:
    refused = fixture("resource_roles_bounds_inverted")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [
        {
            "pointer": "/query/monthly_hours_max",
            "code": "VALUE_OUT_OF_RANGE",
            "params": {"minimum": "1000"},
        }
    ]


def _command(entry: Entry) -> tuple[str, bool, list[str]]:
    """Return the command that changes the state of an object, the first it lists.

    A nature lists the change of its kind after it (`CostTypeCommand`), a category its move under
    a nature of another kind (`CostCategoryCommand`, EP-02/L42g), a calendar its designation by
    default (`CalendarCommand`, EP-14/L42j); every other object of the reference lists that command
    alone.
    """
    available, *others = entry["available_commands"]
    assert [other["command"] for other in others] in (
        [],
        ["change_kind"],
        ["change_cost_type"],
        ["set_default"],
    )
    return available["command"], available["is_available"], available["missing_conditions"]


def test_each_object_of_the_reference_bears_the_command_that_changes_its_state(
    volumes: dict[str, Any],
) -> None:
    lists = [
        fixture("org_nodes"),
        fixture("org_nodes_with_inactive"),
        fixture("resource_roles")["items"],
        fixture("calendars")["items"],
        fixture("calendars_with_inactive")["items"],
        fixture("cost_types")["items"],
        fixture("cost_types_with_inactive")["items"],
        volumes["cost_categories.json"]["items"],
        [fixture("resource_role_reactivated")],
    ]
    for entries in lists:
        for entry in entries:
            command, _, _ = _command(entry)
            assert command == ("deactivate" if entry["is_active"] else "reactivate")


def test_the_conditions_of_the_reference_are_named_where_their_state_misses_them() -> None:
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    for node in nodes.values():
        parent = nodes.get(node["parent_id"])
        blocked = not node["is_active"] and parent is not None and not parent["is_active"]
        assert _command(node)[2] == (["org_node_parent_active"] if blocked else [])
    for role in fixture("resource_roles")["items"]:
        assert role["org_node_label"] == nodes[role["org_node_id"]]["label"]
        blocked = not role["is_active"] and not nodes[role["org_node_id"]]["is_active"]
        assert _command(role)[2] == (["org_node_active"] if blocked else [])
    for calendar in fixture("calendars_with_inactive")["items"]:
        assert _command(calendar)[2] == (["calendar_not_default"] if calendar["is_default"] else [])
    for entry in [*nodes.values(), *fixture("resource_roles")["items"]]:
        _, available, missing = _command(entry)
        assert available == (not missing)


def test_the_witness_tree_is_the_tree_with_its_deactivated_nodes_left_out() -> None:
    active = [node for node in fixture("org_nodes_with_inactive") if node["is_active"]]
    assert active == fixture("org_nodes")


def test_the_witness_calendars_are_those_with_the_deactivated_week_left_out() -> None:
    whole = fixture("calendars_with_inactive")["items"]
    assert [entry for entry in whole if entry["is_active"]] == fixture("calendars")["items"]
    [week] = [entry for entry in whole if not entry["is_active"]]
    # Its designation by default is listed after, unavailable while it is deactivated (EP-14/L42j).
    assert (week["calendar_id"], week["available_commands"][:1]) == (universe(483), REACTIVATE)
    hours = sum(Decimal(value) for value in week["weekly_hours"].values())
    assert hours == Decimal(39)


def test_the_refused_reactivation_is_that_of_the_role_whose_node_is_deactivated() -> None:
    refused = fixture("resource_role_reactivation_refused")
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    role = roles[universe(455)]
    assert (role["is_active"], _command(role)) == (
        False,
        ("reactivate", False, ["org_node_active"]),
    )
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {
        "missing_condition": "org_node_active",
        "conflicting_object_id": role["org_node_id"],
    }


def test_the_refused_reactivation_of_a_node_names_its_deactivated_parent() -> None:
    refused = fixture("org_node_reactivation_refused")
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    cell = nodes[universe(475)]
    assert _command(cell) == ("reactivate", False, ["org_node_parent_active"])
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {
        "missing_condition": "org_node_parent_active",
        "conflicting_object_id": cell["parent_id"],
    }
    assert cell["parent_id"] == universe(474)


def test_the_refused_deactivation_is_that_of_the_default_calendar() -> None:
    refused = fixture("calendar_deactivation_refused")
    [default] = [entry for entry in fixture("calendars")["items"] if entry["is_default"]]
    assert default["label"] == "Semaine standard"
    assert _command(default) == ("deactivate", False, ["calendar_not_default"])
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": "calendar_not_default"}


def test_the_reactivation_of_a_node_makes_it_alone_active_from_the_version_read(
    named: dict[str, Any],
) -> None:
    answer = named["org_node_reactivated.json"]
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    [node] = answer["org_nodes"]
    read = nodes[universe(474)]
    assert answer["resource_roles"] == []
    assert node["org_node_id"] == read["org_node_id"]
    assert (node["is_active"], node["available_commands"]) == (True, DEACTIVATE)
    assert node["lock_version"] == read["lock_version"] + 1
    assert node["audit"]["updated_at"] == "2026-06-03T14:05:00Z"
    stale = fixture("org_node_activation_stale")
    assert (stale["status"], stale["code"]) == (412, "STALE_LOCK_VERSION")
    assert stale["params"] == {"expected_lock_version": node["lock_version"]}


def test_the_stale_reactivations_name_the_version_another_session_wrote() -> None:
    stale = fixture("resource_role_activation_stale")
    reactivated = fixture("resource_role_reactivated")
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    read = roles[reactivated["resource_role_id"]]
    assert (stale["status"], stale["code"]) == (412, "STALE_LOCK_VERSION")
    assert stale["params"] == {"expected_lock_version": reactivated["lock_version"]}
    assert read["lock_version"] < reactivated["lock_version"]
    calendar = fixture("calendar_activation_stale")
    [week] = [e for e in fixture("calendars_with_inactive")["items"] if not e["is_active"]]
    assert (calendar["status"], calendar["code"]) == (412, "STALE_LOCK_VERSION")
    assert calendar["params"]["expected_lock_version"] > week["lock_version"]


def test_the_grid_and_the_calendars_refuse_bounds_inverted_or_a_bound_without_its_year() -> None:
    for name, pointer, minimum in (
        ("calendars_bounds_inverted", "/query/friday_max", "10"),
        ("hourly_rate_grid_bounds_inverted", "/query/rate_max", "100"),
    ):
        refused = fixture(name)
        assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
        assert refused["fields"] == [
            {"pointer": pointer, "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": minimum}}
        ]
    missing = fixture("hourly_rate_grid_rate_year_missing")
    assert (missing["status"], missing["code"]) == (422, "VALIDATION_FAILED")
    assert missing["fields"] == [{"pointer": "/query/rate_year", "code": "VALUE_REQUIRED"}]


def test_the_last_category_of_provision_goes_as_any_other() -> None:
    # The rule of #578 is withdrawn (EP-14/L42p, #579): the last active category of provision for
    # risks has its deactivation available, the creation of a project and the declaration of a
    # risk naming what they then miss (WF-CYC-0120, WF-RIS-0010).
    category: Entry = {
        "cost_category_id": universe(404),
        "cost_type_id": universe(463),
        "is_active": True,
    }
    assert mockreference.category_commands(category, set(), set()) == [
        {"command": "deactivate", "is_available": True, "missing_conditions": []},
        {"command": "change_cost_type", "is_available": True, "missing_conditions": []},
    ]
