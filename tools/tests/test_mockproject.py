# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the project, its subprojects and its contributors: commands and refusals (EP-14/L42i).

They try the examples of #590 and #592 against the universe they illustrate and against the
contract, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre
aucune exigence »).
"""

import json
import re
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockcore, mockstructure, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
SCHEMAS = API / "components" / "schemas"

WIN_PROBABILITY = "update_win_probability"
BEFORE_IN_PROGRESS = "project_before_in_progress"
NOT_TERMINAL = "project_not_terminal"
WITHOUT_COSTS = "subproject_without_actual_costs"
FORBIDDEN = (409, "STATE_FORBIDS_OPERATION")
"""The one envelope of a command a state makes unavailable, its condition named (EP-02/L42a)."""

OPEN = ("created", "pricing")
"""The states in which the win probability is modifiable (WF-PRJ-0090)."""
TERMINAL = ("completed", "lost", "abandoned")

ZERO, ONE = Decimal(0), Decimal(1)
"""The bounds of the two rates of a project, ratios (WF-PRJ-0040, WF-PRJ-0090)."""

NEXT = {
    "project": "next_state",
    "project_created": "next_state_created",
    "project_pricing": "next_state_pricing",
    "project_completed": "next_state_completed",
}
"""The reading of the next state of each project example (`getProjectNextState`)."""

TRIGGERS = {
    "created": ("pricing", "first_revision_created"),
    "pricing": ("in_progress", "reference_designated_and_code_set"),
}
"""The next state and the trigger of each state before pricing is left (WF-CYC-0020)."""

SUBPROJECTS = (
    "subprojects",
    "subprojects_by_label",
    "subprojects_with_actual_costs",
    "subproject_created",
    "subproject_updated",
)
"""The examples that read or write subprojects, each with its commands."""

TOLD: dict[str, tuple[int, str, list[tuple[str, str]], dict[str, Any]]] = {
    "project_code_taken": (409, "ALREADY_EXISTS", [("/code", "ALREADY_EXISTS")], {}),
    "project_reference_incomplete": (
        409,
        "REFERENCE_INCOMPLETE",
        [],
        {"missing_prerequisites": ["active_cost_category", "active_resource_role"]},
    ),
    "project_creation_refused": (
        422,
        "VALIDATION_FAILED",
        [("/label", "VALUE_REQUIRED"), ("/code", "VALUE_TOO_LONG")],
        {},
    ),
    "project_win_probability_frozen": (
        *FORBIDDEN,
        [],
        {"missing_condition": BEFORE_IN_PROGRESS},
    ),
    "project_rates_out_of_range": (
        422,
        "VALIDATION_FAILED",
        [("/win_probability", "VALUE_OUT_OF_RANGE"), ("/inflation_rate", "VALUE_OUT_OF_RANGE")],
        {},
    ),
    "subproject_code_taken": (409, "ALREADY_EXISTS", [("/code", "ALREADY_EXISTS")], {}),
    "subproject_delete_refused": (*FORBIDDEN, [], {"missing_condition": WITHOUT_COSTS}),
    "contributors_without_manager_refused": (409, "LAST_PROJECT_MANAGER", [], {}),
    "contributors_accounts_refused": (
        422,
        "VALIDATION_FAILED",
        [("/contributors/1/user_id", "USER_INACTIVE"), ("/contributors/4/user_id", "UNKNOWN_USER")],
        {},
    ),
}
"""What each refusal of the project, its subprojects and its contributors tells, as its summary
says it: its status and code, the fields it names with their motive, in order, and its
parameters."""

SAID = {
    "project_code_taken": ["PRJ-001", "rénovation du poste de livraison"],
    "project_reference_incomplete": ["aucune catégorie de coût active", "aucun rôle de ressources"],
    "project_creation_refused": ["sans libellé", "cinquante-et-un caractères"],
    "project_win_probability_frozen": ["ramenée à 0,8", "figée"],
    "project_rates_out_of_range": ["à 40", "à -0,01"],
    "subproject_code_taken": ["SP-CMD", "poste de commande"],
    "subproject_delete_refused": ["poste de commande", "facture des écrans"],
    "contributors_without_manager_refused": ["sans aucun chef de projet"],
    "contributors_accounts_refused": ["Alix Moreau", "deuxième ligne", "cinquième"],
}
"""What the summary of each refusal says of the value sent, by the fields and motives it tells."""


def _every_example() -> dict[str, Any]:
    return {
        path.relative_to(mockwitness.FIXTURES).with_suffix("").as_posix(): json.loads(
            path.read_text(encoding="utf-8")
        )
        for path in sorted(mockwitness.FIXTURES.rglob("*.json"))
    }


@pytest.fixture(scope="module")
def examples() -> dict[str, Any]:
    """Read every example once, its summary with its value."""
    return _every_example()


def _walk(value: Any) -> list[Entry]:
    """Return every object a value read from JSON holds, itself included."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _walk(item)]
    if not isinstance(value, dict):
        return []
    entry = cast("Entry", value)
    return [entry, *(found for item in entry.values() for found in _walk(item))]


