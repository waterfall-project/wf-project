# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The aggregated workload of the portfolio, served (``getPortfolioWorkload``; US-2700).

The documents ``portfolio_workload`` the markings of the four projects of the fabrics kept
(``portfolio_support``) are set to the hours of the sentence under test, as a marking of EP-11 would
have kept them, then read at a past date, the 3rd of June 2026, the date of the witness; the current
day is read against what the day computes. The roles are those of the scene, and a few written
around the service, under a tree of nodes of their own for the filter. Every answer is validated
against the contract by the client of the tests.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from estimate_support import add_role
from portfolio_listing_support import READ, example, kept_changed, read, revision_of, served
from portfolio_support import Portfolio, another_in_progress, at, portfolio
from projects_support import Scene, person
from projects_support import scene as make_scene
from sqlalchemy import delete, text, update

from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.resource_settings.interface import NodeWrite, create_node, read_role
from waterfall.core.resource_settings.tables import ResourceRole
from waterfall.core.revisions.interface import last_marked_revision
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

NODES = "/api/v1/reference/org-nodes"
# The current day of the tests of the day, after the whole chronology of the fabrics.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)
JUNE = "2026-06"
# Hours a week of the roles written around the service: 30 hours a week make 130.00 hours a month.
THIRTY = (6, 6, 6, 6, 6, 0, 0)
TWENTY = (4, 4, 4, 4, 4, 0, 0)
FORTY = (8, 8, 8, 8, 8, 0, 0)
NONE = (0, 0, 0, 0, 0, 0, 0)
PRICING = f"{READ}&states=in_progress,pricing"
type Loads = dict[UUID, dict[str, str]]


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def document(loads: Loads) -> dict[str, Any]:
    """Write the document ``portfolio_workload`` of hours by role and by month."""
    return {
        "roles": [
            {
                "resource_role_id": str(role),
                "months": [{"month": month, "hours": hours} for month, hours in months.items()],
            }
            for role, months in loads.items()
        ]
    }


def keep(owner: Engine, revision_id: UUID, loads: Loads) -> None:
    """Set the workload a marked revision kept, as a superuser around the service."""
    kept_changed(owner, revision_id, "portfolio_workload", lambda _: document(loads))


def keep_probability(owner: Engine, revision_id: UUID, probability: Decimal | None) -> None:
    """Set the probability of winning a marked revision kept, none for a marking before EP-07."""
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(
            update(Revision).where(Revision.id == revision_id).values(win_probability=probability)
        )


def forget(owner: Engine, revision_id: UUID) -> None:
    """Remove the workload a marked revision kept, as a revision marked before EP-11 has none."""
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        connection.execute(
            delete(RevisionIndicator).where(
                RevisionIndicator.revision_id == revision_id,
                RevisionIndicator.kind == "portfolio_workload",
            )
        )


def workload(api: ContractClient, fabrics: Portfolio, query: str = READ) -> dict[str, Any]:
    """Read the workload as the manager that reads the portfolio does; the contract judges it."""
    return served(api, fabrics.stage.reader, "workload", query)


def role_of(body: dict[str, Any], role_id: UUID) -> dict[str, Any]:
    """Give the role of an answer by its identifier."""
    found = [each for each in body["roles"] if each["resource_role_id"] == str(role_id)]
    assert len(found) == 1
    role: dict[str, Any] = found[0]
    return role


def hours(role: dict[str, Any]) -> dict[str, str]:
    """Give the hours of a role by month."""
    return {each["month"]: each["hours"] for each in role["months"]}


def zones(role: dict[str, Any]) -> dict[str, str]:
    """Give the zone of a role by month."""
    return {each["month"]: each["zone"] for each in role["months"]}


def second_project(api: ContractClient, fabrics: Portfolio) -> UUID:
    """Write a second project In progress, and give the revision its review marked."""
    project_id = another_in_progress(api, fabrics, "Second chantier", "PRJ-2673")
    with fabrics.stage.database.transaction() as session:
        revision = last_marked_revision(session, project_id)
    assert revision is not None
    return revision


def placed(database: Database, code: str, week: tuple[int, ...], node_id: UUID | None) -> UUID:
    """Write a role of a calendar of its own, and put it under a node when one is given."""
    role = add_role(database, code, week)
    if node_id is not None:
        with database.transaction() as session:
            session.execute(
                update(ResourceRole).where(ResourceRole.id == role).values(org_node_id=node_id)
            )
    return role


