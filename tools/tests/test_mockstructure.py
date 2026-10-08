# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the structure of a thousand tasks the fake back serves, and of its indicators.

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

import json
import re
from collections import Counter
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockcore, mockdata, mockids, mockstructure, mockwitness
from wftools.mockcalendar import Calendar, Instant
from wftools.mockids import PREFIX
from wftools.mockwitness import GENERATED, N

MONEY = re.compile(r"^\d+\.\d{2}$")
TODAY = mockwitness.TODAY.date().isoformat()

type Node = dict[str, Any]


@pytest.fixture(scope="module")
def answer() -> dict[str, Any]:
    """Make the structure once, as the JSON the fake back serves."""
    return cast("dict[str, Any]", json.loads(json.dumps(mockcore.whole(mockcore.current()))))


@pytest.fixture(scope="module")
def items(answer: dict[str, Any]) -> list[Node]:
    """Read the nodes of the structure of a thousand tasks."""
    return cast("list[Node]", answer["items"])


def tasks(items: list[Node]) -> list[Node]:
    return [node for node in items if node["kind"] == "task"]


def lines(items: list[Node]) -> list[Node]:
    return [node for node in items if node["kind"] == "estimate_line"]


def drawn(nodes: list[Node]) -> list[Node]:
    """Return the nodes drawn about the core: those of the generated family."""
    return [node for node in nodes if not node["node_id"].startswith(PREFIX + "0000")]


def by_id(items: list[Node]) -> dict[str, Node]:
    return {node["node_id"]: node for node in items}


def children(items: list[Node], parent: Node) -> list[Node]:
    return [node for node in items if node["parent_id"] == parent["node_id"]]


def instant(value: dict[str, str]) -> Instant:
    return Instant(date.fromisoformat(value["date"]), Decimal(value["hours"]))


def calendar_of(items: list[Node], task: Node) -> Calendar:
    """Return the calendar of a task drawn: the cable fitter's, or the standard week."""
    roles = {line["estimate_line"]["resource_role_id"] for line in children(items, task)}
    calendars = mockwitness.calendars()
    if roles & {mockwitness.CABLE_FITTER}:
        return calendars[mockwitness.FOUR_DAY_WEEK]
    return calendars[mockwitness.STANDARD_WEEK]


def test_a_thousand_tasks_carry_five_thousand_lines(answer: dict[str, Any]) -> None:
    assert len(tasks(answer["items"])) == 1_000
    assert len(lines(answer["items"])) == 5_000
    assert answer["totals"]["task_count"] == 1_000
    assert answer["totals"]["estimate_line_count"] == 5_000


def test_the_core_comes_first_as_its_readings_give_it(items: list[Node]) -> None:
    # The readable core is incrusted at the head of the structure (#376): its rows are its first
    # rows, its nodes those of its readings, down to their float and their amounts.
    core = mockcore.rows_of(mockwitness.CORE)
    assert sorted(core.values()) == list(range(1, 25))
    readings = [
        mockwitness.fixture(name)["items"]
        for name in ("nodes", "nodes_estimate", "nodes_installation")
    ]
    read = {node["node_id"]: node for reading in readings for node in reading}
    assert [node["node_id"] for node in items[:24]] == list(read)
    assert all(node == read[node["node_id"]] for node in items[:24])
    assert all(node["node_id"].startswith(PREFIX + "0001") for node in items[24:])


def test_the_tasks_drawn_are_linked_to_the_core(items: list[Node]) -> None:
    # The lots of the control station follow the factory acceptance, the others the reception of
    # the studies; the commissioning of the core leads to the commissioning of the control
    # station: the core's float and critical path are those of the whole structure.
    followers: dict[str, list[str]] = {}
    for node in tasks(items):
        for link in node.get("predecessors", []):
            followers.setdefault(link["predecessor_node_id"], []).append(node["task"]["label"])
    universe = mockids.universe
    assert followers[universe(N.FACTORY_ACCEPTANCE)] == [
        "Montage des armoires sur site",
        "Préparation 1.1.1",
        "Conception 1.1.2",
        "Revue 1.1.3",
    ]
    assert followers[universe(N.STUDIES_RECEIVED)] == [
        "Câblage des armoires",
        "Préparation 1.2.1",
        "Conception 1.2.2",
        "Revue 1.2.3",
        "Préparation 1.3.1",
        "Conception 1.3.2",
        "Revue 1.3.3",
    ]
    assert followers[universe(N.COMMISSIONING)] == ["Fin du lot 8.1"]


