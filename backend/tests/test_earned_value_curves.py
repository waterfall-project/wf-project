# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The curves of the earned value on the current day, served (``getEarnedValueCurves``; US-1690/L2).

The planned value to the end of the reference, the earned value by month of completion, the actual
cost by month of document, the gap of the two at the day, the scope and the refusals; then the
curves of the witness, compared with the example of the contract. The project is the one of
``curves_support``. Every answer is checked against the contract.
"""

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from curves_support import (
    COST_CURVE,
    EARNED_VALUE_CURVES,
    TODAY,
    curve,
    curve_answer,
    over_three_months,
    series,
)
from day_indicators_support import Planned, completed, indicators, priced, subproject
from indicators_support import clock_setter, marked
from nodes_support import faults, refusal
from planning_support import DAY
from projects_support import PROJECTS
from projects_support import scene as make_scene
from witness_support import PRJ_001, READ_AT, example, read

from waterfall.core.projects.interface import current_day
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from indicators_support import Clock
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

D = Decimal
MONTH_ENDS = 3
CENTS = [Planned("Études", "333.33", None, "30"), Planned("Câblage", "666.67", None, "60")]


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the curves are computed on."""
    return clock_setter(monkeypatch)


@pytest.mark.requirement("WF-IND-0110-A")
def test_the_planned_value_reaches_the_budget_at_the_end_of_the_reference_and_stays(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « La courbe de valeur planifiée atteint le budget de référence à la fin de la référence. »
    # 490, 350 and 160 over three months, 1 000 at the end of January, where the last task ends,
    # the budget of the indicators; the reference budget of the cost curve is the same series.
    over_three_months(api, stage, clock)
    body = curve(api, stage, EARNED_VALUE_CURVES)
    planned = series(body, "planned_value")
    assert planned == [
        ("2026-10-31", "0.00"),
        ("2026-11-30", "490.00"),
        ("2026-12-31", "840.00"),
        ("2027-01-31", "1000.00"),
    ]
    assert planned[-1][1] == indicators(api, stage)["reference_budget"]
    assert planned == series(curve(api, stage, COST_CURVE), "reference_budget")
    assert (body["payment_delays"], body["steps"], body["cash_out_by_month"]) == (False, [], None)
    assert body["context"]["is_stored"] is False


def month_ends_read(
    api: ContractClient, stage: Scene, clock: Clock, name: str, curve_name: str
) -> list[tuple[str, str, str]]:
    """Give, at each month-end of a curve read that day, its point and the planned value there."""
    found: list[tuple[str, str, str]] = []
    for day in (DAY + timedelta(days=28), DAY + timedelta(days=59), DAY + timedelta(days=90)):
        clock(day)
        planned = indicators(api, stage)["planned_value"]
        found.extend(
            (when, amount, planned)
            for when, amount in series(curve(api, stage, curve_name), name)
            if when == day.isoformat()
        )
    return found


@pytest.mark.requirement("WF-IND-0110-A")
def test_the_planned_value_of_the_curve_is_that_of_the_indicators_at_the_same_day(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « La courbe de valeur planifiée atteint le budget de référence à la fin de la référence. »
    # The test holds the body of the requirement, the planned value of WF-DEV-0080, not that
    # Vérif. Amounts that do not spread to the cent (333.33 and 666.67): at each month-end, the
    # point of the curve, which sums the rounded parts of each line, is the planned value of the
    # indicators read that day (``planned_value_at``), not a sum of the unrounded months. The
    # month that tells the two apart is 30 November: 466.66 by line, 466.67 by the total.
    priced(api, stage, CENTS)
    found = month_ends_read(api, stage, clock, "planned_value", EARNED_VALUE_CURVES)
    assert len(found) == MONTH_ENDS
    assert all(amount == planned for _, amount, planned in found), found


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_reference_budget_of_the_cost_curve_is_the_planned_value_at_the_same_day(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « La courbe du budget de référence atteint le budget de référence à la date de fin de la
    # référence. » The test holds the body of the requirement, the reference budget read by the
    # rule of the planned value (WF-DEV-0080), not that Vérif. Without a payment delay, each
    # month-end of the reference budget is the planned value of the indicators that day, amounts
    # not spreading to the cent included; 30 November, 466.66 by line against 466.67 by the total,
    # is the month that tells the roundings apart.
    priced(api, stage, CENTS)
    found = month_ends_read(api, stage, clock, "reference_budget", COST_CURVE)
    assert len(found) == MONTH_ENDS
    assert all(amount == planned for _, amount, planned in found), found


@pytest.mark.requirement("WF-IND-0110-A")
def test_a_completed_task_makes_a_step_in_the_earned_value_at_the_month_of_its_completion(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « Une tâche terminée produit une marche dans la valeur acquise au point du mois de sa date de
    # terminaison. » The studies, 400, completed on 6 November, the wiring, 600, on 3 December, the
    # day the 10th: the point of November carries the first and not the second, the date of the day
    # a point of its own, the series stopping there.
    found = priced(api, stage, [Planned("Études", "400", None, "30"), Planned("Câblage", "600")])
    completed(found.tree, "Études", DAY + timedelta(days=4))
    completed(found.tree, "Câblage", DAY + timedelta(days=31))
    clock(DAY + timedelta(days=38))
    body = curve(api, stage, EARNED_VALUE_CURVES)
    assert series(body, "earned_value") == [
        ("2026-10-31", "0.00"),
        ("2026-11-30", "400.00"),
        ("2026-12-10", "1000.00"),
    ]
    assert series(body, "actual_cost") == [
        ("2026-10-31", "0.00"),
        ("2026-11-30", "0.00"),
        ("2026-12-10", "0.00"),
    ]


@pytest.mark.requirement("WF-IND-0110-A")
def test_at_the_date_of_calculation_the_gap_of_the_two_curves_is_the_cost_variance(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « À la date de calcul, l'écart vertical entre la courbe de valeur acquise et celle du coût
    # réel égale la différence des deux grandeurs. » 400 earned, 100 spent: the points of the day
    # of the two series, and the variance of the indicators.
    over_three_months(api, stage, clock)
    body = curve(api, stage, EARNED_VALUE_CURVES)
    earned, spent = series(body, "earned_value")[-1], series(body, "actual_cost")[-1]
    assert earned == ("2026-11-13", "400.00")
    assert spent == ("2026-11-13", "100.00")
    assert D(earned[1]) - D(spent[1]) == D(indicators(api, stage)["cost_variance"])


@pytest.mark.requirement("WF-IND-0110-A")
def test_the_curves_of_a_scope_count_its_lines_only_and_a_scope_without_any_has_none(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « `scope` restreint chaque série aux lignes et aux coûts de la maille » : the lines are
    # borne by a subproject, the cost by the project alone.
    named = subproject(api, stage, "SP-1", "Poste de commande")
    empty = subproject(api, stage, "SP-2", "Essais")
    over_three_months(api, stage, clock, subproject_id=named)
    body = curve(api, stage, EARNED_VALUE_CURVES, f"?scope={named}")
    assert series(body, "planned_value")[-1] == ("2027-01-31", "1000.00")
    assert series(body, "earned_value")[-1] == ("2026-11-13", "400.00")
    assert series(body, "actual_cost")[-1] == ("2026-11-13", "0.00")
    alone = curve(api, stage, EARNED_VALUE_CURVES, "?scope=unassigned")
    assert series(alone, "planned_value") == []
    assert series(alone, "earned_value") == [("2026-10-31", "0.00"), ("2026-11-13", "0.00")]
    assert series(alone, "actual_cost")[-1] == ("2026-11-13", "100.00")
    nothing = curve(api, stage, EARNED_VALUE_CURVES, f"?scope={empty}")
    assert [each["points"] for each in nothing["series"]] == [[], [], []]
    assert nothing["context"]["scope"] == empty


@pytest.mark.requirement("WF-IND-0110-A")
def test_the_refusals_are_those_of_the_indicators(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # 409 before In progress with the state named, then 422 on a revision named with a date and on
    # an unknown scope, at once; 404 for a revision the project does not have.
    assert refusal(curve_answer(api, stage, EARNED_VALUE_CURVES)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"state": "created", "state_enum": "ProjectState"},
    )
    found = over_three_months(api, stage, clock)
    revision_id = found.tree.revision["revision_id"]
    both = f"?revision_id={revision_id}&as_of={TODAY.isoformat()}&scope=SP-1"
    assert faults(curve_answer(api, stage, EARNED_VALUE_CURVES, both)) == [
        ("/query/scope", "UNKNOWN_SUBPROJECT", {}),
        ("/query/revision_id", "VALIDATION_FAILED", {}),
    ]
    unknown = curve_answer(api, stage, EARNED_VALUE_CURVES, f"?revision_id={UUID(int=1)}")
    assert unknown.status_code == 404, unknown.text


@pytest.mark.requirement("WF-DAT-0040-A")
def test_kept_curves_of_a_subproject_created_after_the_marking_are_refused_without_a_state(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # Décision de l'auteur du 2026-11-16 (#3604), as for ``getProjectIndicators``: the revision,
    # named or designated by its date, kept the curves of the project, not those of a subproject
    # created since, which the project has today — no 422 —: 409 ``STATE_FORBIDS_OPERATION``
    # without ``params``, and no empty series in its place. The marking is set after the
    # reference, which the service marked at the instant it wrote it.
    found = over_three_months(api, stage, clock)
    revision_id = found.tree.revision["revision_id"]
    at = clock(utc_now().date() + timedelta(days=1))
    marked(stage, found.tree.revision, "Revue de novembre")
    since = subproject(api, stage, "SP-9", "Essais")
    for query in (f"?revision_id={revision_id}", f"?as_of={current_day(at).isoformat()}"):
        assert curve(api, stage, EARNED_VALUE_CURVES, query)["context"]["is_stored"] is True
        refused = curve_answer(api, stage, EARNED_VALUE_CURVES, f"{query}&scope={since}")
        assert refusal(refused) == (409, "STATE_FORBIDS_OPERATION", {}), query
    day = curve(api, stage, EARNED_VALUE_CURVES, f"?scope={since}")
    assert day["context"]["is_stored"] is False


def points_of(body: dict[str, Any], name: str) -> dict[str, D]:
    """Give the points of a series by day."""
    return {day: D(amount) for day, amount in series(body, name)}


@pytest.mark.requirement("WF-IND-0110-A")
def test_the_curves_of_the_witness_are_the_example_but_for_the_reference(
    api: ContractClient, witness: Database, realm: TestRealm, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « À la date de calcul, l'écart vertical entre la courbe de valeur acquise et celle du coût
    # réel égale la différence des deux grandeurs. » The witness read on 3 June 2026: the earned
    # value, by step at the month of each completion, and the actual cost are the example's, point
    # for point; the planned value, measured to the offer 100, the reference until the amendment 1
    # (EP-08), has the days of the example's and only grows. The gap of the two curves at the day
    # is the example's, 1 493 354.19 less 1 412 970.20.
    monkeypatch.setattr("waterfall.api.indicator_curves.utc_now", lambda: READ_AT)
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/indicators/{EARNED_VALUE_CURVES}")
    expected = example("earned_value_curves")
    for name in ("earned_value", "actual_cost"):
        assert series(body, name) == series(expected, name)
    planned, wanted = points_of(body, "planned_value"), points_of(expected, "planned_value")
    assert list(planned) == list(wanted)
    assert list(planned.values()) == sorted(planned.values())
    assert D(series(body, "earned_value")[-1][1]) - D(series(body, "actual_cost")[-1][1]) == D(
        "80383.99"
    )
