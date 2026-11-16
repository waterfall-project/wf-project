# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the detail of the workload of the witness by task, and of the parts of a line.

They try the examples `getProjectWorkload` serves against the rules the contract states of them
(US-2040/L1, #3511): the tasks of a role sum to it month by month, a role and a task carry only
the months they load (#3096), the tasks are in the order of their start, then of the plan.
"""

import json
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from wftools import (
    mockcore,
    mockcurves,
    mockdata,
    mockhistory,
    mockindicators,
    mockspending,
    mocktoday,
    mockwitness,
)
from wftools.mockcalendar import Calendar, Instant
from wftools.mockids import universe
from wftools.mockindicators import Flow

type Node = dict[str, Any]

PLANS = ("workload", "workload_reference_budget", "workload_marked_remaining", "workload_org_node")

WEEK = Calendar(universe(481), tuple(Decimal(h) for h in ("8", "8", "8", "8", "8", "0", "0")))


@pytest.fixture(scope="module")
def plans() -> dict[str, Node]:
    """Return the examples of the workload, read back from the text the generator writes."""
    found = mocktoday.examples()
    return {name: json.loads(mockdata.render(found[f"{name}.json"]))["value"] for name in PLANS}


def _hours(months: list[Node]) -> dict[str, Decimal]:
    return {month["month"]: Decimal(month["hours"]) for month in months}


@pytest.mark.parametrize("name", PLANS)
def test_the_tasks_of_a_role_sum_to_its_hours_month_by_month(
    plans: dict[str, Node], name: str
) -> None:
    for role in plans[name]["roles"]:
        summed: dict[str, Decimal] = {}
        for task in role["tasks"]:
            months = _hours(task["months"])
            assert Decimal(task["hours"]) == sum(months.values(), Decimal(0))
            for month, hours in months.items():
                summed[month] = summed.get(month, Decimal(0)) + hours
        assert summed == _hours(role["months"])


@pytest.mark.parametrize("name", PLANS)
def test_a_role_and_a_task_carry_only_the_months_they_load(
    plans: dict[str, Node], name: str
) -> None:
    for role in plans[name]["roles"]:
        assert all(Decimal(month["hours"]) for month in role["months"])
        for task in role["tasks"]:
            months = [month["month"] for month in task["months"]]
            assert months == sorted(set(months))
            assert all(Decimal(month["hours"]) for month in task["months"])


def test_the_witness_has_a_role_loaded_on_fewer_months_than_the_others(
    plans: dict[str, Node],
) -> None:
    # #3096: the cable fitter is loaded on 8 months of the 39 of the plan, which the axis spans.
    plan = plans["workload"]
    counts = [len(role["months"]) for role in plan["roles"]]
    assert counts == [38, 38, 8]
    assert len(plan["monthly_totals"]) == 39


@pytest.mark.parametrize("name", PLANS)
def test_the_tasks_of_a_role_are_in_the_order_of_their_start_then_of_the_plan(
    plans: dict[str, Node], name: str
) -> None:
    for role in plans[name]["roles"]:
        keys = [
            (task["start"]["date"], Decimal(task["start"]["hours"]), task["row_number"])
            for task in role["tasks"]
        ]
        assert keys == sorted(keys)
        assert len({task["node_id"] for task in role["tasks"]}) == len(role["tasks"])


def test_on_the_remaining_a_completed_task_is_not_in_the_detail(plans: dict[str, Node]) -> None:
    witness = mockindicators.today()
    completed = {
        str(witness.by_number[number].node["node_id"])
        for number in {line.parent for line in witness.lines}
        if number is not None and witness.task(number)["progress"] == "completed"
    }
    assert completed
    for role in plans["workload"]["roles"]:
        assert not completed & {task["node_id"] for task in role["tasks"]}


def test_two_lines_of_a_role_under_a_task_make_one_task_of_their_summed_hours(
    plans: dict[str, Node],
) -> None:
    witness = mockindicators.reference()
    by_pair: dict[tuple[str, int], list[Decimal]] = {}
    for line in witness.lines:
        role = witness.facet(line)["resource_role_id"]
        if isinstance(role, str) and line.parent is not None:
            by_pair.setdefault((role, line.parent), []).append(line.hours)
    (role_id, number), hours = next((pair, each) for pair, each in by_pair.items() if len(each) > 1)
    node = witness.by_number[number].node["node_id"]
    [role] = [
        role
        for role in plans["workload_reference_budget"]["roles"]
        if role["resource_role_id"] == role_id
    ]
    [task] = [task for task in role["tasks"] if task["node_id"] == node]
    assert Decimal(task["hours"]) == sum(hours, Decimal(0))


def test_the_parts_of_a_line_sum_to_its_total_the_remainder_on_its_last_month() -> None:
    # Ten hours over three days, the last of a month and two of the next: 10/3 each.
    flow = Flow(
        Decimal(10),
        WEEK,
        Instant(date(2026, 6, 30), Decimal(0)),
        Instant(date(2026, 7, 2), Decimal(8)),
    )
    assert mockcurves.parts(flow) == {"2026-06": Decimal("3.33"), "2026-07": Decimal("6.67")}
    # 1,200 over a task of exactly two months, pro rata of their hours worked: 22 and 23 days.
    spent = Flow(
        Decimal(1200),
        WEEK,
        Instant(date(2026, 6, 1), Decimal(0)),
        Instant(date(2026, 7, 31), Decimal(8)),
    )
    assert mockcurves.parts(spent) == {"2026-06": Decimal("586.67"), "2026-07": Decimal("613.33")}
    # Spent at once, the whole in its month; a part rounded to nought is no month loaded.
    once = Flow(
        Decimal("0.004"),
        WEEK,
        Instant(date(2026, 6, 3), Decimal(8)),
        Instant(date(2026, 6, 3), Decimal(8)),
    )
    assert mockcurves.parts(once) == {}


def test_a_task_whose_lines_carry_no_hour_is_listed_without_a_month() -> None:
    witness = mockindicators.today()
    line = next(line for line in witness.lines if witness.facet(line)["resource_role_id"])
    # The same line with no hour: its task stays in the detail, with nothing to spread.
    idle = replace(line, hours=Decimal(0))
    [(task, months)] = mockcurves.tasks_of(witness, [idle], "reference_budget")
    assert task["hours"] == "0"
    assert task["months"] == []
    assert months == {}


def test_the_parts_of_a_line_are_never_negative_and_sum_to_its_total() -> None:
    # 0.011 over two months and a day: the exact parts, 0.00526, 0.00564 and 0.00010, round to
    # 0.01, 0.01 and 0.00 — the remainder carried on the last month would be -0.01.
    flow = Flow(
        Decimal("0.011"),
        WEEK,
        Instant(date(2026, 6, 1), Decimal(0)),
        Instant(date(2026, 8, 3), Decimal(8)),
    )
    found = mockcurves.parts(flow)
    assert found == {"2026-06": Decimal("0.01")}
    assert all(part > 0 for part in found.values())
    assert sum(found.values(), Decimal(0)) == Decimal("0.011").quantize(Decimal("0.01"))


def _at_once(amount: str) -> Flow:
    day = Instant(date(2026, 6, 3), Decimal(8))
    return Flow(Decimal(amount), WEEK, day, day)


def test_the_hours_round_an_exact_half_to_the_even_hundredth() -> None:
    # Hours: half to the nearest even, as the workload of the core (`parting.HOURS`).
    assert mockcurves.parts(_at_once("0.005")) == {}
    assert mockcurves.parts(_at_once("0.015")) == {"2026-06": Decimal("0.02")}
    assert mockcurves.parts(_at_once("0.025")) == {"2026-06": Decimal("0.02")}


def test_the_amounts_round_an_exact_half_away_from_zero() -> None:
    # Amounts: half away from zero, as the pricing of the core (`parting.MONEY`). The mode is the
    # one the projection of spending chooses (`mockspending.amounts_of`): a line of half a cent,
    # budgeted, spreads a cent in all, where the hours would round it to nought.
    witness = mockindicators.today()
    line = next(line for line in witness.lines if line.amounts.budgeted)
    half = replace(line, amounts=replace(line.amounts, budgeted=Decimal("0.005")))
    parts = mockspending.amounts_of(witness, half, "reference_budget", delays=False)
    assert list(parts.values()) == [Decimal("0.01")]


def _rows_of(rows: list[mockcore.Row]) -> dict[str, int]:
    return {str(row.node["node_id"]): int(str(row.node["row_number"])) for row in rows}


@pytest.mark.requirement("WF-DEV-0090-A")
@pytest.mark.parametrize(
    ("name", "rows"),
    [
        ("workload", mockcore.current),
        ("workload_reference_budget", mockhistory.reference_rows),
        ("workload_marked_remaining", mockhistory.reference_rows),
    ],
)
def test_a_task_of_the_detail_has_the_row_of_its_node_in_the_revision_the_plan_reads(
    plans: dict[str, Node], name: str, rows: Any
) -> None:
    """The tasks of the detail of a role, by task (WF-DEV-0090), carry the row of their node.

    The plan of the 101 numbers its tasks as the 101 does, which lacks the rows the 102 added (a
    provision, the tasks of risks): not a shift, the contract says so (#3584).
    """
    held = _rows_of(rows())
    tasks = [task for role in plans[name]["roles"] for task in role["tasks"]]
    assert tasks
    assert all(task["row_number"] == held[task["node_id"]] for task in tasks)


def test_a_task_of_the_detail_of_the_102_has_its_row_in_the_planning_examples() -> None:
    """A task of the detail of the workload by task (WF-DEV-0090) has the row of the planning."""
    found = mocktoday.examples()
    planned = {
        node["node_id"]: node["row_number"]
        for state in mockwitness.fixture("startable_tasks").values()
        for node in state
    }
    detail = json.loads(mockdata.render(found["workload.json"]))["value"]
    tasks = [task for role in detail["roles"] for task in role["tasks"]]
    shared = [task for task in tasks if task["node_id"] in planned]
    assert shared
    assert all(task["row_number"] == planned[task["node_id"]] for task in shared)
