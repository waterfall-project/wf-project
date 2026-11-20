# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The list of the projects of the portfolio, served (``getPortfolioProjects``; US-2690/L2).

Read through the service on the four projects of the fabrics (``portfolio_support``), at the date of
the witness, 3 June 2026, so that the answer does not move with the clock — the current day is read
too, with a period that does not either; every answer is validated against the contract by the
client of the tests. The columns, the projects the states and the period retain (#4020), the filters
by column and their refusals, the sort on every column, the page and its total, the reader who
opens a project and the one who does not (WF-PTF-0030); the pure part — the rows, the bounds, the
sort — is in ``test_portfolio_rows``.
"""

import json
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
import yaml
from costs_support import cost, load_import
from estimate_support import costing
from portfolio_listing_support import (
    COUNTED,
    EVERY,
    READ,
    example,
    kept_changed,
    read,
    revision_of,
    served,
    with_index,
)
from portfolio_support import OFFER, OFFERS_MARKED, REVIEW, REVIEW_MARKED, Portfolio, portfolio
from projects_support import Scene, contribute, person
from projects_support import scene as make_scene
from remaining_support import in_progress, line_named, review_marked
from support import CONTRACT

from waterfall.api.portfolio_projects import BOUNDED, DECIMAL, MONEY, ProjectsQuery
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.contributions import contribution_key
from waterfall.core.indicators.interface import current_day_reading, day_indicators, day_reading_of
from waterfall.core.portfolio.contributing import day_contribution
from waterfall.core.portfolio.interface import (
    PortfolioAsked,
    PortfolioListing,
    PortfolioReading,
    read_portfolio_projects,
)
from waterfall.core.projects.interface import Viewer
from waterfall.core.resource_settings.interface import roles_stamp
from waterfall.platform.cache import PREFIX, IndicatorsCache, Unavailable
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError, NotFoundError

if TYPE_CHECKING:
    from estimate_support import Lines
    from nodes_support import Tree
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

# The default period of a view read on 3 June 2026 starts the day after 3 June 2025; a period given
# by its start alone ends at the date.
PERIOD = "from=2026-01-01"
ESTIMATE = "1520.00"


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def labels(body: dict[str, Any]) -> list[str]:
    """Give the labels of the rows of an answer, in their order."""
    return [item["label"] for item in body["items"]]


OFFER_LABEL, RUNNING_LABEL, COMPLETED_LABEL = (
    "Extension du dépôt",
    "Rénovation de la ligne 3",
    "Poste de livraison",
)


@pytest.mark.requirement("WF-PTF-0040-A")
def test_each_column_is_present_and_an_offer_shows_its_estimate_where_a_project_shows_its_budget(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # « Chacune des colonnes citées est présente » — « Un projet en chiffrage affiche son devis et
    # sa probabilité là où un projet en cours affiche son budget de référence » : the label, the
    # code, the state, the budget or the estimate and the probability, the projection and its
    # variance, the indices with their zone, the instant of the last marked revision; the other
    # column of each is null, and the probability of a project that is not an offer.
    reader = fabrics.stage.reader
    body = served(api, reader, "projects", f"{READ}&states={COUNTED}&{PERIOD}")
    assert labels(body) == [OFFER_LABEL, COMPLETED_LABEL, RUNNING_LABEL]
    offer, completed, running = body["items"]
    assert offer == {
        "project_id": str(fabrics.offer.project_id),
        "label": OFFER_LABEL,
        "code": None,
        "state": "pricing",
        "can_open": True,
        "reference_budget": None,
        "current_estimate": ESTIMATE,
        "win_probability": "0.4",
        "project_manager_projection": None,
        "delta_to_reference": None,
        "cost_index": None,
        "schedule_index": None,
        "last_marked_at": "2026-02-16T09:00:00Z",
    }
    not_computed = {"is_computable": False, "value": None, "reason": "no_actual_cost"}
    assert running["project_id"] == str(fabrics.in_progress.project_id)
    assert (running["code"], running["state"], running["can_open"]) == (
        "PRJ-2671",
        "in_progress",
        True,
    )
    assert (running["reference_budget"], running["current_estimate"]) == (ESTIMATE, None)
    assert running["win_probability"] is None
    assert (running["project_manager_projection"], running["delta_to_reference"]) == (
        ESTIMATE,
        "0.00",
    )
    assert running["cost_index"] == {"value": not_computed, "zone": None}
    assert running["schedule_index"]["value"]["reason"] == "no_planned_value"
    assert running["last_marked_at"] == "2026-03-02T09:00:00Z"
    # A project completed shows its budget and its indices, and no projection: it is no longer
    # driven (``PortfolioProjectRow``).
    assert (completed["state"], completed["reference_budget"]) == ("completed", ESTIMATE)
    assert (completed["project_manager_projection"], completed["delta_to_reference"]) == (
        None,
        None,
    )
    assert completed["cost_index"] is not None
    assert body["scope"] == {
        "states": ["in_progress", "pricing", "completed"],
        "as_of": "2026-06-03",
        "from": "2026-01-01",
        "to": "2026-06-03",
        "org_node_id": None,
        "org_node_label": None,
        "project_count": 3,
    }
    assert body["meta"] == {"limit": 50, "offset": 0, "total": 3}


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_list_without_a_period_retains_no_project_completed_and_ignores_the_states_not_counted(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # Propre à l'US, #4020 (décision de l'auteur du 2026-11-19) : une liste lue sans période n'a
    # pas de période où un projet aurait été terminé ; ``PortfolioStates`` s'applique, le projet
    # terminé n'est pas retenu, et un état créé, perdu ou abandonné, demandé, est sans effet.
    reader = fabrics.stage.reader
    without = served(api, reader, "projects", f"{READ}&states={EVERY}")
    assert labels(without) == [OFFER_LABEL, RUNNING_LABEL]
    assert without["scope"]["states"] == EVERY.split(",")
    assert (without["scope"]["from"], without["scope"]["to"]) == (None, None)
    assert without["scope"]["project_count"] == without["meta"]["total"] == 2
    # With a period — a start alone, an end alone — the project completed on 15 April is retained
    # when it falls in it, and not when it does not.
    for query, found in (
        ("from=2026-04-15", True),
        ("to=2026-04-15", True),
        ("from=2026-04-16", False),
        ("to=2026-04-14", False),
    ):
        body = served(api, reader, "projects", f"{READ}&states={EVERY}&{query}")
        assert (COMPLETED_LABEL in labels(body)) is found, query
        assert body["scope"]["from"] is not None
        assert body["scope"]["project_count"] == len(body["items"])
    # The default state is In progress alone, on the current day as at a date.
    assert labels(served(api, reader, "projects", READ)) == [RUNNING_LABEL]
    today = served(api, reader, "projects", PERIOD)
    assert labels(today) == [RUNNING_LABEL]
    assert today["scope"]["as_of"] >= "2026-06-03"


@pytest.mark.requirement("WF-PTF-0040-A")
def test_the_list_is_filtered_by_each_column_sorted_by_the_server_and_paged_with_its_total(
    api: ContractClient, owner: Engine, fabrics: Portfolio
) -> None:
    # « Le tri par indice de coût place les projets en alerte en tête » — propre à l'US : « la
    # liste se trie sur chaque colonne dans les deux sens, par le serveur ; ``meta.total`` compte
    # les projets retenus par les filtres, et la pagination est celle du contrat ». The cost index
    # of the project In progress is 0.7 (alert), that of the project completed 1.1 (nominal), as the
    # markings kept them: the figures are those the list reads, the offer has none.
    kept_changed(owner, revision_of(fabrics, "running"), "project", with_index("cost_index", "0.7"))
    kept_changed(
        owner, revision_of(fabrics, "completed"), "project", with_index("cost_index", "1.1")
    )
    reader = fabrics.stage.reader
    base = f"{READ}&states={COUNTED}&{PERIOD}"

    def found(query: str) -> list[str]:
        return labels(served(api, reader, "projects", f"{base}&{query}"))

    assert found("sort_by=cost_index") == [RUNNING_LABEL, COMPLETED_LABEL, OFFER_LABEL]
    assert found("sort_by=cost_index&sort_order=desc") == [
        OFFER_LABEL,
        COMPLETED_LABEL,
        RUNNING_LABEL,
    ]
    by_zone = served(api, reader, "projects", f"{base}&zones=alert")
    assert labels(by_zone) == [RUNNING_LABEL]
    assert by_zone["items"][0]["cost_index"]["zone"] == "alert"
    assert found("zones=nominal,watch") == [COMPLETED_LABEL]
    # Each column by its bounds: inclusive, a null column retained by no bound.
    assert found("cost_index_max=0.7") == [RUNNING_LABEL]
    assert found("cost_index_min=0.71") == [COMPLETED_LABEL]
    assert found(f"reference_budget_min={ESTIMATE}&reference_budget_max={ESTIMATE}") == [
        COMPLETED_LABEL,
        RUNNING_LABEL,
    ]
    assert found("reference_budget_min=1520.01") == []
    assert found(f"current_estimate_min={ESTIMATE}") == [OFFER_LABEL]
    assert found("win_probability_min=0.4&win_probability_max=0.4") == [OFFER_LABEL]
    assert found("win_probability_max=0.39") == []
    assert found("project_manager_projection_min=0") == [RUNNING_LABEL]
    assert found("delta_to_reference_min=0&delta_to_reference_max=0") == [RUNNING_LABEL]
    assert found("delta_to_reference_max=-1") == []
    assert found("schedule_index_min=-1") == []
    # The code and the search ignore case and accents; a project without a code is not retained.
    assert found("code=prj-2671") == [RUNNING_LABEL]
    assert found("code=PRJ") == [COMPLETED_LABEL, RUNNING_LABEL]
    assert found("search=renovation") == [RUNNING_LABEL]
    assert found("search=DEPOT") == [OFFER_LABEL]
    assert found("search=livraison&code=prj-2672") == [COMPLETED_LABEL]
    assert found("search=livraison&code=prj-2671") == []
    # The period of the last marked revision: its start included, its end excluded.
    review = REVIEW_MARKED.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert found(f"last_marked_at_from={review}") == [COMPLETED_LABEL, RUNNING_LABEL]
    assert found(f"last_marked_at_to={review}") == [OFFER_LABEL]
    offer_marked = OFFERS_MARKED.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert found(f"last_marked_at_from={offer_marked}&last_marked_at_to={review}") == [OFFER_LABEL]
    # The sort on the other columns, in both directions; a tie by the label.
    assert found("sort_by=state") == [OFFER_LABEL, RUNNING_LABEL, COMPLETED_LABEL]
    assert found("sort_by=state&sort_order=desc") == [COMPLETED_LABEL, RUNNING_LABEL, OFFER_LABEL]
    assert found("sort_by=code&sort_order=desc") == [OFFER_LABEL, COMPLETED_LABEL, RUNNING_LABEL]
    assert found("sort_by=reference_budget") == [COMPLETED_LABEL, RUNNING_LABEL, OFFER_LABEL]
    assert found("sort_by=win_probability") == [OFFER_LABEL, COMPLETED_LABEL, RUNNING_LABEL]
    assert found("sort_by=win_probability&sort_order=desc") == [
        COMPLETED_LABEL,
        RUNNING_LABEL,
        OFFER_LABEL,
    ]
    assert found("sort_by=last_marked_at&sort_order=desc") == [
        COMPLETED_LABEL,
        RUNNING_LABEL,
        OFFER_LABEL,
    ]
    # The page, and the total of the projects the filters retain, whatever the page.
    page = served(api, reader, "projects", f"{base}&limit=1&offset=1")
    assert (labels(page), page["meta"]) == (
        [COMPLETED_LABEL],
        {"limit": 1, "offset": 1, "total": 3},
    )
    filtered = served(api, reader, "projects", f"{base}&limit=1&reference_budget_min=1000")
    assert (labels(filtered), filtered["meta"]["total"]) == ([COMPLETED_LABEL], 2)
    beyond = served(api, reader, "projects", f"{base}&limit=5&offset=3")
    assert (beyond["items"], beyond["meta"]["total"]) == ([], 3)
    assert beyond["scope"]["project_count"] == 3


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_filter_at_fault_is_refused_with_every_other_at_once_and_a_period_by_its_own_rule(
    api: ContractClient, fabrics: Portfolio
) -> None:
    # README, « A column of numbers… », « A period… » : a malformed bound is ``NUMBER_INVALID``, an
    # upper bound lower than the lower ``VALUE_OUT_OF_RANGE`` on the upper naming the lower, an end
    # before its start the same on ``last_marked_at_to``; no empty list stands in for a refusal.
    reader = fabrics.stage.reader
    query = (
        "reference_budget_min=2000&reference_budget_max=1000&cost_index_min=abc"
        "&win_probability_max=1,5&delta_to_reference_min=1.234&current_estimate_max=1.234"
        "&last_marked_at_from=2026-04-01T00:00:00Z&last_marked_at_to=2026-03-01T00:00:00Z"
    )
    answer = read(api, reader, "projects", f"{READ}&{query}")
    assert (answer.status_code, answer.json()["code"]) == (422, "VALIDATION_FAILED")
    faults = {
        (each["pointer"], each["code"]): each.get("params") for each in answer.json()["fields"]
    }
    assert faults == {
        ("/query/reference_budget_max", "VALUE_OUT_OF_RANGE"): {"minimum": "2000"},
        ("/query/cost_index_min", "NUMBER_INVALID"): None,
        ("/query/win_probability_max", "NUMBER_INVALID"): None,
        ("/query/delta_to_reference_min", "NUMBER_INVALID"): None,
        ("/query/current_estimate_max", "NUMBER_INVALID"): None,
        ("/query/last_marked_at_to", "VALUE_OUT_OF_RANGE"): {"minimum": "2026-04-01T00:00:00Z"},
    }
    # A malformed instant, a state or a zone that is none, a page outside the contract.
    for malformed, pointer, code in (
        ("last_marked_at_from=yesterday", "/query/last_marked_at_from", "DATE_INVALID"),
        ("last_marked_at_to=2026-04-01T00:00:00", "/query/last_marked_at_to", "DATE_INVALID"),
        ("from=2026-02-30", "/query/from", "DATE_INVALID"),
        ("states=in_progress,sleeping", "/query/states", "VALIDATION_FAILED"),
        ("zones=red", "/query/zones", "VALIDATION_FAILED"),
        ("limit=501", "/query/limit", "VALUE_OUT_OF_RANGE"),
        ("offset=-1", "/query/offset", "VALUE_OUT_OF_RANGE"),
        ("sort_by=cost", "/query/sort_by", "VALIDATION_FAILED"),
    ):
        refused = read(api, reader, "projects", malformed).json()
        assert (refused["status"], refused["fields"][0]["pointer"]) == (422, pointer), malformed
        assert refused["fields"][0]["code"] == code, malformed
    # A state, a zone and a bound at fault together are named at once, none masking another.
    together = read(
        api, reader, "projects", f"{READ}&states=sleeping&zones=red&cost_index_min=abc"
    ).json()
    assert {(each["pointer"], each["code"]) for each in together["fields"]} == {
        ("/query/states", "VALIDATION_FAILED"),
        ("/query/zones", "VALIDATION_FAILED"),
        ("/query/cost_index_min", "NUMBER_INVALID"),
    }
    # The period is refused by the one rule of every view: the end before the start.
    inverted = read(api, reader, "projects", f"{READ}&from=2026-03-31&to=2026-01-01").json()
    assert inverted["fields"] == [
        {"pointer": "/query/to", "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": "2026-03-31"}}
    ]


@pytest.mark.requirement("WF-PTF-0030-A")
def test_a_reader_who_opens_no_project_still_sees_every_row_and_the_one_it_contributes_to_opens(
    api: ContractClient, realm: TestRealm, database: Database, fabrics: Portfolio
) -> None:
    # « Un utilisateur habilité au portefeuille sans « consulter tous les projets », contributeur
    # d'un seul projet du périmètre, voit les totaux de tous et n'ouvre que le sien » : ``can_open``
    # est vrai pour son seul projet, les autres figurent sous leur libellé et leur code.
    reading = person(database, realm, "portfolio_projects.read", name="Zoé")
    query = f"{READ}&states={COUNTED}&{PERIOD}"
    contribute(database, str(fabrics.in_progress.project_id), reading, "contributor")
    body = served(api, reading, "projects", query)
    assert {item["label"]: item["can_open"] for item in body["items"]} == {
        OFFER_LABEL: False,
        COMPLETED_LABEL: False,
        RUNNING_LABEL: True,
    }
    assert {item["code"] for item in body["items"]} == {None, "PRJ-2671", "PRJ-2672"}
    assert body["scope"]["project_count"] == body["meta"]["total"] == 3
    every = served(api, fabrics.stage.reader, "projects", query)
    assert {item["can_open"] for item in every["items"]} == {True}


@pytest.mark.requirement("WF-PTF-0030-A")
def test_the_list_and_the_value_are_read_under_the_permission_of_the_list_alone(
    api: ContractClient, realm: TestRealm, database: Database, fabrics: Portfolio
) -> None:
    # « Chaque vue est gardée par la permission de sa fonction au catalogue, et par elle seule » :
    # a project manager — who no longer holds it, #3355 — has a 404 on both, a manager reads them,
    # and an account that holds the permission without contributing to any project reads them too.
    manager = fabrics.stage.manager
    for view in ("projects", "value"):
        refused = read(api, manager, view, READ)
        assert (refused.status_code, refused.json()["code"]) == (404, "NOT_FOUND"), view
        assert read(api, fabrics.stage.reader, view, READ).status_code == 200
        alone = person(database, realm, "portfolio_projects.read", name="Léo")
        assert read(api, alone, view, READ).status_code == 200
        without = person(database, realm, "portfolio_workload.read", name="Mia")
        assert read(api, without, view, READ).status_code == 404


@pytest.mark.requirement("WF-PTF-0040-A")
def test_the_documents_of_the_current_day_are_computed_once_and_then_read_from_the_cache(
    queue: TaskQueue, fabrics: Portfolio
) -> None:
    # « Au jour courant, chaque projet contribue par ses indicateurs du jour, lus par le cache
    # d'EP-10 » : the entry of each project that contributes is written by the first reading, and
    # the second reads the same entries and answers the same list; a reading without a cache
    # answers it too.
    database = fabrics.stage.database
    states = ("in_progress", "pricing", "completed")
    asked = PortfolioAsked(states=states, period_from=date(2026, 1, 1))
    viewer = Viewer(fabrics.stage.reader.user_id, {"all_projects_read"})
    now = datetime(2026, 11, 19, 12, tzinfo=UTC)
    cache = IndicatorsCache.of(queue, 300)
    contributing = {
        each.project_id: revision_of(fabrics, name)
        for each, name in (
            (fabrics.in_progress, "running"),
            (fabrics.offer, "offer"),
            (fabrics.completed, "completed"),
        )
    }

    def read(reading: PortfolioReading) -> dict[str, Any]:
        with database.transaction() as session:
            return read_portfolio_projects(
                session, asked, PortfolioListing(limit=50, offset=0), reading, viewer
            )

    with database.transaction() as session:
        roles = roles_stamp(session)
        keys = [
            contribution_key(session, project_id, revision, now, roles)
            for project_id, revision in contributing.items()
        ]
    try:
        assert cache.lookup_many(keys) == [None, None, None]
        first = read(PortfolioReading(now, cache))
        entries = cache.lookup_many(keys)
        assert not isinstance(entries, Unavailable)
        assert all(isinstance(entry, str) for entry in entries)
        assert read(PortfolioReading(now, cache)) == first
        assert read(PortfolioReading(now)) == first
        # The second reading serves the entry, it computes nothing: an entry altered in the cache is
        # what the list shows, and a reading without the cache shows the computed figure again.
        running = keys[0]
        kept = cache.read(running)
        assert kept is not None
        altered = json.loads(kept)
        computed = altered["project"]["reference_budget"]
        altered["project"]["reference_budget"] = "123456.00"
        cache.write(running, json.dumps(altered))
        served_again = read(PortfolioReading(now, cache))
        shown = {item["label"]: item["reference_budget"] for item in served_again["items"]}
        assert shown[RUNNING_LABEL] == "123456.00"
        assert shown[RUNNING_LABEL] != computed
        assert read(PortfolioReading(now)) == first
        assert [item["label"] for item in first["items"]] == [
            OFFER_LABEL,
            COMPLETED_LABEL,
            RUNNING_LABEL,
        ]
    finally:
        cache.client.delete(*(PREFIX + key for key in keys))
        cache.close()


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_project_of_budget_1000_cost_500_and_remaining_550_projects_1050_with_a_variance_of_50(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # « Un projet en cours de budget 1 000, de coût réel 500 et de reste à engager 550 affiche une
    # projection de 1 050 et un écart de 50 » — the same on the service, from the fixture: the
    # budget is that of the reference, the actual cost that of a line of cost loaded, the remaining
    # that of the re-estimation of the line; read on the current day, then as its marking kept it.
    data = example("WF-PTF-0040-A#b7dfea08ee32")
    stage = make_scene(api, owner, database, realm)
    costs = costing(database)

    def build(tree: Tree, lines: Lines) -> None:
        lines.made(
            tree.made("Études"),
            label="Matériel",
            quantity="1",
            cost_category_id=str(costs.material),
            unit_disbursement=data["reference_budget"],
        )

    review = in_progress(api, stage, build)
    load_import(
        stage, UUID(stage.project["project_id"]), [cost("FA-1001", None, data["actual_cost"])]
    )
    line = line_named(review.tree, "Matériel")
    sent = {
        "reestimated_amount_basis": {"unit_disbursement": data["remaining"]},
        "lock_version": line["lock_version"],
    }
    path = f"{review.tree.path}/nodes/{line['node_id']}/remaining"
    assert api.put(path, headers=stage.manager.headers, json=sent).status_code == 200

    def row(query: str) -> dict[str, Any]:
        (found,) = served(api, stage.reader, "projects", query)["items"]
        return found

    expected = {
        "reference_budget": data["reference_budget"],
        "project_manager_projection": data["projection"],
        "delta_to_reference": data["variance"],
    }
    today = row("")
    assert {name: today[name] for name in expected} == expected
    review_marked(stage, review.tree.revision, "Revue")
    kept = row(f"as_of={datetime.now(UTC).date().isoformat()}")
    assert {name: kept[name] for name in expected} == expected
    assert kept["last_marked_at"] is not None


@pytest.mark.requirement("WF-PTF-0040-A")
def test_the_forms_of_a_bound_are_the_patterns_of_money_and_of_decimal_of_the_contract() -> None:
    # The route reads a bound in the form of its column, with the patterns of the contract copied
    # (``MONEY``, ``DECIMAL``): read here in ``components/common.yaml``, so that a copy that drifts
    # is found by this test, the digits being 0 to 9 where the contract writes ``\d``.
    common = yaml.safe_load(
        (CONTRACT.parent / "components" / "common.yaml").read_text(encoding="utf-8")
    )

    def written(pattern: str) -> str:
        return pattern.removeprefix("^").removesuffix("$").replace(r"\d", "[0-9]")

    assert MONEY.pattern == written(common["Money"]["pattern"])
    assert DECIMAL.pattern == written(common["Decimal"]["pattern"])


@pytest.mark.requirement("WF-PTF-0040-A")
def test_a_contribution_is_computed_on_the_revision_it_is_given_not_on_the_current_one(
    fabrics: Portfolio,
) -> None:
    # « La révision du jour est donnée, jamais choisie » : the cache keys the entry on the revision
    # of the day, so the document must be that of this revision. The project In progress has two
    # marked revisions, its offer and its review; the contribution on each gives its own document,
    # and the one on the review is the one the reading of the day, which chooses it, gives.
    running = fabrics.in_progress
    offer, review = running.marked[OFFER][0], running.marked[REVIEW][0]
    now = datetime(2026, 11, 19, 12, tzinfo=UTC)
    with fabrics.stage.database.transaction() as session:
        on_offer = day_contribution(
            session, project_id=running.project_id, revision_id=offer, at=now
        )
        on_review = day_contribution(
            session, project_id=running.project_id, revision_id=review, at=now
        )
        chosen = current_day_reading(session, running.project_id, now)
        assert chosen.basis.revision_id == review
        assert on_review["project"] == day_indicators(session, chosen, (PROJECT,), None)[PROJECT]
    assert on_offer["project"] != on_review["project"]


@pytest.mark.requirement("WF-IND-0010-A")
def test_the_day_on_a_revision_given_refuses_a_project_never_in_progress_and_a_foreign_revision(
    fabrics: Portfolio,
) -> None:
    # « Au jour courant, chaque projet contribue par sa révision courante et ses indicateurs au
    # jour courant (WF-IND-0010) » : the revision is given, never chosen (#4199) — an offer, which
    # never was In progress, has no indicators of a project (409 ``STATE_FORBIDS_OPERATION``), and
    # a revision that is another project's is a 404, whatever the project.
    now = datetime(2026, 11, 19, 12, tzinfo=UTC)
    offer, running = fabrics.offer, fabrics.in_progress
    database = fabrics.stage.database
    with database.transaction() as session, pytest.raises(ConflictError) as never:
        day_reading_of(session, offer.project_id, offer.marked[OFFER][0], now)
    assert never.value.code == STATE_FORBIDS_OPERATION
    with database.transaction() as session, pytest.raises(NotFoundError):
        day_reading_of(session, running.project_id, offer.marked[OFFER][0], now)
    with database.transaction() as session:
        own = day_reading_of(session, running.project_id, running.marked[REVIEW][0], now)
    assert own.basis.revision_id == running.marked[REVIEW][0]


@pytest.mark.requirement("WF-PTF-0040-A")
def test_every_column_of_numbers_filtered_by_two_bounds_has_both_parameters_on_the_query() -> None:
    # « Chaque colonne de nombres se filtre par ses deux bornes » : the two texts of a column are
    # read by name from the query (``_texts``), so a column added to ``BOUNDED`` without its two
    # parameters is found here, not by a request (#4199).
    fields = set(ProjectsQuery.model_fields)
    assert {f"{column}_{bound}" for column in BOUNDED for bound in ("min", "max")} <= fields
