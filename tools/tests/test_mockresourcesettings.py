# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the writes of the resource settings: their refusals and their commands (EP-14/L42j).

They try the examples of the nodes, the roles and the calendars against the universe they
illustrate and against the contract, not the Vérif of a requirement: none cites one (WF-QUA-0010,
« un test qui ne couvre aucune exigence »).
"""

import json
import re
from decimal import Decimal
from typing import Any

import pytest

from wftools import REPOSITORY
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

PATHS = REPOSITORY / "docs" / "api" / "paths" / "reference.yaml"

REFUSED = {
    "org_node_move_cycle_refused": (("updateOrgNode",), [("/parent_id", "ORG_NODE_CYCLE")]),
    "resource_role_attachments_refused": (
        ("createResourceRole",),
        [
            ("/org_node_id", "UNKNOWN_ORG_NODE"),
            ("/cost_category_id", "LABOUR_CATEGORY_REQUIRED"),
            ("/calendar_id", "INACTIVE_REFERENCE_OBJECT"),
        ],
    ),
    "resource_role_update_refused": (
        ("updateResourceRole",),
        [
            ("/calendar_id", "INACTIVE_REFERENCE_OBJECT"),
            ("/capacity/headcount", "VALUE_OUT_OF_RANGE"),
        ],
    ),
    "calendar_hours_refused": (
        ("createCalendar", "updateCalendar"),
        [
            ("/weekly_hours/monday", "VALUE_OUT_OF_RANGE"),
            ("/weekly_hours/saturday", "VALUE_OUT_OF_RANGE"),
        ],
    ),
}
"""Each refusal by field of the resource settings: the operations that cite it, its fields."""

STALE = {
    "org_node_update_stale": ("updateOrgNode", "org_node_updated"),
    "resource_role_update_stale": ("updateResourceRole", "resource_role_updated"),
    "calendar_update_stale": ("updateCalendar", "calendar_updated"),
    "calendar_default_stale": ("setDefaultCalendar", "calendar_updated"),
}
"""Each stale write, its operation, and the write of another session whose version it names."""


def _cited(operation: str) -> set[str]:
    """Return the fixtures the contract cites under an operation of the reference."""
    text = PATHS.read_text(encoding="utf-8")
    block = text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]
    return set(re.findall(r"fixtures/api/([a-z_]+)\.json", block))


def _calendars() -> dict[str, Entry]:
    return {c["calendar_id"]: c for c in fixture("calendars_with_inactive")["items"]}


def _summary(name: str) -> str:
    text = (REPOSITORY / "fixtures" / "api" / f"{name}.json").read_text(encoding="utf-8")
    return json.loads(text)["summary"].lower()


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_each_refusal_by_field_names_its_fields_and_is_cited_by_its_operation(name: str) -> None:
    operations, fields = REFUSED[name]
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert [(field["pointer"], field["code"]) for field in refused["fields"]] == fields
    for operation in operations:
        assert name in _cited(operation), operation


def test_a_node_under_its_descendant_and_a_role_given_deactivated_objects_are_refused() -> None:
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    # The technical direction (470), a root, is an ancestor of the wiring workshop (472).
    workshop = nodes[universe(472)]
    assert nodes[workshop["parent_id"]]["parent_id"] == universe(470)
    assert nodes[universe(470)]["parent_id"] is None
    # The category the summary names is outside labour; the calendar, deactivated, is not the one
    # the technician has, which a role keeps without refusal.
    categories = fixture("volume/cost_categories")["items"]
    summary = _summary("resource_role_attachments_refused")
    [named] = [c for c in categories if f"à la {c['label'].lower()}," in summary]
    assert named["cost_type_kind"] == "non_labor"
    [week] = [c for c in _calendars().values() if not c["is_active"]]
    assert week["label"].lower() in summary
    assert week["label"].lower() in _summary("resource_role_update_refused")
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    assert roles[universe(452)]["calendar_id"] != week["calendar_id"]


def test_each_bound_crossed_is_the_one_its_refusal_names_and_the_universe_holds() -> None:
    _, headcount = fixture("resource_role_update_refused")["fields"]
    assert headcount["params"] == {"minimum": "0"}
    assert "effectif de -1" in _summary("resource_role_update_refused")
    monday, saturday = fixture("calendar_hours_refused")["fields"]
    assert (monday["params"], saturday["params"]) == ({"maximum": "24"}, {"minimum": "0"})
    assert "25 heures le lundi et -7 le samedi" in _summary("calendar_hours_refused")
    for calendar in _calendars().values():
        assert all(0 <= Decimal(v) <= 24 for v in calendar["weekly_hours"].values())
    for role in fixture("resource_roles")["items"]:
        assert all(Decimal(v) >= 0 for v in role["capacity"].values())


def test_a_node_taken_names_its_bearer_by_its_label_a_calendar_by_its_identifier() -> None:
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    [code] = fixture("org_node_code_taken")["fields"]
    bearer = nodes[code["params"]["conflicting_object_id"]]
    # The tree read without the deactivated nodes does not show the bearer: its label names it.
    assert bearer["is_active"] is False
    assert code["params"]["conflicting_object_label"] == bearer["label"]
    [label] = fixture("calendar_label_taken")["fields"]
    assert list(label["params"]) == ["conflicting_object_id"]
    for operation, expected in (
        ("createOrgNode", "org_node_code_taken"),
        ("updateOrgNode", "org_node_code_taken"),
        ("createCalendar", "calendar_label_taken"),
        ("updateCalendar", "calendar_label_taken"),
    ):
        assert expected in _cited(operation), operation


def test_only_a_move_is_refused_under_a_deactivated_node() -> None:
    # WF-REF-0070 bounds the move: the body takes the parent read, and a deactivated node that keeps
    # its deactivated parent is modified; the move refused gives another parent than the one read.
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes_with_inactive")}
    renamed = fixture("org_node_renamed_under_inactive")
    read = nodes[renamed["org_node_id"]]
    assert (read["is_active"], nodes[read["parent_id"]]["is_active"]) == (False, False)
    assert renamed["parent_id"] == read["parent_id"]
    assert renamed["label"] != read["label"]
    assert renamed["lock_version"] == read["lock_version"] + 1
    assert "org_node_renamed_under_inactive" in _cited("updateOrgNode")
    # The workshop (472), refused under the office of automation studies (474), leaves its own.
    assert nodes[universe(472)]["parent_id"] != universe(474)
    assert not nodes[universe(474)]["is_active"]
    assert "bureau d'études automatismes" in _summary("org_node_move_refused")


def test_a_designation_already_made_answers_without_change_after_the_version() -> None:
    # The default calendar lists no designation; sent anyway, the version is checked first, and the
    # answer changes nothing: the contract says it where the commands and the operation are.
    schema = (REPOSITORY / "docs" / "api" / "components" / "schemas" / "reference.yaml").read_text(
        encoding="utf-8"
    )
    commands = schema.split("\nCalendarCommands:\n", 1)[1].split("\n\n", 1)[0]
    text = PATHS.read_text(encoding="utf-8")
    operation = text.split("operationId: setDefaultCalendar\n", 1)[1].split("parameters:", 1)[0]
    for said in (commands, operation):
        flat = " ".join(said.split())
        assert "répond 200 sans rien changer" in flat
        assert "412 si elle est périmée" in flat


@pytest.mark.parametrize("name", sorted(STALE))
def test_each_stale_write_names_the_version_another_session_wrote(name: str) -> None:
    operation, written = STALE[name]
    refused = fixture(name)
    assert (refused["status"], refused["code"]) == (412, "STALE_LOCK_VERSION")
    assert refused["params"] == {"expected_lock_version": fixture(written)["lock_version"]}
    assert name in _cited(operation)


def test_each_calendar_but_the_default_lists_its_designation_available_when_active() -> None:
    calendars = [
        *_calendars().values(),
        *fixture("calendars")["items"],
        *(fixture(n) for n in ("calendar_created", "calendar_updated", "calendar_deactivated")),
        fixture("calendar_default"),
    ]
    for calendar in calendars:
        listed = [c for c in calendar["available_commands"] if c["command"] == "set_default"]
        missing = [] if calendar["is_active"] else ["calendar_active"]
        expected = [
            {"command": "set_default", "is_available": not missing, "missing_conditions": missing}
        ]
        assert listed == ([] if calendar["is_default"] else expected), calendar["label"]
    # The designation refused is that of the deactivated calendar, by the condition it misses.
    refused = fixture("calendar_default_refused")
    [week] = [c for c in _calendars().values() if not c["is_active"]]
    assert week["label"].lower() in _summary("calendar_default_refused")
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": "calendar_active"}
    assert "calendar_default_refused" in _cited("setDefaultCalendar")


def test_each_category_says_the_kind_of_its_nature_and_a_role_bears_one_of_labour() -> None:
    kinds = {n["cost_type_id"]: n["kind"] for n in fixture("cost_types_with_inactive")["items"]}
    categories = [
        *fixture("volume/cost_categories")["items"],
        *(fixture(n) for n in ("cost_category_created", "cost_category_updated")),
        fixture("cost_category_deactivated"),
    ]
    for category in categories:
        assert category["cost_type_kind"] == kinds[category["cost_type_id"]], category["code"]
    labour = {c["cost_category_id"] for c in categories if c["cost_type_kind"] == "labor"}
    assert {role["cost_category_id"] for role in fixture("resource_roles")["items"]} <= labour


def test_each_category_says_whether_its_nature_is_active_as_the_universe_reads_it() -> None:
    # `cost_type_is_active`, resolved at the reading (EP-14/L42p, revue 2): the natures of the
    # universe, never those of `cost_types_with_inactive`, where the disbursements are deactivated.
    natures = {n["cost_type_id"]: n for n in fixture("cost_types")["items"]}
    categories = [
        *fixture("volume/cost_categories")["items"],
        *(fixture(n) for n in ("cost_category_created", "cost_category_updated")),
        fixture("cost_category_deactivated"),
    ]
    for category in categories:
        nature = natures[category["cost_type_id"]]
        assert category["cost_type_is_active"] == nature["is_active"], category["code"]


def test_the_parent_is_required_to_modify_a_node() -> None:
    # An absent parent would read neither as the root nor as the parent read: the body is whole, a
    # root sends `null`, and « keeps its parent » is judged on the value sent (revue 2 of L42j).
    schema = (REPOSITORY / "docs" / "api" / "components" / "schemas" / "reference.yaml").read_text(
        encoding="utf-8"
    )
    block = re.split(r"\n(?=\S)", schema.split("\nOrgNodeUpdate:\n", 1)[1], maxsplit=1)[0]
    required = [
        {name.strip() for name in found.split(",")}
        for found in re.findall(r"required: \[([^\]]*)\]", block)
    ]
    assert {"lock_version", "parent_id"} in required
    # Redeclared in the branch, without which the generated client leaves it optional (revue 3).
    branch = block.split("required: [lock_version, parent_id]", 1)[1]
    assert "\n        parent_id:\n" in branch
    text = PATHS.read_text(encoding="utf-8")
    operation = text.split("operationId: updateOrgNode\n", 1)[1].split("operationId:", 1)[0]
    refusals = operation.split("'422':", 1)[1].split("content:", 1)[0]
    assert "`/parent_id` absent, par `VALUE_REQUIRED`" in " ".join(refusals.split())
