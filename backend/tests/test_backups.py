# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A backup is asked for, taken by the worker, listed, and copied out of the platform.

The worker dumps two real databases of the PostgreSQL of the tests — the database of the tests as
Waterfall's, and one made for the run as the identity provider's — into a bucket of its own on the
object storage of the tests. Each person is an account written around the service, with the roles a
test gives it, and calls the API with a token of the realm of test; every answer is checked against
the contract (``ContractClient``).
"""

import io
import json
import subprocess
import tarfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from backup_support import Corrupting, Run, worker_of
from fastapi.testclient import TestClient
from realm import KEY, TestRealm
from sqlalchemy import Engine, select, text, update
from sqlalchemy.exc import ProgrammingError
from support import ContractClient, bearer, captured_logs
from task_handlers import REQUEST, deposit, task

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.backups.interface import TakenBackup, add_backup, last_scheduled_outcome
from waterfall.core.backups.tables import BackupSchedule
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ServiceSettings, load_worker_settings
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker import backup as backup_module
from waterfall.worker.backup import MANIFEST, BackupTask, DumpError, connection, dump, verified

if TYPE_CHECKING:
    from pathlib import Path

    from openapi_core import OpenAPI
    from sqlalchemy.orm import Session

    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue

BACKUPS = "/api/v1/backups"
READ = "backups.read"
WRITE = "backups.write"
UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:9/nowhere"

type Person = Callable[..., tuple[UUID, dict[str, str]]]


@pytest.fixture
def taking(databases: dict[str, str], backups_bucket: Bucket) -> BackupTask:
    """Give the task that backs up the two databases of the test into the bucket of the test."""
    return BackupTask(databases, backups_bucket)


type ApiOn = Callable[[Bucket], ContractClient]


@pytest.fixture
def api_on(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ApiOn:
    """Give a maker of clients of the API that deposit in the queue of the test, on a bucket."""

    def client(bucket: Bucket) -> ContractClient:
        administration = KeycloakAdmin(keycloak, realm_settings)
        services = Services(database, keycloak, administration, queue, bucket)
        app = create_app(services)
        return ContractClient(TestClient(app, raise_server_exceptions=False), contract)

    return client


@pytest.fixture
def backups_api(api_on: ApiOn, backups_bucket: Bucket) -> ContractClient:
    """Give a client of the API on the queue and the bucket of the test."""
    return api_on(backups_bucket)


@pytest.fixture
def person(database: Database, realm: TestRealm) -> Person:
    """Give a maker of accounts, each holding a role of the permissions given, and its header."""

    def make(*permissions: str) -> tuple[UUID, dict[str, str]]:
        subject = f"subject-{uuid4()}"
        held = role(database, f"Rôle {uuid4().hex[:8]}", permissions=permissions)
        user_id = account(database, "Martin", uuid4().hex[:8], roles=(held,), idp_subject=subject)
        return user_id, bearer(realm.token(subject, KEY))

    return make


def stored(bucket: Bucket, key: str) -> bytes:
    """Read an object of the bucket of the test whole."""
    return bucket.client.get_object(Bucket=bucket.name, Key=key)["Body"].read()


def listed_contents(dump: bytes, folder: Path) -> str:
    """Give the table of contents pg_restore reads in a dump."""
    path = folder / "listed.dump"
    path.write_bytes(dump)
    return subprocess.run(
        ["/usr/bin/pg_restore", "--list", str(path)], capture_output=True, text=True, check=True
    ).stdout


@pytest.mark.requirement("WF-ADM-0150-A")
def test_a_backup_asked_for_is_listed_with_its_date_its_size_and_a_verification_passed(
    backups_api: ContractClient,
    database: Database,
    queue: TaskQueue,
    taking: BackupTask,
    person: Person,
) -> None:
    # « Une sauvegarde déclenchée apparaît dans la liste avec sa date, sa taille et une vérification
    # réussie. » : asked for, it is deposited for the worker and the request answers at once; the
    # worker takes it, and the list gives it, verified; the journal inscribes it at its date, by
    # whom asked for it, under the correlation of the request (WF-SEC-0030), and listAuditEvents
    # reads it back as the contract says: its parameters an empty object until the EPIC that
    # realises them.
    user_id, headers = person(READ, WRITE, "audit_log.read")
    asked = backups_api.post(BACKUPS, headers={**headers, "X-Correlation-ID": REQUEST})
    assert asked.status_code == 202
    ref = asked.json()
    assert (ref["kind"], ref["status"]) == ("backup", "queued")
    before = utc_now()
    assert worker_of(database, queue, taking).step()
    done = task(database, UUID(ref["task_id"]))
    assert (done.status, done.requested_by) == ("succeeded", user_id)
    listed = backups_api.get(BACKUPS, headers=headers)
    assert listed.status_code == 200
    (item,) = listed.json()["items"]
    assert listed.json()["meta"] == {"limit": 50, "offset": 0, "total": 1}
    assert item["verification"] == "passed"
    assert item["size_bytes"] > 0
    assert before.isoformat() <= item["taken_at"].replace("Z", "+00:00")
    assert (item["origin"], item["scope"], item["is_retained"]) == ("manual", "database", False)
    assert done.result == {"backup_id": item["backup_id"], "verification": "passed"}
    one = backups_api.get(f"{BACKUPS}/{item['backup_id']}", headers=headers)
    assert (one.status_code, one.json()) == (200, item)
    with database.transaction() as session:
        (inscribed,) = session.scalars(select(AuditEntry).where(AuditEntry.action == "backup"))
    assert (inscribed.object_kind, str(inscribed.object_id)) == ("backup", item["backup_id"])
    assert (inscribed.actor_user_id, inscribed.correlation_id) == (user_id, REQUEST)
    assert inscribed.occurred_at.isoformat() == item["taken_at"].replace("Z", "+00:00")
    assert inscribed.params == {}
    journal = backups_api.get("/api/v1/audit-events?actions=backup", headers=headers)
    assert journal.status_code == 200, journal.text
    (event,) = journal.json()["items"]
    assert (event["object"]["object_id"], event["actor"]["user_id"], event["params"]) == (
        item["backup_id"],
        str(user_id),
        {},
    )


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_backup_that_succeeded_gives_from_its_task_where_to_read_the_backup_it_took(
    backups_api: ContractClient,
    database: Database,
    queue: TaskQueue,
    taking: BackupTask,
    person: Person,
) -> None:
    # « … et l'utilisateur en voit l'aboutissement. » : queued, the task gives no result yet; ended,
    # its result is the backup it took, which the address it gives reads.
    _, headers = person(READ, WRITE)
    task_id = backups_api.post(BACKUPS, headers=headers).json()["task_id"]
    queued = backups_api.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert (queued.status_code, queued.json()["result_url"]) == (200, None)
    assert worker_of(database, queue, taking).step()
    ended = backups_api.get(f"/api/v1/tasks/{task_id}", headers=headers).json()
    (item,) = backups_api.get(BACKUPS, headers=headers).json()["items"]
    assert ended["status"] == "succeeded"
    assert ended["result_url"] == f"{BACKUPS}/{item['backup_id']}"
    assert backups_api.get(ended["result_url"], headers=headers).json() == item


@pytest.mark.requirement("WF-ADM-0150-A")
def test_a_backup_is_downloaded_whole_as_the_bucket_of_the_backups_keeps_it(
    backups_api: ContractClient,
    database: Database,
    queue: TaskQueue,
    taking: BackupTask,
    person: Person,
) -> None:
    # « Elle peut être téléchargée ou copiée vers un emplacement externe. » : by its download, the
    # archive streamed as the bucket keeps it; the copy to an external location is EP-13's.
    _, headers = person(READ, WRITE)
    asked = backups_api.post(BACKUPS, headers=headers)
    assert asked.status_code == 202
    assert worker_of(database, queue, taking).step()
    (item,) = backups_api.get(BACKUPS, headers=headers).json()["items"]
    copied = backups_api.get(f"{BACKUPS}/{item['backup_id']}/content", headers=headers)
    assert copied.status_code == 200
    assert copied.headers["content-type"] == "application/octet-stream"
    assert copied.headers["content-disposition"].startswith('attachment; filename="waterfall-')
    assert copied.content == stored(taking.bucket, f"backup-{asked.json()['task_id']}.tar")
    assert len(copied.content) == item["size_bytes"]
    assert copied.headers["content-length"] == str(item["size_bytes"])


@pytest.mark.requirement("WF-ADM-0150-A")
def test_a_backup_holds_both_databases_the_journal_included_in_the_bucket_of_the_backups(
    owner: Engine, run: Run, taking: BackupTask, tmp_path: Path
) -> None:
    # Proper to US-0440: a backup covers both databases, Waterfall's and the identity provider's,
    # each in a consistent state, the journal of audit saved with the first (WF-SEC-0030, #705);
    # it lives in the bucket of the backups (WF-DAT-0120). The manifest gives the date, the version,
    # the revision of the schema and the digest of each dump.
    task_id = run(taking)
    archived = stored(taking.bucket, f"backup-{task_id}.tar")
    with tarfile.open(fileobj=io.BytesIO(archived)) as tar:
        assert tar.getnames() == [MANIFEST, "waterfall.dump", "identity_provider.dump"]
        manifest: dict[str, Any] = json.loads(member(tar, MANIFEST))
        dumps = {name: member(tar, f"{name}.dump") for name in ("waterfall", "identity_provider")}
    with owner.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert (manifest["format"], manifest["application_version"]) == (1, __version__)
    assert manifest["schema_revision"] == revision
    assert [each["name"] for each in manifest["databases"]] == ["waterfall", "identity_provider"]
    for each in manifest["databases"]:
        assert each["size_bytes"] == len(dumps[each["name"]])
    waterfall = listed_contents(dumps["waterfall"], tmp_path)
    assert "TABLE DATA public audit_entry" in waterfall
    assert "TABLE DATA public user_account" in waterfall
    assert "TABLE DATA public realm" in listed_contents(dumps["identity_provider"], tmp_path)


def member(tar: tarfile.TarFile, name: str) -> bytes:
    """Read a member of an archive whole."""
    read = tar.extractfile(name)
    assert read is not None
    return read.read()


FAILED_VERIFICATION = {
    "code": "INTERNAL_ERROR",
    "status": 500,
    "correlation_id": REQUEST,
}


def failed_problem(database: Database, task_id: UUID) -> dict[str, Any]:
    """Read the problem of a task that failed, whole."""
    failed = task(database, task_id)
    assert failed.status == "failed"
    assert failed.result is None
    assert failed.problem is not None
    return dict(failed.problem)


@pytest.mark.requirement("WF-ADM-0170-A")
def test_an_archive_that_does_not_read_back_whole_fails_its_scheduled_task_and_stays_listed(
    database: Database,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Une archive qui échoue à sa vérification fait échouer sa tâche » (#4230, US-2910): read
    # back damaged, the backup is listed with its archive, ``failed``; its task fails by an
    # INTERNAL_ERROR under its correlation, and neither rotation nor copy follows.
    rotations: list[int] = []

    def rotate_spy(session: Session, retained_count: int) -> list[str]:
        del session, retained_count
        rotations.append(1)
        return []

    monkeypatch.setattr(backup_module, "rotate", rotate_spy)
    copy_set(database)
    corrupting = Corrupting(backups_bucket.client, backups_bucket.name)
    task_id = run(BackupTask(databases, corrupting))
    problem = failed_problem(database, task_id)
    assert {key: problem[key] for key in FAILED_VERIFICATION} == FAILED_VERIFICATION
    with database.transaction() as session:
        rows = session.execute(text("SELECT verification, origin, object_key FROM backup")).all()
        # One source of the failure: the task, which the gauge and the screen of the state read.
        outcome = last_scheduled_outcome(session)
    assert [tuple(row) for row in rows] == [("failed", "scheduled", f"backup-{task_id}.tar")]
    assert keys_of(backups_bucket, f"backup-{task_id}") == [f"backup-{task_id}.tar"]
    assert rotations == []
    # The copy is set and enabled: a backup verified would deposit it (the test below), this one
    # deposits none (US-2910/L3, #4100).
    assert copies_deposited(database) == []
    assert outcome is not None
    assert not outcome.succeeded


def copy_set(database: Database, *, is_enabled: bool = True) -> None:
    """Set the copy of the scheduled backups, to a location, enabled or suspended."""
    with database.transaction() as session:
        session.execute(
            update(BackupSchedule).values(
                external_copy_is_enabled=is_enabled,
                external_copy_location="secours-lyon",
                external_copy_path="waterfall/sauvegardes",
                external_copy_retained_count=30,
            )
        )


def copies_deposited(database: Database) -> list[dict[str, Any]]:
    """Give the payloads of the copies deposited, queued, by the platform."""
    with database.transaction() as session:
        return list(
            session.scalars(
                select(BackgroundTask.payload).where(
                    BackgroundTask.kind == "backup_copy",
                    BackgroundTask.status == "queued",
                    BackgroundTask.requested_by.is_(None),
                )
            )
        )


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_scheduled_backup_verified_deposits_its_copy_and_a_manual_one_none(
    database: Database,
    queue: TaskQueue,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
) -> None:
    # « la copie attend la vérification de la sauvegarde » (US-2910): a scheduled backup verified,
    # under a schedule whose copy is set and enabled, deposits the task of its copy, in its own
    # transaction; a manual backup, copied out by its download, deposits none, nor a scheduled one
    # whose copy is suspended.
    copy_set(database)
    task_id = run(BackupTask(databases, backups_bucket))
    backup_id = task(database, task_id).result or {}
    assert copies_deposited(database) == [{"backup_id": backup_id["backup_id"]}]
    asker = account(database, "Martin", uuid4().hex[:8])
    worker = worker_of(database, queue, BackupTask(databases, backups_bucket))
    deposit(database, queue, "backup", requested_by=asker)
    assert worker.step()
    assert len(copies_deposited(database)) == 1
    copy_set(database, is_enabled=False)
    run(BackupTask(databases, backups_bucket))
    assert len(copies_deposited(database)) == 1


@pytest.mark.requirement("WF-ADM-0170-A")
def test_an_archive_that_does_not_read_back_whole_fails_a_manual_backup_the_same_way(
    database: Database,
    queue: TaskQueue,
    databases: dict[str, str],
    backups_bucket: Bucket,
) -> None:
    # The same for a backup an account asked for: a row ``failed`` and its archive, the task failed,
    # the journal inscribing the backup by its author (#4230).
    asker = account(database, "Martin", uuid4().hex[:8])
    corrupting = Corrupting(backups_bucket.client, backups_bucket.name)
    worker = worker_of(database, queue, BackupTask(databases, corrupting))
    task_id = deposit(database, queue, "backup", requested_by=asker)
    assert worker.step()
    problem = failed_problem(database, task_id)
    assert {key: problem[key] for key in FAILED_VERIFICATION} == FAILED_VERIFICATION
    with database.transaction() as session:
        rows = session.execute(text("SELECT verification, origin FROM backup")).all()
        outcome = last_scheduled_outcome(session)
    assert [tuple(row) for row in rows] == [("failed", "manual")]
    assert keys_of(backups_bucket, f"backup-{task_id}") == [f"backup-{task_id}.tar"]
    assert outcome is None


DATABASE = "database"


def keys_of(bucket: Bucket, prefix: str = "") -> list[str]:
    """List the keys, under ``prefix``, of the objects the bucket holds, paginated."""
    pages = bucket.client.get_paginator("list_objects_v2").paginate(
        Bucket=bucket.name, Prefix=prefix
    )
    return [item.get("Key", "") for page in pages for item in page.get("Contents", [])]


def unavailable(component: str = "object_storage") -> UnavailableError:
    """Give the error of a component, which does not answer: the object storage unless told."""
    return UnavailableError("COMPONENT_UNAVAILABLE", {"component": component})


class Unreadable(Bucket):
    """A bucket that takes an archive and cannot give it back."""

    def download(self, key: str, path: Path) -> None:
        del key, path
        raise unavailable()


class Unremovable(Unreadable):
    """A bucket that cannot give an archive back, nor remove it."""

    def remove(self, key: str) -> None:
        del key
        raise unavailable()


@pytest.mark.requirement("WF-DAT-0120-A")
def test_an_archive_written_and_not_read_back_leaves_no_object_under_its_key(
    database: Database, run: Run, databases: dict[str, str], backups_bucket: Bucket
) -> None:
    # WF-DAT-0120: « Aucun autre fichier n'y est conservé » (#2242): the archive is written, then
    # the read-back fails; the task fails as it did, and nothing stays under the key.
    failing = Unreadable(backups_bucket.client, backups_bucket.name)
    task_id = run(BackupTask(databases, failing))
    failed = task(database, task_id)
    assert (failed.status, (failed.problem or {}).get("params")) == (
        "failed",
        {"component": "object_storage"},
    )
    assert keys_of(backups_bucket, f"backup-{task_id}") == []
    with database.transaction() as session:
        assert session.execute(text("SELECT count(*) FROM backup")).scalar_one() == 0


@pytest.mark.requirement("WF-DAT-0120-A")
def test_an_archive_written_and_not_recorded_leaves_no_object_under_its_key(
    database: Database,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # WF-DAT-0120 (#2242): the verification passed, the database refuses the backup.
    def refuse(*_: object) -> UUID:
        raise unavailable(DATABASE)

    monkeypatch.setattr(backup_module, "add_backup", refuse)
    task_id = run(BackupTask(databases, backups_bucket))
    failed = task(database, task_id)
    assert (failed.status, (failed.problem or {}).get("params")) == (
        "failed",
        {"component": "database"},
    )
    assert keys_of(backups_bucket, f"backup-{task_id}") == []


@pytest.mark.requirement("WF-DAT-0120-A")
def test_an_archive_whose_verification_raises_leaves_no_object_under_its_key(
    database: Database,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # WF-DAT-0120 (#2242): the verification itself raises, inside the guarded block.
    def raising(*_: object) -> None:
        raise unavailable()

    monkeypatch.setattr(backup_module, "verified", raising)
    task_id = run(BackupTask(databases, backups_bucket))
    failed = task(database, task_id)
    assert failed.status == "failed"
    assert keys_of(backups_bucket, f"backup-{task_id}") == []


@pytest.mark.requirement("WF-DAT-0120-A")
def test_a_removal_that_fails_is_logged_and_does_not_hide_the_fault_of_the_backup(
    database: Database, run: Run, databases: dict[str, str], backups_bucket: Bucket
) -> None:
    # WF-DAT-0120 (#2242): the archive cannot be removed either; the task fails on the fault that
    # came first, and the removal that failed is logged.
    failing = Unremovable(backups_bucket.client, backups_bucket.name)
    with captured_logs() as logs:
        task_id = run(BackupTask(databases, failing))
    failed = task(database, task_id)
    assert (failed.status, (failed.problem or {}).get("params")) == (
        "failed",
        {"component": "object_storage"},
    )
    (removal,) = logs.named("backup.archive_not_removed")
    assert removal["key"] == f"backup-{task_id}.tar"


def test_verification_refuses_an_archive_without_its_manifest_or_its_two_dumps(
    tmp_path: Path,
) -> None:
    dump = tmp_path / "waterfall.dump"
    dump.write_bytes(b"not a dump")
    for name, members in (("bare.tar", [dump]), ("absent.tar", [])):
        path = tmp_path / name
        with tarfile.open(path, "w") as tar:
            for each in members:
                tar.add(each, arcname=each.name)
        assert not verified(path, tmp_path)
    (tmp_path / "garbage.tar").write_bytes(b"\x00garbage")
    assert not verified(tmp_path / "garbage.tar", tmp_path)


@pytest.mark.parametrize("unreachable", ["waterfall", "identity_provider"])
def test_a_backup_of_a_database_out_of_reach_fails_and_records_nothing(
    database: Database,
    run: Run,
    databases: dict[str, str],
    backups_bucket: Bucket,
    unreachable: str,
) -> None:
    task_id = run(BackupTask({**databases, unreachable: UNREACHABLE}, backups_bucket))
    failed = task(database, task_id)
    assert (failed.status, failed.problem) == (
        "failed",
        {
            "code": "COMPONENT_UNAVAILABLE",
            "status": 503,
            "params": {"component": "database"},
            "correlation_id": REQUEST,
        },
    )
    with database.transaction() as session:
        assert session.execute(text("SELECT count(*) FROM backup")).scalar_one() == 0


def test_a_dump_whose_database_stops_answering_fails_as_the_database_unavailable(
    tmp_path: Path,
) -> None:
    # #907: the database answered before its dump, then stopped answering; pg_dump fails, and the
    # dump reaches the database again to tell an outage from an internal error.
    with pytest.raises(UnavailableError) as raised:
        dump("waterfall", UNREACHABLE, tmp_path)
    assert (raised.value.code, dict(raised.value.params)) == (
        "COMPONENT_UNAVAILABLE",
        {"component": "database"},
    )


def test_a_backup_the_object_storage_does_not_take_fails_as_its_storage_unavailable(
    database: Database, run: Run, taking: BackupTask
) -> None:
    nowhere = Bucket.connect("backups", "http://127.0.0.1:9", "us-east-1", "GK0", "secret")
    task_id = run(BackupTask(taking.databases, nowhere))
    failed = task(database, task_id)
    assert failed.status == "failed"
    assert failed.problem is not None
    assert failed.problem["params"] == {"component": "object_storage"}


def test_the_role_of_the_service_cannot_dump_the_database_which_the_role_of_the_backup_dumps(
    database: Database, run: Run, taking: BackupTask, service_database_url: str, tmp_path: Path
) -> None:
    # #701: the API and the worker connect as the role of the service, which holds only what the
    # tables grant it; a dump reads every table, and that role cannot. The role of the backup can.
    # The database answers: what fails is not a component out of reach but an internal error.
    with pytest.raises(DumpError):
        dump("waterfall", service_database_url, tmp_path)
    readable = taking.databases["waterfall"]
    assert dump("waterfall", readable, tmp_path).size_bytes > 0
    serving = {"waterfall": readable, "identity_provider": service_database_url}
    failed = task(database, run(BackupTask(serving, taking.bucket)))
    assert (failed.status, failed.problem) == (
        "failed",
        {"code": "INTERNAL_ERROR", "status": 500, "correlation_id": REQUEST},
    )
    with database.transaction() as session:
        assert session.execute(text("SELECT count(*) FROM backup")).scalar_one() == 0


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_entry SET action = action",
        "DELETE FROM audit_entry",
        "INSERT INTO backup DEFAULT VALUES",
        "ALTER TABLE audit_entry DISABLE TRIGGER ALL",
        "SET session_replication_role = replica",
    ],
    ids=["update", "delete", "insert", "trigger", "replica"],
)
def test_the_role_of_the_backup_dumps_both_databases_and_can_neither_write_nor_turn_a_trigger_off(
    databases: dict[str, str], owner: Engine, statement: str, tmp_path: Path
) -> None:
    # #895: the worker dumps the databases as a member of pg_read_all_data, never as the owner of
    # the tables nor as a superuser. « Une mise à jour ou une suppression exécutée directement en
    # base sur une inscription du journal est rejetée par la base. » : by this role too, which can
    # no more write a table, nor turn off the trigger that guards the journal, nor every trigger.
    with owner.connect() as connection:
        found = connection.execute(text("SELECT count(*) FROM audit_entry")).scalar_one()
    dumped = dump("waterfall", databases["waterfall"], tmp_path)
    assert "TABLE DATA public audit_entry" in listed_contents(dumped.path.read_bytes(), tmp_path)
    assert dump("identity_provider", databases["identity_provider"], tmp_path).size_bytes > 0
    backup = create_database_engine(databases["waterfall"])
    try:
        with backup.connect() as connection:
            with pytest.raises(ProgrammingError, match=r"permission denied|must be owner"):
                connection.execute(text(statement))
            connection.rollback()
            role = connection.execute(
                text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            ).one()
            assert tuple(role) == (False, False)
    finally:
        backup.dispose()
    with owner.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM audit_entry")).scalar_one() == found


def test_a_dump_reaches_its_database_by_its_whole_address_and_its_password_apart(
    tmp_path: Path,
) -> None:
    # The address of a database may say how to reach it — its encryption, its certificate, a socket
    # — in its query, which the dump keeps; its password, in the address or in its query, never goes
    # on a command line, which any listing of the processes shows, but by PGPASSWORD.
    service = tmp_path / "waterfall.service"
    query = "sslmode=disable&application_name=x"
    for address in (
        f"postgresql://owner:s3cret@db.example:5433/waterfall?{query}",
        f"postgresql://owner@db.example:5433/waterfall?{query}&password=s3cret",
    ):
        environment = connection(address, service)
        assert service.read_text(encoding="utf-8").splitlines() == [
            "[backup]",
            "host=db.example",
            "port=5433",
            "dbname=waterfall",
            "user=owner",
            "sslmode=disable",
            "application_name=x",
        ]
        assert (environment["PGSERVICEFILE"], environment["PGSERVICE"]) == (str(service), "backup")
        assert environment["PGPASSWORD"] == "s3cret"
    socket = "postgresql://owner@/waterfall?host=/tmp&host=/run/postgresql"
    environment = connection(socket, service)
    assert service.read_text(encoding="utf-8").splitlines() == [
        "[backup]",
        "dbname=waterfall",
        "user=owner",
        "host=/run/postgresql",
    ]
    assert "PGPASSWORD" not in environment


def test_the_worker_backs_up_as_the_role_of_the_backup_and_connects_as_the_service(
    platform_environment: dict[str, str],
) -> None:
    # #701, #895: the backup the worker runs dumps each database as the role of the backup, which
    # the settings name apart from the address the worker connects by.
    taking = BackupTask.of(load_worker_settings())
    assert taking.databases == {
        "waterfall": platform_environment["WATERFALL_BACKUP_DATABASE_URL"],
        "identity_provider": platform_environment["WATERFALL_KEYCLOAK_DATABASE_URL"],
    }
    assert platform_environment["WATERFALL_DATABASE_URL"] not in taking.databases.values()
    assert taking.bucket.name == "backups"


def backup_row(database: Database, queue: TaskQueue, key: str, *, days: int = 0) -> str:
    """Record a backup by its module, as the worker does, and give its identifier."""
    task_id = deposit(database, queue, "backup")
    taken_at = datetime(2026, 10, 1 + days, 1, 0, tzinfo=UTC)
    taken = TakenBackup(task_id, taken_at, 2048, key, __version__, "0010", is_verified=True)
    with logging_context(correlation_id=REQUEST), database.transaction() as session:
        return str(add_backup(session, taken, Act(None, taken_at)))


@pytest.mark.requirement("WF-ADM-0150-A")
def test_the_backups_are_listed_by_pages_the_latest_first(
    backups_api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    older = backup_row(database, queue, "older.tar")
    later = backup_row(database, queue, "later.tar", days=1)
    _, headers = person(READ)
    first = backups_api.get(f"{BACKUPS}?limit=1", headers=headers).json()
    assert ([item["backup_id"] for item in first["items"]], first["meta"]["total"]) == ([later], 2)
    second = backups_api.get(f"{BACKUPS}?limit=1&offset=1", headers=headers).json()
    assert [item["backup_id"] for item in second["items"]] == [older]
    beyond = backups_api.get(f"{BACKUPS}?offset=2", headers=headers).json()
    assert beyond["items"] == []


def test_each_backup_lists_the_commands_its_reader_may_exercise_with_what_they_lack(
    backups_api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # A command the permissions of the caller do not allow is not presented; one that the state of
    # the platform makes impossible for a while is presented unavailable, with the condition it
    # lacks (WF-IHM-0090, WF-ADM-0100). The task of the backup recorded stays queued: a backup
    # runs, and withholds the restoration alone.
    backup_id = backup_row(database, queue, "listed.tar")
    _, reader = person(READ)
    _, keeper = person(READ, WRITE, "platform_restore")
    [read] = backups_api.get(BACKUPS, headers=reader).json()["items"]
    assert read["available_commands"] == []
    expected: list[dict[str, Any]] = [
        {"command": "retain", "is_available": True, "missing_conditions": []},
        {"command": "download", "is_available": True, "missing_conditions": []},
        {"command": "restore", "is_available": False, "missing_conditions": ["no_backup_running"]},
    ]
    [kept] = backups_api.get(BACKUPS, headers=keeper).json()["items"]
    assert kept["available_commands"] == expected
    alone = backups_api.get(f"{BACKUPS}/{backup_id}", headers=keeper).json()
    assert alone["available_commands"] == expected


def test_a_backup_is_read_and_copied_only_under_the_permissions_of_the_backups(
    backups_api: ContractClient, database: Database, queue: TaskQueue, person: Person
) -> None:
    # Reading the list does not let the archive out of the platform: its copy asks for the
    # permission to change the backups besides (WF-ADM-0100); without the permission to read
    # them, a backup does not exist (WF-ADM-0110).
    backup_id = backup_row(database, queue, "kept.tar")
    _, reader = person(READ)
    _, nobody = person()
    content = f"{BACKUPS}/{backup_id}/content"
    forbidden = backups_api.get(content, headers=reader)
    assert (forbidden.status_code, forbidden.json()["params"]) == (
        403,
        {"missing_permission": WRITE},
    )
    for path in (f"{BACKUPS}/{backup_id}", content, BACKUPS):
        assert backups_api.get(path, headers=nobody).status_code == 404
    refused = backups_api.post(BACKUPS, headers=reader)
    assert refused.status_code == 403
    assert len(queue.waiting()) == 1


def test_a_backup_whose_archive_is_gone_or_out_of_reach_is_not_copied(
    backups_api: ContractClient, api_on: ApiOn, database: Database, queue: TaskQueue, person: Person
) -> None:
    backup_id = backup_row(database, queue, "gone.tar")
    _, headers = person(READ, WRITE)
    content = f"{BACKUPS}/{backup_id}/content"
    assert backups_api.get(content, headers=headers).status_code == 404
    assert backups_api.get(f"{BACKUPS}/{uuid4()}", headers=headers).status_code == 404
    nowhere = Bucket.connect("backups", "http://127.0.0.1:9", "us-east-1", "GK0", "secret")
    unavailable = api_on(nowhere).get(content, headers=headers)
    assert (unavailable.status_code, unavailable.json()["params"]) == (
        503,
        {"component": "object_storage"},
    )
