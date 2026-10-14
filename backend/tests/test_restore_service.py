# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The service of the restoration runs the restorations the API deposits, in their order (#985).

Each test makes an installation of its own (``installations``) and serves the API on it, the
maintenance beside its queue; the service of the restoration runs on the same queue, as the owner of
both databases. Keycloak is not here: what a restoration asks of it is kept by ``Provider``, in its
order; the tests of the platform try the requests themselves (``test_keycloak_restoration``).
"""

import json
import tarfile
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import role
from installations import (
    Installation,
    Provider,
    Take,
    inscribe,
    restorer_headers,
    written_task,
)
from openapi_core import OpenAPI
from realm import TestRealm
from redis.exceptions import RedisError
from sqlalchemy import Engine, insert, select
from support import ContractClient, Logs, nowhere
from task_handlers import Runs, deposit, held_run

from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.backups.tables import Backup
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.maintenance import Maintenance, Restoring
from waterfall.platform.queue import TaskQueue
from waterfall.platform.tasks import BackgroundTask
from waterfall.restore import task as restoration
from waterfall.restore.provider import RealmNotAppliedError, RealmRequests
from waterfall.restore.runner import Restorer
from waterfall.restore.task import GIVE_THE_REALM_BACK, RestoreTask, await_runs
from waterfall.worker.backup import MANIFEST
from waterfall.worker.runner import Timing, Worker

RESTORES = "/api/v1/restores"


@dataclass
class Service:
    """The service of the restoration on an installation, what it asks Keycloak, and its API."""

    restorer: Restorer
    provider: Provider
    maintenance: Maintenance
    api: ContractClient
    headers: dict[str, str]
    sessions: str


@pytest.fixture
def service(
    installation: Installation,
    queue: TaskQueue,
    installation_api: ContractClient,
    realm: TestRealm,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Service]:
    """Run the service of the restoration on an installation, its steps kept in their order.

    The sessions of the front it closes are those of a pattern of the test alone: other tests
    share the Redis.
    """
    steps: list[str] = []
    provider = Provider(steps)
    sessions = f"wf-test-{uuid4().hex}:"
    maintenance = Maintenance(queue.client, queue.stream + ":maintenance", f"{sessions}*")
    for name in ("keep_for_restoration", "replace", "write_back_after_restoration"):
        monkeypatch.setattr(restoration, name, kept_as(steps, name, getattr(restoration, name)))

    def migrate(engine: Engine) -> None:
        steps.append("migrate")
        upgrade(engine)

    task = RestoreTask(installation.owner, installation.bucket, maintenance, provider, migrate)
    owner = Database(create_database_engine(installation.owner["waterfall"]))
    restorer = Restorer(owner, queue, task, "restorer-test", Timing(0, 0.1))
    restorer.queue.prepare()
    headers = restorer_headers(installation, realm)
    yield Service(restorer, provider, maintenance, installation_api, headers, sessions)
    owner.dispose()


def kept_as(steps: list[str], name: str, done: Any) -> Any:
    """Keep the step a function of the restoration makes, then make it."""

    def keeping(*arguments: Any) -> Any:
        steps.append(f"replace {arguments[0]}" if name == "replace" else name)
        return done(*arguments)

    return keeping


def taken(installation: Installation) -> dict[str, str]:
    """Give the identifier and the date of the latest backup, as the list says them."""
    with installation.database.transaction() as session:
        backup = session.scalars(select(Backup).order_by(Backup.taken_at.desc()).limit(1)).one()
    return {"backup_id": str(backup.id), "taken_at": iso(backup)}


def iso(backup: Backup) -> str:
    """Write the date of a backup as the API does."""
    return backup.taken_at.isoformat().replace("+00:00", "Z")


def asked(backup: dict[str, str], taken_at: str | None = None) -> dict[str, object]:
    """Ask for the restoration of a backup, the date its confirmation states."""
    return {
        "backup_id": backup["backup_id"],
        "confirmed": True,
        "acknowledged_backup_taken_at": taken_at or backup["taken_at"],
    }


def read_task(installation: Installation, task_id: str) -> BackgroundTask:
    """Read a task in the database of the installation."""
    with installation.database.transaction() as session:
        return session.get_one(BackgroundTask, UUID(task_id))


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_restoration_asked_of_the_api_is_run_by_its_service_alone_and_inscribed_last(
    installation: Installation, take: Take, service: Service, queue: TaskQueue
) -> None:
    # « Une inscription faite après la sauvegarde est encore présente après la restauration, et la
    # dernière inscription est la restauration elle-même. » The task goes to the stream of the
    # restorations, never to the worker's, which runs nothing of it; the service runs it in the
    # order of #981 — sessions closed, kept, replaced, migrated, written back, the caches of
    # Keycloak cleared and its realm applied again, sessions closed again —, then lifts the
    # maintenance, the restoration inscribed last.
    take()
    backup = taken(installation)
    after = inscribe(installation.database, "Après la sauvegarde")
    answer = service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    assert answer.status_code == 202
    task_id = answer.json()["task_id"]
    assert UUID(task_id) in queue.restores().waiting()
    assert UUID(task_id) not in queue.waiting()
    assert not Worker(installation.database, queue, {}, "worker-test", Timing(0, 0.1)).step()
    assert service.restorer.step()
    assert service.provider.steps == [
        "close_sessions",
        "keep_for_restoration",
        "prepare",
        "replace waterfall",
        "replace identity_provider",
        "migrate",
        "write_back_after_restoration",
        "clear_caches",
        "apply_realm",
        "remove",
        "close_sessions",
    ]
    assert service.maintenance.current() is None
    assert service.api.get("/api/v1/health").json() == {"status": "ok"}
    read = service.api.get(f"/api/v1/tasks/{task_id}", headers=service.headers)
    assert (read.status_code, read.json()["status"]) == (200, "succeeded")
    with installation.database.transaction() as session:
        latest = AuditEntry.occurred_at.desc(), AuditEntry.id.desc()
        last = session.scalars(select(AuditEntry).order_by(*latest).limit(1)).one()
        kept = session.scalar(select(AuditEntry.id).where(AuditEntry.id == after))
    assert (last.action, str(last.object_id)) == ("restore", backup["backup_id"])
    assert kept == after
    assert not queue.restores().waiting()


@pytest.mark.requirement("WF-ADM-0160-A")
def test_no_partial_restoration_is_offered_both_databases_are_replaced_whole(
    contract: OpenAPI, installation: Installation, take: Take, service: Service
) -> None:
    # « Aucune restauration partielle n'est proposée. » The request names a backup and its date,
    # nothing that would choose a part of it; a role made after the backup is gone from the
    # database of Waterfall, and a realm made after it from the provider's.
    body = contract.spec / "paths" / "/restores" / "post" / "requestBody" / "content"
    schema = body / "application/json" / "schema"
    assert set((schema / "properties").keys()) == {
        "backup_id",
        "external_backup_upload_id",
        "acknowledged_backup_taken_at",
        "confirmed",
    }
    take()
    backup = taken(installation)
    later = role(installation.database, "Après la sauvegarde")
    provider = create_database_engine(installation.owner["identity_provider"])
    with provider.begin() as connection:
        connection.exec_driver_sql("INSERT INTO realm VALUES ('after-the-backup')")
    answer = service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    assert answer.status_code == 202
    assert service.restorer.step()
    with provider.connect() as connection:
        realms = connection.exec_driver_sql("SELECT id FROM realm").scalars().all()
    provider.dispose()
    with installation.database.transaction() as session:
        assert session.get(AccessRole, later) is None
    assert realms == ["waterfall"]


@pytest.mark.requirement("WF-ADM-0160-A")
def test_the_confirmation_names_the_date_of_the_backup_another_date_is_refused(
    installation: Installation, take: Take, service: Service, queue: TaskQueue
) -> None:
    # « La confirmation nomme la date de la sauvegarde. » A date that is not the backup's is a
    # confirmation that does not name it: 400, and nothing is deposited.
    take()
    backup = taken(installation)
    answer = service.api.post(
        RESTORES, json=asked(backup, "2026-01-01T00:00:00Z"), headers=service.headers
    )
    assert answer.status_code == 400
    assert answer.json()["code"] == "CONFIRMATION_REQUIRED"
    assert not queue.restores().waiting()


def test_an_unknown_backup_is_not_found_and_a_second_restoration_conflicts(
    installation: Installation, take: Take, service: Service
) -> None:
    # The refusals of startRestore: a backup unknown, 404; a restoration already queued, 409.
    take()
    backup = taken(installation)
    unknown = {**backup, "backup_id": str(uuid4())}
    missing = service.api.post(RESTORES, json=asked(unknown), headers=service.headers)
    assert missing.status_code == 404
    first = service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    second = service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    assert first.status_code == 202
    assert (second.status_code, second.json()["code"]) == (409, "STATE_FORBIDS_OPERATION")


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_restoration_asked_without_the_permission_to_read_the_backups_is_not_found(
    installation: Installation,
    take: Take,
    service: Service,
    realm: TestRealm,
    queue: TaskQueue,
) -> None:
    # « Une adresse d’objet inexistant et une adresse d’objet non consultable mènent au même
    # écran. » The permission to restore without that to read the backups: the backup named does
    # not exist for the caller, 404 as an unknown one, and nothing is deposited.
    take()
    backup = taken(installation)
    restoring_only = restorer_headers(installation, realm, ("platform_restore",), "Louise")
    hidden = service.api.post(RESTORES, json=asked(backup), headers=restoring_only)
    unknown = service.api.post(
        RESTORES, json=asked({**backup, "backup_id": str(uuid4())}), headers=service.headers
    )
    assert hidden.status_code == unknown.status_code == 404
    assert hidden.json()["code"] == unknown.json()["code"] == "NOT_FOUND"
    assert not queue.restores().waiting()


def test_in_maintenance_every_operation_but_the_probe_answers_503_and_the_probe_says_it(
    service: Service,
) -> None:
    # The maintenance of a restoration (#604): the probe of liveness says it, and its end; every
    # other operation answers 503 COMPONENT_UNAVAILABLE, the database being replaced.
    service.maintenance.hold(Restoring(uuid4(), {}, None, "request-3f6a", 1))
    refused = service.api.get("/api/v1/me", headers=service.headers)
    assert refused.status_code == 503
    assert (refused.json()["code"], refused.json()["params"]) == (
        "COMPONENT_UNAVAILABLE",
        {"component": "database"},
    )
    assert service.api.get("/api/v1/health").json() == {"status": "maintenance"}
    service.maintenance.lift()
    assert service.api.get("/api/v1/health").json() == {"status": "ok"}
    assert service.api.get("/api/v1/me", headers=service.headers).status_code == 200


def test_a_restoration_closes_the_sessions_of_the_front_before_it_keeps_and_once_done(
    installation: Installation, take: Take, service: Service, queue: TaskQueue
) -> None:
    # Proper to US-0440: during a restoration, the users are signed out — every session of the
    # provider closed, and the front's, which Redis keeps, deleted —, before anything is kept, and
    # again at the end: a session opened meanwhile does not outlive it.
    take()
    backup = taken(installation)
    queue.client.set(f"{service.sessions}session:before", "{}")
    seen: list[int] = []
    keep = restoration.keep_for_restoration

    def keeping(*arguments: Any) -> None:
        seen.append(int(queue.client.exists(f"{service.sessions}session:before")))
        queue.client.set(f"{service.sessions}session:meanwhile", "{}")
        keep(*arguments)

    restoration.keep_for_restoration = keeping
    try:
        service.api.post(RESTORES, json=asked(backup), headers=service.headers)
        assert service.restorer.step()
    finally:
        restoration.keep_for_restoration = keep
    assert seen == [0]
    assert not queue.client.exists(
        f"{service.sessions}session:before", f"{service.sessions}session:meanwhile"
    )
    assert service.provider.steps.count("close_sessions") == 2


def test_a_backup_of_a_newer_version_fails_its_restoration_before_the_maintenance(
    installation: Installation, service: Service, tmp_path: Path
) -> None:
    # Proper to US-0440: a backup of a version newer than the installation is refused, by the
    # task, before the maintenance: no session closed, nothing kept nor replaced.
    manifest = tmp_path / MANIFEST
    manifest.write_text(json.dumps({"application_version": "999.0.0", "databases": []}))
    archive = tmp_path / "newer.tar"
    with tarfile.open(archive, "w") as tar:
        tar.add(manifest, arcname=MANIFEST)
    installation.bucket.upload("newer.tar", archive)
    backup_id, at = newer_backup(installation)
    confirmed = {"backup_id": str(backup_id), "taken_at": at}
    answer = service.api.post(RESTORES, json=asked(confirmed), headers=service.headers)
    assert answer.status_code == 202
    assert service.restorer.step()
    failed = read_task(installation, answer.json()["task_id"])
    assert failed.status == "failed"
    assert failed.problem is not None
    assert (failed.problem["code"], failed.problem["params"]["backup_version"]) == (
        "BACKUP_FROM_NEWER_VERSION",
        "999.0.0",
    )
    assert service.provider.steps == []
    assert service.maintenance.current() is None


def newer_backup(installation: Installation) -> tuple[UUID, str]:
    """Record a backup of a newer version, whose archive is ``newer.tar``; give it and its date."""
    task_id = written_task(installation.database, "backup", "queued")
    backup_id, at = uuid4(), utc_now()
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        connection.execute(
            insert(Backup).values(
                id=backup_id,
                taken_at=at,
                size_bytes=1,
                verification="passed",
                origin="manual",
                is_retained=False,
                object_key="newer.tar",
                application_version="999.0.0",
                schema_revision="9999",
                task_id=task_id,
            )
        )
    owner.dispose()
    return backup_id, at.isoformat().replace("+00:00", "Z")


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_restoration_interrupted_in_maintenance_starts_again_and_lifts_it_at_its_end(
    installation: Installation, take: Take, service: Service
) -> None:
    # A restoration interrupted once the maintenance is held — the realm not applied again —
    # leaves the maintenance and its entry: taken over, it starts again from the beginning, its
    # attempt counted in the maintenance, and lifts it once it has ended. The journal names the
    # restoration once.
    service.provider.failing = 1
    take()
    backup = taken(installation)
    service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    assert service.restorer.step()
    held = service.maintenance.current()
    assert held is not None
    assert held.attempts == 1
    assert service.api.get("/api/v1/health").json() == {"status": "maintenance"}
    assert service.restorer.step()
    assert service.maintenance.current() is None
    with installation.database.transaction() as session:
        restored = session.scalars(select(AuditEntry).where(AuditEntry.action == "restore")).all()
    assert len(restored) == 1
    assert service.provider.steps.count("keep_for_restoration") == 2


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_restoration_interrupted_once_the_caches_are_cleared_gives_the_realm_back_first(
    installation: Installation, take: Take, service: Service
) -> None:
    # Interrupted once the caches of Keycloak are cleared, the realm not applied again: Keycloak
    # serves the realm of the backup, whose secrets refuse the service account and the client of
    # the bootstrap. Taken up, the restoration has the realm of the installation applied again
    # first, then starts again from the beginning, and lifts the maintenance at its end.
    service.provider.failing = 1
    take()
    backup = taken(installation)
    service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    assert service.restorer.step()
    assert service.maintenance.current() is not None
    assert service.provider.serving_backup
    del service.provider.steps[:]
    assert service.restorer.step()
    assert service.provider.steps[:3] == ["apply_realm", "close_sessions", "keep_for_restoration"]
    assert service.maintenance.current() is None
    assert service.api.get("/api/v1/health").json() == {"status": "ok"}


def test_a_restoration_ended_whose_maintenance_was_not_lifted_lifts_it_and_runs_no_more(
    installation: Installation, take: Take, service: Service, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The task succeeded and the restoration inscribed, committed, then the maintenance not lifted
    # — Redis out of reach, the process stopped —: the entry is left. Taken over, the restoration
    # lifts the maintenance and runs nothing again; the journal names it once.
    lift = service.restorer.maintenance.lift
    lifts: list[int] = []

    def lifting() -> None:
        lifts.append(1)
        if len(lifts) == 1:
            message = "Redis out of reach"
            raise RedisError(message)
        lift()

    monkeypatch.setattr(service.restorer.maintenance, "lift", lifting)
    take()
    backup = taken(installation)
    answer = service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    assert service.restorer.step()
    assert service.maintenance.current() is not None
    assert service.restorer.step()
    assert service.maintenance.current() is None
    assert len(lifts) == 2
    assert service.provider.steps.count("keep_for_restoration") == 1
    assert read_task(installation, answer.json()["task_id"]).status == "succeeded"
    with installation.database.transaction() as session:
        restored = session.scalars(select(AuditEntry).where(AuditEntry.action == "restore")).all()
    assert len(restored) == 1
    assert not service.restorer.queue.waiting()


def test_a_restoration_whose_attempts_are_spent_leaves_the_platform_in_maintenance(
    installation: Installation, take: Take, service: Service, logs: Logs
) -> None:
    # Three attempts interrupted: the databases are in no state to serve, which an operator must
    # look at; the maintenance stays, and the entry is acknowledged. The realm never applied
    # again, each attempt taken up says what the operator does, and goes on: refused.
    service.provider.failing = 9
    take()
    backup = taken(installation)
    service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    for _ in range(4):
        assert service.restorer.step()
    assert service.provider.steps.count("clear_caches") == 1
    assert service.provider.steps.count("apply_realm") == 3
    told = [record["action"] for record in logs.named("restore.realm_not_given_back")]
    assert told == [GIVE_THE_REALM_BACK] * 2


def test_a_restoration_whose_attempts_are_spent_is_abandoned_and_never_deposited_again(
    installation: Installation, take: Take, service: Service, logs: Logs
) -> None:
    # Its attempts spent, the restoration is abandoned in the maintenance, which stays: the
    # service deposits it no more, and its failure is said once.
    service.provider.failing = 9
    take()
    backup = taken(installation)
    service.api.post(RESTORES, json=asked(backup), headers=service.headers)
    for _ in range(4):
        assert service.restorer.step()
    held = service.maintenance.current()
    assert held is not None
    assert held.abandoned
    service.restorer.redeposit()
    assert not service.restorer.queue.waiting()
    assert not service.restorer.step()
    spent = [r for r in logs.named("task.failed") if r.get("reason") == "attempts_spent"]
    assert len(spent) == 1
    assert service.maintenance.current() is not None
    assert not service.restorer.queue.waiting()


def test_the_worker_runs_no_task_in_maintenance_and_runs_it_after(
    installation: Installation, queue: TaskQueue, service: Service
) -> None:
    # #953: while a restoration holds the maintenance, the worker runs nothing, and leaves the
    # entry; once it is lifted, it takes the entry over and runs the task.
    runs = Runs()
    worker = Worker(
        installation.database, queue, {"identity_sync": runs}, "worker-test", Timing(0, 0.1)
    )
    queue.prepare()
    task_id = deposit(installation.database, queue)
    service.maintenance.hold(Restoring(uuid4(), {}, None, "request-3f6a", 1))
    assert worker.step()
    assert not worker.run_task(task_id)
    assert runs == []
    service.maintenance.lift()
    assert worker.step()
    assert runs == [task_id]


def test_each_consumer_deposits_again_only_its_own_kind(
    installation: Installation, queue: TaskQueue, service: Service
) -> None:
    # #953: a restoration left queued is deposited again by its service alone, in its stream; in
    # maintenance, the service deposits again the restoration that holds it, which the database
    # may no longer hold, and the worker deposits nothing.
    restoring = written_task(installation.database, "restore", "queued")
    syncing = written_task(installation.database, "identity_sync", "queued")
    worker = Worker(installation.database, queue, {}, "worker-test", Timing(0, 0.1))
    worker.redeposit()
    service.restorer.redeposit()
    assert queue.waiting() == {syncing}
    assert service.restorer.queue.waiting() == {restoring}
    queue.client.delete(queue.stream, service.restorer.queue.stream)
    held = uuid4()
    service.maintenance.hold(Restoring(held, {}, None, "request-3f6a", 1))
    worker.redeposit()
    service.restorer.redeposit()
    assert not queue.client.exists(queue.stream)
    assert service.restorer.queue.waiting() == {held}


def test_a_restoration_waits_for_the_run_of_a_task_the_worker_started_before(
    installation: Installation,
) -> None:
    # The worker runs nothing once it reads the maintenance, but a task it started before goes on:
    # the restoration waits for the lock of its run before it keeps anything.
    running = written_task(installation.database, "identity_sync", "running")
    owner = create_database_engine(installation.owner["waterfall"])
    released: list[float] = []

    def run_for_a_while() -> None:
        with held_run(installation.database, running):
            started.set()
            time.sleep(0.5)
            released.append(time.monotonic())

    started = threading.Event()
    worker = threading.Thread(target=run_for_a_while)
    worker.start()
    started.wait()
    await_runs(owner, uuid4())
    waited = time.monotonic()
    worker.join()
    owner.dispose()
    assert released
    assert waited >= released[0]


def test_the_realm_applied_again_is_asked_in_a_folder_and_its_answer_read(tmp_path: Path) -> None:
    # #955: a request written whole, then renamed; the answer of keycloak-realm read and removed;
    # a failure, or no answer in time, fails the restoration.
    def answer(outcome: str) -> None:
        while not (tmp_path / "asked.request").exists():
            time.sleep(0.01)
        (tmp_path / "asked.request").unlink()
        (tmp_path / f"asked.{outcome}").write_text("")

    (tmp_path / "asked.failed").write_text("")
    requests = RealmRequests(tmp_path, patience=5, pause=0.01)
    answering = threading.Thread(target=answer, args=("done",))
    answering.start()
    requests.apply("asked")
    answering.join()
    assert not list(tmp_path.iterdir())
    answering = threading.Thread(target=answer, args=("failed",))
    answering.start()
    with pytest.raises(RealmNotAppliedError):
        requests.apply("asked")
    answering.join()
    ticks = iter([0.0, 0.0, 10.0])
    late = RealmRequests(tmp_path, patience=5, clock=lambda: next(ticks), sleep=lambda _: None)
    with pytest.raises(RealmNotAppliedError, match="did not answer"):
        late.apply("never")


def test_a_worker_that_cannot_read_the_maintenance_after_its_lock_runs_the_task(
    installation: Installation,
) -> None:
    # The maintenance read once the lock of a run is taken: a Redis out of reach says none, as for
    # the API, and the task runs.
    runs = Runs()
    unreached, _ = nowhere()
    task_id = written_task(installation.database, "identity_sync", "queued")
    worker = Worker(installation.database, unreached, {"identity_sync": runs}, "worker-test")
    try:
        assert worker.run_task(task_id)
    finally:
        unreached.close()
    assert runs == [task_id]
