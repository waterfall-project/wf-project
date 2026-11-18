# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The evolution of the indices of a project, served (``getIndexHistory``; US-1700).

A project In progress whose current revision is marked three times, after its reference — marked
during the pricing, which gives no point —, and costs loaded between the reviews: a point by review
for each scope, as its marking kept it, the point of the day, the thresholds, the scope asked for,
the zones classified on the thresholds of the reading, and the refusals. The project is the one of
``curves_support``, its two tasks borne by a subproject. Every answer is checked against the
contract by the client of the tests.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from costs_support import load_import
from curves_support import over_three_months
from day_indicators_support import dated, indicators, subproject
from indicators_support import clock_setter, marked, thresholds
from nodes_support import Tree, faults, opened, refusal
from planning_support import DAY
from projects_support import PROJECTS
from projects_support import scene as make_scene

from waterfall.core.cost_settings.interface import (
    IndexThresholds,
    SettingsChange,
    read_reference_settings,
    write_reference_settings,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from indicators_support import Clock
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

FIRST, SECOND, THIRD, TODAY = (DAY + timedelta(days=each) for each in (60, 67, 74, 75))
VERSIONS = ("v1", "v2", "v3")
PROJECT = "project"
UNASSIGNED = "unassigned"
THRESHOLDS = {
    "cost_watch": "0.9",
    "cost_alert": "0.8",
    "schedule_watch": "0.9",
    "schedule_alert": "0.8",
}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the history is computed on."""
    return clock_setter(monkeypatch)


@dataclass(frozen=True)
class Review:
    """A review: the revision marked, its version, its instant, the indicators read before it."""

    revision_id: str
    version_name: str
    at: datetime
    read: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class Reviewed:
    """A project In progress marked three times: its subprojects, its reviews, its current tree."""

    named: str
    empty: str
    reviews: list[Review]
    tree: Tree

    @property
    def scopes(self) -> list[str]:
        """Give the scopes of the history, in the order of the answer."""
        return [PROJECT, self.named, self.empty, UNASSIGNED]


def text(at: datetime) -> str:
    """Write an instant as the contract does."""
    return at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def charged(stage: Scene, number: str, code: str | None, amount: str, day: date) -> None:
    """Import a line of cost dated a day, imputed to a subproject by its code or to none."""
    load_import(stage, UUID(stage.project["project_id"]), [dated(number, code, amount, day)])


def history_answer(api: ContractClient, stage: Scene, query: str = "") -> Any:
    """Ask for the history of the project of the stage, the query said; give the answer."""
    return api.get(
        f"{PROJECTS}/{stage.project['project_id']}/indicators/index-history{query}",
        headers=stage.manager.headers,
    )


def history(api: ContractClient, stage: Scene, query: str = "") -> dict[str, Any]:
    """Read the history of the project of the stage, which must be served."""
    answer = history_answer(api, stage, query)
    assert answer.status_code == 200, answer.text
    return answer.json()


def scope_points(body: dict[str, Any], scope: str) -> list[dict[str, Any]]:
    """Give the points of a scope of the history."""
    return next(each for each in body["scopes"] if each["scope"] == scope)["points"]


def reviewed(api: ContractClient, stage: Scene, clock: Clock, *, reopen: bool = True) -> Reviewed:
    """Mark the current revision three times, costs loaded between; read each scope just before.

    The studies are completed (EV 400), 100 of cost dated early, then 350 before the second
    review, and 100 imputed to ``SP-1`` before the third: the cost index of the project is 4,
    0.8889, 0.7273.
    """
    # Created in the reverse order of their codes: ``listSubprojects`` sorts by code.
    empty = subproject(api, stage, "SP-2", "Essais")
    named = subproject(api, stage, "SP-1", "Poste de commande")
    tree = over_three_months(api, stage, clock, subproject_id=named).tree
    costs = {
        SECOND: ("FA-2", None, "350.00", DAY + timedelta(days=62)),
        THIRD: ("FA-3", "SP-1", "100.00", DAY + timedelta(days=70)),
    }
    scopes = [PROJECT, named, empty, UNASSIGNED]
    reviews: list[Review] = []
    for day, version in zip((FIRST, SECOND, THIRD), VERSIONS, strict=True):
        if day in costs:
            charged(stage, *costs[day])
        clock(day)
        read = {each: indicators(api, stage, f"?scope={each}") for each in scopes}
        revision_id = tree.revision["revision_id"]
        at = marked(stage, tree.revision, version)
        reviews.append(Review(revision_id, version, at, read))
        if reopen or version != VERSIONS[-1]:
            tree = Tree(api, stage, opened(api, stage))
    clock(TODAY)
    return Reviewed(named, empty, reviews, tree)


@pytest.fixture
def project(api: ContractClient, stage: Scene, clock: Clock) -> Reviewed:
    """Give a project In progress marked three times."""
    return reviewed(api, stage, clock)


@pytest.mark.requirement("WF-IND-0130-A")
def test_three_reviews_marked_in_progress_give_four_points_the_last_of_the_day(
    api: ContractClient, stage: Scene, project: Reviewed
) -> None:
    # « Sur un projet de trois révisions marquées à partir de l’état En cours, chaque courbe porte
    # quatre points, le dernier au jour courant ; une révision marquée pendant le chiffrage n’en
    # donne aucun (WF-DAT-0040) ; les deux seuils sont tracés ; un sous-projet a ses courbes. » The
    # reference, marked during the pricing, gives no point; each scope has the three reviews by
    # marking, their indices as the marking kept them, then the day, its version name null.
    body = history(api, stage)
    assert [each["scope"] for each in body["scopes"]] == project.scopes
    assert [each["label"] for each in body["scopes"]] == [
        None,
        "Poste de commande",
        "Essais",
        None,
    ]
    assert body["thresholds"] == THRESHOLDS
    for scope in project.scopes:
        found = scope_points(body, scope)
        assert len(found) == len(project.reviews) + 1 == 4
        for point, review in zip(found[:-1], project.reviews, strict=True):
            assert (point["at"], point["revision_id"], point["version_name"]) == (
                text(review.at),
                review.revision_id,
                review.version_name,
            )
            for name in ("cost_index", "schedule_index"):
                assert point[name] == review.read[scope][name]
        last = found[-1]
        assert (last["at"], last["version_name"]) == (
            text(project.reviews[-1].at + timedelta(days=1)),
            None,
        )
        today = indicators(api, stage, f"?scope={scope}")
        assert (last["cost_index"], last["schedule_index"]) == (
            today["cost_index"],
            today["schedule_index"],
        )
        assert last["revision_id"] == project.tree.revision["revision_id"]


@pytest.mark.requirement("WF-IND-0130-A")
@pytest.mark.usefixtures("project")
def test_the_zone_of_each_point_is_classified_on_the_thresholds_of_the_reading(
    api: ContractClient, stage: Scene
) -> None:
    # « les deux seuils sont tracés » : the cost index of the project, 4, 0.8889, 0.7273 then the
    # day, 0.7273, is nominal, in watch, in alert; the thresholds lowered afterward reclassify every
    # point, the values untouched, and the answer carries the thresholds that classified them.
    found = scope_points(history(api, stage), PROJECT)
    assert [
        (each["cost_index"]["value"]["value"], each["cost_index"]["zone"]) for each in found
    ] == [
        ("4", "nominal"),
        ("0.8889", "watch"),
        ("0.7273", "alert"),
        ("0.7273", "alert"),
    ]
    thresholds(stage, "0.5", "0.3")
    body = history(api, stage)
    assert body["thresholds"] == {
        "cost_watch": "0.5",
        "cost_alert": "0.3",
        "schedule_watch": "0.5",
        "schedule_alert": "0.3",
    }
    again = scope_points(body, PROJECT)
    assert [each["cost_index"]["value"]["value"] for each in again] == [
        each["cost_index"]["value"]["value"] for each in found
    ]
    assert {each["cost_index"]["zone"] for each in again} == {"nominal"}
    # The schedule index, 0.47 to 0.42, is reclassified too: in alert at 0.8, in watch at 0.5.
    assert {each["schedule_index"]["zone"] for each in found} == {"alert"}
    assert {each["schedule_index"]["zone"] for each in again} == {"watch"}


@pytest.mark.requirement("WF-IND-0130-A")
def test_an_index_a_marking_could_not_compute_is_a_point_not_computable_never_omitted(
    api: ContractClient, stage: Scene, project: Reviewed
) -> None:
    # #1777: the subproject without actual cost at the first two reviews, its cost index is not
    # computable there — a point nonetheless, its zone null —, and computable at the third, when a
    # cost is imputed to it; the subproject without a line nor a cost has no index at any point.
    body = history(api, stage)
    named = scope_points(body, project.named)
    assert [each["cost_index"]["value"]["is_computable"] for each in named] == [
        False,
        False,
        True,
        True,
    ]
    assert named[0]["cost_index"] == {
        "value": {"is_computable": False, "value": None, "reason": "no_actual_cost"},
        "zone": None,
    }
    empty = scope_points(body, project.empty)
    assert len(empty) == 4
    assert {
        (each[name]["value"]["is_computable"], each[name]["zone"])
        for each in empty
        for name in ("cost_index", "schedule_index")
    } == {(False, None)}


@pytest.mark.requirement("WF-IND-0130-A")
def test_a_subproject_created_after_the_markings_has_the_point_of_the_day_alone(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # No marking kept a document for it: the points of the reviews are not invented.
    reviewed(api, stage, clock)
    created = subproject(api, stage, "SP-3", "Réception")
    found = scope_points(history(api, stage), created)
    assert [each["version_name"] for each in found] == [None]


@pytest.mark.requirement("WF-IND-0130-A")
def test_with_a_scope_the_history_is_that_of_the_scope_alone_that_the_context_names(
    api: ContractClient, stage: Scene, project: Reviewed
) -> None:
    # « avec `scope`, la seule maille demandée, que `context.scope` nomme » : a subproject, the
    # project, the set of none; `context` is the one of the last point.
    whole = history(api, stage)
    for scope in (project.named, PROJECT, UNASSIGNED):
        body = history(api, stage, f"?scope={scope}")
        assert body["context"]["scope"] == scope
        assert [each["scope"] for each in body["scopes"]] == [scope]
        assert body["scopes"][0] == next(each for each in whole["scopes"] if each["scope"] == scope)
    assert history(api, stage)["context"]["scope"] == PROJECT
    assert whole["context"] == {
        "revision_id": project.tree.revision["revision_id"],
        "revision_status": "draft",
        "computed_at": text(project.reviews[-1].at + timedelta(days=1)),
        "scope": PROJECT,
        "is_stored": False,
    }
    unknown = history_answer(api, stage, f"?scope={uuid4()}")
    assert faults(unknown) == [("/query/scope", "UNKNOWN_SUBPROJECT", {})]
    assert faults(history_answer(api, stage, "?scope=SP-1")) == [
        ("/query/scope", "UNKNOWN_SUBPROJECT", {})
    ]


@pytest.mark.requirement("WF-IND-0130-A")
def test_without_a_current_revision_the_point_of_the_day_is_on_the_last_marked_revision(
    api: ContractClient, stage: Scene, clock: Clock
) -> None:
    # « sur la révision en cours ou, sans elle, sur la dernière révision marquée avec le coût réel
    # du jour » : the third review marked and none opened, the last point is on it, named by no
    # version, and the context says marked.
    found = reviewed(api, stage, clock, reopen=False)
    body = history(api, stage)
    last = scope_points(body, PROJECT)[-1]
    assert (last["revision_id"], last["version_name"]) == (found.reviews[-1].revision_id, None)
    assert (body["context"]["revision_id"], body["context"]["revision_status"]) == (
        found.reviews[-1].revision_id,
        "marked",
    )
    assert len(scope_points(body, PROJECT)) == 4


@pytest.mark.requirement("WF-IND-0130-A")
def test_a_project_before_in_progress_has_no_history_its_state_is_named(
    api: ContractClient, stage: Scene
) -> None:
    # #1778: 409 ``STATE_FORBIDS_OPERATION``, ``params.state`` and ``params.state_enum``, before the
    # scope, which an unknown one would refuse otherwise; the pricing under way is not In progress.
    assert refusal(history_answer(api, stage)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"state": "created", "state_enum": "ProjectState"},
    )
    Tree(api, stage, opened(api, stage))
    for query in ("", "?scope=SP-1"):
        assert refusal(history_answer(api, stage, query)) == (
            409,
            "STATE_FORBIDS_OPERATION",
            {"state": "pricing", "state_enum": "ProjectState"},
        )


@pytest.mark.requirement("WF-IND-0130-A")
def test_an_unknown_project_is_not_found(api: ContractClient, stage: Scene) -> None:
    answer = api.get(
        f"{PROJECTS}/{uuid4()}/indicators/index-history", headers=stage.manager.headers
    )
    assert answer.status_code == 404, answer.text


@pytest.mark.requirement("WF-REF-0170-A")
@pytest.mark.usefixtures("project")
def test_the_history_and_the_settings_write_the_thresholds_alike(
    api: ContractClient, stage: Scene
) -> None:
    # One writing of the four thresholds serves ``getReferenceSettings`` and ``getIndexHistory``:
    # a value like 0.875 reads the same, without a useless zero.
    held = IndexThresholds(Decimal("0.900"), Decimal("0.875"), Decimal("0.9500"), Decimal("0.8"))
    with stage.database.transaction() as session:
        counter = read_reference_settings(session).lock_version
        write_reference_settings(
            session, SettingsChange(index_thresholds=held), counter, Act(None, utc_now())
        )
    settings = api.get("/api/v1/reference/settings", headers=stage.manager.headers)
    assert settings.status_code == 200, settings.text
    assert history(api, stage)["thresholds"] == settings.json()["index_thresholds"]
    assert settings.json()["index_thresholds"]["cost_alert"] == "0.875"
