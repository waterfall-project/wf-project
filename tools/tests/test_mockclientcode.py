# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the client of a project and of the bounded code of a subproject (EP-16/US-0610).

They try the contract and its examples: the client every reading of a project bears, the code of
a declared subproject that names its tab in the file of the remaining to commit — at most 31
characters, none of the characters a tab refuses (FORBIDDEN), neither « Synthèse » nor « Hors
sous-projet », whatever the case —, the refusal of a code that would not, and every code of the
witness under that bound. Not the Vérif of a requirement: WF-PRJ-0080-A and WF-PRJ-0050-A are
closed by the service, EP-04, and the exported estimate, EP-07; none is cited (WF-QUA-0010, « un
test qui ne couvre aucune exigence »).
"""

import json
import re
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockwitness

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
SCHEMAS = API / "components" / "schemas"

LONGEST_CODE = 31
"""The most characters the code of a declared subproject holds, the most a tab of Excel holds."""
FORBIDDEN = ":\\/?*[]"
"""The characters a tab of Excel refuses, which the code of a subproject may not bear."""
RESERVED = ("Synthèse", "Hors sous-projet")
"""The two tabs Waterfall names in the file of the remaining to commit (ANNEXE B)."""
LONGEST_READ = 50
"""The bound the code read in the WBS element of an actual cost line keeps (WF-CRE-0020)."""
LONGEST_CLIENT = 300
"""The most characters the name of the client holds, as the label of a project."""
CLIENT = "Papeteries de la Vienne"
"""The client of the witness, PRJ-001."""


def _schemas(name: str) -> Entry:
    return cast("Entry", yaml.safe_load((SCHEMAS / name).read_text(encoding="utf-8")))


def _walk(value: Any) -> list[Entry]:
    """Return every object a value read from JSON holds, itself included."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _walk(item)]
    if not isinstance(value, dict):
        return []
    entry = cast("Entry", value)
    return [entry, *(found for item in entry.values() for found in _walk(item))]


def _examples() -> dict[str, Any]:
    return {
        path.relative_to(mockwitness.FIXTURES).with_suffix("").as_posix(): json.loads(
            path.read_text(encoding="utf-8")
        )["value"]
        for path in sorted(mockwitness.FIXTURES.rglob("*.json"))
    }


def _operation(name: str) -> str:
    text = (API / "paths" / "projects.yaml").read_text(encoding="utf-8")
    return text.split(f"operationId: {name}\n", 1)[1].split("operationId:", 1)[0]


def _answer(name: str, status: str) -> str:
    return _operation(name).split(f"'{status}':", 1)[1].split("\n      '", 1)[0]


# --- The code of a declared subproject -----------------------------------------------------------


def _code() -> Entry:
    return cast("Entry", _schemas("projects.yaml")["DeclaredSubprojectCode"])


def _accepted(code: str) -> bool:
    """Return whether the contract accepts a code, by its bounds and its pattern."""
    schema = _code()
    within = schema["minLength"] <= len(code) <= schema["maxLength"]
    return within and re.search(schema["pattern"], code) is not None


def test_the_reading_and_the_writes_of_a_subproject_share_the_bounded_code() -> None:
    schemas = _schemas("projects.yaml")
    assert schemas["Subproject"]["properties"]["code"] == {"$ref": "#/DeclaredSubprojectCode"}
    assert schemas["SubprojectWrite"]["properties"]["code"] == {"$ref": "#/DeclaredSubprojectCode"}
    # The update is the write and its counter.
    assert schemas["SubprojectUpdate"]["allOf"][0] == {"$ref": "#/SubprojectWrite"}
    assert (_code()["minLength"], _code()["maxLength"]) == (1, LONGEST_CODE)


@pytest.mark.parametrize(
    "code",
    [
        "SP/01",
        "Synthèse",
        "SYNTHÈSE",
        "synthèse",
        "Hors sous-projet",
        "HORS SOUS-PROJET",
        "x" * (LONGEST_CODE + 1),
        "",
        "   ",
        *(f"SP{character}01" for character in FORBIDDEN),
    ],
)
def test_a_code_that_cannot_name_a_tab_is_refused_by_the_contract(code: str) -> None:
    assert not _accepted(code)


@pytest.mark.parametrize(
    "code", ["SP-CMD", "SP-ESS", "x" * LONGEST_CODE, "Synthese", "Synthèse 2", "Hors lot", "SP 01"]
)
def test_a_code_that_names_a_tab_is_accepted_by_the_contract(code: str) -> None:
    assert _accepted(code)


def test_every_subproject_code_of_the_witness_respects_the_bound() -> None:
    # Every subproject the examples read or write, wherever it lies.
    keys = {"subproject_id", "code", "label", "has_actual_costs"}
    codes = {
        entry["code"]
        for example in _examples().values()
        for entry in _walk(example)
        if keys <= entry.keys()
    }
    assert {"SP-CMD", "SP-ESS"} <= codes
    assert all(_accepted(code) for code in codes), codes


