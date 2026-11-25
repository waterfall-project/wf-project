# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A storage that does not answer leaves an import to run again, not failed for good (US-3260).

The file of an import is read from the storage by the analysis and by the application. Of that
reading, only the file gone fails the import, its file deleted; the storage out of reach — at the
opening of the stream or in the middle of it — leaves the import as it stands, its file in place,
and the task runs again by its attempts (WF-ARC-0090): the storage back, the import goes through
without a new deposit. The attempts spent during the outage, the import reads ``failed`` and the
task names the component (#4427). A format that refuses or breaks still fails the import. Through
the service and its worker, each answer checked against the contract.
"""

from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from botocore.exceptions import ResponseStreamingError
from fastapi.testclient import TestClient
from imports_trial import (
    AT_ONCE,
    TrialFormat,
    analysed,
    apply,
    import_worker,
    nodes,
    opened,
    read,
    run,
    stand_in,
    stored,
)
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import inspect, update
from support import ContractClient
from task_handlers import deposit, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.storage import Bucket, unavailable
from waterfall.platform.tasks import BackgroundTask, RetriedError
from waterfall.worker.runner import MAX_ATTEMPTS, Worker

if TYPE_CHECKING:
    from collections.abc import Iterator

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import Logs

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.tasks import Task

UNAVAILABLE = "COMPONENT_UNAVAILABLE"
COMPONENT = {"component": "object_storage"}
# The two ways a reading of the storage breaks: the stream does not open, or breaks after a chunk.
OUTAGES = ("opening", "stream")
# What a defect of the reading says: not an outage, but run again as one.
DEFECT = "a defect in the reading of the file"


class Outage(Bucket):
    """The bucket of the tests, which the storage can be made not to answer: ``outage`` says how."""

    def __init__(self, bucket: Bucket) -> None:
        super().__init__(bucket.client, bucket.name)
        self.outage: str | None = None

    def stream(self, key: str) -> Iterator[bytes]:
        """Read as the bucket does, unless the storage is down: at the opening, or after a chunk."""
        if self.outage == "opening":
            raise unavailable()
        if self.outage == "defect":
            raise RuntimeError(DEFECT)
        chunks = super().stream(key)
        return chunks if self.outage is None else self.broken(chunks)

    @staticmethod
    def broken(chunks: Iterator[bytes]) -> Iterator[bytes]:
        """Give the first chunk, then the error of a connection lost in the middle of the body."""
        yield next(chunks)
        raise ResponseStreamingError(error="the connection was lost")


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
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests, for the test."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


@pytest.fixture
def storage(backups_bucket: Bucket) -> Outage:
    """Give the bucket of the test, which the worker reads through and a test can bring down."""
    return Outage(backups_bucket)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, storage: Outage) -> Worker:
    """Give a worker whose storage a test can bring down."""
    return import_worker(database, queue, storage)


def task_of(database: Database, import_id: str) -> BackgroundTask:
    """Read the task of an import."""
    with database.transaction() as session:
        row = session.get_one(ImportReport, UUID(import_id))
        task = session.get_one(BackgroundTask, row.task_id)
        session.expunge(task)
        return task


def whole(database: Database, import_id: str) -> dict[str, object]:
    """Read every column of the row of an import: its report and its expiry with the rest."""
    row = stored(database, import_id)
    return {column.key: getattr(row, column.key) for column in inspect(ImportReport).column_attrs}


def stands(stage: Scene, bucket: Bucket, import_id: str, before: dict[str, object]) -> None:
    """Say an import left as it stood after an attempt: its row whole, its file, its task."""
    assert whole(stage.database, import_id) == before
    assert bucket.size(str(before["object_key"])) is not None
    task = task_of(stage.database, import_id)
    assert (task.status, task.attempts, task.problem) == ("running", 1, None)


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
@pytest.mark.parametrize("outage", OUTAGES)
def test_an_analysis_the_storage_stops_is_run_again_and_goes_through_without_a_new_deposit(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    storage: Outage,
    outage: str,
) -> None:
    # « Aucune donnée partiellement écrite ne subsiste après le rétablissement d'un composant tombé
    # en cours d'écriture. » : the file read at the analysis, the import stays analysing, its file
    # in place, and the task runs again; the storage back, the report is written, the file the same.
    storage.outage = outage
    import_id = opened(api, stage, "Câblage")["import_id"]
    key = stored(stage.database, import_id).object_key
    before = whole(stage.database, import_id)
    assert worker.step()
    stands(stage, storage, import_id, before)
    storage.outage = None
    run(worker)
    found = read(api, stage, import_id)
    assert (found["status"], found["task"]["status"]) == ("analysed", "succeeded")
    assert stored(stage.database, import_id).object_key == key
    assert task_of(stage.database, import_id).attempts == 2


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
@pytest.mark.parametrize("outage", OUTAGES)
def test_an_application_the_storage_stops_is_run_again_and_writes_once_the_storage_is_back(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    storage: Outage,
    outage: str,
) -> None:
    # The same for the application: nothing of the project written while the file cannot be read,
    # the import still applying with its file; the storage back, it is applied, once.
    import_id = analysed(api, stage, worker, "Câblage")["import_id"]
    key = stored(stage.database, import_id).object_key
    storage.outage = outage
    assert apply(api, stage, import_id).status_code == 202
    before = whole(stage.database, import_id)
    assert worker.step()
    stands(stage, storage, import_id, before)
    assert nodes(stage.database) == []
    storage.outage = None
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"
    assert len(nodes(stage.database)) == 1
    assert stored(stage.database, import_id).object_key == key
    assert task_of(stage.database, import_id).attempts == 2


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
@pytest.mark.parametrize("outage", OUTAGES)
def test_an_analysis_the_storage_stops_for_every_attempt_fails_the_import_naming_the_component(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    storage: Outage,
    outage: str,
) -> None:
    # [US-3260] The attempts of the task spent during the outage: the import reads ``failed`` and
    # its task names the object storage.
    storage.outage = outage
    import_id = opened(api, stage, "Câblage")["import_id"]
    run(worker)
    found = read(api, stage, import_id)
    assert found["status"] == "failed"
    assert found["task"]["status"] == "failed"
    assert found["task"]["problem"]["code"] == UNAVAILABLE
    assert found["task"]["problem"]["params"] == COMPONENT
    assert task_of(stage.database, import_id).attempts == MAX_ATTEMPTS


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
@pytest.mark.parametrize("outage", OUTAGES)
def test_an_application_the_storage_stops_for_every_attempt_fails_the_import_naming_the_component(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    storage: Outage,
    outage: str,
) -> None:
    # [US-3260] Likewise at the application: failed, nothing of the project written.
    import_id = analysed(api, stage, worker, "Câblage")["import_id"]
    storage.outage = outage
    assert apply(api, stage, import_id).status_code == 202
    run(worker)
    found = read(api, stage, import_id)
    assert found["status"] == "failed"
    assert found["task"]["problem"]["code"] == UNAVAILABLE
    assert found["task"]["problem"]["params"] == COMPONENT
    assert task_of(stage.database, import_id).attempts == MAX_ATTEMPTS
    assert nodes(stage.database) == []


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
def test_a_file_gone_from_the_storage_still_fails_the_import_at_once(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    # [US-3260] The one error of the reading that fails the import: the object is not there, at the
    # analysis and at the application, at the first attempt.
    first = opened(api, stage, "Câblage")["import_id"]
    backups_bucket.remove(stored(stage.database, first).object_key)
    run(worker)
    assert read(api, stage, first)["status"] == "failed"
    assert task_of(stage.database, first).attempts == 1
    second = analysed(api, stage, worker, "Essais")["import_id"]
    backups_bucket.remove(stored(stage.database, second).object_key)
    assert apply(api, stage, second).status_code == 202
    run(worker)
    assert read(api, stage, second)["status"] == "failed"
    assert task_of(stage.database, second).attempts == 1
    assert nodes(stage.database) == []


@pytest.mark.requirement("WF-EXP-0040-A")
def test_a_format_that_breaks_still_fails_the_import_at_once_its_file_deleted(
    api: ContractClient, stage: Scene, trial: TrialFormat, worker: Worker, backups_bucket: Bucket
) -> None:
    # [US-3260] An error of the format is not one of the storage, at the analysis or at the
    # preparation of the application: the import fails at the first attempt, its file deleted.
    trial.analysis = "break"
    first = opened(api, stage, "Câblage")["import_id"]
    run(worker)
    assert read(api, stage, first)["status"] == "failed"
    assert task_of(stage.database, first).attempts == 1
    assert backups_bucket.size(stored(stage.database, first).object_key) is None
    trial.analysis = None
    second = analysed(api, stage, worker, "Essais")["import_id"]
    trial.preparation = "break"
    assert apply(api, stage, second).status_code == 202
    run(worker)
    assert read(api, stage, second)["status"] == "failed"
    assert task_of(stage.database, second).attempts == 1
    assert backups_bucket.size(stored(stage.database, second).object_key) is None


@pytest.mark.requirement("WF-EXP-0040-A")
@pytest.mark.usefixtures("trial")
def test_a_defect_of_the_reading_is_run_again_with_its_trace_in_the_logs(
    api: ContractClient, stage: Scene, worker: Worker, storage: Outage, logs: Logs
) -> None:
    # [US-3260] A bug of the stream is not told apart from an outage: the task runs again, but the
    # retry leaves a line with the trace of the error it came from, not only the 503 it ends in.
    storage.outage = "defect"
    import_id = opened(api, stage, "Câblage")["import_id"]
    assert worker.step()
    (retried,) = logs.named("task.retried")
    assert retried["attempt"] == 1
    assert retried["code"] == UNAVAILABLE
    assert f"RuntimeError: {DEFECT}" in retried["exception"]
    assert task_of(stage.database, import_id).status == "running"


def stall(session: Session, running: Task) -> None:
    """Write something, then stall as a handler does on a component that does not answer."""
    mark = update(BackgroundTask).where(BackgroundTask.id == running.task_id)
    session.execute(mark.values(progress=50))

    def trace(written: Session) -> None:
        written.execute(mark.values(progress=75))

    raise RetriedError(unavailable(), trace)


@pytest.mark.requirement("WF-EXP-0040-A")
def test_a_task_that_stalls_stays_pending_until_its_last_attempt_and_then_fails_with_its_cause(
    database: Database, queue: TaskQueue
) -> None:
    # [US-3260] The general mechanism, at the worker: a handler that raises ``RetriedError`` has its
    # work undone and writes nothing, the entry stays to be claimed again; on the last attempt, the
    # trace is written and the task fails with the code and parameters of the refusal it carries.
    queue.prepare()
    taker = Worker(database, queue, {"identity_sync": stall}, "worker", AT_ONCE)
    task_id = deposit(database, queue)
    for attempt in range(1, MAX_ATTEMPTS):
        assert taker.step()
        waiting = task(database, task_id)
        assert (waiting.status, waiting.attempts, waiting.progress) == ("running", attempt, 0)
        assert (waiting.problem, waiting.finished_at) == (None, None)
    assert taker.step()
    ended = task(database, task_id)
    assert (ended.status, ended.attempts, ended.progress) == ("failed", MAX_ATTEMPTS, 75)
    assert ended.problem is not None
    assert ended.problem["code"] == UNAVAILABLE
    assert ended.problem["params"] == COMPONENT
