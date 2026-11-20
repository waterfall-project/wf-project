# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The S-curve of the portfolio, served (``getPortfolioCostCurve``; US-2740).

The curves the markings of the projects of the fabrics (``portfolio_support``) kept — the documents
``cost_curve`` and ``cost_curve_payment_delays`` of a project, ``portfolio_offer_curves`` of an
offer — are set to the series of the sentence under test, as a marking would have kept them, then
read at a past date, the 3rd of June 2026, the date of the witness; the current day is read against
what the day computes, and against ``getCostCurve`` of each project. Every answer is validated
against the contract by the client of the tests.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from portfolio_listing_support import READ, example, kept_changed, read, revision_of, served
from portfolio_support import Portfolio, another_in_progress, another_offer, portfolio
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import delete, text, update

from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.portfolio.interface import (
    PortfolioAsked,
    PortfolioReading,
    read_portfolio_cost_curve,
)
from waterfall.core.revisions.interface import last_marked_revision
from waterfall.core.revisions.tables import Revision
from waterfall.platform.cache import PREFIX, IndicatorsCache

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from realm import TestRealm
    from redis import Redis
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

# The current day of the tests of the day, after the whole chronology of the fabrics.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
AS_OF = date(2026, 6, 3)
# The twelve months before June 2026 and the six from it: the days the budget is read at.
ENDS = [
    "2025-06-30",
    "2025-07-31",
    "2025-08-31",
    "2025-09-30",
    "2025-10-31",
    "2025-11-30",
    "2025-12-31",
    "2026-01-31",
    "2026-02-28",
    "2026-03-31",
    "2026-04-30",
    "2026-05-31",
    "2026-06-30",
    "2026-07-31",
    "2026-08-31",
    "2026-09-30",
    "2026-10-31",
    "2026-11-30",
]
type Points = dict[str, str]


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def series(name: str, points: Points) -> dict[str, Any]:
    """Write a series of a ``CurveSeries``: its name and its points, by date."""
    return {
        "name": name,
        "points": [{"date": day, "amount": amount} for day, amount in points.items()],
    }


