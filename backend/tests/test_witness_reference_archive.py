# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference set kept as a backup, and restored on a fresh platform (US-2950/L2b, #4114).

The shape is played on a short set — the witness, its reference, and a month of the history of
PRJ-001 —, as the tests of US-2950/L2 play three months: the command checks the set, deposits a
backup as the schedule does, which a worker takes, and keeps its archive and its manifest in a
folder; the archive is restored twice, each time on a fresh platform — a database of Waterfall
freshly migrated, an empty one for the identity provider —, which then holds the set whole, as
``check-reference`` reads it, by the role of its service. The full set is kept and restored on the
service platform, out of the fast tier (``make service-reference-backup``,
``make service-reference-restore``).
"""

import io
import json
import os
import tarfile
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest
from backup_rows import Row, days, recorded
from backup_support import stand_in_realm
from installations import created, dropped
from pydantic import SecretStr
from sqlalchemy import delete, func, select, text
from support import WITNESS, as_backup
from test_backup_rotation import set_retention
from test_backup_schedule_restoration import LYON, set_schedule
from test_witness_reference import identifying, settings
from test_witness_reference_history import described, short

from waterfall import __version__
from waterfall.core.backups.interface import (
    NO_BACKUP_RUNNING,
    ExternalCopy,
    backup_to_test,
    last_scheduled_outcome,
)
from waterfall.core.backups.tables import Backup
from waterfall.core.projects.tables import Project
from waterfall.migrations.runner import upgrade
from waterfall.platform.database import Database, create_database_engine, engine_url
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ReferenceBackupSettings, ReferenceRestoreSettings
from waterfall.platform.tasks import BackgroundTask
from waterfall.restore.trial import manifest_of
from waterfall.witness import reference_check, reference_load
from waterfall.witness.main import main
from waterfall.witness.reference_archive import (
    ARCHIVE,
    MANIFEST,
    Waiting,
    archive_name,
    backup_reference,
    ended,
    kept,
    restore_reference,
)
from waterfall.witness.reference_draw import SEED
from waterfall.witness.reference_history import COST_LINES, MARKED, History
from waterfall.worker.backup import BackupTask
from waterfall.worker.inventory import inventory_of
from waterfall.worker.runner import Timing, Worker, end, failure
from waterfall.worker.schedule import deposit_backup

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from support import Logs

    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.storage import Bucket

STORY = "US-2950"
# The projects of the portfolio of the short set: the witness's alone.
WANTED = 8
# The people of the realm of the source.
PEOPLE = 3
# The correlation the commands of a test deposit under.
CORRELATION = "reference-archive"


@dataclass(frozen=True, slots=True)
class Source:
    """The platform the set is loaded on, and backed up: the witness of the test, and its reach."""

    witness: Database
    owner_url: str
    service_url: str
    server: str
    role: tuple[str, str]
    queue: TaskQueue
    bucket: Bucket
    redis_url: str

    def settings(self) -> ReferenceBackupSettings:
        """Give the settings of ``backup-reference`` on it."""
        storage = urlsplit(os.environ["WATERFALL_TEST_STORAGE_URL"])
        return ReferenceBackupSettings(
            database_url=SecretStr(self.service_url),
            witness_path=str(WITNESS),
            redis_url=SecretStr(self.redis_url),
            storage_address=f"{storage.scheme}://{storage.hostname}:{storage.port}",
            storage_access_key=storage.username or "",
            storage_secret=SecretStr(storage.password or ""),
            backups_bucket=self.bucket.name,
        )

    def worker(self, provider: str) -> Worker:
        """Give its worker, which takes its backups as the platform's does, ``provider`` dumped."""
        taking = BackupTask(
            {
                "waterfall": as_backup(self.owner_url, self.role),
                "identity_provider": as_backup(provider, self.role),
            },
            self.bucket,
        )
        self.queue.prepare()
        handlers = {"backup": taking}
        return Worker(self.witness, self.queue, handlers, "worker-reference", Timing(0, 0.1))


