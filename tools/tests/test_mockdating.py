# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the dating and the pricing of the core of the witness (``wftools.mockdating``).

They try the simplifications of the fake back against the figures of the witness, not the Vérif
of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune exigence »).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest
from witnessreadings import (
    ACCEPTANCE,
    BLOCKS,
    COMMISSIONING,
    CONTROL_STATION,
    DESKS,
    DETAILED_STUDIES,
    FILE,
    LABOUR,
    MILESTONE,
    MOUNTING,
    OCCURRED,
    PROVISION,
    REMINDER,
    REVIEW,
    STUDIES,
    TRANSPORT,
    WIRING,
    Node,
    facet,
    nodes,
)

from wftools import (
    mockcore,
    mockdating,
    mockstructure,
    mockwitness,
    mockwrites,
)
from wftools.mockwitness import Line, Task


def test_a_labour_line_is_priced_by_its_hours_and_the_rate_of_the_reference_year(
    readings: dict[str, Any],
) -> None:
    estimate = nodes(readings["nodes_estimate.json"])
    labour, blocks, provision = (facet(estimate[n]) for n in (LABOUR, BLOCKS, PROVISION))
    assert (labour["hours"], labour["unit_disbursement"]) == ("12.5", None)
    assert labour["base_amount"] == "1000.00"
    assert labour["resource_role_label"] == "Ingénieur électricien"
    assert (blocks["unit_disbursement"], blocks["base_amount"]) == ("1234.56", "1234.56")
    # Neither amount is entered; a labour line enters its role and its hours, not a
    # disbursement; another its disbursement, not hours; a provision none of them, nor its
    # nature: its quantity and its disbursement come from its risk, and its subproject is the one
    # its risk designates (EP-14/L42p, revue 1); nor a payment delay, which it does not carry
    # (WF-DEV-0020, EP-14/L42s).
    for node in estimate.values():
        assert not any("amount" in name for name in node["editable_fields"]), node["node_id"]
    assert "estimate_line.hours" in estimate[LABOUR]["editable_fields"]
    assert "estimate_line.unit_disbursement" not in estimate[LABOUR]["editable_fields"]
    assert "estimate_line.hours" not in estimate[BLOCKS]["editable_fields"]
    assert estimate[PROVISION]["editable_fields"] == ["estimate_line.label"]
    assert estimate[PROVISION]["computed_fields"] == [
        "estimate_line.quantity",
        "estimate_line.unit_disbursement",
        "estimate_line.subproject_id",
    ]
    assert (provision["is_computed"], provision["base_amount"]) == (True, "500000.00")
    # The provision of 751 today, 1,250,000 at 40 %, budgeted at the 250,000 the reference 101
    # knew — 1,000,000 at 25 % — which the reserve for risks counts, never the reference budget
    # (WF-RIS-0050): the budgeted total of the wiring is 252,234.56, not the 502,234.56 of its
    # lines (751 at the scale of the structure, EP-14/L45b).
    assert provision["budgeted_amount"] == str(mockwitness.REFERENCE_PROVISION_751)
    # The last review before the reference 101 was marked (1 February) is what justifies it.
    reviews = cast("list[dict[str, str]]", mockwitness.fixture("risk_reviews"))
    before = [
        review
        for review in reviews
        if date.fromisoformat(review["reviewed_on"]) <= mockwitness.AMENDMENT_MERGED.on
    ]
    known = max(before, key=lambda review: review["reviewed_on"])
    assert Decimal(known["severity"]) * Decimal(known["probability"]) == Decimal("250000.00")
    assert facet(estimate[WIRING])["budgeted_amount"] == "252234.56"


def test_the_progress_is_read_at_the_day_given() -> None:
    # Read in the middle of April, the same tree tells where it was then.
    # The reception of the studies is declared completed by a gesture made on 24 April: before it,
    # nothing completes it by itself (WF-RAE-0030).
    then = {row.number: facet(row.node) for row in mockcore.core(today=date(2026, 4, 15))}
    assert then[DETAILED_STUDIES]["progress"] == "completed"
    assert then[REVIEW]["progress"] == "started"
    assert then[ACCEPTANCE]["progress"] == "not_started"
    after = {row.number: facet(row.node) for row in mockcore.core(today=date(2026, 4, 24))}
    assert after[ACCEPTANCE]["progress"] == "completed"
    assert then[WIRING]["progress"] == "not_started"
    assert "started_on" not in then[WIRING]
    # A started task past its finish is overdue; the desks, declared started, already were.
    assert then[DESKS]["finish_overdue"] is False


