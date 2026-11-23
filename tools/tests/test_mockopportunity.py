# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the contract of the risks: their trend, an opportunity, its occurrence (US-3080/L1).

EP-30 makes the severity of a risk a signed net gap, gives each risk its trend since the previous
marked revision, gives the report of an occurrence the form of a merge, and marks the occurrence on
the earned value curve (#4589): ``wftools.mockwitnessrisks`` says the trend of the register of the
witness, and ``wftools.mockopportunity`` writes the declared variants of an opportunity.
"""

import re
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcore, mockcurves, mockhistory, mockopportunity, mocktoday
from wftools.mockids import universe
from wftools.mockwitness import AMENDMENT_MERGED, TODAY, N, lineage_id
from wftools.mockwitnessrisks import (
    DOWN,
    IDENTIFIED,
    NEW,
    REGISTER,
    STABLE,
    UP,
    Review,
    trend,
)

type Entry = dict[str, Any]

API = REPOSITORY / "docs" / "api"
MARKED = AMENDMENT_MERGED.instant


def _risk(before: tuple[str, str] | None, now: tuple[str, str], state: str = IDENTIFIED) -> Any:
    """Return 751 reviewed once before the marking of the reference, if at all, and once today."""
    reviews: tuple[Review, ...] = ()
    if before is not None:
        reviews = (Review(MARKED, Decimal(before[1]), Decimal(before[0])),)
    today = Review(TODAY, Decimal(now[1]), Decimal(now[0]), state)
    return replace(REGISTER[0], reviews=(*reviews, today))


@pytest.mark.requirement("WF-RIS-0040-A")
@pytest.mark.parametrize(
    ("before", "now", "expected"),
    [
        (("300", "0.2"), ("300", "0.25"), UP),
        (("300", "0.2"), ("300", "0.15"), DOWN),
        (("300", "0.2"), ("200", "0.3"), STABLE),
        (("-100", "0.3"), ("-150", "0.3"), DOWN),
        (None, ("300", "0.2"), NEW),
    ],
)
def test_the_trend_compares_the_signed_products_with_the_reference(
    before: tuple[str, str] | None, now: tuple[str, str], expected: str
) -> None:
    # 60 to 75 is up, to 45 down, to 60 stable; an opportunity from -30 to -45 is down; a risk not
    # identified at the marking of the reference is new (WF-RIS-0040).
    assert trend(_risk(before, now)) == expected


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_risk_dismissed_at_the_reference_and_identified_again_is_new() -> None:
    dismissed = (Review(MARKED, Decimal("0.2"), Decimal(300), "dismissed"),)
    risk = replace(REGISTER[0], reviews=(*dismissed, Review(TODAY, Decimal("0.2"), Decimal(300))))
    assert trend(risk) == NEW


@pytest.mark.requirement("WF-RIS-0040-A")
def test_a_risk_occurred_or_dismissed_has_no_trend() -> None:
    assert trend(_risk(("300", "0.2"), ("300", "0.2"), "occurred")) is None
    assert trend(_risk(("300", "0.2"), ("300", "0.2"), "dismissed")) is None


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_register_of_the_witness_carries_the_trend_of_each_risk() -> None:
    # 751, from 1,000,000 at 25 % to 1,250,000 at 40 %, is up; 752 occurred and 753 dismissed have
    # none.
    items = cast("list[Entry]", mockhistory.readings()["risks"]["items"])
    assert [each["trend"] for each in items] == [UP, None, None]


def _value(name: str) -> Entry:
    return cast("Entry", mockopportunity.examples()[f"{name}.json"]["value"])


@pytest.mark.requirement("WF-RIS-0080-A")
def test_the_opportunity_has_a_negative_severity_and_a_provision_of_nought() -> None:
    [*witness, opportunity] = _value("risks_opportunity")["items"]
    assert Decimal(opportunity["severity"]) < 0
    assert opportunity["provision_amount"] == "0.00"
    assert opportunity["trend"] == NEW
    assert opportunity["provision_node_id"] == universe(588)
    assert witness == mockhistory.readings()["risks"]["items"]


@pytest.mark.requirement("WF-RIS-0080-A")
def test_the_opportunity_changes_no_total_of_the_register() -> None:
    assert _value("risks_opportunity")["totals"] == mockhistory.readings()["risks"]["totals"]


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_matrix_counts_the_opportunity_at_the_lowest_severity_level() -> None:
    matrix, witness = _value("risk_matrix_opportunity"), mockhistory.readings()["risk_matrix"]
    point = cast("list[Entry]", matrix["points"])[-1]
    counted = {
        (cell["probability_level"], cell["severity_level"]): cell["count"]
        for cell in cast("list[Entry]", witness["cells"])
    }
    [added] = [
        cell
        for cell in cast("list[Entry]", matrix["cells"])
        if cell["count"] != counted[cell["probability_level"], cell["severity_level"]]
    ]
    assert added["severity_level"] == 1
    assert added["count"] == counted[added["probability_level"], 1] + 1
    assert Decimal(point["severity_ratio"]["value"]) < 0
    assert point["provision_amount"] == "0.00"


@pytest.mark.requirement("WF-RIS-0060-A")
def test_the_report_names_the_abandoned_task_completed_and_its_earned_value() -> None:
    # The commissioning, not started, is kept and completed: its budgeted amount comes in at once.
    report = _value("risk_occurrence_report_abandoned_task")
    lines = [
        row
        for row in mockcore.current()
        if row.kind == mockcore.ESTIMATE_LINE and row.parent == N.COMMISSIONING
    ]
    budgeted = sum((row.amounts.budgeted for row in lines), Decimal(0))
    assert report["completed_tasks"] == [
        {
            "lineage_id": lineage_id(N.COMMISSIONING),
            "label": "Mise en service",
            "completed_on": None,
        }
    ]
    assert [(each["change"], each["target"]) for each in report["differences"]] == [
        ("kept", "task"),
        ("removed", "estimate_line"),
    ]
    assert Decimal(report["earned_value_added"]) == budgeted
    assert report["earned_value_removed"] == "0.00"
    assert report["reopened_tasks"] == []
    assert report["provision_amount"] == "0.00"
    assert "own_estimate_past_planning_start_on" not in report


@pytest.mark.requirement("WF-IND-0140-A")
def test_the_curve_carries_the_step_of_the_occurrence_at_its_day() -> None:
    curves = _value("earned_value_curves_occurrence")
    report = _value("risk_occurrence_report_abandoned_task")
    found = mocktoday.witness()
    witness = mockcurves.earned_value_curves(found.today, found.reference, found.costs)
    [step] = curves["steps"]
    brought = Decimal(report["earned_value_added"]) - Decimal(report["earned_value_removed"])
    assert step["date"] == TODAY.date().isoformat()
    assert step["cause"] == "risk_occurrence"
    assert step["risk_id"] == universe(755)
    assert Decimal(step["amount"]) == brought

    def earned(of: Entry) -> list[Entry]:
        [points] = [s["points"] for s in of["series"] if s["name"] == "earned_value"]
        return cast("list[Entry]", points)

    assert earned(curves)[:-1] == earned(witness)[:-1]
    assert Decimal(earned(curves)[-1]["amount"]) == Decimal(earned(witness)[-1]["amount"]) + brought


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_coverage_counts_the_negative_cost_at_occurrence_as_it_is() -> None:
    covered = _value("risk_coverage_opportunity")
    witness = cast("Entry", mockhistory.readings()["risk_coverage"])
    cost = mockopportunity.severity()
    assert cost < 0
    assert Decimal(covered["occurred_cost"]) == Decimal(witness["occurred_cost"]) + cost
    assert Decimal(covered["coverage_variance"]) == Decimal(witness["coverage_variance"]) - cost
    assert covered["remaining_provisions"] == witness["remaining_provisions"]


def _cited(path: str, method: str, status: str) -> list[str]:
    document = cast("Entry", yaml.safe_load((API / "paths" / path).read_text("utf-8")))
    examples = [
        operation[method]["responses"][status]["content"]["application/json"].get("examples", {})
        for operation in document.values()
        if status in operation.get(method, {}).get("responses", {})
        and "application/json" in operation[method]["responses"][status].get("content", {})
    ]
    return [
        re.sub(r".*/(\w+)\.json$", r"\1", each["$ref"])
        for found in examples
        for each in found.values()
    ]


def test_every_example_of_the_module_is_cited_by_the_contract() -> None:
    cited = {*_cited("risks.yaml", "get", "200"), *_cited("analysis.yaml", "get", "200")}
    names = {name.removesuffix(".json") for name in mockopportunity.examples()}
    assert names <= cited
