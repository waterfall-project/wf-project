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
        "hourly_rate_grid.json",
        "hourly_rates.json",
        "nodes_thousand.json",
        "portfolio_cost_structure.json",
        "portfolio_performance.json",
        "portfolio_projects.json",
        "portfolio_risks.json",
        "portfolio_value.json",
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
    assert total == mockstructure.computable("60553621.36")
    assert "60 553 621,36 au total" in volumes["estimate_indicators.json"]["summary"]
    assert "Les 300 projets" in volumes["portfolio_projects.json"]["summary"]
    assert "seuils de 0,9 et 0,8" in volumes["portfolio_projects.json"]["summary"]
    assert "15 ans" in volumes["hourly_rates.json"]["summary"]
    assert "80,00 de l'heure" in volumes["hourly_rates.json"]["summary"]
    assert "150 catégories de main-d'œuvre en lignes" in volumes["hourly_rate_grid.json"]["summary"]


def test_the_dependencies_written_are_those_of_the_structure_written(
    volumes: dict[str, Any],
) -> None:
    assert volumes["summary_dependencies.json"]["value"] == mockdata.summary_dependencies(
        volumes["nodes_thousand.json"]["value"]
    )


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
    # Every rate of the universe is set: every amount is computable (WF-DEV-0010).
    total = indicators["total"]
    assert total == mockstructure.computable(nodes["totals"]["budgeted_amount"])
    provisions = sum(Decimal(line["budgeted_amount"]) for line in lines if line["is_computed"])
    assert Decimal(indicators["provisions_identified"]) == provisions
    for name in ("by_cost_type", "by_subproject"):
        parts = indicators[name]
        assert all(part["amount"]["is_computable"] for part in parts)
        assert sum(Decimal(part["amount"]["value"]) for part in parts) == Decimal(total["value"])
        assert sum(Decimal(part["share"]["value"]) for part in parts) == 1
    assert indicators["by_order_item"] is None
    unassigned = sum(
        (Decimal(line["budgeted_amount"]) for line in lines if not line["subproject_id"]),
        Decimal(0),
    )
    assert indicators["by_subproject"][-1] == {
        "key": "unassigned",
        "amount": mockstructure.computable(mockstructure.money(unassigned)),
        "share": indicators["by_subproject"][-1]["share"],
    }


def test_the_indicators_keep_the_context_and_labels_of_the_universe(
    volumes: dict[str, Any],
) -> None:
    indicators = volumes["estimate_indicators.json"]["value"]
    witness = mockdata.fixture("estimate_indicators")
    assert indicators["context"] == witness["context"]
    assert indicators["delta_to_reference"] == witness["delta_to_reference"]
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


def rows_of(volumes: dict[str, Any], state: str) -> list[dict[str, Any]]:
    """Return the rows of the list of the portfolio in a state."""
    rows = volumes["portfolio_projects.json"]["value"]["items"]
    return [row for row in rows if row["state"] == state]


def total(amounts: Any) -> Decimal:
    """Return the sum of amounts written as the contract writes them."""
    return sum((Decimal(amount) for amount in amounts), Decimal(0))


def test_the_value_sums_the_rows_of_the_list(volumes: dict[str, Any]) -> None:
    value = volumes["portfolio_value.json"]["value"]
    offers = [row for row in rows_of(volumes, "pricing") if row["current_estimate"] is not None]
    assert value["scope"]["project_count"] == 300
    assert Decimal(value["order_book"]) == total(
        row["reference_budget"] for row in rows_of(volumes, "in_progress")
    )
    assert Decimal(value["pipeline_gross"]) == total(row["current_estimate"] for row in offers)
    weighted = total(
        Decimal(row["current_estimate"]) * Decimal(row["win_probability"]) for row in offers
    )
    assert Decimal(value["pipeline_weighted"]) == weighted
    assert value["delivered"] == "0.00"
    assert value["conversion_rate"]["value"] == "0.4"


def test_the_performance_is_a_ratio_of_sums_and_counts_each_project_once(
    volumes: dict[str, Any],
) -> None:
    performance = volumes["portfolio_performance.json"]["value"]
    progressing = rows_of(volumes, "in_progress")
    sums = [mockdata.earned(row) for row in progressing]
    value, actual = total(e.earned for e in sums), total(e.actual for e in sums)
    cost = performance["cost_index"]
    assert Decimal(cost["value"]["value"]) == (value / actual).quantize(Decimal("0.01"))
    assert cost["zone"] == mockdata.zone(Decimal(cost["value"]["value"]))
    assert performance["reference_budget"] == volumes["portfolio_value.json"]["value"]["order_book"]
    assert performance["scope"]["project_count"] == len(progressing)
    for index in ("cost", "schedule"):
        counted = Counter(
            row[f"{index}_index"]["zone"] for row in progressing if row[f"{index}_index"]["zone"]
        )
        assert {
            entry["zone"]: entry["project_count"]
            for entry in performance["zone_distribution"]
            if entry["index"] == index
        } == {zone: counted[zone] for zone in ("nominal", "watch", "alert")}
    assert performance["quarterly"][-1]["cost_index"]["value"] == cost["value"]["value"]


