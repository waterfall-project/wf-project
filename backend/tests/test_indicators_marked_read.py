# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of a marked revision read as its marking kept them, by name or at a date.

Laid by US-1660/L1, the socle of EP-10, so that no two stories create the same file;
US-1670/L2 writes its tests here (EP-10, "Les tests du back"). ``getProjectIndicators`` with the
``revision_id`` of a marked revision answers the document its marking kept, its zones classified on
the thresholds of the day; with ``as_of``, that of the last revision marked on or before the day
among those that kept one, the same 409 as an offer's when there is none; the estimate and the
remaining to commit of a marked revision are read as kept; the exit that marks is read on the
revision it marked. The project is the one of ``test_indicators_stored``, whose helpers are read.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import declare, line
from costs_support import load_import
from day_indicators_support import (
    Planned,
    completed,
    dated,
    indicators,
    indicators_answer,
    priced,
    subproject,
)
from fastapi.testclient import TestClient
from imports_trial import import_worker
from indicators_support import clock_setter
from nodes_support import faults, refusal
from planning_support import DAY
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from support import ContractClient
from test_indicators_stored import ELEMENT, ONE_DAY, document, imported, kept, zulu

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.interface import (
    IndexThresholds,
    SettingsChange,
    read_reference_settings,
    write_reference_settings,
)
from waterfall.core.costs.interface import PROJECT
from waterfall.core.costs.tables import CostLine
from waterfall.core.indicators.interface import KeptOfKind, kept_of_kind
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.revisions.interface import mark_revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.installation import TIME_ZONE
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from day_indicators_support import Priced
    from indicators_support import Clock
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

D = Decimal
OFFER: tuple[int, str, dict[str, Any]] = (409, "STATE_FORBIDS_OPERATION", {})


