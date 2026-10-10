# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the bounds the writes publish and of the refusal that crosses them (EP-14/L42o, #677).

Each bound a schema of a write publishes in `minimum` or `maximum` has its refusal told under the
422 of its operation — `VALUE_OUT_OF_RANGE`, the one bound crossed in `params` — with an example
after the first. They try the examples against the contract, not the Vérif of a requirement: none
cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from typing import Any

import pytest

from wftools import REPOSITORY, mockwitness
from wftools.mockwitness import fixture

API = REPOSITORY / "docs" / "api"

BOUNDED = [
    ("setBackupSchedule", "BackupSchedule", "weekday", "/weekday"),
    ("createNode", "NodeCreate", "position", "/position"),
    ("createNode", "EstimateLineWrite", "payment_delay_days", "/estimate_line/payment_delay_days"),
    ("updateEstimateLine", "EstimateLineUpdate", "payment_delay_days", "/payment_delay_days"),
    ("moveNodes", "NodeMove", "position", "/position"),
    ("requestExport", "ExportRequest", "depth", "/depth"),
]
"""Each bound of #677: the operation, the schema of its body, the field and its pointer."""

REFUSED = {
    "setBackupSchedule": ("platform.yaml", "backup_schedule_weekday_out_of_range"),
    "createNode": ("revisions.yaml", "node_create_out_of_range"),
    "updateEstimateLine": ("revisions.yaml", "estimate_line_payment_delay_out_of_range"),
    "moveNodes": ("revisions.yaml", "nodes_move_position_out_of_range"),
    "requestExport": ("exchanges.yaml", "export_depth_out_of_range"),
}
"""The file of each operation and the example of its refusal."""

FIRST = {
    "setBackupSchedule": "backup_schedule_unknown_location",
    "createNode": "estimate_line_provision_refused",
}
"""The first example of the 422 that the fake back served before the bounds, which stays first."""

WRITES = {
    "platform.yaml": ["BackupSchedule", "BackupExternalCopy"],
    "revisions.yaml": ["NodeCreate", "EstimateLineWrite", "EstimateLineUpdate", "NodeMove"],
    "exchanges.yaml": ["ExportRequest"],
}
"""The schemas of the bodies of the five operations, each bound of which has its refusal."""

TOLD_BEFORE = {("BackupSchedule", "retained_count"), ("BackupExternalCopy", "retained_count")}
"""The bounds whose refusal EP-14/L42m told (`backup_schedule_retention_out_of_range`)."""


def _block(file: str, schema: str) -> str:
    text = (API / "components" / "schemas" / file).read_text(encoding="utf-8")
    return text.split(f"\n{schema}:\n", 1)[1].split("\n\n", 1)[0]


def _properties(file: str, schema: str) -> dict[str, str]:
    """Return the text of each property of a schema, by its name."""
    found = re.split(r"\n    (\w+):", _block(file, schema).split("\n  properties:", 1)[1])
    return dict(zip(found[1::2], found[2::2], strict=True))


def _bounds(file: str, schema: str, field: str) -> dict[str, int]:
    text = _properties(file, schema)[field]
    return {key: int(value) for key, value in re.findall(r"\b(minimum|maximum): (\d+)", text)}


def _schema_file(schema: str) -> str:
    return next(file for file, schemas in WRITES.items() if schema in schemas)


def _refusals(operation: str) -> str:
    file, _ = REFUSED[operation]
    text = (API / "paths" / file).read_text(encoding="utf-8")
    block = text.split(f"operationId: {operation}\n", 1)[1].split("operationId:", 1)[0]
    return block.split("'422':", 1)[1].split("\n      '", 1)[0]


@pytest.mark.parametrize(("operation", "schema", "field", "pointer"), BOUNDED)
def test_a_value_out_of_its_bounds_is_refused_with_the_one_bound_it_crosses(
    operation: str, schema: str, field: str, pointer: str
) -> None:
    bounds = _bounds(_schema_file(schema), schema, field)
    assert bounds, (schema, field)
    _, name = REFUSED[operation]
    refused = fixture(name)
    assert set(refused) == {"code", "status", "fields", "correlation_id"}
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    [told] = [each for each in refused["fields"] if each["pointer"] == pointer]
    assert told["code"] == "VALUE_OUT_OF_RANGE"
    # One bound, the one the schema publishes on the side crossed.
    [(side, bound)] = told["params"].items()
    assert bounds[side] == bound, (schema, field)
    # The operation tells the refusal at its pointer.
    refusals = _refusals(operation)
    assert f"`{pointer}`" in refusals, operation
    assert "VALUE_OUT_OF_RANGE" in refusals, operation


@pytest.mark.parametrize("operation", sorted(REFUSED))
def test_each_refusal_is_cited_last_under_its_422_after_the_first_the_fake_back_serves(
    operation: str,
) -> None:
    _, name = REFUSED[operation]
    cited = re.findall(r"fixtures/api/(\w+)\.json", _refusals(operation))
    assert cited[-1] == name
    assert cited[0] == FIRST.get(operation, name)


def test_every_bound_of_the_bodies_has_its_refusal_but_the_counter() -> None:
    # `lock_version` is a counter, not an entry: its 412 says it is stale (WF-IHM-0110).
    published = {
        (schema, field)
        for file, schemas in WRITES.items()
        for schema in schemas
        for field in _properties(file, schema)
        if field != "lock_version" and _bounds(file, schema, field)
    }
    assert published == {(schema, field) for _, schema, field, _ in BOUNDED} | TOLD_BEFORE


def test_the_examples_keep_within_the_bounds() -> None:
    # The weekly schedules within the days of the week, the lines and nodes within theirs.
    weekday = _bounds("platform.yaml", "BackupSchedule", "weekday")
    for path in sorted(mockwitness.FIXTURES.glob("backup_schedule*.json")):
        value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))["value"]
        if value.get("weekday") is not None:
            assert weekday["minimum"] <= value["weekday"] <= weekday["maximum"], path.name
    delay = _bounds("revisions.yaml", "EstimateLineWrite", "payment_delay_days")
    position = _bounds("revisions.yaml", "NodeMove", "position")
    volume = mockwitness.FIXTURES / "volume" / "nodes_thousand.json"
    nodes = json.loads(volume.read_text(encoding="utf-8"))["value"]["items"]
    lines = [node["estimate_line"] for node in nodes if node.get("estimate_line")]
    assert lines
    for line in lines:
        assert (line["payment_delay_days"] or 0) >= delay["minimum"], line["label"]
    assert min(node["position"] for node in nodes) == position["minimum"]
