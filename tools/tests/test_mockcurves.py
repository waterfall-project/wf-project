# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the curves and the indicators of the witness against their requirements (US-0701/L5).

They try the contract and its examples, not the service, which EP-08 to EP-11 write: the curves of
a project at the pace of the month, each point the cumulative amount at the end of its month, the
day of the calculation one point more on the series that stop or start there (WF-IND-0100,
WF-IND-0110, WF-DAT-0040); the indicators of the day of a project without a current revision,
computed on its last marked revision with the actual cost of the day (WF-IND-0010).
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from wftools import mockcurves, mockdata, mockhistory, mockindicators, mocktoday
from wftools.mockindicators import Cost
from wftools.mockwitness import TODAY

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
