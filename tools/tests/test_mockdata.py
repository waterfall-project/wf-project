# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the volumes the fake back serves, generated at the sizes of §4.6.2."""

import json
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockdata, mockstructure

MONEY = re.compile(r"^\d+\.\d{2}$")
CONTRACT = REPOSITORY / "docs" / "api" / "paths"

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def volumes() -> dict[str, Any]:
    """Generate the volumes once, read back from the text the generator writes."""
    return {
        name: json.loads(mockdata.render(example)) for name, example in mockdata.volumes().items()
    }


def first_example(path: str, operation: str) -> str:
    """Return the line of the first example of an operation, in a file of the contract."""
    text = (CONTRACT / path).read_text(encoding="utf-8")
    rest = text[text.index(f"operationId: {operation}") :]
    return rest[rest.index("examples:") :].splitlines()[1].strip()


def test_every_volume_is_an_example_of_the_contract(volumes: dict[str, Any]) -> None:
    assert sorted(volumes) == [
        "cost_categories.json",
        "estimate_indicators.json",
        "hourly_rates.json",
        "nodes_thousand.json",
        "portfolio_projects.json",
        "summary_dependencies.json",
    ]
    for example in volumes.values():
        assert set(example) == {"summary", "description", "value"}


def test_a_summary_counts_what_its_volume_holds(volumes: dict[str, Any]) -> None:
    nodes = volumes["nodes_thousand.json"]["summary"]
    assert "1 000 tâches" in nodes
    assert "930 tâches de travail et leurs 30 jalons" in nodes
    assert "5 000 lignes de devis" in nodes
    assert "provision de plus sur 350" in nodes
    total = volumes["estimate_indicators.json"]["value"]["total"]
    assert total == "60553621.36"
    assert "60 553 621,36 au total" in volumes["estimate_indicators.json"]["summary"]
    assert "Les 300 projets" in volumes["portfolio_projects.json"]["summary"]
    assert "seuils de 0,9 et 0,8" in volumes["portfolio_projects.json"]["summary"]
    assert "15 ans" in volumes["hourly_rates.json"]["summary"]
    assert "80,00 de l'heure" in volumes["hourly_rates.json"]["summary"]


def test_the_dependencies_of_a_summary_are_its_tasks_not_its_lines() -> None:
    def task(row: int, parent: int | None, label: str, *, summary: bool = False) -> Node:
        return {
            "node_id": f"n{row}",
            "parent_id": None if parent is None else f"n{parent}",
            "row_number": row,
            "kind": "task",
            "task": {"label": label, "is_summary": summary},
        }

    line: Node = {
        "node_id": "n3",
        "parent_id": "n2",
        "row_number": 3,
        "kind": "estimate_line",
        "estimate_line": {"label": "Ligne propre"},
    }
    answer: dict[str, Any] = {
        "items": [
            task(1, None, "Tâche seule"),
            task(2, None, "Phase", summary=True),
            line,
            task(4, 2, "Lot A"),
            task(5, 2, "Lot B"),
        ]
    }
    dependencies = mockdata.summary_dependencies(answer)
    assert dependencies["node_id"] == "n2"
    assert dependencies["rows"] == [
        {"node_id": "n4", "row_number": 4, "label": "Lot A"},
        {"node_id": "n5", "row_number": 5, "label": "Lot B"},
    ]


def test_the_indicators_are_summed_from_the_lines_of_the_grid(volumes: dict[str, Any]) -> None:
    indicators = volumes["estimate_indicators.json"]["value"]
    nodes = volumes["nodes_thousand.json"]["value"]
    lines = [node["estimate_line"] for node in nodes["items"] if node["kind"] == "estimate_line"]
    assert indicators["total"] == nodes["totals"]["budgeted_amount"]
    provisions = sum(Decimal(line["budgeted_amount"]) for line in lines if line["is_computed"])
    assert Decimal(indicators["provisions_identified"]) == provisions
    for name in ("by_cost_type", "by_subproject"):
        parts = indicators[name]
        assert sum(Decimal(part["amount"]) for part in parts) == Decimal(indicators["total"])
        assert sum(Decimal(part["share"]) for part in parts) == 1
    unassigned = sum(
        (Decimal(line["budgeted_amount"]) for line in lines if not line["subproject_id"]),
        Decimal(0),
    )
    assert indicators["by_subproject"][-1] == {
        "key": "unassigned",
        "amount": mockstructure.money(unassigned),
        "share": indicators["by_subproject"][-1]["share"],
    }


def test_the_indicators_keep_the_context_and_labels_of_the_universe(
    volumes: dict[str, Any],
) -> None:
    indicators = volumes["estimate_indicators.json"]["value"]
    witness = mockdata.fixture("estimate_indicators")
    assert indicators["context"] == witness["context"]
    assert indicators["delta_to_previous_revision"] == witness["delta_to_previous_revision"]
    natures = mockdata.fixture("estimate_indicators_breakdown")["by_cost_type"]
    assert [(part["key"], part["label"]) for part in indicators["by_cost_type"]] == [
        (part["key"], part["label"]) for part in natures
    ]
    subprojects = [
        (entry["subproject_id"], entry["label"]) for entry in mockdata.fixture("subprojects")
    ]
    assert [(part["key"], part.get("label")) for part in indicators["by_subproject"]] == [
        *subprojects,
        ("unassigned", None),
    ]


