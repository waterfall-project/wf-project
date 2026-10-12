# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A restoration replaces both databases by a backup, and keeps what the backup cannot hold.

Each test makes an installation of its own on the PostgreSQL of the tests — a database of Waterfall,
migrated, and one that stands for the identity provider's —, backs it up as the worker does into a
bucket of the object storage of the tests, then restores it by the functions a restoration runs,
whoever runs them: what is kept before the replacement (``keep_for_restoration``), the replacement
of each database by its dump, the migrations, and what is written back after
(``write_back_after_restoration``). The databases are reached as their owner, the superuser of the
tests standing for it; the API and the worker reach them as the role of the service.
"""

import hashlib
import io
import json
import tarfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import ColumnElement, func, insert, select, text, update
from support import ContractClient, as_backup, bearer, captured_logs
from task_handlers import REQUEST, deposit

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.backups.interface import (
    inscribe_restoration,
    keep_for_restoration,
    write_back_after_restoration,
)
from waterfall.core.backups.tables import Backup
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import AuditEntry, AuditObject, Inscription, record
from waterfall.platform.database import Database, create_database_engine, engine_url, utc_now
from waterfall.platform.errors import UnavailableError, UnprocessableError
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import TaskQueue
from waterfall.platform.restoration import begin_keeping, keep
from waterfall.platform.settings import ServiceSettings
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker import backup
from waterfall.worker.backup import DATABASES, MANIFEST, BackupTask, dump
from waterfall.worker.restore import RestoreError, extracted, replace
from waterfall.worker.runner import Timing, Worker

BACKUPS = "/api/v1/backups"
# An account the inscriptions of these tests name, without a foreign key.
NAMED = UUID("01926f3a-7c00-7000-8000-0000000004c1")
# A database no server answers for.
UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:9/nowhere"


@dataclass(frozen=True, slots=True)
class Installation:
    """An installation of the tests: its databases as their owner and as the role of the backup.

    ``database`` is the database of Waterfall as the role of the service reaches it, which the API
    and the worker use; ``bucket``, the bucket of its backups.
    """

    owner: dict[str, str]
    backup: dict[str, str]
    database: Database
    bucket: Bucket


def created(server_address: str, name: str) -> str:
    """Create a database of the server, and give its address as the superuser reaches it."""
    server = create_database_engine(server_address).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    server.dispose()
    return engine_url(server_address).set(database=name).render_as_string(hide_password=False)


@pytest.fixture
def installation(
    database_url: str, backup_role: tuple[str, str], backups_bucket: Bucket
) -> Iterator[Installation]:
    """Make an installation of its own: Waterfall's database migrated, the provider's with a realm.

    The role of the service of that database is the one its migrations create; a role that signs
    in, member of it alone, stands for the API and the worker.
    """
    suffix = uuid4().hex
    waterfall = created(database_url, f"waterfall_test_restore_{suffix}")
    provider = created(database_url, f"waterfall_test_restore_idp_{suffix}")
    owner = create_database_engine(waterfall)
    upgrade(owner)
    owner.dispose()
    identity = create_database_engine(provider)
    with identity.begin() as connection:
        connection.execute(text("CREATE TABLE realm (id text PRIMARY KEY)"))
        connection.execute(text("INSERT INTO realm VALUES ('waterfall')"))
    identity.dispose()
    service = f"waterfall_test_restore_{suffix}_service"
    signing, password = f"waterfall_test_signing_{suffix}", uuid4().hex
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(
            text(f'CREATE ROLE "{signing}" LOGIN PASSWORD \'{password}\' IN ROLE "{service}"')
        )
    signed = engine_url(waterfall).set(username=signing, password=password)
    database = Database(create_database_engine(signed.render_as_string(hide_password=False)))
    owners: dict[str, str] = dict(zip(DATABASES, (waterfall, provider), strict=True))
    yield Installation(
        owners,
        {name: as_backup(address, backup_role) for name, address in owners.items()},
        database,
        backups_bucket,
    )
    database.dispose()
    with server.connect() as connection:
        for address in owners.values():
            name = engine_url(address).database
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        connection.execute(text(f'DROP ROLE "{signing}"'))
        connection.execute(text(f'DROP ROLE "{service}"'))
    server.dispose()


def dropped(server_address: str, *addresses: str) -> None:
    """Drop databases of the server, the connections left to them closed."""
    server = create_database_engine(server_address).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        for address in addresses:
            name = engine_url(address).database
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    server.dispose()


type Take = Callable[[], UUID]


@pytest.fixture
def take(installation: Installation, queue: TaskQueue) -> Take:
    """Give a taker of backups: a backup deposited as a request does, then run by a worker."""
    worker = Worker(
        installation.database,
        queue,
        {"backup": BackupTask(installation.backup, installation.bucket)},
        "worker-restoration",
        Timing(0, 0.1),
    )
    queue.prepare()

    def backup_taken() -> UUID:
        task_id = deposit(installation.database, queue, "backup")
        assert worker.step()
        return task_id

    return backup_taken


def restore(installation: Installation, backup_task: UUID, folder: Path) -> UUID:
    """Restore the backup a task took, as a restoration does whoever runs it; give its task.

    The restoration is a task the API deposits (``startRestore``): its row is in the database it
    replaces, which keeps it, and spares it when the tasks restored pending fail; what runs the
    restoration then ends it.
    """
    restoration = new_restoration(installation)
    archive = folder / "restored.tar"
    installation.bucket.download(f"backup-{backup_task}.tar", archive)
    dumps = extracted(archive, folder)
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        keep_for_restoration(connection, restoration)
    for name in DATABASES:
        replace(name, dumps[name], installation.owner[name], folder)
    upgrade(owner)
    with owner.begin() as connection:
        write_back_after_restoration(connection, restoration, utc_now())
        spared = select(BackgroundTask.status).where(BackgroundTask.id == restoration)
        assert connection.scalar(spared) == "running"
        ended = {"status": "succeeded", "progress": 100, "finished_at": utc_now()}
        connection.execute(
            update(BackgroundTask).where(BackgroundTask.id == restoration).values(**ended)
        )
    owner.dispose()
    return restoration


def new_restoration(installation: Installation) -> UUID:
    """Write the task of a restoration, as ``startRestore`` does, without depositing it."""
    return written_task(installation.database, "restore", "running")


def written_task(database: Database, kind: str, status: str) -> UUID:
    """Write a task in a state, around the queue, and give its identifier."""
    task_id = uuid4()
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=task_id,
                kind=kind,
                status=status,
                progress=0,
                payload={},
                correlation_id=REQUEST,
                attempts=1 if status == "running" else 0,
                submitted_at=utc_now(),
                started_at=utc_now() if status == "running" else None,
            )
        )
    return task_id


def inscribe(database: Database, label: str) -> UUID:
    """Inscribe the update of an account by the platform, committed; give the inscription."""
    audited = AuditObject("user", NAMED, label)
    with logging_context(correlation_id=REQUEST), database.transaction() as session:
        return record(session, Inscription("user_update", None, audited, utc_now()))


def count(database: Database, *where: ColumnElement[bool]) -> int:
    """Count the inscriptions of the journal that match."""
    with database.transaction() as session:
        return session.scalar(select(func.count()).select_from(AuditEntry).where(*where)) or 0


def sha256(bucket: Bucket, key: str) -> str:
    """Give the digest of an object of the bucket."""
    content = bucket.client.get_object(Bucket=bucket.name, Key=key)["Body"].read()
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def backups_api(
    contract: OpenAPI,
    installation: Installation,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the API on the database of the installation, as the role of the service."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    services = Services(installation.database, keycloak, administration, queue, installation.bucket)
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.mark.requirement("WF-ADM-0160-A")
def test_two_backups_stay_listed_and_downloadable_once_the_first_is_restored(
    installation: Installation,
    take: Take,
    backups_api: ContractClient,
    realm: TestRealm,
    tmp_path: Path,
) -> None:
    # #893: the table of the backups is in the dump of the first, which lacks the second; it is
    # kept before the replacement and written back after, as the journal is. The API reads both
    # as the role of the service, whose rights the restoration gives back.
    subject = f"subject-{uuid4()}"
    held = role(installation.database, "Sauvegardes", permissions=("backups.read", "backups.write"))
    account(installation.database, "Martin", "Claire", roles=(held,), idp_subject=subject)
    headers = bearer(realm.token(subject, KEY))
    first, second = take(), take()
    before = backups_api.get(BACKUPS, headers=headers).json()["items"]
    restore(installation, first, tmp_path)
    listed = backups_api.get(BACKUPS, headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"] == before
    assert len(before) == 2
    for item, task_id in zip(listed.json()["items"], (second, first), strict=True):
        copied = backups_api.get(f"{BACKUPS}/{item['backup_id']}/content", headers=headers)
        assert copied.status_code == 200
        assert hashlib.sha256(copied.content).hexdigest() == sha256(
            installation.bucket, f"backup-{task_id}.tar"
        )


@pytest.mark.requirement("WF-ADM-0160-A")
def test_an_inscription_made_while_the_backup_ran_is_written_back_once_and_the_backup_is_inscribed(
    installation: Installation,
    take: Take,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # #894: the backup is dated before its dumps; an inscription made between the two is in the
    # dump and after the date. Written back by its identifier, it is there once; the inscription
    # of the backup, made after the dump, and one made after the backup, are there too; the
    # restoration, inscribed once done, is the last.
    during: list[UUID] = []
    reach = backup.reached

    def reached_while_backing_up(address: str) -> None:
        during.append(inscribe(installation.database, "Pendant la sauvegarde"))
        reach(address)

    monkeypatch.setattr(backup, "reached", reached_while_backing_up)
    backup_task = take()
    monkeypatch.undo()
    with installation.database.transaction() as session:
        taken = session.execute(select(Backup.id, Backup.taken_at)).one()
    (made_during,) = during
    after = inscribe(installation.database, "Après la sauvegarde")
    restore(installation, backup_task, tmp_path)
    assert count(installation.database, AuditEntry.id == made_during) == 1
    assert count(installation.database, AuditEntry.id == after) == 1
    with installation.database.transaction() as session:
        dated = session.scalar(select(AuditEntry.occurred_at).where(AuditEntry.id == made_during))
    assert dated is not None
    assert dated > taken.taken_at
    inscribed = (AuditEntry.action == "backup", AuditEntry.object_id == taken.id)
    assert count(installation.database, *inscribed) == 1
    # « … et la dernière inscription est la restauration elle-même. »
    with logging_context(correlation_id=REQUEST), installation.database.transaction() as session:
        inscribe_restoration(session, taken.id, None, utc_now())
    with installation.database.transaction() as session:
        latest = AuditEntry.occurred_at.desc(), AuditEntry.id.desc()
        last = session.scalars(select(AuditEntry).order_by(*latest).limit(1)).one()
    assert (last.action, last.object_kind, last.object_id) == ("restore", "backup", taken.id)


@pytest.mark.requirement("WF-ADM-0160-A")
def test_no_task_restored_queued_or_running_runs_again_and_the_archive_restored_is_unchanged(
    installation: Installation,
    take: Take,
    queue: TaskQueue,
    tmp_path: Path,
) -> None:
    # #892: the dump holds the task of the backup running, and a task still queued; restored, both
    # fail with a code of its own, the restoration's spared. A step of the worker then runs
    # nothing: the archive keeps its digest, and no backup is added.
    queued = written_task(installation.database, "identity_sync", "queued")
    backup_task = take()
    key = f"backup-{backup_task}.tar"
    digest = sha256(installation.bucket, key)
    restoration = restore(installation, backup_task, tmp_path)
    worker = Worker(
        installation.database,
        queue,
        {"backup": BackupTask(installation.backup, installation.bucket)},
        "worker-after-restoration",
        Timing(0, 0.1),
    )
    worker.redeposit()
    assert not worker.step()
    assert sha256(installation.bucket, key) == digest
    with installation.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Backup)) == 1
        tasks = {row.id: row for row in session.scalars(select(BackgroundTask))}
    interrupted = {"code": "TASK_INTERRUPTED_BY_RESTORE", "status": 409, "correlation_id": REQUEST}
    for task_id in (queued, backup_task):
        assert (tasks[task_id].status, tasks[task_id].problem) == ("failed", interrupted)
        assert tasks[task_id].finished_at is not None
    assert tasks[restoration].status == "succeeded"


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_restoration_taken_up_after_an_interruption_writes_back_what_it_kept_the_first_time(
    installation: Installation,
    take: Take,
    tmp_path: Path,
) -> None:
    # Interrupted once the database of Waterfall is replaced, a restoration starts again from the
    # beginning; it keeps nothing again from a database half replaced, and writes back what it
    # kept the first time: an inscription made after the backup, there once.
    backup_task = take()
    after = inscribe(installation.database, "Après la sauvegarde")
    restoration = new_restoration(installation)
    archive = tmp_path / "restored.tar"
    installation.bucket.download(f"backup-{backup_task}.tar", archive)
    dumps = extracted(archive, tmp_path)
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        keep_for_restoration(connection, restoration)
    replace("waterfall", dumps["waterfall"], installation.owner["waterfall"], tmp_path)
    with owner.begin() as connection:
        keep_for_restoration(connection, restoration)
    for name in DATABASES:
        replace(name, dumps[name], installation.owner[name], tmp_path)
    upgrade(owner)
    with owner.begin() as connection:
        write_back_after_restoration(connection, restoration, utc_now() + timedelta(seconds=1))
        assert not connection.execute(
            text("SELECT EXISTS (SELECT FROM pg_namespace WHERE nspname = 'restoring')")
        ).scalar_one()
    owner.dispose()
    assert count(installation.database, AuditEntry.id == after) == 1
    with installation.database.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Backup)) == 1


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_keeping_cut_short_before_the_replacement_is_made_again_whole(
    installation: Installation,
    take: Take,
    backups_api: ContractClient,
    realm: TestRealm,
    tmp_path: Path,
) -> None:
    # A keeping committed on the way — the journal kept, nothing else — and cut short: the
    # database is not replaced yet, and the restoration taken up keeps all again. The backups,
    # an inscription made after the backup and the rights of the role of the service come back.
    subject = f"subject-{uuid4()}"
    held = role(installation.database, "Sauvegardes", permissions=("backups.read",))
    account(installation.database, "Martin", "Claire", roles=(held,), idp_subject=subject)
    backup_task = take()
    after = inscribe(installation.database, "Après la sauvegarde")
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        begin_keeping(connection)
        keep(connection, AuditEntry)
    owner.dispose()
    restore(installation, backup_task, tmp_path)
    assert count(installation.database, AuditEntry.id == after) == 1
    listed = backups_api.get(BACKUPS, headers=bearer(realm.token(subject, KEY)))
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1


def test_an_archive_of_a_newer_version_than_the_installation_is_refused_before_anything_changes(
    tmp_path: Path,
) -> None:
    # Proper to US-0440: a backup of a version newer than the installation is refused; the
    # archive is read, and refused, before a database is touched.
    manifest = tmp_path / MANIFEST
    manifest.write_text(json.dumps({"application_version": "999.0.0", "databases": []}))
    archive = tmp_path / "newer.tar"
    with tarfile.open(archive, "w") as tar:
        tar.add(manifest, arcname=MANIFEST)
    with pytest.raises(UnprocessableError) as raised:
        extracted(archive, tmp_path)
    assert (raised.value.code, dict(raised.value.params)) == (
        "BACKUP_FROM_NEWER_VERSION",
        {"backup_version": "999.0.0", "installed_version": __version__},
    )


def archive_of(folder: Path, databases: list[dict[str, str]], members: dict[str, bytes]) -> Path:
    """Write an archive of this version: a manifest that names ``databases``, and ``members``."""
    manifest = folder / MANIFEST
    manifest.write_text(json.dumps({"application_version": __version__, "databases": databases}))
    archive = folder / "archive.tar"
    with tarfile.open(archive, "w") as tar:
        tar.add(manifest, arcname=MANIFEST)
        for name, content in members.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            tar.addfile(member, io.BytesIO(content))
    return archive


NOT_A_DUMP = b"not a dump"


def entry(name: str, content: bytes = NOT_A_DUMP, sha256: str | None = None) -> dict[str, str]:
    """Name a dump in the manifest: its database, its file, its digest, that of ``content``."""
    given = hashlib.sha256(content).hexdigest() if sha256 is None else sha256
    return {"name": name, "file": f"{name}.dump", "sha256": given}


@pytest.mark.parametrize(
    ("databases", "members"),
    [
        ([entry("waterfall", sha256="0" * 64), entry("identity_provider")], ["waterfall"]),
        ([entry("waterfall"), entry("identity_provider")], ["identity_provider"]),
        ([entry("waterfall")], ["waterfall"]),
        ([entry("waterfall"), entry("identity_provider")], ["waterfall", "identity_provider"]),
    ],
    ids=["digest", "member", "databases", "unlisted"],
)
def test_an_archive_that_does_not_read_back_whole_is_refused_before_anything_changes(
    databases: list[dict[str, str]], members: list[str], tmp_path: Path
) -> None:
    # Proper to US-0440: a dump unlike its digest, one the archive lacks, a database of the
    # platform the manifest does not name, a dump pg_restore does not list: the archive is
    # unreadable, refused as it is read, before a database is touched.
    archive = archive_of(tmp_path, databases, {f"{name}.dump": NOT_A_DUMP for name in members})
    with pytest.raises(UnprocessableError) as raised:
        extracted(archive, tmp_path)
    assert (raised.value.code, dict(raised.value.params)) == ("FILE_FORMAT_UNREADABLE", {})


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_dump_the_database_refuses_is_journaled_without_the_row_it_refused(
    database_url: str, tmp_path: Path
) -> None:
    # « Une recherche des secrets et des jetons connus dans les journaux ne les trouve pas. » The
    # dump of the provider holds the secrets of its clients and the digests of its passwords; the
    # database refuses a row of it — by a check that only the source admits —, and pg_restore
    # quotes that row after its error. The journal gets the error, without the row.
    marker = f"marker-{uuid4().hex}"
    source = created(database_url, f"waterfall_test_refused_{uuid4().hex}")
    target = created(database_url, f"waterfall_test_refusing_{uuid4().hex}")
    admitted = "coalesce(current_setting('waterfall.admitted', true), '') = 'yes'"
    owner = create_database_engine(source)
    with owner.begin() as connection:
        name = engine_url(source).database
        connection.execute(text(f"ALTER DATABASE \"{name}\" SET waterfall.admitted = 'yes'"))
    owner.dispose()
    owner = create_database_engine(source)
    with owner.begin() as connection:
        connection.execute(
            text(f"CREATE TABLE realm (id text PRIMARY KEY, secret text CHECK ({admitted}))")
        )
        connection.execute(
            text("INSERT INTO realm VALUES ('waterfall', :marker)"), {"marker": marker}
        )
    owner.dispose()
    try:
        dumped = dump("identity_provider", source, tmp_path)
        with captured_logs() as logs, pytest.raises(RestoreError):
            replace("identity_provider", dumped.path, target, tmp_path)
    finally:
        dropped(database_url, source, target)
    (failed,) = logs.named("restore.replace_failed")
    refused = 'new row for relation "..." violates check constraint "..."'
    assert failed["said"] == [
        f'pg_restore: error: COPY failed for table "realm": ERROR:  {refused}'
    ]
    assert marker not in logs.text


def test_a_database_the_restoration_cannot_reach_is_unavailable_and_journaled_as_the_restoration(
    tmp_path: Path,
) -> None:
    # #907, for the restoration: a database that does not answer is a component out of reach
    # (503), which the journal names as the restoration's, not as a backup's.
    dumped = tmp_path / "unread.dump"
    dumped.write_bytes(b"")
    with captured_logs() as logs, pytest.raises(UnavailableError) as raised:
        replace("waterfall", dumped, UNREACHABLE, tmp_path)
    assert (raised.value.code, dict(raised.value.params)) == (
        "COMPONENT_UNAVAILABLE",
        {"component": "database"},
    )
    assert len(logs.named("restore.database_unreached")) == 1
    assert logs.named("backup.database_unreached") == []
