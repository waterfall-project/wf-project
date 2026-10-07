# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the structure of a thousand tasks the fake back serves, and of its indicators."""

import json
import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import REPOSITORY, mockdata, mockstructure, mockwitness
from wftools.mockstructure import Task

MONEY = re.compile(r"^\d+\.\d{2}$")

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def answer() -> dict[str, Any]:
    """Make the structure once, as the JSON the fake back serves."""
    return cast("dict[str, Any]", json.loads(json.dumps(mockstructure.structure().nodes)))


@pytest.fixture(scope="module")
def items(answer: dict[str, Any]) -> list[Node]:
    """Read the nodes of the structure of a thousand tasks."""
    return cast("list[Node]", answer["items"])


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


def test_a_thousand_tasks_carry_five_thousand_lines(answer: dict[str, Any]) -> None:
    value = answer
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
    rates = {line.category: line.rate for line in mockstructure.LINE_KINDS if line.rate}
    for node in lines(items):
        line = node["estimate_line"]
        assert MONEY.match(line["base_amount"])
        assert line["base_amount"] == line["budgeted_amount"] == line["reestimated_amount"]
        if line["hours"] is None:
            expected = Decimal(line["quantity"]) * Decimal(line["unit_disbursement"])
        else:
            assert line["resource_role_id"] is not None
            expected = Decimal(line["hours"]) * rates[line["cost_category_id"]]
        assert Decimal(line["base_amount"]) == expected


@pytest.mark.parametrize(
    "amount", ["base_amount", "budgeted_amount", "reestimated_amount", "inflated_amount"]
)
def test_a_task_sums_the_lines_under_it_and_the_totals_all_of_them(
    answer: dict[str, Any], items: list[Node], amount: str
) -> None:
    # Each amount of a task and of the totals, the one corrected for inflation among them
    # (WF-DEV-0050): the sum of the same amount of the lines.
    nodes = by_id(items)
    sums: dict[str, Decimal] = dict.fromkeys(nodes, Decimal(0))
    for node in lines(items):
        value = Decimal(node["estimate_line"][amount])
        parent = node["parent_id"]
        while parent is not None:
            sums[parent] += value
            parent = nodes[parent]["parent_id"]
    for node in tasks(items):
        assert Decimal(node["task"][amount]) == sums[node["node_id"]]
    totals = answer["totals"]
    amounts = [Decimal(node["estimate_line"][amount]) for node in lines(items)]
    hours = [Decimal(node["estimate_line"]["hours"] or 0) for node in lines(items)]
    assert Decimal(totals[amount]) == sum(amounts)
    assert Decimal(totals["hours"]) == sum(hours)


def test_a_task_lasts_its_duration_in_working_days(items: list[Node]) -> None:
    for node in tasks(items):
        task = node["task"]
        start, finish = task["start"]["date"], task["finish"]["date"]
        assert date.fromisoformat(start).weekday() < 5
        assert date.fromisoformat(finish).weekday() < 5
        # A task starts at the first hour of its first day and finishes at the last of its
        # last, as WF-DAT-0100 writes an instant of work; a milestone sits at one instant.
        assert task["duration"]["unit"] == "d"
        assert task["finish_overdue"] is False
        if task["is_milestone"]:
            assert task["duration"]["value"] == "0"
            assert task["start"] == task["finish"]
        else:
            assert (task["start"]["hours"], task["finish"]["hours"]) == ("0", "8")
            assert working_days(start, finish) == int(task["duration"]["value"])


def test_a_task_starts_after_its_predecessors_finish(items: list[Node]) -> None:
    nodes = by_id(items)
    for node in tasks(items):
        for link in node.get("predecessors", []):
            designated = nodes[link["predecessor_node_id"]]
            assert link["predecessor_row_number"] == designated["row_number"]
        finishes = [
            nodes[link["predecessor_node_id"]]["task"]["finish"]
            for link in node.get("predecessors", [])
        ]
        if not finishes:
            continue
        task = node["task"]
        if task["is_milestone"]:
            # Where its predecessors finish: the last hour of their last day.
            assert task["start"] == max(finishes, key=_instant)
        else:
            assert working_days(max(finishes, key=_instant)["date"], task["start"]["date"]) == 2


