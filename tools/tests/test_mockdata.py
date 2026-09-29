# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the volumes the fake back serves, generated at the sizes of §4.6.2."""

import json
import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockdata

MONEY = re.compile(r"^\d+\.\d{2}$")
CONTRACT = REPOSITORY / "docs" / "api" / "paths"

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def volumes() -> dict[str, Any]:
    """Generate the volumes once, read back from the text the generator writes."""
    return {
        name: json.loads(mockdata.render(example)) for name, example in mockdata.volumes().items()
    }


@pytest.fixture(scope="module")
def items(volumes: dict[str, Any]) -> list[Node]:
    """Read the nodes of the structure of a thousand tasks."""
    return cast("list[Node]", volumes["nodes_thousand.json"]["value"]["items"])


def tasks(items: list[Node]) -> list[Node]:
    return [node for node in items if node["kind"] == "task"]


def lines(items: list[Node]) -> list[Node]:
    return [node for node in items if node["kind"] == "estimate_line"]


def by_id(items: list[Node]) -> dict[str, Node]:
    return {node["node_id"]: node for node in items}


def children(items: list[Node], parent: Node) -> list[Node]:
    return [node for node in items if node["parent_id"] == parent["node_id"]]


def working_days(first: str, last: str) -> int:
    """Count the working days from one date to another, both included."""
    start, end = date.fromisoformat(first), date.fromisoformat(last)
    days = (start + timedelta(days=n) for n in range((end - start).days + 1))
    return sum(1 for day in days if day.weekday() < 5)


def test_every_volume_is_an_example_of_the_contract(volumes: dict[str, Any]) -> None:
    assert sorted(volumes) == [
        "cost_categories.json",
        "hourly_rates.json",
        "nodes_thousand.json",
        "portfolio_projects.json",
    ]
    for example in volumes.values():
        assert set(example) == {"summary", "description", "value"}


def test_a_thousand_tasks_carry_five_thousand_lines(volumes: dict[str, Any]) -> None:
    value = volumes["nodes_thousand.json"]["value"]
    assert len(tasks(value["items"])) == 1_000
    assert len(lines(value["items"])) == 5_000
    assert value["totals"]["task_count"] == 1_000
    assert value["totals"]["estimate_line_count"] == 5_000


def test_the_work_tasks_carry_five_lines_and_some_a_provision(items: list[Node]) -> None:
    work = [
        node
        for node in tasks(items)
        if not node["task"]["is_summary"] and not node["task"]["is_milestone"]
    ]
    counts = Counter(len(children(items, node)) for node in work[:60])
    assert set(counts) == {5, 6}
    for node in tasks(items):
        if node["task"]["is_summary"] or node["task"]["is_milestone"]:
            assert all(child["kind"] == "task" for child in children(items, node))


def test_the_tree_is_read_depth_first(items: list[Node]) -> None:
    assert [node["row_number"] for node in items] == list(range(1, 6_001))
    assert len({node["node_id"] for node in items}) == 6_000
    assert len({node["lineage_id"] for node in items}) == 6_000
    ancestors: list[Node] = []
    for node in items:
        del ancestors[node["level"] - 1 :]
        parent = ancestors[-1]["node_id"] if ancestors else None
        assert node["parent_id"] == parent
        ancestors.append(node)


def test_positions_count_the_siblings_of_one_parent(items: list[Node]) -> None:
    siblings: dict[str | None, list[int]] = {}
    for node in items:
        siblings.setdefault(node["parent_id"], []).append(node["position"])
    assert all(positions == list(range(len(positions))) for positions in siblings.values())


def test_a_line_amount_is_exact(items: list[Node]) -> None:
    rates = {line.category: line.rate for line in mockdata.LINE_KINDS if line.rate}
    for node in lines(items):
        line = node["estimate_line"]
        assert MONEY.match(line["budgeted_amount"])
        assert line["budgeted_amount"] == line["reestimated_amount"]
        if line["hours"] is None:
            expected = Decimal(line["quantity"]) * Decimal(line["unit_disbursement"])
        else:
            assert line["resource_role_id"] is not None
            expected = Decimal(line["hours"]) * rates[line["cost_category_id"]]
        assert Decimal(line["budgeted_amount"]) == expected


