# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cumulative costs of a project on the current day, served (``getCostCurve``; US-1690/L2).

The reference budget, the actual cost up to the day, the projection of the project manager that
starts there, the same shifted by the payment delays, the scope, and the refusals of
``getProjectIndicators``; then the curve of the witness, compared with the example of the contract.
The project is the one of ``curves_support``. Every answer is checked against the contract.
"""

from datetime import timedelta
from decimal import Decimal
from itertools import pairwise
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from curves_support import COST_CURVE, TODAY, curve, curve_answer, over_three_months, series
from day_indicators_support import indicators, subproject
from indicators_support import clock_setter, marked
from nodes_support import Tree, faults, opened, refusal
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

FORBIDDEN = (409, "STATE_FORBIDS_OPERATION")
D = Decimal


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the curves are computed on."""
    return clock_setter(monkeypatch)


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_reference_budget_reaches_the_budget_at_the_end_of_the_reference_and_stays(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « La courbe du budget de référence atteint le budget de référence à la date de fin de la
    # référence. » 490 in November, 350 in December, 160 in January, where the last task ends: the
    # point of that month is the budget of the indicators, and there is no point after.
    over_three_months(api, stage, clock)
    body = curve(api, stage, COST_CURVE)
    assert series(body, "reference_budget") == [
        ("2026-10-31", "0.00"),
        ("2026-11-30", "490.00"),
        ("2026-12-31", "840.00"),
        ("2027-01-31", "1000.00"),
    ]
    assert series(body, "reference_budget")[-1][1] == indicators(api, stage)["reference_budget"]
    assert (body["steps"], body["cash_out_by_month"], body["payment_delays"]) == ([], None, False)


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_actual_cost_stops_at_the_date_of_calculation_where_the_projection_starts(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « Celle du coût réel s'arrête à la date de calcul, et la projection part de ce point pour
    # atteindre la projection du chef de projet. » The actual cost, 100, ends at the day of the
    # clock, a point of its own; the 600 left of the wiring, from the 16th, are 132, 276 and 192
    # over the end of the months, up to the projection of the project manager, 700.
    over_three_months(api, stage, clock)
    body = curve(api, stage, COST_CURVE)
    assert body["context"] == {
        "revision_id": body["context"]["revision_id"],
        "revision_status": "draft",
        "computed_at": "2026-11-13T09:00:00Z",
        "scope": "project",
        "is_stored": False,
    }
    assert series(body, "actual_cost") == [("2026-10-31", "0.00"), ("2026-11-13", "100.00")]
    projection = series(body, "project_manager_projection")
    assert projection == [
        ("2026-11-13", "100.00"),
        ("2026-11-30", "232.00"),
        ("2026-12-31", "508.00"),
        ("2027-01-31", "700.00"),
    ]
    assert projection[-1][1] == indicators(api, stage)["projections"]["project_manager"]


@pytest.mark.requirement("WF-IND-0100-A")
def test_with_a_delay_of_60_days_the_budget_is_the_curve_translated_by_60_days_not_the_actual_cost(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « Avec un délai de paiement de 60 jours saisi sur toutes les lignes, […] la courbe du budget
    # de référence décalée est la courbe non décalée translatée de 60 jours ; la projection l'est
    # aussi […] ; le coût réel n'est pas décalé. » The delayed curve at a month-end is the other
    # at that day less 60 days: 31 December is 1 November, nothing yet; 31 January is 2 December,
    # 280 + 210 of November and 2 days of December, 26.67 + 20; 28 February is 30 December, all
    # but the last working day of the wiring.
    over_three_months(api, stage, clock, payment_delay_days=60)
    plain = curve(api, stage, COST_CURVE)
    shifted = curve(api, stage, COST_CURVE, "?payment_delays=true")
    assert shifted["payment_delays"] is True
    assert series(shifted, "reference_budget") == [
        ("2026-12-31", "0.00"),
        ("2027-01-31", "536.67"),
        ("2027-02-28", "830.00"),
        ("2027-03-31", "1000.00"),
    ]
    assert series(shifted, "actual_cost") == series(plain, "actual_cost")
    # The 600 left, 12 a working day from the 16th, translated by 60 days the same way: 2 December
    # for 31 January, 30 December for 28 February.
    assert series(shifted, "project_manager_projection") == [
        ("2026-11-13", "100.00"),
        ("2026-11-30", "100.00"),
        ("2026-12-31", "100.00"),
        ("2027-01-31", "256.00"),
        ("2027-02-28", "496.00"),
        ("2027-03-31", "700.00"),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_curve_of_a_scope_counts_its_lines_and_its_costs_only(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « `scope` restreint chaque série aux lignes et aux coûts de la maille — une maille sans ligne
    # […] et sans coût réel a des séries sans point, `steps` vide et `cash_out_by_month` vide avec
    # les délais ; […] le coût réel d'une maille qui a des lignes et aucune pièce est tracé nul. »
    # Both tasks are borne by a subproject, the cost by the project alone: the subproject has the
    # budget and the remaining, its actual cost drawn at zero; the project alone has the cost,
    # no budget, and its projection is its actual cost; another subproject has nothing to draw.
    named = subproject(api, stage, "SP-1", "Poste de commande")
    empty = subproject(api, stage, "SP-2", "Essais")
    over_three_months(api, stage, clock, subproject_id=named)
    body = curve(api, stage, COST_CURVE, f"?scope={named}")
    assert body["context"]["scope"] == named
    assert series(body, "reference_budget")[-1] == ("2027-01-31", "1000.00")
    assert series(body, "actual_cost") == [("2026-10-31", "0.00"), ("2026-11-13", "0.00")]
    assert series(body, "project_manager_projection")[0] == ("2026-11-13", "0.00")
    assert series(body, "project_manager_projection")[-1] == ("2027-01-31", "600.00")
    alone = curve(api, stage, COST_CURVE, "?scope=unassigned")
    assert series(alone, "reference_budget") == []
    assert series(alone, "actual_cost") == [("2026-10-31", "0.00"), ("2026-11-13", "100.00")]
    assert series(alone, "project_manager_projection") == [("2026-11-13", "100.00")]
    nothing = curve(api, stage, COST_CURVE, f"?scope={empty}")
    assert nothing["context"]["scope"] == empty
    assert [each["points"] for each in nothing["series"]] == [[], [], []]
    assert (nothing["steps"], nothing["cash_out_by_month"]) == ([], None)
    delayed = curve(api, stage, COST_CURVE, f"?scope={empty}&payment_delays=true")
    assert [each["points"] for each in delayed["series"]] == [[], [], []]
    assert delayed["cash_out_by_month"] == []


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_project_before_in_progress_has_no_curve_its_state_is_named(
    api: ContractClient, stage: Scene
) -> None:
    # The 409 of ``getProjectIndicators``: the state named with its enumeration, before the
    # parameters, which an unknown scope would refuse otherwise.
    assert refusal(curve_answer(api, stage, COST_CURVE)) == (
        *FORBIDDEN,
        {"state": "created", "state_enum": "ProjectState"},
    )
    Tree(api, stage, opened(api, stage))
    for query in ("", "?scope=SP-1&as_of=2026-11-02&revision_id=" + str(UUID(int=1))):
        assert refusal(curve_answer(api, stage, COST_CURVE, query)) == (
            *FORBIDDEN,
            {"state": "pricing", "state_enum": "ProjectState"},
        )


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_revision_named_with_a_date_is_refused_and_an_unknown_revision_is_not_found(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # 422 on ``/query/revision_id`` for a revision and a date together, with an unknown scope both
    # at once, the scope first; 404 for a revision the project does not have.
    found = over_three_months(api, stage, clock)
    revision_id = found.tree.revision["revision_id"]
    both = f"?revision_id={revision_id}&as_of={TODAY.isoformat()}"
    assert faults(curve_answer(api, stage, COST_CURVE, both)) == [
        ("/query/revision_id", "VALIDATION_FAILED", {}),
    ]
    assert faults(curve_answer(api, stage, COST_CURVE, f"{both}&scope=SP-1")) == [
        ("/query/scope", "UNKNOWN_SUBPROJECT", {}),
        ("/query/revision_id", "VALIDATION_FAILED", {}),
    ]
    unknown = curve_answer(api, stage, COST_CURVE, f"?revision_id={UUID(int=1)}")
    assert unknown.status_code == 404, unknown.text
    assert curve_answer(api, stage, COST_CURVE, f"?revision_id={revision_id}").status_code == 200


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_kept_curve_of_a_subproject_created_after_the_marking_is_refused_without_a_state(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # Décision de l'auteur du 2026-11-16 (#3604), as for ``getProjectIndicators``: the revision,
    # named or designated by its date, kept the curves of the project, not those of a subproject
    # created since, which the project has today — no 422 —: 409 ``STATE_FORBIDS_OPERATION``
    # without ``params``, with or without the payment delays, and no empty series in its place.
    # The marking is set after the reference, which the service marked at the instant it wrote it.
    found = over_three_months(api, stage, clock)
    revision_id = found.tree.revision["revision_id"]
    at = clock(utc_now().date() + timedelta(days=1))
    marked(stage, found.tree.revision, "Revue de novembre")
    since = subproject(api, stage, "SP-9", "Essais")
    for query in (f"?revision_id={revision_id}", f"?as_of={current_day(at).isoformat()}"):
        assert curve(api, stage, COST_CURVE, query)["context"]["is_stored"] is True, query
        for asked in (f"{query}&scope={since}", f"{query}&scope={since}&payment_delays=true"):
            assert refusal(curve_answer(api, stage, COST_CURVE, asked)) == (*FORBIDDEN, {}), asked
    assert curve(api, stage, COST_CURVE, f"?scope={since}")["context"]["is_stored"] is False


# The provision of the risk identified, 500 000, and the two lines its occurrence added, 120 and 80,
# all of EP-08, are among the remaining to commit of the example, that no line of the witness bears
# yet: 500 200.
PROVISION = D("500200.00")


def points_of(body: dict[str, Any], name: str) -> dict[str, D]:
    """Give the points of a series by day."""
    return {day: D(amount) for day, amount in series(body, name)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_curve_of_the_witness_is_the_example_but_for_the_reference_and_the_provision(
    api: ContractClient, witness: Database, realm: TestRealm, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Celle du coût réel s'arrête à la date de calcul, et la projection part de ce point pour
    # atteindre la projection du chef de projet. » The witness read on 3 June 2026, as the
    # examples: the actual cost is the example's, but for its origin, which the example draws at
    # the end of January, where the amendment 1 steps the budget (EP-08), the reference of the
    # witness being the offer 100 until it merges; the projection starts at the actual cost and
    # follows the example, less the provision (EP-08), month-end for month-end to the end of the
    # last task. The reference budget, measured to the offer 100, is not compared.
    monkeypatch.setattr("waterfall.api.indicator_curves.utc_now", lambda: READ_AT)
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/indicators/{COST_CURVE}")
    expected = example("cost_curve")
    assert (body["context"]["is_stored"], body["steps"]) == (False, [])
    actual, wanted = points_of(body, "actual_cost"), points_of(expected, "actual_cost")
    assert wanted.pop("2026-01-31") == 0
    assert actual == wanted
    projection = points_of(body, "project_manager_projection")
    asked = points_of(expected, "project_manager_projection")
    assert projection["2026-06-03"] == asked["2026-06-03"] == actual["2026-06-03"]
    assert set(projection) == set(asked)
    assert {day: asked[day] - amount for day, amount in projection.items()} == {
        day: D(0) if day == "2026-06-03" else PROVISION for day in asked
    }


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_projection_grows_each_month_by_the_projection_of_spending_to_the_cent(
    api: ContractClient, witness: Database, realm: TestRealm, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Propre à l'US : « la courbe de coûts passe, comme la projection de dépenses et le plan de
    # charge, par les parts arrondies communes de core/estimate » (US-1690/L4, #3564, #3614). The
    # witness read on 3 June 2026 by the two routes: what the projection of the project manager
    # gains in each month is the total of that month `getProjectSpending` gives on the remaining
    # to commit, to the cent; the occurrence of a risk (EP-08) and the provision are left out of
    # both, the witness bearing neither.
    monkeypatch.setattr("waterfall.api.indicator_curves.utc_now", lambda: READ_AT)
    monkeypatch.setattr("waterfall.api.spending.utc_now", lambda: READ_AT)
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/indicators/{COST_CURVE}")
    points = series(body, "project_manager_projection")
    gained = {
        day[:7]: D(amount) - D(before)
        for (_, before), (day, amount) in pairwise(points)
        if D(amount) != D(before)
    }
    spent = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/spending?basis=current_remaining")
    spending = {
        row["month"]: D(row["amount"]) for row in spent["monthly_totals"] if D(row["amount"])
    }
    assert spending
    assert gained == spending
