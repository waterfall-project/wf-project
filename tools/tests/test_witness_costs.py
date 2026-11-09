# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the actual costs of the witness written for the loader of the costs (US-1650/L1)."""

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from wftools import REPOSITORY, mockcosts, mockdata, mockwitness, paths
from wftools import mockwitnesscostfile as module
from wftools.mockids import hex_identifier
from wftools.mockwitnesscosts import JOURNAL

pytestmark = pytest.mark.requirement("WF-QUA-0040-A")

FIXTURES = REPOSITORY / "fixtures" / "api"
FILE = FIXTURES / module.NAME

IMPORT_KEYS = {
    "cost_import_id",
    "imported_at",
    "import_id",
    "filename",
    "period_from",
    "period_to",
    "kept_columns",
    "report",
    "created_count",
    "updated_count",
    "unchanged_count",
    "rejected_count",
}
LINE_KEYS = {
    "cost_line_id",
    "document_number",
    "document_item",
    "document_date",
    "amount",
    "subproject_code",
    "subproject_id",
    "passthrough",
    "created_by_cost_import_id",
    "updated_by_cost_import_ids",
    "excluded",
}


def _read(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["value"]


def _imports() -> list[dict[str, Any]]:
    return _read(module.NAME)["imports"]


def _lines() -> list[dict[str, Any]]:
    return _read(module.NAME)["lines"]


def _events() -> list[dict[str, Any]]:
    return _read("project_state_transitions.json")["events"]


def test_the_costs_are_held_by_the_check_of_make_mock_data_up_to_date() -> None:
    # « L'engendrement du jeu aboutit sur une plateforme neuve et produit les volumes annoncés. »
    assert module.NAME in mockdata.named()
    assert module.NAME in mockdata.declared_names()
    assert FILE.read_text(encoding="utf-8") == mockdata.render(mockdata.named()[module.NAME])
    assert not [problem for problem in mockdata.check(FIXTURES) if module.NAME in problem]


def test_the_costs_are_declared_generated_by_make_mock_data() -> None:
    # A file written by the generator is declared so, and left out of a lot's size.
    declared = [
        entry for entry in paths.read().generated if f"fixtures/api/{module.NAME}" in entry.paths
    ]
    assert [entry.by for entry in declared] == ["make mock-data"]


def test_two_engenderings_give_the_same_bytes() -> None:
    # « Deux engendrements successifs donnent des données identifiantes identiques. »
    first = mockdata.render(module.examples()[module.NAME])
    second = mockdata.render(module.examples()[module.NAME])
    assert first == second


def test_the_file_is_an_example_of_a_summary_a_description_and_a_value() -> None:
    assert set(json.loads(FILE.read_text(encoding="utf-8"))) == {"summary", "description", "value"}
    assert set(_read(module.NAME)) == {"imports", "lines"}


def test_each_import_of_the_journal_is_there_with_its_counts_and_its_exchange() -> None:
    # The five imports of the journal (cost_imports.json), in the order they were applied, each
    # with the import of the exchanges that applied it and the file it came from (imports.json).
    journal = {item["cost_import_id"]: item for item in _read("cost_imports.json")["items"]}
    exchanges = {item["import_id"]: item for item in _read("imports.json")["items"]}
    assert len(_imports()) == len(JOURNAL) == 5
    assert [entry["imported_at"] for entry in _imports()] == sorted(
        entry["imported_at"] for entry in _imports()
    )
    for entry in _imports():
        assert set(entry) == IMPORT_KEYS
        kept = journal[entry["cost_import_id"]]
        assert entry["imported_at"] == kept["imported_at"]
        assert (entry["period_from"], entry["period_to"]) == (
            kept["period_from"],
            kept["period_to"],
        )
        for count in ("created", "updated", "unchanged", "rejected"):
            assert entry[f"{count}_count"] == kept[f"{count}_count"], entry["filename"]
        exchange = exchanges[entry["import_id"]]
        assert entry["filename"] == exchange["filename"]
        assert (exchange["kind"], exchange["status"]) == ("actual_costs", "applied")
        assert (entry["period_from"], entry["period_to"]) == (
            exchange["period_from"],
            exchange["period_to"],
        )


def test_the_report_of_an_import_counts_what_the_journal_counts() -> None:
    # The report as the analysis presented it: lines read = added + updated + unchanged + rejected,
    # and the counts of the journal are those of the report.
    for entry in _imports():
        report = entry["report"]
        changes = [difference["change"] for difference in report["differences"]]
        assert changes.count("added") == entry["created_count"]
        assert changes.count("updated") == entry["updated_count"]
        assert report["unchanged_count"] == entry["unchanged_count"]
        assert len(report["rejected"]) == entry["rejected_count"]
        assert report["read_count"] == (
            len(changes) + report["unchanged_count"] + len(report["rejected"])
        )
        assert {difference["target"] for difference in report["differences"]} <= {
            "actual_cost_line"
        }


def test_the_report_of_april_is_the_one_the_analysis_example_presents() -> None:
    # The first extraction of April: the report is the one getImport answered before its
    # application (import_actual_costs_first.json).
    [april] = [entry for entry in _imports() if entry["filename"] == "couts-reels-2026-04.xlsx"]
    presented = _read("import_actual_costs_first.json")
    assert april["import_id"] == presented["import_id"]
    assert april["report"] == presented["report"]


def test_the_columns_kept_by_an_import_are_those_of_the_lines_it_brought() -> None:
    declared = _read("actual_cost_mapping.json")["kept_columns"]
    for entry in _imports():
        brought = [
            line
            for line in _lines()
            if entry["cost_import_id"]
            in (line["created_by_cost_import_id"], *line["updated_by_cost_import_ids"])
        ]
        expected: list[str] = declared if brought else []
        assert entry["kept_columns"] == expected, entry["filename"]


def test_the_file_gives_the_twenty_eight_lines_of_the_consultation() -> None:
    # The lines the consultation reads (actual_costs.json): the same, by document and item, with
    # their date, amount, subproject, excluded state and columns kept.
    read = {item["cost_line_id"]: item for item in _read("actual_costs.json")["items"]}
    assert len(_lines()) == len(mockcosts.lines()) == len(read) == 28
    for line in _lines():
        assert set(line) == LINE_KEYS
        item = read[line["cost_line_id"]]
        assert line["document_number"] == item["document_number"]
        assert line["document_item"] == item["document_item"]
        assert line["document_date"] == item["document_date"]
        assert line["amount"] == item["amount"]
        assert line["subproject_code"] == item["subproject_code"]
        assert line["subproject_id"] == item["subproject_id"]
        assert line["passthrough"] == item["passthrough"]
        assert (line["excluded"] is None) is item["is_in_tracked_scope"]


def test_a_line_names_the_import_that_brought_it_and_those_that_updated_it() -> None:
    # WF-CRE-0010: the first import creates a line, the others update it; they exist in the journal.
    known = {entry["cost_import_id"]: entry for entry in _imports()}
    for line in _lines():
        brought = [line["created_by_cost_import_id"], *line["updated_by_cost_import_ids"]]
        assert set(brought) <= set(known), line["document_number"]
        instants = [known[each]["imported_at"] for each in brought]
        assert instants == sorted(instants), line["document_number"]
        assert len(set(brought)) == len(brought)
    for entry in _imports():
        created = [
            line
            for line in _lines()
            if line["created_by_cost_import_id"] == entry["cost_import_id"]
        ]
        updated = [
            line
            for line in _lines()
            if entry["cost_import_id"] in line["updated_by_cost_import_ids"]
        ]
        assert (len(created), len(updated)) == (entry["created_count"], entry["updated_count"])


def test_the_lines_are_identified_by_their_document_and_their_item() -> None:
    # WF-INTF-0140, D-4: a document and its item identify a line of the project, once.
    keys = [(line["document_number"], line["document_item"]) for line in _lines()]
    assert len(keys) == len(set(keys))
    identifiers = [line["cost_line_id"] for line in _lines()]
    assert len(identifiers) == len(set(identifiers))


def test_the_exclusion_of_the_reception_of_the_customer_is_in_the_file_and_in_the_chronology() -> (
    None
):
    # WF-CRE-0030: one line is excluded, on 6 April at 9:15, with its reason; the chronology has an
    # event for it, at that instant, naming the document, the item and the reason.
    [excluded] = [line for line in _lines() if line["excluded"] is not None]
    assert excluded["excluded"] == {
        "excluded_at": "2026-04-06T09:15:00Z",
        "reason": "Réception du client, non budgétée",
    }
    what = mockwitness.RECEPTION_EXCLUDED.what
    [event] = [event for event in _events() if event["what"] == what]
    assert event["occurred_at"] == excluded["excluded"]["excluded_at"]
    assert event["writes"] == [
        {
            "kind": "cost_line_excluded",
            "project": "PRJ-001",
            "document": excluded["document_number"],
            "item": excluded["document_item"],
            "reason": excluded["excluded"]["reason"],
        }
    ]
    assert mockwitness.RECEPTION_EXCLUDED.instant == datetime(2026, 4, 6, 9, 15, tzinfo=UTC)
    # Excluded after the first import that brought it, and before the next one.
    first = next(
        entry
        for entry in _imports()
        if entry["cost_import_id"] == excluded["created_by_cost_import_id"]
    )
    assert first["imported_at"] < excluded["excluded"]["excluded_at"]


def test_each_import_of_the_journal_is_applied_by_an_event_of_the_chronology() -> None:
    # The five events « Import de coûts réels » write cost_import_applied, with the import's
    # identifier, at the instant of the import.
    applied = [
        (event["occurred_at"], write["cost_import_id"])
        for event in _events()
        for write in event["writes"]
        if write["kind"] == "cost_import_applied"
    ]
    assert applied == [(entry["imported_at"], entry["cost_import_id"]) for entry in _imports()]
    for event in _events():
        kinds = [write["kind"] for write in event["writes"]]
        assert (kinds == ["cost_import_applied"]) is (event["what"] == "Import de coûts réels")
    assert hex_identifier(0xC11) == applied[0][1]


def test_the_replayed_extraction_of_april_expires_in_the_chronology() -> None:
    # The re-extraction of 2 June, analysed and expired the day after, is an import of the exchanges
    # that was never applied (imports.json); its event writes import_expired.
    [event] = [event for event in _events() if event["what"].startswith("Extraction d'avril")]
    [write] = event["writes"]
    assert write == {
        "kind": "import_expired",
        "project": "PRJ-001",
        "import_id": module.expired_exchange_id(),
    }
    expired = next(item for item in _read("imports.json")["items"] if item["status"] == "expired")
    assert expired["import_id"] == write["import_id"]
    assert expired["kind"] == "actual_costs"
    assert expired["import_id"] not in {entry["import_id"] for entry in _imports()}


def test_the_amounts_of_the_lines_total_those_of_the_consultation() -> None:
    # The computed becomes the expected: the lines add up to the totals the consultation reads.
    totals = _read("actual_costs.json")["totals"]
    overall = sum(float(line["amount"]) for line in _lines())
    assert f"{overall:.2f}" == totals["overall"]


def test_no_address_and_only_the_fictitious_suppliers_of_the_witness() -> None:
    # « Aucune adresse électronique ni aucun libellé de projet réel n'y figure. »
    assert "@" not in FILE.read_text(encoding="utf-8")
    suppliers = {value for line in _lines() for value in line["passthrough"].values()}
    described = {value for line in mockcosts.lines() for value in (line.supplier, line.text)}
    assert suppliers <= described
