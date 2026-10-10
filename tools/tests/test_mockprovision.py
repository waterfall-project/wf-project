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

from wftools import REPOSITORY, mockdata, mockwitness
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


def test_until_c291_an_active_category_of_provision_is_one_under_an_active_nature() -> None:
    # #728: without the cascade of C-291, the condition says the nature active.
    said = "sous une nature active de ce type"
    reference = (SCHEMAS / "reference.yaml").read_text(encoding="utf-8")
    assert said in _flat(reference.split("\nReferenceReadiness:\n", 1)[1])
    assert "une catégorie active sous une nature désactivée ne compte pas" in _schema(
        "reference.yaml", "CostTypeCommand"
    )
    assert "rattachée à une nature active de ce type" in _schema(
        "projects.yaml", "CommandCondition"
    )
    assert "ne compte pas pour `active_provision_category`" in _description("setCostTypeActivation")
    assert "sous une nature désactivée" in _schema("risks.yaml", "RiskWrite")


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
    assert said.index("`at_least_one_task`") < said.index("puis `active_provision_category`")
    assert "Ce 409 précède le 422" in said


# --- The answers of the second review (revue 2) --------------------------------------------------


def test_a_deactivated_nature_of_provision_marks_its_category_with_its_nature_inactive() -> None:
    # A form keeps the active categories of an active nature of provision for risks (#728).
    [nature] = [n for n in fixture("cost_types")["items"] if n["kind"] == "provision"]
    entries = [(universe(404), "Provisions pour risques")]
    [active] = cast("list[Entry]", mockdata.categories_of(entries, "PRV", "681", nature))
    inactive_nature = {**nature, "is_active": False}
    [inactive] = cast("list[Entry]", mockdata.categories_of(entries, "PRV", "681", inactive_nature))
    assert active["cost_type_is_active"] is True
    assert inactive["cost_type_is_active"] is False
    assert inactive["is_active"] is True
    [witness] = _provision_categories()
    assert witness["cost_type_is_active"] is True
    assert "`cost_type_is_active`" in _schema("projects.yaml", "CommandCondition")


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
