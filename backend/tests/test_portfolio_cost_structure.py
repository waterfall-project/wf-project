# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of the costs of the portfolio, served (``getPortfolioCostStructure``; US-2720).

The documents ``portfolio_cost_structure`` the markings of the four projects of the fabrics kept
(``portfolio_support``) are set to the amounts of the sentence under test, as a marking of EP-11
would have kept them — the budget without its provision lines, the remaining with them, the labour
of the budget by role —, then read at a past date, the 3rd of June 2026, the date of the witness;
the current day is read against what the day computes from the lines. Every answer is validated
against the contract by the client of the tests.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from portfolio_listing_support import READ, example, kept_changed, read, revision_of, served
from portfolio_support import (
    OFFER_PROBABILITY,
    Portfolio,
    node,
    offer_being_priced,
    placed,
    portfolio,
    revision_opened,
)
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import delete, select, text, update

from waterfall.core.cost_settings.interface import rates_stamp, set_hourly_rate
from waterfall.core.cost_settings.tables import CostCategory, HourlyRate
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.indicators.contributions import contribution_key, stamps_of
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.portfolio.contributing import cost_structure_document
from waterfall.core.portfolio.interface import (
    PortfolioAsked,
    PortfolioReading,
    read_portfolio_cost_structure,
)
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.core.revisions.interface import reference_year_of
from waterfall.platform.audit import Act
from waterfall.platform.cache import PREFIX, IndicatorsCache

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from uuid import UUID

    from realm import TestRealm
    from redis import Redis
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

COST_STRUCTURE = "portfolio_cost_structure"
# The current day of the tests of the day, after the whole chronology of the fabrics.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
PRICING = f"{READ}&states=in_progress,pricing"
# Hours a week of the roles written around the service.
THIRTY = (6, 6, 6, 6, 6, 0, 0)
MISSING = "hourly_rate_missing"
type Amounts = Mapping[UUID, str]


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def natures(fabrics: Portfolio) -> dict[str, UUID]:
    """Give the cost types of the scene: of its labour, of its material and of its provisions."""
    costs = fabrics.costs
    categories = {
        "labour": costs.labour,
        "other": costs.material,
        "risk_provision": costs.provision,
    }
    with fabrics.stage.database.transaction() as session:
        types = dict(
            session.execute(
                select(CostCategory.id, CostCategory.cost_type_id).where(
                    CostCategory.id.in_(categories.values())
                )
            ).all()
        )
    return {name: types[category] for name, category in categories.items()}


def document(budget: Amounts, remaining: Amounts, labour: Amounts | None = None) -> dict[str, Any]:
    """Write a document ``portfolio_cost_structure``: amounts by cost type, and labour by role."""

    def by_type(amounts: Amounts) -> list[dict[str, str]]:
        return [
            {"cost_type_id": str(key), "label": f"Nature {key}", "amount": amount}
            for key, amount in amounts.items()
        ]

    roles = [
        {"resource_role_id": str(key), "amount": amount} for key, amount in (labour or {}).items()
    ]
    return {
        "budget_revision_id": str(next(iter(budget), "")),
        "budget_by_cost_type": by_type(budget),
        "remaining_by_cost_type": by_type(remaining),
        "budget_labour_by_role": roles,
        "remaining_labour_by_role": roles,
    }


def keep(owner: Engine, revision_id: UUID, kept: dict[str, Any]) -> None:
    """Set the structure of the costs a marked revision kept, as a superuser around the service."""
    kept_changed(owner, revision_id, COST_STRUCTURE, lambda _: kept)


def empty(owner: Engine, fabrics: Portfolio, *names: str) -> None:
    """Set the structure of the costs of the projects named to nothing: they add no amount."""
    for name in names:
        keep(owner, revision_of(fabrics, name), document({}, {}))