def test_a_task_sums_the_lines_under_it_and_the_totals_all_of_them(
    volumes: dict[str, Any], items: list[Node]
) -> None:
    nodes = by_id(items)
    sums: dict[str, Decimal] = dict.fromkeys(nodes, Decimal(0))
    for node in lines(items):
        amount = Decimal(node["estimate_line"]["budgeted_amount"])
        parent = node["parent_id"]
        while parent is not None:
            sums[parent] += amount
            parent = nodes[parent]["parent_id"]
    for node in tasks(items):
        assert Decimal(node["task"]["budgeted_amount"]) == sums[node["node_id"]]
    totals = volumes["nodes_thousand.json"]["value"]["totals"]
    amounts = [Decimal(node["estimate_line"]["budgeted_amount"]) for node in lines(items)]
    hours = [Decimal(node["estimate_line"]["hours"] or 0) for node in lines(items)]
    assert Decimal(totals["budgeted_amount"]) == sum(amounts)
    assert Decimal(totals["reestimated_amount"]) == sum(amounts)
    assert Decimal(totals["hours"]) == sum(hours)


def test_a_task_lasts_its_duration_in_working_days(items: list[Node]) -> None:
    for node in tasks(items):
        task = node["task"]
        assert date.fromisoformat(task["start_date"]).weekday() < 5
        assert date.fromisoformat(task["finish_date"]).weekday() < 5
        if task["is_milestone"]:
            assert task["duration_days"] == 0
            assert task["start_date"] == task["finish_date"]
        else:
            assert working_days(task["start_date"], task["finish_date"]) == task["duration_days"]


def test_a_task_starts_after_its_predecessors_finish(items: list[Node]) -> None:
    nodes = by_id(items)
    for node in tasks(items):
        finishes = [
            nodes[link["predecessor_node_id"]]["task"]["finish_date"]
            for link in node.get("predecessors", [])
        ]
        if not finishes:
            continue
        task = node["task"]
        if task["is_milestone"]:
            assert task["start_date"] == max(finishes)
        else:
            assert working_days(max(finishes), task["start_date"]) == 2


def test_a_summary_spans_its_subordinates(items: list[Node]) -> None:
    for node in tasks(items):
        task = node["task"]
        if not task["is_summary"]:
            continue
        below = [child["task"] for child in children(items, node)]
        assert task["start_date"] == min(child["start_date"] for child in below)
        assert task["finish_date"] == max(child["finish_date"] for child in below)
        assert "task.duration_days" in node["computed_fields"]
        assert "total_float_days" not in task


def test_the_critical_path_runs_to_the_last_finish(items: list[Node]) -> None:
    work = [node["task"] for node in tasks(items) if not node["task"]["is_summary"]]
    last = max(task["finish_date"] for task in work)
    assert all(task["total_float_days"] >= 0 for task in work)
    assert all(task["is_critical"] == (task["total_float_days"] == 0) for task in work)
    assert all(task["is_critical"] for task in work if task["finish_date"] == last)
    assert 0 < sum(task["is_critical"] for task in work) < len(work)


def test_progress_is_that_of_the_day_the_examples_are_read(items: list[Node]) -> None:
    today = mockdata.AS_OF.isoformat()
    nodes = by_id(items)
    for node in tasks(items):
        task = node["task"]
        if task["is_summary"]:
            continue
        if task["progress"] == "completed":
            assert task["finish_date"] < today
            assert task["completed_on"] == task["finish_date"]
        elif task["progress"] == "started":
            assert task["start_date"] <= today <= task["finish_date"]
        else:
            assert today < task["start_date"] or task["is_milestone"]
    states = Counter(node["task"]["progress"] for node in tasks(items))
    assert set(states) == {"completed", "started", "not_started"}
    for node in lines(items):
        completed = nodes[node["parent_id"]]["task"]["progress"] == "completed"
        entry = node["estimate_line"]["remaining_entry"]
        assert entry["is_available"] is not completed
        assert entry["missing_conditions"] == (["task_not_completed"] if completed else [])


def test_a_provision_is_computed_and_outside_the_subprojects(items: list[Node]) -> None:
    provisions = [node for node in lines(items) if node["estimate_line"]["is_computed"]]
    assert len(provisions) == 350
    for node in provisions:
        assert node["estimate_line"]["cost_category_id"] == mockdata.PROVISIONS
        assert node["estimate_line"]["subproject_id"] is None
        assert node["computed_fields"] == [
            "estimate_line.quantity",
            "estimate_line.unit_disbursement",
        ]


def test_the_structure_stays_in_the_universe_of_the_examples(items: list[Node]) -> None:
    fixtures = REPOSITORY / "fixtures" / "api"
    known = (fixtures / "subprojects.json").read_text(encoding="utf-8")
    subprojects = {node["estimate_line"]["subproject_id"] for node in lines(items)} - {None}
    assert subprojects == {mockdata.SUBPROJECT_CONTROL, mockdata.SUBPROJECT_TESTS}
    assert all(subproject in known for subproject in subprojects)
    assert items[0]["task"]["label"] == "Études"


