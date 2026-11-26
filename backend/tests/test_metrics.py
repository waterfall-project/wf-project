# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The metrics of the API, and its readiness: what they count, what they read, what they probe.

The application runs on the database, the Redis and the storage of the tests, and on the realm of
test, which serves its keys: every component answers. A component stopped is one the services reach
at an address where nothing listens; the realm of test is stopped for real, between two collections.
"""

import dataclasses
import threading
import time
from concurrent.futures import wait
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from backup_support import Corrupting
from fastapi.testclient import TestClient
from metrics_reading import Samples, samples, value
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool
from support import PLATFORM_SECRETS, ContractClient, raw_account
from witness_support import example

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.backups.tables import Backup
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import (
    POOL_OVERFLOW,
    Database,
    create_database_engine,
    engine_url,
    utc_now,
)
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.maintenance import Maintenance, Restoring
from waterfall.platform.metrics import (
    COMPONENT_UP,
    COMPONENT_VERSION,
    LAST_RUN_SUCCESS,
    LAST_RUN_TIMESTAMP,
    OLDEST_QUEUED_TASK_AGE,
    PROBE_SECONDS,
    PROBED,
    QUEUED_TASKS,
    STORAGE_AVAILABLE,
    STORAGE_USED,
    Capacities,
    Flights,
    MetricsRegistry,
    PlatformState,
    Probe,
    probe,
)
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.backup import BackupTask

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from backup_support import Run
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.settings import ServiceSettings

METRICS = "/api/v1/metrics"
READINESS = "/api/v1/health/ready"
# Where nothing listens: a component the services reach there is stopped.
NOWHERE = "127.0.0.1:9"
REQUEST = "request-3f6a"
CAPACITIES = Capacities(database=10**12, object_storage=10**12)


class Platform:
    """The services of an API on the components of the tests, one of them stopped if asked."""

    def __init__(
        self,
        contract: OpenAPI,
        services: Services,
        capacities: Capacities = CAPACITIES,
    ) -> None:
        app = create_app(services, capacities=capacities)
        self.observed = app.state.observed
        self.api = ContractClient(TestClient(app, raise_server_exceptions=False), contract)

    def collect(self) -> Samples:
        """Collect the metrics, as Prometheus does, and read them."""
        response = self.api.get(METRICS)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        return samples(response.text)


type MakePlatform = Callable[..., Platform]


def stopped_database(service_database_url: str) -> Database:
    """Give a database at an address where no PostgreSQL listens."""
    address = engine_url(service_database_url).set(host="127.0.0.1", port=9)
    return Database(create_database_engine(address.render_as_string(hide_password=False)))


def stopped_queue() -> TaskQueue:
    """Give a queue on a Redis that does not listen."""
    return TaskQueue.connect(f"redis://{NOWHERE}/0", timeout=DEPOSIT_TIMEOUT)


def stopped_bucket() -> Bucket:
    """Give a bucket of a storage that does not listen."""
    return Bucket.connect("backups", f"http://{NOWHERE}", "us-east-1", "GK0000", "not-a-secret")


@pytest.fixture
def reached(
    database: Database,
    queue: TaskQueue,
    backups_bucket: Bucket,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
) -> Services:
    """Give the services of an API on the components of the tests, each of which answers."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def platform(contract: OpenAPI, reached: Services, service_database_url: str) -> MakePlatform:
    """Give a maker of platforms on the components of the tests, ``stopped`` naming one down."""

    def make(
        stopped: str | None = None,
        capacities: Capacities = CAPACITIES,
        *,
        maintenance: bool = False,
    ) -> Platform:
        services = dataclasses.replace(
            reached,
            database=stopped_database(service_database_url)
            if stopped == "database"
            else reached.database,
            queue=stopped_queue() if stopped == "cache" else reached.queue,
            backups=stopped_bucket() if stopped == "object_storage" else reached.backups,
            maintenance=Maintenance.of(reached.database, reached.queue) if maintenance else None,
        )
        return Platform(contract, services, capacities)

    return make