@pytest.fixture
def source(witness: Database, request: pytest.FixtureRequest) -> Source:
    """Give the witness of the test as the platform the set is kept from."""
    value = request.getfixturevalue
    return Source(
        witness,
        value("database_url"),
        value("service_database_url"),
        value("process_database_url"),
        value("backup_role"),
        value("platform_queue"),
        value("backups_bucket"),
        value("redis_url"),
    )


@contextmanager
def provider_of(server: str) -> Generator[str]:
    """Make the database of the identity provider of the source, its realm and its people."""
    address = created(server, f"waterfall_test_reference_idp_{uuid4().hex}")
    engine = create_database_engine(address)
    with engine.begin() as connection:
        stand_in_realm(connection, PEOPLE)
    engine.dispose()
    try:
        yield address
    finally:
        dropped(server, address)


@contextmanager
def fresh_platform(server: str) -> Generator[tuple[ReferenceRestoreSettings, Database]]:
    """Make a fresh platform: Waterfall's database migrated, the provider's empty.

    Gives the settings of ``restore-reference``, as its owners, and the database of Waterfall as
    the role of its service reaches it, by a role that signs in, member of it alone.
    """
    suffix = uuid4().hex
    waterfall = created(server, f"waterfall_test_fresh_{suffix}")
    provider = created(server, f"waterfall_test_fresh_idp_{suffix}")
    owner = create_database_engine(waterfall)
    upgrade(owner)
    owner.dispose()
    service, signing, password = f"waterfall_test_fresh_{suffix}_service", f"fresh_{suffix}", suffix
    root = create_database_engine(server).execution_options(isolation_level="AUTOCOMMIT")
    with root.connect() as connection:
        connection.execute(
            text(f'CREATE ROLE "{signing}" LOGIN PASSWORD \'{password}\' IN ROLE "{service}"')
        )
    signed = engine_url(waterfall).set(username=signing, password=password)
    database = Database(create_database_engine(signed.render_as_string(hide_password=False)))
    settings = ReferenceRestoreSettings(
        database_url=SecretStr(waterfall), keycloak_database_url=SecretStr(provider)
    )
    try:
        yield settings, database
    finally:
        database.dispose()
        dropped(server, waterfall, provider)
        with root.connect() as connection:
            connection.execute(text(f'DROP ROLE "{signing}"'))
            connection.execute(text(f'DROP ROLE "{service}"'))
        root.dispose()


def stepping(worker: Worker) -> Waiting:
    """Wait for a backup by running the worker of the source, a step for each pause."""

    def step(_pause: float) -> None:
        worker.step()

    return Waiting(sleep=step)


def restored_once(
    source: Source, archive: Path, history: History, task_id: UUID
) -> reference_check.Volumes:
    """Restore ``archive`` on a fresh platform, check what it holds; give the volumes of the set.

    The source's backups are not listed, and the backup the dump caught running — ``task_id`` — is
    forgotten, rather than be run again by the worker of the restored platform (#892), or said
    failed: the restored platform has scheduled no backup yet.
    """
    with fresh_platform(source.server) as (restoring, restored):
        assert restore_reference(restoring, archive) == 0
        with restored.transaction() as session:
            report = reference_check.check(session, described(), WANTED, history)
            listed = session.scalars(select(Backup)).all()
            caught = session.get(BackgroundTask, task_id)
            outcome = last_scheduled_outcome(session)
        assert report.faults == []
        assert identifying(restored) == identifying(source.witness)
    assert listed == []
    assert caught is None
    assert outcome is None
    return report.held