def test_the_critical_path_and_the_float_follow_the_links_of_the_core(
    readings: dict[str, Any],
) -> None:
    planning = nodes(readings["nodes_planning.json"])
    estimate = nodes(readings["nodes_estimate.json"])
    tasks = {**planning, **estimate}
    installation = nodes(readings["nodes_installation.json"])
    tasks = {**tasks, **installation}
    critical = [n for n, node in tasks.items() if facet(node).get("is_critical")]
    # The core is linked to the tasks drawn about it (#376): the lots of the control station
    # follow its factory acceptance, on the critical path of the whole structure, which ends in
    # August 2029; the installation on site leads to the commissioning of the control station.
    assert critical == [DETAILED_STUDIES, REVIEW, ACCEPTANCE, WIRING, MILESTONE]
    assert all(facet(tasks[n])["total_float"] == {"value": "0", "unit": "d"} for n in critical)
    assert facet(installation[MOUNTING])["total_float"] == {"value": "597.5", "unit": "d"}
    assert facet(installation[COMMISSIONING])["total_float"] == {"value": "597.5", "unit": "d"}
    # The design file, without a successor, may wait for the end of the whole structure.
    assert facet(planning[FILE])["total_float"] == {"value": "880.5", "unit": "d"}
    assert facet(installation[COMMISSIONING])["finish"] == {"date": "2027-01-01", "hours": "8"}
    assert facet(planning[FILE])["start"] == {"date": "2026-04-09", "hours": "0"}
    # A task in manual mode shows no float and is never critical; its successor is.
    assert (facet(planning[DESKS])["total_float"], facet(planning[DESKS])["is_critical"]) == (
        None,
        False,
    )
    assert planning[DESKS]["computed_fields"] == []
    assert {"task.start", "task.finish"} <= set(planning[DESKS]["editable_fields"])
    # The two tasks of the occurrence, in parallel with the wiring, may wait for the end too.
    assert facet(estimate[REMINDER])["total_float"] == {"value": "858.5", "unit": "d"}
    assert facet(estimate[TRANSPORT])["total_float"] == {"value": "858.5", "unit": "d"}


def test_the_physical_progress_of_a_summary_is_the_budget_of_its_completed_tasks(
    readings: dict[str, Any],
) -> None:
    planning = nodes(readings["nodes_planning.json"])
    estimate = nodes(readings["nodes_estimate.json"])
    # The whole budget of the studies is on the detailed studies, completed; nothing of the
    # control station's is on a completed task; the occurrence has no budget at all.
    assert facet(planning[STUDIES])["physical_progress"] == mockstructure.computable("1")
    assert facet(estimate[CONTROL_STATION])["physical_progress"] == mockstructure.computable("0")
    assert facet(estimate[OCCURRED])["physical_progress"] == {
        "is_computable": False,
        "value": None,
        "reason": "no_budgeted_amount",
    }
    assert "physical_progress" not in facet(planning[DETAILED_STUDIES])


def test_a_line_without_hours_nor_disbursement_cannot_be_priced() -> None:
    with pytest.raises(ValueError, match="the line 999 has neither hours nor a unit disbursement"):
        mockdating.price(Line(999, "Rien", mockwitness.EQUIPMENT), 2026)
    with pytest.raises(ValueError, match="a line is borne by a task"):
        _ = mockcore.Place(None, 0, 1, 1).bearing


def test_the_core_is_dated_in_the_order_of_its_links_whatever_the_order_of_the_plan(
    readings: dict[str, Any],
) -> None:
    # The review linked to the design file too, a predecessor further down the plan: dated after
    # it, it starts after the design file finishes, 15 April, and names it by its row.
    review = next(task for task in mockdating.tasks_in_order() if task.number == REVIEW)
    roots = mockwrites.amended(
        mockwitness.CORE,
        mockwrites.on_task(REVIEW, links=(*review.links, mockwitness.Link(FILE))),
    )
    dated = mockdating.schedule(roots)
    assert dated[FILE].finish.day == date(2026, 4, 15)
    assert dated[REVIEW].start.day > dated[FILE].finish.day
    node = next(row.node for row in mockcore.core(roots) if row.number == REVIEW)
    links = cast("list[dict[str, Any]]", node["predecessors"])
    assert [link["predecessor_row_number"] for link in links] == [2, 7]
    # Unlinked, the order of the plan stands; the whole reading gives every row and the totals.
    order = [task.number for task in mockdating.in_link_order(mockdating.tasks_in_order())]
    assert order == [task.number for task in mockdating.tasks_in_order()]
    whole = readings["nodes_core.json"]
    assert [item["row_number"] for item in whole["items"]] == list(range(1, 25))
    assert whole["totals"]["task_count"] == 15


