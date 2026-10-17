# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A restoration replaces both databases by a backup, and keeps what the backup cannot hold.

Each test makes an installation of its own (``installations``), backs it up, then restores it by the
functions a restoration runs, whoever runs them: what is kept before the replacement
(``keep_for_restoration``), the replacement of each database by its dump, the migrations, and what
is written back after (``write_back_after_restoration``). The service that runs them is tried by
``test_restore_service``.
"""

import hashlib
import io
import json
import tarfile
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from installations import (
    Installation,
    Take,
    count,
    created,
    dropped,
    inscribe,
    new_restoration,
    restore,
    sha256,
    written_task,
)
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import func, select, text
from support import ContractClient, bearer, captured_logs
from task_handlers import REQUEST

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.backups.interface import (
    inscribe_restoration,
    keep_for_restoration,
    write_back_after_restoration,
)
from waterfall.core.backups.tables import Backup
from waterfall.core.users.interface import anonymize_account
from waterfall.core.users.tables import UserAccount
from waterfall.migrations.runner import alembic_config, downgrade, upgrade
from waterfall.platform.audit import Act, AuditEntry, AuditObject, Inscription, record
from waterfall.platform.database import create_database_engine, engine_url, utc_now
from waterfall.platform.errors import UnavailableError, UnprocessableError
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import TaskQueue
from waterfall.platform.restoration import begin_keeping, keep
from waterfall.platform.settings import ServiceSettings
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker import backup
from waterfall.worker.backup import DATABASES, MANIFEST, BackupTask, dump
from waterfall.worker.restore import RestoreError, errors_of, extracted, replace
from waterfall.worker.runner import Timing, Worker

BACKUPS = "/api/v1/backups"
# The revision of the schema of the installation, to which a restoration migrates.
HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()
# A database no server answers for.
UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:9/nowhere"


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
def test_both_databases_are_replaced_and_hold_what_they_held_at_the_backup_and_nothing_after(
    installation: Installation, take: Take, tmp_path: Path
) -> None:
    # « … la plateforme présente exactement les projets, révisions et comptes qu'elle contenait à
    # la date de la sauvegarde, et rien de postérieur … » : an account and a role made before the
    # backup are there after the restoration, one of each made after are not; and so for a row of
    # the database of the identity provider, which is restored too.
    held = role(installation.database, "Avant la sauvegarde")
    kept = account(installation.database, "Martin", "Claire", roles=(held,))
    backup_task = take()
    later = role(installation.database, "Après la sauvegarde")
    gone = account(installation.database, "Durand", "Paul", roles=(later,))
    provider = create_database_engine(installation.owner["identity_provider"])
    with provider.begin() as connection:
        connection.execute(text("INSERT INTO realm VALUES ('after-the-backup')"))
    restore(installation, backup_task, tmp_path)
    with provider.connect() as connection:
        realms = connection.scalars(text("SELECT id FROM realm ORDER BY id")).all()
    provider.dispose()
    assert realms == ["waterfall"]
    with installation.database.transaction() as session:
        roles = set(session.scalars(select(AccessRole.id).where(AccessRole.id.in_((held, later)))))
        accounts = set(
            session.scalars(select(UserAccount.id).where(UserAccount.id.in_((kept, gone))))
        )
    assert (roles, accounts) == ({held}, {kept})


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
    # inscription of the restoration, written after what was written back, comes after them.
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
    # The test inscribes the restoration itself, as what runs it will: it holds that the
    # inscription comes after those written back, not that what runs the restoration makes it.
    # It does not prove « … et la dernière inscription est la restauration elle-même. » of
    # WF-ADM-0160-A, which US-0440/L2b proves with the service that runs the restoration (#985).
    with logging_context(correlation_id=REQUEST), installation.database.transaction() as session:
        inscribe_restoration(session, AuditObject("backup", taken.id, None), None, utc_now())
    with installation.database.transaction() as session:
        latest = AuditEntry.occurred_at.desc(), AuditEntry.id.desc()
        last = session.scalars(select(AuditEntry).order_by(*latest).limit(1)).one()
    assert (last.action, last.object_kind, last.object_id) == ("restore", "backup", taken.id)


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_task_restored_pending_fails_and_the_backup_kept_keeps_its_state_and_its_archive(
    installation: Installation,
    take: Take,
    queue: TaskQueue,
    tmp_path: Path,
) -> None:
    # #892, #987: the dump holds the task of the backup running, and a task still queued. The
    # task of the backup is kept, succeeded, which wins over the state the dump holds: the backup
    # is listed, verified. The task queued fails with a code of its own; the restoration's is
    # spared. A step of the worker then runs nothing: the archive keeps its digest, and no backup
    # is added.
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
    assert (tasks[queued].status, tasks[queued].problem) == ("failed", interrupted)
    assert tasks[queued].finished_at is not None
    assert (tasks[backup_task].status, tasks[backup_task].problem) == ("succeeded", None)
    assert (tasks[backup_task].result or {}).get("verification") == "passed"
    assert tasks[restoration].status == "succeeded"


@pytest.mark.requirement("WF-SEC-0030-A")
def test_an_account_anonymised_after_the_backup_is_anonymised_again_once_it_is_restored(
    installation: Installation, take: Take, tmp_path: Path
) -> None:
    # « Après anonymisation d'un compte, aucune inscription ne porte plus son nom » (#988): the
    # backup holds the account named, and inscriptions that name it; it is anonymised after. The
    # restoration brings it back named, and writes back its anonymisation: it is anonymised again,
    # as of that date, and no inscription bears its name; the provider's account is to be removed.
    label = f"Martin-{uuid4().hex[:8]}"
    subject = f"subject-{uuid4()}"
    named = account(
        installation.database, label, "Claire", idp_subject=subject, state="deactivated"
    )
    audited = AuditObject("user", named, f"Claire {label}")
    with logging_context(correlation_id=REQUEST), installation.database.transaction() as session:
        record(session, Inscription("user_deactivate", None, audited, utc_now(), params={}))
    backup_task = take()
    at = utc_now()
    with logging_context(correlation_id=REQUEST), installation.database.transaction() as session:
        anonymize_account(session, named, 0, Act(None, at))
    subjects: list[str] = []
    restore(installation, backup_task, tmp_path, subjects)
    assert subjects == [subject]
    with installation.database.transaction() as session:
        row = session.get_one(UserAccount, named)
        labels = session.scalars(
            select(AuditEntry.object_label).where(AuditEntry.object_label.is_not(None))
        ).all()
    assert (row.anonymized_at, row.last_name, row.email, row.state) == (
        at,
        None,
        None,
        "deactivated",
    )
    assert not [found for found in labels if found and label in found]
    assert count(installation.database, AuditEntry.action == "user_anonymize") == 1


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_keeping_another_restoration_left_is_taken_over_and_its_task_fails(
    installation: Installation, take: Take, tmp_path: Path
) -> None:
    # #985: a restoration kept, then never wrote back — its replacement failed for good. Another
    # one finds what it kept: it takes it over, with its own task, and writes it back; the task of
    # the first, kept running, fails, and an inscription made after the backup is there once.
    backup_task = take()
    after = inscribe(installation.database, "Après la sauvegarde")
    first = new_restoration(installation)
    owner = create_database_engine(installation.owner["waterfall"])
    with owner.begin() as connection:
        keep_for_restoration(connection, first)
    owner.dispose()
    second = restore(installation, backup_task, tmp_path)
    with installation.database.transaction() as session:
        tasks = {row.id: row for row in session.scalars(select(BackgroundTask))}
    assert tasks[first].status == "failed"
    assert (tasks[first].problem or {}).get("code") == "TASK_INTERRUPTED_BY_RESTORE"
    assert tasks[second].status == "succeeded"
    assert count(installation.database, AuditEntry.id == after) == 1


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_backup_of_an_earlier_revision_is_migrated_before_the_role_of_the_service_gets_its_rights(
    installation: Installation,
    take: Take,
    backups_api: ContractClient,
    realm: TestRealm,
    tmp_path: Path,
) -> None:
    # The backup is taken at 0012, which lacks the reports of the readings of the accounts (0013);
    # the installation is then brought to the head. The restoration keeps, replaces, migrates, and
    # only then writes back: the rights kept name that table, which the migrations make again.
    subject = f"subject-{uuid4()}"
    held = role(installation.database, "Sauvegardes", permissions=("backups.read",))
    account(installation.database, "Martin", "Claire", roles=(held,), idp_subject=subject)
    owner = create_database_engine(installation.owner["waterfall"])
    downgrade(owner, "0012")
    take()
    upgrade(owner)
    with installation.database.transaction() as session:
        backup_task, revision = session.execute(
            select(Backup.task_id, Backup.schema_revision)
        ).one()
    assert revision == "0012"
    restore(installation, backup_task, tmp_path)
    service = f"{engine_url(installation.owner['waterfall']).database}_service"
    granted = "SELECT has_table_privilege(:service, 'identity_sync_report', 'SELECT, INSERT')"
    with owner.connect() as connection:
        migrated = connection.scalar(text("SELECT version_num FROM alembic_version"))
        assert connection.scalar(text(granted), {"service": service})
    owner.dispose()
    assert migrated == HEAD
    listed = backups_api.get(BACKUPS, headers=bearer(realm.token(subject, KEY)))
    assert listed.status_code == 200
    assert listed.json()["meta"]["total"] == 1


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


def test_a_compressed_archive_is_unreadable(tmp_path: Path) -> None:
    # A backup is an archive as the worker writes it, uncompressed: one compressed is not read,
    # whatever its manifest says — here a newer version, which it would refuse otherwise.
    manifest = tmp_path / MANIFEST
    manifest.write_text(json.dumps({"application_version": "999.0.0", "databases": []}))
    archive = tmp_path / "compressed.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(manifest, arcname=MANIFEST)
    with pytest.raises(UnprocessableError) as raised:
        extracted(archive, tmp_path)
    assert raised.value.code == "FILE_FORMAT_UNREADABLE"


def test_an_archive_whose_manifest_nests_too_deep_is_unreadable(tmp_path: Path) -> None:
    # A manifest of 60 000 opening brackets is no manifest: refused before anything changes.
    nested = tmp_path / MANIFEST
    nested.write_bytes(b"[" * 60_000)
    archive = tmp_path / "nested.tar"
    with tarfile.open(archive, "w") as tar:
        tar.add(nested, arcname=MANIFEST)
    with pytest.raises(UnprocessableError) as raised:
        extracted(archive, tmp_path)
    assert raised.value.code == "FILE_FORMAT_UNREADABLE"


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
    refused = 'new row for relation "..."'
    assert failed["said"] == [
        f'pg_restore: error: COPY failed for table "realm": ERROR:  {refused}'
    ]
    assert marker not in logs.text


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_value_the_server_quotes_is_masked_whole_whatever_it_holds_and_its_language() -> None:
    # « Une recherche des secrets et des jetons connus dans les journaux ne les trouve pas. » A
    # value may hold a quotation mark or a line break that cuts it — splitlines() cuts on \x1e as
    # on \n —, a few bytes may follow it, a server may quote with “ ” or „ “ after « ERROR: », or
    # with « » after « ERREUR: » : nothing of the value is kept, in any case.
    marker = "s3cr3t"
    realm = 'pg_restore: error: COPY failed for table "realm": ERROR:  malformed array literal: '
    query = "pg_restore: error: could not execute query: "
    account = 'pg_restore: error: COPY failed for table "account": ERROR:  invalid input syntax: '
    client = 'pg_restore: error: COPY failed for table "client": ERROR:  invalid input value '
    encoding = "pg_restore: error: could not execute query: ERROR:  invalid byte sequence for "
    said = "\n".join(
        [
            f'{realm}"{{"{marker} x"}}"',
            f"{query}ERREUR:  valeur « {marker} » refusée",
            f'{account}"ab"{marker}"',
            f"DETAIL:  Failing row contains ({marker}).",
            f'{realm}"{{{marker}\nx}}"',
            f'{realm}"{{{marker}\x1ex}}"',
            f"{client}\u201c{marker}\u201d refused",
            f"{client}\u201e{marker}\u201c refused",
            f'{encoding}encoding "UTF8": 0x{marker}',
        ]
    ).encode()
    kept = errors_of(said)
    assert kept == [
        f'{realm}"..."',
        f"{query}...",
        f'{account}"..."',
        f'{realm}"..."',
        f'{realm}"..."',
        f'{client}"..."',
        f'{client}"..."',
        f'{encoding}encoding "..."',
    ]
    assert marker not in "".join(kept)


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
