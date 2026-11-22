# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A worker stopped during a marking, and during the application of an import (WF-ARC-0090).

The worker is a process of its own (``worker_platform_process``), on the PostgreSQL, the Redis and
the object storage of the tests, running the handler of the platform: it is stopped — ``SIGTERM``
as the platform stops it, ``SIGKILL`` as a failure ends it — once the work is done and not
committed. The base is as it was, the task is still the one the stopped attempt left running, and
a worker started again takes it up and ends it.
"""

import os
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from imports_trial import TrialFormat, analysed, apply, import_worker, nodes, read, stand_in, stored
from process_support import PATIENCE, started, wait_for
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.tables import Project
from waterfall.platform.audit import AuditEntry
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
    from collections.abc import Callable

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

PROCESS = Path(__file__).resolve().parent / "worker_platform_process.py"
STOPS = pytest.mark.parametrize("stop", [signal.SIGTERM, signal.SIGKILL], ids=["stopped", "killed"])


@pytest.fixture
def services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API on the database, the queue and the bucket of the test."""
    return Services(
        database, keycloak, KeycloakAdmin(keycloak, realm_settings), queue, backups_bucket
    )


@pytest.fixture
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests, for the test."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


@dataclass(frozen=True)
class Process:
    """What a worker of a process needs: the queue and the bucket it works on, its environment."""

    queue: TaskQueue
    bucket: Bucket
    environment: dict[str, str]
    folder: Path

    def stopped_then_taken_up(
        self,
        kind: str,
        stop: signal.Signals,
        *,
        unchanged: Callable[[], None],
        ended: Callable[[], bool],
    ) -> None:
        """Stop a worker once the work of a task of ``kind`` is done, then start another.

        ``unchanged`` holds the database as it was while the first is gone, and ``ended`` says the
        second has ended the task.
        """
        stalled = self.folder / "stalled"
        worker = [sys.executable, str(PROCESS), self.queue.stream]
        with started([*worker, "first", kind, "stall", str(stalled)], self.environment) as first:
            wait_for(stalled.exists)
            first.send_signal(stop)
            assert first.wait(timeout=PATIENCE) == (0 if stop is signal.SIGTERM else -stop)
        unchanged()
        with started([*worker, "second", kind, "finish", str(stalled)], self.environment):
            wait_for(ended)


@pytest.fixture
def process(
    service_environment: dict[str, str], queue: TaskQueue, backups_bucket: Bucket, tmp_path: Path
) -> Process:
    """Give the processes of workers the database and the Redis of the tests, and their storage."""
    environment = {
        **service_environment,
        "WATERFALL_TEST_STORAGE_URL": os.environ["WATERFALL_TEST_STORAGE_URL"],
        "WATERFALL_TEST_BUCKET": backups_bucket.name,
    }
    return Process(queue, backups_bucket, environment, tmp_path)


def task_of(database: Database, task_id: UUID) -> tuple[str, int]:
    """Read the status and the attempts of a task."""
    with database.transaction() as session:
        row = session.get_one(BackgroundTask, task_id)
        return row.status, row.attempts


@pytest.mark.requirement("WF-ARC-0090-A")
@STOPS
def test_a_worker_stopped_during_a_marking_leaves_the_base_unchanged_and_the_marking_is_taken_up(
    api: ContractClient,
    stage: Scene,
    database: Database,
    process: Process,
    stop: signal.Signals,
) -> None:
    # « L'arrêt du worker pendant une tâche laisse la base inchangée, et la tâche est reprise après
    # redémarrage. » (constaté sur un marquage) The worker has marked, its transaction is open,
    # and it is stopped: the revision is still current and open, no marking is inscribed, the task
    # runs; the worker started again marks the revision, under the same task, at its second attempt.
    manager, project_id = stage.manager.headers, stage.project["project_id"]
    path = f"{PROJECTS}/{project_id}/revisions"
    revision = api.post(path, headers=manager, json={}).json()
    sent = {"version_name": "v1.0", "lock_version": revision["lock_version"]}
    asked = api.post(f"{path}/{revision['revision_id']}/mark", headers=manager, json=sent)
    assert asked.status_code == 202, asked.text
    task_id = UUID(asked.json()["task_id"])

    def marked() -> int:
        with database.transaction() as session:
            return (
                session.scalar(select(func.count()).where(AuditEntry.action == "revision_mark"))
                or 0
            )

    def current() -> UUID | None:
        with database.transaction() as session:
            return session.scalar(select(Project.current_revision_id))

    def unchanged() -> None:
        found = api.get(f"{path}/{revision['revision_id']}", headers=manager).json()
        assert (found["status"], found["version_name"]) == ("draft", None)
        assert (marked(), current()) == (0, UUID(revision["revision_id"]))
        assert task_of(database, task_id) == ("running", 1)

    def ended() -> bool:
        return task_of(database, task_id) == ("succeeded", 2)

    process.stopped_then_taken_up("revision_mark", stop, unchanged=unchanged, ended=ended)
    found = api.get(f"{path}/{revision['revision_id']}", headers=manager).json()
    assert (found["status"], found["version_name"]) == ("marked", "v1.0")
    assert (marked(), current()) == (1, None)
    again = api.get(f"/api/v1/tasks/{task_id}", headers=manager).json()
    assert again["status"] == "succeeded"


@pytest.mark.requirement("WF-ARC-0090-A")
@STOPS
@pytest.mark.usefixtures("trial")
def test_a_worker_stopped_during_the_application_of_an_import_leaves_the_project_as_it_was(
    api: ContractClient,
    stage: Scene,
    database: Database,
    process: Process,
    stop: signal.Signals,
) -> None:
    # « L'arrêt du worker pendant une tâche laisse la base inchangée, et la tâche est reprise après
    # redémarrage. » (constaté sur l'application d'un import) The worker has written the tasks of
    # the file, its transaction is open, and it is stopped: the project holds none of them, the
    # import is still being applied, its file still in the storage; the worker started again
    # applies it, once, at its second attempt.
    found = analysed(api, stage, import_worker(database, process.queue, process.bucket))
    import_id = found["import_id"]
    key = stored(database, import_id).object_key
    assert apply(api, stage, import_id).status_code == 202
    before = nodes(database)
    task_id = stored(database, import_id).task_id
    assert task_id is not None

    def unchanged() -> None:
        assert nodes(database) == before
        assert (stored(database, import_id).status, process.bucket.size(key) is not None) == (
            "applying",
            True,
        )
        assert task_of(database, task_id) == ("running", 1)

    def ended() -> bool:
        return task_of(database, task_id) == ("succeeded", 2)

    process.stopped_then_taken_up("import_apply", stop, unchanged=unchanged, ended=ended)
    assert read(api, stage, import_id)["status"] == "applied"
    assert len(nodes(database)) == len(before) + 2
    assert process.bucket.size(key) is None