def _projects(examples: dict[str, Any]) -> dict[str, list[Entry]]:
    """Return the projects every example reads whole (`Project`), by example."""
    keys = {"project_id", "state", "win_probability", "available_commands"}
    found = {
        name: [entry for entry in _walk(example["value"]) if keys <= entry.keys()]
        for name, example in examples.items()
    }
    return {name: projects for name, projects in found.items() if projects}


def _commands(entry: Entry) -> list[tuple[str, bool, list[str]]]:
    return [
        (each["command"], each["is_available"], each["missing_conditions"])
        for each in entry["available_commands"]
    ]


def enumeration(text: str, schema: str, field: str | None = None) -> list[str]:
    """Return the values an enumeration of a schema file declares, in line or one a line."""
    block = text.split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]
    if field is not None:
        block = block.split(f"\n    {field}:\n", 1)[1]
    found = re.search(r"enum: \[(?P<line>[^\]]*)\]", block)
    if found is not None:
        return [value.strip() for value in found["line"].split(",")]
    listed = block.split("enum:\n", 1)[1]
    return [line.strip()[2:] for line in listed.splitlines() if line.strip().startswith("- ")]


# --- The win probability, frozen from in progress (#590) ------------------------------------------


def test_the_win_probability_command_follows_update_and_is_frozen_from_in_progress(
    examples: dict[str, Any],
) -> None:
    projects = _projects(examples)
    assert {"project", "projects", "project_completed", "project_reader"} <= projects.keys()
    for name, listed in projects.items():
        for project in listed:
            commands = _commands(project)
            names = [command for command, _, _ in commands]
            if "update" not in names:
                assert WIN_PROBABILITY not in names, name
                continue
            assert names.index(WIN_PROBABILITY) == names.index("update") + 1, name
            state = project["state"]
            missing = [] if state in OPEN else [BEFORE_IN_PROGRESS]
            missing += [NOT_TERMINAL] if state in TERMINAL else []
            assert (WIN_PROBABILITY, not missing, missing) in commands, (name, state)


def test_the_frozen_win_probability_is_refused_by_the_condition_its_command_misses() -> None:
    witness, refused = fixture("project"), fixture("project_win_probability_frozen")
    assert witness["state"] == "in_progress"
    [(_, available, missing)] = [c for c in _commands(witness) if c[0] == WIN_PROBABILITY]
    assert (available, missing) == (False, [BEFORE_IN_PROGRESS])
    # The envelope of the frozen kind of a cost type (`cost_type_kind_refused`, EP-02/L42g).
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert (refused["status"], refused["code"]) == FORBIDDEN
    assert refused["params"] == {"missing_condition": missing[0]}
    assert BEFORE_IN_PROGRESS in enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )


def test_the_rates_of_every_project_lie_within_the_bounds_the_refusal_names(
    examples: dict[str, Any],
) -> None:
    for name, listed in _projects(examples).items():
        for project in listed:
            for rate in ("inflation_rate", "win_probability"):
                assert ZERO <= Decimal(project[rate]) <= ONE, (name, rate)
    refused = examples["project_rates_out_of_range"]["value"]
    bounds = {field["pointer"]: field["params"] for field in refused["fields"]}
    assert bounds == {"/win_probability": {"maximum": "1"}, "/inflation_rate": {"minimum": "0"}}
    assert Decimal(bounds["/win_probability"]["maximum"]) == ONE
    assert Decimal(bounds["/inflation_rate"]["minimum"]) == ZERO


