# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the item of a line of cost, in the contract and the witness (EP-16/US-0630).

They try the contract and its examples, not the service, which EP-09 writes with the constraint of
uniqueness: a line of cost is identified by its project, its document and its item (D-4). Each line
of the consultation carries its item, none for a line whose extraction gives none; the invoice of
the witness spread over two elements of the work breakdown structure gives two lines, two items of
the same document; the report designates a line by its document and its item, neither ever a field
of a difference; and two lines of the file of the same document and item are each rejected, naming
the ranks of the others (WF-CRE-0010, WF-INTF-0140).
"""

from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcosts
from wftools.mockwitness import fixture
from wftools.mockwitnesscosts import COSTS

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"

CONSULTATIONS = (
    "actual_costs",
    "actual_costs_page",
    "actual_costs_subproject",
    "actual_costs_after_exclusion",
    "actual_costs_empty",
)
"""The examples of the consultation of the actual costs (`listActualCosts`)."""
WRITES = ("actual_cost_excluded", "actual_cost_reinstated")
"""The examples of a line written (`setActualCostTrackedScope`)."""
COST_REPORTS = (
    "import_actual_costs_analysed",
    "import_actual_costs_column_ignored",
    "import_actual_costs_duplicate_line",
)
"""The reports of an import of actual costs (`getImport`)."""
DUPLICATE = "DUPLICATE_COST_LINE"


def _yaml(*parts: str) -> Entry:
    return cast("Entry", yaml.safe_load(Path(API, *parts).read_text(encoding="utf-8")))


def _witness_items() -> dict[str, list[str | None]]:
    """Return the items of the lines of the witness, by their document."""
    found: dict[str, list[str | None]] = {}
    for item in fixture("actual_costs")["items"]:
        found.setdefault(item["document_number"], []).append(item["document_item"])
    return found


# --- The line carries its item -----------------------------------------------------------------


@pytest.mark.requirement("WF-CRE-0010-A")
def test_a_line_of_cost_carries_its_item_none_when_the_extraction_gives_none() -> None:
    # « Une ligne de coût porte : un numéro de pièce, le numéro de son poste dans la pièce,
    # facultatif… » : required in the reading, and nullable.
    line = _yaml("components", "schemas", "costs.yaml")["ActualCostLine"]
    assert "document_item" in line["required"]
    assert {"type": "null"} in line["properties"]["document_item"]["anyOf"]
    lines = [
        *(item for name in CONSULTATIONS for item in fixture(name)["items"]),
        *(fixture(name) for name in WRITES),
    ]
    assert lines
    described = {(each.document, each.item) for each in mockcosts.lines()}
    for each in lines:
        assert (each["document_number"], each["document_item"]) in described, each
    # The credit note bears no item: its extraction gives none.
    [credit] = [each for each in fixture("actual_costs")["items"] if Decimal(each["amount"]) < 0]
    assert credit["document_item"] is None


@pytest.mark.requirement("WF-INTF-0140-A")
def test_an_invoice_spread_over_two_wbs_elements_gives_two_lines_two_items_of_one_document() -> (
    None
):
    # « Une facture ventilée sur deux éléments d'OTP, en deux postes de la même pièce, donne deux
    # lignes de coût. »
    spread = mockcosts.spread()
    assert len(spread) == 2
    assert len({line.document for line in spread}) == 1
    assert len({line.item for line in spread}) == 2
    assert len({mockcosts.wbs_element(line) for line in spread}) == 2
    assert None not in {line.item for line in spread}
    assert _witness_items()[spread[0].document] == [line.item for line in spread]
    # No other document of the consultation holds two lines; none twice the same item.
    items = _witness_items()
    assert [document for document, held in items.items() if len(held) > 1] == [spread[0].document]
    assert all(len(held) == len(set(held)) for held in items.values())


@pytest.mark.requirement("WF-INTF-0140-A")
def test_the_mapping_of_the_witness_reads_the_item_its_lines_carry() -> None:
    # An extraction gives an item only if the mapping declares its column: the witness's lines
    # carry one, its mapping reads it.
    assert any(line.item is not None for line in COSTS)
    columns = {column["column"]: column for column in fixture("actual_cost_mapping")["columns"]}
    assert columns["document_item"]["labels"]
    assert columns["document_item"]["required"] is False


@pytest.mark.requirement("WF-INTF-0140-A")
def test_the_item_sorts_the_consultation_but_is_never_a_field_of_a_difference() -> None:
    column = _yaml("components", "schemas", "exchanges.yaml")["ActualCostColumn"]
    [named] = [each for each in column["anyOf"] if "enum" in each]
    assert "document_item" in named["enum"]
    operation = _yaml("paths", "costs.yaml")["/projects/{project_id}/actual-costs"]["get"]
    [sort] = [each for each in operation["parameters"] if each.get("name") == "sort_by"]
    [sorted_by] = [each for each in sort["schema"]["anyOf"] if "enum" in each]
    assert "document_item" in sorted_by["enum"]
    for name in COST_REPORTS:
        for difference in fixture(name)["report"]["differences"]:
            assert not {"document_number", "document_item"} & set(difference["fields"]), name


# --- The report designates a line by its document and its item ---------------------------------


@pytest.mark.requirement("WF-INTF-0140-A")
def test_the_report_designates_a_line_of_cost_by_its_document_and_its_item() -> None:
    difference = _yaml("components", "schemas", "exchanges.yaml")["ImportDifference"]
    assert {"type": "null"} in difference["properties"]["document_item"]["anyOf"]
    items = _witness_items()
    for name in COST_REPORTS:
        found = [
            each
            for each in fixture(name)["report"]["differences"]
            if each["target"] == "actual_cost_line"
        ]
        assert found, name
        for each in found:
            # The line the difference updates is the witness's of that document and item.
            assert each["document_item"] in items[each["label"]], (name, each["label"])


@pytest.mark.requirement("WF-INTF-0140-A")
def test_two_lines_of_one_document_without_item_are_each_rejected_naming_the_other() -> None:
    # « Deux lignes de la même pièce sans poste sont rejetées au compte rendu » : each, the other's
    # rank named, none preferred.
    assert DUPLICATE in _yaml("components", "common.yaml")["ErrorCode"]["enum"]
    analysed = fixture("import_actual_costs_analysed")
    duplicate = fixture("import_actual_costs_duplicate_line")
    rejected = duplicate["report"]["rejected"]
    rows = [each["row"] for each in rejected]
    assert len(rows) == 2
    assert len(set(rows)) == len(rows)
    for each in rejected:
        assert each["code"] == DUPLICATE
        assert each["sheet"] is None
        assert each["params"] == {"rows": [row for row in rows if row != each["row"]]}
    assert duplicate["report"]["read_count"] == analysed["report"]["read_count"] + len(rows)
    # The rest of the report is the analysed one's, of which it is a counterfactual variant.
    analysed["report"]["rejected"] = rejected
    analysed["report"]["read_count"] = duplicate["report"]["read_count"]
    assert duplicate == analysed


@pytest.mark.requirement("WF-INTF-0140-A")
def test_the_contract_cites_the_report_of_the_rejected_duplicates() -> None:
    operation = _yaml("paths", "exchanges.yaml")["/projects/{project_id}/imports/{import_id}"]
    examples = operation["get"]["responses"]["200"]["content"]["application/json"]["examples"]
    cited = {Path(each["$ref"]).stem for each in examples.values()}
    assert set(COST_REPORTS) <= cited
