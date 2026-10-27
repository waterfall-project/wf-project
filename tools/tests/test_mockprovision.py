# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the category of provision for risks a risk designates, and its subproject (EP-14/L42p).

They try the examples of #579 and C-299 against the universe they illustrate and against the
contract — the prerequisite of the creation of a project, the refusals of the declaration and of the
change of a provision —, not the Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui
ne couvre aucune exigence »).
"""

import json
import re
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockdata, mockhistory, mockreference, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
SCHEMAS = API / "components" / "schemas"

ACTIVE_PROVISION = "active_provision_category"
"""The condition and the prerequisite an active category of provision for risks holds."""

COUNTERFACTUAL = "Une variante contrefactuelle"
"""What the summary of an example the witness does not reach says of it."""


def _summary(name: str) -> str:
    return json.loads((mockwitness.FIXTURES / f"{name}.json").read_text(encoding="utf-8"))[
        "summary"
    ]


def _block(operation: str, status: str) -> str:
    """Return what a status of an operation of the contract declares, examples included."""
    for path in sorted((API / "paths").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if f"operationId: {operation}\n" not in text:
            continue
        block = text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]
        found = re.search(rf"\n      '{status}':\n(?P<said>(?:        .*\n|\n)+)", block)
        assert found is not None, (operation, status)
        return found["said"]
    message = f"{operation} is no operation of the contract"
    raise AssertionError(message)


def _enumeration(text: str, schema: str) -> list[str]:
    block = text.split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]
    listed = block.split("enum:\n", 1)[1]
    return [line.strip()[2:] for line in listed.splitlines() if line.strip().startswith("- ")]


def _provision_categories() -> list[Entry]:
    """Return the categories of the witness whose nature is of the kind provision for risks."""
    natures = {n["cost_type_id"]: n["kind"] for n in fixture("cost_types")["items"]}
    return [
        category
        for category in fixture("volume/cost_categories")["items"]
        if natures[category["cost_type_id"]] == "provision"
    ]


# --- The prerequisite and its refusals (#579) -----------------------------------------------------


def test_the_witness_has_one_active_category_of_provision_the_counterfactuals_deactivate() -> None:
    # PRV-001 is the one category of provision for risks of the witness: the examples that miss an
    # active one deactivate it, and say they are counterfactual (WF-CYC-0120, WF-RIS-0010).
    [category] = _provision_categories()
    assert (category["cost_category_id"], category["code"]) == (universe(404), "PRV-001")
    assert category["is_active"] is True
    for name in (
        "reference_readiness_without_provision",
        "project_reference_without_provision",
        "risk_without_provision_category",
    ):
        assert "PRV-001" in _summary(name), name
        assert COUNTERFACTUAL in _summary(name), name
    assert fixture("reference_readiness_without_provision") == {
        "is_complete": False,
        "missing": [ACTIVE_PROVISION],
    }
    assert fixture("reference_readiness")["missing"] == []


def test_the_declaration_without_an_active_category_names_the_condition_it_misses() -> None:
    refused = fixture("risk_without_provision_category")
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": ACTIVE_PROVISION}
    conditions = _enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )
    assert ACTIVE_PROVISION in conditions
    assert "fixtures/api/risk_without_provision_category.json" in _block("createRisk", "409")
    assert f"`{ACTIVE_PROVISION}`" in _block("reviewRisk", "409")


@pytest.mark.parametrize(
    ("operation", "status", "first", "new"),
    [
        (
            "getReferenceReadiness",
            "200",
            "reference_readiness",
            "reference_readiness_without_provision",
        ),
        (
            "createProject",
            "409",
            "project_reference_incomplete",
            "project_reference_without_provision",
        ),
    ],
)
def test_each_new_example_comes_after_the_first_its_status_serves(
    operation: str, status: str, first: str, new: str
) -> None:
    said = _block(operation, status)
    assert said.index(f"fixtures/api/{first}.json") < said.index(f"fixtures/api/{new}.json")


# --- The category and the subproject a risk designates (#579, C-299) -----------------------------


def test_the_refused_declaration_names_a_labour_category_and_a_subproject_unknown() -> None:
    refused = fixture("risk_provision_refused")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert "params" not in refused
    assert [(f["pointer"], f["code"]) for f in refused["fields"]] == [
        ("/provision_cost_category_id", "PROVISION_CATEGORY_REQUIRED"),
        ("/provision_subproject_id", "UNKNOWN_SUBPROJECT"),
    ]
    # The category the summary names is one of labour: of a nature of another kind.
    summary = _summary("risk_provision_refused")
    [named] = [
        c for c in fixture("volume/cost_categories")["items"] if c["label"].lower() in summary
    ]
    assert named["cost_type_kind"] == "labor"
    said = _block("createRisk", "422")
    assert "fixtures/api/risk_provision_refused.json" in said
    for code in ("VALUE_REQUIRED", "UNKNOWN_COST_CATEGORY", "INACTIVE_REFERENCE_OBJECT"):
        assert f"`{code}`" in said, code
    common = (API / "components" / "common.yaml").read_text(encoding="utf-8")
    codes = _enumeration(common, "ErrorCode")
    assert {"PROVISION_CATEGORY_REQUIRED", "UNKNOWN_SUBPROJECT"} <= set(codes)


def test_the_probability_sent_as_a_percent_is_refused_with_the_bound_it_crosses() -> None:
    # Written by hand, like its sibling above: 120 sent for a ratio, refused at its maximum,
    # which the front says as a percent (WF-RIS-0010).
    # Its correlation is its own: test_each_correlation_is_told_by_one_example_alone
    # (test_mockuniverse.py) reads every fixture, those written by hand included.
    refused = fixture("risk_probability_out_of_range")
    assert set(refused) == {"code", "status", "fields", "correlation_id"}
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    assert refused["fields"] == [
        {"pointer": "/probability", "code": "VALUE_OUT_OF_RANGE", "params": {"maximum": "1"}}
    ]
    assert refused["correlation_id"] == universe(1306)
    assert "WF-RIS-0010" in _summary("risk_probability_out_of_range")
    said = _block("createRisk", "422")
    assert said.index("fixtures/api/risk_provision_task_refused.json") < said.index(
        "fixtures/api/risk_probability_out_of_range.json"
    )
    assert "`/probability` hors de 0 à 1, `VALUE_OUT_OF_RANGE`" in _flat(said)


def test_the_probability_sent_as_a_percent_is_refused_alike_when_the_risk_is_modified() -> None:
    # The change says the bound of the declaration, by an example of its own, which the fake
    # client of the front serves to it alone (#1371).
    declared = fixture("risk_probability_out_of_range")
    modified = fixture("risk_update_probability_out_of_range")
    assert set(modified) == set(declared)
    assert (modified["status"], modified["code"], modified["fields"]) == (
        declared["status"],
        declared["code"],
        declared["fields"],
    )
    assert modified["correlation_id"] == universe(1307)
    summary = _summary("risk_update_probability_out_of_range")
    assert summary.startswith("Un risque modifié")
    assert "WF-RIS-0010" in summary
    said = _block("updateRisk", "422")
    assert "fixtures/api/risk_update_probability_out_of_range.json" in said
    assert "fixtures/api/risk_probability_out_of_range.json" not in said
    assert "`/probability` hors de 0 à 1, `VALUE_OUT_OF_RANGE`" in _flat(said)


def test_the_probability_sent_as_a_percent_is_refused_alike_when_the_risk_is_reviewed() -> None:
    # The review says the bound of the declaration, by an example of its own, as the change does,
    # and its body says it as RiskWrite does (#1371).
    declared = fixture("risk_probability_out_of_range")
    reviewed = fixture("risk_review_probability_out_of_range")
    assert set(reviewed) == set(declared)
    assert (reviewed["status"], reviewed["code"], reviewed["fields"]) == (
        declared["status"],
        declared["code"],
        declared["fields"],
    )
    assert reviewed["correlation_id"] == universe(1309)
    summary = _summary("risk_review_probability_out_of_range")
    assert summary.startswith("Un risque réexaminé")
    assert "WF-RIS-0010" in summary
    said = _block("reviewRisk", "422")
    assert "fixtures/api/risk_review_probability_out_of_range.json" in said
    assert "fixtures/api/risk_probability_out_of_range.json" not in said
    assert "`/probability` hors de 0 à 1, `VALUE_OUT_OF_RANGE`" in _flat(said)
    bound = "De `0` à `1` inclus, un rapport (WF-RIS-0010)."
    assert bound in _schema("risks.yaml", "RiskReviewWrite")
    assert bound in _schema("risks.yaml", "RiskWrite")


def test_the_review_of_a_risk_occurred_is_refused_by_the_condition_its_command_misses() -> None:
    # Written by hand, a static refusal: no transition leaves the state occurred (WF-RIS-0020).
    refused = fixture("risk_review_occurred")
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["correlation_id"] == universe(1310)
    summary = _summary("risk_review_occurred")
    [risk] = [r for r in fixture("risks")["items"] if r["label"] in summary]
    assert risk["state"] == "occurred"
    commands = {each["command"]: each for each in risk["available_commands"]}
    assert commands["review"]["missing_conditions"] == [refused["params"]["missing_condition"]]
    assert "fixtures/api/risk_review_occurred.json" in _block("reviewRisk", "409")


def test_the_provision_of_a_dismissed_risk_is_refused_by_the_condition_its_command_misses() -> None:
    refused = fixture("risk_provision_frozen")
    assert set(refused) == {"code", "status", "params", "correlation_id"}
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    summary = _summary("risk_provision_frozen")
    [risk] = [r for r in fixture("risks")["items"] if r["label"].lower() in summary.lower()]
    assert risk["state"] == "dismissed"
    commands = {each["command"]: each for each in risk["available_commands"]}
    assert commands["update"]["is_available"] is True
    assert commands["update_provision"]["missing_conditions"] == [
        refused["params"]["missing_condition"]
    ]
    assert "fixtures/api/risk_provision_frozen.json" in _block("updateRisk", "409")


def test_the_change_of_a_provision_is_a_command_listed_after_the_update() -> None:
    commands = _enumeration((SCHEMAS / "risks.yaml").read_text(encoding="utf-8"), "RiskCommand")
    assert commands == ["update", "update_provision", "review", "declare_occurrence", "delete"]
    for risk in fixture("risks")["items"]:
        listed = [each["command"] for each in risk["available_commands"]]
        assert listed == commands, risk["label"]


# --- The answers of the first review (revue 1) ---------------------------------------------------


def _flat(text: str) -> str:
    """Return a text of the contract with its line breaks and indents read as single spaces."""
    return " ".join(text.split())


def _schema(file: str, name: str) -> str:
    """Return the text of a schema of a file of the contract, up to the next one, flattened."""
    text = (SCHEMAS / file).read_text(encoding="utf-8")
    return _flat(text.split(f"\n{name}:\n", 1)[1].split("\n\n", 1)[0])


def _description(operation: str) -> str:
    for path in sorted((API / "paths").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if f"operationId: {operation}\n" in text:
            block = text.split(f"operationId: {operation}\n", 1)[1]
            return _flat(block.split("    parameters:", 1)[0].split("    responses:", 1)[0])
    message = f"{operation} is no operation of the contract"
    raise AssertionError(message)


def test_with_c291_a_nature_deactivates_its_categories_and_the_provisional_definition_is_gone() -> (
    None
):
    # C-291, now in the contract (#728, EP-14/L42s): « Désactiver une nature de coût désactive ses
    # catégories ; une catégorie ne peut être réactivée que si sa nature est active » (WF-REF-0010).
    for path in sorted(API.rglob("*.yaml")):
        assert "jusqu'à C-291" not in _flat(path.read_text(encoding="utf-8")), path.name
    assert "désactive ses catégories" in _description("setCostTypeActivation")
    assert "ne compte pas pour `active_provision_category`" not in _description(
        "setCostTypeActivation"
    )
    assert "`cost_type_active`" in _description("setCostCategoryActivation")
    assert "se réactive même sous une nature désactivée" not in _description(
        "setCostCategoryActivation"
    )
    said = _flat(_block("setCostCategoryActivation", "409"))
    assert "`cost_type_active`" in said
    assert "fixtures/api/cost_category_reactivation_refused.json" in said
    # The refusal names the nature to reactivate first, as that of a node names its parent (#532,
    # WF-IHM-0090): the debours, deactivated by `cost_type_deactivated` (relecture 1).
    refused = fixture("cost_category_reactivation_refused")
    parent = fixture("org_node_reactivation_refused")
    assert list(refused["params"]) == list(parent["params"])
    nature = fixture("cost_type_deactivated")
    assert nature["is_active"] is False
    assert refused["params"] == {
        "missing_condition": "cost_type_active",
        "conflicting_object_id": nature["cost_type_id"],
    }
    assert "conflicting_object_id" in _flat(_block("setCostCategoryActivation", "409"))
    assert "cost_type_deactivated" in _summary("cost_category_reactivation_refused")
    conditions = _enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )
    assert "cost_type_active" in conditions
    assert "`cost_type_active`" in _schema("reference.yaml", "CostCategoryCommand")


def test_an_unchanged_category_deactivated_since_is_kept_at_the_modification() -> None:
    said = "ne vaut que si la valeur change la catégorie du risque"
    assert said in _schema("risks.yaml", "RiskWrite")
    assert "que si la valeur change la catégorie du risque" in _flat(_block("updateRisk", "422"))


def test_a_deleted_subproject_leaves_the_risks_not_identified_without_designation() -> None:
    # The specification does not settle it: a provisional decision, #732.
    assert "#732" in _description("deleteSubproject")
    assert "passe à nul la désignation" in _description("deleteSubproject")
    risk = (SCHEMAS / "risks.yaml").read_text(encoding="utf-8").split("\nRisk:\n", 1)[1]
    subproject = risk.split("    provision_subproject_id:\n", 1)[1].split("    provision_", 1)[0]
    assert "#732" in _flat(subproject)
    assert "#732" in _schema("risks.yaml", "RiskReviewWrite")


def test_the_category_of_a_risk_says_whether_it_is_still_active() -> None:
    risk = (SCHEMAS / "risks.yaml").read_text(encoding="utf-8").split("\nRisk:\n", 1)[1]
    assert "    - provision_cost_category_is_active\n" in risk
    assert "provision_cost_category_is_active" in _schema("risks.yaml", "RiskReviewWrite")
    for item in fixture("risks")["items"]:
        assert item["provision_cost_category_is_active"] is True, item["label"]


def test_the_command_of_the_provision_names_identified_alone_and_the_refusals_their_order() -> None:
    assert "ne nomme que `risk_identified`" in _schema("risks.yaml", "RiskCommand")
    said = _flat(_block("createRisk", "409"))
    assert said.index("`at_least_one_task`, puis") < said.index("puis `active_provision_category`")
    assert "Ce 409 précède le 422" in said


def test_a_risk_declared_on_a_main_structure_without_task_is_refused_naming_the_condition() -> None:
    # WF-RIS-0010 : « La déclaration d'un risque sur une structure principale sans tâche est
    # refusée, en nommant la condition manquante » (#728, EP-14/L42s). The project created today,
    # passed to Chiffrage, bears the revision without task: no variant.
    said = _flat(_block("createRisk", "409"))
    cited = re.findall(r"fixtures/api/(\w+)\.json", said)
    assert cited == ["risk_without_provision_category", "risk_without_task"]
    refused = fixture("risk_without_task")
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": "at_least_one_task"}
    project = fixture("project_revision_opened")
    assert project["label"] in _summary("risk_without_task")
    assert COUNTERFACTUAL not in _summary("risk_without_task")
    [main] = [each for each in fixture("structures_without_tasks") if each["kind"] == "main"]
    assert main["revision_id"] == project["current_revision_id"]
    assert fixture("nodes_empty")["totals"]["task_count"] == 0
    general = _schema("projects.yaml", "CommandCondition")
    assert "`at_least_one_task` manque à la déclaration d'un risque" in general
    assert "`at_least_one_task`" in _schema("risks.yaml", "RiskWrite")


DECLARE = "declare_risk"
"""The command that says ahead whether a risk may be declared (EP-14/L42s, relecture 1)."""


def _declaration(commands: list[Entry]) -> Entry:
    """Return the declaration among commands, checked to follow the entry of the risks."""
    names = [each["command"] for each in commands]
    assert names.index(DECLARE) == names.index("edit_risks") + 1
    return commands[names.index(DECLARE)]


def test_the_declaration_of_a_risk_says_ahead_the_conditions_its_409_names() -> None:
    # WF-IHM-0090: a command a state makes impossible is shown unavailable with its condition —
    # the revision without task of the project created today, unavailable; the current revision of
    # the witness, available; its own conditions first, in the order of the 409, then those of the
    # entry of the risks — none listed where the entry is not (relecture 1).
    for file, schema in (
        ("revisions.yaml", "RevisionCommand"),
        ("projects.yaml", "ProjectCommand"),
    ):
        assert DECLARE in _enumeration((SCHEMAS / file).read_text(encoding="utf-8"), schema)
    without = _declaration(fixture("revision_without_tasks")["available_commands"])
    assert without == {
        "command": DECLARE,
        "is_available": False,
        "missing_conditions": ["at_least_one_task"],
    }
    current = _declaration(fixture("revision")["available_commands"])
    assert (current["is_available"], current["missing_conditions"]) == (True, [])
    for name in ("revision_marking", "revision_importing"):
        commands = fixture(name)["available_commands"]
        entry = next(each for each in commands if each["command"] == "edit_risks")
        assert _declaration(commands)["missing_conditions"] == entry["missing_conditions"]
    # On a project without a current revision, the revision the declaration would create: none of
    # the project created today, which has no revision at all, nor of the offer in pricing.
    for name, missing in (
        ("project_created", ["at_least_one_task"]),
        ("project_pricing", ["at_least_one_task"]),
        ("project_without_current_revision", []),
    ):
        assert _declaration(fixture(name)["available_commands"])["missing_conditions"] == missing
    for path in sorted(mockwitness.FIXTURES.glob("*.json")):
        listed = [each["command"] for each in _commands(json.loads(path.read_text("utf-8")))]
        assert listed.count("edit_risks") == listed.count(DECLARE), path.name
    said = _flat(_block("createRisk", "409"))
    assert "la commande `declare_risk` les liste" in said


def _commands(value: object) -> list[Entry]:
    """Return every availability of a command an example holds, however deep, in its order."""
    found: list[Entry] = []
    if isinstance(value, dict):
        entry = cast("Entry", value)
        if "command" in entry and "missing_conditions" in entry:
            found.append(entry)
        for each in entry.values():
            found += _commands(each)
    elif isinstance(value, list):
        for each in cast("list[object]", value):
            found += _commands(each)
    return found


STATE_FIRST = [
    "project_not_terminal",
    "no_background_task_running",
    "at_least_one_task",
    ACTIVE_PROVISION,
]
"""The conditions of the declaration in their order: those of the state of the entry of the risks,
then its own (relecture 2, as `update_work_breakdown`)."""


def _in_order(text: str, names: list[str]) -> bool:
    """Tell whether a text names each condition, in the order given."""
    at = [text.find(f"`{name}`") for name in names]
    return -1 not in at and at == sorted(at)


def test_the_declaration_names_the_state_of_the_entry_before_its_own_conditions() -> None:
    # WF-IHM-0090: the conditions of the state of the entry of the risks first — on a terminal
    # project or during a task in the background, a task added would not make the declaration
    # possible —, then the main structure with a task, then the active category (WF-RIS-0010;
    # relecture 2).
    revision = (SCHEMAS / "revisions.yaml").read_text(encoding="utf-8")
    said = _flat(
        revision.split("\nRevisionCommand:\n", 1)[1].split("\nRevisionCommandAvailability:")[0]
    )
    paragraph = said.split(f"`{DECLARE}` dit d'avance", 1)[1].split("`generate_skeleton`", 1)[0]
    assert _in_order(paragraph, STATE_FIRST)
    assert "les autres conditions d'`edit_risks`" in paragraph
    project = _flat((SCHEMAS / "projects.yaml").read_text(encoding="utf-8"))
    commands = project.split("ProjectCommand: type: string", 1)[1].split(
        "ProjectCommandAvailability:"
    )[0]
    assert _in_order(
        commands.split(f"`{DECLARE}` la suit", 1)[1], [*STATE_FIRST, "may_create_revision"]
    )
    general = project.split("CommandCondition: type: string", 1)[1].split(" enum: ", 1)[0]
    # `at_least_one_task`, the condition the sentence is of, between those of the state and the
    # active category.
    told = general.split("`at_least_one_task` manque à la déclaration", 1)[1].split("(EP-14/L42s)")[
        0
    ]
    told = told.split("`createRisk` la nomme dans son 409, après", 1)[1]
    assert _in_order(told, [name for name in STATE_FIRST if name != "at_least_one_task"])
    assert told.index("`no_background_task_running`, et avant `active_provision_category`") > 0
    refused = _flat(_block("createRisk", "409"))
    first = " puis ".join(f"`{name}`," for name in STATE_FIRST).rstrip(",")
    assert f"nomme la première qui manque : {first}" in refused
    assert "de la révision en cours, ou de celle que la déclaration créerait" in refused
    # The examples name the conditions in that order, `project_not_terminal` first on a terminal
    # project; those of the entry of the risks alone, where the structure is not judged.
    for path in sorted(mockwitness.FIXTURES.glob("*.json")):
        for entry in _commands(json.loads(path.read_text("utf-8"))):
            if entry["command"] == DECLARE:
                missing = cast("list[str]", entry["missing_conditions"])
                known = [name for name in missing if name in STATE_FIRST]
                assert known == [name for name in STATE_FIRST if name in missing], path.name
                assert missing[: len(known)] == known, path.name
    assert "la déclaration d'un risque indisponible faute de tâche" in _summary(
        "revision_without_tasks"
    )
    assert "la déclaration d'un risque, qui attend une tâche" in _summary("project_pricing")


def test_the_conditions_name_the_declaration_wherever_they_name_the_entry_of_the_risks() -> None:
    # A command a background task or a revision to create suspends is named with them: the
    # declaration of a risk wherever the entry of the risks is (WF-IHM-0090; relecture 2).
    general = _flat((SCHEMAS / "projects.yaml").read_text(encoding="utf-8"))
    general = general.split("CommandCondition: type: string", 1)[1].split(" enum: ", 1)[0]
    named = [part for part in re.split(r"(?<=[.;]) ", general) if "edit_risks" in part]
    assert len(named) >= 3
    for part in named:
        assert f"`{DECLARE}`" in part or f"`ProjectCommand.{DECLARE}`" in part, part
    assert f"et des risques, la déclaration d'un risque (`{DECLARE}`)" in general


def test_a_fresh_installation_misses_the_labour_category_and_the_role_alone() -> None:
    # WF-CYC-0120, Vérif : « Sur une installation neuve, dont la seule catégorie est celle des
    # provisions pour risques, la création est refusée en nommant la catégorie de main-d'œuvre et
    # le rôle manquants » — the calendar by default is bootstrapped (WF-EXP-0020; #728).
    fresh = fixture("reference_readiness_incomplete")
    assert fresh == {
        "is_complete": False,
        "missing": ["active_cost_category", "active_resource_role"],
    }
    assert "installation neuve" in _summary("reference_readiness_incomplete")
    assert "catégorie de main-d'œuvre active" in _summary("reference_readiness_incomplete")
    readiness = (SCHEMAS / "reference.yaml").read_text(encoding="utf-8")
    assert "catégorie de main-d'œuvre active" in _flat(
        readiness.split("\nReferenceReadiness:\n")[1]
    )


# --- The answers of the second review (revue 2) --------------------------------------------------


def test_a_deactivated_nature_deactivates_its_category_whose_reactivation_it_withholds() -> None:
    # A category of a deactivated nature is deactivated with it, and its reactivation misses
    # `cost_type_active` until the nature is reactivated (WF-REF-0010; EP-14/L42s, C-291).
    [nature] = [n for n in fixture("cost_types")["items"] if n["kind"] == "provision"]
    entries = [(universe(404), "Provisions pour risques")]
    [active] = cast("list[Entry]", mockdata.categories_of(entries, "PRV", "681", nature))
    inactive_nature = {**nature, "is_active": False}
    [inactive] = cast("list[Entry]", mockdata.categories_of(entries, "PRV", "681", inactive_nature))
    assert (active["is_active"], active["cost_type_is_active"]) == (True, True)
    assert (inactive["is_active"], inactive["cost_type_is_active"]) == (False, False)
    [state, _] = mockreference.category_commands(inactive, set(), set(), set())
    assert state == {
        "command": "reactivate",
        "is_available": False,
        "missing_conditions": ["cost_type_active"],
    }
    reactivated_nature = {**inactive, "cost_type_is_active": True}
    [state, _] = mockreference.category_commands(reactivated_nature, set(), set(), set())
    assert state == {"command": "reactivate", "is_available": True, "missing_conditions": []}
    [witness] = _provision_categories()
    assert (witness["is_active"], witness["cost_type_is_active"]) == (True, True)


def test_a_designation_set_to_nil_advances_the_risk_and_names_who_deleted() -> None:
    for said in (
        _description("deleteSubproject"),
        _flat(
            (SCHEMAS / "risks.yaml")
            .read_text(encoding="utf-8")
            .split("    provision_subproject_id:\n", 1)[1]
            .split("    provision_subproject_label:", 1)[0]
        ),
    ):
        assert "`lock_version` avancer" in said
        assert "l'auteur de la suppression" in said


def test_the_undo_that_would_restore_a_deleted_subproject_is_refused_by_its_condition() -> None:
    conditions = _enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )
    assert "restored_subproject_exists" in conditions
    assert "`restored_subproject_exists`" in _description("updateRisk")
    assert "#732" in _description("updateRisk")
    assert "`restored_subproject_exists`" in _description("deleteRisk")
    # Every undo and every redo that would restore it, deleteRisk and the writes of the grid
    # included (revue 3).
    general = _schema("projects.yaml", "CommandCondition")
    assert "toute annulation et à tout rétablissement" in general
    assert "sa suppression défaites ou rétablies" in general
    for operation, verb in (("undoLastChange", "défait"), ("redoLastUndo", "rétablit")):
        said = _flat(_block(operation, "409"))
        assert "`restored_subproject_exists`" in said, operation
        assert f"dont {'elle' if verb == 'défait' else 'il'} {verb} la création" in said
        assert "la modification ou la suppression" in said, operation
        assert "la suppression d'une ligne ou d'une tâche" in said, operation


def test_the_category_of_a_risk_reads_inactive_once_its_nature_is_deactivated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A generator that wrote the flag true would pass on the witness alone, whose category is
    # active: the reference read with the nature deactivated, as C-291 deactivates its
    # categories, makes the same risk read inactive (#747, points 2 and 3).
    [nature] = [n for n in fixture("cost_types")["items"] if n["kind"] == "provision"]
    entries = [(universe(404), "Provisions pour risques")]
    inactive = cast(
        "list[Entry]",
        mockdata.categories_of(entries, "PRV", "681", {**nature, "is_active": False}),
    )
    volume = fixture("volume/cost_categories")
    items = [
        inactive[0] if each["cost_category_id"] == universe(404) else each
        for each in volume["items"]
    ]
    assert mockhistory.is_active_provision(universe(404)) is True

    def read(name: str) -> Any:
        return {**volume, "items": items} if name == "volume/cost_categories" else fixture(name)

    monkeypatch.setattr(mockhistory, "fixture", read)
    assert mockhistory.is_active_provision(universe(404)) is False


def test_the_category_of_a_risk_reads_false_once_moved_to_a_nature_of_another_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A category the risk designates while dismissed is employed by no line, and may be moved to a
    # nature of another kind (WF-REF-0030): still active, it is no longer among « les catégories
    # actives de type provision pour risques » (WF-RIS-0010), and its return asks for another one
    # (#747, point 4).
    [other] = [n for n in fixture("cost_types")["items"] if n["kind"] == "non_labor"]
    assert other["is_active"] is True
    moved = cast(
        "list[Entry]",
        mockdata.categories_of([(universe(404), "Provisions pour risques")], "PRV", "681", other),
    )
    assert moved[0]["is_active"] is True
    volume = fixture("volume/cost_categories")
    items = [
        moved[0] if each["cost_category_id"] == universe(404) else each for each in volume["items"]
    ]

    def read(name: str) -> Any:
        return {**volume, "items": items} if name == "volume/cost_categories" else fixture(name)

    monkeypatch.setattr(mockhistory, "fixture", read)
    assert mockhistory.is_active_provision(universe(404)) is False
    # The kind is judged, not the flag alone: an active category of labour reads false as well.
    assert mockhistory.is_active_provision(universe(402)) is False
    # The contract says it of the flag, of the return and of its refusal.
    flag = _flat(
        (SCHEMAS / "risks.yaml")
        .read_text(encoding="utf-8")
        .split("    provision_cost_category_is_active:\n", 1)[1]
        .split("\n    provision_subproject_id:", 1)[0]
    )
    assert "active et que sa nature est de type provision pour risques" in flag
    assert "rattachée depuis à une nature d'un autre type" in flag
    assert "encore active et de type provision pour risques" in _schema(
        "risks.yaml", "RiskReviewWrite"
    )
    assert "n'est plus de type provision pour risques" in _flat(_block("reviewRisk", "422"))


def test_the_undo_or_redo_that_would_recreate_a_provision_names_the_conditions_of_its_return() -> (
    None
):
    # Recreating a line of provision on a main structure emptied since, or with a category no
    # longer active and of provision, is refused as the return of a dismissed risk is (WF-RIS-0010,
    # WF-IHM-0110), by the existing conditions in the order of the enumeration (#795, point 2).
    conditions = _enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )
    order = ["at_least_one_task", "restored_subproject_exists", ACTIVE_PROVISION]
    assert sorted(order, key=conditions.index) == order
    said = ", ".join(f"`{each}`" for each in order)
    for operation, example, condition in (
        ("undoLastChange", "undo_risk_without_task", "at_least_one_task"),
        ("redoLastUndo", "redo_risk_category_deactivated", ACTIVE_PROVISION),
    ):
        block = _flat(_block(operation, "409"))
        assert "recréerait la ligne de provision d'un risque" in block, operation
        assert said in block, operation
        assert f"fixtures/api/{example}.json" in block, operation
        answer = json.loads((mockwitness.FIXTURES / f"{example}.json").read_text(encoding="utf-8"))
        assert answer["value"]["status"] == 409
        assert answer["value"]["code"] == "STATE_FORBIDS_OPERATION"
        assert answer["value"]["params"] == {"missing_condition": condition}
    general = _schema("projects.yaml", "CommandCondition")
    assert "`at_least_one_task` manque aussi au retour d'un risque écarté" in general
    assert "et de même à toute annulation et à tout rétablissement" in general
    # The return itself, which the undo of a dismissal repeats (decision of the author, #787).
    review = _flat(_block("reviewRisk", "409"))
    assert "`params.missing_condition` à `at_least_one_task`" in review
    assert "fixtures/api/risk_review_without_task.json" in review
    answer = json.loads(
        (mockwitness.FIXTURES / "risk_review_without_task.json").read_text(encoding="utf-8")
    )
    assert answer["value"]["params"] == {"missing_condition": "at_least_one_task"}
    assert "n'envoyant rien, ils ne peuvent pas en désigner une autre" in general


def test_the_change_of_a_provision_refused_by_its_state_precedes_the_refusal_of_its_value() -> None:
    # Which refusal wins when a dismissed risk is sent another category that is itself refused:
    # the 409, as at the declaration (#747, point 5).
    said = _flat(_block("updateRisk", "409"))
    assert "Ce 409 précède le 422, comme à la déclaration (`createRisk`)" in said
    assert "qu'elle soit désactivée, inconnue ou d'une nature d'un autre type" in said
    assert "Ce 409 précède le 422" in _flat(_block("createRisk", "409"))


def test_the_condition_of_the_restored_subproject_is_said_where_its_enumeration_ranks_it() -> None:
    # The description follows the order of the enumeration: after the creation of a revision,
    # before the conditions of a risk (#752, point 1).
    conditions = _enumeration(
        (SCHEMAS / "projects.yaml").read_text(encoding="utf-8"), "CommandCondition"
    )
    ranked = conditions.index("restored_subproject_exists")
    assert conditions[ranked - 1 : ranked + 2] == [
        "may_create_revision",
        "restored_subproject_exists",
        "risk_not_cited",
    ]
    general = _schema("projects.yaml", "CommandCondition")
    said = general.index("`restored_subproject_exists` manque")
    assert general.rindex("`may_create_revision` manque", 0, said) < said
    assert said < general.index("Trois conditions tiennent à l'état d'un risque")