def ended_task(
    database: Database,
    kind: str,
    at: datetime,
    *,
    succeeded: bool,
    requested_by: UUID | None = None,
) -> UUID:
    """Write a task ended at a moment, succeeded or failed, by the platform or an account."""
    task_id = uuid4()
    problem = None if succeeded else {"code": "INTERNAL_ERROR", "status": 500}
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=task_id,
                kind=kind,
                status="succeeded" if succeeded else "failed",
                progress=100 if succeeded else 0,
                payload={},
                problem=None if problem is None else {**problem, "correlation_id": REQUEST},
                requested_by=requested_by,
                correlation_id=REQUEST,
                attempts=1,
                submitted_at=at - timedelta(minutes=5),
                started_at=at - timedelta(minutes=4),
                finished_at=at,
            )
        )
    return task_id


def queued_task(database: Database, submitted_at: datetime) -> None:
    """Write a task queued since a moment, that no worker has taken."""
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=uuid4(),
                kind="revision_mark",
                status="queued",
                progress=0,
                payload={},
                correlation_id=REQUEST,
                attempts=0,
                submitted_at=submitted_at,
            )
        )


def backup_of(database: Database, task_id: UUID, verification: str) -> None:
    """Write the backup a task took, with the outcome of its verification."""
    with database.transaction() as session:
        session.execute(
            insert(Backup).values(
                id=uuid4(),
                taken_at=utc_now(),
                size_bytes=1024,
                verification=verification,
                origin="scheduled",
                is_retained=False,
                object_key=f"backups/{task_id}.tar",
                application_version="0.3.0",
                schema_revision="0049",
                task_id=task_id,
            )
        )


@pytest.mark.requirement("WF-OBS-0010-A")
def test_the_api_answers_on_its_metrics_endpoint_with_its_requests(
    platform: MakePlatform,
) -> None:
    # « Le front, l'API et le worker répondent sur leur point de métriques. » : the API, by
    # ``getMetrics``, in the text format of Prometheus.
    served = platform()
    assert served.api.get("/api/v1/health").status_code == 200
    read = served.collect()
    assert value(read, "waterfall_api_requests_total", operation="getLiveness", status="200") == 1


def test_the_requests_are_counted_by_operation_and_status_with_their_duration(
    platform: MakePlatform,
) -> None:
    # Proper to US-2870: for the API, the number, the duration and the error rate of the requests;
    # an error is an answer of 500 or more, a refusal of the client is none.
    served = platform()
    for _ in range(3):
        served.api.get("/api/v1/health")
    project = uuid4()
    assert served.api.get(f"/api/v1/projects/{project}").status_code == 401
    assert served.api.get("/api/v1/installation").status_code == 503
    read = served.collect()
    counted = "waterfall_api_requests_total"
    assert value(read, counted, operation="getLiveness", status="200") == 3
    assert value(read, counted, operation="getProject", status="401") == 1
    assert value(read, counted, operation="getInstallation", status="503") == 1
    durations = "waterfall_api_request_duration_seconds_count"
    assert value(read, durations, operation="getLiveness") == 3
    summed = value(read, "waterfall_api_request_duration_seconds_sum", operation="getLiveness")
    assert (summed or 0) > 0


def test_a_request_that_reaches_no_operation_is_counted_apart(platform: MakePlatform) -> None:
    # Proper to US-2870: a path outside the contract is no operation, and no label takes its path.
    served = platform()
    served.api.client.get("/api/v1/nothing-here")
    read = served.collect()
    assert value(read, "waterfall_api_requests_total", operation="unrouted", status="404") == 1


@pytest.mark.requirement("WF-OBS-0010-A")
def test_every_component_answering_is_said_available(platform: MakePlatform) -> None:
    # « Chaque disponibilité et chaque espace présentés par l'écran d'état se retrouvent dans une
    # métrique. » : the availability of each component of data and of the identity provider, and
    # the space of PostgreSQL and of the object storage, used and left.
    read = platform().collect()
    for component in PROBED:
        assert value(read, COMPONENT_UP, component=component) == 1
    for component in ("database", "object_storage"):
        used = value(read, STORAGE_USED, component=component)
        left = value(read, STORAGE_AVAILABLE, component=component)
        assert used is not None
        assert left == 10**12 - used


@pytest.mark.requirement("WF-OBS-0010-A")
@pytest.mark.parametrize("stopped", ["database", "cache", "object_storage"])
def test_a_component_stopped_is_said_unavailable_at_the_next_collection(
    platform: MakePlatform, stopped: str
) -> None:
    # « L'arrêt de PostgreSQL, de Redis, du stockage objet ou du fournisseur d'identité fait passer
    # sa disponibilité à zéro à la collecte suivante. » : the others stay available, and the
    # metrics are served all the same.
    assert value(platform().collect(), COMPONENT_UP, component=stopped) == 1
    read = platform(stopped).collect()
    for component in PROBED:
        assert value(read, COMPONENT_UP, component=component) == (component != stopped)


