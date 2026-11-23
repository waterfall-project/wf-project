# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Who reads the eight views of the portfolio, and what they open (US-2670/L4, WF-PTF-0030-A).

An account that holds the permission of a view reads it, whatever the projects it contributes to:
the totals are those of every project, and only ``can_open`` follows the account — in the list, in
the heaviest risks, in the signals of the health of the control. The eight operations are reads. The
rule that says who opens a project is written once (``Viewer.sees_all``), the access judgement of a
project and the portfolio reading it both (#4131).
"""

from typing import TYPE_CHECKING, Any

import pytest
from portfolio_listing_support import READ, read, served
from portfolio_support import OFFER, REVIEW, Portfolio, another_in_progress, portfolio
from portfolio_transverse_support import READS, VIEWS, plant_risks, without_can_open
from projects_support import Person, Scene, contribute, person
from projects_support import scene as make_scene
from support import operations

from waterfall.api.app import create_app
from waterfall.core.access_roles.interface import Actor, Standing, judge_project
from waterfall.core.projects.interface import Viewer, openable
from waterfall.core.revisions.interface import last_marked_revision
from waterfall.platform.errors import NotFoundError
from waterfall.platform.permissions import ALL_PROJECTS_READ

if TYPE_CHECKING:
    from uuid import UUID

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.api.authentication import Services
    from waterfall.platform.database import Database

SECOND = "Second chantier"
STATES = "states=in_progress,pricing"


@pytest.fixture
def fabrics(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Portfolio:
    """Give the four projects of the fabrics, on the platform of a scene."""
    stage: Scene = make_scene(api, owner, database, realm)
    return portfolio(api, stage)


def second_with_risks(api: ContractClient, owner: Engine, fabrics: Portfolio) -> UUID:
    """Write a second project In progress, and a risk kept by each of the three that bear one."""
    second = another_in_progress(api, fabrics, SECOND, "PRJ-2674")
    with fabrics.stage.database.transaction() as session:
        revision = last_marked_revision(session, second)
    assert revision is not None
    plant_risks(
        owner,
        [
            (fabrics.in_progress.marked[REVIEW][0], "Retard du fournisseur", "60.00"),
            (fabrics.offer.marked[OFFER][0], "Retard de livraison", "250.00"),
            (revision, "Gel des sols", "40.00"),
        ],
    )
    return second


def readings(api: ContractClient, who: Person) -> dict[str, dict[str, Any]]:
    """Read the eight views as an account does, as of the date of the witness; each is served."""
    query = f"{READ}&{STATES}"
    return {view: served(api, who, view, query) for view in VIEWS}


def openings(body: dict[str, Any], view: str) -> dict[str, bool]:
    """Give, by project label, whether a view says the reader opens its project."""
    match view:
        case "projects":
            return {each["label"]: each["can_open"] for each in body["items"]}
        case "risks":
            return {each["project_label"]: each["can_open"] for each in body["heaviest"]}
        case "pilot-health":
            return {each["project_label"]: each["can_open"] for each in body["signals"]}
        case _:
            message = f"{view} gives no project to open"
            raise ValueError(message)


@pytest.mark.requirement("WF-PTF-0030-A")
def test_an_account_that_holds_the_portfolio_permissions_and_contributes_to_no_project_reads_all(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, fabrics: Portfolio
) -> None:
    # « Un utilisateur habilité au portefeuille mais contributeur d'aucun projet consulte toutes
    # les vues » : the permissions of the eight views, no ``all_projects_read``, no project. Every
    # view answers, with the totals of the reader of every project; no project opens.
    second_with_risks(api, owner, fabrics)
    who = person(database, realm, *READS, name="Alix")
    held = readings(api, who)
    every = readings(api, fabrics.stage.reader)
    assert set(held) == set(VIEWS)
    for view in VIEWS:
        assert without_can_open(held[view]) == without_can_open(every[view]), view
    for view in ("projects", "risks", "pilot-health"):
        assert openings(every[view], view), view
        assert set(openings(every[view], view).values()) == {True}, view
        assert set(openings(held[view], view).values()) == {False}, view


@pytest.mark.requirement("WF-PTF-0030-A")
def test_the_contributor_of_one_project_sees_every_total_and_opens_his_own_alone(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm, fabrics: Portfolio
) -> None:
    # « Un utilisateur habilité au portefeuille sans « consulter tous les projets », contributeur
    # d'un seul projet du périmètre, voit les totaux de tous et n'ouvre que le sien » : can_open is
    # true for his one project, in the list, in the heaviest risks and in the signals of the health
    # of the control; the others stay there under their label and their code.
    second_with_risks(api, owner, fabrics)
    mine = fabrics.in_progress
    who = person(database, realm, *READS, name="Zoé")
    contribute(database, str(mine.project_id), who, "contributor")
    held = readings(api, who)
    every = readings(api, fabrics.stage.reader)
    for view in VIEWS:
        assert without_can_open(held[view]) == without_can_open(every[view]), view
    expected = {mine.label: True, fabrics.offer.label: False, SECOND: False}
    assert openings(held["projects"], "projects") == expected
    assert openings(held["risks"], "risks") == expected
    assert openings(held["pilot-health"], "pilot-health") == {mine.label: True, SECOND: False}
    rows = {each["label"]: each for each in held["projects"]["items"]}
    assert (rows[SECOND]["code"], rows[fabrics.offer.label]["code"]) == ("PRJ-2674", None)
    # The same account, once the contributor of the second, opens it too and nothing else changes.
    contribute(database, str(rows[SECOND]["project_id"]), who, "contributor")
    both = readings(api, who)
    assert openings(both["projects"], "projects") == {**expected, SECOND: True}
    assert without_can_open(both["value"]) == without_can_open(every["value"])


@pytest.mark.requirement("WF-PTF-0030-A")
def test_each_view_is_read_under_the_permission_of_its_function_and_under_it_alone(
    api: ContractClient, database: Database, realm: TestRealm, fabrics: Portfolio
) -> None:
    # « Chaque vue est gardée par la permission de sa fonction au catalogue, et par elle seule » :
    # an account that holds one of the permissions reads the views that permission guards — the list
    # and the value share one — and finds the others absent (404), as an account that holds none of
    # them, a project manager included; an anonymous caller is refused (401).
    guarded = {
        "projects": "portfolio_projects.read",
        "value": "portfolio_projects.read",
        "workload": "portfolio_workload.read",
        "performance": "portfolio_performance.read",
        "cost-structure": "portfolio_cost_structure.read",
        "risks": "portfolio_risks.read",
        "cost-curve": "portfolio_cost_curve.read",
        "pilot-health": "portfolio_pilot_health.read",
    }
    assert set(guarded) == set(VIEWS)
    assert set(guarded.values()) == set(READS)
    for number, permission in enumerate(READS):
        who = person(database, realm, permission, name=f"Lou{number}")
        found = {view: read(api, who, view, READ).status_code for view in VIEWS}
        assert found == {view: 200 if guarded[view] == permission else 404 for view in VIEWS}
    manager = fabrics.stage.manager
    assert {read(api, manager, view, READ).status_code for view in VIEWS} == {404}
    assert {api.get(f"/api/v1/portfolio/{view}").status_code for view in VIEWS} == {401}


@pytest.mark.requirement("WF-PTF-0030-A")
def test_the_eight_operations_of_the_portfolio_are_reads_and_the_portfolio_serves_nothing_else(
    contract: OpenAPI, services: Services
) -> None:
    # « Aucune vue ne propose de modifier une donnée » : the contract declares the eight under GET,
    # no other operation under the portfolio, and the service serves the same routes and no other.
    declared = operations(contract)
    assert {declared[name][0] for name in VIEWS.values()} == {"GET"}
    below = {
        name: method
        for name, (method, path) in declared.items()
        if path.startswith("/api/v1/portfolio/")
    }
    assert below == dict.fromkeys(VIEWS.values(), "GET")
    served_below = {
        operation["operationId"]: method
        for path, item in create_app(services).openapi()["paths"].items()
        if path.startswith("/api/v1/portfolio/")
        for method, operation in item.items()
    }
    assert served_below == dict.fromkeys(VIEWS.values(), "get")


@pytest.mark.requirement("WF-PTF-0030-A")
def test_the_access_judgement_of_a_project_and_can_open_of_the_portfolio_agree(
    api: ContractClient, database: Database, realm: TestRealm, fabrics: Portfolio
) -> None:
    # « Une seule règle « qui peut ouvrir un projet » » (#4131) : for the reader of every project,
    # the contributor of one project and an account that is neither, each project the list says is
    # opened is one the service of the project answers (200), and each it says is not is one it
    # judges absent (404) — whatever the account.
    consulting = ("project_settings.read", *READS)
    mine, other = fabrics.in_progress, fabrics.offer
    contributor = person(database, realm, *consulting, name="Lou")
    outsider = person(database, realm, *consulting, name="Max")
    contribute(database, str(mine.project_id), contributor, "contributor")
    for who in (fabrics.stage.reader, contributor, outsider):
        listed = {
            each["project_id"]: each["can_open"]
            for each in served(api, who, "projects", f"{READ}&{STATES}")["items"]
        }
        assert set(listed) == {str(mine.project_id), str(other.project_id)}
        for project_id, opens in listed.items():
            answered = api.get(f"/api/v1/projects/{project_id}", headers=who.headers).status_code
            assert answered == (200 if opens else 404), (who.user_id, project_id)
    assert listed == {str(mine.project_id): False, str(other.project_id): False}


@pytest.mark.requirement("WF-PTF-0030-A")
def test_changing_the_rule_that_says_who_sees_every_project_changes_the_judgement_and_can_open(
    database: Database, fabrics: Portfolio, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The rule is ``Viewer.sees_all``, read by the judgement of a project (``access_roles``) and by
    # ``openable``: with ``all_projects_read`` both let the account through, and when the one rule
    # says no, both follow — no second copy of it is left to say yes.
    project_id = fabrics.in_progress.project_id
    user_id = fabrics.stage.reader.user_id
    actor = Actor(user_id, (ALL_PROJECTS_READ,))
    outside = Standing(exists=True, kind=None)
    viewer = Viewer(user_id, {ALL_PROJECTS_READ})
    judge_project(actor, outside, ())
    with database.transaction() as session:
        assert openable(session, [project_id], viewer) == {project_id}
    monkeypatch.setattr(Viewer, "sees_all", property(lambda _: False))
    with pytest.raises(NotFoundError):
        judge_project(actor, outside, ())
    with database.transaction() as session:
        assert openable(session, [project_id], Viewer(user_id, {ALL_PROJECTS_READ})) == frozenset()
