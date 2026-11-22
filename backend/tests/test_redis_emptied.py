# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Redis emptied whole: the platform goes on, and what it queued is run (WF-ARC-0040, WF-ARC-0090).

The API and its worker run on a Redis a test may empty (``FLUSHDB``, ``emptied_queue``), on the
PostgreSQL and the object storage of the tests: a platform that carries a project and its
revision, a marking and an import asked for and not yet taken. What the browser holds of its
session is the front's, tried against the service (``frontend/e2e/service``).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast
from uuid import UUID

import pytest
from degraded_platform import row_counts
from fastapi.testclient import TestClient
from imports_trial import TrialFormat, import_worker, opened, read, run, stand_in
from projects_support import MANAGING, PROJECTS, Scene, create, person
from projects_support import scene as make_scene
from realm import KEY
from sqlalchemy import select
from support import ContractClient, bearer, emptied

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.tables import UserAccount
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.maintenance import Maintenance

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from projects_support import Person
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

TASKS = "/api/v1/tasks"
HEALTH = "/api/v1/health"


@pytest.fixture
def services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    emptied_queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API, on a queue whose Redis the test empties."""
    return Services(
        database,
        keycloak,
        KeycloakAdmin(keycloak, realm_settings),
        emptied_queue,
        backups_bucket,
        Maintenance.of(database, emptied_queue),
    )


@pytest.fixture
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Serve the API on a queue whose Redis the test empties."""
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@dataclass(frozen=True)
class Signing:
    """An account that signs in: its session, and a new token of the realm for the same account."""

    session: Person
    database: Database
    realm: TestRealm

    def again(self) -> dict[str, str]:
        """Sign in again: the header of a token the realm gives the account now."""
        with self.database.transaction() as session:
            subject = session.scalars(
                select(UserAccount.idp_subject).where(UserAccount.id == self.session.user_id)
            ).one()
        return bearer(self.realm.token(str(subject), KEY))


@pytest.fixture
def signing(stage: Scene, realm: TestRealm) -> Signing:
    """Give an account of the platform that signs in, as the browser's session does again."""
    return Signing(
        person(stage.database, realm, *MANAGING, name="Reconnecté"), stage.database, realm
    )


@pytest.fixture
def worker(database: Database, emptied_queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the emptied queue: the imports, by the platform's handlers, and markings."""
    return import_worker(database, emptied_queue, backups_bucket)


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests, for the test."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


class Counted(Protocol):
    """What a test asks of the client of Redis of a queue it counts: ``DBSIZE``."""

    def dbsize(self) -> int: ...


def held_in_redis(queue: TaskQueue) -> int:
    """Count the keys the database of Redis of a queue holds."""
    return cast("Counted", queue.client).dbsize()


def ask_marking(api: ContractClient, stage: Scene, name: str, project_id: str | None = None) -> str:
    """Open the current revision of a project, the stage's by default, ask for its marking."""
    path = f"{PROJECTS}/{project_id or stage.project['project_id']}/revisions"
    revision = api.post(path, headers=stage.manager.headers, json={})
    assert revision.status_code == 201, revision.text
    sent = {"version_name": name, "lock_version": revision.json()["lock_version"]}
    asked = api.post(
        f"{path}/{revision.json()['revision_id']}/mark", headers=stage.manager.headers, json=sent
    )
    assert asked.status_code == 202, asked.text
    return asked.json()["task_id"]


def task_status(api: ContractClient, stage: Scene, task_id: str) -> str:
    """Read the status of a task the manager asked for, as the user follows it."""
    found = api.get(f"{TASKS}/{task_id}", headers=stage.manager.headers)
    assert found.status_code == 200, found.text
    return found.json()["status"]


def revisions_of(api: ContractClient, stage: Scene) -> list[tuple[str, str]]:
    """Read the revisions of the project of the stage, as the manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    found = api.get(path, headers=stage.manager.headers)
    assert found.status_code == 200, found.text
    return sorted((each["revision_id"], each["status"]) for each in found.json()["items"])


def current_draft(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the revision of the project of the stage that is still open."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    items = api.get(path, headers=stage.manager.headers).json()["items"]
    return next(each for each in items if each["status"] == "draft")


@pytest.mark.requirement("WF-ARC-0040-A")
def test_after_redis_is_emptied_the_platform_goes_on_users_sign_in_and_no_project_data_is_lost(
    api: ContractClient, stage: Scene, worker: Worker, emptied_queue: TaskQueue, signing: Signing
) -> None:
    # « Après vidage de Redis, la plateforme fonctionne, les utilisateurs se reconnectent et
    # aucune donnée de projet ne manque. » A project, a revision marked and another open; Redis
    # emptied whole: the probe answers, the sessions held go on, an account signs in again — a new
    # token of the realm — and every row of the database is as it was. What Redis held of the
    # platform, the queue, is made again by the worker: a marking asked for now is run.
    manager = stage.manager.headers
    marked = ask_marking(api, stage, "v1.0")
    assert worker.step()
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    assert api.post(path, headers=manager, json={}).status_code == 201

    def held() -> tuple[dict[str, int], list[tuple[str, str]], Any]:
        return (
            row_counts(stage.owner),
            revisions_of(api, stage),
            api.get(PROJECTS, headers=manager).json(),
        )

    before = held()
    emptied(emptied_queue)
    assert held_in_redis(emptied_queue) == 0
    assert api.get(HEALTH).json() == {"status": "ok"}
    assert api.get("/api/v1/me", headers=manager).status_code == 200
    assert api.get("/api/v1/me", headers=signing.again()).status_code == 200
    assert held() == before
    assert task_status(api, stage, marked) == "succeeded"
    current = current_draft(api, stage)
    sent = {"version_name": "v2.0", "lock_version": current["lock_version"]}
    asked = api.post(f"{path}/{current['revision_id']}/mark", headers=manager, json=sent)
    assert asked.status_code == 202, asked.text
    # The first step makes the stream and its group again; the task is then run.
    worker.step()
    run(worker)
    assert task_status(api, stage, asked.json()["task_id"]) == "succeeded"


@pytest.mark.requirement("WF-ARC-0040-A")
@pytest.mark.usefixtures("trial")
def test_a_task_asked_before_redis_is_emptied_and_not_taken_is_run_once_it_is_back(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    emptied_queue: TaskQueue,
) -> None:
    # « Une tâche demandée avant le vidage de Redis et non encore prise est exécutée après le
    # rétablissement. » A marking and the analysis of an import asked for, no worker taking them,
    # their entries in the queue; Redis emptied, the entries are gone and the tasks are queued in
    # the table. The worker, which makes its stream again and deposits the queued tasks from the
    # table, runs both, and the user reads the marking succeeded and the import analysed.
    other = create(api, stage.manager, label="Autre projet")["project_id"]
    task_id = ask_marking(api, stage, "v1.0", other)
    found: dict[str, Any] = opened(api, stage, "Câblage", "Essais")
    import_id = found["import_id"]
    assert emptied_queue.waiting() == {UUID(task_id), UUID(found["task"]["task_id"])}
    emptied(emptied_queue)
    assert held_in_redis(emptied_queue) == 0
    assert (task_status(api, stage, task_id), read(api, stage, import_id)["status"]) == (
        "queued",
        "analysing",
    )
    # A step makes the stream and its group again and deposits the queued tasks, then each runs.
    worker.step()
    run(worker)
    assert task_status(api, stage, task_id) == "succeeded"
    assert read(api, stage, import_id)["status"] == "analysed"
    assert emptied_queue.waiting() == set()
