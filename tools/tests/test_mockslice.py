# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the portfolio of the witness and the readings of its eight views (US-2770/L1)."""

import ast
import json
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from functools import cache
from typing import TYPE_CHECKING, Any, cast

import pytest

from wftools import REPOSITORY, mockids, mockslice, mocksliceviews
from wftools.mockslice import (
    ABANDONED,
    COMPLETED,
    IN_PROGRESS,
    LOST,
    PRICING,
    SLICE,
    Revision,
)
from wftools.mockslicereadings import AS_OF, PERIOD_FROM, member, members
from wftools.mocksliceviews import Portfolio

if TYPE_CHECKING:
    from pathlib import Path

REQUIREMENT = "WF-QUA-0040-A"
GENERATORS = ("mockslice", "mockslicereadings", "mocksliceviews")


@cache
def _readings() -> dict[str, Any]:
    return {
        name.removeprefix("readings/").removesuffix(".json"): document["value"]
        for name, document in mocksliceviews.readings().items()
    }


def _described() -> list[dict[str, Any]]:
    """Return the value of each document of the description, read as JSON."""
    return [
        cast("dict[str, Any]", document["value"]) for document in mockslice.description().values()
    ]


def _rows() -> dict[str, dict[str, Any]]:
    return {row["code"]: row for row in _readings()["portfolio_projects"]["items"]}


@pytest.mark.requirement(REQUIREMENT)
def test_the_slice_counts_ten_projects_of_the_composition_the_story_asks() -> None:
    # Ten projects, besides PRJ-001 and PRJ-002, in small numbers (US-2770, « la tranche compte
    # une dizaine de projets »).
    assert len(SLICE) == 10
    assert len({project.project_id for project in SLICE}) == 10
    states = {project.code: project.state_on(AS_OF) for project in SLICE}
    offers = [project for project in SLICE if states[project.code] == PRICING]
    # Offers of different probabilities of winning, one of them marked.
    assert len({project.probability for project in offers}) == len(offers) >= 2
    assert [p.code for p in offers if any(r.marked for r in p.revisions)] == ["PRJ-306"]
    # A project completed in the default period.
    completed = [p for p in SLICE if states[p.code] == COMPLETED]
    assert [p.code for p in completed] == ["PRJ-305"]
    assert PERIOD_FROM <= completed[0].history()[-1][0].date() <= AS_OF
    # An offer lost and one abandoned, both out of pricing.
    for state in (LOST, ABANDONED):
        (project,) = (p for p in SLICE if states[p.code] == state)
        assert project.history()[-2][2] == PRICING
    # Projects in progress, one in alert, one whose review is overdue.
    progressing = {p.code for p in SLICE if states[p.code] == IN_PROGRESS}
    assert len(progressing) >= 3
    rows = _rows()
    assert {code for code in progressing if rows[code]["cost_index"]["zone"] == "alert"} == {
        "PRJ-302"
    }
    overdue = {
        signal["project_id"]
        for signal in _readings()["pilot_health"]["signals"]
        if signal["code"] == "review_overdue"
    }
    assert mockslice.R3.project_id in overdue


@pytest.mark.requirement(REQUIREMENT)
def test_each_project_has_its_tasks_lines_and_transitions_and_the_slice_its_costs_and_risks() -> (
    None
):
    for project in _described():
        assert project["tasks"], project["project"]["code"]
        assert project["lines"], project["project"]["code"]
        assert [each["to_state"] for each in project["transitions"]][:2] == ["created", "pricing"]
    assert sum(len(p.risks) for p in SLICE) >= 4
    assert sum(len(p.imports) for p in SLICE) >= 8
    assert sum(1 for p in SLICE for r in p.revisions if r.marked) >= 12


def _working_day(day: date) -> bool:
    return day.weekday() < 5


@pytest.mark.requirement(REQUIREMENT)
def test_the_dates_of_the_slice_keep_to_the_rules_that_spare_its_readings_any_doubt() -> None:
    installed = datetime.fromisoformat("2025-09-01T09:00:00+00:00")
    for project in SLICE:
        moments = mockslice.instants(project)
        assert all(moment > installed for moment in moments), project.code
        assert [t for t, _, _ in project.history()] == sorted(t for t, _, _ in project.history())
        for task in project.tasks:
            # Each task lies within one month, on working days.
            assert (task.start.year, task.start.month) == (task.finish.year, task.finish.month)
            assert _working_day(task.start), (project.code, task.label)
            assert _working_day(task.finish), (project.code, task.label)
            assert task.completed_on in {None, task.finish}
        for revision in project.revisions:
            if revision.marked is None:
                continue
            day = revision.marked.date()
            for task in project.tasks:
                # At a marking, a task is completed, or ahead of it, or started past its finish.
                ahead = task.start > day
                assert task.completed_by(day) or ahead or task.started_on, (project.code, day)