@pytest.mark.requirement("WF-OBS-0010-A")
def test_the_identity_provider_stopped_is_unavailable_at_the_next_collection(
    platform: MakePlatform, realm: TestRealm
) -> None:
    # « L'arrêt de PostgreSQL, de Redis, du stockage objet ou du fournisseur d'identité fait passer
    # sa disponibilité à zéro à la collecte suivante. » : the realm stopped between two
    # collections of the same API; nothing is kept from one to the next.
    served = platform()
    assert value(served.collect(), COMPONENT_UP, component="identity_provider") == 1
    realm.stop()
    assert value(served.collect(), COMPONENT_UP, component="identity_provider") == 0


def test_a_probe_that_does_not_answer_in_time_is_said_unavailable() -> None:
    # Proper to US-2870: the probes are asked together, and the collection does not wait for one
    # that hangs.
    def hanging() -> str | None:
        time.sleep(2)
        return "never"

    def failing() -> str | None:
        raise ConnectionError

    started = time.monotonic()
    found = probe({"database": lambda: "18.1", "cache": hanging, "object_storage": failing}, 0.2)
    assert time.monotonic() - started < 1
    assert [(each.component, each.is_available, each.version) for each in found] == [
        ("database", True, "18.1"),
        ("cache", False, None),
        ("object_storage", False, None),
    ]


def test_the_queue_says_how_many_tasks_wait_and_how_long_the_oldest_has(
    platform: MakePlatform, database: Database
) -> None:
    # Proper to US-2870: the number of tasks queued and the age of the oldest, read at each
    # collection; the age grows while no worker takes it.
    served = platform()
    read = served.collect()
    assert (value(read, QUEUED_TASKS), value(read, OLDEST_QUEUED_TASK_AGE)) == (0, 0)
    queued_task(database, utc_now() - timedelta(minutes=20))
    queued_task(database, utc_now() - timedelta(minutes=1))
    first = served.collect()
    time.sleep(0.05)
    second = served.collect()
    assert value(first, QUEUED_TASKS) == 2
    age = value(first, OLDEST_QUEUED_TASK_AGE) or 0
    assert 20 * 60 <= age < 21 * 60
    assert (value(second, OLDEST_QUEUED_TASK_AGE) or 0) > age


def test_the_latest_scheduled_backup_and_reading_of_the_accounts_are_given_with_their_outcome(
    platform: MakePlatform, database: Database
) -> None:
    # Proper to US-2870: the latest outcome of a scheduled backup and of a reading of the accounts,
    # read from the database, which the alerts read (WF-OBS-0030). A backup is failed when its task
    # failed; one an account asked for is not scheduled.
    served = platform()
    read = served.collect()
    assert value(read, LAST_RUN_SUCCESS, run="scheduled_backup") is None
    assert value(read, LAST_RUN_SUCCESS, run="identity_sync") is None
    now = utc_now().replace(microsecond=0)
    verified = ended_task(database, "backup", now - timedelta(days=1), succeeded=True)
    backup_of(database, verified, "passed")
    ended_task(database, "identity_sync", now - timedelta(hours=2), succeeded=True)
    ended_task(database, "identity_sync", now - timedelta(hours=1), succeeded=False)
    account = uuid4()
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**raw_account(id=account)))
    asked = ended_task(database, "backup", now, succeeded=True, requested_by=account)
    backup_of(database, asked, "failed")
    read = served.collect()
    assert value(read, LAST_RUN_SUCCESS, run="scheduled_backup") == 1
    assert (
        value(read, LAST_RUN_TIMESTAMP, run="scheduled_backup")
        == (now - timedelta(days=1)).timestamp()
    )
    assert value(read, LAST_RUN_SUCCESS, run="identity_sync") == 0
    ended_task(database, "backup", now - timedelta(minutes=30), succeeded=False)
    assert value(served.collect(), LAST_RUN_SUCCESS, run="scheduled_backup") == 0
    ended_task(database, "backup", now - timedelta(minutes=10), succeeded=True)
    assert value(served.collect(), LAST_RUN_SUCCESS, run="scheduled_backup") == 1


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_scheduled_backup_whose_archive_does_not_read_back_whole_is_said_failed_by_the_gauge(
    platform: MakePlatform,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
) -> None:
    # « Une archive qui échoue à sa vérification fait échouer sa tâche » (#4230, US-2910): the
    # task of the scheduled backup the worker played fails, and the gauge says the same.
    served = platform()
    assert value(served.collect(), LAST_RUN_SUCCESS, run="scheduled_backup") is None
    corrupting = Corrupting(backups_bucket.client, backups_bucket.name)
    run(BackupTask(databases, corrupting))
    assert value(served.collect(), LAST_RUN_SUCCESS, run="scheduled_backup") == 0


