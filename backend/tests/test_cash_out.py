# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cash-out by month of ``getCostCurve`` with the payment delays (US-1690/L2; #3556).

The past by month of document, the forecast by month of the remaining to commit shifted by the
delay of each line, the month of the date of calculation carrying both; the sum of the forecast
equals the remaining to commit to the cent, the amounts of the lines being cents already — on the
service, and on the witness, whose cash-out is compared with the example of the contract. The
project is the one of ``curves_support``.
"""

from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import load_import
from curves_support import COST_CURVE, curve, over_three_months, series
from day_indicators_support import Planned, dated, indicators, priced, reestimated
from indicators_support import clock_setter
from planning_support import DAY
from projects_support import PROJECTS
from projects_support import scene as make_scene
from witness_support import PRJ_001, READ_AT, example, read

if TYPE_CHECKING:
    from indicators_support import Clock
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

D = Decimal
DELAYED = "?payment_delays=true"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the curves are computed on."""
    return clock_setter(monkeypatch)


def months(body: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Give the cash-out of a curve: each month, its past and its forecast."""
    return [(each["month"], each["past"], each["forecast"]) for each in body["cash_out_by_month"]]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_forecast_adds_up_to_the_remaining_to_commit_to_the_cent(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « La somme des décaissements à venir égale le reste à engager […] » (#3556): amounts that
    # do not divide to the cent, three lines of three delays, one of them re-estimated. The
    # remaining of the revision is the sum of the amounts of its lines, which are cents: the sum of
    # the rounded parts is the rounded sum, which is the remaining, to the cent.
    found = priced(
        api,
        stage,
        [
            Planned("A", "333.33", None, "30"),
            Planned("B", "1000.01", None, "45", 30),
            Planned("C", "777.77", None, "20", 61),
        ],
    )
    reestimated(found.tree, "A", "100.07")
    clock(DAY + timedelta(days=11))
    remaining = indicators(api, stage)["remaining"]
    assert remaining == "1877.85"
    body = curve(api, stage, COST_CURVE, DELAYED)
    rows = months(body)
    assert sum((D(forecast) for _, _, forecast in rows), D(0)) == D(remaining)
    assert all(D(forecast) == D(forecast).quantize(D("0.01")) for _, _, forecast in rows)
    assert series(body, "project_manager_projection")[-1][1] == "1877.85"
    assert sum((D(forecast) for _, _, forecast in rows), D(0)) == D("1877.85")


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_past_is_by_month_of_document_and_the_month_of_the_day_carries_both(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « le passé par mois de date de pièce, l'avenir par mois de part décalée, le mois de la date
    # de calcul portant les deux, nul sinon » ; « le coût réel n'est pas décalé ». A document of
    # October, one of November, the day the 13th: November carries its 100 and the 132 of the
    # wiring left in the month; the days after the date are not paid yet.
    over_three_months(api, stage, clock)
    load_import(
        stage,
        UUID(stage.project["project_id"]),
        [dated("FA-2", None, "40.00", DAY - timedelta(days=20))],
    )
    body = curve(api, stage, COST_CURVE, DELAYED)
    assert months(body) == [
        ("2026-10", "40.00", "0.00"),
        ("2026-11", "100.00", "132.00"),
        ("2026-12", "0.00", "276.00"),
        ("2027-01", "0.00", "192.00"),
    ]
    assert series(body, "actual_cost")[-1] == ("2026-11-13", "140.00")


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_delay_moves_the_forecast_and_leaves_the_past_where_the_documents_are(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « Le coût réel n'est pas décalé » : with 60 days on every line, the 600 left, from the 16th,
    # are due from January (2 December, the translation of 31 January, 156), the past is November's.
    over_three_months(api, stage, clock, payment_delay_days=60)
    body = curve(api, stage, COST_CURVE, DELAYED)
    assert months(body) == [
        ("2026-11", "100.00", "0.00"),
        ("2026-12", "0.00", "0.00"),
        ("2027-01", "0.00", "156.00"),
        ("2027-02", "0.00", "240.00"),
        ("2027-03", "0.00", "204.00"),
    ]
    assert curve(api, stage, COST_CURVE)["cash_out_by_month"] is None


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_cash_out_of_the_witness_is_the_example_but_for_the_occurrence(
    api: ContractClient, witness: Database, realm: TestRealm, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « La somme des décaissements à venir égale le reste à engager, provisions des risques
    # identifiés comprises. » The witness read on 3 June 2026: the past is the example's, month for
    # month, and the forecast too, the provision of 751 included (EP-08), but for the two lines the
    # occurrence of 752 added, 200, of tasks completed, which the example puts in June (#4278; the
    # forecast is otherwise the same to the cent, #3564); the sum of the forecast is the remaining
    # of the witness, the projection of the project manager less the actual cost at the day, as the
    # example's is.
    monkeypatch.setattr("waterfall.api.indicator_curves.utc_now", lambda: READ_AT)
    url = f"{PROJECTS}/{PRJ_001}/indicators/{COST_CURVE}"
    body = read(api, witness, realm, f"{url}{DELAYED}")
    expected = example("cost_curve_payment_delays")
    provision = D("200.00")
    got, wanted = months(body), months(expected)
    assert [(month, past) for month, past, _ in got] == [(m, p) for m, p, _ in wanted]
    assert {
        m: D(want) - D(have) for (m, _, have), (_, _, want) in zip(got, wanted, strict=True)
    } == {month: provision if month == "2026-06" else D(0) for month, _, _ in wanted}
    forecast = sum((D(each) for _, _, each in got), D(0))
    projection = series(body, "project_manager_projection")
    assert D(projection[-1][1]) - D(projection[0][1]) == forecast
    assert forecast == D(sum((D(each) for _, _, each in wanted), D(0))) - provision
    assert body["cash_out_by_month"] is not None
    assert read(api, witness, realm, url)["cash_out_by_month"] is None


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_cash_out_to_come_is_the_projection_of_spending_to_the_cent(
    api: ContractClient, witness: Database, realm: TestRealm, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Propre à l'US : « la courbe de coûts passe, comme la projection de dépenses et le plan de
    # charge, par les parts arrondies communes de core/estimate : à chaque mois, ses décaissements
    # sans les provisions et la projection de dépenses ne diffèrent pas d'un centime » (#3564,
    # #3614). The witness read on 3 June 2026 by the two routes: month for month, the cash-out to
    # come of `getCostCurve` is the total of `getProjectSpending` on the remaining to commit with
    # the payment delays, to the cent, but for the provision of 751, which the cash-out counts in
    # June, the month of its task, and the spending leaves out (EP-08).
    monkeypatch.setattr("waterfall.api.indicator_curves.utc_now", lambda: READ_AT)
    monkeypatch.setattr("waterfall.api.spending.utc_now", lambda: READ_AT)
    body = read(api, witness, realm, f"{PROJECTS}/{PRJ_001}/indicators/{COST_CURVE}{DELAYED}")
    forecast = {month: D(each) for month, _, each in months(body) if D(each)}
    spent = read(
        api,
        witness,
        realm,
        f"{PROJECTS}/{PRJ_001}/spending?basis=current_remaining&payment_delays=true",
    )
    spending = {
        row["month"]: D(row["amount"]) for row in spent["monthly_totals"] if D(row["amount"])
    }
    assert spending
    provision = D(example("remaining_indicators")["coverage"]["remaining_provisions"])
    gaps = {month: amount - spending.get(month, D(0)) for month, amount in forecast.items()}
    assert {month: gap for month, gap in gaps.items() if gap} == {"2026-06": provision}