# --- The next state and its trigger (#590) ------------------------------------------------------


@pytest.mark.parametrize(("project", "reading"), sorted(NEXT.items()))
def test_the_next_state_of_each_project_follows_its_state_and_names_a_trigger_of_the_lifecycle(
    project: str, reading: str
) -> None:
    read, state = fixture(reading), fixture(project)["state"]
    triggers = enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "LifecycleTrigger"
    )
    assert read["current_state"] == state
    if state in TRIGGERS:
        following, trigger = TRIGGERS[state]
        assert (read["next_state"], read["trigger"]) == (following, trigger)
        assert trigger in triggers
        conditions = {"reference_revision_designated", "project_code_set"}
        assert set(read["missing_conditions"]) <= conditions
        if state == "pricing":
            # The code is a condition of the passage to in progress alone (WF-CYC-0030).
            coded = fixture(project)["code"] is not None
            assert ("project_code_set" in read["missing_conditions"]) is not coded
    else:
        # In progress or terminal: no fact leads the project further (WF-CYC-0050, WF-CYC-0060).
        assert state == "in_progress" or state in TERMINAL
        assert (read["next_state"], read["trigger"], read["missing_conditions"]) == (None, None, [])


def test_the_triggers_are_the_two_facts_of_the_lifecycle() -> None:
    text = (SCHEMAS / "projects.yaml").read_text(encoding="utf-8")
    assert sorted(enumeration(text, "LifecycleTrigger")) == sorted(
        trigger for _, trigger in TRIGGERS.values()
    )
    assert "$ref: '#/LifecycleTrigger'" in text.split("\nNextState:\n", 1)[1].split("\n\n", 1)[0]


# --- The subprojects and their commands (#592, #625) ---------------------------------------------


def _cited_by_the_reference() -> set[str]:
    """Return the subprojects a line of the reference 101, marked, bears (WF-DAT-0080)."""
    return {
        line.subproject
        for task in mockcore.tasks_in_order(mockwitness.reference())
        for line in task.lines
        if line.subproject is not None
    }


def _subprojects(name: str) -> list[Entry]:
    read = fixture(name)
    return cast("list[Entry]", read if isinstance(read, list) else [read])


def _listed(subproject: Entry) -> list[tuple[str, bool, list[str]]]:
    """Return the commands a subproject lists to whom bears `update`: its costs alone say them."""
    missing = [WITHOUT_COSTS] if subproject["has_actual_costs"] else []
    return [("update", True, []), ("delete", not missing, missing)]


@pytest.mark.parametrize("name", SUBPROJECTS)
def test_each_subproject_lists_its_commands_as_its_costs_alone_say(name: str) -> None:
    for subproject in _subprojects(name):
        assert _commands(subproject) == _listed(subproject), (name, subproject["code"])


def test_every_subproject_of_the_examples_misses_its_costs_the_uncharged_one_nothing() -> None:
    # The witness charges each of its subprojects since EP-14/L45a, the created one included
    # (#625): no example shows the deletion available (WF-PRJ-0050).
    for name in SUBPROJECTS:
        for subproject in _subprojects(name):
            assert subproject["has_actual_costs"] is True, (name, subproject["code"])
            assert _commands(subproject)[1] == ("delete", False, [WITHOUT_COSTS])
    # The other side of the rule, on a variant built here rather than a new example.
    uncharged = {**fixture("subprojects")[1], "has_actual_costs": False}
    assert _listed(uncharged) == [("update", True, []), ("delete", True, [])]


def test_a_subproject_the_marked_reference_cites_keeps_no_condition_from_it() -> None:
    # The deletion of a subproject a marked revision cites succeeds and marks it deleted
    # (WF-DAT-0080): only the actual costs charged to it ground a refusal (WF-PRJ-0050).
    cited = _cited_by_the_reference()
    assert cited == {universe(801)}
    [control] = [each for each in fixture("subprojects") if each["subproject_id"] in cited]
    assert _commands(control)[1] == ("delete", False, [WITHOUT_COSTS])
    conditions = enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )
    assert [c for c in conditions if c.startswith("subproject_")] == [WITHOUT_COSTS]
    assert not [c for c in conditions if "subproject" in c and "cited" in c]


