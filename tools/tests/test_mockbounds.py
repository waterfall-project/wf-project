# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the bounds the writes publish and of the refusal that crosses them (EP-14/L42o, #677).

Each bound a body of a write publishes in `minimum` or `maximum`, wherever it lies in the schemas
the body refers to, has its refusal told under the 422 of its operation — `VALUE_OUT_OF_RANGE`, the
one bound crossed in `params` — with an example after the first (EP-14/L42r, #711: every body, read
from the contract, not five of them listed). They try the examples against the contract, not the
Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import fixture

API = REPOSITORY / "docs" / "api"

PATHS = sorted((API / "paths").glob("*.yaml"))

CONTRACT = sorted([API / "openapi.yaml", *PATHS, *(API / "components").rglob("*.yaml")])
"""The files of the contract written by hand: never a bundle `make build-openapi` writes beside."""

ANY = "<…>"
"""A key a map of the body chooses — a grid, a column —, which a pointer names between brackets."""

REFUSED = {
    ("setBackupSchedule", "/weekday"): "backup_schedule_weekday_out_of_range",
    ("setBackupSchedule", "/retained_count"): "backup_schedule_retention_out_of_range",
    ("setBackupSchedule", "/external_copy/retained_count"): (
        "backup_schedule_retention_out_of_range"
    ),
    ("setIdentitySyncSchedule", "/weekday"): "identity_sync_schedule_weekday_out_of_range",
    ("updateReferenceSettings", "/max_weeks_between_reviews"): "reference_settings_out_of_range",
    ("createNode", "/estimate_line/payment_delay_days"): "node_create_out_of_range",
    ("updateEstimateLine", "/payment_delay_days"): "estimate_line_payment_delay_out_of_range",
    ("requestExport", "/depth"): "export_depth_out_of_range",
    ("updateMyPreferences", f"/grids/{ANY}/column_widths/{ANY}"): (
        "preferences_column_width_out_of_range"
    ),
    ("updateMyPreferences", f"/timelines/{ANY}/lanes/{ANY}"): "preferences_lane_out_of_range",
    ("openChunkedUpload", "/size_bytes"): "chunked_upload_size_out_of_range",
}
"""Each bound of a body, by its operation and its pointer, and the example of its refusal."""

FIRST = {
    "setBackupSchedule": "backup_schedule_unknown_location",
    "createNode": "estimate_line_provision_refused",
    "updateReferenceSettings": "reference_settings_bounds_refused",
}
"""The first example of the 422 that the fake back served before the bounds, which stays first."""

KEY = re.compile(r"(?P<key>'[^']*'|[\w$/.{}-]+):(?: |$)")
REF = re.compile(r"\$ref: *'?(?P<ref>[^'\s},\]]+)'?")
BOUND = re.compile(
    r"\b(?P<side>minimum|maximum|exclusiveMinimum|exclusiveMaximum): (?P<bound>-?\d+(?:\.\d+)?)\b"
)
FOLDED = {">", ">-", "|", "|-"}
ITEM = "-"
"""The place of an item of a list written as a flow map, `- { $ref: … }`: it adds to no pointer."""

type Bound = tuple[str, str, Decimal]
"""A bound: the pointer of the field, the side, and the value."""


def _walk(value: Any) -> list[dict[str, Any]]:
    """Return every object a value read from JSON holds, itself included."""
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _walk(item)]
    if not isinstance(value, dict):
        return []
    entry = cast("dict[str, Any]", value)
    return [entry, *(found for item in entry.values() for found in _walk(item))]


