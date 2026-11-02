# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the curves and the indicators of the witness against their requirements (US-0701/L5).

They try the contract and its examples, not the service, which EP-08 to EP-11 write: the curves of
a project at the pace of the month, each point the cumulative amount at the end of its month, the
day of the calculation one point more on the series that stop or start there (WF-IND-0100,
WF-IND-0110, WF-DAT-0040); the indicators of the day of a project without a current revision,
computed on its last marked revision with the actual cost of the day (WF-IND-0010); the
disbursements, the actual cost not shifted and the remaining spread after the day of the
calculation (WF-IND-0100); the gap to the previous review, a revision marked In progress
(WF-RAE-0020); the time/time chart (WF-IND-0090); the physical progress of a summary, out of the
lines of provision (WF-IND-0060).
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockcore, mockcurves, mockdata, mockhistory, mockindicators, mocktoday
from wftools.mockcalendar import Instant
from wftools.mockindicators import END_OF_DAY, Cost
from wftools.mockwitness import PROVISIONS, SUBCONTRACTING, TODAY, Line, Task

type Node = dict[str, Any]

CURVES = (
    "cost_curve",
    "cost_curve_payment_delays",
    "cost_curve_amendment",
    "cost_curve_subproject",
    "cost_curve_subproject_unbudgeted",
    "earned_value_curves",
)
"""The examples of the curves of the witness that draw something."""

STOPPING = {"actual_cost", "earned_value", "project_manager_projection"}
"""The series that stop or start at the day of the calculation: it is one point more on them."""


