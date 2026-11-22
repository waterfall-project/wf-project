# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the examples of the contract of the exchanges that EP-33 changes (US-3250/L1, #4525).

Each example is held to the operation that cites it, to the condition, the code or the shape the
contract declares for it, and to the readings it derives from (``wftools.mockimportfindings``).
They try the examples of the fake back, not the Vérif of a requirement: none cites one
(WF-QUA-0010); the criterion they bear is the US's own — the contract and its examples follow
(US-3250), and prepare those of US-3200, US-3210, US-3230 and US-3240.
"""

from datetime import timedelta
from decimal import Decimal
from functools import cache
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockimportfindings
from wftools.mockexchanges import tab_name
from wftools.mockwitness import SUBPROJECT_CONTROL, TODAY, fixture

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"


@cache
def _operations() -> dict[str, Entry]:
    """Return every operation of the contract, by its identifier."""
    found: dict[str, Entry] = {}
    for path in sorted((API / "paths").glob("*.yaml")):
        for item in cast("dict[str, Entry]", yaml.safe_load(path.read_text("utf-8"))).values():
            for operation in item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    found[cast("str", operation["operationId"])] = cast("Entry", operation)
    return found


def _cited(operation: str, status: str) -> list[str]:
    """Return the examples an answer of an operation cites, by the name of their file."""
    answer = _operations()[operation]["responses"][status]
    [content] = cast("dict[str, Entry]", answer["content"]).values()
    return [Path(each["$ref"]).stem for each in content["examples"].values()]


def _schema(file: str, name: str) -> Entry:
    path = API / "components" / file
    return cast("Entry", yaml.safe_load(path.read_text("utf-8"))[name])


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_every_example_is_the_one_the_generator_writes_and_is_cited() -> None:
    cited = {
        "import_apply_structure_changed": ("applyImport", "409"),
        "file_upload_permission_missing": ("uploadFile", "403"),
        "file_upload_pending_limit": ("uploadFile", "409"),
        "file_upload_filename_nul": ("uploadFile", "422"),
        "import_actual_costs_task_purged": ("getImport", "200"),
        "import_remaining_column_missing": ("openImport", "422"),
        "import_remaining_amount_rounded": ("getImport", "200"),
    }
    written = mockimportfindings.examples()
    assert sorted(written) == sorted(f"{name}.json" for name in cited)
    for name, (operation, status) in cited.items():
        assert fixture(name) == written[f"{name}.json"]["value"], name
        assert name in _cited(operation, status), name


@pytest.mark.story("US-3210")
def test_an_application_on_a_structure_written_since_is_refused_for_good_by_its_condition() -> None:
    refused = fixture("import_apply_structure_changed")
    assert (refused["status"], refused["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert refused["params"] == {"missing_condition": "import_structure_unchanged"}
    said = _flat(_operations()["applyImport"]["responses"]["409"]["description"])
    # After ``import_file_accepted``, before the state conditions, among the refusals for good.
    accepted = said.index("Then `import_file_accepted`")
    assert accepted < said.index("Then `import_structure_unchanged`") < said.index("Then the state")
    good = said[said.index("Refused for good") :]
    assert "`import_structure_unchanged`" in good[: good.index("the import becomes `refused`")]
    # The analysed import is the estimate of the amendment 2, and the write since one on it, which
    # moves the counter of its structure past the one the analysis read.
    analysed = fixture("import_analysed")
    assert analysed["status"] == "analysed"
    [structure] = [
        each for each in fixture("structures") if each["structure_id"] == analysed["structure_id"]
    ]
    written = fixture("estimate_line_updated_amendment")
    assert written["structure_lock_version"] > structure["lock_version"]


@pytest.mark.story("US-3240")
def test_an_upload_is_refused_without_an_import_permission_and_beyond_twenty_pending() -> None:
    missing = fixture("file_upload_permission_missing")
    assert (missing["status"], missing["code"]) == (403, "PERMISSION_MISSING")
    assert missing["params"] == {"missing_permission": "planning.write"}
    pending = fixture("file_upload_pending_limit")
    assert (pending["status"], pending["code"]) == (409, "STATE_FORBIDS_OPERATION")
    assert pending["params"] == {"missing_condition": "pending_uploads_below_limit", "maximum": 20}
    said = _flat(_operations()["uploadFile"]["description"])
    for permission in mockimportfindings.IMPORT_PERMISSIONS:
        assert f"`{permission}`" in said
    nul = fixture("file_upload_filename_nul")
    assert (nul["status"], nul["code"]) == (422, "VALIDATION_FAILED")
    assert nul["fields"] == [{"pointer": "/file", "code": "VALIDATION_FAILED"}]


@pytest.mark.story("US-3250")
def test_an_import_whose_task_was_deleted_is_read_with_its_task_null() -> None:
    read = fixture("import_actual_costs_task_purged")
    listed = {each["import_id"]: each for each in fixture("imports")["items"]}[read["import_id"]]
    # The import of the list, applied, its report the one its analysis presented.
    assert {key: read[key] for key in listed} == listed
    assert listed["status"] == "applied"
    assert read["report"] == fixture("import_actual_costs_first")["report"]
    assert read["task"] is None
    commands = {each["command"]: each["missing_conditions"] for each in read["available_commands"]}
    assert commands == {"apply": ["import_awaiting_decision"], "abandon": ["import_not_applied"]}
    # Its application ended more than the retention of a task ago.
    retention = fixture("system_status")["operating_parameters"]["background_task_retention_days"]
    assert TODAY - mockimportfindings.applied_at() > timedelta(days=retention)
    # The contract lets the task be null, in the list's schema and the reading's.
    detail = _schema("schemas/exchanges.yaml", "ImportDetail")["allOf"][1]
    assert {"type": "null"} in detail["properties"]["task"]["anyOf"]
    imported = _schema("schemas/exchanges.yaml", "Import")
    assert {"type": "null"} in imported["properties"]["task"]["anyOf"]


@pytest.mark.story("US-3250")
def test_the_three_operations_say_the_purge_deletes_an_import_expired_or_abandoned() -> None:
    for operation in ("listImports", "getImport", "abandonImport"):
        said = _flat(_operations()[operation]["description"])
        assert "pass of the purge" in said, operation
        assert "expired or abandoned" in said or "abandoned import is deleted" in said, operation
    status = _flat(
        _schema("schemas/exchanges.yaml", "Import")["properties"]["status"]["description"]
    )
    assert "deleted, its report included, by the pass of the purge" in status


@pytest.mark.story("US-3200")
def test_a_remaining_to_commit_whose_tab_lost_a_column_names_it_with_its_tab() -> None:
    refused = fixture("import_remaining_column_missing")
    assert (refused["status"], refused["code"]) == (422, "FILE_FORMAT_UNREADABLE")
    params = refused["params"]
    assert (params["expected_format"], params["expected_version"]) == ("remaining", "1")
    assert params["missing_columns"] == [
        {"header": "Débours restant", "sheet": tab_name(SUBPROJECT_CONTROL)}
    ]
    # The one or the other: a column of an extraction by its identifier, one of a workbook by its
    # header and its sheet.
    shape = _schema("common.yaml", "ProblemMissingColumn")
    assert shape["oneOf"] == [{"required": ["column", "labels"]}, {"required": ["header", "sheet"]}]


@pytest.mark.story("US-3230")
def test_a_line_whose_amount_is_rounded_is_signalled_with_both_amounts() -> None:
    analysed = fixture("import_remaining_analysed")
    rounded = fixture("import_remaining_amount_rounded")
    [signal] = rounded["report"]["signals"]
    assert (signal["code"], signal["column"]) == ("AMOUNT_ROUNDED", "unit_disbursement")
    typed = Decimal(signal["params"]["typed_amount"])
    written = Decimal(signal["params"]["written_amount"])
    # 1,234.56 entered on a quantity of 1,000 write 1,230.00 (#4428).
    assert (typed, written) == (Decimal("1234.56"), Decimal("1230.00"))
    assert written == mockimportfindings.unit_disbursement(typed) * Decimal(1000)
    # An amount that divides exactly writes itself.
    assert mockimportfindings.written_amount(Decimal("1230.00")) == Decimal("1230.00")
    # The line the report presents, by its lineage and its label; the rest of the report kept.
    [difference] = [
        each
        for each in rounded["report"]["differences"]
        if each["lineage_id"] == signal["lineage_id"]
    ]
    assert (difference["label"], difference["fields"]) == (signal["label"], ["unit_disbursement"])
    kept = {key for key in analysed["report"] if key not in {"differences", "signals"}}
    assert {key: rounded["report"][key] for key in kept} == {
        key: analysed["report"][key] for key in kept
    }
    code = _schema("schemas/exchanges.yaml", "ImportSignal")["properties"]["code"]["allOf"][1]
    assert "AMOUNT_ROUNDED" in code["enum"]
    signals = _flat(
        _schema("schemas/exchanges.yaml", "ImportReport")["properties"]["signals"]["description"]
    )
    assert "and for Excel imports" not in signals
