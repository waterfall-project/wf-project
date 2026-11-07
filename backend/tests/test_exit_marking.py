# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exit of a project that marks its current revision (US-0980/L2, WF-CYC-0090; #2204).

``exitProject`` with the fate ``mark`` answers 202 and the task ``revision_mark``, which a worker
of the test runs by the handler of the platform: it marks the revision then exits the project, in
the one transaction of the task. Every answer is checked against the contract.
"""

from contextlib import ExitStack
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from projects_support import MANAGING, PROJECTS, Scene, create, person
from projects_support import scene as make_scene
from sqlalchemy import select
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import mark_revision, register_indicators
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
HOURLY_RATE_MISSING = "HOURLY_RATE_MISSING"
MISSING_RATES = {
    "missing_rates": [{"cost_category_id": "01926f3a-7c00-7000-8000-000000000201", "year": 2026}]
}
MARKING: dict[str, Any] = {
    "action": "mark",
    "version_name": "Clôture",
    "description": "La révision en cours, marquée à la sortie du projet.",
}


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    _, bucket = nowhere()
    app = create_app(Services(database, keycloak, administration, queue, bucket))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the markings, by the platform's handler."""
    queue.prepare()
    return Worker(database, queue, {"revision_mark": mark}, "worker", AT_ONCE)


def project_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the project of the stage, as its manager does."""
    response = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


def leave(api: ContractClient, stage: Scene, **body: Any) -> Any:
    """Exit the project of the stage as its manager does, confirmed, marking its revision."""
    sent = {
        "to_state": "abandoned",
        "confirmed": True,
        "current_revision": MARKING,
        "lock_version": project_of(api, stage)["lock_version"],
        **body,
    }
    path = f"{PROJECTS}/{stage.project['project_id']}/exit"
    return api.post(path, headers=stage.manager.headers, json=sent)


def written(database: Database, stage: Scene) -> tuple[str, UUID | None, int, list[str]]:
    """Read the state, the current revision, the counter and the revisions' statuses."""
    with database.transaction() as session:
        project = session.get_one(Project, UUID(stage.project["project_id"]))
        statuses = session.scalars(
            select(Revision.status).where(Revision.project_id == project.id)
        ).all()
        return project.state, project.current_revision_id, project.lock_version, list(statuses)


@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.requirement("WF-SEC-0030-A")
def test_an_exit_that_marks_the_current_revision_is_applied_when_the_task_succeeds(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « La sortie d'un projet qui porte une révision en cours demande de la marquer ou de
    # l'abandonner » : 202 and the task, nothing applied; the worker marks, then exits, under the
    # correlation of the task, the marking and the exit in the journal.
    revision = open_revision(api, stage)
    before = written(database, stage)
    asked = leave(api, stage, reason="Fin de l'offre")
    assert asked.status_code == 202, asked.text
    assert (asked.json()["kind"], asked.json()["status"]) == ("revision_mark", "queued")
    assert written(database, stage) == before
    during = project_of(api, stage)
    running = {each["command"]: each["missing_conditions"] for each in during["available_commands"]}
    assert "no_background_task_running" in running["abandon"]
    assert worker.step()
    project = project_of(api, stage)
    assert (project["state"], project["current_revision_id"]) == ("abandoned", None)
    state, current, _, statuses = written(database, stage)
    assert (state, current, statuses) == ("abandoned", None, ["marked"])
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}"
    marked = api.get(path, headers=stage.manager.headers).json()
    assert (marked["status"], marked["version_name"]) == ("marked", "Clôture")
    transitions = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/state-transitions",
        headers=stage.manager.headers,
    ).json()
    assert (transitions[-1]["to_state"], transitions[-1]["reason"]) == (
        "abandoned",
        "Fin de l'offre",
    )
    with database.transaction() as session:
        entries = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.action.in_(["revision_mark", "project_exit"]))
            .order_by(AuditEntry.id)
        ).all()
        assert [entry.action for entry in entries] == ["revision_mark", "project_exit"]
        assert len({entry.correlation_id for entry in entries}) == 1
        assert entries[1].actor_user_id == stage.manager.user_id