def test_the_refused_deletion_names_the_condition_its_command_misses() -> None:
    refused = fixture("subproject_delete_refused")
    [control] = [each for each in fixture("subprojects") if each["code"] == "SP-CMD"]
    _, available, missing = _commands(control)[1]
    assert not available
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert (refused["status"], refused["code"]) == FORBIDDEN
    assert refused["params"] == {"missing_condition": missing[0]}
    text = (SCHEMAS / "projects.yaml").read_text(encoding="utf-8")
    assert WITHOUT_COSTS in enumeration(text, "CommandCondition")
    assert enumeration(text, "SubprojectCommand") == ["update", "delete"]


# --- A code taken names the object that bears it, by its label (#590, #592) ---------------------


@pytest.mark.parametrize(
    ("name", "listed", "key"),
    [
        ("project_code_taken", "projects", "project_id"),
        ("subproject_code_taken", "subprojects", "subproject_id"),
    ],
)
def test_a_code_taken_names_the_object_that_bears_it_by_its_identifier_and_its_label(
    examples: dict[str, Any], name: str, listed: str, key: str
) -> None:
    example = examples[name]
    refused, summary = example["value"], example["summary"]
    read = fixture(listed)
    objects = {
        entry[key]: entry
        for entry in cast("list[Entry]", read["items"] if isinstance(read, dict) else read)
    }
    assert (refused["status"], refused["code"]) == (409, "ALREADY_EXISTS")
    assert "params" not in refused
    [field] = refused["fields"]
    assert (field["pointer"], field["code"]) == ("/code", "ALREADY_EXISTS")
    assert list(field["params"]) == ["conflicting_object_id", "conflicting_object_label"]
    bearer = objects[field["params"]["conflicting_object_id"]]
    assert field["params"]["conflicting_object_label"] == bearer["label"]
    assert bearer["code"] in summary


def test_every_write_of_a_project_or_subproject_code_says_the_label_of_its_bearer() -> None:
    text = (API / "paths" / "projects.yaml").read_text(encoding="utf-8")
    for operation in ("createProject", "updateProject", "createSubproject", "updateSubproject"):
        block = text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]
        found = re.search(r"\n      '409':\n(?P<said>(?:        .*\n|\n)+)", block)
        assert found is not None, operation
        assert "`fields[].params.conflicting_object_label`" in found["said"], operation


# --- The contributors (#592) ---------------------------------------------------------------------


def _accounts() -> dict[str, Entry]:
    return {account["user_id"]: account for account in fixture("users")["items"]}


def test_a_refused_list_of_contributors_points_at_the_accounts_at_their_rows(
    examples: dict[str, Any],
) -> None:
    example = examples["contributors_accounts_refused"]
    refused, summary = example["value"], example["summary"]
    accounts = _accounts()
    assert "params" not in refused
    rows: list[int] = []
    for field in refused["fields"]:
        found = re.fullmatch(r"/contributors/(?P<row>\d+)/user_id", field["pointer"])
        assert found is not None, field
        assert "params" not in field
        rows.append(int(found["row"]))
    # The deactivated account the summary names is the one of the universe (WF-ADM-0060), at the
    # second row of the list of the witness; the unknown account is a fifth row the list has not.
    [alix] = [each for each in accounts.values() if each["is_active"] is False]
    assert f"{alix['first_name']} {alix['last_name']}" in summary
    contributors = fixture("contributors")["items"]
    assert len(contributors) == 4
    assert contributors[1]["user_id"] == alix["user_id"]
    assert contributors[1]["display_name"] == "Alix Moreau"
    assert rows == [1, 4]
    assert rows[1] == len(contributors)


def test_the_list_without_a_manager_is_refused_without_parameter() -> None:
    refused = fixture("contributors_without_manager_refused")
    assert set(refused) == {"code", "status", "correlation_id"}
    managers = [c for c in fixture("contributors")["items"] if c["kind"] == "project_manager"]
    assert len(managers) == 1