def test_a_summary_spans_its_subordinates(items: list[Node]) -> None:
    for node in tasks(items):
        task = node["task"]
        if not task["is_summary"]:
            continue
        below = [child["task"] for child in children(items, node)]
        assert task["start"] == min((child["start"] for child in below), key=_instant)
        assert task["finish"] == max((child["finish"] for child in below), key=_instant)
        assert "task.duration" in node["computed_fields"]
        assert "total_float" not in task


def _instant(instant: dict[str, str]) -> tuple[str, Decimal]:
    return instant["date"], Decimal(instant["hours"])


def test_the_critical_path_runs_to_the_last_finish(items: list[Node]) -> None:
    work = [node["task"] for node in tasks(items) if not node["task"]["is_summary"]]
    last = max(task["finish"]["date"] for task in work)
    floats = [task["total_float"] for task in work]
    assert all(total["unit"] == "d" and Decimal(total["value"]) >= 0 for total in floats)
    assert all(task["is_critical"] == (Decimal(task["total_float"]["value"]) == 0) for task in work)
    assert all(task["is_critical"] for task in work if task["finish"]["date"] == last)
    assert 0 < sum(task["is_critical"] for task in work) < len(work)


def test_progress_is_that_of_the_day_the_examples_are_read(items: list[Node]) -> None:
    today = mockstructure.AS_OF.isoformat()
    nodes = by_id(items)
    for node in tasks(items):
        task = node["task"]
        if task["is_summary"]:
            continue
        if task["progress"] == "completed":
            assert task["finish"]["date"] < today
            assert task["completed_on"] == task["finish"]["date"]
        elif task["progress"] == "started":
            assert task["start"]["date"] <= today <= task["finish"]["date"]
        else:
            assert today < task["start"]["date"] or task["is_milestone"]
    states = Counter(node["task"]["progress"] for node in tasks(items))
    assert set(states) == {"completed", "started", "not_started"}
    for node in lines(items):
        completed = nodes[node["parent_id"]]["task"]["progress"] == "completed"
        entry = node["estimate_line"]["remaining_entry"]
        assert entry["is_available"] is not completed
        assert entry["missing_conditions"] == (["task_not_completed"] if completed else [])


def test_a_line_is_projected_on_the_year_its_task_starts(items: list[Node]) -> None:
    nodes = by_id(items)
    for node in lines(items):
        line = node["estimate_line"]
        start = nodes[node["parent_id"]]["task"]["start"]["date"]
        assert line["consumption_year"] == int(start[:4])
        assert line["uses_inactive_object"] is False
    # Witness values, at 3 % a year: a line of 2026 is not projected, the first line of 2027
    # grows by 3 %, the last line of the structure, of 2029, by 9.27 %.
    projected = {
        4: (2026, "2640.00", "2640.00"),
        1363: (2027, "440.00", "453.20"),
        5999: (2029, "758.80", "829.16"),
    }
    for row, (year, amount, inflated) in projected.items():
        line = items[row - 1]["estimate_line"]
        assert (line["consumption_year"], line["base_amount"]) == (year, amount)
        assert line["inflated_amount"] == inflated


def test_a_provision_is_computed_and_outside_the_subprojects(items: list[Node]) -> None:
    provisions = [node for node in lines(items) if node["estimate_line"]["is_computed"]]
    assert len(provisions) == 350
    for node in provisions:
        assert node["estimate_line"]["cost_category_id"] == mockwitness.PROVISIONS
        assert node["estimate_line"]["subproject_id"] is None
        assert node["computed_fields"] == [
            "estimate_line.quantity",
            "estimate_line.unit_disbursement",
        ]