@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.requirement("WF-DAT-0040-A")
def test_an_exit_whose_marking_fails_applies_nothing_and_can_be_asked_again(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « une tâche qui échoue n'applique rien, et le projet garde son état et sa révision en
    # cours » : the computation of the indicators raises, the exit is not applied.
    open_revision(api, stage)
    before = written(database, stage)

    def failing(_session: Session, _revision: UUID) -> None:
        raise UnprocessableError(HOURLY_RATE_MISSING, MISSING_RATES)

    with ExitStack() as registered:
        registered.callback(register_indicators(failing))
        first = leave(api, stage).json()
        assert worker.step()
    task = api.get(f"/api/v1/tasks/{first['task_id']}", headers=stage.manager.headers).json()
    assert (task["status"], task["problem"]["code"]) == ("failed", "HOURLY_RATE_MISSING")
    assert written(database, stage) == before
    again = leave(api, stage)
    assert again.status_code == 202
    assert worker.step()
    assert written(database, stage)[0] == "abandoned"


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-CYC-0090-A")
def test_a_project_written_between_the_request_and_the_worker_does_not_exit(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « le projet a été écrit depuis sa lecture, il ne sort pas » (412): the counter the chief read
    # is judged again by the worker, under the lock of the project; the task fails, nothing is
    # written, the revision stays current and unmarked.
    open_revision(api, stage)
    asked = leave(api, stage)
    assert asked.status_code == 202, asked.text
    renamed = api.patch(
        f"{PROJECTS}/{stage.project['project_id']}",
        headers=stage.manager.headers,
        json={
            "label": "Renommé entre-temps",
            "lock_version": project_of(api, stage)["lock_version"],
        },
    )
    assert renamed.status_code == 200, renamed.text
    before = written(database, stage)
    assert worker.step()
    task = api.get(f"/api/v1/tasks/{asked.json()['task_id']}", headers=stage.manager.headers).json()
    assert (task["status"], task["problem"]["code"]) == ("failed", "STALE_LOCK_VERSION")
    assert written(database, stage) == before
    state, current, _, statuses = before
    assert (state, current is not None, statuses) == ("pricing", True, ["draft"])


@pytest.mark.requirement("WF-REV-0020-A")
def test_an_exit_naming_a_version_a_marked_revision_bears_is_refused_where_it_is_named(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # Like ``markRevision``: 409 ``ALREADY_EXISTS``, the place of the body that holds the name and
    # the revision that bears it; nothing is queued nor written.
    first = open_revision(api, stage)
    with (
        logging_context(correlation_id="marking"),
        database.transaction() as session,
    ):
        mark_revision(session, UUID(first["revision_id"]), "Clôture", None, Act(None, utc_now()))
    open_revision(api, stage)
    before = written(database, stage)
    answer = leave(api, stage)
    body = answer.json()
    assert (answer.status_code, body["code"]) == (409, "ALREADY_EXISTS")
    assert body["fields"] == [
        {
            "pointer": "/current_revision/version_name",
            "code": "ALREADY_EXISTS",
            "params": {"conflicting_object_id": first["revision_id"]},
        }
    ]
    assert written(database, stage) == before
    assert not worker.step()


@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.requirement("WF-ADM-0100-A")
def test_an_exit_marking_the_revision_asks_for_the_permission_to_mark_one(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    chief = person(
        stage.database, realm, *(each for each in MANAGING if each != "revision_mark"), name="Zoé"
    )
    project = create(api, chief, label="Sans marquage")
    path = f"{PROJECTS}/{project['project_id']}"
    assert api.post(f"{path}/revisions", headers=chief.headers, json={}).status_code == 201
    body = {
        "to_state": "abandoned",
        "confirmed": True,
        "lock_version": api.get(path, headers=chief.headers).json()["lock_version"],
        "current_revision": MARKING,
    }
    answer = api.post(f"{path}/exit", headers=chief.headers, json=body)
    assert (answer.status_code, answer.json()["code"]) == (403, "PERMISSION_MISSING")
    assert api.get(path, headers=chief.headers).json()["state"] == "pricing"


@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.requirement("WF-ADM-0100-A")
def test_an_exit_marking_asks_for_the_permission_even_without_a_current_revision(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # The mirror of the abandonment: the fate ``mark`` is judged on the permission to mark a
    # revision whether the project bears one or not.
    chief = person(
        stage.database, realm, *(each for each in MANAGING if each != "revision_mark"), name="Zoé"
    )
    project = create(api, chief, label="Sans révision")
    path = f"{PROJECTS}/{project['project_id']}"
    body = {
        "to_state": "abandoned",
        "confirmed": True,
        "lock_version": api.get(path, headers=chief.headers).json()["lock_version"],
        "current_revision": MARKING,
    }
    answer = api.post(f"{path}/exit", headers=chief.headers, json=body)
    assert (answer.status_code, answer.json()["code"]) == (403, "PERMISSION_MISSING")
    assert api.get(path, headers=chief.headers).json()["state"] == "created"