def test_the_parts_of_the_cost_structure_sum_to_their_totals(volumes: dict[str, Any]) -> None:
    structure = volumes["portfolio_cost_structure.json"]["value"]
    budget = Decimal(volumes["portfolio_performance.json"]["value"]["reference_budget"])
    assert total(part["amount"] for part in structure["budget_by_cost_type"]) == budget
    for parts in ("budget_by_cost_type", "remaining_by_cost_type"):
        assert total(part["share"] for part in structure[parts]) == 1
    labor = structure["budget_by_cost_type"][0]
    assert labor["label"] == "Main-d'œuvre"
    nodes = {node["org_node_id"]: node["label"] for node in mockdata.fixture("org_nodes")}
    assert all(nodes[part["key"]] == part["label"] for part in structure["labor_by_org_node"])
    assert total(part["amount"] for part in structure["labor_by_org_node"]) == Decimal(
        labor["amount"]
    )


def test_the_heaviest_risks_are_those_of_projects_of_the_list(volumes: dict[str, Any]) -> None:
    risks = volumes["portfolio_risks.json"]["value"]
    labels = {row["project_id"]: row["label"] for row in rows_of(volumes, "in_progress")}
    heaviest = risks["heaviest"]
    assert len(heaviest) == 10
    assert all(labels[risk["project_id"]] == risk["project_label"] for risk in heaviest)
    amounts = [Decimal(risk["provision_amount"]) for risk in heaviest]
    assert amounts == sorted(amounts, reverse=True)
    totals = risks["matrix"]["totals"]
    assert totals["identified"] == risks["identified_total"]
    assert totals["occurred"] == risks["period_outcome"]["occurred_provisions"]
    assert Decimal(totals["total"]) == total(
        totals[name] for name in ("identified", "occurred", "dismissed")
    )
    assert len(risks["matrix"]["cells"]) == 16


@pytest.mark.parametrize("name", ["portfolio_workload", "portfolio_cash_out"])
def test_a_view_written_by_hand_reads_the_portfolio_of_the_list(
    volumes: dict[str, Any], name: str
) -> None:
    scope = mockdata.fixture(name)["scope"]
    assert scope["as_of"] == mockstructure.AS_OF.isoformat()
    assert scope["states"] == ["in_progress"]
    assert scope["project_count"] == len(rows_of(volumes, "in_progress"))


def test_the_roles_of_the_workload_are_those_of_the_universe() -> None:
    roles = {role["resource_role_id"]: role for role in mockdata.fixture("resource_roles")}
    for role in mockdata.fixture("portfolio_workload")["roles"]:
        known = roles[role["resource_role_id"]]
        assert role["label"] == known["label"]
        capacity = Decimal(known["capacity"]["monthly_hours"]) * Decimal(
            known["capacity"]["headcount"]
        )
        assert Decimal(role["capacity_monthly_hours"]) == capacity
        for month in role["months"]:
            assert Decimal(month["hours"]) == capacity * Decimal(month["load_ratio"]["value"])


def test_the_marks_the_portfolio_journey_reads(volumes: dict[str, Any]) -> None:
    # The end-to-end path of the portfolio (portfolio.spec.ts) reads the list, the witness
    # project in alert by its schedule index, and the performance by these figures: a change of
    # the generator that moves them fails here.
    value = volumes["portfolio_projects.json"]["value"]
    assert value["meta"]["total"] == 300
    witness = value["items"][0]
    assert witness["label"] == "Modernisation du poste de commande"
    assert witness["schedule_index"]["zone"] == "alert"
    performance = volumes["portfolio_performance.json"]["value"]
    assert performance["cost_index"]["value"]["value"] == "0.94"
    assert performance["zone_distribution"][2] == {
        "index": "cost",
        "zone": "alert",
        "project_count": 53,
    }


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