def test_the_code_read_in_an_actual_cost_line_keeps_its_own_bound() -> None:
    line = _schemas("costs.yaml")["ActualCostLine"]["properties"]["subproject_code"]
    [text, _null] = line["anyOf"]
    assert text == {"type": "string", "maxLength": LONGEST_READ}
    assert "garde sa borne de 50 caractères" in " ".join(line["description"].split())


def test_a_code_refused_names_its_motive_and_its_parameter() -> None:
    said = " ".join(_code()["description"].split())
    assert "`VALUE_TOO_LONG`, `fields[].params.max_length` à `31`" in said
    assert "`SUBPROJECT_CODE_INVALID`, `fields[].params.forbidden_characters`" in said
    assert "`SUBPROJECT_CODE_INVALID`, `fields[].params.reserved_name`" in said
    common = yaml.safe_load((API / "components" / "common.yaml").read_text(encoding="utf-8"))
    assert "SUBPROJECT_CODE_INVALID" in common["ErrorCode"]["enum"]
    for operation in ("createSubproject", "updateSubproject"):
        answer = " ".join(_answer(operation, "422").split())
        assert "`SUBPROJECT_CODE_INVALID`" in answer, operation
        assert "`fields[].params.max_length` à `31`" in answer, operation
        assert "subproject_code_invalid.json" in answer, operation


def test_the_refusal_of_a_forbidden_character_names_the_characters_the_code_bears() -> None:
    example = json.loads(
        (mockwitness.FIXTURES / "subproject_code_invalid.json").read_text(encoding="utf-8")
    )
    refused = example["value"]
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    [field] = refused["fields"]
    assert (field["pointer"], field["code"]) == ("/code", "SUBPROJECT_CODE_INVALID")
    sent = "SP/01"
    assert sent in example["summary"]
    assert not _accepted(sent)
    assert field["params"] == {
        "forbidden_characters": [each for each in dict.fromkeys(sent) if each in FORBIDDEN]
    }


def test_the_refusal_of_a_reserved_name_names_it_as_waterfall_writes_it() -> None:
    # Its twin for the reserved names (#1507): the code of the summary, written in another case, is
    # refused all the same, and the name is given as Waterfall writes its tab.
    example = json.loads(
        (mockwitness.FIXTURES / "subproject_code_reserved.json").read_text(encoding="utf-8")
    )
    refused = example["value"]
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    [field] = refused["fields"]
    assert (field["pointer"], field["code"]) == ("/code", "SUBPROJECT_CODE_INVALID")
    sent = "synthèse"
    assert f"« {sent} »" in example["summary"]
    assert not _accepted(sent)
    assert field["params"] == {"reserved_name": "Synthèse"}
    named = field["params"]["reserved_name"]
    assert named.casefold() == sent.casefold()
    assert named != sent
    for operation in ("createSubproject", "updateSubproject"):
        answer = " ".join(_answer(operation, "422").split())
        assert "code_reserved: { $ref: ../../../fixtures/api/subproject_code_reserved.json }" in (
            answer
        ), operation


# --- The client of a project ---------------------------------------------------------------------


def test_the_client_is_nullable_and_bounded_as_the_label_in_the_reading_and_the_writes() -> None:
    schemas = _schemas("projects.yaml")
    client = schemas["ProjectClient"]
    bounds = (client["minLength"], client["pattern"], client["maxLength"])
    assert bounds == (1, "\\S", LONGEST_CLIENT)
    label = schemas["Project"]["properties"]["label"]
    assert label["maxLength"] == LONGEST_CLIENT
    nullable = [{"$ref": "#/ProjectClient"}, {"type": "null"}]
    for schema in ("Project", "ProjectCreate", "ProjectUpdate"):
        assert schemas[schema]["properties"]["client"]["anyOf"] == nullable, schema
        # Optional to write: no transition requires it (WF-PRJ-0080); always rendered by the
        # reading, null when not entered, and so required there (D-11, #1780).
        assert ("client" in schemas[schema].get("required", [])) == (schema == "Project"), schema
    for operation in ("createProject", "updateProject"):
        assert "`/client`" in _answer(operation, "422"), operation


def test_every_reading_of_a_project_bears_its_client() -> None:
    # Every project read whole, wherever it lies: the witness by its client, the others without.
    keys = {"project_id", "state", "win_probability", "available_commands"}
    clients = {
        (entry["code"], entry["client"])
        for example in _examples().values()
        for entry in _walk(example)
        if keys <= entry.keys()
    }
    assert clients == {("PRJ-001", CLIENT), ("PRJ-002", None), (None, None)}