def keyed(text: str, missed: list[str] | None = None) -> Iterator[tuple[tuple[str, ...], str]]:
    """Yield each line of YAML with the keys that lead to it, and what follows its own key.

    The text of a folded scalar — a description — is skipped; an item of a list is read as a map at
    the place of its first key, or, written as a flow map, at the place of the list. Any other line
    is not read, and goes to `missed` when it is given.
    """
    stack: list[tuple[int, str]] = []
    folded: int | None = None
    for line in text.splitlines():
        body = line.lstrip(" ")
        indent = len(line) - len(body)
        if not body or body.startswith("#") or (folded is not None and indent > folded):
            continue
        folded = None
        if body.startswith("- "):
            indent, body = indent + 2, body[2:]
        found = KEY.match(body)
        if found is None and body.startswith("{"):
            while stack and stack[-1][0] >= indent:
                stack.pop()
            yield (*(key for _, key in stack), ITEM), body
            continue
        if found is None:
            if missed is not None:
                missed.append(line)
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, found["key"]))
        rest = body[found.end() :].strip()
        if rest in FOLDED:
            folded = indent
        yield tuple(key for _, key in stack), f"{found['key']}: {rest}"


def pointer(keys: tuple[str, ...]) -> str:
    """Return the pointer of the field the keys of a schema lead to: its properties, its maps."""
    parts: list[str] = []
    for before, key in zip(("", *keys), keys, strict=False):
        if before == "properties":
            parts.append(key)
        elif key == "additionalProperties":
            parts.append(ANY)
        elif key == "items":
            parts.append("<n>")
    return "".join(f"/{part}" for part in parts)


def schema_text(file: Path, name: str) -> str:
    """Return the text of a schema written at the top of a file of the contract."""
    text = "\n" + file.read_text(encoding="utf-8")
    return re.split(r"\n(?=\S)", text.split(f"\n{name}:\n", 1)[1], maxsplit=1)[0]


def bounds(text: str, file: Path, at: str = "", seen: frozenset[str] = frozenset()) -> set[Bound]:
    """Return the bounds a text of schema publishes, the schemas it refers to followed.

    A schema already followed on the way is not followed again: a tree refers to itself.
    """
    found: set[Bound] = set()
    for keys, line in keyed(text):
        here = at + pointer(keys)
        found |= {(here, b["side"], Decimal(b["bound"])) for b in BOUND.finditer(line)}
        for each in REF.finditer(line):
            target, _, name = each["ref"].partition("#/")
            if target.endswith(".json"):
                # An example of the body, not a schema: it publishes no bound (EP-14/L42k).
                continue
            path = (file.parent / target).resolve() if target else file
            followed = f"{path}#{name}"
            if followed not in seen:
                found |= bounds(schema_text(path, name), path, here, seen | {followed})
    return found


def operations() -> dict[str, tuple[Path, str]]:
    """Return each operation of the contract, its file of paths and its text."""
    found: dict[str, tuple[Path, str]] = {}
    for file in PATHS:
        for block in file.read_text(encoding="utf-8").split("operationId: ")[1:]:
            name, text = block.split("\n", 1)
            found[name.strip()] = (file, text)
    return found


def body(text: str) -> str:
    """Return the request body an operation declares, or nothing."""
    if "\n    requestBody:\n" not in text:
        return ""
    return text.split("\n    requestBody:\n", 1)[1].split("\n    responses:", 1)[0]


def refusals(text: str) -> str:
    """Return the 422 an operation declares in place."""
    return text.split("\n      '422':", 1)[1].split("\n      '", 1)[0]


def published() -> dict[tuple[str, str], dict[str, Decimal]]:
    """Return every bound of every body of a write, by operation and pointer — but the counters.

    `lock_version` is a counter, not an entry: its 412 says it is stale (WF-IHM-0110); so are the
    counters a confirmation sends back, those of the structures a merge read (`StructureMerge`,
    `…_lock_version`, EP-14/L42s).
    """
    found: dict[tuple[str, str], dict[str, Decimal]] = {}
    for name, (file, text) in operations().items():
        for at, side, bound in bounds(body(text), file):
            if not at.endswith("lock_version"):
                found.setdefault((name, at), {})[side] = bound
    return found


def _pattern(at: str, key: str) -> str:
    return "".join(key if part == ANY else re.escape(part) for part in re.split(f"({ANY})", at))


