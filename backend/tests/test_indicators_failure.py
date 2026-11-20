# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A computation of the indicators that raises fails the marking, nothing written (#2180).

Laid by US-1660/L1, the socle of EP-10, so that no two stories create the same file; US-1670/L1
writes its tests here (EP-10, "Les tests du back"). An entry of ``register_indicators`` that raises,
after the one of the indicators, which has then written its documents: the task ``revision_mark``
fails with the code of the exception, or that of an internal error for one that bears none; the
revision stays current, nothing of the marking is written — its documents, its status, its line of
the journal —, and a new ``markRevision``, the entry withdrawn, marks it and keeps them.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from nodes_support import opened
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.core.revisions.interface import register_indicators
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import AuditEntry
from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act
    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)


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


class DataFaultError(ValueError):
    """A fault of the data a computation meets, which bears no code."""


# What an entry raises, and the code the task fails with: a refusal its own, a fault an internal
# error's.
FAILURES = [
    pytest.param((ConflictError(STATE_FORBIDS_OPERATION), STATE_FORBIDS_OPERATION), id="refusal"),
    pytest.param((DataFaultError("a line without its task"), "INTERNAL_ERROR"), id="fault"),
]


@pytest.fixture
def raising(request: pytest.FixtureRequest) -> Iterator[str]:
    """Register, after the indicators, an entry that raises the exception given; give its code."""
    failure, code = request.param

    def compute(session: Session, revision_id: UUID, act: Act) -> None:
        del session, revision_id, act
        raise failure

    withdraw = register_indicators(compute)
    try:
        yield code
    finally:
        withdraw()


def asked(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> str:
    """Ask the marking of a revision as its manager does; give its task."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}/mark"
    sent = {"version_name": "Offre v1.0", "lock_version": revision["lock_version"]}
    answer = api.post(path, headers=stage.manager.headers, json=sent)
    assert answer.status_code == 202, answer.text
    return answer.json()["task_id"]


def written(database: Database, revision_id: UUID) -> tuple[str, int, int]:
    """Read what a marking writes: the status of the revision, its documents, its journal."""
    with database.transaction() as session:
        status = session.scalar(select(Revision.status).where(Revision.id == revision_id))
        documents = session.scalar(
            select(func.count())
            .select_from(RevisionIndicator)
            .where(RevisionIndicator.revision_id == revision_id)
        )
        journal = session.scalar(
            select(func.count()).select_from(AuditEntry).where(AuditEntry.action == "revision_mark")
        )
    assert status is not None
    return status, documents or 0, journal or 0


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.parametrize("raising", FAILURES, indirect=True)
def test_a_computation_of_the_indicators_that_raises_fails_the_marking_and_writes_nothing(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, raising: str
) -> None:
    # « Le marquage d'une révision échoue entièrement si le calcul de ses indicateurs échoue. »
    # The indicators have written their documents when the entry after them raises: the task fails
    # with its code, the revision stays current, and nothing of the marking is left.
    revision = opened(api, stage)
    revision_id = UUID(revision["revision_id"])
    task_id = asked(api, stage, revision)
    assert worker.step()
    task = api.get(f"{TASKS}/{task_id}", headers=stage.manager.headers).json()
    assert (task["status"], task["problem"]["code"]) == ("failed", raising)
    assert written(database, revision_id) == ("draft", 0, 0)


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_marking_failed_by_its_indicators_is_asked_again_and_keeps_them(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # The revision left current, a new ``markRevision`` marks it once the computation no longer
    # raises: no indicator was left out in place of the one that failed.
    revision = opened(api, stage)
    revision_id = UUID(revision["revision_id"])

    def compute(session: Session, revision_id: UUID, act: Act) -> None:
        del session, revision_id, act
        raise DataFaultError

    withdraw = register_indicators(compute)
    try:
        failed = asked(api, stage, revision)
        assert worker.step()
    finally:
        withdraw()
    first = api.get(f"{TASKS}/{failed}", headers=stage.manager.headers).json()
    assert first["status"] == "failed"
    again = asked(api, stage, revision)
    assert worker.step()
    task = api.get(f"{TASKS}/{again}", headers=stage.manager.headers).json()
    assert task["status"] == "succeeded", task
    status, documents, journal = written(database, revision_id)
    # The estimate of the project and of the lines out of any subproject, and the remaining; and
    # what the portfolio keeps of an offer, its workload, its costs and its curves (US-2680/L2).
    assert (status, documents, journal) == ("marked", 6, 1)