def node(database: Database, code: str, parent: UUID | None = None) -> UUID:
    """Create an active node, a root without a parent."""
    with database.transaction() as session:
        return create_node(
            session, NodeWrite(code, f"Nœud {code}", parent), Act(None, at(1, 4))
        ).node_id


def monthly_hours(fabrics: Portfolio, role: UUID) -> Decimal:
    """Read the hours a month of a role, as its capacity gives them (EP-10)."""
    with fabrics.stage.database.transaction() as session:
        return read_role(session, role, may_change=False).capacity.monthly_hours


# --- The sums ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PTF-0060-A")
def test_two_projects_in_progress_of_100_and_150_hours_of_a_role_the_same_month_give_250(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Sur deux projets en cours dont les restes à engager portent 100 et 150 heures d'un même
    # rôle le même mois, le plan agrégé porte 250 heures » — the same on the service, from the same
    # fixture: the two projects In progress keep their hours, read at the date of the witness.
    data = example("WF-PTF-0060-A#45748fe78d7c")
    role = fabrics.costs.role
    first, second = data["in_progress_hours"]
    keep(owner, revision_of(fabrics, "running"), {role: {JUNE: first}})
    keep(owner, second_project(api, fabrics), {role: {JUNE: second}})
    body = workload(api, fabrics)
    assert body["scope"]["project_count"] == 2
    assert hours(role_of(body, role))[JUNE] == data["aggregated_hours"]
    assert body["monthly_totals"][0] == {"month": JUNE, "hours": data["aggregated_hours"]}


@pytest.mark.requirement("WF-PTF-0060-A")
def test_an_offer_at_50_percent_of_100_hours_adds_50_when_pricing_is_asked_and_nothing_otherwise(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Une offre à 50 % avec 100 heures ajoute 50 heures quand le chiffrage est inclus, rien
    # sinon » — the offer of the fabrics keeps 50 % at its marking, and 100 hours in June.
    data = example("WF-PTF-0060-A#dd1733488885")
    role = fabrics.costs.role
    first, second = data["in_progress_hours"]
    keep(owner, revision_of(fabrics, "running"), {role: {JUNE: first}})
    keep(owner, second_project(api, fabrics), {role: {JUNE: second}})
    offer = revision_of(fabrics, "offer")
    keep(owner, offer, {role: {JUNE: data["offer"]["hours"]}})
    keep_probability(owner, offer, Decimal(data["offer"]["win_probability"]))
    without = workload(api, fabrics)
    assert hours(role_of(without, role))[JUNE] == data["aggregated_hours"]
    with_offer = workload(api, fabrics, PRICING)
    assert with_offer["scope"]["states"] == ["in_progress", "pricing"]
    assert hours(role_of(with_offer, role))[JUNE] == data["with_offer_hours"]
    offers = workload(api, fabrics, f"{READ}&states=pricing")
    assert hours(role_of(offers, role))[JUNE] == data["offer_hours"]


@pytest.mark.requirement("WF-PTF-0060-A")
def test_a_month_at_120_percent_of_the_capacity_is_in_alert_under_the_threshold_in_watch(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Un mois à 120 % de la capacité est signalé » : alert beyond the capacity, watch below the
    # threshold of under-load — the load over the capacity, strictly —, nominal otherwise. The
    # fixture says 120 hours on 100: the role of 30 hours a week, 130.00 a month, carries 156.
    data = example("WF-PTF-0060-A#9bd0b92b0168")
    month = data["overloaded"]
    role = placed(fabrics.stage.database, "R30", THIRTY, None)
    ratio = Decimal(month["hours"]) / Decimal(month["capacity"])
    capacity = Decimal(130)
    assert monthly_hours(fabrics, role) == capacity
    loads = {
        JUNE: f"{capacity * ratio:.2f}",
        "2026-07": f"{capacity:.2f}",
        "2026-08": f"{capacity / 2:.2f}",
        "2026-09": f"{capacity * Decimal('0.4'):.2f}",
    }
    keep(owner, revision_of(fabrics, "running"), {role: loads})
    body = workload(api, fabrics)
    held = role_of(body, role)
    assert held["capacity_monthly_hours"] == "130.00"
    assert held["months"][0] == {
        "month": JUNE,
        "hours": "156.00",
        "load_ratio": {"is_computable": True, "value": month["load_ratio"], "reason": None},
        "zone": month["zone"],
    }
    assert zones(held) == {
        JUNE: "alert",
        "2026-07": "nominal",
        "2026-08": "nominal",
        "2026-09": "watch",
        "2026-10": "watch",
        "2026-11": "watch",
    }
    assert body["under_load_threshold"] == data["under_load_threshold"]
    # The threshold asked: at 0.4 the month at 40 % is no longer under it; it is given back as sent.
    asked = workload(api, fabrics, f"{READ}&under_load_threshold=0.4")
    assert asked["under_load_threshold"] == "0.4"
    assert zones(role_of(asked, role))["2026-09"] == "nominal"
    assert workload(api, fabrics, f"{READ}&under_load_threshold=1")["under_load_threshold"] == "1"


@pytest.mark.requirement("WF-REF-0100-A")
def test_the_load_ratio_of_each_month_is_its_hours_over_the_hours_a_month_of_the_role(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Le plan de charge agrégé compare la charge mensuelle de chaque rôle à ces heures » : the
    # capacity of a role is its hours calculated (EP-10), read from the role itself, and the ratio
    # of a month is the load over them, to four decimals.
    database = fabrics.stage.database
    role = placed(database, "R20", TWENTY, None)
    keep(owner, revision_of(fabrics, "running"), {role: {JUNE: "40.00", "2026-07": "1.00"}})
    held = role_of(workload(api, fabrics), role)
    capacity = monthly_hours(fabrics, role)
    assert (capacity, held["capacity_monthly_hours"]) == (Decimal("86.67"), "86.67")
    ratios = {each["month"]: each["load_ratio"]["value"] for each in held["months"]}
    assert ratios[JUNE] == f"{(Decimal(40) / capacity).quantize(Decimal('0.0001')).normalize():f}"
    assert ratios["2026-07"] == "0.0115"
    assert ratios["2026-08"] == "0"


@pytest.mark.requirement("WF-PTF-0060-A")
def test_a_role_without_capacity_is_in_alert_with_a_load_and_in_watch_without(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Un rôle sans capacité est alert s'il a de la charge, watch sinon, son taux non calculable
    # (no_capacity) » : a role on a calendar that works no hour.
    role = placed(fabrics.stage.database, "R00", NONE, None)
    keep(owner, revision_of(fabrics, "running"), {role: {JUNE: "10.00"}})
    held = role_of(workload(api, fabrics), role)
    assert held["capacity_monthly_hours"] == "0.00"
    assert held["months"][0]["load_ratio"] == {
        "is_computable": False,
        "value": None,
        "reason": "no_capacity",
    }
    assert zones(held) == dict.fromkeys(zones(held), "watch") | {JUNE: "alert"}


# --- The months and the roles --------------------------------------------------------------------


@pytest.mark.story("US-2700")
def test_the_months_run_from_that_of_the_date_without_a_gap_and_every_role_has_each_of_them(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « les mois vont de celui de la date de calcul sur horizon_months, six par
    # défaut, sans trou ; chaque rôle retenu porte un mois par mois, un rôle sans charge compris ;
    # la capacité du périmètre est la somme des capacités des rôles retenus » : a year turned, a
    # role without load, a role deactivated left out with its capacity.
    database = fabrics.stage.database
    idle = placed(database, "R30", THIRTY, None)
    off = placed(database, "R20", TWENTY, None)
    with database.transaction() as session:
        session.execute(update(ResourceRole).where(ResourceRole.id == off).values(is_active=False))
    keep(owner, revision_of(fabrics, "running"), {fabrics.costs.role: {JUNE: "20.00"}})
    by_default = workload(api, fabrics)
    assert by_default["months"] == [JUNE, "2026-07", "2026-08", "2026-09", "2026-10", "2026-11"]
    assert len(by_default["roles"]) == 2
    assert [each["month"] for each in by_default["monthly_totals"]] == by_default["months"]
    for each in by_default["roles"]:
        assert [one["month"] for one in each["months"]] == by_default["months"]
    assert hours(role_of(by_default, idle)) == dict.fromkeys(by_default["months"], "0.00")
    assert all(each["resource_role_id"] != str(off) for each in by_default["roles"])
    capacity = monthly_hours(fabrics, fabrics.costs.role) + monthly_hours(fabrics, idle)
    assert by_default["capacity_monthly_hours"] == f"{capacity:.2f}"
    turned = workload(api, fabrics, "as_of=2026-10-15&horizon_months=4")
    assert turned["months"] == ["2026-10", "2026-11", "2026-12", "2027-01"]
    assert turned["scope"]["as_of"] == "2026-10-15"
    assert len(workload(api, fabrics, f"{READ}&horizon_months=240")["months"]) == 240
    assert workload(api, fabrics, f"{READ}&horizon_months=1")["months"] == [JUNE]


@pytest.mark.story("US-2700")
def test_a_horizon_or_a_threshold_out_of_its_bounds_is_refused_with_its_bounds_named(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US : « un horizon ou un seuil hors de ses bornes est refusé par 422 » — each
    # designated, both at once, by ``VALUE_OUT_OF_RANGE`` and the bounds the contract gives.
    for query, pointer, bounds in (
        ("horizon_months=0", "/query/horizon_months", {"minimum": 1, "maximum": 240}),
        ("horizon_months=241", "/query/horizon_months", {"minimum": 1, "maximum": 240}),
        ("under_load_threshold=1.01", "/query/under_load_threshold", {"minimum": 0, "maximum": 1}),
        ("under_load_threshold=-0.01", "/query/under_load_threshold", {"minimum": 0, "maximum": 1}),
    ):
        refused = read(api, fabrics.stage.reader, "workload", f"{READ}&{query}")
        assert refused.status_code == 422, query
        fields = refused.json()["fields"]
        assert [(each["pointer"], each["code"]) for each in fields] == [
            (pointer, "VALUE_OUT_OF_RANGE")
        ], query
        assert {name: Decimal(str(value)) for name, value in fields[0]["params"].items()} == {
            name: Decimal(value) for name, value in bounds.items()
        }
    query = f"{READ}&horizon_months=0&under_load_threshold=2"
    both = read(api, fabrics.stage.reader, "workload", query)
    assert [each["pointer"] for each in both.json()["fields"]] == [
        "/query/horizon_months",
        "/query/under_load_threshold",
    ]


@pytest.mark.story("US-2700")
def test_a_state_unknown_is_refused_with_the_parameters_of_the_view_and_the_node_in_a_second_answer(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # The state and the parameters of the view are refused at once (``portfolio_asked``); the node
    # comes from the scope, which reads the database, so it is refused in a second answer (#4199).
    headers = fabrics.stage.reader.headers
    unknown = UUID(int=1)
    states = api.get(
        f"/api/v1/portfolio/workload?states=finished&horizon_months=0&org_node_id={unknown}",
        headers=headers,
    )
    assert [each["pointer"] for each in states.json()["fields"]] == [
        "/query/states",
        "/query/horizon_months",
    ]
    node = api.get(f"/api/v1/portfolio/workload?org_node_id={unknown}", headers=headers)
    assert node.status_code == 422
    assert [(each["pointer"], each["code"]) for each in node.json()["fields"]] == [
        ("/query/org_node_id", "UNKNOWN_ORG_NODE")
    ]


@pytest.mark.requirement("WF-PTF-0060-A")
def test_a_state_other_than_in_progress_and_pricing_has_no_effect_and_the_view_takes_no_period(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # #1714 : « seuls les projets en cours et, s'ils sont demandés, en chiffrage y contribuent ;
    # un autre état que states nomme — terminé compris — est sans effet, et la vue ne prend pas de
    # période ». The project completed in April keeps 999 hours in June: asked alone, or with every
    # state, it adds nothing, and a period — even inverted — is not read.
    role = fabrics.costs.role
    keep(owner, revision_of(fabrics, "completed"), {role: {JUNE: "999.00"}})
    keep(owner, revision_of(fabrics, "running"), {role: {JUNE: "10.00"}})
    completed = workload(api, fabrics, f"{READ}&states=completed")
    assert completed["scope"]["states"] == ["completed"]
    assert completed["scope"]["project_count"] == 0
    assert set(hours(role_of(completed, role)).values()) == {"0.00"}
    every = "in_progress,pricing,completed,created,lost,abandoned"
    asked = workload(api, fabrics, f"{READ}&states={every}&from=2026-04-01&to=2026-01-01")
    assert asked["scope"]["states"] == every.split(",")
    assert asked["scope"]["project_count"] == 2
    assert (asked["scope"]["from"], asked["scope"]["to"]) == (None, None)
    assert hours(role_of(asked, role))[JUNE] == "10.00"


@pytest.mark.story("US-2700")
def test_the_parts_of_an_offer_are_rounded_once_and_the_plan_sums_hours_already_rounded(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « les parts d'une ligne s'arrondissent de façon que leur somme soit son
    # total, comme au plan de charge d'un projet (EP-10), et le plan agrégé somme des heures déjà
    # arrondies » : the hours of a document are rounded as EP-10 gives them; the part of an offer
    # at 50 % is rounded once to the hundredth, a half to the even (0.125 is 0.12, 0.175 is 0.18),
    # and the plan adds those parts as they are, without rounding the sum again.
    role = fabrics.costs.role
    keep(owner, revision_of(fabrics, "running"), {role: {JUNE: "33.34", "2026-07": "0.01"}})
    keep(owner, second_project(api, fabrics), {role: {JUNE: "33.33", "2026-07": "0.01"}})
    offer = revision_of(fabrics, "offer")
    keep(owner, offer, {role: {JUNE: "0.25", "2026-07": "0.35"}})
    keep_probability(owner, offer, Decimal("0.5"))
    held = hours(role_of(workload(api, fabrics, PRICING), role))
    assert (held[JUNE], held["2026-07"]) == ("66.79", "0.20")
    assert Decimal(held[JUNE]) == Decimal("33.34") + Decimal("33.33") + Decimal("0.12")
    assert Decimal(held["2026-07"]) == Decimal("0.01") + Decimal("0.01") + Decimal("0.18")


@pytest.mark.story("US-2700")
def test_a_project_that_kept_no_workload_or_no_probability_adds_nothing_and_is_not_an_error(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # A revision marked before EP-11 keeps no workload, one marked before EP-07 no probability of
    # winning: nothing is taken up nor recalculated (EP-11, "Ce que le cadrage décide"), the
    # project is retained by its state all the same.
    role = fabrics.costs.role
    running, offer = revision_of(fabrics, "running"), revision_of(fabrics, "offer")
    keep(owner, running, {role: {JUNE: "10.00"}})
    keep(owner, offer, {role: {JUNE: "100.00"}})
    keep_probability(owner, offer, None)
    body = workload(api, fabrics, PRICING)
    assert body["scope"]["project_count"] == 2
    assert hours(role_of(body, role))[JUNE] == "10.00"
    forget(owner, running)
    nothing = workload(api, fabrics, PRICING)
    assert hours(role_of(nothing, role))[JUNE] == "0.00"


# --- The dates -----------------------------------------------------------------------------------


@pytest.mark.story("US-2700")
def test_at_a_past_date_the_hours_are_those_the_markings_kept_and_the_capacity_is_the_current_one(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # Propre à l'US : « à une date passée, la vue lit la charge par rôle et par mois que les
    # révisions marquées ont conservée (US-2680), et la capacité courante des rôles » : the hours
    # kept are not those the day would compute, and the capacity follows the role as it stands.
    role = fabrics.costs.role
    keep(owner, revision_of(fabrics, "running"), {role: {JUNE: "77.00"}})
    body = workload(api, fabrics)
    held = role_of(body, role)
    assert hours(held)[JUNE] == "77.00"
    assert Decimal(held["capacity_monthly_hours"]) == monthly_hours(fabrics, role)
    with fabrics.stage.database.transaction() as session:
        session.execute(update(ResourceRole).where(ResourceRole.id == role).values(headcount=1))
    again = role_of(workload(api, fabrics), role)
    assert Decimal(again["capacity_monthly_hours"]) == monthly_hours(fabrics, role)
    assert again["capacity_monthly_hours"] != held["capacity_monthly_hours"]
    assert hours(again) == hours(held)


@pytest.mark.requirement("WF-PTF-0060-A")
def test_on_the_current_day_the_hours_are_those_the_day_computes_and_an_offer_counts_by_its_weight(
    api: ContractClient, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without a date, the day: the eight hours of the line of the project In progress, then the
    # eight of the offer weighted by its 40 % (3.20) when the pricing is asked, whatever the
    # months the tasks fall on, so over a horizon that holds them all.
    monkeypatch.setattr("waterfall.api.portfolio_workload.utc_now", lambda: NOW)
    role = fabrics.costs.role
    plain = workload(api, fabrics, "horizon_months=24")
    assert plain["scope"]["as_of"] == "2026-11-19"
    assert plain["months"][0] == "2026-11"
    assert sum(Decimal(each["hours"]) for each in plain["monthly_totals"]) == Decimal("8.00")
    with_offer = workload(api, fabrics, "horizon_months=24&states=in_progress,pricing")
    assert sum(Decimal(each["hours"]) for each in with_offer["monthly_totals"]) == Decimal("11.20")
    assert sum(Decimal(each) for each in hours(role_of(with_offer, role)).values()) == Decimal(
        "11.20"
    )


# --- The node ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REF-0070-A")
def test_the_filter_by_node_keeps_its_roles_and_those_of_its_descendants_and_a_move_brings_more(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, fabrics: Portfolio
) -> None:
    # « Le déplacement d'un nœud sous un autre emporte ses descendants et ses rôles ; le plan de
    # charge agrégé filtré sur le nœud d'arrivée inclut désormais ces rôles, et les valeurs par
    # rôle sont inchangées » : read with the arrival node before and after ``updateOrgNode``.
    base = fabrics.stage.database
    arrival = node(base, "TECH")
    child = node(base, "TECH-A", arrival)
    other = node(base, "OPS")
    in_arrival = placed(base, "RA", THIRTY, arrival)
    in_child = placed(base, "RB", TWENTY, child)
    moved = placed(base, "RC", FORTY, other)
    loads: Loads = {
        in_arrival: {JUNE: "10.00"},
        in_child: {JUNE: "20.00", "2026-07": "5.00"},
        moved: {JUNE: "30.00"},
        fabrics.costs.role: {JUNE: "40.00"},
    }
    keep(owner, revision_of(fabrics, "running"), loads)
    everyone = workload(api, fabrics)
    assert len(everyone["roles"]) == 4
    before = workload(api, fabrics, f"{READ}&org_node_id={arrival}")
    assert before["scope"]["org_node_id"] == str(arrival)
    assert before["scope"]["org_node_label"] == "Nœud TECH"
    assert {each["resource_role_id"] for each in before["roles"]} == {
        str(in_arrival),
        str(in_child),
    }
    capacity = monthly_hours(fabrics, in_arrival) + monthly_hours(fabrics, in_child)
    assert before["capacity_monthly_hours"] == f"{capacity:.2f}"
    assert [each["hours"] for each in before["monthly_totals"]][:2] == ["30.00", "5.00"]
    writer = person(database, realm, "resource_settings.write")
    tree = api.get(f"{NODES}?include_inactive=true", headers=writer.headers).json()
    held = next(each for each in tree if each["org_node_id"] == str(other))
    sent = {
        "code": held["code"],
        "label": held["label"],
        "parent_id": str(arrival),
        "lock_version": held["lock_version"],
    }
    answer = api.patch(f"{NODES}/{other}", headers=writer.headers, json=sent)
    assert answer.status_code == 200, answer.text
    after = workload(api, fabrics, f"{READ}&org_node_id={arrival}")
    assert {each["resource_role_id"] for each in after["roles"]} == {
        str(in_arrival),
        str(in_child),
        str(moved),
    }
    for each in before["roles"]:
        assert role_of(after, UUID(each["resource_role_id"])) == each
    assert role_of(after, moved) == role_of(everyone, moved)
    unchanged = workload(api, fabrics)
    assert unchanged["roles"] == everyone["roles"]


@pytest.mark.story("US-2700")
def test_a_node_unknown_is_refused_on_its_parameter_and_the_view_is_read_under_its_permission(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « la lecture est sous portfolio_workload.read » : the project manager, who does not read the
    # portfolio, does not see the view (404), an anonymous caller is refused (401); the manager of
    # the portfolio reads it. An unknown node is refused on its parameter (422).
    stage = fabrics.stage
    refused = read(api, stage.reader, "workload", f"{READ}&org_node_id={uuid4()}")
    assert refused.status_code == 422
    assert [(each["pointer"], each["code"]) for each in refused.json()["fields"]] == [
        ("/query/org_node_id", "UNKNOWN_ORG_NODE")
    ]
    path = "/api/v1/portfolio/workload"
    assert api.get(path, headers=stage.manager.headers).status_code == 404
    assert api.get(path).status_code == 401
    assert api.get(path, headers=stage.reader.headers).status_code == 200