def told(at: str, said: str) -> bool:
    """Say whether the contract names a pointer, a key a map chooses between brackets."""
    return re.search(f"`{_pattern(at, '<[^>`]+>')}`", said) is not None


def designates(at: str, sent: str) -> bool:
    """Say whether the pointer of a refusal designates the field, a key a map chooses as it is."""
    return re.fullmatch(_pattern(at, "[^/]+"), sent) is not None


def test_every_bound_of_every_body_has_its_refusal_told_and_its_example() -> None:
    assert set(published()) == set(REFUSED)


def test_every_body_of_the_contract_is_read() -> None:
    declared = sum(file.read_text(encoding="utf-8").count("requestBody:") for file in PATHS)
    read = [name for name, (_, text) in operations().items() if body(text)]
    assert len(read) == declared > 60


def test_no_reference_nor_bound_of_the_contract_escapes_the_reading() -> None:
    # A line outside a folded text that names a schema or a bound, and that `keyed` cannot place,
    # would leave a bound unseen: there is none in the contract (revue 1).
    for file in CONTRACT:
        missed: list[str] = []
        for _ in keyed(file.read_text(encoding="utf-8"), missed):
            pass
        assert [line for line in missed if REF.search(line) or BOUND.search(line)] == [], file.name
    missed = []
    for _ in keyed("A:\n  b: [\n    1, { $ref: x } ]\n", missed):
        pass
    assert missed == ["    1, { $ref: x } ]"]


def test_the_bounds_are_read_through_the_schemas_a_body_refers_to(tmp_path: Path) -> None:
    schemas = tmp_path / "components" / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "a.yaml").write_text(
        "Prefs:\n  properties:\n    grids:\n      additionalProperties:\n"
        "        anyOf: [{ $ref: '#/Grid' }, { type: 'null' }]\n"
        "    note:\n      description: >-\n        minimum: 3 is prose.\n"
        "    tree:\n      anyOf:\n        - { $ref: '#/Tree' }\n        - type: 'null'\n"
        "Grid:\n  allOf:\n    - $ref: b.yaml#/Base\n    - type: object\n      properties:\n"
        "        widths:\n          additionalProperties: { type: integer, minimum: 20 }\n"
        "Tree:\n  properties:\n    rate: { type: number, exclusiveMinimum: -0.5 }\n"
        "    children:\n      type: array\n      items: { $ref: '#/Tree' }\n",
        encoding="utf-8",
    )
    (schemas / "b.yaml").write_text(
        "Base:\n  properties:\n    day:\n      type: integer\n      minimum: 1\n      maximum: 7\n",
        encoding="utf-8",
    )
    text = "      content:\n        application/json:\n          schema: { $ref: a.yaml#/Prefs }\n"
    # A tree that refers to itself is read once along each way, its bounds where it first lies.
    assert bounds(text, schemas / "x.yaml") == {
        (f"/grids/{ANY}/widths/{ANY}", "minimum", Decimal(20)),
        (f"/grids/{ANY}/day", "minimum", Decimal(1)),
        (f"/grids/{ANY}/day", "maximum", Decimal(7)),
        ("/tree/rate", "exclusiveMinimum", Decimal("-0.5")),
    }
    assert told(f"/grids/{ANY}/widths/{ANY}", "sur `/grids/<grille>/widths/<colonne>` par")
    assert not told(f"/grids/{ANY}/widths/{ANY}", "sur `/grids/widths` par")
    assert designates(f"/grids/{ANY}/widths/{ANY}", "/grids/estimate/widths/label")
    assert not designates(f"/grids/{ANY}/day", "/grids/estimate/widths/label")