def test_the_work_tasks_drawn_carry_five_lines_and_some_a_sixth(items: list[Node]) -> None:
    work = [
        node
        for node in drawn(tasks(items))
        if not node["task"]["is_summary"] and not node["task"]["is_milestone"]
    ]
    assert len(work) == 922
    counts = Counter(len(children(items, node)) for node in work)
    assert counts == {5: 922 - 381, 6: 381}
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
    # A node drawn is named by its row as described, in its family: identifiers that a write
    # adding or removing a row above leaves as they are.
    for node in drawn(items):
        assert int(node["node_id"][-8:]) == node["row_number"]
        assert node["lineage_id"] == mockwitness.lineage_id(GENERATED + node["row_number"])


def test_positions_count_the_siblings_of_one_parent(items: list[Node]) -> None:
    siblings: dict[str | None, list[int]] = {}
    for node in items:
        siblings.setdefault(node["parent_id"], []).append(node["position"])
    assert all(positions == list(range(len(positions))) for positions in siblings.values())


def test_a_line_drawn_is_priced_exactly_and_paid_by_its_nature(items: list[Node]) -> None:
    for node in drawn(lines(items)):
        line = node["estimate_line"]
        assert MONEY.match(line["base_amount"])
        assert line["base_amount"] == line["budgeted_amount"] == line["reestimated_amount"]
        if line["hours"] is None:
            expected = Decimal(line["quantity"]) * Decimal(line["unit_disbursement"])
            # The other lines are paid a month after their work, labour as it is worked.
            assert line["payment_delay_days"] == mockwitness.PAYMENT_DELAY
        else:
            assert line["resource_role_id"] is not None
            rate = mockcore.LABOUR_RATES[line["cost_category_id"]]
            expected = Decimal(line["quantity"]) * Decimal(line["hours"]) * rate
            assert line["payment_delay_days"] == 0
        assert Decimal(line["base_amount"]) == expected
        # Drawn, a line was in the reference as it is: its previous review is itself.
        assert line["previous_quantity"] == line["quantity"]
        assert line["previous_reestimated_amount"] == line["reestimated_amount"]


@pytest.mark.parametrize(
    "amount", ["base_amount", "budgeted_amount", "reestimated_amount", "inflated_amount"]
)
def test_a_task_sums_the_lines_under_it_and_the_totals_all_of_them(
    answer: dict[str, Any], items: list[Node], amount: str
) -> None:
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
    assert Decimal(totals[amount]) == sum(Decimal(n["estimate_line"][amount]) for n in lines(items))
    hours = [Decimal(node["estimate_line"]["hours"] or 0) for node in lines(items)]
    assert Decimal(totals["hours"]) == sum(hours)


def test_a_task_drawn_lasts_its_hours_on_the_calendar_of_its_roles(items: list[Node]) -> None:
    # WF-PLA-0010, WF-PLA-0160: the duration in days of eight hours, placed hour after hour on the
    # calendar of the roles of its labour lines — the wiring on the cable fitter's week of four
    # days of ten hours, never a Friday.
    on_four_days = 0
    for node in drawn(tasks(items)):
        task = node["task"]
        if task["is_summary"]:
            continue
        calendar = calendar_of(items, node)
        start, finish = instant(task["start"]), instant(task["finish"])
        worked = calendar.work_between(start, finish)
        assert worked == Decimal(task["duration"]["value"]) * 8
        if task["is_milestone"]:
            assert start == finish
        if calendar.calendar_id == mockwitness.FOUR_DAY_WEEK:
            on_four_days += 1
            assert start.day.weekday() < 4
            assert finish.day.weekday() < 4
    assert on_four_days == 103


def test_a_task_starts_where_its_predecessors_finish(items: list[Node]) -> None:
    nodes = by_id(items)
    for node in drawn(tasks(items)):
        task = node["task"]
        if task["is_summary"]:
            continue
        links = node["predecessors"]
        for link in links:
            assert (
                link["predecessor_row_number"] == nodes[link["predecessor_node_id"]]["row_number"]
            )
            assert (link["link_type"], link["lag"]) == (
                "finish_to_start",
                {"value": "0", "unit": "d"},
            )
        calendar = calendar_of(items, node)
        latest = max(
            calendar.elapsed(instant(nodes[link["predecessor_node_id"]]["task"]["finish"]))
            for link in links
        )
        assert calendar.elapsed(instant(task["start"])) == latest


def test_a_summary_spans_its_subordinates(items: list[Node]) -> None:
    for node in tasks(items):
        task = node["task"]
        if not task["is_summary"]:
            continue
        below = [child["task"] for child in children(items, node) if child["kind"] == "task"]
        assert instant(task["start"]) == min(instant(child["start"]) for child in below)
        assert instant(task["finish"]) == max(instant(child["finish"]) for child in below)
        assert "total_float" not in task
        # Its physical progress, as the core's summaries give it (WF-IND-0060, #370).
        assert "physical_progress" in task


