# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the accounts asked for through the API, and its report (US-0370).

A reading is deposited for the worker and the request answers at once (WF-ARC-0090); its report is
read apart. Keycloak is the realm of test, which the reading never reaches here: what the worker
reads of Keycloak is tried against the platform (``test_keycloak_identity_sync.py``). What the
reading does once committed — the removal of the orphans — is tried here against PostgreSQL: it
runs once its transaction is committed, never if what registered it is rolled back.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import update
from sqlalchemy.orm import Session
from support import ContractClient, bearer, nowhere
from task_handlers import deposit, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.interface import SyncReport, record_report
from waterfall.platform.database import Database
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.queue import TaskQueue
from waterfall.platform.settings import ServiceSettings
from waterfall.platform.tasks import BackgroundTask, Task
from waterfall.worker.identity_sync import after_commit
from waterfall.worker.runner import Worker

SYNCS = "/api/v1/identity-syncs"
LATEST = f"{SYNCS}/latest"
NIGHT = datetime(2026, 10, 12, 2, 0, tzinfo=UTC)

type Person = Callable[..., tuple[UUID, dict[str, str]]]


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the API that deposits in the queue of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    _, bucket = nowhere()
    app = create_app(Services(database, keycloak, administration, queue, bucket))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts, each holding a role of the permissions given, and its header."""

    def make(*permissions: str) -> tuple[UUID, dict[str, str]]:
        subject = f"subject-{uuid4()}"
        held = role(database, f"Rôle {uuid4().hex[:8]}", permissions=permissions)
        user_id = account(database, "Martin", uuid4().hex[:8], roles=(held,), idp_subject=subject)
        return user_id, bearer(realm.token(subject, KEY))

    return make


def reported(database: Database, queue: TaskQueue, finished_at: datetime, created: int) -> UUID:
    """Keep the report of a reading the platform scheduled, ended at ``finished_at``."""
    task_id = deposit(database, queue)
    with database.transaction() as session:
        report = SyncReport(
            task_id, finished_at, created, 1, 0, [("d@x.org", "LAST_ADMINISTRATOR")], ["o@x.org"]
        )
        record_report(session, report)
    return task_id


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_reading_asked_for_is_deposited_for_the_worker_and_answered_at_once(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # « Aucun de ces traitements n'est joignable par un endpoint qui répondrait après l'avoir
    # exécuté. » : for the reading of the accounts, the answer is the task, queued, deposited.
    user_id, headers = person("users.write")
    asked = api.post(SYNCS, headers=headers)
    assert asked.status_code == 202, asked.text
    ref = asked.json()
    assert (ref["kind"], ref["status"], ref["progress"], ref["result_url"]) == (
        "identity_sync",
        "queued",
        0,
        None,
    )
    task_id = UUID(ref["task_id"])
    deposited = task(database, task_id)
    assert (deposited.status, deposited.requested_by) == ("queued", user_id)
    assert task_id in queue.waiting()
    # Once it succeeded, the task says where its report is read.
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id == task_id)
            .values(status="succeeded", progress=100, finished_at=NIGHT)
        )
    done = api.get(f"/api/v1/tasks/{task_id}", headers=headers).json()
    assert (done["status"], done["result_url"]) == ("succeeded", LATEST)


def test_a_reading_is_asked_for_under_the_permission_to_change_the_accounts(
    api: ContractClient, person: Person
) -> None:
    _, headers = person("users.read")
    refused = api.post(SYNCS, headers=headers)
    assert (refused.status_code, refused.json()["params"]) == (
        403,
        {"missing_permission": "users.write"},
    )


def test_the_report_read_is_that_of_the_latest_reading_ended(
    api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    _, headers = person("users.read")
    assert api.get(LATEST, headers=headers).status_code == 404
    reported(database, queue, NIGHT - timedelta(days=1), 3)
    latest = reported(database, queue, NIGHT, 2)
    response = api.get(LATEST, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "task_id": str(latest),
        "finished_at": "2026-10-12T02:00:00Z",
        "created": 2,
        "updated": 1,
        "deactivated": 0,
        "skipped": [{"email": "d@x.org", "code": "LAST_ADMINISTRATOR"}],
        "removed": ["o@x.org"],
    }
    # The accounts not consulted, the report does not exist for the caller.
    _, outside = person("users.write")
    assert api.get(LATEST, headers=outside).status_code == 404


class Undone(Exception):
    """What undoes the savepoint of a test."""


@pytest.mark.requirement("WF-ARC-0090-A")
def test_what_waits_for_the_commit_is_dropped_with_the_savepoint_rolled_back(
    database: Database, queue: TaskQueue
) -> None:
    # « L'arrêt du worker pendant une tâche laisse la base inchangée » : a reading that fails
    # leaves the realm as it was too — what it registered in the savepoint of its run never runs,
    # though the worker commits the end of the task after.
    ran: list[str] = []
    with database.transaction() as session:
        try:
            with session.begin_nested():
                after_commit(session, lambda: ran.append("savepoint"))
                with session.begin_nested():
                    after_commit(session, lambda: ran.append("within"))
                raise Undone
        except Undone:
            pass
        after_commit(session, lambda: ran.append("root"))
    assert ran == ["root"]

    def failing(session: Session, _task: Task) -> None:
        after_commit(session, lambda: ran.append("task"))
        raise Undone

    task_id = deposit(database, queue)
    assert Worker(database, queue, {"identity_sync": failing}, "worker").run_task(task_id)
    assert task(database, task_id).status == "failed"
    assert ran == ["root"]


@pytest.mark.requirement("WF-ARC-0090-A")
def test_what_waits_for_the_commit_runs_once_after_it_and_never_after_a_rollback(
    database: Database,
) -> None:
    ran: list[str] = []
    with database.transaction() as session:
        with session.begin_nested():
            after_commit(session, lambda: ran.append("released"))
        assert ran == []
        try:
            with session.begin_nested():
                raise Undone
        except Undone:
            pass
    assert ran == ["released"]
    with pytest.raises(Undone), database.transaction() as session:
        after_commit(session, lambda: ran.append("root"))
        with session.begin_nested():
            after_commit(session, lambda: ran.append("savepoint"))
        raise Undone
    assert ran == ["released"]