@pytest.mark.heavy
@pytest.mark.requirement("WF-QUA-0040-A")
@pytest.mark.story(STORY)
def test_the_set_kept_as_a_backup_is_restored_twice_on_a_fresh_platform_and_found_whole(
    source: Source, tmp_path: Path, logs: Logs
) -> None:
    # Propre à l'US : « le jeu engendré une fois par version est gardé en sauvegarde et restauré par
    # ses consommateurs » : the set, loaded once on the source, is backed up by the platform itself,
    # its archive kept out of it; restored on a fresh platform, it is the set ``check-reference``
    # finds whole, as the role of the service reads it; restored again, the same counts.
    history = short(1, 100)
    witness = source.witness
    assert reference_load.load_reference(settings(source.service_url), WANTED, history) == 0
    with witness.transaction() as session:
        loaded = reference_check.check(session, described(), WANTED, history)
    assert loaded.faults == []
    # A backup pending holds the command back, as it holds the schedule back; once it has ended, the
    # set is backed up.
    with logging_context(correlation_id=CORRELATION):
        pending = deposit_backup(witness, source.queue)
    assert isinstance(pending, UUID)
    assert backup_reference(source.settings(), WANTED, history, tmp_path) == 1
    (held,) = logs.named("reference.backup_held_back")
    assert held["missing_condition"] == NO_BACKUP_RUNNING
    with witness.transaction() as session:
        end(session, pending, problem=failure("INTERNAL_ERROR", 500, CORRELATION))
    # A scheduled backup older than the set, under a retention of one: the backup of the set is a
    # scheduled one, and turns the list as any (EP-13, "Le jeu de données de référence").
    older = recorded(witness, days(1), Row(origin="scheduled"))
    set_retention(witness, 1)
    with provider_of(source.server) as provider:
        waiting = stepping(source.worker(provider))
        assert backup_reference(source.settings(), WANTED, history, tmp_path, waiting) == 0
    name = archive_name(WANTED, history)
    archive, manifest = tmp_path / f"{name}{ARCHIVE}", tmp_path / f"{name}{MANIFEST}"
    # The archive and its manifest, readable by their owner alone, and nothing else in the folder.
    assert sorted(each.name for each in tmp_path.iterdir()) == sorted([archive.name, manifest.name])
    assert {archive.stat().st_mode & 0o777, manifest.stat().st_mode & 0o777} == {0o600}
    said = json.loads(manifest.read_text(encoding="utf-8"))
    assert said == manifest_of(archive)
    inventory = inventory_of(said)
    assert inventory is not None
    assert (inventory.projects, inventory.marked_revisions, inventory.cost_lines) == (
        loaded.held.projects,
        loaded.held.marked_revisions,
        loaded.held.cost_lines,
    )
    assert inventory.identity_accounts == PEOPLE
    # The backup is the platform's own, as a scheduled one: no requester, verified. It has turned
    # the older one out of the list, and is the one the test of a restoration elects.
    with witness.transaction() as session:
        (backup,) = session.scalars(select(Backup)).all()
        task = session.get_one(BackgroundTask, backup.task_id)
        elected = backup_to_test(session)
    assert backup.id != older
    assert (backup.origin, backup.verification, task.requested_by) == ("scheduled", "passed", None)
    assert elected is not None
    assert elected.backup_id == backup.id
    (kept,) = logs.named("reference.kept")
    assert kept["archive"] == name
    counted = [restored_once(source, archive, history, backup.task_id) for _ in range(2)]
    assert counted == [loaded.held, loaded.held]


@pytest.mark.story(STORY)
def test_a_backup_is_deposited_without_a_requester_and_not_while_another_is_pending(
    database: Database, queue: TaskQueue
) -> None:
    # The backup of the set is the platform's own, as the schedule deposits it; and, as it does, it
    # waits for the backup or the restoration pending (``lock_backup_deposit``, #4369).
    with logging_context(correlation_id=CORRELATION):
        deposited = deposit_backup(database, queue)
        again = deposit_backup(database, queue)
    assert isinstance(deposited, UUID)
    with database.transaction() as session:
        task = session.get_one(BackgroundTask, deposited)
    assert (task.kind, task.status, task.requested_by) == ("backup", "queued", None)
    assert again == [NO_BACKUP_RUNNING]