def test_the_critical_path_runs_through_the_core_to_the_last_finish(items: list[Node]) -> None:
    work = [node for node in tasks(items) if not node["task"]["is_summary"]]
    automatic = [node["task"] for node in work if node["task"]["scheduling_mode"] == "automatic"]
    last = max(instant(task["finish"]) for task in automatic)
    assert last.day == date(2029, 8, 30)
    assert all(Decimal(task["total_float"]["value"]) >= 0 for task in automatic)
    assert all(
        task["is_critical"] == (Decimal(task["total_float"]["value"]) == 0) for task in automatic
    )
    assert all(task["is_critical"] for task in automatic if instant(task["finish"]) == last)
    critical = [node["task"]["label"] for node in work if node["task"]["is_critical"]]
    assert critical[:5] == [
        "Études de détail",
        "Revue de conception",
        "Réception des études",
        "Câblage des armoires",
        "Réception usine",
    ]
    assert 0 < len(critical) < len(work)


def test_progress_is_that_of_today_and_nothing_completes_by_itself(items: list[Node]) -> None:
    nodes = by_id(items)
    for node in drawn(tasks(items)):
        task = node["task"]
        if task["is_summary"]:
            continue
        if task["progress"] == "completed":
            assert task["finish"]["date"] < TODAY
            assert task["completed_on"] == task["finish"]["date"]
        elif task["progress"] == "started":
            assert task["start"]["date"] <= TODAY <= task["finish"]["date"]
        elif not task["is_milestone"]:
            assert task["start"]["date"] > TODAY
        # A milestone is completed by a gesture alone (WF-RAE-0030): none drawn is.
        if task["is_milestone"]:
            assert task["progress"] == "not_started"
    states = Counter(node["task"]["progress"] for node in drawn(tasks(items)))
    assert states == {"not_started": 955, "completed": 21, "started": 9}
    for node in lines(items):
        completed = nodes[node["parent_id"]]["task"]["progress"] == "completed"
        entry = node["estimate_line"]["remaining_entry"]
        assert entry["is_available"] is not completed


def test_a_line_is_projected_on_the_year_its_task_starts(items: list[Node]) -> None:
    nodes = by_id(items)
    for node in lines(items):
        line = node["estimate_line"]
        start = nodes[node["parent_id"]]["task"]["start"]["date"]
        assert line["consumption_year"] == int(start[:4])
        assert line["inflated_amount"] == mockstructure.money(
            mockstructure.inflated(Decimal(line["base_amount"]), line["consumption_year"])
        )


def test_the_one_provision_is_that_of_the_risk_identified(items: list[Node]) -> None:
    # A line of provision is created by the declaration of a risk alone (WF-DEV-0020,
    # WF-RIS-0010): none is drawn; the core's, of 751, is budgeted at what the reference knew.
    provisions = [node for node in lines(items) if node["estimate_line"]["is_computed"]]
    assert [node["node_id"] for node in provisions] == [mockids.universe(N.PROVISION)]
    [line] = [node["estimate_line"] for node in provisions]
    assert (line["base_amount"], line["budgeted_amount"]) == ("500.00", "250.00")


def test_a_line_names_its_category_role_and_subproject_as_the_universe_does(
    items: list[Node],
) -> None:
    categories = cast("list[dict[str, str]]", mockdata.categories())
    names = {category["cost_category_id"]: category["label"] for category in categories}
    names.update(
        (role["resource_role_id"], role["label"]) for role in mockwitness.fixture("resource_roles")
    )
    names.update(
        (entry["subproject_id"], entry["label"]) for entry in mockwitness.fixture("subprojects")
    )
    for node in lines(items):
        line = node["estimate_line"]
        for key in ("cost_category", "resource_role", "subproject"):
            identifier = line[f"{key}_id"]
            assert line[f"{key}_label"] == (None if identifier is None else names[identifier])


