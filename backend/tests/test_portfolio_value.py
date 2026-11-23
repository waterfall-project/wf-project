# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the portfolio is worth, served (``getPortfolioValue``; US-2690/L2).

Read through the service on the four projects of the fabrics (``portfolio_support``), at the date of
the witness, 3 June 2026, and on the current day with a period that does not move with the clock;
every answer is validated against the contract by the client of the tests. The order book, the
pipeline gross and weighted, the value delivered by the projects completed in the period, the rate
of conversion; the numeric examples of the document replayed on the service, from their fixtures,
as their tests without a database replay them (``tests/examples``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from portfolio_listing_support import (
    COUNTED,
    EVERY,
    READ,
    example,
    kept_changed,
    read,
    revision_of,
    served,
)
from portfolio_support import Portfolio, at, portfolio
from projects_support import MANAGING, Scene
from projects_support import scene as make_scene
from sqlalchemy import insert

from waterfall.core.projects.interface import (
    ProjectChange,
    Viewer,
    stored_lock_version,
    update_project,
)
from waterfall.core.projects.tables import ProjectStateTransition
from waterfall.platform.audit import Act
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

ESTIMATE, WEIGHTED = "1520.00", "608.00"
PERIOD = "from=2026-01-01"


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def value(api: ContractClient, fabrics: Portfolio, query: str) -> dict[str, Any]:
    """Read the value of the portfolio as the manager of the scene does."""
    return served(api, fabrics.stage.reader, "value", query)


@pytest.mark.requirement("WF-PTF-0050-A")
def test_the_order_book_counts_the_projects_in_progress_the_pipeline_the_projects_in_pricing(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Le carnet ne compte que les projets en cours, le pipeline que les projets en chiffrage » :
    # the order book is the sum of the reference budgets, the pipeline that of the estimates, gross
    # and weighted by the probability of winning, 40 % for the offer of the fabrics; the project
    # completed adds to neither — its figures are the delivered — and nor does the offer lost.
    both = value(api, fabrics, f"{READ}&states=in_progress,pricing")
    assert {name: both[name] for name in ("order_book", "pipeline_gross", "pipeline_weighted")} == {
        "order_book": ESTIMATE,
        "pipeline_gross": ESTIMATE,
        "pipeline_weighted": WEIGHTED,
    }
    assert both["scope"] == {
        "states": ["in_progress", "pricing"],
        "as_of": "2026-06-03",
        "from": "2025-06-04",
        "to": "2026-06-03",
        "org_node_id": None,
        "org_node_label": None,
        "project_count": 2,
    }
    running = value(api, fabrics, READ)
    assert (running["order_book"], running["pipeline_gross"], running["pipeline_weighted"]) == (
        ESTIMATE,
        "0.00",
        "0.00",
    )
    offers = value(api, fabrics, f"{READ}&states=pricing")
    assert (offers["order_book"], offers["pipeline_gross"], offers["pipeline_weighted"]) == (
        "0.00",
        ESTIMATE,
        WEIGHTED,
    )
    every = value(api, fabrics, f"{READ}&states={EVERY}")
    assert every["scope"]["project_count"] == 3
    assert (every["order_book"], every["pipeline_weighted"]) == (ESTIMATE, WEIGHTED)
    # The current day reads the indicators of the day, as the markings kept them at that date.
    today = value(api, fabrics, f"states={COUNTED}&{PERIOD}")
    assert (today["order_book"], today["pipeline_gross"], today["pipeline_weighted"]) == (
        ESTIMATE,
        ESTIMATE,
        WEIGHTED,
    )
    assert today["scope"]["from"] == "2026-01-01"


@pytest.mark.requirement("WF-PTF-0050-A")
def test_an_offer_at_40_percent_counts_for_all_in_the_gross_pipeline_and_40_percent_in_the_weighted(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Une offre à 40 % de probabilité contribue pour tout au pipeline brut et pour 40 % au
    # pipeline pondéré » — the same on the service: the quote of the offer is 100 000, as the
    # example writes it, its probability the 40 % of the fabrics.
    data = example("WF-PTF-0050-A#2495b6b38022")
    assert data["win_probability"] == "0.4"

    def total(document: dict[str, Any]) -> dict[str, Any]:
        figure = {"is_computable": True, "value": data["estimate"], "reason": None}
        return {**document, "total": figure}

    kept_changed(owner, revision_of(fabrics, "offer"), "estimate", total)
    body = value(api, fabrics, f"{READ}&states=pricing")
    assert body["pipeline_gross"] == data["pipeline_gross"]
    assert body["pipeline_weighted"] == data["pipeline_weighted"]


@pytest.mark.requirement("WF-PTF-0050-A")
def test_the_weight_of_an_offer_is_the_probability_its_marking_kept_at_a_date_and_its_own_today(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « La probabilité de gain étant celle que ce marquage a gardée » : the offer, marked at 40 %,
    # is now at 70 % — read on 3 June it weighs 40 %, on the current day 70 %, 1 064.00.
    database = fabrics.stage.database
    manager = fabrics.stage.manager.user_id
    with logging_context(correlation_id="probability"), database.transaction() as session:
        offer = fabrics.offer.project_id
        change = ProjectChange(
            {"win_probability": Decimal("0.70")}, stored_lock_version(session, offer)
        )
        update_project(session, offer, change, Act(manager, at(6, 10)), Viewer(manager, MANAGING))
    assert value(api, fabrics, f"{READ}&states=pricing")["pipeline_weighted"] == WEIGHTED
    assert value(api, fabrics, "states=pricing")["pipeline_weighted"] == "1064.00"
    assert value(api, fabrics, "states=pricing")["pipeline_gross"] == ESTIMATE


@pytest.mark.requirement("WF-PTF-0050-A")
def test_the_delivered_is_the_actual_cost_of_the_projects_completed_in_the_period(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « le réalisé est la somme des coûts réels des projets terminés dans la
    # période ; la période par défaut est celle des douze mois qui finissent à la date de calcul ».
    # The project completed on 15 April has an actual cost of 500 as its marking kept it.
    kept_changed(
        owner,
        revision_of(fabrics, "completed"),
        "project",
        lambda document: {**document, "actual_cost": "500.00"},
    )

    def delivered(query: str) -> str:
        return str(value(api, fabrics, f"{READ}&states={COUNTED}&{query}")["delivered"])

    default = value(api, fabrics, f"{READ}&states=completed")
    assert (default["delivered"], default["scope"]["from"], default["scope"]["to"]) == (
        "500.00",
        "2025-06-04",
        "2026-06-03",
    )
    assert delivered("from=2026-04-15&to=2026-04-15") == "500.00"
    assert delivered("from=2026-04-16") == "0.00"
    assert delivered("to=2026-04-14") == "0.00"
    # A state not asked is not read: the default scope retains the projects In progress alone.
    assert value(api, fabrics, READ)["delivered"] == "0.00"
    # The default period ends at the date: the project completed is outside the twelve months
    # that end on 14 April.
    assert value(api, fabrics, f"as_of=2026-04-14&states={COUNTED}")["delivered"] == "0.00"
    assert value(api, fabrics, f"as_of=2026-04-15&states={COUNTED}")["delivered"] == "500.00"


def closed(fabrics: Portfolio, destination: str, count: int, day: date) -> None:
    """Write transitions of an offer out of pricing for a destination, dated a day, as a loader."""
    with fabrics.stage.database.transaction() as session:
        session.execute(
            insert(ProjectStateTransition),
            [
                {
                    "id": uuid4(),
                    "project_id": fabrics.offer.project_id,
                    "from_state": "pricing",
                    "to_state": destination,
                    "occurred_at": at(day.month, day.day),
                    "actor_user_id": None,
                    "reason": None,
                }
                for _ in range(count)
            ],
        )


@pytest.mark.requirement("WF-PTF-0050-A")
def test_four_offers_won_out_of_ten_out_of_pricing_give_40_percent_and_an_abandoned_one_none(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Sur dix offres sorties de l'état Chiffrage dans la période vers En cours ou vers Perdu,
    # dont quatre passées à En cours, le taux de transformation vaut 40 % ; une onzième,
    # abandonnée dans la période, ne le change pas » — the same on the service, from the fixture.
    # The fabrics hold two offers won on 19 January and one lost on 15 March; the others are
    # written, around the offer of the fabrics, who is not in the scope of the view that reads them.
    data = example("WF-PTF-0050-A#82adcb588823")
    assert (data["won"], data["lost"], data["abandoned"]) == (4, 6, 1)
    closed(fabrics, "in_progress", 2, date(2026, 2, 20))
    closed(fabrics, "lost", 5, date(2026, 5, 10))
    rate = value(api, fabrics, f"{READ}&states=in_progress")["conversion_rate"]
    assert rate == {"is_computable": True, "value": data["conversion_rate"], "reason": None}
    closed(fabrics, "abandoned", 1, date(2026, 5, 11))
    for states in ("in_progress", COUNTED, "created"):
        again = value(api, fabrics, f"{READ}&states={states}")["conversion_rate"]
        assert again["value"] == data["conversion_rate"], states
    # An offer out of pricing outside the period is not counted: those of January and March are.
    after = value(api, fabrics, f"{READ}&from=2026-04-01")["conversion_rate"]
    assert (after["is_computable"], after["value"]) == (True, "0")


@pytest.mark.requirement("WF-PTF-0050-A")
def test_without_an_offer_out_of_pricing_in_the_period_the_rate_is_not_computable(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Sans offre sortie, le taux n'est pas calculable (``no_offer_out_of_pricing``) » : read on
    # 10 January, before any offer of the fabrics left Pricing; an abandoned offer alone is none.
    expected = {"is_computable": False, "value": None, "reason": "no_offer_out_of_pricing"}
    assert value(api, fabrics, "as_of=2026-01-10")["conversion_rate"] == expected
    closed(fabrics, "abandoned", 1, date(2026, 1, 5))
    assert value(api, fabrics, "as_of=2026-01-10")["conversion_rate"] == expected


@pytest.mark.requirement("WF-PTF-0050-A")
def test_a_period_refused_or_a_state_unknown_is_refused_as_the_other_views_refuse_them(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Une période inversée, ou qui commence après sa fin par défaut, est refusée par 422 » — the
    # one rule of the views that take a period; no empty value stands in for a refusal.
    reader = fabrics.stage.reader

    def faults(query: str) -> list[tuple[str, str, Any]]:
        answer = read(api, reader, "value", f"{READ}&{query}")
        assert (answer.status_code, answer.json()["code"]) == (422, "VALIDATION_FAILED"), query
        return [
            (each["pointer"], each["code"], each.get("params")) for each in answer.json()["fields"]
        ]

    assert faults("from=2026-03-31&to=2026-01-01") == [
        ("/query/to", "VALUE_OUT_OF_RANGE", {"minimum": "2026-03-31"})
    ]
    assert faults("from=2026-09-01") == [
        ("/query/from", "VALUE_OUT_OF_RANGE", {"maximum": "2026-06-03"})
    ]
    assert [each[:2] for each in faults("states=sleeping")] == [
        ("/query/states", "VALIDATION_FAILED")
    ]
    assert [each[:2] for each in faults(f"org_node_id={UUID(int=1)}")] == [
        ("/query/org_node_id", "UNKNOWN_ORG_NODE")
    ]