@pytest.mark.story(STORY)
def test_a_platform_without_the_set_whole_is_not_backed_up(
    source: Source, tmp_path: Path, logs: Logs
) -> None:
    # The witness alone, the reference not loaded: the set is not whole — a real installation holds
    # not even the witness —, and nothing is deposited nor written.
    assert backup_reference(source.settings(), WANTED, History(0, 0), tmp_path) == 1
    (said,) = logs.named("reference.not_whole")
    assert said["faults"] > 0
    with source.witness.transaction() as session:
        backups = select(BackgroundTask).where(BackgroundTask.kind == "backup")
        assert session.scalars(backups).all() == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.story(STORY)
def test_a_platform_whose_schedule_copies_its_backups_out_is_not_backed_up(
    source: Source, tmp_path: Path, logs: Logs
) -> None:
    # The copy of a scheduled backup would carry the archive, the secrets of the realm in it, to its
    # location: refused before the set is read, nothing deposited nor written. Suspended, the copy
    # holds nothing back.
    copy = ExternalCopy(is_enabled=True, location=LYON, path="reference", retained_count=30)
    set_schedule(source.witness, 7, copy, None)
    assert backup_reference(source.settings(), WANTED, History(0, 0), tmp_path) == 1
    (said,) = logs.named("reference.external_copy_set")
    assert said["location"] == LYON
    assert logs.named("reference.not_whole") == []
    suspended = ExternalCopy(is_enabled=False, location=LYON, path="reference", retained_count=30)
    set_schedule(source.witness, 7, suspended, None)
    assert backup_reference(source.settings(), WANTED, History(0, 0), tmp_path) == 1
    assert len(logs.named("reference.not_whole")) == 1
    with source.witness.transaction() as session:
        backups = select(BackgroundTask).where(BackgroundTask.kind == "backup")
        assert session.scalars(backups).all() == []
    assert list(tmp_path.iterdir()) == []