@pytest.mark.requirement(REQUIREMENT)
def test_every_identifier_of_the_slice_is_of_its_family_and_names_one_object() -> None:
    families = {family.what: family for family in mockids.IDENTIFIERS}
    seen: list[str] = []
    for project in _described():
        assert families["projets de la tranche du portefeuille"].holds(project["project_id"])
        for each in project["revisions"]:
            assert families["révisions de la tranche du portefeuille"].holds(each["revision_id"])
        nodes = [*project["tasks"], *project["lines"]]
        nodes += [node for risk in project["risks"] for node in risk["own_estimate"]]
        for each in nodes:
            assert families["nœuds de la tranche du portefeuille"].holds(each["node_id"])
        for each in project["risks"]:
            assert families["risques de la tranche du portefeuille"].holds(each["risk_id"])
        seen += [project["project_id"], *(each["node_id"] for each in nodes)]
        seen += [each["revision_id"] for each in project["revisions"]]
        seen += [each["risk_id"] for each in project["risks"]]
        seen += [each["cost_import_id"] for each in project["imports"]]
        seen += [line["cost_line_id"] for each in project["imports"] for line in each["lines"]]
    assert len(seen) == len(set(seen))


@pytest.mark.requirement(REQUIREMENT)
def test_the_readings_are_computed_by_the_tools_alone_never_by_the_back() -> None:
    # « par un calcul que le back ne réemploie pas » (US-2770): no module of the generator imports
    # the back, nor names its sources.
    for name in GENERATORS:
        source = (REPOSITORY / "tools" / "src" / "wftools" / f"{name}.py").read_text("utf-8")
        tree = ast.parse(source)
        imported = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ] + [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        ]
        assert not [module for module in imported if module.split(".")[0] == "waterfall"], name
        assert "backend" not in source, name


@pytest.mark.requirement(REQUIREMENT)
def test_the_readings_carry_the_figures_computed_by_hand() -> None:
    value = _readings()["portfolio_value"]
    # The order book: PRJ-001's reference budget kept by its reference, and those of the four
    # projects in progress of the slice, 33,730 + 50,595 + 32,850 + 14,425.
    assert value["order_book"] == "70447996.56"
    # The one offer marked: 120 h at 80, 15,000 and 60 h at 75 = 29,100, at 60 %.
    assert (value["pipeline_gross"], value["pipeline_weighted"]) == ("29100.00", "17460.00")
    # PRJ-305, completed on 16 March 2026: 3,800 + 12,500 + 2,900.
    assert value["delivered"] == "19200.00"
    # Won in the period: PRJ-001, PRJ-301 to PRJ-305; lost: PRJ-309; PRJ-310 abandoned counts not.
    assert value["conversion_rate"]["value"] == "0.8571"
    rows = _rows()
    # PRJ-302 on 13 April 2026: earned 11,775 + 30,000, spent 16,000 + 38,000.
    assert rows["PRJ-302"]["cost_index"]["value"]["value"] == "0.7736"
    # Its remaining: the tests, 120 h at 73.50, and the provision of 4,000 at 75 %.
    assert rows["PRJ-302"]["project_manager_projection"] == "65820.00"
    # PRJ-304: its frame planned and not completed, 9,000 earned of 10,500 planned.
    assert rows["PRJ-304"]["schedule_index"]["zone"] == "watch"
    # The offers never marked, and PRJ-002, are listed without an amount (US-2670).
    for code in ("PRJ-002", "PRJ-307", "PRJ-308"):
        assert rows[code]["win_probability"] is None
        assert rows[code]["last_marked_at"] is None
    assert "PRJ-309" not in rows
    assert "PRJ-310" not in rows
    health = _readings()["pilot_health"]["signals"]
    weeks = {
        s["project_label"]: s["params"]["weeks_since_last_mark"]
        for s in health
        if s["code"] == "review_overdue"
    }
    # PRJ-303 last marked on 9 February 2026; PRJ-001 on 1 February.
    assert weeks == {mockslice.R3.label: 16, "Modernisation du poste de commande": 17}
    risks = _readings()["portfolio_risks"]
    # The provisions kept: PRJ-001's 850,060, and 300, 3,000 and 2,000 of the slice.
    assert risks["identified_total"] == "855360.00"
    # The reserve of PRJ-001 and that of PRJ-305, its risk identified when its offer was marked.
    assert risks["coverage"]["reserve"] == "851560.00"


def _amounts(items: list[dict[str, Any]]) -> Decimal:
    return sum((Decimal(item["amount"]) for item in items), Decimal(0))