def structure(api: ContractClient, fabrics: Portfolio, query: str = READ) -> dict[str, Any]:
    """Read the structure of the costs as the manager of the portfolio does; the contract judges."""
    return served(api, fabrics.stage.reader, "cost-structure", query)


def amounts(entries: list[dict[str, Any]]) -> dict[str, str]:
    """Give the amounts of a breakdown by key."""
    return {each["key"]: each["amount"] for each in entries}


def shares(entries: list[dict[str, Any]]) -> dict[str, str]:
    """Give the shares of a breakdown by key, each computed."""
    assert all(each["share"]["is_computable"] for each in entries)
    return {each["key"]: each["share"]["value"] for each in entries}


def offer_kept(data: dict[str, Any], types: Mapping[str, UUID]) -> dict[str, Any]:
    """Write what the marking of the offer of a sentence keeps: its quote stands for both totals.

    The budget leaves the provision lines out, the remaining keeps them (``portfolio_totals``): the
    rule is written here by hand, as a marking of EP-11 keeps it; that the document itself leaves
    them out is held by the test of the current day below, which prices a real provision line, and
    by ``test_portfolio_contribution``.
    """
    budget: dict[UUID, Decimal] = {}
    remaining: dict[UUID, Decimal] = {}
    for line in data["quote_lines"]:
        key, amount = types[line["nature"]], Decimal(line["amount"])
        remaining[key] = remaining.get(key, Decimal(0)) + amount
        if not line["provision"]:
            budget[key] = budget.get(key, Decimal(0)) + amount
    return document(
        {key: f"{each:.2f}" for key, each in budget.items()},
        {key: f"{each:.2f}" for key, each in remaining.items()},
    )


def by_nature(data: dict[str, str], types: Mapping[str, UUID]) -> dict[str, str]:
    """Give the amounts of a sentence by the cost type each of its natures stands for."""
    return {str(types[nature]): amount for nature, amount in data.items()}


def offer_read(api: ContractClient, owner: Engine, fabrics: Portfolio, key: str) -> Any:
    """Read the structure of the costs of the offer of a sentence alone, its pricing asked."""
    data = example(key)
    assert Decimal(data["win_probability"]) == OFFER_PROBABILITY
    types = natures(fabrics)
    empty(owner, fabrics, "running")
    keep(owner, revision_of(fabrics, "offer"), offer_kept(data, types))
    return data, types, structure(api, fabrics, PRICING)