def cut_short(bucket: Bucket, key: str, folder: Path) -> None:
    """Store under ``key`` an archive cut in its middle: its manifest whole, its dump not."""
    said = {"databases": [{"name": "waterfall", "file": "waterfall.dump", "sha256": "0"}]}
    whole = io.BytesIO()
    with tarfile.open(fileobj=whole, mode="w") as tar:
        members = (
            ("manifest.json", json.dumps(said).encode()),
            ("waterfall.dump", os.urandom(1 << 16)),
        )
        for name, data in members:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    stored = folder / "cut.tar"
    stored.write_bytes(whole.getvalue()[: len(whole.getvalue()) // 2])
    bucket.upload(key, stored)


@pytest.mark.story(STORY)
def test_an_archive_cut_short_gone_or_read_while_a_backup_is_pending_keeps_nothing(
    database: Database, queue: TaskQueue, backups_bucket: Bucket, tmp_path: Path, logs: Logs
) -> None:
    # The archive is read under the locks of a deposit, then verified again: an object cut short,
    # a backup the rotation has deleted, or a backup pending — whose rotation could delete it —
    # keep neither archive nor manifest.
    into, work = tmp_path / "into", tmp_path / "work"
    into.mkdir()
    work.mkdir()
    key = f"backup-{uuid4()}.tar"
    cut_short(backups_bucket, key, work)
    backup_id = recorded(database, days(2), Row(origin="scheduled", key=key))
    assert not kept(database, backups_bucket, backup_id, into / "cut")
    (unverified,) = logs.named("reference.archive_unverified")
    assert unverified["backup_id"] == str(backup_id)
    gone = new_id()
    assert not kept(database, backups_bucket, gone, into / "gone")
    (said,) = logs.named("reference.backup_gone")
    assert said["backup_id"] == str(gone)
    with logging_context(correlation_id=CORRELATION):
        assert isinstance(deposit_backup(database, queue), UUID)
    assert not kept(database, backups_bucket, backup_id, into / "pending")
    (held,) = logs.named("reference.archive_not_read")
    assert held["missing_condition"] == NO_BACKUP_RUNNING
    assert list(into.iterdir()) == []


@pytest.mark.story(STORY)
def test_a_backup_that_fails_or_does_not_end_in_time_keeps_nothing(
    database: Database, queue: TaskQueue, logs: Logs
) -> None:
    # The command waits for its backup a time, then says it did not end; a backup that failed, it
    # says at once. Either way, it keeps nothing.
    with logging_context(correlation_id=CORRELATION):
        deposited = deposit_backup(database, queue)
    assert isinstance(deposited, UUID)
    now = iter([0.0, 5.0])
    patience = Waiting(patience=1.0, clock=lambda: next(now), sleep=lambda _pause: None)
    assert ended(database, deposited, patience) is None
    (late,) = logs.named("reference.backup_not_ended")
    assert late["status"] == "queued"
    with database.transaction() as session:
        end(session, deposited, problem=failure("INTERNAL_ERROR", 500, CORRELATION))
    assert ended(database, deposited, Waiting()) is None
    (failed,) = logs.named("reference.backup_failed")
    assert failed["status"] == "failed"


@pytest.mark.story(STORY)
def test_an_archive_missing_unreadable_or_a_platform_not_fresh_is_refused_unchanged(
    process_database_url: str, tmp_path: Path, logs: Logs
) -> None:
    # Each refused before a database is touched: the fresh platform stays as migrated. Not fresh,
    # a platform whose Waterfall holds what its migrations do not write, or whose identity provider
    # has started.
    with fresh_platform(process_database_url) as (restoring, restored):
        assert restore_reference(restoring, tmp_path / "absent.tar") == 1
        (missing,) = logs.named("reference.archive_missing")
        assert missing["archive"] == "absent.tar"
        unreadable = tmp_path / "unreadable.tar"
        unreadable.write_bytes(b"not an archive")
        assert restore_reference(restoring, unreadable) == 1
        (refused,) = logs.named("reference.archive_refused")
        assert refused["code"] == "FILE_FORMAT_UNREADABLE"
        # Waterfall holds what its migrations do not write — a task, here —: not fresh.
        owner = Database(create_database_engine(restoring.database_url.get_secret_value()))
        recorded(owner, days(3))
        assert restore_reference(restoring, unreadable) == 1
        with owner.transaction() as session:
            session.execute(delete(Backup))
            session.execute(delete(BackgroundTask))
        owner.dispose()
        provider = create_database_engine(restoring.keycloak_database_url.get_secret_value())
        with provider.begin() as connection:
            stand_in_realm(connection)
        provider.dispose()
        assert restore_reference(restoring, unreadable) == 1
        reasons = [said["reason"] for said in logs.named("reference.platform_not_fresh")]
        assert reasons == [
            "the database of Waterfall holds more than its migrations",
            "the identity provider has started on this platform",
        ]
        with restored.transaction() as session:
            assert session.scalar(select(func.count()).select_from(Project)) == 0


@pytest.mark.story(STORY)
def test_the_commands_end_two_on_a_folder_or_a_setting_that_lacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    absent = tmp_path / "absent"
    assert main(["backup-reference", "--into", str(absent)]) == 2
    assert "is not a directory" in capsys.readouterr().err
    for name in ("WATERFALL_DATABASE_URL", "WATERFALL_KEYCLOAK_DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    assert main(["restore-reference", "--from", str(tmp_path)]) == 2
    assert "WATERFALL_DATABASE_URL" in capsys.readouterr().err
    assert main(["backup-reference", "--into", str(tmp_path)]) == 2
    assert "settings are not valid" in capsys.readouterr().err
    assert (
        archive_name(300, History()) == f"reference-{__version__}-{SEED}-300-{MARKED}-{COST_LINES}"
    )