def test_a_task_in_manual_mode_bounds_its_predecessors_whose_float_may_be_negative() -> None:
    # WF-PLA-0100 (#402, #464): a date entered by hand downstream bounds its predecessors. The
    # task of five days from 2 March finishes on Friday 6 March; its successor, set by hand to
    # start on Wednesday 4 March, asks it to finish by Tuesday evening: three days late, critical.
    first = Task(1, "Préparation", days=5)
    imposed = Task(
        2,
        "Livraison imposée",
        days=5,
        links=(mockwitness.Link(1),),
        manual=(date(2026, 3, 4), date(2026, 3, 10)),
        progress="not_started",
    )
    rows = mockcore.core([Task(3, "Lot", children=(first, imposed))])
    tasks = {row.number: cast("Node", row.node["task"]) for row in rows}
    assert tasks[1]["finish"] == {"date": "2026-03-06", "hours": "8"}
    assert tasks[1]["total_float"] == {"value": "-3", "unit": "d"}
    assert tasks[1]["is_critical"] is True
    # The task entered by hand shows no float itself.
    assert (tasks[2]["total_float"], tasks[2]["is_critical"]) == (None, False)


def test_a_task_of_another_year_is_corrected_for_inflation() -> None:
    # A line consumed two years after the reference year, at 3 %: 1.03 x 1.03 its amount.
    later = Task(
        591,
        "Plus tard",
        days=1,
        manual=(date(2028, 1, 3), date(2028, 1, 3)),
        progress="not_started",
        lines=(Line(592, "Matériel", mockwitness.EQUIPMENT, unit=Decimal("100.00")),),
    )
    [task, line] = mockcore.core((later,))
    assert facet(line.node)["consumption_year"] == 2028
    assert (facet(line.node)["base_amount"], facet(line.node)["inflated_amount"]) == (
        "100.00",
        "106.09",
    )
    assert facet(task.node)["inflated_amount"] == "106.09"
    assert mockdating.price(later.lines[0], 2028).inflated == Decimal("106.09")


def test_a_quantity_is_an_exact_decimal_in_the_amount_of_a_line() -> None:
    # A quantity of 2.5 times a disbursement of 100: 250 exactly.
    line = Line(
        1, "Location", mockwitness.EQUIPMENT, unit=Decimal("100.00"), quantity=Decimal("2.5")
    )
    assert mockdating.price(line, 2026).base == Decimal(250)


def test_a_summary_is_dated_on_the_calendar_of_its_own_lines_not_on_its_subordinates() -> None:
    # #1410, WF-PLA-0040: a summary spans its subordinates, but its duration is the work between
    # its dates on its own applicable calendar, which its labour lines give (WF-PLA-0010). The
    # laying of three days on the standard week runs from Monday 2 March to Wednesday evening; the
    # lot above it, which bears a line of the cable fitter, four days of ten hours, spans the same
    # dates, but counts 10 + 10 + 8 hours on its own calendar: three days and a half.
    laying = Task(1, "Pose", days=3)
    supervision = Line(
        2,
        "Encadrement",
        mockwitness.ELECTRICAL_ENGINEERING,
        hours=Decimal(10),
        role=mockwitness.CABLE_FITTER,
    )
    lot = Task(3, "Lot", children=(laying,), lines=(supervision,))
    tasks = {row.number: facet(row.node) for row in mockcore.core([lot]) if row.kind == "task"}
    assert (tasks[3]["start"], tasks[3]["finish"]) == (tasks[1]["start"], tasks[1]["finish"])
    assert tasks[1]["duration"] == {"value": "3", "unit": "d"}
    assert tasks[3]["duration"] == {"value": "3.5", "unit": "d"}
    four_days = {
        **dict.fromkeys(("monday", "tuesday", "wednesday", "thursday"), "10"),
        **dict.fromkeys(("friday", "saturday", "sunday"), "0"),
    }
    standard = {**dict.fromkeys(("monday", "tuesday", "wednesday", "thursday", "friday"), "8")}
    standard |= {"saturday": "0", "sunday": "0"}
    assert (tasks[3]["calendar_hours"], tasks[1]["calendar_hours"]) == (four_days, standard)
