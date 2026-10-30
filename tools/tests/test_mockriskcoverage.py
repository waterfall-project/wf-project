# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the risks aligned on the specification 1.0.0 (US-0701/L4, #1604).

The cost at occurrence of a risk that occurred, which the coverage compares to the reserve (H-01,
H-02, WF-RIS-0050); the provision of a risk that occurred or was dismissed, that of the reference
(H-03, WF-RIS-0040); the probability written by the review alone (H-04); the tasks the occurrence
merges, placed and in their modes (M-05, WF-RIS-0060) — on the witness and its examples.
"""

from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockcore, mockhistory, mockwitness
from wftools.mockids import universe
from wftools.mockwitness import N
from wftools.mockwitnessrisks import DELIVERY_DELAY, IDENTIFIED, OCCURRED, REGISTER

type Entry = dict[str, Any]

SCHEMAS = REPOSITORY / "docs" / "api" / "components" / "schemas"


def _risks_schemas() -> Entry:
    return cast("Entry", yaml.safe_load((SCHEMAS / "risks.yaml").read_text(encoding="utf-8")))


def _items() -> list[Entry]:
    return cast("list[Entry]", mockwitness.fixture("risks")["items"])


@pytest.mark.requirement("WF-RIS-0050-A")
def test_the_completion_of_the_merged_tasks_changes_neither_the_cost_of_the_occurred_nor_the_variance() -> (
    None
):
    today, rows = mockcore.current(), mockhistory.reference_rows()
    read = mockhistory.coverage(today, rows)
    # The witness's merged tasks are completed, in May: the coverage counts the cost at occurrence.
    assert read == mockwitness.fixture("risk_coverage")
    assert read["occurred_cost"] == "200.00"
    merged = {row.number for row in mockhistory.merged_lines(today)}
    assert merged == {N.REMINDER_LINE, N.TRANSPORT_LINE}
    # Re-estimated since — what their completion, their dates or a re-estimate do to their lines —,
    # the lines merged by 752 change neither the cost of the occurred nor the variance.
    moved = [
        replace(row, amounts=replace(row.amounts, reestimated=row.amounts.reestimated * 3))
        if row.number in merged
        else row
        for row in today
    ]
    again = mockhistory.coverage(moved, rows)
    assert (again["occurred_cost"], again["coverage_variance"]) == (
        read["occurred_cost"],
        read["coverage_variance"],
    )
    reserve, remaining = Decimal(read["reserve"]), Decimal(read["remaining_provisions"])
    assert Decimal(read["coverage_variance"]) == reserve - remaining - Decimal("200.00")


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_risk_that_occurred_keeps_its_cost_at_occurrence_and_the_others_have_none() -> None:
    items = {item["risk_id"]: item for item in _items()}
    for risk in REGISTER:
        item = items[universe(risk.number)]
        expected = "200.00" if risk.last.state == OCCURRED else None
        assert item["occurrence_cost"] == expected, risk.label
    detail = mockwitness.fixture("risk_occurred_detail")
    assert detail["occurrence_cost"] == "200.00"
    assert detail == items[universe(DELIVERY_DELAY.number)]
    occurrence_cost = _risks_schemas()["Risk"]["properties"]["occurrence_cost"]
    assert "coût à la survenance" in occurrence_cost["description"]
    assert "occurrence_cost" in _risks_schemas()["Risk"]["required"]


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_provisions_of_the_register_sum_to_the_three_distinct_totals() -> None:
    register = mockwitness.fixture("risks")
    totals = register["totals"]
    by_state: dict[str, Decimal] = {}
    for item in _items():
        by_state[item["state"]] = by_state.get(item["state"], Decimal(0)) + Decimal(
            item["provision_amount"]
        )
    for state, amount in by_state.items():
        assert Decimal(totals[state]) == amount, state
    # A risk that occurred or was dismissed is read for the provision the reference bore.
    for risk in REGISTER:
        if risk.last.state != IDENTIFIED:
            reference = risk.known_on(mockwitness.AMENDMENT_MERGED.on)
            assert reference is not None
            assert mockhistory.provision_amount(risk) == (
                reference.severity * reference.probability
            ).quantize(Decimal("0.01"))


def test_a_risk_identified_after_the_reference_and_dismissed_is_read_at_no_provision() -> None:
    engineer = REGISTER[2]
    late = replace(
        engineer,
        reviews=tuple(
            replace(review, at=review.at.replace(year=2026, month=3, day=10))
            for review in engineer.reviews
        ),
    )
    assert mockhistory.provision_amount(late) == Decimal("0.00")


def test_the_modification_of_a_risk_does_not_receive_its_probability() -> None:
    # H-04: the probability is written by the review alone (decision of the author, 2026-10-28).
    schemas = _risks_schemas()
    update = schemas["RiskUpdate"]
    assert "allOf" not in update
    assert "probability" not in update["properties"]
    assert set(update["required"]) == {"label", "lock_version"}
    assert "probability" in schemas["RiskReviewWrite"]["required"]
    assert not (mockwitness.FIXTURES / "risk_update_probability_out_of_range.json").exists()


@pytest.mark.requirement("WF-RIS-0060-A")
def test_a_merged_task_without_a_predecessor_is_in_manual_mode_at_its_dates() -> None:
    subtree = cast("list[Entry]", mockwitness.fixture("nodes_risk_occurred")["items"])
    tasks = {node["node_id"]: node for node in subtree if node["kind"] == "task"}
    reminder = tasks[universe(N.REMINDER)]
    assert reminder["task"]["scheduling_mode"] == "manual"
    assert reminder.get("predecessors", []) == []
    assert (reminder["task"]["start"]["date"], reminder["task"]["finish"]["date"]) == (
        "2026-05-04",
        "2026-05-08",
    )
    transport = tasks[universe(N.TRANSPORT)]
    assert transport["task"]["scheduling_mode"] == "automatic"
    assert [link["predecessor_node_id"] for link in transport["predecessors"]] == [
        universe(N.REMINDER)
    ]
    # The merged lines bear a budget of nothing and their own amount as re-estimate.
    lines = [node["estimate_line"] for node in subtree if node["kind"] == "estimate_line"]
    assert [(line["budgeted_amount"], line["reestimated_amount"]) for line in lines] == [
        ("0.00", "120.00"),
        ("0.00", "80.00"),
    ]
    # Under the task that bore the provision of 752 in the reference: the control station.
    head = tasks[universe(N.MERGED)]
    assert head["parent_id"] == universe(N.CONTROL_STATION)