def test_a_scheduled_backup_that_succeeded_stays_succeeded_once_the_rotation_removed_its_row(
    platform: MakePlatform, database: Database, owner: Engine
) -> None:
    # Proper to US-2870: the failure of a backup is that of its task (contract, OperationOutcome):
    # the table of the backups is not read, and the rotation that removes a row changes nothing.
    now = utc_now().replace(microsecond=0)
    task_id = ended_task(database, "backup", now, succeeded=True)
    backup_of(database, task_id, "passed")
    served = platform()
    assert value(served.collect(), LAST_RUN_SUCCESS, run="scheduled_backup") == 1
    with Session(owner) as session, session.begin():
        session.execute(delete(Backup).where(Backup.task_id == task_id))
    read = served.collect()
    assert value(read, LAST_RUN_SUCCESS, run="scheduled_backup") == 1
    assert value(read, LAST_RUN_TIMESTAMP, run="scheduled_backup") == now.timestamp()


@pytest.mark.requirement("WF-OBS-0010-A")
def test_the_space_of_the_object_storage_is_the_sum_of_its_objects(
    platform: MakePlatform, backups_bucket: Bucket
) -> None:
    # « Chaque disponibilité et chaque espace présentés par l'écran d'état se retrouvent dans une
    # métrique. » : the space used of the storage measured, what is left the capacity declared
    # less it; a capacity smaller than the space used leaves nothing. The bucket of the tests holds
    # what the tests before this one left: what it holds is measured first.
    measured = platform(capacities=Capacities(database=1, object_storage=10**9))
    before = value(measured.collect(), STORAGE_USED, component="object_storage")
    assert before is not None
    keys = [f"uploads/{uuid4()}", f"backups/{uuid4()}"]
    backups_bucket.put(keys[0], b"x" * 1000)
    backups_bucket.put(keys[1], b"y" * 24)
    try:
        read = measured.collect()
    finally:
        for key in keys:
            backups_bucket.remove(key)
    assert value(read, STORAGE_USED, component="object_storage") == before + 1024
    assert value(read, STORAGE_AVAILABLE, component="object_storage") == 10**9 - before - 1024
    assert value(read, STORAGE_AVAILABLE, component="database") == 0


def test_without_a_declared_capacity_only_the_space_used_is_given(platform: MakePlatform) -> None:
    # Proper to US-2870: what is left of a capacity not declared is unknown, and never said.
    read = platform(capacities=Capacities()).collect()
    assert (value(read, STORAGE_USED, component="database") or 0) > 0
    assert value(read, STORAGE_AVAILABLE, component="database") is None
    assert value(read, STORAGE_AVAILABLE, component="object_storage") is None


def test_a_database_stopped_leaves_out_what_is_read_in_it_and_nothing_else(
    platform: MakePlatform,
) -> None:
    # Proper to US-2870: a gauge that cannot be read is left out, never given a value it has not.
    read = platform("database").collect()
    assert value(read, COMPONENT_UP, component="database") == 0
    assert value(read, QUEUED_TASKS) is None
    assert value(read, OLDEST_QUEUED_TASK_AGE) is None
    assert value(read, STORAGE_USED, component="database") is None
    assert value(read, STORAGE_USED, component="object_storage") is not None