def test_the_structure_stays_in_the_universe_of_the_examples(items: list[Node]) -> None:
    fixtures = REPOSITORY / "fixtures" / "api"
    known = (fixtures / "subprojects.json").read_text(encoding="utf-8")
    subprojects = {node["estimate_line"]["subproject_id"] for node in lines(items)} - {None}
    assert subprojects == {mockwitness.SUBPROJECT_CONTROL, mockstructure.SUBPROJECT_TESTS}
    assert all(subproject in known for subproject in subprojects)
    assert items[0]["task"]["label"] == "Études"


def test_a_line_names_its_category_role_and_subproject_as_the_universe_does(
    items: list[Node],
) -> None:
    # The labels the server resolves at the reading (#305): those of the categories the fake back
    # lists, of the roles and the subprojects of the witness.
    categories = cast("list[dict[str, str]]", mockdata.categories())
    names = {category["cost_category_id"]: category["label"] for category in categories}
    roles = mockwitness.fixture("resource_roles")
    names.update((role["resource_role_id"], role["label"]) for role in roles)
    subprojects = mockwitness.fixture("subprojects")
    names.update((entry["subproject_id"], entry["label"]) for entry in subprojects)
    for node in lines(items):
        line = node["estimate_line"]
        for key in ("cost_category", "resource_role", "subproject"):
            identifier = line[f"{key}_id"]
            assert line[f"{key}_label"] == (None if identifier is None else names[identifier])


def test_schedule_dates_a_small_network_by_hand() -> None:
    # A (3 days) and B (1 day) both lead to C (2 days), then to the milestone M: A and C make
    # the critical path, and B may slip two days.
    a, b, c = Task("A", duration=3), Task("B", duration=1), Task("C", duration=2)
    m = Task("M", is_milestone=True)
    for before, after in ((a, c), (b, c), (c, m)):
        before.successors.append(after)
        after.predecessors.append(before)
    summary = Task("S", children=[a, b, c, m])
    mockstructure.schedule([summary], [a, b, c, m])
    assert [(task.start, task.end) for task in (a, b, c, m)] == [(0, 2), (0, 0), (3, 4), (4, 4)]
    assert [task.late_end - task.end for task in (a, b, c, m)] == [0, 2, 0, 0]
    assert (summary.start, summary.end, summary.duration) == (0, 4, 5)
    assert mockstructure.working_day(m.end) == date(2026, 3, 6)