def test_the_grid_of_rates_has_the_labour_categories_in_rows_and_the_years_in_columns(
    volumes: dict[str, Any],
) -> None:
    grid = volumes["hourly_rate_grid.json"]["value"]
    assert grid["years"] == list(range(2012, 2027))
    rows = grid["rows"]
    assert len(rows) == 150
    labour = [
        category
        for category in volumes["cost_categories.json"]["value"]
        if category["cost_type_id"] == mockstructure.LABOR
    ]
    assert [row["cost_category_id"] for row in rows] == [c["cost_category_id"] for c in labour]
    assert [(row["code"], row["label"]) for row in rows] == [
        (c["code"], c["label"]) for c in labour
    ]
    for row in rows:
        assert len(row["cells"]) == 15
        for year, cell in zip(grid["years"], row["cells"], strict=True):
            if cell is not None:
                assert (cell["cost_category_id"], cell["year"]) == (row["cost_category_id"], year)
                assert MONEY.match(cell["amount"])


def test_the_grid_of_rates_agrees_with_the_rates_of_one_category_and_leaves_cells_empty(
    volumes: dict[str, Any],
) -> None:
    grid = volumes["hourly_rate_grid.json"]["value"]
    electrical = next(
        row
        for row in grid["rows"]
        if row["cost_category_id"] == mockstructure.ELECTRICAL_ENGINEERING
    )
    assert electrical["cells"] == volumes["hourly_rates.json"]["value"]
    commissioning = next(
        row for row in grid["rows"] if row["cost_category_id"] == mockstructure.COMMISSIONING
    )
    assert commissioning["cells"][-1]["amount"] == "75.00"
    assert all(cell is not None for cell in commissioning["cells"])
    # A category without a rate for its first years has empty cells there, never a column less.
    empties = [sum(cell is None for cell in row["cells"]) for row in grid["rows"]]
    assert max(empties) <= 4
    assert any(empties)
    for row in grid["rows"]:
        filled = [cell is not None for cell in row["cells"]]
        assert filled == sorted(filled)
        assert filled[-1]


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
    # Each category names its nature as the natures of the universe do (WF-ARC-0020).
    natures = {nature["cost_type_id"]: nature["label"] for nature in mockdata.fixture("cost_types")}
    assert all(
        category["cost_type_label"] == natures[category["cost_type_id"]] for category in categories
    )


def test_the_marks_the_reference_journeys_read(volumes: dict[str, Any]) -> None:
    # The journey of the reference data (reference.spec.ts), the tests of the grid of the rates
    # (rate-grid.dom.test.tsx) and the two examples of setHourlyRate read the third row of the
    # grid: a change of the generator that moves it fails here.
    grid = volumes["hourly_rate_grid.json"]["value"]
    mechanical = grid["rows"][2]
    assert mechanical["code"] == "MO-003"
    assert mechanical["label"] == "Ingénierie mécanique — niveau 1"
    years = grid["years"]
    rates = dict(zip(years, mechanical["cells"], strict=True))
    assert all(rates[year] is None for year in range(2012, 2016))
    assert (rates[2016]["amount"], rates[2016]["lock_version"]) == ("86.98", 1)
    assert grid["rows"][0]["cells"][-1]["amount"] == "80.00"
    for name, year in (("hourly_rate_entered", 2015), ("hourly_rate_corrected", 2016)):
        written = mockdata.fixture(name)
        assert (written["cost_category_id"], written["year"]) == (
            mechanical["cost_category_id"],
            year,
        )
    assert mockdata.fixture("hourly_rate_corrected")["lock_version"] == 2


def test_the_missing_rates_are_those_the_estimate_indicators_name() -> None:
    # The same estimate, the same rates missing: the list and the amount that cannot be
    # calculated name the same categories, for the same year (#205).
    indicators = mockdata.fixture("estimate_indicators_missing_rates")
    assert mockdata.fixture("missing_rates") == indicators["total"]["params"]["missing_rates"]


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
    assert first_example("reference.yaml", "getHourlyRateGrid") == (
        "volume: { $ref: ../../../fixtures/api/volume/hourly_rate_grid.json }"
    )
    for operation, name in [
        ("getPortfolioProjects", "portfolio_projects"),
        ("getPortfolioValue", "portfolio_value"),
        ("getPortfolioPerformance", "portfolio_performance"),
    ]:
        assert first_example("portfolio.yaml", operation) == (
            f"volume: {{ $ref: ../../../fixtures/api/volume/{name}.json }}"
        )


def test_a_fixture_is_read_by_its_value() -> None:
    project = cast("dict[str, Any]", mockdata.fixture("project"))
    assert project["project_id"] == "01926f3a-7c00-7000-8000-000000000001"