def curve(
    budget: Points,
    actual: Points,
    projection: Points,
    cash_out: Mapping[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """Write a document ``cost_curve`` the way a marking kept it, the cash-out by month if given."""
    return {
        "context": {},
        "payment_delays": cash_out is not None,
        "series": [
            series("reference_budget", budget),
            series("actual_cost", actual),
            series("project_manager_projection", projection),
        ],
        "steps": [],
        "cash_out_by_month": None
        if cash_out is None
        else [
            {"month": month, "past": past, "forecast": forecast}
            for month, (past, forecast) in cash_out.items()
        ],
    }


def keep(owner: Engine, revision_id: UUID, kind: str, document: dict[str, Any]) -> None:
    """Set the document of a kind a marked revision kept, as a superuser around the service."""
    kept_changed(owner, revision_id, kind, lambda _: document)


def keep_offer(
    owner: Engine, revision_id: UUID, plain: dict[str, Any], delayed: dict[str, Any]
) -> None:
    """Set the curves of an offer a marked revision kept: without and with the payment delays."""
    keep(
        owner,
        revision_id,
        "portfolio_offer_curves",
        {"cost_curve": plain, "cost_curve_payment_delays": delayed},
    )


def curves(api: ContractClient, fabrics: Portfolio, query: str = READ) -> dict[str, Any]:
    """Read the S-curve as the manager that reads the portfolio does; the contract judges it."""
    return served(api, fabrics.stage.reader, "cost-curve", query)


def points(body: dict[str, Any], name: str) -> Points:
    """Give the points of a series of an answer, by date."""
    found = [each for each in body["series"] if each["name"] == name]
    assert len(found) == 1
    return {each["date"]: each["amount"] for each in found[0]["points"]}


def second_project(api: ContractClient, fabrics: Portfolio) -> UUID:
    """Write a second project In progress, and give the revision its review marked."""
    project_id = another_in_progress(api, fabrics, "Second chantier", "PRJ-2740")
    with fabrics.stage.database.transaction() as session:
        revision = last_marked_revision(session, project_id)
    assert revision is not None
    return revision


def forget(
    owner: Engine,
    revision_id: UUID,
    kinds: tuple[str, ...] = ("cost_curve", "cost_curve_payment_delays"),
) -> None:
    """Remove the curves a marked revision kept, as a revision marked before In progress has."""
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(
            delete(RevisionIndicator).where(
                RevisionIndicator.revision_id == revision_id,
                RevisionIndicator.kind.in_(kinds),
            )
        )


FIRST = curve(
    {
        "2026-04-30": "100.00",
        "2026-05-31": "200.00",
        "2026-06-30": "300.00",
        "2026-07-31": "400.00",
    },
    {"2026-04-30": "60.00", "2026-05-31": "120.00", "2026-06-03": "130.00"},
    {"2026-06-03": "130.00", "2026-06-30": "250.00", "2026-07-31": "400.00"},
)
SECOND = curve(
    {"2026-05-31": "10.00", "2026-06-30": "30.00"},
    {"2026-05-31": "5.00", "2026-06-03": "8.00"},
    {"2026-06-03": "8.00", "2026-06-30": "20.00", "2026-07-31": "30.00"},
)
# The cash-out the two projects keep, by month: one with a month negative (a credit).
FIRST_DELAYED = curve(
    {"2026-05-31": "50.00", "2026-06-30": "150.00"},
    {"2026-04-30": "60.00", "2026-06-03": "130.00"},
    {"2026-06-03": "130.00", "2026-06-30": "200.00", "2026-07-31": "380.00"},
    {
        "2026-05": ("40.00", "0.00"),
        "2026-06": ("30.00", "70.00"),
        "2026-07": ("0.00", "-20.00"),
    },
)
SECOND_DELAYED = curve(
    {"2026-06-30": "12.00"},
    {"2026-06-03": "8.00"},
    {"2026-06-03": "8.00", "2026-07-31": "25.00"},
    {"2026-06": ("8.00", "5.00"), "2026-07": ("0.00", "12.00")},
)


def two_projects(api: ContractClient, owner: Engine, fabrics: Portfolio) -> tuple[UUID, UUID]:
    """Set the curves of the two projects In progress, with and without the payment delays."""
    first, second = revision_of(fabrics, "running"), second_project(api, fabrics)
    for revision, plain, delayed in (
        (first, FIRST, FIRST_DELAYED),
        (second, SECOND, SECOND_DELAYED),
    ):
        keep(owner, revision, "cost_curve", plain)
        keep(owner, revision, "cost_curve_payment_delays", delayed)
    return first, second


# --- The sums ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0100-A")
def test_each_point_of_the_curve_is_the_sum_of_the_points_of_the_projects_for_each_curve(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Chaque point de la courbe agrégée égale la somme des points de ce mois sur les projets du
    # périmètre, pour chacune des trois courbes et en mode décaissement » : the budget at the end of
    # each month — a curve stands at its last point, nought before its first —, the actual cost up
    # to the date, the projection from it; nothing is recalculated.
    two_projects(api, owner, fabrics)
    body = curves(api, fabrics)
    assert body["payment_delays"] is False
    assert body["cash_out_by_month"] is None
    assert body["scope"]["project_count"] == 2
    budget = points(body, "reference_budget")
    assert list(budget) == ENDS
    assert {day: budget[day] for day in ENDS[9:]} == {
        "2026-03-31": "0.00",
        "2026-04-30": "100.00",
        "2026-05-31": "210.00",
        "2026-06-30": "330.00",
        "2026-07-31": "430.00",
        "2026-08-31": "430.00",
        "2026-09-30": "430.00",
        "2026-10-31": "430.00",
        "2026-11-30": "430.00",
    }
    assert set(list(budget.values())[:9]) == {"0.00"}
    assert points(body, "actual_cost") == dict.fromkeys(ENDS[:10], "0.00") | {
        "2026-04-30": "60.00",
        "2026-05-31": "125.00",
        "2026-06-03": "138.00",
    }
    assert points(body, "project_manager_projection") == {
        "2026-06-03": "138.00",
        "2026-06-30": "270.00",
        "2026-07-31": "430.00",
        "2026-08-31": "430.00",
        "2026-09-30": "430.00",
        "2026-10-31": "430.00",
        "2026-11-30": "430.00",
    }


@pytest.mark.requirement("WF-PTF-0100-A")
def test_with_the_payment_delays_the_series_are_the_cash_out_and_the_detail_is_by_month(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « avec payment_delays, les séries sont celles des décaissements de chaque
    # projet, et cash_out_by_month en rend le détail par mois, un mois pouvant être négatif ; sans
    # lui, ce champ est nul » : the series of the cash-out, a month of the window none holds being
    # nought, the past and the forecast summed apart.
    two_projects(api, owner, fabrics)
    body = curves(api, fabrics, f"{READ}&payment_delays=true")
    assert body["payment_delays"] is True
    assert points(body, "reference_budget")["2026-06-30"] == "162.00"
    assert points(body, "reference_budget")["2026-05-31"] == "50.00"
    assert points(body, "actual_cost")["2026-06-03"] == "138.00"
    assert points(body, "project_manager_projection")["2026-07-31"] == "405.00"
    detail = {each["month"]: (each["past"], each["forecast"]) for each in body["cash_out_by_month"]}
    assert list(detail) == [day[:7] for day in ENDS]
    assert detail["2026-05"] == ("40.00", "0.00")
    assert detail["2026-06"] == ("38.00", "75.00")
    assert detail["2026-07"] == ("0.00", "-8.00")
    assert detail["2026-08"] == ("0.00", "0.00")
    assert detail["2025-06"] == ("0.00", "0.00")
    assert curves(api, fabrics, f"{READ}&payment_delays=false")["cash_out_by_month"] is None


@pytest.mark.story("US-2740")
def test_a_project_that_kept_no_curves_adds_nothing_and_is_not_an_error(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # A revision marked before the project was In progress keeps no curve: nothing is taken up nor
    # recalculated, and the project is retained by its state all the same.
    first, second = two_projects(api, owner, fabrics)
    forget(owner, second)
    body = curves(api, fabrics)
    assert body["scope"]["project_count"] == 2
    assert points(body, "reference_budget")["2026-06-30"] == "300.00"
    assert points(body, "actual_cost")["2026-06-03"] == "130.00"
    assert first != second


@pytest.mark.requirement("WF-PTF-0100-A")
def test_the_sum_is_that_of_the_curves_getcostcurve_gives_of_each_project_at_the_date(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Rien n'est recalculé : la vue somme les séries que getCostCurve rend de chaque projet » : on
    # the curves the markings really kept, the portfolio of the project In progress and of the one
    # Completed is, point by point, the sum of the two answers of ``getCostCurve`` at that date.
    del owner
    projects = [fabrics.in_progress.project_id, fabrics.completed.project_id]
    query = f"{READ}&states=in_progress,completed"
    for delays in (False, True):
        flag = "true" if delays else "false"
        body = curves(api, fabrics, f"{query}&payment_delays={flag}")
        assert body["scope"]["project_count"] == 2
        each_one = [
            api.get(
                f"/api/v1/projects/{project}/indicators/cost-curve?as_of={AS_OF}&payment_delays={flag}",
                headers=fabrics.stage.reader.headers,
            ).json()
            for project in projects
        ]
        for name in ("reference_budget", "actual_cost", "project_manager_projection"):
            held = points(body, name)
            assert held
            # At each day where every project has a point of its own, the sum of those points: no
            # rule of reading between two points is assumed here (``value_at`` has its own tests).
            common = [day for day in held if all(day in points(one, name) for one in each_one)]
            assert common, name
            for day in common:
                expected = sum((Decimal(points(one, name)[day]) for one in each_one), Decimal(0))
                assert Decimal(held[day]) == expected, (name, day)
        assert any(Decimal(amount) != 0 for amount in points(body, "reference_budget").values())


@pytest.mark.story("US-2740")
def test_a_curve_over_keeps_its_cumulative_and_one_that_starts_late_is_nought(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : a curve is read at its last point on or before each day. A project whose
    # curve ends in September 2025 keeps its cumulative to the end of the window; one whose curve
    # starts in October 2026 is nought until then. The expected values are written by hand.
    first, second = two_projects(api, owner, fabrics)
    keep(owner, first, "cost_curve", curve({"2025-08-31": "50.00", "2025-09-30": "70.00"}, {}, {}))
    keep(owner, second, "cost_curve", curve({"2026-10-31": "5.00"}, {}, {}))
    budget = points(curves(api, fabrics), "reference_budget")
    assert budget == {
        "2025-06-30": "0.00",
        "2025-07-31": "0.00",
        "2025-08-31": "50.00",
        **dict.fromkeys(ENDS[3:16], "70.00"),
        "2026-10-31": "75.00",
        "2026-11-30": "75.00",
    }


@pytest.mark.requirement("WF-PTF-0100-A")
def test_a_project_completed_read_on_the_current_day_is_what_get_cost_curve_gives_it(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without a date, a project Completed is read as the day computes it, whatever its state:
    # the portfolio of the sole project Completed is, at each end of month its curve holds, the
    # answer of ``getCostCurve``, and keeps its cumulative after its last point.
    monkeypatch.setattr("waterfall.api.portfolio_cost_curve.utc_now", lambda: NOW)
    monkeypatch.setattr("waterfall.api.indicator_curves.utc_now", lambda: NOW)
    own = api.get(
        f"/api/v1/projects/{fabrics.completed.project_id}/indicators/cost-curve",
        headers=fabrics.stage.reader.headers,
    ).json()
    body = curves(api, fabrics, "states=completed")
    assert body["scope"]["as_of"] == "2026-11-19"
    assert body["scope"]["project_count"] == 1
    for name in ("reference_budget", "actual_cost", "project_manager_projection"):
        held, theirs = points(body, name), points(own, name)
        shared = [day for day in held if day in theirs]
        assert shared, name
        assert all(held[day] == theirs[day] for day in shared), name
    budget, theirs = points(body, "reference_budget"), points(own, "reference_budget")
    assert Decimal(theirs[max(theirs)]) > 0
    assert budget["2027-04-30"] == theirs[max(theirs)]


@pytest.mark.story("US-2740")
def test_each_project_is_rounded_once_before_the_sum_not_the_sum_once(
    owner: Engine, api: ContractClient, fabrics: Portfolio
) -> None:
    # Two offers at a probability of 0.333, each with a budget of 0.50: each part is 0.1665, which
    # rounds to 0.17, so the sum is 0.34; the sum, 1.00, weighted once would be 0.33.
    other = another_offer(api, fabrics, "Seconde extension", Decimal("0.4"))
    held = {"2026-07-31": "0.50"}
    for revision in (revision_of(fabrics, "offer"), other):
        keep_probability(owner, revision, Decimal("0.333"))
        keep_offer(owner, revision, curve(held, {}, {}), curve(held, {}, {}, {}))
    body = curves(api, fabrics, f"{READ}&states=pricing")
    assert body["scope"]["project_count"] == 2
    assert points(body, "reference_budget")["2026-07-31"] == "0.34"


# --- The offers ----------------------------------------------------------------------------------


def offer_of(data: dict[str, Any], *, delayed: bool = False) -> dict[str, Any]:
    """Write the curves of an offer from the fixture of its example: its budget and its projection.

    The budget at the end of July and of August, the projection from the date of calculation on a
    base of nought — an offer has paid nothing — then at the same two ends, its actual cost empty.
    """
    first, last = data["budget_curve"]
    ahead, end = data["projection_curve"]
    return curve(
        {"2026-07-31": first, "2026-08-31": last},
        {},
        {"2026-06-03": "0.00", "2026-07-31": ahead, "2026-08-31": end},
        {"2026-07": ("0.00", ahead), "2026-08": ("0.00", end)} if delayed else None,
    )


def keep_probability(owner: Engine, revision_id: UUID, probability: Decimal | None) -> None:
    """Set the probability of winning a marked revision kept, none for a marking before EP-07."""
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(
            update(Revision).where(Revision.id == revision_id).values(win_probability=probability)
        )


@pytest.mark.requirement("WF-PTF-0100-A")
def test_an_offer_at_40_percent_contributes_40_percent_of_its_curves_when_it_is_included(
    owner: Engine, api: ContractClient, fabrics: Portfolio
) -> None:
    # « Un projet en chiffrage à 40 % contribue pour 40 % de ses courbes lorsqu'il est inclus » —
    # the same fixture as the harness (``tests/examples``): the offer of the fabrics keeps 40 % at
    # its marking, and the curves of its current estimate; asked alone or with the projects In
    # progress, it adds 40 % of each of its points, each part rounded once, and nothing otherwise.
    data = example("WF-PTF-0100-A#b4875ef04969")
    offer = revision_of(fabrics, "offer")
    keep_offer(owner, offer, offer_of(data), offer_of(data, delayed=True))
    keep(owner, revision_of(fabrics, "running"), "cost_curve", FIRST)
    without = curves(api, fabrics)
    assert points(without, "reference_budget")["2026-07-31"] == "400.00"
    included = curves(api, fabrics, f"{READ}&states=in_progress,pricing")
    assert included["scope"]["states"] == ["in_progress", "pricing"]
    assert included["scope"]["project_count"] == 2
    budget = points(included, "reference_budget")
    first, last = (Decimal(each) for each in data["weighted_budget_curve"])
    assert (budget["2026-07-31"], budget["2026-08-31"]) == (
        str(Decimal("400.00") + first),
        str(Decimal("400.00") + last),
    )
    alone = curves(api, fabrics, f"{READ}&states=pricing")
    assert alone["scope"]["project_count"] == 1
    assert points(alone, "reference_budget")["2026-07-31"] == str(first)
    # The actual cost of an offer is empty: it adds nothing before the date of calculation.
    assert set(points(alone, "actual_cost").values()) == {"0.00"}
    delayed = curves(api, fabrics, f"{READ}&states=pricing&payment_delays=true")
    assert points(delayed, "reference_budget")["2026-08-31"] == str(last)
    detail = {each["month"]: each["forecast"] for each in delayed["cash_out_by_month"]}
    assert (detail["2026-07"], detail["2026-08"]) == ("30.00", "60.00")


@pytest.mark.requirement("WF-PTF-0100-A")
def test_an_offer_included_at_40_percent_of_100_and_a_provision_of_50_adds_40_and_60(
    owner: Engine, api: ContractClient, fabrics: Portfolio
) -> None:
    # « Une offre incluse à 40 %, dont le devis porte 100 hors provisions et une provision de 50,
    # apporte 40 au budget cumulé final et 60 à la projection » — the same on the service, from the
    # same fixture: the budget of the offer ends at 100 without the provisions, its projection at
    # 150 with them.
    data = example("WF-PTF-0100-A#faac2b71539d")
    offer = revision_of(fabrics, "offer")
    keep_offer(owner, offer, offer_of(data), offer_of(data, delayed=True))
    body = curves(api, fabrics, f"{READ}&states=pricing")
    assert body["scope"]["project_count"] == 1
    assert list(points(body, "reference_budget"))[-1] == "2026-11-30"
    assert points(body, "reference_budget")["2026-11-30"] == data["final_budget"]
    assert points(body, "project_manager_projection")["2026-11-30"] == data["final_projection"]
    assert (data["final_budget"], data["final_projection"]) == ("40.00", "60.00")


@pytest.mark.story("US-2740")
def test_an_offer_with_no_curves_or_no_probability_adds_nothing_and_is_not_an_error(
    owner: Engine, api: ContractClient, fabrics: Portfolio
) -> None:
    # A revision marked before EP-07 keeps no probability of winning, one marked before EP-11 no
    # curves of an offer: the offer is retained by its state and adds to no sum.
    data = example("WF-PTF-0100-A#faac2b71539d")
    offer = revision_of(fabrics, "offer")
    keep_offer(owner, offer, offer_of(data), offer_of(data, delayed=True))
    keep_probability(owner, offer, None)
    body = curves(api, fabrics, f"{READ}&states=pricing")
    assert body["scope"]["project_count"] == 1
    assert set(points(body, "reference_budget").values()) == {"0.00"}
    keep_probability(owner, offer, Decimal("0.4"))
    forget(owner, offer, ("portfolio_offer_curves",))
    again = curves(api, fabrics, f"{READ}&states=pricing")
    assert again["scope"]["project_count"] == 1
    assert set(points(again, "reference_budget").values()) == {"0.00"}


# --- The months ----------------------------------------------------------------------------------


@pytest.mark.story("US-2740")
def test_the_curve_runs_twelve_months_before_that_of_the_date_then_the_horizon_from_it(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US : « la courbe court sur les douze mois qui précèdent celui de la date de calcul,
    # puis sur horizon_months mois à partir de lui, six par défaut » : eighteen months by default,
    # from June 2025 to November 2026; the actual cost stops at the date and the projection starts
    # at it, in a month it ends and in a month it does not.
    by_default = curves(api, fabrics)
    assert list(points(by_default, "reference_budget")) == ENDS
    assert list(points(by_default, "actual_cost")) == [*ENDS[:12], "2026-06-03"]
    assert list(points(by_default, "project_manager_projection")) == ["2026-06-03", *ENDS[12:]]
    turned = curves(api, fabrics, "as_of=2026-10-15&horizon_months=3")
    months = list(points(turned, "reference_budget"))
    assert (months[0], months[-1], len(months)) == ("2025-10-31", "2026-12-31", 15)
    assert list(points(turned, "actual_cost"))[-2:] == ["2026-09-30", "2026-10-15"]
    assert list(points(turned, "project_manager_projection")) == [
        "2026-10-15",
        "2026-10-31",
        "2026-11-30",
        "2026-12-31",
    ]
    # On the last day of a month it is a point of both, once: the actual cost ends at it, the
    # projection starts at it.
    ended = curves(api, fabrics, "as_of=2025-12-31&horizon_months=1")
    assert list(points(ended, "reference_budget"))[0::12] == ["2024-12-31", "2025-12-31"]
    assert list(points(ended, "actual_cost"))[-2:] == ["2025-11-30", "2025-12-31"]
    assert list(points(ended, "project_manager_projection")) == ["2025-12-31"]
    longest = curves(api, fabrics, f"{READ}&horizon_months=240")
    assert len(points(longest, "reference_budget")) == 252


@pytest.mark.story("US-2740")
def test_the_period_chooses_the_projects_completed_and_bounds_no_month(
    owner: Engine, api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US : « la période ne borne pas ses mois, elle choisit les projets terminés » : the
    # project Completed on 15 April is retained by the default period, which the scope gives back;
    # a period that does not hold the day leaves it out, and the months are the same.
    keep(owner, revision_of(fabrics, "completed"), "cost_curve", SECOND)
    states = f"{READ}&states=completed"
    inside = curves(api, fabrics, states)
    assert inside["scope"]["project_count"] == 1
    assert (inside["scope"]["from"], inside["scope"]["to"]) == ("2025-06-04", "2026-06-03")
    assert points(inside, "reference_budget")["2026-06-30"] == "30.00"
    outside = curves(api, fabrics, f"{states}&from=2026-05-01&to=2026-05-31")
    assert outside["scope"]["project_count"] == 0
    assert (outside["scope"]["from"], outside["scope"]["to"]) == ("2026-05-01", "2026-05-31")
    assert points(outside, "reference_budget") == dict.fromkeys(ENDS, "0.00")
    assert list(points(outside, "reference_budget")) == list(points(inside, "reference_budget"))
    # Not asked, the project Completed adds nothing to the view by default.
    assert curves(api, fabrics)["scope"]["project_count"] == 1


# --- The dates -----------------------------------------------------------------------------------


@pytest.mark.story("US-2740")
def test_at_a_past_date_the_curves_are_those_the_markings_kept_not_those_the_day_computes(
    owner: Engine, api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US : « à une date passée, la vue somme les courbes que les révisions marquées ont
    # conservées (EP-10, et US-2680 pour une offre) » : what a marking kept is read as it is.
    running = revision_of(fabrics, "running")
    keep(owner, running, "cost_curve", FIRST)
    body = curves(api, fabrics)
    assert points(body, "reference_budget")["2026-07-31"] == "400.00"
    assert points(body, "actual_cost")["2026-06-03"] == "130.00"
    keep(owner, running, "cost_curve", SECOND)
    assert points(curves(api, fabrics), "reference_budget")["2026-07-31"] == "30.00"


@pytest.mark.requirement("WF-PTF-0100-A")
def test_on_the_current_day_the_curve_is_what_get_cost_curve_gives_and_an_offer_is_weighted(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without a date, the day: the project In progress gives the curves ``getCostCurve`` gives it on
    # the current day, and the offer, weighted by its 40 %, those of its estimate — the document the
    # day computes, as a marking would keep it (``offer_curves``).
    monkeypatch.setattr("waterfall.api.portfolio_cost_curve.utc_now", lambda: NOW)
    monkeypatch.setattr("waterfall.api.indicator_curves.utc_now", lambda: NOW)
    for flag in ("false", "true"):
        own = api.get(
            f"/api/v1/projects/{fabrics.in_progress.project_id}/indicators/cost-curve"
            f"?payment_delays={flag}",
            headers=fabrics.stage.reader.headers,
        ).json()
        body = curves(api, fabrics, f"payment_delays={flag}")
        assert body["scope"]["as_of"] == "2026-11-19"
        assert body["scope"]["project_count"] == 1
        budget = points(body, "reference_budget")
        assert (next(iter(budget)), list(budget)[-1]) == ("2025-11-30", "2027-04-30")
        held = points(own, "reference_budget")
        shared = [day for day in budget if day in held]
        assert shared
        assert all(budget[day] == held[day] for day in shared)
        # The project keeps the cumulative of its last point after it: its plateau to the horizon.
        assert budget["2027-04-30"] == held[max(held)]
        assert Decimal(budget["2027-04-30"]) > 0
        offer = curves(api, fabrics, f"states=pricing&payment_delays={flag}")
        both = curves(api, fabrics, f"states=in_progress,pricing&payment_delays={flag}")
        assert both["scope"]["project_count"] == 2
        weighted = Decimal(points(offer, "reference_budget")["2027-04-30"])
        assert weighted > 0
        assert Decimal(points(both, "reference_budget")["2027-04-30"]) == (
            Decimal(budget["2027-04-30"]) + weighted
        )


class Written(IndicatorsCache):
    """The cache of the indicators, which records the batches of documents it writes."""

    def __init__(self, client: Redis, ttl: int) -> None:
        """Record nothing yet."""
        super().__init__(client, ttl)
        self.batches: list[set[str]] = []

    def write_many(self, documents: Mapping[str, str]) -> None:
        """Record the keys, then write."""
        self.batches.append(set(documents))
        super().write_many(documents)


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[Written]:
    """Give a cache of the indicators beside the queue; the entries it wrote deleted."""
    opened = Written.of(queue, 300)
    yield opened
    keys = [PREFIX + key for batch in opened.batches for key in batch]
    if keys:
        opened.client.delete(*keys)
    opened.close()


@pytest.mark.story("US-2740")
def test_the_view_reads_the_cache_it_is_given_in_the_reading_of_the_day(
    fabrics: Portfolio, cache: Written
) -> None:
    # The cache given in ``PortfolioReading`` is the one the day is read from: the first reading
    # writes what it computed, the second is served from it and writes nothing.
    reading = PortfolioReading(NOW, cache)
    asked = PortfolioAsked(states=("in_progress", "pricing"))

    def read_day() -> dict[str, Any]:
        with fabrics.stage.database.transaction() as session:
            return dict(
                read_portfolio_cost_curve(
                    session, asked, reading, horizon_months=6, payment_delays=True
                )
            )

    first = read_day()
    written = len(cache.batches)
    assert written >= 1
    assert read_day() == first
    assert len(cache.batches) == written


# --- The refusals --------------------------------------------------------------------------------


@pytest.mark.story("US-2740")
def test_a_horizon_out_of_its_bounds_or_malformed_is_refused_with_the_fault_of_a_state(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # The horizon is from 1 to 240: refused by ``VALUE_OUT_OF_RANGE`` with its bounds, or by
    # ``NUMBER_INVALID`` when it is no number, in the answer of the state's fault.
    for query in ("horizon_months=0", "horizon_months=241"):
        refused = read(api, fabrics.stage.reader, "cost-curve", f"{READ}&{query}")
        assert refused.status_code == 422, query
        fields = refused.json()["fields"]
        assert [(each["pointer"], each["code"]) for each in fields] == [
            ("/query/horizon_months", "VALUE_OUT_OF_RANGE")
        ]
        assert {name: Decimal(str(value)) for name, value in fields[0]["params"].items()} == {
            "minimum": Decimal(1),
            "maximum": Decimal(240),
        }
    query = f"{READ}&horizon_months=abc&states=done"
    refused = read(api, fabrics.stage.reader, "cost-curve", query)
    assert refused.status_code == 422
    assert [(each["pointer"], each["code"]) for each in refused.json()["fields"]] == [
        ("/query/states", "VALIDATION_FAILED"),
        ("/query/horizon_months", "NUMBER_INVALID"),
    ]


@pytest.mark.story("US-2740")
def test_a_period_inverted_is_refused_as_every_view_refuses_it_and_the_view_takes_no_node(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # The period of the view, whose default the scope gives back: the rule of the portfolio, one
    # answer designating the fault (``resolve_scope``). The contract names no node for this view: a
    # node sent is not read, and the scope gives none back.
    query = f"{READ}&from=2026-05-01&to=2026-01-01"
    inverted = read(api, fabrics.stage.reader, "cost-curve", query)
    assert inverted.status_code == 422
    assert [each["pointer"] for each in inverted.json()["fields"]] == ["/query/to"]
    body = curves(api, fabrics, f"{READ}&org_node_id={UUID(int=1)}")
    assert (body["scope"]["org_node_id"], body["scope"]["org_node_label"]) == (None, None)