def test_the_portfolio_holds_three_hundred_projects(volumes: dict[str, Any]) -> None:
    value = volumes["portfolio_projects.json"]["value"]
    rows = value["items"]
    assert len(rows) == 300
    assert value["scope"]["project_count"] == value["meta"]["total"] == 300
    assert value["meta"]["limit"] >= 300
    assert len({row["project_id"] for row in rows}) == 300
    assert len({row["code"] for row in rows}) == 300
    assert [row["project_id"] for row in rows[:2]] == [mockdata.PROJECT, mockdata.OFFER]
    assert {row["state"] for row in rows} == set(value["scope"]["states"])


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


def test_the_rates_span_fifteen_years_up_to_the_reference_year(volumes: dict[str, Any]) -> None:
    rates = volumes["hourly_rates.json"]["value"]
    assert [rate["year"] for rate in rates] == list(range(2012, 2027))
    assert {rate["cost_category_id"] for rate in rates} == {mockdata.ELECTRICAL_ENGINEERING}
    # 12.5 hours for 1,000.00 in the witness estimate: 80.00 an hour in 2026.
    assert rates[-1]["amount"] == "80.00"
    assert all(MONEY.match(rate["amount"]) for rate in rates)


def test_two_hundred_categories_a_hundred_and_fifty_of_them_labour(
    volumes: dict[str, Any],
) -> None:
    categories = volumes["cost_categories.json"]["value"]
    assert len(categories) == 200
    kinds = Counter(category["cost_type_id"] for category in categories)
    assert kinds == {mockdata.LABOR: 150, mockdata.NON_LABOR: 49, mockdata.PROVISION: 1}
    for field in ("cost_category_id", "code", "accounting_code", "label"):
        assert len({category[field] for category in categories}) == 200
    labels = {category["cost_category_id"]: category["label"] for category in categories}
    # The labels the examples of missing rates give.
    assert labels[mockdata.ELECTRICAL_ENGINEERING] == "Ingénierie électrique"
    assert labels[mockdata.COMMISSIONING] == "Mise en service"
    used = {kind.category for kind in mockdata.LINE_KINDS}
    assert used <= labels.keys()


def test_two_runs_write_the_same_bytes() -> None:
    first = {name: mockdata.render(example) for name, example in mockdata.volumes().items()}
    second = {name: mockdata.render(example) for name, example in mockdata.volumes().items()}
    assert first == second


def test_a_drawn_value_depends_on_its_key_alone() -> None:
    assert mockdata.draw("duration/1.1.1", 3, 12) == mockdata.draw("duration/1.1.1", 3, 12)
    values = {mockdata.draw(f"duration/{n}", 3, 12) for n in range(200)}
    assert values == set(range(3, 13))


def test_an_example_is_written_one_line_per_item() -> None:
    text = mockdata.render(
        {"summary": "s", "value": {"items": [{"a": 1}, {"a": 2}], "meta": {"total": 2}}}
    )
    assert text == (
        '{\n  "summary": "s",\n  "value": {\n    "items": [\n'
        '      {"a":1},\n      {"a":2}\n    ],\n    "meta": {"total":2}\n  }\n}\n'
    )


def test_exact_decimals_are_written_as_the_contract_carries_them() -> None:
    assert mockdata.money(Decimal(1000)) == "1000.00"
    assert mockdata.decimal(Decimal("12.50")) == "12.5"
    assert mockdata.decimal(Decimal(40)) == "40"
    assert mockdata.working_day(5) == date(2026, 3, 9)
    assert mockdata.working_offset(date(2026, 3, 16)) == 10


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


def test_writing_removes_a_volume_the_generator_no_longer_makes(tmp_path: Path) -> None:
    (tmp_path / "old.json").write_text("{}\n", encoding="utf-8")
    mockdata.write(tmp_path)
    assert not (tmp_path / "old.json").exists()
    assert mockdata.check(tmp_path / "absent") == [
        f"{name} is missing" for name in mockdata.volumes()
    ]


def test_the_contract_cites_every_volume_so_that_its_lint_checks_it() -> None:
    contract = "".join(path.read_text(encoding="utf-8") for path in CONTRACT.glob("*.yaml"))
    for name in mockdata.volumes():
        assert f"$ref: ../../../fixtures/api/volume/{name} }}" in contract


def test_the_fake_back_serves_the_thousand_tasks_first() -> None:
    text = (CONTRACT / "revisions.yaml").read_text(encoding="utf-8")
    operation = text[text.index("operationId: listNodes") :]
    examples = operation[operation.index("examples:") :].splitlines()
    assert (
        examples[1].strip() == "volume: { $ref: ../../../fixtures/api/volume/nodes_thousand.json }"
    )
