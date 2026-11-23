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
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.tables import ImportReport
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.storage import Bucket, unavailable
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.runner import MAX_ATTEMPTS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker

UNAVAILABLE = "COMPONENT_UNAVAILABLE"
COMPONENT = {"component": "object_storage"}
# The two ways a reading of the storage breaks: the stream does not open, or breaks after a chunk.
OUTAGES = ("opening", "stream")


class Outage(Bucket):
    """The bucket of the tests, which the storage can be made not to answer: ``outage`` says how."""

    def __init__(self, bucket: Bucket) -> None:
        super().__init__(bucket.client, bucket.name)
        self.outage: str | None = None

    def stream(self, key: str) -> Iterator[bytes]:
        """Read as the bucket does, unless the storage is down: at the opening, or after a chunk."""
        if self.outage == "opening":
            raise unavailable()
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


def stands(stage: Scene, bucket: Bucket, import_id: str, status: str, key: str) -> None:
    """Say an import left as it stands after an attempt: its file in place, its task running."""
    row = stored(stage.database, import_id)
    assert (row.status, row.object_key) == (status, key)
    assert bucket.size(key) is not None
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
    assert worker.step()
    stands(stage, storage, import_id, "analysing", key)
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
    assert worker.step()
    stands(stage, storage, import_id, "applying", key)
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