def test_the_marks_the_journeys_read(answer: dict[str, Any], items: list[Node]) -> None:
    # The end-to-end paths of the front read the structure by these rows (grid.spec.ts,
    # planning.spec.ts, witness.spec.ts, computed.spec.ts), and the refusal of computed.spec.ts
    # what summary_dependencies.json says of row 1: a change of the generator that moves them
    # fails here.
    assert answer["totals"] == {
        "task_count": 1_000,
        "estimate_line_count": 5_000,
        "hours": "116348",
        "base_amount": "60553621.36",
        "budgeted_amount": "60553621.36",
        "reestimated_amount": "60553621.36",
        "inflated_amount": "62862868.14",
    }
    assert len(items) == 6_000
    assert all(node["row_number"] == rank for rank, node in enumerate(items, start=1))

    def row(number: int) -> Node:
        return items[number - 1]

    def task(number: int) -> dict[str, Any]:
        return cast("dict[str, Any]", row(number)["task"])

    def follows(number: int, before: int) -> bool:
        link = {
            "predecessor_node_id": row(before)["node_id"],
            "predecessor_row_number": before,
            "link_type": "finish_to_start",
            "lag": {"value": "0", "unit": "d"},
        }
        return row(number)["predecessors"] == [link]

    assert (task(1)["label"], task(1)["is_summary"]) == ("Études", True)
    assert task(2)["label"] == "Études — Poste de commande"
    assert task(3)["label"] == "Préparation 1.1.1"
    assert (task(3)["progress"], task(3)["is_critical"]) == ("completed", False)
    assert row(4)["kind"] == "estimate_line"
    assert row(4)["estimate_line"]["label"] == "Heures d'ingénierie"
    assert row(4)["estimate_line"]["resource_role_id"] is not None
    assert (
        row(4)["estimate_line"]["cost_category_label"],
        row(4)["estimate_line"]["resource_role_label"],
    ) == ("Ingénierie électrique", "Ingénieur électricien")
    assert row(4)["estimate_line"]["hours"].isdigit()
    assert row(4)["computed_fields"] == []
    # A labour line takes its role and its hours, never a unit disbursement nor a payment
    # delay, nil for labour (WF-DEV-0020, §3.2.5).
    assert row(4)["editable_fields"] == [
        "estimate_line.label",
        "estimate_line.cost_category_id",
        "estimate_line.resource_role_id",
        "estimate_line.quantity",
        "estimate_line.hours",
        "estimate_line.subproject_id",
    ]
    assert row(6)["estimate_line"]["label"] == "Matériel"
    assert "estimate_line.unit_disbursement" in row(6)["editable_fields"]
    assert "estimate_line.hours" not in row(6)["editable_fields"]
    # A summary accepts its label, its description and its attachment to an order item or a
    # work package of the work breakdown (WF-PLA-0130).
    assert row(1)["editable_fields"] == [
        "task.label",
        "task.description",
        "task.order_item_id",
        "task.work_package_id",
    ]
    subordinates = [node for node in items if node["parent_id"] == row(1)["node_id"]]
    assert [(node["row_number"], node["task"]["label"]) for node in subordinates] == [
        (2, "Études — Poste de commande"),
        (201, "Études — Ligne d'essais"),
        (401, "Études — Utilités"),
    ]
    assert "task.finish" in row(1)["computed_fields"]
    dependencies = cast("dict[str, Any]", mockdata.summary_dependencies(answer))
    assert dependencies["node_id"] == row(1)["node_id"]
    assert dependencies["field"] == "task.finish"
    assert dependencies["depends_on"] == ["subordinates"]
    assert [(entry["row_number"], entry["label"]) for entry in dependencies["rows"]] == [
        (2, "Études — Poste de commande"),
        (201, "Études — Ligne d'essais"),
        (401, "Études — Utilités"),
    ]
    assert [entry["node_id"] for entry in dependencies["rows"]] == [
        node["node_id"] for node in subordinates
    ]
    assert (task(22)["label"], task(22)["progress"]) == ("Réalisation 1.1.4", "started")
    assert follows(22, 3)
    assert task(453)["label"] == "Préparation 1.3.9"
    assert (task(453)["progress"], task(453)["is_critical"]) == ("not_started", True)
    assert follows(453, 434)
    assert (task(6_000)["label"], task(6_000)["is_milestone"]) == ("Fin du lot 10.3", True)
    assert {node["task"]["scheduling_mode"] for node in tasks(items)} == {"automatic"}


def test_a_breakdown_gives_what_rounding_leaves_to_the_largest_part() -> None:
    parts = mockstructure.breakdown(
        [("a", Decimal(1)), ("b", Decimal(1)), (None, Decimal(1))],
        Decimal(3),
        {"a": "A", "b": "B"},
    )
    computable = mockstructure.computable
    assert parts == [
        {"key": "a", "label": "A", "amount": computable("1.00"), "share": computable("0.3334")},
        {"key": "b", "label": "B", "amount": computable("1.00"), "share": computable("0.3333")},
        {"key": "unassigned", "amount": computable("1.00"), "share": computable("0.3333")},
    ]


def test_a_drawn_value_depends_on_its_key_alone() -> None:
    assert mockstructure.draw("duration/1.1.1", 3, 12) == mockstructure.draw(
        "duration/1.1.1", 3, 12
    )
    values = {mockstructure.draw(f"duration/{n}", 3, 12) for n in range(200)}
    assert values == set(range(3, 13))


def test_exact_decimals_are_written_as_the_contract_carries_them() -> None:
    assert mockstructure.money(Decimal(1000)) == "1000.00"
    assert mockstructure.decimal(Decimal("12.50")) == "12.5"
    assert mockstructure.decimal(Decimal(40)) == "40"
    assert mockstructure.working_day(5) == date(2026, 3, 9)
    assert mockstructure.working_offset(date(2026, 3, 16)) == 10