@pytest.mark.parametrize(("operation", "at"), sorted(REFUSED))
def test_a_value_out_of_its_bounds_is_refused_with_the_one_bound_it_crosses(
    operation: str, at: str
) -> None:
    schema = published()[operation, at]
    refused = fixture(REFUSED[operation, at])
    assert set(refused) == {"code", "status", "fields", "correlation_id"}
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    [crossed] = [each for each in refused["fields"] if designates(at, each["pointer"])]
    assert crossed["code"] == "VALUE_OUT_OF_RANGE"
    # One bound, the one the schema publishes on the side crossed: a number as the field is.
    [(side, bound)] = crossed["params"].items()
    assert schema[side] == Decimal(str(bound)), (operation, at)
    # The operation tells the refusal at its pointer.
    said = refusals(operations()[operation][1])
    assert told(at, said), operation
    assert "VALUE_OUT_OF_RANGE" in said, operation


@pytest.mark.parametrize("operation", sorted({operation for operation, _ in REFUSED}))
def test_the_refusals_of_the_bounds_form_one_block_after_the_first_example(
    operation: str,
) -> None:
    # The first example of the 422, the one the fake back serves, stays first; the refusals of the
    # bounds come after it, together, whatever other examples come before or after them
    # (EP-14/L42s). A 422 without an example before its bounds has its refusals first, in the order
    # of their names.
    names = {name for (each, _), name in REFUSED.items() if each == operation}
    cited = re.findall(r"fixtures/api/(\w+)\.json", refusals(operations()[operation][1]))
    assert cited[0] == FIRST.get(operation, cited[0])
    start = min(cited.index(name) for name in names)
    assert set(cited[start : start + len(names)]) == names
    if operation in FIRST:
        assert start > 0
    else:
        assert cited[: len(names)] == sorted(names)


def test_the_examples_keep_within_the_bounds() -> None:
    # The weekly schedules within the days of the week, the lines within theirs.
    weekday = published()["setBackupSchedule", "/weekday"]
    for path in sorted(mockwitness.FIXTURES.glob("backup_schedule*.json")):
        value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))["value"]
        if value.get("weekday") is not None:
            assert weekday["minimum"] <= value["weekday"] <= weekday["maximum"], path.name
    delay = published()["createNode", "/estimate_line/payment_delay_days"]
    volume = mockwitness.FIXTURES / "volume" / "nodes_thousand.json"
    nodes = json.loads(volume.read_text(encoding="utf-8"))["value"]["items"]
    lines = [node["estimate_line"] for node in nodes if node.get("estimate_line")]
    assert lines
    for line in lines:
        assert (line["payment_delay_days"] or 0) >= delay["minimum"], line["label"]
    # Every example that bears widths of columns — the preferences, the account — keeps them at
    # least as wide as the narrowest admitted.
    width = published()["updateMyPreferences", f"/grids/{ANY}/column_widths/{ANY}"]
    checked: list[str] = []
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        for entry in _walk(json.loads(path.read_text(encoding="utf-8"))["value"]):
            widths = cast("dict[str, int]", entry.get("column_widths") or {})
            assert all(each >= width["minimum"] for each in widths.values()), path.name
            checked.extend(path.name for _ in widths)
    assert checked
    assert "me_grid_settings.json" in checked


PAGE_SIZES = (10, 25, 50, 100)
"""The numbers of lines per page a flat table offers (WF-IHM-0060, C-351, #1045)."""


def test_a_number_of_lines_per_page_is_one_of_four_and_any_other_is_refused() -> None:
    # Not a bound but four values: the schema says them, the refusal names no parameter (#1045).
    schema = schema_text(API / "components" / "schemas" / "access.yaml", "GridPreferences")
    assert f"enum: [{', '.join(str(each) for each in PAGE_SIZES)}]" in schema
    refused = fixture("preferences_page_size_out_of_range")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    [crossed] = refused["fields"]
    assert designates(f"/grids/{ANY}/page_size", crossed["pointer"])
    assert crossed == {"pointer": crossed["pointer"], "code": "VALUE_OUT_OF_RANGE"}
    said = refusals(operations()["updateMyPreferences"][1])
    assert told(f"/grids/{ANY}/page_size", said)
    assert "preferences_page_size_out_of_range" in said