@pytest.fixture
def import_services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API on the database, the queue and the bucket of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def api(contract: OpenAPI, import_services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(import_services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, the mapping of the extractions declared, and a project."""
    made = make_scene(api, owner, database, realm)
    declare(database)
    return made


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the indicators are computed on."""
    return clock_setter(monkeypatch)


@pytest.fixture
def lot(api: ContractClient, stage: Scene) -> str:
    """Give a subproject of the project, which the line of the wiring bears."""
    return subproject(api, stage, "10001", "Lot 10001")


@pytest.fixture
def project(api: ContractClient, stage: Scene, lot: str) -> Priced:
    """Give a project In progress of budget 1 000, the studies, 400, completed on ``DAY``."""
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600", lot)])
    completed(found.tree, "Études", DAY)
    return found


def marked_on(
    stage: Scene, clock: Clock, revision: dict[str, Any], days: int, name: str = "Revue"
) -> datetime:
    """Mark a revision by the transaction of the worker, ``days`` after the real day; give it."""
    at = clock(utc_now().date() + days * ONE_DAY)
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        act = Act(stage.manager.user_id, at)
        mark_revision(session, UUID(revision["revision_id"]), name, None, act)
    return at


def project_path(stage: Scene) -> str:
    """Give the address of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def reopened(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the revision that follows the one marked, as the manager does."""
    answer = api.post(f"{project_path(stage)}/revisions", headers=stage.manager.headers, json={})
    assert answer.status_code == 201, answer.text
    return answer.json()


def thresholds(stage: Scene, watch: str, alert: str) -> None:
    """Set the watch and alert thresholds of both indices, as ``updateReferenceSettings`` does."""
    held = IndexThresholds(D(watch), D(alert), D(watch), D(alert))
    with stage.database.transaction() as session:
        counter = read_reference_settings(session).lock_version
        change = SettingsChange(index_thresholds=held)
        write_reference_settings(session, change, counter, Act(None, utc_now()))


def named(revision_id: str, scope: str = "") -> str:
    """Give the query that names a revision, and a scope if said."""
    return f"?revision_id={revision_id}" + (f"&scope={scope}" if scope else "")


@pytest.mark.requirement("WF-IND-0010-A")
@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_marked_revision_named_answers_the_document_its_marking_kept(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced, lot: str
) -> None:
    # Propre à l'US : avec le `revision_id` d'une révision marquée, le document conservé de la
    # maille, `is_stored` vrai, `computed_at` l'instant du marquage, `revision_status` `marked`,
    # on the project and on a subproject; the day, since, has moved on.
    revision_id = project.tree.revision["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    at = marked_on(stage, clock, project.tree.revision, 1)
    clock(utc_now().date() + 9 * ONE_DAY)
    for scope in (PROJECT, lot):
        found = indicators(api, stage, named(revision_id, scope))
        assert found["context"] == {
            "revision_id": revision_id,
            "revision_status": "marked",
            "computed_at": zulu(at),
            "scope": scope,
            "is_stored": True,
        }
        held = document(stage.database, revision_id, "project", scope)
        zones = {name: held[name] for name in ("cost_index", "schedule_index")}
        assert {**found, **zones} == held
    whole = indicators(api, stage, named(revision_id))
    assert (whole["reference_budget"], whole["earned_value"], whole["actual_cost"]) == (
        "1000.00",
        "400.00",
        "500.00",
    )


@pytest.mark.requirement("WF-REF-0130-A")
def test_the_zone_of_a_kept_index_follows_the_thresholds_of_the_day_and_its_value_does_not(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # « Après abaissement du seuil d'alerte, la zone de l'indice de coût d'une révision marquée
    # peut changer, sa valeur non. » An index of 0.8 (earned 400, cost 500): in watch at 0.9 and
    # 0.7, nominal at 0.8 and 0.6; the document kept holds the value, never the zone.
    revision_id = project.tree.revision["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    marked_on(stage, clock, project.tree.revision, 1)
    found: dict[str, dict[str, Any]] = {}
    for watch, alert in (("0.9", "0.7"), ("0.8", "0.6")):
        thresholds(stage, watch, alert)
        found[watch] = indicators(api, stage, named(revision_id))["cost_index"]
    assert {each: index["zone"] for each, index in found.items()} == {
        "0.9": "watch",
        "0.8": "nominal",
    }
    assert {index["value"]["value"] for index in found.values()} == {"0.8"}
    held = document(stage.database, revision_id, "project", PROJECT)
    assert held["cost_index"]["zone"] is None


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-IND-0010-A")
def test_the_kept_answer_is_the_same_after_an_import_and_after_the_exclusion_of_a_line(
    api: ContractClient, stage: Scene, worker: Worker, clock: Clock, project: Priced
) -> None:
    # « Les indicateurs conservés d'une révision marquée sont identiques avant et après un import
    # de coûts réels postérieur. » The answer, not only the row: after an extraction that adds a
    # line dated before the marking and updates a known one, then after the exclusion of a line
    # known at the marking by ``setActualCostTrackedScope``, the same body.
    revision_id = project.tree.revision["revision_id"]
    first_line = line(element=ELEMENT, number="FA-1", on="2026-04-02", amount=500)
    imported(api, stage, worker, [first_line])
    marked_on(stage, clock, project.tree.revision, 1)
    before = indicators(api, stage, named(revision_id))
    assert before["actual_cost"] == "500.00"
    rows = [
        line(element=ELEMENT, number="FA-1", on="2026-04-02", amount=700),
        line(element=ELEMENT, number="FA-2", on="2026-04-03", amount=250),
    ]
    imported(api, stage, worker, rows)
    assert indicators(api, stage, named(revision_id)) == before
    with stage.database.transaction() as session:
        first = session.scalars(select(CostLine.id).where(CostLine.document_number == "FA-1")).one()
    path = f"{project_path(stage)}/actual-costs/{first}/tracked-scope"
    excluded = api.put(
        path,
        headers=stage.manager.headers,
        json={"is_in_tracked_scope": False, "reason": "Doublon"},
    )
    assert excluded.status_code == 200, excluded.text
    assert indicators(api, stage, named(revision_id)) == before
    assert indicators(api, stage)["actual_cost"] == "250.00"


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_revision_marked_before_in_progress_has_no_indicator_of_the_project_and_is_refused(
    api: ContractClient, stage: Scene, project: Priced
) -> None:
    # « Sur un projet à l'état Chiffrage, aucun indicateur projet n'est proposé. » The reference,
    # marked in pricing, kept its estimate alone: named, 409 without ``params.state`` (#1779, G-02),
    # the project being In progress now.
    reference = str(project.reference_id)
    assert refusal(indicators_answer(api, stage, named(reference))) == OFFER
    assert refusal(indicators_answer(api, stage, named(reference, "unassigned"))) == OFFER


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_date_names_the_last_revision_marked_on_or_before_it_among_those_that_kept_a_document(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # `as_of` : la dernière révision marquée dont `marked_at` ≤ la date, parmi celles qui ont un
    # document `project`, `context.revision_id` la nommant. Three markings: the reference, in
    # pricing, which kept none; the review, marked in one day, and its successor two days after.
    first = project.tree.revision["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    one = marked_on(stage, clock, project.tree.revision, 1)
    second = reopened(api, stage)["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-2", None, "100.00", DAY)])
    three = marked_on(stage, clock, {"revision_id": second}, 3, "Revue 2")
    asked = [
        (one.date(), first),
        (three.date() - ONE_DAY, first),
        (three.date(), second),
        (three.date() + 30 * ONE_DAY, second),
    ]
    for day, revision_id in asked:
        found = indicators(api, stage, f"?as_of={day.isoformat()}")
        assert found["context"]["revision_id"] == revision_id, day
        assert (found["context"]["is_stored"], found["context"]["computed_at"]) == (
            True,
            zulu(one if revision_id == first else three),
        )
    assert indicators(api, stage, f"?as_of={three.date().isoformat()}")["actual_cost"] == "600.00"
    assert indicators(api, stage, f"?as_of={one.date().isoformat()}")["actual_cost"] == "500.00"


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_date_that_names_no_revision_with_a_document_is_refused_as_an_offer_is(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # Le 409 de l'offre (#2449) : a date before every marking, and a date on which the only
    # revision marked is the reference, marked in pricing, which kept no document of the project.
    reference_day = utc_now().date()
    marked_on(stage, clock, project.tree.revision, 1)
    for day in (reference_day, reference_day - 30 * ONE_DAY, date(2000, 1, 1)):
        assert refusal(indicators_answer(api, stage, f"?as_of={day.isoformat()}")) == OFFER, day


@pytest.mark.requirement("WF-DAT-0040-A")
def test_the_estimate_and_the_remaining_of_a_marked_revision_are_read_as_kept(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # Propre à l'US : `getEstimateIndicators` and `getRemainingIndicators` with the `revision_id`
    # of a marked revision answer the document kept, `is_stored` true; on the current revision,
    # the computation at the reading, `is_stored` false, unchanged.
    base = project_path(stage)
    headers = stage.manager.headers
    review = project.tree.revision["revision_id"]
    for path in ("estimate-indicators", "remaining-indicators"):
        current = api.get(f"{base}/{path}?revision_id={review}", headers=headers)
        assert current.status_code == 200, current.text
        assert current.json()["context"]["is_stored"] is False
    marked_on(stage, clock, project.tree.revision, 1)
    rows = kept(stage.database, review)
    for path, key in (("estimate-indicators", "estimate"), ("remaining-indicators", "remaining")):
        found = api.get(f"{base}/{path}?revision_id={review}", headers=headers)
        assert found.status_code == 200, found.text
        assert found.json() == rows[key, PROJECT][0]
        assert found.json()["context"]["is_stored"] is True
    # Without a current revision, the last one marked, as kept.
    latest = api.get(f"{base}/estimate-indicators", headers=headers).json()
    assert latest == rows["estimate", PROJECT][0]
    # The reference, marked in pricing, kept its estimate: read as kept too.
    old = api.get(f"{base}/estimate-indicators?revision_id={project.reference_id}", headers=headers)
    assert old.json()["context"]["is_stored"] is True
    assert old.json()["total"]["value"] == "1000.00"


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_scope_the_marking_did_not_keep_is_unknown_to_the_revision_not_computed(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced, lot: str
) -> None:
    # « Les routes lisent `stored_document` pour une révision marquée » : a subproject created
    # after the marking is none of that revision's, refused as a subproject the project does not
    # have (422), the revision never computed again; the scopes it kept are read as kept.
    review = project.tree.revision["revision_id"]
    marked_on(stage, clock, project.tree.revision, 1)
    since = subproject(api, stage, "10002", "Lot 10002")
    base = project_path(stage)
    headers = stage.manager.headers
    unknown: list[tuple[str, str, dict[str, Any]]] = [("/query/scope", "UNKNOWN_SUBPROJECT", {})]
    refused = api.get(f"{base}/estimate-indicators{named(review, since)}", headers=headers)
    assert faults(refused) == unknown
    # The current revision, opened after, knows it and computes it.
    current = reopened(api, stage)["revision_id"]
    found = api.get(f"{base}/estimate-indicators{named(current, since)}", headers=headers)
    assert found.status_code == 200, found.text
    assert found.json()["context"]["is_stored"] is False
    kept_scope = api.get(
        f"{base}/estimate-indicators{named(review, lot)}",
        headers=headers,
    )
    assert kept_scope.status_code == 200, kept_scope.text
    assert kept_scope.json()["context"]["is_stored"] is True


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_marked_revision_that_holds_no_document_at_all_is_computed_and_not_stored(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # A revision marked before the indicators were kept holds no row (migration 0032 takes none
    # up): neither refused nor recomputed as kept, it is read as the current one is, `is_stored`
    # false. The rows the marking kept are deleted, and the real query of ``kept_of_kind`` reads.
    review = project.tree.revision["revision_id"]
    marked_on(stage, clock, project.tree.revision, 1)
    with stage.database.transaction() as session:
        present = kept_of_kind(session, UUID(review), "project", PROJECT)
        assert present.kind_kept
        assert present.document is not None
    # The table refuses the deletion of a marked row (trigger): the owner lifts it for the test.
    with Session(stage.owner) as session, session.begin():
        session.execute(text("ALTER TABLE revision_indicator DISABLE TRIGGER USER"))
        session.execute(
            delete(RevisionIndicator).where(RevisionIndicator.revision_id == UUID(review))
        )
        session.execute(text("ALTER TABLE revision_indicator ENABLE TRIGGER USER"))
    with stage.database.transaction() as session:
        assert kept_of_kind(session, UUID(review), "project", PROJECT) == KeptOfKind(
            None, kind_kept=False
        )
    base = project_path(stage)
    for path in ("estimate-indicators", "remaining-indicators"):
        found = api.get(f"{base}/{path}?revision_id={review}", headers=stage.manager.headers)
        assert found.status_code == 200, found.text
        assert found.json()["context"]["is_stored"] is False
        assert found.json()["context"]["revision_status"] == "marked"


@pytest.mark.requirement("WF-IND-0010-A")
def test_the_day_of_a_date_is_that_of_the_time_zone_of_the_installation(
    api: ContractClient, stage: Scene, project: Priced
) -> None:
    # `as_of` is read on the day of the installation, as the day of a marking is: a marking at
    # 23:30 universal time is already on the next day in Paris. The day before is refused (409), the
    # next day names the revision; in universal time the same marking falls on the first. The
    # time zone is the test's: ``installation_time_zone`` restores universal time when it ends.
    TIME_ZONE.read_from(lambda: "Europe/Paris")
    day = utc_now().date() + ONE_DAY
    at = datetime(day.year, day.month, day.day, 23, 30, tzinfo=UTC)
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        act = Act(stage.manager.user_id, at)
        mark_revision(session, UUID(project.tree.revision["revision_id"]), "Revue", None, act)
    revision = project.tree.revision["revision_id"]
    assert refusal(indicators_answer(api, stage, f"?as_of={day.isoformat()}")) == OFFER
    next_day = day + ONE_DAY
    found = indicators(api, stage, f"?as_of={next_day.isoformat()}")
    assert found["context"]["revision_id"] == revision
    # The same marking, read by an installation in universal time.
    TIME_ZONE.read_from(lambda: "UTC")
    assert indicators(api, stage, f"?as_of={day.isoformat()}")["context"]["revision_id"] == revision


@pytest.mark.requirement("WF-CYC-0090-A")
def test_the_project_that_exited_marking_reads_its_last_marked_revision_with_the_cost_of_the_day(
    api: ContractClient, stage: Scene, worker: Worker, clock: Clock, project: Priced
) -> None:
    # « … ses indicateurs se lisent dans sa dernière révision marquée (WF-IND-0010). » The exit
    # that marks computes and keeps the indicators of the revision in the same transaction; the
    # indicators of the exited project without ``revision_id`` are computed on it with the actual
    # cost of the day, ``is_stored`` false; with its ``revision_id``, the document kept.
    review = project.tree.revision["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    counter = api.get(project_path(stage), headers=stage.manager.headers).json()["lock_version"]
    body = {
        "to_state": "completed",
        "confirmed": True,
        "lock_version": counter,
        "current_revision": {"action": "mark", "version_name": "Clôture", "description": "Fin"},
    }
    asked = api.post(f"{project_path(stage)}/exit", headers=stage.manager.headers, json=body)
    assert asked.status_code == 202, asked.text
    while worker.step():
        pass
    state = api.get(project_path(stage), headers=stage.manager.headers).json()
    assert (state["state"], state["current_revision_id"]) == ("completed", None)
    clock(utc_now().date() + 5 * ONE_DAY)
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-2", None, "250.00", DAY)])
    today = indicators(api, stage)
    assert today["context"]["revision_id"] == review
    assert (today["context"]["is_stored"], today["context"]["revision_status"]) == (False, "marked")
    assert today["actual_cost"] == "750.00"
    stored = indicators(api, stage, named(review))
    assert stored["context"]["is_stored"] is True
    assert stored["actual_cost"] == "500.00"
    assert stored["context"]["computed_at"] != today["context"]["computed_at"]
