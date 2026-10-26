# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the mapping of the extraction of actual costs, in the contract and the witness.

They try the contract and its examples, not the service, which EP-05 and EP-09 write: the mapping of
the witness and the columns its lines keep agree; every mapping read holds its five columns in their
order, and says what it misses; no example declares a label twice once compared without regard to
case, accents or spaces at the ends, and the refusal of a double names both; a new installation
refuses the import by naming the mapping to set, a file without a required column names it, and the
report names a column neither read nor kept (WF-REF-0190). And the WBS elements of the examples: the
code of the project, then a slash and the code of the subproject (WF-CRE-0020, C-373 ;
EP-16/US-0620).
"""

import json
import re
import unicodedata
from datetime import datetime
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcosts, mockwitness, mockwitnesscosts
from wftools.mockwitness import TODAY, fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"

ORDER = ["wbs_element", "document_number", "document_item", "document_date", "amount"]
"""The columns read, in the fixed order of the mapping (`ActualCostSourceColumn`)."""
OPTIONAL = "document_item"
"""The one column read that is not required: the item of a document (WF-REF-0190)."""
MAPPINGS = ("actual_cost_mapping", "actual_cost_mapping_empty", "actual_cost_mapping_updated")
"""The examples of the mapping read: the witness's, a new installation's, and the write of today."""
VERIF = {
    "wbs_element": ["Elément d'OTP"],
    "document_number": ["Nº pièce référence"],
    "document_date": ["Date de la pièce"],
    "amount": ["Val./Devise objet"],
}
"""The labels the Vérif of WF-REF-0190-A declares, those of the extraction of the author."""


def normalized(label: str) -> str:
    """Return a label as the mapping compares it: no case, no accent, no space at the ends."""
    decomposed = unicodedata.normalize("NFKD", label.strip().casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _schemas(name: str) -> Entry:
    path = API / "components" / "schemas" / name
    return cast("Entry", yaml.safe_load(path.read_text(encoding="utf-8")))


def _labels(mapping: Entry) -> dict[str, list[str]]:
    return {column["column"]: column["labels"] for column in mapping["columns"]}


def _pointed(body: Entry, pointer: str) -> str:
    """Return the label a pointer of a refusal designates in a body (RFC 6901)."""
    value: Any = body
    for step in pointer.removeprefix("/").split("/"):
        value = cast("Any", value[int(step)] if isinstance(value, list) else value[step])
    return cast("str", value)


def _doubles(body: Entry) -> list[tuple[str, str]]:
    """Return each label of a body that doubles another, with the one it doubles, by pointers."""
    pointers = [
        f"/columns/{rank}/labels/{index}"
        for rank, column in enumerate(body["columns"])
        for index in range(len(column["labels"]))
    ] + [f"/kept_columns/{index}" for index in range(len(body["kept_columns"]))]
    first: dict[str, str] = {}
    found: list[tuple[str, str]] = []
    for pointer in pointers:
        key = normalized(_pointed(body, pointer))
        if key in first:
            found.append((pointer, first[key]))
        else:
            first[key] = pointer
    return found


# --- The mapping of the witness and the columns its lines keep ---------------------------------


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_mapping_of_the_witness_keeps_the_columns_its_lines_keep() -> None:
    # « Déclarée conservée, elle est restituée à la consultation des lignes importées ensuite » :
    # the columns the witness's lines keep are those its mapping declares kept, in its order.
    mapping = fixture("actual_cost_mapping")
    assert mapping["kept_columns"] == list(mockwitnesscosts.PASSTHROUGH)
    for name in ("actual_costs", "actual_costs_page", "actual_costs_subproject"):
        assert fixture(name)["meta"]["passthrough_columns"] == mapping["kept_columns"], name
    for line in fixture("actual_costs")["items"]:
        assert list(line["passthrough"]) == mapping["kept_columns"], line["document_number"]
    # The element of the WBS is a column read: kept as well, its label would double its own.
    kept = {normalized(label) for label in mapping["kept_columns"]}
    assert normalized("Élément d'OTP") not in kept


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_witness_declares_the_labels_of_the_verif_before_its_first_import() -> None:
    mapping = fixture("actual_cost_mapping")
    assert {column: labels for column, labels in _labels(mapping).items() if labels} == VERIF
    assert mapping["is_complete"] is True
    first = min(entry.event.instant for entry in mockwitnesscosts.JOURNAL)
    declared = datetime.fromisoformat(mapping["audit"]["updated_at"])
    assert datetime.fromisoformat(mapping["audit"]["created_at"]) == mockwitness.INSTALLED.instant
    assert mockwitness.INSTALLED.instant < declared < first
    # « Une extraction dont l'en-tête est « Élément d'OTP » s'importe » : the header of the file
    # is the label declared, compared without regard to its accent.
    assert normalized("Élément d'OTP") == normalized(VERIF["wbs_element"][0])


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_write_of_today_changes_only_what_it_declares_at_the_next_version() -> None:
    before, after = fixture("actual_cost_mapping"), fixture("actual_cost_mapping_updated")
    assert after["lock_version"] == before["lock_version"] + 1
    assert after["kept_columns"] == [*before["kept_columns"], "Document d'achat"]
    assert after["columns"] == before["columns"]
    assert datetime.fromisoformat(after["audit"]["updated_at"]) == TODAY
    assert after["audit"]["created_at"] == before["audit"]["created_at"]
    stale = fixture("actual_cost_mapping_stale")
    assert stale["params"] == {"expected_lock_version": after["lock_version"]}


# --- Every mapping read ------------------------------------------------------------------------


@pytest.mark.requirement("WF-REF-0190-A")
@pytest.mark.parametrize("name", MAPPINGS)
def test_a_mapping_holds_its_five_columns_in_order_and_says_the_required_ones_it_misses(
    name: str,
) -> None:
    mapping = fixture(name)
    assert [column["column"] for column in mapping["columns"]] == ORDER
    assert _schemas("reference.yaml")["ActualCostSourceColumn"]["enum"] == ORDER
    for column in mapping["columns"]:
        assert column["required"] is (column["column"] != OPTIONAL), name
    missing = [
        column["column"]
        for column in mapping["columns"]
        if column["required"] and not column["labels"]
    ]
    assert mapping["missing_columns"] == missing
    assert mapping["is_complete"] is (not missing)
    assert _doubles(mapping) == [], name


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_new_installation_has_an_empty_mapping_missing_the_four_required_columns() -> None:
    empty = fixture("actual_cost_mapping_empty")
    assert all(not column["labels"] for column in empty["columns"])
    assert empty["kept_columns"] == []
    assert empty["missing_columns"] == [column for column in ORDER if column != OPTIONAL]
    assert empty["is_complete"] is False
    audit = empty["audit"]
    assert audit["created_at"] == audit["updated_at"]
    assert datetime.fromisoformat(audit["created_at"]) == mockwitness.INSTALLED.instant
    assert audit["created_by"] == audit["updated_by"] == {"kind": "platform"}


# --- The rule of doubles -------------------------------------------------------------------------


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_refusal_of_a_double_names_the_label_doubled_and_the_one_it_doubles() -> None:
    # The write the refusal answers: the witness's mapping, the element of the WBS kept as well.
    witness = fixture("actual_cost_mapping")
    sent = {
        "columns": [
            {"column": column["column"], "labels": column["labels"]}
            for column in witness["columns"]
        ],
        "kept_columns": [*witness["kept_columns"], "Élément d'OTP"],
        "lock_version": witness["lock_version"],
    }
    refused = fixture("actual_cost_mapping_duplicate")
    assert (refused["code"], refused["status"]) == ("VALIDATION_FAILED", 422)
    assert [
        (field["pointer"], field["params"]["duplicate_of"])
        for field in refused["fields"]
        if field["code"] == "DUPLICATE_COLUMN_LABEL"
    ] == _doubles(sent)
    assert "DUPLICATE_COLUMN_LABEL" in _schemas("../common.yaml")["ErrorCode"]["enum"]


@pytest.mark.requirement("WF-REF-0190-A")
def test_labels_compare_without_regard_to_case_accents_or_spaces_at_the_ends() -> None:
    assert normalized("  NOM MATRICULE ") == normalized("Nom Matricule")
    assert normalized("Élément d'OTP") == normalized("elément d'otp")
    assert normalized("Nom Matricule") != normalized("Nom  Matricule")


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_bounds_of_a_label_and_of_its_lists_are_those_of_the_conception() -> None:
    schemas = _schemas("reference.yaml")
    label = schemas["ActualCostColumnLabel"]
    assert (label["minLength"], label["maxLength"]) == (1, 200)
    for name in ("ActualCostMappingColumn", "ActualCostMappingColumnWrite"):
        assert schemas[name]["properties"]["labels"]["maxItems"] == 20, name
    for name in ("ActualCostMapping", "ActualCostMappingWrite"):
        assert schemas[name]["properties"]["kept_columns"]["maxItems"] == 50, name
    write = schemas["ActualCostMappingWrite"]["properties"]
    assert "required" not in schemas["ActualCostMappingColumnWrite"]["properties"]
    assert not {"is_complete", "missing_columns", "audit"} & set(write)


# --- The import of actual costs ------------------------------------------------------------------


@pytest.mark.requirement("WF-REF-0190-A")
def test_on_a_new_installation_the_import_is_refused_naming_the_mapping_to_set() -> None:
    # « Sur une installation neuve, l'import d'un fichier de coûts réels est refusé et nomme la
    # correspondance à régler. »
    refused = fixture("import_actual_cost_mapping_incomplete")
    assert (refused["code"], refused["status"]) == ("STATE_FORBIDS_OPERATION", 409)
    assert refused["params"] == {
        "missing_condition": "actual_cost_mapping_complete",
        "columns": fixture("actual_cost_mapping_empty")["missing_columns"],
    }
    conditions = _schemas("projects.yaml")["CommandCondition"]["enum"]
    assert "actual_cost_mapping_complete" in conditions
    # The command of the project says it beforehand; the other commands are the witness's.
    witness, waiting = fixture("project"), fixture("project_actual_cost_mapping_incomplete")
    commands = {entry["command"]: entry for entry in waiting["available_commands"]}
    assert commands["import_actual_costs"] == {
        "command": "import_actual_costs",
        "is_available": False,
        "missing_conditions": ["actual_cost_mapping_complete"],
    }

    def others(project: Entry) -> list[Entry]:
        return [
            entry
            for entry in project["available_commands"]
            if entry["command"] != "import_actual_costs"
        ]

    assert others(waiting) == others(witness)
    assert {key: value for key, value in waiting.items() if key != "available_commands"} == {
        key: value for key, value in witness.items() if key != "available_commands"
    }


@pytest.mark.requirement("WF-REF-0190-A")
def test_a_file_missing_a_required_column_is_refused_naming_the_column_expected() -> None:
    # « Une extraction à laquelle manque une colonne exigée est refusée, et le message nomme la
    # colonne attendue » : by its identifier and the labels the mapping declares for it.
    refused = fixture("import_actual_costs_column_missing")
    assert (refused["code"], refused["status"]) == ("FILE_FORMAT_UNREADABLE", 422)
    assert refused["params"]["expected_format"] == "actual_costs"
    # An extraction of the ERP has no version (D-2).
    assert "expected_version" not in refused["params"]
    labels = _labels(fixture("actual_cost_mapping"))
    missing = refused["params"]["missing_columns"]
    assert missing
    for entry in missing:
        assert entry["column"] != OPTIONAL
        assert entry["labels"] == labels[entry["column"]]


@pytest.mark.requirement("WF-REF-0190-A")
def test_the_report_names_a_column_neither_read_nor_kept() -> None:
    # « Une colonne « Nom Matricule » non déclarée n'est pas conservée, et le compte rendu la
    # nomme. »
    assert "columns" in _schemas("exchanges.yaml")["ImportIgnoredKind"]["enum"]
    analysed = fixture("import_actual_costs_analysed")
    ignored = fixture("import_actual_costs_column_ignored")
    [entry] = ignored["report"]["ignored"]
    assert entry == {"kind": "columns", "count": 1, "labels": ["Nom Matricule"]}
    mapping = fixture("actual_cost_mapping")
    read = [label for column in mapping["columns"] for label in column["labels"]]
    declared = {normalized(label) for label in [*mapping["kept_columns"], *read]}
    assert normalized("Nom Matricule") not in declared
    analysed["report"]["ignored"] = ignored["report"]["ignored"]
    assert ignored == analysed


# --- The WBS elements of the examples -----------------------------------------------------------


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_wbs_element_of_a_line_is_the_code_of_the_project_then_that_of_its_subproject() -> None:
    # « Sur le projet de code A.ABC.26001, une ligne d'élément A.ABC.26001/10001 est imputée au
    # sous-projet 10001 » : the witness's elements carry its code, then a slash and the code of
    # the subproject, with no prefix before the code (C-373).
    code = fixture("project")["code"]
    known = {entry["code"]: entry["subproject_id"] for entry in fixture("subprojects")}
    for line in mockcosts.lines():
        element = mockcosts.wbs_element(line)
        project, _, subproject = element.partition("/")
        assert project == code, element
        assert (subproject or None) == line.code, element
        assert mockcosts.imputed(line) == known.get(subproject), element


@pytest.mark.requirement("WF-CRE-0020-A")
def test_no_example_names_a_wbs_element_with_the_former_prefix() -> None:
    former = re.compile(r"\bWF\.[A-Z]")
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        assert not former.search(path.read_text(encoding="utf-8")), path.name


@pytest.mark.requirement("WF-CRE-0020-A")
def test_the_analysed_import_names_the_element_of_the_subproject_of_the_control_station() -> None:
    # The summary says the credit note's element now carries the code of the project, a slash and
    # the code of the subproject of the control station, as the generator forms it.
    line = next(line for line in mockcosts.lines() if line.code == "SP-CMD")
    summary = json.loads(
        (mockwitness.FIXTURES / "import_actual_costs_analysed.json").read_text(encoding="utf-8")
    )["summary"]
    assert mockcosts.wbs_element(line) in summary
