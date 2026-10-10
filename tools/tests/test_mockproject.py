# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the project, its subprojects and its contributors: commands and refusals (EP-14/L42i).

They try the examples of #590 and #592 against the universe they illustrate and against the
contract, the refusal to delete a subproject a marked revision cites (EP-14/L42l, #647) or that
lines of the current revision bear (EP-14/L42q, C-273) — not the Vérif of a requirement: none
cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
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
NOT_CITED = "subproject_not_cited"
WITHOUT_LINES = "subproject_without_estimate_lines"
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
CLOSED = "subprojects_completed"
"""The subprojects of the witness completed (`project_completed`), their commands all unavailable
(EP-14/L42o, #673)."""

TOLD: dict[str, tuple[int, str, list[tuple[str, str]], dict[str, Any]]] = {
    "project_code_taken": (409, "ALREADY_EXISTS", [("/code", "ALREADY_EXISTS")], {}),
    "project_reference_incomplete": (
        409,
        "REFERENCE_INCOMPLETE",
        [],
        {"missing_prerequisites": ["active_cost_category", "active_resource_role"]},
    ),
    "project_reference_without_provision": (
        409,
        "REFERENCE_INCOMPLETE",
        [],
        {"missing_prerequisites": ["active_provision_category"]},
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
    "subproject_delete_cited": (*FORBIDDEN, [], {"missing_condition": NOT_CITED}),
    "subproject_delete_refused": (*FORBIDDEN, [], {"missing_condition": WITHOUT_COSTS}),
    "subproject_delete_estimated": (
        *FORBIDDEN,
        [],
        {
            "missing_condition": WITHOUT_LINES,
            "estimate_lines": [
                {
                    "structure_id": universe(201),
                    "node_id": universe(553),
                    "row_number": 10,
                    "label": "Raccordement des borniers",
                },
                {
                    "structure_id": universe(201),
                    "node_id": universe(554),
                    "row_number": 11,
                    "label": "Borniers",
                },
            ],
        },
    ),
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
    "project_reference_without_provision": ["PRV-001", "variante contrefactuelle"],
    "project_creation_refused": ["sans libellé", "cinquante-et-un caractères"],
    "project_win_probability_frozen": ["ramenée à 0,8", "figée"],
    "project_rates_out_of_range": ["à 40", "à -0,01"],
    "subproject_code_taken": ["SP-CMD", "poste de commande"],
    "subproject_delete_cited": ["poste de commande", "1er février 2026", "facture des écrans"],
    "subproject_delete_refused": ["réception sur site", "FA-2026-0295", "aucune révision marquée"],
    "subproject_delete_estimated": [
        "réception sur site",
        "lignes 10 et 11 de la structure principale",
        "variante contrefactuelle",
    ],
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


def _cited_by_a_marked_revision() -> set[str]:
    """Return the subprojects a marked revision of the witness cites by a line it bears.

    The reference 101, on its whole structure: the lines of the core and of the lots « Poste de
    commande » bear the control station, those of the lots « Ligne d'essais » the tests and
    commissioning. The offer v1.0, marked before any subproject was declared, cites none.
    """
    created = min(
        each["audit"]["created_at"] for name in SUBPROJECTS for each in _subprojects(name)
    )
    cited: set[str] = set()
    for revision in fixture("revisions")["items"]:
        if revision["status"] != "marked":
            continue
        if revision["is_reference"]:
            cited |= {
                line.subproject
                for task in mockcore.tasks_in_order(mockcore.REFERENCE)
                for line in task.lines
                if line.subproject is not None
            }
        else:
            assert revision["marked_at"] < created, revision["revision_id"]
    return cited


def _own_estimate(structure: Entry) -> tuple[mockwitness.Task, ...]:
    """Return the tasks of the own estimate of a risk, as the universe describes them: none.

    The universe draws no line in the own estimate of a risk — its severity is read from its
    reviews (`mockwitness.Risk`) —; the structure is said, its lines bear no subproject.
    """
    [risk] = [
        r for r in fixture("risks")["items"] if r["structure_id"] == structure["structure_id"]
    ]
    assert risk["severity"], risk["label"]
    return ()


def _borne_by_the_current_revision() -> set[str]:
    """Return the subprojects the lines of the current revision 102 bear, on all its structures.

    The main structure whole — the core and the lots « Poste de commande » bear the control
    station, the lots « Ligne d'essais » the tests and commissioning —, and the own estimates of the
    risks, a line of which bears its subproject as any other (C-273); the subproject created today
    none.
    """
    current = fixture("project")["current_revision_id"]
    structures = [each for each in fixture("structures") if each["revision_id"] == current]
    assert {each["kind"] for each in structures} == {"main", "risk"}
    borne: set[str] = set()
    for structure in structures:
        roots = (
            mockstructure.described() if structure["kind"] == "main" else _own_estimate(structure)
        )
        borne |= {
            line.subproject
            for task in mockcore.tasks_in_order(roots)
            for line in task.lines
            if line.subproject is not None
        }
    return borne


def _subprojects(name: str) -> list[Entry]:
    read = fixture(name)
    return cast("list[Entry]", read if isinstance(read, list) else [read])


def _listed(
    subproject: Entry,
    cited: set[str],
    *,
    terminal: bool = False,
    borne: set[str] | None = None,
) -> list[tuple[str, bool, list[str]]]:
    """Return the commands a subproject lists to whom bears `update`.

    Its citation by a marked revision, then its costs, then the lines of the current revision that
    bear it, then the closing of its project say them, in that order (§4.4.1, WF-DAT-0080,
    WF-PRJ-0050, WF-CYC-0100): from the condition that never lifts to the one a move of the lines
    lifts, the conditions of the subproject before the one of the project, as a project lists its
    commands (`project_completed`).
    """
    borne = _borne_by_the_current_revision() if borne is None else borne
    closed = [NOT_TERMINAL] if terminal else []
    missing = [NOT_CITED] if subproject["subproject_id"] in cited else []
    missing += [WITHOUT_COSTS] if subproject["has_actual_costs"] else []
    missing += [WITHOUT_LINES] if subproject["subproject_id"] in borne else []
    missing += closed
    return [("update", not closed, closed), ("delete", not missing, missing)]


@pytest.mark.parametrize("name", SUBPROJECTS)
def test_each_subproject_lists_its_commands_as_its_citation_costs_and_lines_say(name: str) -> None:
    cited = _cited_by_a_marked_revision()
    for subproject in _subprojects(name):
        assert _commands(subproject) == _listed(subproject, cited), (name, subproject["code"])


def test_the_marked_reference_cites_both_subprojects_of_the_witness_not_the_created_one() -> None:
    # Since EP-14/L45a the reference bears the whole structure: the lots « Ligne d'essais » cite
    # the tests and commissioning, as the core and the lots « Poste de commande » the control
    # station. The subproject created today, after every marking, is cited by none.
    cited = _cited_by_a_marked_revision()
    assert cited == {universe(801), universe(802)}
    assert {each["subproject_id"] for each in fixture("subprojects")} == cited
    assert fixture("subproject_created")["subproject_id"] not in cited
    every = [NOT_CITED, WITHOUT_COSTS, WITHOUT_LINES]
    for name in ("subprojects", "subproject_updated"):
        for subproject in _subprojects(name):
            assert _commands(subproject)[1] == ("delete", False, every)
    assert _commands(fixture("subproject_created"))[1] == ("delete", False, [WITHOUT_COSTS])


def test_the_current_revision_bears_both_subprojects_of_the_witness_not_the_created_one() -> None:
    # C-273: the lines of the current revision bear the two subprojects of the witness, on its
    # whole structure; the subproject created today bears none.
    borne = _borne_by_the_current_revision()
    assert borne == {universe(801), universe(802)}
    assert fixture("subproject_created")["subproject_id"] not in borne


def test_every_subproject_of_the_examples_is_charged_and_none_offers_its_deletion() -> None:
    # The witness charges each of its subprojects since EP-14/L45a, the created one included
    # (#625): no example shows the deletion available (WF-PRJ-0050).
    cited = _cited_by_a_marked_revision()
    for name in SUBPROJECTS:
        for subproject in _subprojects(name):
            assert subproject["has_actual_costs"] is True, (name, subproject["code"])
            assert _commands(subproject)[1][1] is False, (name, subproject["code"])
    # The rule the test applies to the examples, fixed on variants built here rather than new
    # examples: relieved of its costs, the created subproject, which no marked revision cites,
    # would offer its deletion; the tests and commissioning, which the reference cites, would not
    # (§4.4.1).
    uncited = {**fixture("subproject_created"), "has_actual_costs": False}
    assert _listed(uncited, cited) == [("update", True, []), ("delete", True, [])]
    tests = {**fixture("subprojects")[1], "has_actual_costs": False}
    assert _listed(tests, cited) == [
        ("update", True, []),
        ("delete", False, [NOT_CITED, WITHOUT_LINES]),
    ]
    # Lines of the current revision passed to the created subproject relieved of its costs: its
    # deletion misses the lines alone, the variant of `subproject_delete_estimated` (C-273).
    estimated = _listed(uncited, cited, borne={cast("str", uncited["subproject_id"])})
    assert estimated == [("update", True, []), ("delete", False, [WITHOUT_LINES])]


def test_on_a_closed_project_the_conditions_of_the_subproject_come_before_its_closing() -> None:
    # The order a project lists its own commands in (`project_completed`): the condition proper to
    # the command first, `project_not_terminal` last. The subprojects of the witness completed
    # follow it (`subprojects_completed`, EP-14/L42o); a variant built here, uncited and
    # uncharged, misses the closing alone.
    assert fixture("project_completed")["state"] in TERMINAL
    completed = {
        each["command"]: each for each in fixture("project_completed")["available_commands"]
    }
    assert completed["update"]["missing_conditions"] == [NOT_TERMINAL]
    assert completed[WIN_PROBABILITY]["missing_conditions"] == [BEFORE_IN_PROGRESS, NOT_TERMINAL]
    cited = _cited_by_a_marked_revision()
    closed = _subprojects(CLOSED)
    for subproject in closed:
        assert subproject["subproject_id"] in cited, subproject["code"]
        assert _commands(subproject) == _listed(subproject, cited, terminal=True)
        assert _commands(subproject) == [
            ("update", False, [NOT_TERMINAL]),
            ("delete", False, [NOT_CITED, WITHOUT_COSTS, WITHOUT_LINES, NOT_TERMINAL]),
        ]
    # The same subprojects as those of the project in progress, their commands apart.
    unlisted = [{**each, "available_commands": None} for each in closed]
    assert unlisted == [{**each, "available_commands": None} for each in fixture("subprojects")]
    bare = {**fixture("subproject_created"), "has_actual_costs": False}
    assert _listed(bare, cited, terminal=True) == [
        ("update", False, [NOT_TERMINAL]),
        ("delete", False, [NOT_TERMINAL]),
    ]


def test_the_citation_by_a_marked_revision_is_a_condition_of_the_catalogue() -> None:
    conditions = enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )
    assert [c for c in conditions if c.startswith("subproject_")] == [
        NOT_CITED,
        WITHOUT_COSTS,
        WITHOUT_LINES,
    ]


@pytest.mark.parametrize(
    ("name", "read", "code"),
    [
        ("subproject_delete_cited", "subprojects", "SP-CMD"),
        ("subproject_delete_refused", "subproject_created", "SP-REC"),
    ],
)
def test_the_refused_deletion_names_the_first_condition_its_command_misses(
    name: str, read: str, code: str
) -> None:
    refused = fixture(name)
    [subproject] = [each for each in _subprojects(read) if each["code"] == code]
    _, available, missing = _commands(subproject)[1]
    assert not available
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert (refused["status"], refused["code"]) == FORBIDDEN
    assert refused["params"] == {"missing_condition": missing[0]}
    text = (SCHEMAS / "projects.yaml").read_text(encoding="utf-8")
    assert missing[0] in enumeration(text, "CommandCondition")
    assert enumeration(text, "SubprojectCommand") == ["update", "delete"]


def test_the_subprojects_of_the_closed_project_are_an_example_after_the_first() -> None:
    # Prism serves the first example of the listing: it stays the witness in progress.
    text = (API / "paths" / "projects.yaml").read_text(encoding="utf-8")
    block = text.split("operationId: listSubprojects\n", 1)[1].split("operationId:", 1)[0]
    cited = re.findall(r"fixtures/api/(\w+)\.json", block)
    assert cited[0] == "subprojects"
    assert CLOSED in cited[1:]


def test_both_refusals_of_a_deletion_are_examples_of_the_operation() -> None:
    text = (API / "paths" / "projects.yaml").read_text(encoding="utf-8")
    block = text.split("operationId: deleteSubproject\n", 1)[1].split("operationId:", 1)[0]
    for name in (
        "subproject_delete_cited",
        "subproject_delete_refused",
        "subproject_delete_estimated",
    ):
        assert f"fixtures/api/{name}.json" in block, name
    # The new example comes last: the first of each status is the one the fake back serves.
    assert block.index("subproject_delete_refused") < block.index("subproject_delete_estimated")


def test_a_line_of_provision_is_moved_off_a_subproject_by_its_risk() -> None:
    # The line of provision bears the subproject its risk designates, computed (EP-14/L42p): the
    # deletion refused for the lines that bear the subproject says how to move that one.
    text = (API / "paths" / "projects.yaml").read_text(encoding="utf-8")
    block = text.split("operationId: deleteSubproject\n", 1)[1].split("    parameters:", 1)[0]
    said = " ".join(block.split())
    assert (
        "une ligne de provision se passe par son risque (`updateRisk`, `provision_subproject_id`)"
        in said
    )
    assert "la décision contredit le Vérif" not in said


def test_the_lines_a_refused_deletion_names_are_lines_of_the_current_revision() -> None:
    # The Vérif of WF-DAT-0080 has the refusal name the lines: each by its structure, its node, its
    # number of row and its label, as the main structure of the current revision reads them.
    refused = fixture("subproject_delete_estimated")
    [main] = [s for s in fixture("structures") if s["kind"] == "main"]
    rows = {row.node["node_id"]: row.node for row in mockcore.current()}
    for line in refused["params"]["estimate_lines"]:
        assert line["structure_id"] == main["structure_id"]
        node = cast("Entry", rows[line["node_id"]])
        assert node["kind"] == "estimate_line"
        assert (node["row_number"], node["estimate_line"]["label"]) == (
            line["row_number"],
            line["label"],
        )
    numbers = [line["row_number"] for line in refused["params"]["estimate_lines"]]
    assert numbers == sorted(numbers)


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
        "subproject_delete_cited",
        "subproject_delete_estimated",
        "cost_type_kind_refused",
        "backup_retain_refused",
        "restore_unverified_refused",
        "risk_delete_cited",
        "calendar_default_refused",
    } <= named.keys()
    for name, refused in named.items():
        assert (refused["status"], refused["code"]) == FORBIDDEN, name
        assert "fields" not in refused, name


def test_the_prerequisites_refused_are_those_the_readiness_names_in_its_order() -> None:
    text = (SCHEMAS / "reference.yaml").read_text(encoding="utf-8")
    readiness = enumeration(text, "ReferenceReadiness", "missing")
    # The four prerequisites of WF-CYC-0120, in its order: the category of provision for risks
    # among them since EP-14/L42p (#579).
    assert readiness == [
        "default_calendar_with_hours",
        "active_cost_category",
        "active_provision_category",
        "active_resource_role",
    ]
    for name in ("project_reference_incomplete", "project_reference_without_provision"):
        missing = fixture(name)["params"]["missing_prerequisites"]
        assert missing == [each for each in readiness if each in missing], name
    for name in ("reference_readiness_incomplete", "reference_readiness_without_provision"):
        read = fixture(name)
        assert read["is_complete"] is False
        assert read["missing"] == [each for each in readiness if each in read["missing"]], name


def test_an_enumeration_is_read_in_line_or_one_a_line() -> None:
    text = "\nA:\n  type: string\n  enum: [x, y]\n\nB:\n  enum:\n    - p\n    - q\n\nC:\n"
    text += "  properties:\n    f:\n      items:\n        enum: [m]\n\n"
    assert enumeration(text, "A") == ["x", "y"]
    assert enumeration(text, "B") == ["p", "q"]
    assert enumeration(text, "C", "f") == ["m"]
