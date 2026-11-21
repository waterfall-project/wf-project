# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The scope, the period and the date of the eight views, read on the service (US-2670/L4).

What every view gives back of what it was asked (``PortfolioScope``), the one rule of the periods
and the bound the performance puts on its own, the offer lost on 15 March, the review just marked
that carries a project that has no revision in progress, the figures of a project at 0 % and at
100 %, and the refusals of a number the contract would not write. The four projects of the fabrics
(``portfolio_support``) on the platform of a scene, read at the date of the witness, 3 June 2026,
or on a current day the tests pin to a day after the whole chronology. Every answer is validated
against the contract by the client of the tests.
"""

import json
import re
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import pytest
import yaml
from costs_support import cost, load_import
from portfolio_listing_support import READ, read, served
from portfolio_support import (
    LOST_ON,
    READ_ON,
    REVIEW,
    Portfolio,
    another_in_progress,
    offer_being_priced,
    portfolio,
    revision_opened,
)
from portfolio_transverse_support import NOW, PERIODIC, VIEWS, now_is, probability_written
from projects_support import MANAGING, Scene
from projects_support import scene as make_scene

from waterfall.core.estimate.workloading import WorkloadAsked, WorkloadBasis, reading_of
from waterfall.core.projects.interface import Viewer
from waterfall.core.revisions.interface import current_revision
from waterfall.platform.installation import TIME_ZONE

if TYPE_CHECKING:
    from uuid import UUID

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

PATHS = Path(__file__).resolve().parents[2] / "docs" / "api" / "paths" / "portfolio.yaml"
PORTFOLIO = "/api/v1/portfolio"
INDICATORS = ("estimate-indicators", "remaining-indicators", "indicators")
# The date of calculation a view is read at: the default period then starts on 4 June 2025.
DEFAULT_PERIOD = ("2025-06-04", "2026-06-03")


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def contract_example() -> dict[str, Any]:
    """Read the example of the refusal of a period too long, as the contract writes it."""
    paths = yaml.safe_load(PATHS.read_text(encoding="utf-8"))
    refused = paths["/portfolio/performance"]["get"]["responses"]["422"]
    found: dict[str, Any] = refused["content"]["application/problem+json"]["examples"]
    return found["period_too_long"]["value"]


def anonymous(body: Any) -> str:
    """Write an answer with each identifier it holds replaced by its rank of appearance."""
    text = json.dumps(body, sort_keys=False)
    ranks: dict[str, int] = {}

    def rank(found: re.Match[str]) -> str:
        return f"#{ranks.setdefault(found.group(), len(ranks))}"

    return re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", rank, text)


def refusal(api: ContractClient, fabrics: Portfolio, view: str, query: str) -> list[Any]:
    """Read a view that refuses its query (422); give the faults it names, each by its parts."""
    answer = read(api, fabrics.stage.reader, view, query)
    assert (answer.status_code, answer.json()["code"]) == (422, "VALIDATION_FAILED"), (view, query)
    return [(each["pointer"], each["code"], each.get("params")) for each in answer.json()["fields"]]


# --- The scope each view gives back -------------------------------------------------------------


@pytest.mark.story("US-2670")
def test_every_view_gives_back_its_scope_and_a_state_it_does_not_count_is_without_effect(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Chaque vue rend le périmètre retenu (PortfolioScope) — les états demandés ou, sans eux, les
    # projets en cours ; la date de calcul ; la période, celle par défaut comprise, nulle pour une
    # vue qui n'en retient pas ; le nœud et son libellé ; le nombre de projets retenus ; un état que
    # la vue ne compte pas est sans effet, jamais refusé. » The list retains no period unless one
    # is asked; the workload and the health of the control retain none at all.
    reader = fabrics.stage.reader
    for view in VIEWS:
        scope = served(api, reader, view, f"as_of={READ_ON}")["scope"]
        period = DEFAULT_PERIOD if view in PERIODIC and view != "projects" else (None, None)
        assert scope == {
            "states": ["in_progress"],
            "as_of": str(READ_ON),
            "from": period[0],
            "to": period[1],
            "org_node_id": None,
            "org_node_label": None,
            "project_count": 1,
        }, view
        # The states no view counts: asked, they stay in the scope and retain no project.
        idle = served(api, reader, view, f"as_of={READ_ON}&states=created,lost,abandoned")["scope"]
        assert (idle["states"], idle["project_count"]) == (["created", "lost", "abandoned"], 0), (
            view
        )
    asked = served(api, reader, "projects", f"as_of={READ_ON}&from=2026-01-01")["scope"]
    assert (asked["from"], asked["to"]) == ("2026-01-01", str(READ_ON))


@pytest.mark.story("US-2670")
def test_the_current_day_is_that_of_the_clock_in_the_time_zone_of_the_installation(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « la date de calcul, le jour courant du fuseau de l'installation sans as_of » : at 23:30
    # universal time on 19 November, an installation in Honolulu (UTC-10) is on the 19th at 13:30
    # and one in Auckland (UTC+13) is already on the 20th; every view says the day of its own.
    reader = fabrics.stage.reader
    now_is(monkeypatch, datetime(2026, 11, 19, 23, 30, tzinfo=UTC))
    for zone, day in (("Pacific/Honolulu", "2026-11-19"), ("Pacific/Auckland", "2026-11-20")):
        TIME_ZONE.read_from(lambda zone=zone: zone)
        assert {served(api, reader, view, "")["scope"]["as_of"] for view in VIEWS} == {day}, zone


# --- The one rule of the periods ----------------------------------------------------------------


@pytest.mark.story("US-2670")
def test_a_period_inverted_or_starting_after_its_end_is_refused_by_one_rule_on_the_six_views(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Une période inversée, ou qui commence après sa fin par défaut, est refusée par 422
    # (PortfolioPeriodRefused), par une seule règle pour les six vues qui prennent une période. »
    # The workload and the health of the control take none: what they are sent is not read.
    inverted = [("/query/to", "VALUE_OUT_OF_RANGE", {"minimum": "2026-03-31"})]
    after = [("/query/from", "VALUE_OUT_OF_RANGE", {"maximum": str(READ_ON)})]
    before = [("/query/to", "VALUE_OUT_OF_RANGE", {"minimum": "2025-06-04"})]
    for view in PERIODIC:
        assert refusal(api, fabrics, view, "from=2026-03-31&to=2026-01-01") == inverted, view
        assert refusal(api, fabrics, view, f"as_of={READ_ON}&from=2026-09-01") == after, view
        assert refusal(api, fabrics, view, f"as_of={READ_ON}&to=2025-01-01") == before, view
    reader = fabrics.stage.reader
    for view in ("workload", "pilot-health"):
        plain = served(api, reader, view, f"{READ}")
        assert served(api, reader, view, f"{READ}&from=2026-03-31&to=2026-01-01") == plain, view


@pytest.mark.story("US-2670")
@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_period_of_the_performance_is_bounded_to_five_years_and_no_other_view_is(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # #4176: beyond five years, 422 ``VALUE_OUT_OF_RANGE`` on the period, ``/query/to`` with the
    # last end admitted, ``/query/from`` with the first start when the start alone is sent; five
    # years exactly is read. The 29 February stands in as the 28th. The contract's example is what
    # the service answers. The other five views take a period of any length.
    reader = fabrics.stage.reader
    base = f"as_of={READ_ON}"
    too_long = refusal(api, fabrics, "performance", f"{base}&from=2020-01-01&to=2026-06-03")
    assert too_long == [("/query/to", "VALUE_OUT_OF_RANGE", {"maximum": "2025-01-01"})]
    example = contract_example()
    assert (example["code"], example["status"]) == ("VALIDATION_FAILED", 422)
    assert [
        (each["pointer"], each["code"], each["params"]) for each in example["fields"]
    ] == too_long
    assert refusal(api, fabrics, "performance", f"{base}&from=2020-01-01") == [
        ("/query/from", "VALUE_OUT_OF_RANGE", {"minimum": "2021-06-03"})
    ]
    assert refusal(api, fabrics, "performance", f"{base}&to=2032-01-01") == [
        ("/query/to", "VALUE_OUT_OF_RANGE", {"maximum": "2030-06-04"})
    ]
    assert refusal(api, fabrics, "performance", f"{base}&from=2024-02-29&to=2029-03-01") == [
        ("/query/to", "VALUE_OUT_OF_RANGE", {"maximum": "2029-02-28"})
    ]
    assert refusal(api, fabrics, "performance", "as_of=2028-02-29&from=2020-01-01") == [
        ("/query/from", "VALUE_OUT_OF_RANGE", {"minimum": "2023-03-01"})
    ]
    five = served(api, reader, "performance", f"{base}&from=2021-06-03&to=2026-06-03")
    assert (five["scope"]["from"], five["scope"]["to"]) == ("2021-06-03", "2026-06-03")
    assert len(five["quarterly"]) == 21
    leap = served(api, reader, "performance", f"{base}&from=2024-02-29&to=2029-02-28")
    assert leap["scope"]["to"] == "2029-02-28"
    for view in ("projects", "value", "cost-structure", "risks"):
        long_period = served(api, reader, view, f"{base}&from=2010-01-01&to=2026-06-03")
        assert long_period["scope"]["from"] == "2010-01-01", view


@pytest.mark.requirement("WF-PTF-0110-A")
def test_the_health_of_the_control_reads_neither_from_nor_to(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # #4333 : « from » and « to » are no parameter of the view (``PeriodlessQuery``): sent, they
    # change nothing of the answer, the scope giving no period.
    reader = fabrics.stage.reader
    plain = served(api, reader, "pilot-health", READ)
    sent = served(api, reader, "pilot-health", f"{READ}&from=2026-05-01&to=2026-05-31")
    assert sent == plain
    assert plain["scope"]["from"] is None
    assert plain["signals"]


# --- The offer lost on 15 March ------------------------------------------------------------------


@pytest.mark.requirement("WF-CYC-0130-A")
def test_an_offer_lost_on_15_march_is_among_the_offers_closed_of_the_periods_that_hold_the_day(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Un projet passé à Perdu le 15 mars compte parmi les offres closes de mars et d'aucun autre
    # mois. » Read on the service, by the rate of conversion of the value: the offer lost on the
    # 15th enters its denominator — a rate of nought, none of the offers closed having been won —
    # for a period that holds the day, its bounds included, and for no other.
    assert LOST_ON.date() == date(2026, 3, 15)
    reader = fabrics.stage.reader

    def rate(period: str) -> dict[str, Any]:
        found: dict[str, Any] = served(api, reader, "value", f"as_of={READ_ON}&{period}")
        return found["conversion_rate"]

    closed = {"is_computable": True, "value": "0", "reason": None}
    absent = {"is_computable": False, "value": None, "reason": "no_offer_out_of_pricing"}
    for period in (
        "from=2026-03-15&to=2026-03-15",
        "from=2026-03-01&to=2026-03-31",
        "from=2026-03-15&to=2026-04-01",
        "from=2026-02-20&to=2026-03-15",
    ):
        assert rate(period) == closed, period
    for period in (
        "from=2026-03-16&to=2026-03-31",
        "from=2026-03-01&to=2026-03-14",
        "from=2026-02-01&to=2026-02-28",
        "from=2026-04-01&to=2026-04-30",
    ):
        assert rate(period) == absent, period
    # The two offers won on 19 January are the other offers closed of the fabrics.
    january = rate("from=2026-01-19&to=2026-01-19")
    assert (january["is_computable"], january["value"]) == (True, "1")
    assert rate("from=2026-01-01&to=2026-03-31")["value"] == "0.6667"


# --- The review just marked ----------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0010-A")
def test_a_project_whose_review_was_just_marked_with_no_revision_in_progress_contributes_by_it(
    api: ContractClient, database: Database, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Un projet dont la revue vient d'être marquée et qui n'a pas de révision en cours contribue
    # par cette revue » : on the current day, by its last revision marked, recalculated with the
    # actual cost of the day — an import of 100 made after the marking —, in the list and in the
    # performance as ``getProjectIndicators`` gives it; at a past date, by what the marking kept.
    now_is(monkeypatch)
    running = fabrics.in_progress.project_id
    with database.transaction() as session:
        assert current_revision(session, running) is None
    load_import(fabrics.stage, running, [cost("FA-3001", None, "100.00")], at=NOW)
    reader = fabrics.stage.reader
    own = api.get(f"/api/v1/projects/{running}/indicators", headers=reader.headers).json()
    assert own["actual_cost"] == "100.00"
    [row] = served(api, reader, "projects", "")["items"]
    performance = served(api, reader, "performance", "")
    assert row["project_id"] == str(running)
    assert row["reference_budget"] == own["reference_budget"] == performance["reference_budget"]
    assert row["cost_index"] == own["cost_index"] == performance["cost_index"]
    assert row["cost_index"]["value"]["is_computable"] is True
    assert performance["cost_variance"] == own["cost_variance"]
    kept = served(api, reader, "performance", f"as_of={READ_ON}")
    assert kept["cost_index"]["value"]["reason"] == "no_actual_cost"


# --- The estimate and the indicators of a project, at 0 % and at 100 % ---------------------------


@pytest.mark.requirement("WF-PRJ-0090-A")
def test_the_estimate_and_the_indicators_of_a_project_marked_at_0_and_at_100_percent_are_the_same(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # « Le devis et les indicateurs du projet lui-même sont identiques à 0 % et à 100 %. » The
    # probability is a weight of the portfolio and no figure of a project. An offer In pricing,
    # whose probability the API writes at 0 % then at 100 %, gives the same
    # ``getEstimateIndicators`` and ``getRemainingIndicators``; and two projects In progress
    # written alike, with the same cost imported, the probability written while each was an offer —
    # the one at 0 %, the other at 100 % — give the same three indicators.
    now_is(monkeypatch)
    reader = fabrics.stage.reader

    def indicators(project_id: UUID, names: tuple[str, ...]) -> dict[str, Any]:
        found: dict[str, Any] = {}
        for name in names:
            answer = api.get(f"/api/v1/projects/{project_id}/{name}", headers=reader.headers)
            assert answer.status_code == 200, (name, answer.text)
            found[name] = answer.json()
        return found

    offer, _ = offer_being_priced(api, fabrics, "Offre à pondérer", Decimal(0))
    read_at = {}
    for probability in (Decimal(0), Decimal(1)):
        probability_written(fabrics, offer, probability)
        read_at[probability] = indicators(offer, INDICATORS[:2])
    assert anonymous(read_at[Decimal(0)]) == anonymous(read_at[Decimal(1)])
    at_nought = another_in_progress(api, fabrics, "Chantier jumeau", "PRJ-2680", Decimal(0))
    at_one = another_in_progress(api, fabrics, "Chantier jumeau", "PRJ-2681", Decimal(1))
    for number, project_id in enumerate((at_nought, at_one)):
        load_import(fabrics.stage, project_id, [cost(f"FA-4{number}", None, "100.00")])
    found = {each: indicators(each, INDICATORS) for each in (at_nought, at_one)}
    assert anonymous(found[at_nought]) == anonymous(found[at_one])
    assert Decimal(found[at_one]["indicators"]["actual_cost"]) > 0


# --- The numbers of a query ----------------------------------------------------------------------


@pytest.mark.story("US-2670")
def test_a_number_written_in_other_digits_than_0_to_9_is_refused_as_the_contract_would_refuse_it(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # #4293 : ``\d`` takes the digits of every script (here the Arabic-Indic ones); the contract
    # writes ``[0-9]``. The horizon of the workload and of the S-curve, the threshold of the
    # workload and a bound of the list are refused as numbers that are none (``NUMBER_INVALID``),
    # the ASCII ones read.
    arabic = quote("\u0661\u0662")
    half = quote("\u0660.\u0665")
    assert refusal(api, fabrics, "workload", f"horizon_months={arabic}") == [
        ("/query/horizon_months", "NUMBER_INVALID", None)
    ]
    assert refusal(api, fabrics, "cost-curve", f"horizon_months={arabic}") == [
        ("/query/horizon_months", "NUMBER_INVALID", None)
    ]
    assert refusal(api, fabrics, "workload", f"under_load_threshold={half}") == [
        ("/query/under_load_threshold", "NUMBER_INVALID", None)
    ]
    assert refusal(api, fabrics, "projects", f"win_probability_min={half}") == [
        ("/query/win_probability_min", "NUMBER_INVALID", None)
    ]
    reader = fabrics.stage.reader
    assert served(api, reader, "workload", "horizon_months=12&under_load_threshold=0.5")["months"]
    assert served(api, reader, "projects", "win_probability_min=0.5")["items"] == []


# --- The day of the load, in the time zone of the installation -----------------------------------


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_day_the_load_is_counted_from_is_read_in_the_time_zone_of_the_installation(
    api: ContractClient, database: Database, fabrics: Portfolio
) -> None:
    # #4281 : the remaining of a marked revision is counted from the day of its marking, that of
    # the current revision from the day of the reading, both in the time zone of the installation —
    # as the key of the day and the curves of the offers read it. In Honolulu (UTC-10), the review
    # marked on 2 March at nine in the morning, universal time, is that of 1 March at 23:00, and
    # 08:30 on 3 June is 22:30 on 2 June: the days before midnight, not those of Greenwich.
    TIME_ZONE.read_from(lambda: "Pacific/Honolulu")
    running = fabrics.in_progress
    manager = fabrics.stage.manager.user_id
    viewer = Viewer(manager, MANAGING)
    review, marked_at = running.marked[REVIEW]
    assert marked_at.date() == date(2026, 3, 2)
    marked = WorkloadAsked(WorkloadBasis.MARKED_REMAINING, review, None, NOW, viewer)
    with database.transaction() as session:
        found = reading_of(session, running.project_id, marked)
    assert found is not None
    assert found.as_of == date(2026, 3, 1)
    revision_opened(api, fabrics, running.project_id, datetime(2026, 6, 1, 9, 0, tzinfo=UTC))
    morning = datetime(2026, 6, 3, 8, 30, tzinfo=UTC)
    current = WorkloadAsked(WorkloadBasis.CURRENT_REMAINING, None, None, morning, viewer)
    with database.transaction() as session:
        found = reading_of(session, running.project_id, current)
    assert found is not None
    assert found.as_of == date(2026, 6, 2)