def test_the_marks_the_journeys_read(answer: dict[str, Any], items: list[Node]) -> None:
    # The end-to-end paths of the front read the structure by these rows (grid.spec.ts,
    # planning.spec.ts, entry.spec.ts, keyboard.spec.ts, paste.spec.ts, computed.spec.ts), and the
    # refusal of computed.spec.ts what summary_dependencies.json says of row 1: a change of the
    # generator that moves them fails here. Those of the core are in the window as the grid
    # opens; the others are scrolled to.
    assert answer["totals"] == {
        "task_count": 1_000,
        "estimate_line_count": 5_000,
        "hours": "116270",
        "base_amount": "65605723.89",
        "budgeted_amount": "65604973.89",
        "reestimated_amount": "65605723.89",
        "inflated_amount": "68424191.06",
    }

    def row(number: int) -> Node:
        return items[number - 1]

    def task(number: int) -> dict[str, Any]:
        return cast("dict[str, Any]", row(number)["task"])

    def line(number: int) -> dict[str, Any]:
        return cast("dict[str, Any]", row(number)["estimate_line"])

    assert (task(1)["label"], task(1)["is_summary"]) == ("Études", True)
    subordinates = [
        (entry["row_number"], entry["label"])
        for entry in cast("dict[str, Any]", mockdata.summary_dependencies(answer))["rows"]
    ]
    assert subordinates == [
        (2, "Études de détail"),
        (4, "Pupitres opérateurs"),
        (5, "Revue de conception"),
        (6, "Réception des études"),
        (7, "Dossier de conception"),
    ]
    # Row 7, completed off the critical path, its bar from 9 to 15 April.
    assert (task(7)["label"], task(7)["progress"], task(7)["is_critical"]) == (
        "Dossier de conception",
        "completed",
        False,
    )
    assert (task(7)["start"]["date"], task(7)["finish"]["date"]) == ("2026-04-09", "2026-04-15")
    # Row 10, the labour of the core; row 12, its provision, whose quantity and unit
    # disbursement the server computes.
    assert (line(10)["label"], line(10)["hours"]) == ("Raccordement des borniers", "12.5")
    assert line(12)["is_computed"] is True
    assert row(12)["editable_fields"] == [
        "estimate_line.label",
        "estimate_line.payment_delay_days",
        "estimate_line.subproject_id",
    ]
    # Row 13, a summary of the second level, folds over rows 14 to 17, before the milestone of row
    # 18; row 14, a task of the third level with its dates, over its line, row 15, before its
    # sibling of row 16.
    assert [
        (row(n)["level"], (row(n).get("task") or row(n)["estimate_line"])["label"])
        for n in (13, 14, 15, 16, 18)
    ] == [
        (2, "Risque survenu — Retard de livraison des armoires"),
        (3, "Relance du fournisseur"),
        (4, "Frais de relance"),
        (3, "Transport exceptionnel"),
        (2, "Réception usine"),
    ]
    assert task(13)["is_summary"] is True
    assert task(14)["start"] is not None
    assert [row(n)["parent_id"] for n in (14, 15, 16, 17, 18)] == [
        row(13)["node_id"],
        row(14)["node_id"],
        row(13)["node_id"],
        row(16)["node_id"],
        row(13)["parent_id"],
    ]
    # Row 25, the first phase drawn; rows 28 to 30, the first lines drawn, where a label is
    # entered and a block pasted.
    assert (task(25)["label"], task(26)["label"], task(27)["label"]) == (
        "Approvisionnements",
        "Approvisionnements — Poste de commande",
        "Préparation 1.1.1",
    )
    assert row(28)["node_id"] == mockwitness.node_id(GENERATED + 28)
    assert [line(number)["label"] for number in (28, 29, 30)] == [
        "Heures d'ingénierie",
        "Heures de mise en service",
        "Matériel",
    ]
    assert (line(28)["hours"], line(28)["base_amount"], line(28)["subproject_label"]) == (
        "74.5",
        "5960.00",
        "Poste de commande",
    )
    assert (line(28)["cost_category_label"], line(28)["resource_role_label"]) == (
        "Ingénierie électrique",
        "Ingénieur électricien",
    )
    assert row(28)["editable_fields"] == [
        "estimate_line.label",
        "estimate_line.cost_category_id",
        "estimate_line.resource_role_id",
        "estimate_line.quantity",
        "estimate_line.hours",
        "estimate_line.subproject_id",
    ]
    # Row 39, of the critical path, not started, after the factory acceptance of row 18; row 311,
    # started, after row 291.
    assert (task(39)["label"], task(39)["progress"], task(39)["is_critical"]) == (
        "Revue 1.1.3",
        "not_started",
        True,
    )
    assert [link["predecessor_row_number"] for link in row(39)["predecessors"]] == [18]
    assert (task(39)["start"]["date"], task(39)["finish"]["date"]) == ("2026-07-01", "2026-07-16")
    assert (task(311)["label"], task(311)["progress"]) == ("Revue 1.2.11", "started")
    assert [link["predecessor_row_number"] for link in row(311)["predecessors"]] == [291]
    assert (task(6_000)["label"], task(6_000)["is_milestone"]) == ("Fin du lot 9.3", True)


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