# --- The three sentences ------------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0080-A")
def test_an_offer_at_40_percent_of_100_of_labour_adds_40_to_the_labour_of_the_aggregated_budget(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Une offre à 40 % dont le devis porte 100 de main-d'œuvre ajoute 40 à la main-d'œuvre du
    # budget agrégé lorsqu'elle est incluse » — the same on the service, from the same fixture; not
    # included, it adds nothing.
    data, types, body = offer_read(api, owner, fabrics, "WF-PTF-0080-A#304cd560fe09")
    labour = str(types["labour"])
    assert amounts(body["budget_by_cost_type"])[labour] == data["aggregated_budget"]["labour"]
    without = structure(api, fabrics)
    assert labour not in amounts(without["budget_by_cost_type"])


@pytest.mark.requirement("WF-PTF-0080-A")
def test_a_provision_line_of_50_of_an_offer_at_40_percent_adds_20_to_the_remaining_only(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Une offre incluse, à 40 %, dont le devis porte une ligne de provision pour risques de 50
    # n'ajoute rien à la nature de cette ligne dans le budget agrégé, et ajoute 20 à cette nature
    # dans le reste à engager agrégé » — both breakdowns compared whole.
    data, types, body = offer_read(api, owner, fabrics, "WF-PTF-0080-A#c53a7c6ba53d")
    assert str(types["risk_provision"]) not in amounts(body["budget_by_cost_type"])
    assert amounts(body["budget_by_cost_type"]) == by_nature(data["aggregated_budget"], types)
    assert amounts(body["remaining_by_cost_type"]) == by_nature(data["aggregated_remaining"], types)


@pytest.mark.requirement("WF-PTF-0080-A")
def test_a_line_of_50_of_another_nature_adds_20_to_its_nature_in_the_budget_and_in_the_remaining(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Une ligne de 50 d'une nature hors main-d'œuvre, une provision pour aléas par exemple, ajoute
    # 20 à sa nature dans l'un et dans l'autre. »
    data, types, body = offer_read(api, owner, fabrics, "WF-PTF-0080-A#47418792a9e5")
    other = str(types["other"])
    assert amounts(body["budget_by_cost_type"])[other] == data["aggregated_budget"]["other"]
    assert amounts(body["remaining_by_cost_type"])[other] == data["aggregated_remaining"]["other"]


@pytest.mark.requirement("WF-PTF-0080-A")
def test_on_the_current_day_a_provision_line_of_an_offer_adds_to_the_remaining_never_to_the_budget(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The sentence of the provision line end to end, with no document written by hand: an offer
    # priced at 40 % whose line of 1 000.00 is of the category of the provisions adds nothing to the
    # budget, under any nature, and 400.00 to the remaining, under the nature of the provisions.
    monkeypatch.setattr("waterfall.api.portfolio_cost_structure.utc_now", lambda: NOW)
    project_id, _ = offer_being_priced(api, fabrics, "Halle 4", OFFER_PROBABILITY)
    with fabrics.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(
                EstimateLine.project_id == project_id,
                EstimateLine.cost_category_id == fabrics.costs.material,
            )
            .values(cost_category_id=fabrics.costs.provision)
        )
    types = natures(fabrics)
    provision, other = str(types["risk_provision"]), str(types["other"])
    body = structure(api, fabrics, "states=in_progress,pricing")
    # The material is the 1 000.00 of the project In progress and the 400.00 of the offer of the
    # fabrics, as without the offer written here: its line adds none.
    assert amounts(body["budget_by_cost_type"])[other] == "1400.00"
    assert provision not in amounts(body["budget_by_cost_type"])
    assert amounts(body["remaining_by_cost_type"])[provision] == "400.00"
    assert amounts(body["remaining_by_cost_type"])[other] == "1400.00"


# --- The shares and the labour ------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0080-A")
def test_the_shares_by_cost_type_sum_to_one_on_the_budget_and_on_the_remaining(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « La somme des parts par nature vaut cent pour cent, sur le budget comme sur le reste à
    # engager » : three thirds round to 0.3333 each, the largest — the first on a tie — carrying
    # the remainder; the remaining, of two projects, sums its parts before its shares.
    types = natures(fabrics)
    labour, other, provision = types["labour"], types["other"], types["risk_provision"]
    thirds = {labour: "1.00", other: "1.00", provision: "1.00"}
    keep(owner, revision_of(fabrics, "running"), document(thirds, {labour: "2.00", other: "1.00"}))
    keep(owner, revision_of(fabrics, "offer"), document({}, {labour: "10.00", provision: "5.00"}))
    body = structure(api, fabrics, PRICING)
    budget = shares(body["budget_by_cost_type"])
    remaining = shares(body["remaining_by_cost_type"])
    for each in (budget, remaining):
        assert sum(Decimal(value) for value in each.values()) == 1
    assert sorted(budget.values()) == ["0.3333", "0.3333", "0.3334"]
    assert amounts(body["remaining_by_cost_type"]) == {
        str(labour): "6.00",
        str(other): "1.00",
        str(provision): "2.00",
    }
    assert remaining == {str(labour): "0.6667", str(other): "0.1111", str(provision): "0.2222"}
    # The keys come in the order of their identifiers.
    keys = [each["key"] for each in body["budget_by_cost_type"]]
    assert keys == sorted(keys)


@pytest.mark.requirement("WF-PTF-0080-A")
def test_the_breakdown_by_node_bears_on_the_labour_alone_by_the_current_node_of_each_role(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « La ventilation par nœud ne porte que sur la main-d'œuvre » : ``labor_by_org_node`` sums the
    # labour of the budget by the node of its role — the material is in no node —, the node as it
    # stands when read, a role moved since the marking bringing its labour to its new node.
    database = fabrics.stage.database
    office, workshop = node(database, "BUREAU"), node(database, "ATELIER")
    drafter = placed(database, "DES", THIRTY, office)
    fitter = placed(database, "MON", THIRTY, workshop)
    types = natures(fabrics)
    budget = {types["labour"]: "300.00", types["other"]: "5000.00"}
    keep(
        owner,
        revision_of(fabrics, "running"),
        document(budget, budget, {drafter: "100.00", fitter: "200.00"}),
    )
    body = structure(api, fabrics)
    assert amounts(body["labor_by_org_node"]) == {str(office): "100.00", str(workshop): "200.00"}
    assert {each["label"] for each in body["labor_by_org_node"]} == {"Nœud BUREAU", "Nœud ATELIER"}
    assert sum(Decimal(each) for each in amounts(body["labor_by_org_node"]).values()) == Decimal(
        budget[types["labour"]]
    )
    assert sum(Decimal(each) for each in shares(body["labor_by_org_node"]).values()) == 1
    with database.transaction() as session:
        session.execute(
            update(ResourceRole).where(ResourceRole.id == fitter).values(org_node_id=office)
        )
    moved = structure(api, fabrics)
    assert moved["labor_by_org_node"] == [
        {
            "key": str(office),
            "label": "Nœud BUREAU",
            "amount": "300.00",
            "share": {"is_computable": True, "value": "1", "reason": None},
        }
    ]


@pytest.mark.requirement("WF-PTF-0080-A")
def test_no_breakdown_of_the_actual_cost_by_cost_type_is_offered(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Aucune vue ne propose de ventilation du coût réel par nature » : the answer bears the budget
    # and the remaining by cost type, and the labour by node, nothing else.
    body = structure(api, fabrics)
    assert set(body) == {
        "scope",
        "budget_by_cost_type",
        "remaining_by_cost_type",
        "labor_by_org_node",
    }
    assert not any("actual" in key for key in body)


@pytest.mark.story("US-2720")
def test_each_part_is_weighted_once_by_project_and_the_portfolio_sums_parts_already_rounded(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # The decision of the framing: « une somme de portefeuille est une somme de montants déjà
    # arrondis » — each amount of a project weighted once, to the cent, a half away from nought; the
    # labour of two roles of a node summed within the project before it is weighted: twice 10.01 at
    # 40 % gives 8.01, where two parts rounded apart would give 8.00.
    database = fabrics.stage.database
    office = node(database, "BUREAU")
    first, second = placed(database, "R1", THIRTY, office), placed(database, "R2", THIRTY, office)
    labour = natures(fabrics)["labour"]
    empty(owner, fabrics, "running")
    kept = document({labour: "0.05"}, {labour: "0.05"}, {first: "10.01", second: "10.01"})
    keep(owner, revision_of(fabrics, "offer"), kept)
    body = structure(api, fabrics, PRICING)
    assert amounts(body["budget_by_cost_type"]) == {str(labour): "0.02"}
    assert amounts(body["labor_by_org_node"]) == {str(office): "8.01"}


# --- The scope ----------------------------------------------------------------------------------


@pytest.mark.story("US-2720")
def test_the_projects_in_progress_and_those_completed_in_the_period_contribute_for_all(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « les projets en cours et terminés du périmètre contribuent pour tout, les
    # terminés étant ceux de la période, celle par défaut comprise » : the project completed on 15
    # April is in the default period of 3 June, and out of one that starts in May.
    other = natures(fabrics)["other"]
    keep(owner, revision_of(fabrics, "running"), document({other: "100.00"}, {other: "60.00"}))
    keep(owner, revision_of(fabrics, "completed"), document({other: "40.00"}, {other: "0.00"}))
    states = f"{READ}&states=in_progress,completed"
    both = structure(api, fabrics, states)
    assert both["scope"]["project_count"] == 2
    assert (both["scope"]["from"], both["scope"]["to"]) == ("2025-06-04", "2026-06-03")
    assert amounts(both["budget_by_cost_type"]) == {str(other): "140.00"}
    assert amounts(both["remaining_by_cost_type"]) == {str(other): "60.00"}
    after = structure(api, fabrics, f"{states}&from=2026-05-01")
    assert after["scope"]["project_count"] == 1
    assert amounts(after["budget_by_cost_type"]) == {str(other): "100.00"}
    alone = structure(api, fabrics)
    assert alone["scope"]["states"] == ["in_progress"]
    assert amounts(alone["budget_by_cost_type"]) == {str(other): "100.00"}


@pytest.mark.story("US-2720")
def test_the_node_restricts_the_labour_alone_and_leaves_the_totals_by_cost_type_unchanged(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « org_node_id ne restreint que la main-d'œuvre : les totaux des autres natures
    # sont inchangés » — the node keeps the labour of its roles and of those of its descendants.
    database = fabrics.stage.database
    office = node(database, "BUREAU")
    team = node(database, "EQUIPE", office)
    workshop = node(database, "ATELIER")
    drafter = placed(database, "DES", THIRTY, office)
    member = placed(database, "MEM", THIRTY, team)
    fitter = placed(database, "MON", THIRTY, workshop)
    types = natures(fabrics)
    budget = {types["labour"]: "350.00", types["other"]: "1000.00"}
    labour = {drafter: "100.00", member: "50.00", fitter: "200.00"}
    keep(owner, revision_of(fabrics, "running"), document(budget, budget, labour))
    everything = structure(api, fabrics)
    restricted = structure(api, fabrics, f"{READ}&org_node_id={office}")
    assert restricted["scope"]["org_node_id"] == str(office)
    assert restricted["scope"]["org_node_label"] == "Nœud BUREAU"
    assert amounts(restricted["labor_by_org_node"]) == {str(office): "100.00", str(team): "50.00"}
    assert shares(restricted["labor_by_org_node"]) == {str(office): "0.6667", str(team): "0.3333"}
    for breakdown in ("budget_by_cost_type", "remaining_by_cost_type"):
        assert restricted[breakdown] == everything[breakdown]
    assert len(everything["labor_by_org_node"]) == 3


@pytest.mark.story("US-2720")
def test_at_a_past_date_the_view_reads_the_totals_the_markings_kept(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « à une date passée, la vue lit les totaux par nature et par nœud que les
    # révisions marquées ont conservés (US-2680) » : the figures kept, not those the lines give
    # today; a project that kept none — a marking before EP-11 — adds nothing.
    other = natures(fabrics)["other"]
    role = fabrics.costs.role
    kept = document({other: "123.45"}, {other: "67.89"}, {role: "11.11"})
    keep(owner, revision_of(fabrics, "running"), kept)
    body = structure(api, fabrics)
    assert amounts(body["budget_by_cost_type"]) == {str(other): "123.45"}
    assert amounts(body["remaining_by_cost_type"]) == {str(other): "67.89"}
    assert [each["amount"] for each in body["labor_by_org_node"]] == ["11.11"]
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(
            delete(RevisionIndicator).where(
                RevisionIndicator.revision_id == revision_of(fabrics, "running"),
                RevisionIndicator.kind == COST_STRUCTURE,
            )
        )
    nothing = structure(api, fabrics)
    assert nothing["scope"]["project_count"] == 1
    assert (nothing["budget_by_cost_type"], nothing["labor_by_org_node"]) == ([], [])


@pytest.mark.story("US-2720")
def test_on_the_current_day_the_view_sums_what_the_day_computes_an_offer_by_its_weight(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without a date, the day: the eight hours of the role at 65.00 and the 1 000.00 of material of
    # the project In progress, its reference standing for the budget; the offer, asked, adds 40 %
    # of its own, 208.00 and 400.00.
    monkeypatch.setattr("waterfall.api.portfolio_cost_structure.utc_now", lambda: NOW)
    types = natures(fabrics)
    labour, other = str(types["labour"]), str(types["other"])
    plain = structure(api, fabrics, "")
    assert plain["scope"]["as_of"] == "2026-11-19"
    assert amounts(plain["budget_by_cost_type"]) == {labour: "520.00", other: "1000.00"}
    assert amounts(plain["remaining_by_cost_type"]) == {labour: "520.00", other: "1000.00"}
    with_offer = structure(api, fabrics, "states=in_progress,pricing")
    assert amounts(with_offer["budget_by_cost_type"]) == {labour: "728.00", other: "1400.00"}
    assert amounts(with_offer["labor_by_org_node"]) == {
        each["key"]: "728.00" for each in with_offer["labor_by_org_node"]
    }


# --- A rate missing (#4283) ---------------------------------------------------------------------


def unrate(fabrics: Portfolio, year: int) -> None:
    """Withdraw the rate of the labour of the scene for a year, around the service."""
    with fabrics.stage.owner.begin() as connection:
        connection.execute(
            delete(HourlyRate).where(
                HourlyRate.cost_category_id == fabrics.costs.labour, HourlyRate.year == year
            )
        )


@pytest.mark.requirement("WF-DEV-0010-A")
def test_on_the_current_day_a_labour_without_a_rate_is_a_nature_not_computed_never_summed(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # #4283, décision de l'auteur du 2026-11-20 : « la structure des coûts du jour signale une
    # main-d'œuvre sans taux horaire par une nature « non calculée », au lieu de la sommer en
    # silence ». An offer priced on its first revision, the rate of its labour withdrawn: its labour
    # adds nothing, the nature and the node it falls under are not computed, the rates named, every
    # other share of the breakdown not computed either — its total is not —; the marked revisions,
    # priced on what they kept, still count. The rate set again moves the key of the cache
    # (WF-DAT-0130-A), and the day computes everything.
    monkeypatch.setattr("waterfall.api.portfolio_cost_structure.utc_now", lambda: NOW)
    project_id, revision_id = offer_being_priced(api, fabrics, "Halle 4", OFFER_PROBABILITY)
    with fabrics.stage.database.transaction() as session:
        year = reference_year_of(session, revision_id)
    unrate(fabrics, year)
    types = natures(fabrics)
    labour, other = str(types["labour"]), str(types["other"])
    with fabrics.stage.database.transaction() as session:
        lacking_key = contribution_key(session, project_id, revision_id, NOW, stamps_of(session))
        kept = cost_structure_document(session, project_id, revision_id)
    lacking = {each["cost_type_id"]: each for each in kept["budget_by_cost_type"]}[labour]
    category = {"cost_category_id": str(fabrics.costs.labour), "year": year}
    named = [{**category, "label": lacking["missing_rates"][0]["label"]}]
    assert {**lacking, "label": None} == {
        "cost_type_id": labour,
        "label": None,
        "amount": None,
        "missing_rates": named,
    }
    assert kept["budget_labour_by_role"] == [
        {"resource_role_id": str(fabrics.costs.role), "amount": None, "missing_rates": named}
    ]
    body = structure(api, fabrics, "states=in_progress,pricing")
    budget = {each["key"]: each for each in body["budget_by_cost_type"]}
    expected = {"is_computable": False, "value": None, "reason": MISSING}
    assert budget[labour]["amount"] == "728.00"
    assert budget[labour]["share"] == {**expected, "params": {"missing_rates": named}}
    assert budget[other]["amount"] == "1800.00"
    assert budget[other]["share"] == expected
    remaining = {each["key"]: each for each in body["remaining_by_cost_type"]}
    assert remaining[labour]["share"] == {**expected, "params": {"missing_rates": named}}
    (office,) = body["labor_by_org_node"]
    assert office["amount"] == "728.00"
    assert office["share"] == {**expected, "params": {"missing_rates": named}}
    with fabrics.stage.database.transaction() as session:
        set_hourly_rate(
            session, (fabrics.costs.labour, year), Decimal("65.00"), None, Act(None, NOW)
        )
    with fabrics.stage.database.transaction() as session:
        after = contribution_key(session, project_id, revision_id, NOW, stamps_of(session))
    # The key read while the rate was lacking is not the one read once it is set.
    assert lacking_key != after
    rated = structure(api, fabrics, "states=in_progress,pricing")
    assert amounts(rated["budget_by_cost_type"]) == {labour: "936.00", other: "1800.00"}
    assert sum(Decimal(each) for each in shares(rated["budget_by_cost_type"]).values()) == 1


@pytest.mark.requirement("WF-DAT-0130-A")
def test_the_stamp_of_the_rates_moves_with_a_rate_set_and_with_a_rate_corrected(
    fabrics: Portfolio,
) -> None:
    # The stamp the key reads alone: a rate set adds one to the count, the instant of the write
    # moving; a rate corrected leaves the count and moves the sum of the counters of the rows.
    category = fabrics.costs.labour
    year = 2090
    with fabrics.stage.database.transaction() as session:
        start = rates_stamp(session)
    with fabrics.stage.database.transaction() as session:
        set_hourly_rate(session, (category, year), Decimal("70.00"), None, Act(None, NOW))
    with fabrics.stage.database.transaction() as session:
        added = rates_stamp(session)
        version = session.scalar(
            select(HourlyRate.lock_version).where(
                HourlyRate.cost_category_id == category, HourlyRate.year == year
            )
        )
    assert added.count == start.count + 1
    assert added.versions > start.versions
    assert added.updated_at is not None
    assert start.updated_at is None or added.updated_at >= start.updated_at
    assert version is not None
    with fabrics.stage.database.transaction() as session:
        set_hourly_rate(session, (category, year), Decimal("71.00"), version, Act(None, NOW))
    with fabrics.stage.database.transaction() as session:
        corrected = rates_stamp(session)
    assert corrected.count == added.count
    assert corrected.versions > added.versions
    assert corrected != added


class Written(IndicatorsCache):
    """The cache of the indicators, which records the keys it writes."""

    def __init__(self, client: Redis, ttl: int) -> None:
        """Record nothing yet."""
        super().__init__(client, ttl)
        self.written: set[str] = set()

    def write_many(self, documents: Mapping[str, str]) -> None:
        """Record the keys, then write."""
        self.written.update(documents)
        super().write_many(documents)


@pytest.fixture
def cache(queue: TaskQueue) -> Iterator[Written]:
    """Give the cache of the indicators beside the queue; the entries it wrote deleted."""
    opened = Written.of(queue, 300)
    yield opened
    if opened.written:
        opened.client.delete(*(PREFIX + key for key in opened.written))
    opened.close()


@pytest.mark.requirement("WF-DAT-0130-A")
def test_a_rate_set_after_a_reading_that_lacked_it_is_not_served_from_the_entry_before(
    api: ContractClient, fabrics: Portfolio, cache: Written
) -> None:
    # A reading of the day, cached, that names the rate missing; the rate set, the second reading
    # through the same cache computes the labour again instead of serving the entry that lacked it.
    _, revision_id = offer_being_priced(api, fabrics, "Halle 4", OFFER_PROBABILITY)
    with fabrics.stage.database.transaction() as session:
        year = reference_year_of(session, revision_id)
    unrate(fabrics, year)
    asked = PortfolioAsked(states=("in_progress", "pricing"))
    reading = PortfolioReading(NOW, cache)

    def read_day() -> dict[str, Any]:
        with fabrics.stage.database.transaction() as session:
            return dict(read_portfolio_cost_structure(session, asked, reading))

    lacking = read_day()
    assert cache.written
    assert any(not each["share"]["is_computable"] for each in lacking["budget_by_cost_type"])
    with fabrics.stage.database.transaction() as session:
        set_hourly_rate(
            session, (fabrics.costs.labour, year), Decimal("65.00"), None, Act(None, NOW)
        )
    rated = read_day()
    assert all(each["share"]["is_computable"] for each in rated["budget_by_cost_type"])
    assert all(each["share"]["is_computable"] for each in rated["labor_by_org_node"])


@pytest.mark.requirement("WF-DEV-0010-A")
def test_a_project_in_progress_whose_current_revision_lacks_a_rate_keeps_its_budget_computed(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The reference of a project In progress is marked, so its budget is never lacking; its
    # remaining to commit is read on the current revision, whose labour lacks a rate: the budget
    # stays computed, the remaining of the labour is not, naming the rate.
    monkeypatch.setattr("waterfall.api.portfolio_cost_structure.utc_now", lambda: NOW)
    types = natures(fabrics)
    labour, other = str(types["labour"]), str(types["other"])
    with fabrics.stage.database.transaction() as session:
        year = reference_year_of(session, revision_of(fabrics, "running"))
    unrate(fabrics, year)
    current = revision_opened(api, fabrics, fabrics.in_progress.project_id, NOW)
    # Deleting the RevisionRate rows of the open revision reproduces the real state of a labour
    # category kept without a rate: in production, a line added in the current revision for a
    # category the marked revision did not hold, since opening copies only the rates already held
    # (core/estimate/keeping.py, imaging.py) and held_rates falls back on the reference.
    with fabrics.stage.owner.begin() as connection:
        connection.execute(delete(RevisionRate).where(RevisionRate.revision_id == current))
    body = structure(api, fabrics, "states=in_progress")
    budget = {each["key"]: each for each in body["budget_by_cost_type"]}
    assert budget[labour]["amount"] == "520.00"
    assert budget[labour]["share"]["is_computable"] is True
    remaining = {each["key"]: each for each in body["remaining_by_cost_type"]}
    share = remaining[labour]["share"]
    assert share["is_computable"] is False
    assert share["reason"] == MISSING
    assert share["params"]["missing_rates"][0]["year"] == year
    assert remaining[other]["share"]["reason"] == MISSING


# --- The permission -----------------------------------------------------------------------------


@pytest.mark.story("US-2720")
def test_the_view_is_read_under_its_permission_and_a_period_or_a_node_refused_as_every_view(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US : « la lecture est sous portfolio_cost_structure.read » : the project manager,
    # who does not read the portfolio, does not see the view (404), an anonymous caller is refused
    # (401); the manager of the portfolio reads it. A period inverted and an unknown node are
    # refused by the rule of every view (422).
    stage = fabrics.stage
    path = "/api/v1/portfolio/cost-structure"
    assert api.get(path, headers=stage.manager.headers).status_code == 404
    assert api.get(path).status_code == 401
    assert api.get(path, headers=stage.reader.headers).status_code == 200
    inverted = read(api, stage.reader, "cost-structure", f"{READ}&from=2026-05-01&to=2026-04-01")
    assert inverted.status_code == 422
    assert [each["pointer"] for each in inverted.json()["fields"]] == ["/query/to"]
    query = f"{READ}&org_node_id={stage.manager.user_id}"
    unknown = read(api, stage.reader, "cost-structure", query)
    assert [(each["pointer"], each["code"]) for each in unknown.json()["fields"]] == [
        ("/query/org_node_id", "UNKNOWN_ORG_NODE")
    ]