@pytest.mark.requirement(REQUIREMENT)
def test_each_total_of_the_readings_is_the_sum_of_its_lines() -> None:
    found = _readings()
    listed = found["portfolio_projects"]
    assert listed["meta"]["total"] == listed["scope"]["project_count"] == len(listed["items"])
    budgets = sum(
        (
            Decimal(row["reference_budget"])
            for row in listed["items"]
            if row["state"] == IN_PROGRESS
        ),
        Decimal(0),
    )
    assert Decimal(found["portfolio_value"]["order_book"]) == budgets
    assert Decimal(found["portfolio_performance"]["reference_budget"]) == budgets
    plan = found["portfolio_workload"]
    for rank, total in enumerate(plan["monthly_totals"]):
        hours = sum((Decimal(role["months"][rank]["hours"]) for role in plan["roles"]), Decimal(0))
        assert Decimal(total["hours"]) == hours
    performance = found["portfolio_performance"]
    assert performance["quarterly"][-1]["cost_index"] == performance["cost_index"]["value"]
    assert performance["quarterly"][-1]["schedule_index"] == performance["schedule_index"]["value"]
    structure = found["portfolio_cost_structure"]
    for key in ("budget_by_cost_type", "remaining_by_cost_type", "labor_by_org_node"):
        assert sum(Decimal(each["share"]["value"]) for each in structure[key]) == 1
    labour = next(e for e in structure["budget_by_cost_type"] if e["label"] == "Main-d'œuvre")
    assert _amounts(structure["labor_by_org_node"]) == Decimal(labour["amount"])
    risks = found["portfolio_risks"]
    points = risks["matrix"]["points"]
    assert _sum_of(points, "provision_amount") == Decimal(risks["identified_total"])
    assert sum(cell["count"] for cell in risks["matrix"]["cells"]) == len(points)
    coverage = risks["coverage"]
    assert Decimal(coverage["coverage_variance"]) == Decimal(coverage["reserve"]) - Decimal(
        coverage["remaining_provisions"]
    ) - Decimal(coverage["occurred_cost"])
    curve = {series["name"]: series["points"] for series in found["portfolio_cost_curve"]["series"]}
    assert curve["actual_cost"][-1]["date"] == curve["project_manager_projection"][0]["date"]


def _sum_of(items: list[dict[str, Any]], key: str) -> Decimal:
    return sum((Decimal(item[key]) for item in items), Decimal(0))


@pytest.mark.requirement(REQUIREMENT)
def test_a_marking_after_the_date_of_the_witness_changes_no_reading() -> None:
    # Read at a past date, the portfolio does not change when a revision is marked after it
    # (WF-PTF-0010): the current revision of PRJ-303 marked on 10 June 2026.
    later = mockslice.at(date(2026, 6, 10))
    marked = replace(
        mockslice.R3,
        revisions=(
            *mockslice.R3.revisions[:-1],
            Revision(mockslice.R3.revisions[-1].opened, later, "Revue de juin"),
        ),
    )
    found = [member(marked) if each.project_id == marked.project_id else each for each in members()]
    before, after = Portfolio(members()), Portfolio(found)
    for _, _, compute in mocksliceviews.VIEWS:
        assert compute(after) == compute(before)


@pytest.mark.requirement(REQUIREMENT)
def test_make_mock_data_writes_the_slice_and_keeps_it(tmp_path: Path) -> None:
    directory = tmp_path / "witness" / "portfolio"
    written = mocksliceviews.write(directory)
    assert len(written) == len(SLICE) + len(mocksliceviews.VIEWS)
    assert mocksliceviews.check(directory) == []
    (directory / "projects" / "PRJ-301.json").write_text("{}\n", encoding="utf-8")
    (directory / "readings" / "pilot_health.json").unlink()
    (directory / "readings" / "old.json").write_text("{}\n", encoding="utf-8")
    assert mocksliceviews.check(directory) == [
        "witness/portfolio/readings/old.json is left over",
        "witness/portfolio/projects/PRJ-301.json is outdated",
        "witness/portfolio/readings/pilot_health.json is missing",
    ]
    mocksliceviews.write(directory)
    assert mocksliceviews.check(directory) == []
    assert mocksliceviews.directory_of(_api_fixtures()) == mocksliceviews.SLICE_DIRECTORY


def _api_fixtures() -> Path:
    return REPOSITORY / "fixtures" / "api"


@pytest.mark.requirement(REQUIREMENT)
def test_the_versioned_slice_is_the_one_the_generator_writes() -> None:
    assert mocksliceviews.check(mocksliceviews.SLICE_DIRECTORY) == []
    reading = json.loads(
        (mocksliceviews.SLICE_DIRECTORY / "readings" / "portfolio_value.json").read_text("utf-8")
    )
    assert reading["operation"] == "getPortfolioValue"
    assert reading["query"] == {"as_of": "2026-06-03", "states": "in_progress,pricing,completed"}