def test_the_examples_keep_the_lines_per_page_and_the_lanes_of_the_timelines_admitted() -> None:
    # Every example that bears a number of lines per page bears one of the four; every lane of a
    # timeline is a rank from 0, of a task inscribed to that timeline of the witness.
    lane = published()["updateMyPreferences", f"/timelines/{ANY}/lanes/{ANY}"]
    inscribed = {
        timeline: {
            universe(number)
            for number, timelines in mockwitness.INSCRIBED.items()
            if timeline in timelines
        }
        for timeline, _ in mockwitness.TIMELINES
    }
    sizes: list[str] = []
    lanes: list[str] = []
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        for entry in _walk(json.loads(path.read_text(encoding="utf-8"))["value"]):
            if "page_size" in entry:
                assert entry["page_size"] in PAGE_SIZES, path.name
                sizes.append(path.name)
            if not isinstance(entry.get("timelines"), dict):
                # A list of timelines, or of the inscriptions of a task: no layout.
                continue
            for timeline, layout in cast("dict[str, Any]", entry["timelines"]).items():
                placed = cast("dict[str, int]", layout["lanes"])
                assert set(placed) <= inscribed[timeline], path.name
                assert all(rank >= lane["minimum"] for rank in placed.values()), path.name
                lanes.append(path.name)
    assert {"me_grid_settings.json", "preferences_page_size.json"} <= set(sizes)
    assert {"me_grid_settings.json", "preferences_timeline_lanes.json"} <= set(lanes)


CHARTS = {"risk_matrix"}
"""The charts a screen folds, by the name the preferences keep them under (EP-15/US-0550)."""


def test_the_examples_keep_the_state_of_a_chart_by_its_name_folded_or_not() -> None:
    # A chart the screen folds keeps its state by its name, `folded` a boolean, always sent.
    schema = schema_text(API / "components" / "schemas" / "access.yaml", "ChartPreferences")
    assert "required: [folded]" in schema
    kept: list[str] = []
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        for entry in _walk(json.loads(path.read_text(encoding="utf-8"))["value"]):
            for name, chart in cast("dict[str, Any]", entry.get("charts") or {}).items():
                assert name in CHARTS, path.name
                assert isinstance(chart["folded"], bool), path.name
                kept.append(path.name)
    assert {"me_grid_settings.json", "preferences_risk_matrix_unfolded.json"} <= set(kept)


def test_a_value_out_of_range_without_its_bound_is_only_a_number_of_lines_per_page() -> None:
    # `VALUE_OUT_OF_RANGE` names the bound crossed, an admitted value; only an integer that is none
    # of the four numbers of lines per page has none to name (#1045). A bound that excludes its
    # value — zero for a constant of duration — has a motif of its own (EP-14/L42h, L42m).
    unnamed: set[str] = set()
    for path in sorted(mockwitness.FIXTURES.rglob("*.json")):
        for entry in _walk(json.loads(path.read_text(encoding="utf-8"))["value"]):
            out = "pointer" in entry and entry.get("code") == "VALUE_OUT_OF_RANGE"
            if out and not entry.get("params"):
                unnamed.add(path.stem)
    assert unnamed == {"preferences_page_size_out_of_range"}


def test_a_constant_of_duration_at_zero_is_refused_by_its_own_motif() -> None:
    # Strictly positive (WF-PLA-0160): the interval is open, and has no least value to name.
    refused = fixture("duration_units_zero")
    assert (refused["status"], refused["code"]) == (422, "VALIDATION_FAILED")
    [crossed] = refused["fields"]
    assert crossed == {"pointer": "/hours_per_day", "code": "DURATION_UNIT_NOT_POSITIVE"}
    said = refusals(operations()["setDurationUnits"][1])
    assert "par `DURATION_UNIT_NOT_POSITIVE`" in said
    assert "duration_units_zero" in said