def test_the_portfolio_holds_three_hundred_projects(volumes: dict[str, Any]) -> None:
    value = volumes["portfolio_projects.json"]["value"]
    rows = value["items"]
    assert len(rows) == 300
    assert value["scope"]["project_count"] == value["meta"]["total"] == 300
    assert value["meta"]["limit"] >= 300
    assert len({row["project_id"] for row in rows}) == 300
    assert len({row["code"] for row in rows}) == 300
    assert len({row["label"] for row in rows}) == 300
    assert {row["state"] for row in rows} == set(value["scope"]["states"])


def test_no_project_takes_the_subject_and_object_of_the_witness_or_the_offer(
    volumes: dict[str, Any],
) -> None:
    rows = volumes["portfolio_projects.json"]["value"]["items"]
    for label in (rows[0]["label"], rows[1]["label"]):
        assert [row["label"] for row in rows if row["label"].startswith(label)] == [label]


def test_the_witness_and_the_offer_are_those_of_their_examples(volumes: dict[str, Any]) -> None:
    witness, offer = volumes["portfolio_projects.json"]["value"]["items"][:2]
    project = mockdata.fixture("project")
    indicators = mockdata.fixture("project_indicators")
    for field in ("project_id", "label", "code", "state", "win_probability"):
        assert witness[field] == project[field]
    assert witness["reference_budget"] == indicators["reference_budget"]
    assert witness["project_manager_projection"] == indicators["projections"]["project_manager"]
    assert witness["cost_index"] == indicators["cost_index"]
    assert witness["schedule_index"] == indicators["schedule_index"]
    assert witness["last_marked_at"] == "2026-02-01T09:00:00Z"
    pricing = mockdata.fixture("project_pricing")
    for field in ("project_id", "label", "code", "state", "win_probability"):
        assert offer[field] == pricing[field]
    assert offer["reference_budget"] is None
    assert offer["last_marked_at"] is None


def test_an_offer_shows_its_estimate_and_a_project_in_progress_its_budget(
    volumes: dict[str, Any],
) -> None:
    for row in volumes["portfolio_projects.json"]["value"]["items"][2:]:
        if row["state"] == "pricing":
            assert row["reference_budget"] is None
            assert MONEY.match(row["current_estimate"])
            assert row["cost_index"] is None
        else:
            assert row["current_estimate"] is None
            assert MONEY.match(row["reference_budget"])
            assert row["last_marked_at"].endswith("Z")


@pytest.mark.parametrize(
    ("index", "zone"),
    [("1", "nominal"), ("0.9", "nominal"), ("0.89", "watch"), ("0.8", "watch"), ("0.5", "alert")],
)
def test_an_index_is_zoned_by_the_thresholds_of_the_reference(index: str, zone: str) -> None:
    assert mockdata.zone(Decimal(index)) == zone


def test_the_zone_of_each_index_is_the_one_its_value_takes(volumes: dict[str, Any]) -> None:
    indexes = [
        row[name]
        for row in volumes["portfolio_projects.json"]["value"]["items"]
        for name in ("cost_index", "schedule_index")
        if row[name] is not None and row[name]["value"]["is_computable"]
    ]
    assert len(indexes) > 500
    assert all(
        index["zone"] == mockdata.zone(Decimal(index["value"]["value"])) for index in indexes
    )
    assert {index["zone"] for index in indexes} == {"nominal", "watch", "alert"}


def test_the_rate_is_the_one_the_witness_estimate_reads() -> None:
    lines = [
        node["estimate_line"]
        for node in mockdata.fixture("nodes_estimate")["items"]
        if node["kind"] == "estimate_line"
        and node["estimate_line"]["cost_category_id"] == mockstructure.ELECTRICAL_ENGINEERING
    ]
    assert lines
    for line in lines:
        rate = Decimal(line["budgeted_amount"]) / Decimal(line["hours"])
        assert rate == mockstructure.ELECTRICAL_RATE


def test_the_rates_span_fifteen_years_up_to_the_reference_year(volumes: dict[str, Any]) -> None:
    rates = volumes["hourly_rates.json"]["value"]
    assert [rate["year"] for rate in rates] == list(range(2012, 2027))
    assert {rate["cost_category_id"] for rate in rates} == {mockstructure.ELECTRICAL_ENGINEERING}
    assert rates[-1]["amount"] == mockstructure.money(mockstructure.ELECTRICAL_RATE)
    assert rates[0]["amount"] == "59.00"
    assert all(MONEY.match(rate["amount"]) for rate in rates)


