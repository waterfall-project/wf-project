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
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import ProgrammingError
from support import ContractClient, as_backup, bearer
from task_handlers import REQUEST, deposit, task

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.backups.interface import TakenBackup, add_backup
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import Database, create_database_engine, engine_url, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import TaskQueue
from waterfall.platform.settings import ServiceSettings, load_worker_settings
from waterfall.platform.storage import Bucket
from waterfall.worker.backup import MANIFEST, BackupTask, DumpError, connection, dump, verified
from waterfall.worker.runner import Timing, Worker

BACKUPS = "/api/v1/backups"
READ = "backups.read"
WRITE = "backups.write"
UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:9/nowhere"

type Person = Callable[..., tuple[UUID, dict[str, str]]]


@pytest.fixture(scope="session")
def provider_url(database_url: str) -> Iterator[str]:
    """Create, for this run, a database that stands for the identity provider's, with a realm."""
    name = f"waterfall_test_idp_{uuid4().hex}"
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = engine_url(database_url).set(database=name).render_as_string(hide_password=False)
    provider = create_database_engine(url)
    with provider.begin() as connection:
        connection.execute(text("CREATE TABLE realm (id text PRIMARY KEY)"))
        connection.execute(text("INSERT INTO realm VALUES ('waterfall')"))
    provider.dispose()
    yield url
    with server.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    server.dispose()


@pytest.fixture
def databases(database_url: str, provider_url: str, backup_role: tuple[str, str]) -> dict[str, str]:
    """Give the two databases of the test as the role of the backup reaches them, by backup name."""
    return {
        "waterfall": as_backup(database_url, backup_role),
        "identity_provider": as_backup(provider_url, backup_role),
    }


@pytest.fixture
def taking(databases: dict[str, str], backups_bucket: Bucket) -> BackupTask:
    """Give the task that backs up the two databases of the test into the bucket of the test."""
    return BackupTask(databases, backups_bucket)


def worker_of(database: Database, queue: TaskQueue, taking: BackupTask) -> Worker:
    """Give a worker of the queue of the test that runs the backups."""
    queue.prepare()
    return Worker(database, queue, {"backup": taking}, "worker-backup", Timing(0, 0.1))


type Run = Callable[[BackupTask], UUID]


@pytest.fixture
def run(database: Database, queue: TaskQueue) -> Run:
    """Give a runner: it deposits a backup the platform asks for, which a worker then takes."""

    def backup(taking: BackupTask) -> UUID:
        task_id = deposit(database, queue, "backup")
        assert worker_of(database, queue, taking).step()
        return task_id

    return backup


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


class Corrupting(Bucket):
    """A bucket that gives back every object with bytes of its middle overwritten."""

    def download(self, key: str, path: Path) -> None:
        super().download(key, path)
        damaged = bytearray(path.read_bytes())
        middle = len(damaged) // 2
        damaged[middle : middle + 16] = b"\xff" * 16
        path.write_bytes(bytes(damaged))


def test_an_archive_that_does_not_read_back_whole_is_listed_with_a_verification_failed(
    database: Database, run: Run, databases: dict[str, str], backups_bucket: Bucket
) -> None:
    # The verification is what tells a backup from a file one hopes to restore (WF-ADM-0150): read
    # back damaged, the backup is listed, and says it failed.
    corrupting = Corrupting(backups_bucket.client, backups_bucket.name)
    task_id = run(BackupTask(databases, corrupting))
    assert task(database, task_id).result is not None
    with database.transaction() as session:
        rows = session.execute(text("SELECT verification, origin FROM backup")).all()
    assert [tuple(row) for row in rows] == [("failed", "scheduled")]


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