@pytest.fixture(scope="module")
def today() -> dict[str, Any]:
    """Read the examples of the indicators back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mocktoday.examples().items()
    }


def _is_month_end(day: date) -> bool:
    return mockcurves.month_end(day) == day


@pytest.mark.requirement("WF-IND-0100-A")
@pytest.mark.requirement("WF-IND-0110-A")
@pytest.mark.parametrize("name", CURVES)
def test_each_point_of_a_curve_is_the_cumulative_amount_at_the_end_of_its_month(
    today: dict[str, Any], name: str
) -> None:
    # « Les courbes se calculent et se présentent au pas du mois, chaque point portant le cumul à
    # la fin du mois » : every point is the end of a month, but the day of the calculation on the
    # series that stop or start there, and the two points of an amendment at its day.
    curve = today[name]
    steps = {step["date"] for step in curve["steps"]}
    for series in curve["series"]:
        dates = [point["date"] for point in series["points"]]
        assert dates == sorted(dates), (name, series["name"])
        for each in dates:
            day = date.fromisoformat(each)
            if _is_month_end(day) or each in steps:
                continue
            assert series["name"] in STOPPING, (name, series["name"], each)
            assert day == TODAY.date(), (name, series["name"], each)
        # Each month once: twice only at the day of a step, before and after it.
        assert all(dates.count(each) == 1 or each in steps for each in dates), name


@pytest.mark.requirement("WF-IND-0110-A")
def test_a_task_completed_steps_the_earned_value_at_the_point_of_its_month(
    today: dict[str, Any],
) -> None:
    # « Une tâche terminée produit une marche dans la valeur acquise au point du mois de sa date de
    # terminaison » : the detailed studies, completed on 10 April, are earned at the end of April,
    # not before.
    earned = {
        point["date"]: Decimal(point["amount"])
        for series in today["earned_value_curves"]["series"]
        if series["name"] == "earned_value"
        for point in series["points"]
    }
    assert earned["2026-03-31"] == 0
    assert earned["2026-04-30"] == mockindicators.earned(mockindicators.today(), date(2026, 4, 30))
    assert earned["2026-04-30"] > 0


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_actual_cost_stops_at_the_day_of_the_calculation_where_the_projection_starts(
    today: dict[str, Any],
) -> None:
    # « Celle du coût réel s'arrête à la date de calcul, et la projection part de ce point pour
    # atteindre la projection du chef de projet. »
    curve = {series["name"]: series["points"] for series in today["cost_curve"]["series"]}
    project = today["project_indicators"]
    assert curve["actual_cost"][-1] == curve["project_manager_projection"][0]
    assert curve["actual_cost"][-1] == {"date": "2026-06-03", "amount": project["actual_cost"]}
    assert (
        curve["project_manager_projection"][-1]["amount"]
        == (project["projections"]["project_manager"])
    )
    assert curve["reference_budget"][-1]["amount"] == project["reference_budget"]


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_project_without_a_current_revision_has_indicators_of_the_day_on_its_last_marked(
    today: dict[str, Any],
) -> None:
    # « Lorsque le projet ne comporte pas de révision en cours, ses indicateurs au jour courant se
    # calculent sur sa dernière révision marquée, avec le coût réel au jour courant » : not kept,
    # the revision named, its status marked.
    latest, kept = (
        today["project_indicators_without_current_revision"],
        today["project_indicators_marked"],
    )
    assert latest["context"] == {
        "revision_id": mockhistory.REFERENCE,
        "revision_status": "marked",
        "computed_at": "2026-06-03T14:05:00Z",
        "scope": "project",
        "is_stored": False,
    }
    assert kept["context"]["is_stored"] is True
    assert latest["actual_cost"] == today["project_indicators"]["actual_cost"]
    assert latest["reference_budget"] == kept["reference_budget"]
    assert latest["remaining"] == kept["remaining"]
    assert kept["actual_cost"] == "0.00"


@pytest.mark.requirement("WF-IND-0010-A")
def test_an_import_of_actual_costs_changes_the_day_and_leaves_the_kept_indicators_unchanged() -> (
    None
):
    # « Sur un projet sans révision en cours, un import de coûts réels change les indicateurs au
    # jour courant et laisse inchangés ceux conservés de la dernière révision marquée. »
    witness = mocktoday.witness()
    base = witness.reference
    # An invoice of today, imported today: after the marking of the reference, 1 February.
    imported = [*witness.costs, Cost(date(2026, 6, 3), Decimal("1000.00"), None)]
    before: Node = mockindicators.project_indicators(
        mockindicators.latest_today(base), base, witness.costs
    )
    after: Node = mockindicators.project_indicators(
        mockindicators.latest_today(base), base, imported
    )
    assert Decimal(after["actual_cost"]) - Decimal(before["actual_cost"]) == Decimal("1000.00")
    kept: Node = mockindicators.project_indicators(base, base, imported)
    assert kept == mockindicators.project_indicators(base, base, witness.costs)
    assert kept["context"]["is_stored"] is True
    assert mockindicators.latest_today(base).is_stored is False


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_actual_cost_of_the_disbursements_is_not_shifted(today: dict[str, Any]) -> None:
    # « Le coût réel n'est pas décalé » : the same series with the payment delays as without.
    def actual(name: str) -> list[Node]:
        return next(
            series["points"] for series in today[name]["series"] if series["name"] == "actual_cost"
        )

    assert actual("cost_curve_payment_delays") == actual("cost_curve")


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_remaining_of_a_task_past_its_finish_is_whole_at_the_day_of_the_calculation() -> None:
    # « porté entier à la date de calcul lorsque la fin de la tâche est dépassée » ; the others
    # over the part of the duration of their task after it.
    witness = mockindicators.today()
    after = Instant(witness.day, END_OF_DAY)
    late = early = 0
    for line in witness.lines:
        amount = mockindicators.remaining_of(witness, line)
        if amount == 0:
            continue
        flow = mockcurves.ahead(witness, line, amount)
        if witness.bearer(line).finish <= after:
            late += 1
            assert flow.first == flow.last == witness.day, line.number
        else:
            early += 1
            assert flow.start >= after, line.number
    assert late
    assert early


def _points_of(example: dict[str, Any], name: str) -> list[Node]:
    return next(series["points"] for series in example["series"] if series["name"] == name)


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_origin_of_the_reference_budget_is_that_of_the_amendment_step_when_it_is_older(
    today: dict[str, Any],
) -> None:
    # « la première, à la fin du mois qui précède le premier montant — ou celui de la marche
    # d'avenant, si elle est plus ancienne » : the amendment steps the budget on 1 February 2026,
    # before the first amount of the reference in force, which the planned value starts from.
    budget = _points_of(today["cost_curve"], "reference_budget")
    planned = _points_of(today["earned_value_curves"], "planned_value")
    steps = [step["date"] for step in today["cost_curve"]["steps"]]
    assert budget[0]["date"] == "2026-01-31"
    assert planned[0]["date"] == "2026-02-28"
    assert budget[0]["date"] < planned[0]["date"]
    assert budget[0]["amount"] == planned[0]["amount"] == "0.00"
    assert steps
    assert mockcurves.month_before(date.fromisoformat(min(steps))).isoformat() == budget[0]["date"]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_provision_stays_at_the_date_of_its_task_under_the_payment_delays() -> None:
    # « une provision de risque identifié reste à sa date » : the delay of a line shifts it, not a
    # provision, placed whole at the finish of its task, or at the day of the reading when past.
    witness = mockindicators.today()
    delayed = mockcurves.remaining_flows(witness, delays=True)
    plain = mockcurves.remaining_flows(witness)
    assert any(delay for delay in witness.delays.values())
    placed = 0
    for line in witness.lines:
        amount = mockindicators.remaining_of(witness, line)
        if amount == 0 or not mockhistory.is_provision(line):
            continue
        finish = witness.bearer(line).finish.day
        at = max(finish, witness.day)
        assert any(flow.amount == amount and flow.first == flow.last == at for flow in delayed), (
            line.number
        )
        placed += 1
    assert placed
    assert len(delayed) == len(plain)


@pytest.mark.requirement("WF-IND-0030-A")
@pytest.mark.requirement("WF-IND-0020-A")
def test_the_earned_value_and_the_budget_of_a_subproject_leave_out_the_lines_of_provision() -> None:
    # « hors lignes de provision » : a provision of 50 budgeted on a task completed earns
    # nothing — two tasks completed, of 100 and 200, and one of 400 started earn 300, by a
    # structure declared here rather than by the logic of the generator (#1634) —, and a
    # provision is no part of the budget of a subproject.
    provision = Line(9019, "Provision", PROVISIONS, unit=Decimal(50), is_provision=True)
    declared = mockindicators.today(
        (
            _leaf(901, "100", "completed", provision),
            _leaf(902, "200", "completed"),
            _leaf(903, "400", "started"),
        )
    )
    assert next(line for line in declared.lines if line.number == 9019).amounts.budgeted == 50
    assert mockindicators.earned(declared, date(2099, 12, 31)) == Decimal(300)
    witness, base = mockindicators.today(), mockindicators.reference()
    for scope, label in mockindicators.scopes()[1:]:
        found = mockindicators.balance(witness, base, [], scope, label)
        assert Decimal(cast("str", found["budget"])) == sum(
            (
                line.amounts.budgeted
                for line in base.lines
                if base.in_scope(line, scope) and not mockhistory.is_provision(line)
            ),
            Decimal(0),
        )
    assert any(mockhistory.is_provision(line) for line in base.lines)


@pytest.mark.requirement("WF-RAE-0020-A")
def test_the_gap_to_the_previous_review_is_absent_after_an_offer_marked_while_pricing() -> None:
    # « Sur un projet dont aucune révision n'a été marquée à l'état En cours avant celle qui est
    # lue, l'écart correspondant est absent plutôt que nul » : the offer, marked while pricing,
    # is no review; the reference, marked In progress, is one.
    witness = mocktoday.witness()
    now, base = witness.today, witness.reference
    after_offer = mockindicators.remaining_indicators(now, base, witness.offer, witness.costs)
    assert after_offer["delta_to_previous_revision"] is None
    after_reference = mockindicators.remaining_indicators(now, base, base, witness.costs)
    assert after_reference["delta_to_previous_revision"] is not None


@pytest.mark.requirement("WF-IND-0090-A")
def test_no_revision_marked_before_the_state_in_progress_gives_a_point(
    today: dict[str, Any],
) -> None:
    # « Les révisions marquées avant l'état En cours ne donnent aucun point » ; « Un jalon terminé
    # n'a plus de point après sa terminaison, et son dernier point est sur la diagonale » ; the
    # last point of the other is that of the current day.
    studies, acceptance = today["milestone_tracking"]["milestones"]
    for milestone in (studies, acceptance):
        assert all(point["marked_at"] != "2025-12-15T16:00:00Z" for point in milestone["points"])
    assert studies["points"][-1] == {
        "marked_at": f"{studies['completed_on']}T00:00:00Z",
        "forecast_date": studies["completed_on"],
    }
    assert acceptance["points"][-1]["marked_at"] == "2026-06-03T14:05:00Z"


WEEK = (date(2026, 3, 2), date(2026, 3, 6))


def _leaf(number: int, amount: str, progress: str, *extra: Line) -> Task:
    return Task(
        number,
        f"Tâche {number}",
        days=5,
        manual=WEEK,
        progress=progress,
        lines=(Line(number * 10, f"Ligne {number}", SUBCONTRACTING, unit=Decimal(amount)), *extra),
    )


@pytest.mark.requirement("WF-IND-0060-A")
@pytest.mark.parametrize(
    ("own", "expected"),
    [
        # « Une récapitulative sans ligne propre dont les deux premières de trois subordonnées, de
        # montants budgétés 100, 100 et 200, sont terminées affiche 50 % » — the provision of 50 on
        # the second, out of both terms.
        ((), "0.5"),
        # Its own line of 100 counts, not earned while it is not completed: 200 on 500.
        ((Line(9009, "Ligne propre", SUBCONTRACTING, unit=Decimal(100)),), "0.4"),
    ],
)
def test_the_physical_progress_of_a_summary_leaves_out_the_lines_of_provision(
    own: tuple[Line, ...], expected: str
) -> None:
    provision = Line(9029, "Provision", PROVISIONS, unit=Decimal(50), is_provision=True)
    summary = Task(
        900,
        "Récapitulative",
        lines=own,
        children=(
            _leaf(901, "100", "completed"),
            _leaf(902, "100", "completed", provision),
            _leaf(903, "200", "started"),
        ),
    )
    [row] = [row for row in mockcore.core((summary,), date(2026, 6, 3)) if row.number == 900]
    facet = cast("Node", row.node["task"])
    assert facet["physical_progress"] == {
        "is_computable": True,
        "value": expected,
        "reason": None,
    }