def test_each_suggestion_names_its_node_and_its_roles_as_the_reference_reads_them() -> None:
    accounts = _accounts()
    nodes = {node["org_node_id"]: node for node in fixture("org_nodes")}
    roles = {role["resource_role_id"]: role for role in fixture("resource_roles")["items"]}
    # The roles the estimate employs: those of the core, and of the structure drawn around it.
    employed = {line.role for task in mockcore.tasks_in_order() for line in task.lines if line.role}
    employed |= {kind.role for kind in mockstructure.CABLING_KINDS if kind.role is not None}
    inscribed = {each["user_id"] for each in fixture("contributors")["items"]}
    suggestions = fixture("contributor_suggestions")
    assert suggestions
    for suggestion in suggestions:
        account = accounts[suggestion["user_id"]]
        assert suggestion["user_id"] not in inscribed
        assert suggestion["is_active"] is True
        assert account["is_active"] is True
        assert suggestion["display_name"] == f"{account['first_name']} {account['last_name']}"
        assert suggestion["org_node_id"] == account["org_node_id"]
        assert suggestion["org_node_label"] == nodes[suggestion["org_node_id"]]["label"]
        assert suggestion["resource_role_ids"]
        assert suggestion["resource_role_labels"] == [
            roles[role]["label"] for role in suggestion["resource_role_ids"]
        ]
        for role in suggestion["resource_role_ids"]:
            # Proposed for a role of its node the estimate employs (WF-PRJ-0070).
            assert roles[role]["org_node_id"] == suggestion["org_node_id"]
            assert role in employed


# --- Each refusal tells what its summary says -----------------------------------------------------


@pytest.mark.parametrize("name", sorted(TOLD))
def test_each_refusal_tells_its_fields_and_motives_as_its_summary_says(
    examples: dict[str, Any], name: str
) -> None:
    refused, summary = examples[name]["value"], examples[name]["summary"]
    status, code, fields, params = TOLD[name]
    assert (refused["status"], refused["code"]) == (status, code)
    assert [(field["pointer"], field["code"]) for field in refused.get("fields", [])] == fields
    assert refused.get("params", {}) == params
    for said in SAID[name]:
        assert said in summary, said


def test_every_refusal_told_has_what_its_summary_says() -> None:
    assert SAID.keys() == TOLD.keys()


def test_every_refusal_that_names_a_missing_condition_is_the_one_envelope_of_a_command(
    examples: dict[str, Any],
) -> None:
    # A field a command freezes is refused by the condition of that command, as the kind of a cost
    # type is (EP-02/L42g): one envelope, whatever the screen (WF-IHM-0090, WF-ARC-0110).
    named = {
        name: example["value"]
        for name, example in examples.items()
        if isinstance(example["value"], dict)
        and "missing_condition" in cast("Entry", example["value"]).get("params", {})
    }
    assert {
        "project_win_probability_frozen",
        "subproject_delete_refused",
        "cost_type_kind_refused",
        "backup_retain_refused",
        "restore_unverified_refused",
        "risk_delete_cited",
    } <= named.keys()
    for name, refused in named.items():
        assert (refused["status"], refused["code"]) == FORBIDDEN, name
        assert "fields" not in refused, name


def test_the_prerequisites_refused_are_those_the_readiness_names() -> None:
    refused = fixture("project_reference_incomplete")
    text = (SCHEMAS / "reference.yaml").read_text(encoding="utf-8")
    readiness = enumeration(text, "ReferenceReadiness", "missing")
    assert set(refused["params"]["missing_prerequisites"]) <= set(readiness)
    assert "default_calendar_with_hours" in readiness


def test_an_enumeration_is_read_in_line_or_one_a_line() -> None:
    text = "\nA:\n  type: string\n  enum: [x, y]\n\nB:\n  enum:\n    - p\n    - q\n\nC:\n"
    text += "  properties:\n    f:\n      items:\n        enum: [m]\n\n"
    assert enumeration(text, "A") == ["x", "y"]
    assert enumeration(text, "B") == ["p", "q"]
    assert enumeration(text, "C", "f") == ["m"]
