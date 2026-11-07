# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the worker of the marking judges under its locks (US-0970, US-0980/L2).

The instant of a marking is taken under the locks of the revision and of the project
(WF-REV-0040): a designation validated while a marking waits for the project is older than the
marking, which the reference is judged correctable against. And the chief who asked for an exit
that marks, demoted before the worker runs, fails the task and undoes the marking with it
(WF-PRJ-0060, WF-CYC-0090).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from support import ContractClient, nowhere, wait_for_a_lock

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.interface import (
    ContributorEntry,
    ContributorsToWrite,
    Viewer,
    set_contributors,
)
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import run_marking
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

EARLY = datetime(2020, 1, 1, tzinfo=UTC)
TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


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
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the markings, by the platform's handler."""
    queue.prepare()
    return Worker(database, queue, {"revision_mark": mark}, "worker", AT_ONCE)


@pytest.mark.requirement("WF-REV-0040-A")
def test_a_marking_that_waited_for_the_project_is_dated_after_the_write_it_waited_for(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    project_id = UUID(stage.project["project_id"])
    opened = api.post(f"{PROJECTS}/{project_id}/revisions", headers=stage.manager.headers, json={})
    assert opened.status_code == 201, opened.text
    revision_id = UUID(opened.json()["revision_id"])
    payload = {
        "project_id": str(project_id),
        "revision_id": str(revision_id),
        "version_name": "v1.0",
        "description": None,
    }

    def run() -> None:
        with logging_context(correlation_id="marking-instant"), database.transaction() as session:
            # The task began long ago: its instant is the run's, taken before the locks.
            run_marking(session, payload, Act(stage.manager.user_id, EARLY))

    with ThreadPoolExecutor(1) as others, Session(database.engine) as holding:
        holding.execute(select(Project.id).where(Project.id == project_id).with_for_update())
        marking = others.submit(run)
        wait_for_a_lock(database)
        released = utc_now()
        holding.commit()
        marking.result(timeout=10)
    with database.transaction() as session:
        marked_at = session.scalar(select(Revision.marked_at).where(Revision.id == revision_id))
    assert marked_at is not None
    assert marked_at >= released


def journal(database: Database) -> tuple[Any, ...]:
    """Read what the exit that marks writes: the project, its revisions, and the journal."""
    with database.transaction() as session:
        project = session.execute(
            select(Project.state, Project.current_revision_id, Project.lock_version)
        ).one()
        statuses = sorted(session.scalars(select(Revision.status)))
        actions = session.scalar(
            select(func.count())
            .select_from(AuditEntry)
            .where(AuditEntry.action.in_(["revision_mark", "project_exit"]))
        )
    return (*project, statuses, actions)


@pytest.mark.requirement("WF-PRJ-0060-A")
@pytest.mark.requirement("WF-CYC-0090-A")
def test_a_chief_demoted_before_the_worker_runs_fails_the_exit_that_marks_and_writes_nothing(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    project_path = f"{PROJECTS}/{stage.project['project_id']}"
    headers = stage.manager.headers
    assert api.post(f"{project_path}/revisions", headers=headers, json={}).status_code == 201
    counter = api.get(f"{project_path}/contributors", headers=headers).json()["lock_version"]
    asked = api.post(
        f"{project_path}/exit",
        headers=headers,
        json={
            "to_state": "abandoned",
            "confirmed": True,
            "lock_version": api.get(project_path, headers=headers).json()["lock_version"],
            "current_revision": {"action": "mark", "version_name": "Clôture"},
        },
    )
    assert asked.status_code == 202, asked.text
    # The chief is demoted, the participant taking the place, between the request and the worker.
    demotion = ContributorsToWrite(
        (
            ContributorEntry(stage.participant.user_id, "project_manager"),
            ContributorEntry(stage.manager.user_id, "contributor"),
        ),
        counter,
    )
    with logging_context(correlation_id="demotion"), database.transaction() as session:
        set_contributors(
            session,
            UUID(stage.project["project_id"]),
            demotion,
            Viewer(stage.manager.user_id, ()),
        )
    before = journal(database)
    assert worker.step()
    task = api.get(f"{TASKS}/{asked.json()['task_id']}", headers=headers).json()
    assert task["status"] == "failed"
    assert task["problem"]["code"] == "NOT_PROJECT_MANAGER"
    assert journal(database) == before
    assert before[0] == "pricing"
    assert before[3] == ["draft"]