def test_the_metrics_expose_no_project_data_identity_nor_secret(
    platform: MakePlatform, database: Database
) -> None:
    # Proper to US-2870: the endpoint exposes no project data, no identity, no secret (TFX-09);
    # an operation is named by its identifier, never by the path of the request.
    served = platform()
    project = uuid4()
    served.api.get(f"/api/v1/projects/{project}")
    with database.transaction() as session:
        account = raw_account()
        session.execute(insert(UserAccount).values(**account))
    response = served.api.get(METRICS)
    for held in [str(project), str(account["id"]), str(account["email"]), "Martin"]:
        assert held not in response.text
    for secret in PLATFORM_SECRETS.values():
        assert secret not in response.text
    labels = {name for _, labelled in samples(response.text) for name, _ in labelled}
    # The version a component announces is no datum of a project, no identity, no secret.
    assert labels <= {"operation", "status", "le", "component", "run", "version"}


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_api_announces_its_version_and_that_of_each_component_its_probe_reads(
    platform: MakePlatform, realm: TestRealm
) -> None:
    # « L'écran d'état présente la version de chaque composant. » : the metrics the screen reads
    # give it — the API its own, PostgreSQL, Redis and Keycloak the one their probe reads, one down
    # none. Keycloak's is given by the extension to the service account (#4641), which the realm of
    # test plays here and ``test_keycloak_component_version`` tries against Keycloak.
    realm.version = "26.8.2"
    announced = versions_in(platform().collect())
    assert announced["api"] == __version__
    assert announced["database"].split(".")[0] == "18"
    assert announced["cache"]
    assert announced["identity_provider"] == "26.8.2"
    assert "database" not in versions_in(platform("database").collect())


@pytest.mark.story("US-2890")
def test_a_version_of_keycloak_not_given_leaves_it_available_without_a_version(
    platform: MakePlatform,
) -> None:
    # Proper to US-2890: the realm of test answers neither the token of the service account nor the
    # version, as a Keycloak without the extension; it serves its keys, and is available all the
    # same, its version not said rather than a wrong one.
    read = platform().collect()
    assert value(read, COMPONENT_UP, component="identity_provider") == 1
    assert "identity_provider" not in versions_in(read)


@pytest.mark.story("US-2890")
@pytest.mark.parametrize("body", [b'{"version": ""}', b'{"version": 26}', b'["26.8.2"]', b""])
def test_a_version_of_keycloak_invalid_leaves_it_available_without_a_version(
    platform: MakePlatform, realm: TestRealm, body: bytes
) -> None:
    # Proper to US-2890: an extension that answers no version — empty, not text, not an object, no
    # body — leaves Keycloak available, its version not said.
    realm.version_body = body
    read = platform().collect()
    assert value(read, COMPONENT_UP, component="identity_provider") == 1
    assert "identity_provider" not in versions_in(read)


@pytest.mark.story("US-2890")
def test_a_version_of_keycloak_slower_than_its_budget_leaves_it_available(
    platform: MakePlatform, realm: TestRealm
) -> None:
    # Proper to US-2890: the version has a budget of its own, within that of the probe: one that
    # outlasts it is not said, and Keycloak, whose keys were served, is available.
    realm.version = "26.8.2"
    realm.version_delay = PROBE_SECONDS * 2
    read = platform().collect()
    assert value(read, COMPONENT_UP, component="identity_provider") == 1
    assert "identity_provider" not in versions_in(read)


def versions_in(read: Samples) -> dict[str, str]:
    """Give the version each component announces in the metrics read, by component."""
    return {
        dict(labelled)["component"]: dict(labelled)["version"]
        for (name, labelled), _ in read.items()
        if name == COMPONENT_VERSION
    }


@pytest.mark.requirement("WF-EXP-0040-A")
def test_the_instance_is_ready_when_the_components_it_needs_answer(platform: MakePlatform) -> None:
    # Proper to US-2870: ``getReadiness`` is served; it answers when the components the instance
    # needs answer, and says each one, the instance first.
    response = platform().api.get(READINESS)
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    assert body["status"] == "ready"
    said = {each["component"]: each for each in body["components"]}
    assert list(said) == ["api", *PROBED]
    assert all(each["is_available"] for each in said.values())
    assert said["database"]["version"]
    # The example of the contract says the same components, in the same order: the instance and
    # what it probes, the worker and Prometheus being read by the collection (#4227).
    assert list(said) == [each["component"] for each in example("readiness")["components"]]