def test_two_hundred_categories_a_hundred_and_fifty_of_them_labour(
    volumes: dict[str, Any],
) -> None:
    categories = volumes["cost_categories.json"]["value"]
    assert len(categories) == 200
    kinds = Counter(category["cost_type_id"] for category in categories)
    assert kinds == {
        mockstructure.LABOR: 150,
        mockstructure.NON_LABOR: 49,
        mockstructure.PROVISION: 1,
    }
    for field in ("cost_category_id", "code", "accounting_code", "label"):
        assert len({category[field] for category in categories}) == 200
    labels = {category["cost_category_id"]: category["label"] for category in categories}
    for missing in mockdata.fixture("missing_rates"):
        assert labels[missing["cost_category_id"]] == missing["label"]
    used = {kind.category for kind in mockstructure.LINE_KINDS}
    assert used <= labels.keys()


def test_two_runs_write_the_same_bytes() -> None:
    first = {name: mockdata.render(example) for name, example in mockdata.volumes().items()}
    second = {name: mockdata.render(example) for name, example in mockdata.volumes().items()}
    assert first == second


def test_an_example_is_written_one_line_per_item() -> None:
    text = mockdata.render(
        {"summary": "s", "value": {"items": [{"a": 1}, {"a": 2}], "meta": {"total": 2}}}
    )
    assert text == (
        '{\n  "summary": "s",\n  "value": {\n    "items": [\n'
        '      {"a":1},\n      {"a":2}\n    ],\n    "meta": {"total":2}\n  }\n}\n'
    )


def test_the_written_volumes_check_up_to_date(tmp_path: Path) -> None:
    assert mockdata.main([], tmp_path) == 0
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(mockdata.volumes())
    assert mockdata.main(["--check"], tmp_path) == 0


def test_an_outdated_missing_or_left_over_volume_fails_the_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mockdata.write(tmp_path)
    (tmp_path / "hourly_rates.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "cost_categories.json").unlink()
    (tmp_path / "old.json").write_text("{}\n", encoding="utf-8")
    assert mockdata.check(tmp_path) == [
        "old.json is left over",
        "cost_categories.json is missing",
        "hourly_rates.json is outdated",
    ]
    assert mockdata.main(["--check"], tmp_path) == 1
    assert "run make mock-data" in capsys.readouterr().err


def test_any_entry_left_over_or_unreadable_fails_the_check(tmp_path: Path) -> None:
    mockdata.write(tmp_path)
    (tmp_path / "old.txt").write_text("notes\n", encoding="utf-8")
    (tmp_path / "archive").mkdir()
    (tmp_path / "hourly_rates.json").write_bytes(b"\xff\xfe not utf-8")
    (tmp_path / "cost_categories.json").unlink()
    (tmp_path / "cost_categories.json").mkdir()
    assert mockdata.check(tmp_path) == [
        "archive is a directory left over, remove it by hand",
        "old.txt is left over",
        "cost_categories.json is outdated",
        "hourly_rates.json is outdated",
    ]


def test_writing_removes_a_file_the_generator_no_longer_makes(tmp_path: Path) -> None:
    (tmp_path / "old.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "archive").mkdir()
    mockdata.write(tmp_path)
    assert not (tmp_path / "old.json").exists()
    assert mockdata.check(tmp_path) == ["archive is a directory left over, remove it by hand"]
    assert mockdata.check(tmp_path / "absent") == [
        f"{name} is missing" for name in mockdata.volumes()
    ]


def test_a_directory_left_over_is_not_sent_to_make_mock_data(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mockdata.write(tmp_path)
    (tmp_path / "archive").mkdir()
    assert mockdata.main(["--check"], tmp_path) == 1
    err = capsys.readouterr().err
    assert "archive is a directory left over, remove it by hand" in err
    assert "run make mock-data" not in err


def test_the_volumes_are_written_with_plain_line_ends_whatever_was_there(tmp_path: Path) -> None:
    for name, example in mockdata.volumes().items():
        (tmp_path / name).write_bytes(mockdata.render(example).replace("\n", "\r\n").encode())
    assert mockdata.check(tmp_path) != []
    mockdata.write(tmp_path)
    assert mockdata.check(tmp_path) == []
    assert all(b"\r\n" not in path.read_bytes() for path in tmp_path.iterdir())


def test_the_contract_cites_every_volume_so_that_its_lint_checks_it() -> None:
    contract = "".join(path.read_text(encoding="utf-8") for path in CONTRACT.glob("*.yaml"))
    for name in mockdata.volumes():
        assert f"$ref: ../../../fixtures/api/volume/{name} }}" in contract


def test_the_fake_back_serves_the_volumes_first() -> None:
    assert first_example("revisions.yaml", "listNodes") == (
        "volume: { $ref: ../../../fixtures/api/volume/nodes_thousand.json }"
    )
    assert first_example("analysis.yaml", "getEstimateIndicators") == (
        "volume: { $ref: ../../../fixtures/api/volume/estimate_indicators.json }"
    )
    assert first_example("revisions.yaml", "getComputedValueDependencies") == (
        "volume: { $ref: ../../../fixtures/api/volume/summary_dependencies.json }"
    )


def test_a_fixture_is_read_by_its_value() -> None:
    project = cast("dict[str, Any]", mockdata.fixture("project"))
    assert project["project_id"] == "01926f3a-7c00-7000-8000-000000000001"