def test_an_instance_without_its_database_is_not_ready_and_names_it(platform: MakePlatform) -> None:
    # Proper to US-2870: 503 otherwise, naming the component (WF-EXP-0040).
    response = platform("database").api.get(READINESS)
    assert response.status_code == 503
    problem = response.json()
    assert (problem["code"], problem["params"]) == (
        "COMPONENT_UNAVAILABLE",
        {"component": "database"},
    )


@pytest.mark.parametrize("stopped", ["cache", "object_storage", "identity_provider"])
def test_an_instance_stays_ready_without_what_it_serves_without_and_says_it_unavailable(
    platform: MakePlatform, realm: TestRealm, stopped: str
) -> None:
    # Proper to US-2870: without Redis, the storage or the identity provider, the instance still
    # serves what does not need them (§4.5.4, table 12); the component is said unavailable, never
    # available.
    served = platform(None if stopped == "identity_provider" else stopped)
    if stopped == "identity_provider":
        realm.stop()
    response = served.api.get(READINESS)
    assert response.status_code == 200
    said = {each["component"]: each["is_available"] for each in response.json()["components"]}
    assert said[stopped] is False


def test_in_maintenance_the_metrics_are_served_and_the_instance_is_not_ready(
    platform: MakePlatform, queue: TaskQueue, owner: Engine
) -> None:
    # Proper to US-2870: the metrics depend on no component, and say each one; a restoration that
    # holds the platform refuses the rest, the readiness with it (WF-ADM-0160).
    served = platform(maintenance=True)
    Maintenance.of(Database(owner), queue).hold(Restoring(uuid4(), {}, None, REQUEST, 1))
    assert value(served.collect(), COMPONENT_UP, component="database") == 1
    refused = served.api.get(READINESS)
    assert refused.status_code == 503
    assert refused.json()["params"] == {"component": "database"}
    # The requests the maintenance refuses come before the routing: counted, but as unrouted.
    assert served.api.get(f"/api/v1/projects/{uuid4()}").status_code == 503
    read = served.collect()
    assert value(read, "waterfall_api_requests_total", operation="unrouted", status="503") == 2


@pytest.mark.requirement("WF-OBS-0010-A")
def test_the_probes_and_the_collection_answer_while_every_connection_of_the_requests_is_taken(
    platform: MakePlatform, reached: Services
) -> None:
    # « L'arrêt de PostgreSQL, de Redis, du stockage objet ou du fournisseur d'identité fait passer
    # sa disponibilité à zéro à la collecte suivante. » : and only then; a pool of the requests
    # saturated does not make the database look down, nor hold the collection. The probe and the
    # reading of the state have a connection of their own.
    served = platform()
    pool = reached.database.engine.pool
    assert isinstance(pool, QueuePool)
    taken = [reached.database.engine.connect() for _ in range(pool.size() + POOL_OVERFLOW)]
    try:
        started = time.monotonic()
        ready = served.api.get(READINESS)
        read = served.collect()
        assert time.monotonic() - started < 2 * PROBE_SECONDS
    finally:
        for connection in taken:
            connection.close()
    assert ready.status_code == 200
    assert value(read, COMPONENT_UP, component="database") == 1
    assert value(read, QUEUED_TASKS) is not None
    assert value(read, STORAGE_USED, component="database") is not None


def test_a_slow_reading_of_the_state_does_not_make_a_request_of_availability_fail(
    platform: MakePlatform,
) -> None:
    # Proper to US-2870: the observation has two connections; one held by a collection that is slow
    # leaves the other to the probe of ``getReadiness``, which would else wait and say the database
    # down.
    served = platform()
    reading = served.observed.database.engine.connect()
    try:
        started = time.monotonic()
        ready = served.api.get(READINESS)
        assert time.monotonic() - started < PROBE_SECONDS
    finally:
        reading.close()
    assert ready.status_code == 200


class SleepingBucket(Bucket):
    """A bucket whose listing of the objects takes longer than a collection waits."""

    def used_bytes(self) -> int:
        """List the objects, slowly."""
        time.sleep(2)
        return 1


def test_a_listing_of_the_storage_that_outlasts_the_budget_leaves_the_space_out(
    database: Database, backups_bucket: Bucket
) -> None:
    # Proper to US-2870: the listing of every object is held to the budget of the probes; past it
    # the space of the storage is left out, and the collection is not held.
    sleeping = SleepingBucket(backups_bucket.client, backups_bucket.name)
    registry = MetricsRegistry()
    probes: dict[str, Probe] = {"object_storage": sleeping.reach}
    state = PlatformState(database, probes, sleeping, {}, Capacities())
    state.budget = 0.2
    registry.read_at_collection.append(state)
    started = time.monotonic()
    read = samples(registry.expose().decode())
    assert time.monotonic() - started < 1
    assert value(read, COMPONENT_UP, component="object_storage") == 1
    assert value(read, STORAGE_USED, component="object_storage") is None


class CountingBucket(SleepingBucket):
    """A sleeping bucket that counts the listings it was asked."""

    listings = 0

    def used_bytes(self) -> int:
        """List the objects, slowly, counting."""
        type(self).listings += 1
        return super().used_bytes()


def test_a_storage_that_does_not_answer_holds_one_listing_however_often_it_is_collected(
    database: Database, backups_bucket: Bucket
) -> None:
    # Proper to US-2870: the listing left to end alone is not started again by the next collection:
    # a storage that sleeps holds one thread, and its space stays out.
    sleeping = CountingBucket(backups_bucket.client, backups_bucket.name)
    CountingBucket.listings = 0
    state = PlatformState(database, {}, sleeping, {}, Capacities())
    state.budget = 0.1
    assert state.storage_used() is None
    assert state.storage_used() is None
    assert CountingBucket.listings == 1


def test_a_probe_that_does_not_answer_is_not_asked_again_while_it_runs() -> None:
    # Proper to US-2870: the same bound for the probes, which share their flights.
    asked: list[int] = []

    def hanging() -> str | None:
        asked.append(1)
        time.sleep(1)
        return None

    flights = Flights()
    for _ in range(2):
        found = probe({"cache": hanging}, 0.1, flights)
        assert [each.is_available for each in found] == [False]
    assert asked == [1]


@pytest.mark.requirement("WF-OBS-0010-A")
def test_a_call_that_raises_a_base_exception_does_not_keep_its_name() -> None:
    # Proper to US-2870: a SystemExit ends the flight, and the next start asks again.
    asked: list[int] = []

    def leaving() -> None:
        asked.append(1)
        raise SystemExit

    flights = Flights()
    first = flights.start("probe-cache", leaving)
    wait([first], timeout=1)
    assert isinstance(first.exception(), SystemExit)
    second = flights.start("probe-cache", leaving)
    wait([second], timeout=1)
    assert second is not first
    assert asked == [1, 1]


@pytest.mark.requirement("WF-OBS-0010-A")
def test_a_thread_that_does_not_start_does_not_keep_its_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2870: no thread left to start is a failed flight, not a name held forever.
    class ExhaustedError(RuntimeError):
        """Stand for the error of a process that can start no more threads."""

    class Refusing(threading.Thread):
        def start(self) -> None:
            raise ExhaustedError

    flights = Flights()
    with monkeypatch.context() as patch:
        patch.setattr(threading, "Thread", Refusing)
        failed = flights.start("probe-cache", lambda: "7")
    assert failed.done()
    assert isinstance(failed.exception(), ExhaustedError)
    again = flights.start("probe-cache", lambda: "7")
    assert again.result(timeout=1) == "7"


@pytest.mark.requirement("WF-OBS-0010-A")
def test_a_thread_that_fails_to_start_with_a_memory_error_does_not_keep_its_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2870: whatever the start raises, not only a RuntimeError, frees the name.
    class Refusing(threading.Thread):
        def start(self) -> None:
            raise MemoryError

    flights = Flights()
    with monkeypatch.context() as patch:
        patch.setattr(threading, "Thread", Refusing)
        failed = flights.start("probe-cache", lambda: "7")
    assert isinstance(failed.exception(), MemoryError)
    assert flights.start("probe-cache", lambda: "8").result(timeout=5) == "8"


@pytest.mark.requirement("WF-OBS-0010-A")
def test_an_interrupt_while_the_thread_starts_reaches_the_caller_and_frees_the_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2870: an interrupt of the calling thread is not swallowed by the flight.
    class Refusing(threading.Thread):
        def start(self) -> None:
            raise KeyboardInterrupt

    flights = Flights()
    with monkeypatch.context() as patch:
        patch.setattr(threading, "Thread", Refusing)
        with pytest.raises(KeyboardInterrupt):
            flights.start("probe-cache", lambda: "7")
    assert flights.start("probe-cache", lambda: "8").result(timeout=5) == "8"
