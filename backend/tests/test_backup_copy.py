# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A scheduled backup is copied to an external location, read back, and its copies turned.

The task ``backup_copy`` (US-2910/L3), which a scheduled backup verified deposits, run by a worker
on the queue of the test: the archive is read from the bucket of the backups of the test and
written on a folder of the test, standing for a mounted share, or on a bucket of its own on the
object storage of the tests, standing for the bucket of another site (``external_support``) — the
two natures of the contract by one interface. Its result is written on the row of the backup; a
refusal fails the task, which the gauge and the status screen read.
"""

import hashlib
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from backup_rows import Row, recorded
from external_support import (
    BUCKET,
    SHARE,
    bucket_elsewhere,
    declaration,
    declared,
    objects,
    unvalidated,
)
from fastapi.testclient import TestClient
from installations import Installation, Take, restore
from realm import KEY, TestRealm
from sqlalchemy import select, update
from support import ContractClient, bearer, captured_logs
from task_handlers import deposit, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.system import OUTCOMES
from waterfall.core.backups.interface import (
    FailedCopy,
    copies_beyond,
    deposit_copy,
    failed_copy,
    last_copy_outcome,
)
from waterfall.core.backups.tables import Backup, BackupSchedule
from waterfall.platform.external_locations import ExternalStore, S3Store, ShareStore, store_of
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.maintenance import Maintenance
from waterfall.worker.backup import BackupTask
from waterfall.worker.backup_copy import CopyTask
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import (
        DeclaredLocation,
        ExternalLocations,
        ServiceSettings,
    )
    from waterfall.platform.storage import Bucket
    from waterfall.platform.tasks import TaskHandler

pytestmark = pytest.mark.story("US-2910")

FOLDER = "waterfall/sauvegardes"
SCHEDULE = "/api/v1/backup-schedule"
READ = "backups.read"
WRITE = "backups.write"
ALERTS = Path(__file__).resolve().parents[2] / "deploy" / "compose" / "prometheus-alerts.yml"
CORRELATION = "test-backup-copy"
FOURTH = datetime(2026, 10, 4, 1, tzinfo=UTC)

type Located = Callable[..., ExternalLocations]
type Opened = Callable[[DeclaredLocation], ExternalStore]


@pytest.fixture
def elsewhere() -> Iterator[Bucket]:
    with bucket_elsewhere() as bucket:
        yield bucket


@pytest.fixture
def share(tmp_path: Path) -> Path:
    folder = tmp_path / "share"
    folder.mkdir()
    return folder


@pytest.fixture
def located(tmp_path: Path, share: Path, elsewhere: Bucket) -> Located:
    """Give a maker of the locations an installation declares, the share and the bucket."""

    def make(**changes: dict[str, Any]) -> ExternalLocations:
        return declared(tmp_path, declaration(share, elsewhere, **changes))

    return make


@dataclass(frozen=True, slots=True)
class Bench:
    """The database, the queue and the bucket of the backups of the test, and the locations."""

    database: Database
    queue: TaskQueue
    bucket: Bucket
    located: Located

    def worker(self, handlers: dict[str, TaskHandler]) -> Worker:
        self.queue.prepare()
        return Worker(self.database, self.queue, handlers, "worker-copy", Timing(0, 0.1))

    def copying(
        self, locations: ExternalLocations | None = None, opened: Opened = store_of
    ) -> Worker:
        """Give a worker that copies, to the locations given or to the share and the bucket."""
        declared_now = self.located() if locations is None else locations
        return self.worker({"backup_copy": CopyTask(self.bucket, declared_now, opened)})

    def archived(self, taken_at: datetime) -> UUID:
        """Record a scheduled backup verified, its archive in the bucket of the backups."""
        content = f"archive of {taken_at.isoformat()}".encode() * 64
        key = f"backup-copy-test-{uuid4().hex}.tar"
        self.bucket.client.put_object(Bucket=self.bucket.name, Key=key, Body=content)
        row = Row(origin="scheduled", size_bytes=len(content), key=key)
        return recorded(self.database, taken_at, row)

    def copied(self, running: Worker, backup_id: UUID) -> UUID:
        """Deposit the copy of a backup as the backup does, then let the worker run it."""
        with logging_context(correlation_id=CORRELATION), self.database.transaction() as session:
            task_id = deposit_copy(session, backup_id)
        assert task_id is not None
        running.redeposit()
        assert running.step()
        return task_id

    def copy_row(self, backup_id: UUID) -> tuple[Any, ...]:
        with self.database.transaction() as session:
            row = session.get_one(Backup, backup_id)
            return (row.last_copy_location, row.last_copy_path, row.last_copy_failure)

    def copy_set(self, location: str, retained_count: int = 30, platform_retained: int = 7) -> None:
        """Set the copy of the scheduled backups to a location's folder, enabled."""
        with self.database.transaction() as session:
            session.execute(
                update(BackupSchedule).values(
                    retained_count=platform_retained,
                    external_copy_is_enabled=True,
                    external_copy_location=location,
                    external_copy_path=FOLDER,
                    external_copy_retained_count=retained_count,
                )
            )


@pytest.fixture
def bench(database: Database, queue: TaskQueue, backups_bucket: Bucket, located: Located) -> Bench:
    return Bench(database, queue, backups_bucket, located)


def read_whole(store: ExternalStore, key: str) -> bytes:
    """Read a file a location holds, whatever its nature."""
    if isinstance(store, ShareStore):
        return (store.root / key).read_bytes()
    assert isinstance(store, S3Store)
    return store.client.get_object(Bucket=store.bucket, Key=key)["Body"].read()


def held(location: DeclaredLocation, key: str) -> bytes:
    store = store_of(location)
    try:
        return read_whole(store, key)
    finally:
        store.close()


def names_in(location: DeclaredLocation, folder: str) -> list[str]:
    store = store_of(location)
    try:
        return sorted(store.names(folder))
    finally:
        store.close()


def put_in(location: DeclaredLocation, key: str, content: bytes, folder: Path) -> None:
    source = folder / "put.bin"
    source.write_bytes(content)
    store = store_of(location)
    try:
        store.put(key, source)
    finally:
        store.close()


@pytest.mark.requirement("WF-ADM-0170-A")
@pytest.mark.parametrize("name", [BUCKET, SHARE])
def test_a_scheduled_backup_with_an_external_copy_is_found_on_the_location_set(
    bench: Bench, databases: dict[str, str], name: str
) -> None:
    # « Une sauvegarde planifiée avec copie externe se retrouve sur l'emplacement paramétré. » :
    # the platform backs itself up, the backup verified deposits its copy, the worker takes it at
    # its next sweep; the archive is on the location, in the folder set, under the date of the
    # backup, byte for byte; the row says the copy made, the gauge a copy succeeded — for an S3
    # bucket and for a mounted share alike.
    locations = bench.located()
    bench.copy_set(name)
    running = bench.worker(
        {
            "backup": BackupTask(databases, bench.bucket),
            "backup_copy": CopyTask(bench.bucket, locations),
        }
    )
    deposit(bench.database, bench.queue, "backup")
    assert running.step()
    running.redeposit()
    assert running.step()
    with bench.database.transaction() as session:
        backup = session.scalars(select(Backup)).one()
        outcome = last_copy_outcome(session)
    archive = bench.bucket.client.get_object(Bucket=bench.bucket.name, Key=backup.object_key)
    copy_name = f"waterfall-backup-{backup.taken_at:%Y%m%dT%H%M%SZ}.tar"
    location = locations.get(name)
    assert location is not None
    assert held(location, f"{FOLDER}/{copy_name}") == archive["Body"].read()
    assert bench.copy_row(backup.id) == (name, FOLDER, None)
    assert backup.last_copy_at is not None
    assert outcome is not None
    assert outcome.succeeded


@pytest.mark.parametrize("name", [BUCKET, SHARE])
def test_the_copies_of_the_folder_beyond_the_number_kept_go_the_oldest_first_and_nothing_else(
    bench: Bench, tmp_path: Path, name: str
) -> None:
    # Proper to US-2910: « la copie externe garde, sur l'emplacement, le nombre de copies
    # paramétré » (WF-EXP-0050). Three copies of earlier backups are in the folder, with a file of
    # another and a copy in another folder: two kept, the copy made and the latest before it; the
    # oldest two go, and nothing that is not a copy of this folder.
    locations = bench.located()
    location = locations.get(name)
    assert location is not None
    bench.copy_set(name, retained_count=2, platform_retained=1)
    for day in (1, 2, 3):
        put_in(location, f"{FOLDER}/waterfall-backup-202610{day:02}T010000Z.tar", b"old", tmp_path)
    put_in(location, f"{FOLDER}/notes.txt", b"not a copy", tmp_path)
    put_in(location, "ailleurs/waterfall-backup-20261001T010000Z.tar", b"elsewhere", tmp_path)
    task_id = bench.copied(bench.copying(locations), bench.archived(FOURTH))
    assert task(bench.database, task_id).status == "succeeded"
    assert (task(bench.database, task_id).result or {})["removed"] == 2
    assert names_in(location, FOLDER) == [
        "notes.txt",
        "waterfall-backup-20261003T010000Z.tar",
        "waterfall-backup-20261004T010000Z.tar",
    ]
    assert names_in(location, "ailleurs") == ["waterfall-backup-20261001T010000Z.tar"]


def test_the_rotation_of_the_copies_counts_only_the_copies_by_their_name() -> None:
    names = [
        "waterfall-backup-20261003T010000Z.tar",
        "waterfall-backup-20261001T010000Z.tar",
        "waterfall-backup-20261002T010000Z.tar",
        "waterfall-backup-2026.tar",
        "waterfall-backup-20261001T010000Z.tar.partial",
        "copie.tar",
    ]
    assert copies_beyond(names, 1) == [
        "waterfall-backup-20261001T010000Z.tar",
        "waterfall-backup-20261002T010000Z.tar",
    ]
    assert copies_beyond(names, 3) == []


@pytest.mark.requirement("WF-ADM-0170-A")
def test_a_copy_the_location_refuses_fails_its_task_and_says_why_on_the_row_and_to_the_alert(
    bench: Bench, elsewhere: Bucket
) -> None:
    # « Un échec planifié, de sauvegarde ou de copie, apparaît comme alerte sur l'écran d'état. » :
    # the key refused, the copy fails its task, the row says the location and the reason, and
    # what the gauge and the alert read says it — the backup, the location, the reason. The journal
    # names the location and the reason, never the secret refused, even unmasked.
    refused_key = f"not-the-secret-{uuid4().hex}"
    locations = bench.located(**{BUCKET: {"secret_key": refused_key}})
    bench.copy_set(BUCKET)
    backup_id = bench.archived(FOURTH)
    running = bench.copying(locations)
    with captured_logs() as logs:
        task_id = bench.copied(running, backup_id)
    ended = task(bench.database, task_id)
    assert ended.status == "failed"
    assert (ended.problem or {})["code"] == "INTERNAL_ERROR"
    assert bench.copy_row(backup_id) == (BUCKET, FOLDER, "access_denied")
    with bench.database.transaction() as session:
        outcome = OUTCOMES["scheduled_backup_copy"](session)
        failed = failed_copy(session)
    assert outcome is not None
    assert not outcome.succeeded
    assert failed == FailedCopy(backup_id, BUCKET, "access_denied")
    [refused] = logs.named("backup_copy.refused")
    assert (refused["location"], refused["failure"]) == (BUCKET, "access_denied")
    assert refused_key not in logs.text
    assert objects(elsewhere) == []


class Damaging:
    """A location that keeps what is written, and reads it back damaged."""

    def __init__(self, store: ExternalStore) -> None:
        self.store = store

    def put(self, key: str, path: Path) -> None:
        self.store.put(key, path)

    def read_back(self, key: str) -> tuple[int, str]:
        size, _ = self.store.read_back(key)
        return size, hashlib.sha256(b"damaged").hexdigest()

    def names(self, folder: str) -> list[str]:
        return self.store.names(folder)

    def remove(self, key: str) -> None:
        self.store.remove(key)

    def tidy(self) -> None:
        self.store.tidy()

    def close(self) -> None:
        self.store.close()


def damaging(location: DeclaredLocation) -> ExternalStore:
    return Damaging(store_of(location))


def test_a_copy_that_does_not_read_back_as_written_is_a_writing_refused(bench: Bench) -> None:
    # The copy is read back, its size and its digest against the archive's: one that differs is
    # ``write_failed``.
    bench.copy_set(SHARE)
    backup_id = bench.archived(FOURTH)
    task_id = bench.copied(bench.copying(opened=damaging), backup_id)
    assert task(bench.database, task_id).status == "failed"
    assert bench.copy_row(backup_id) == (SHARE, FOLDER, "write_failed")


def test_an_archive_the_bucket_gives_at_another_size_is_not_copied(
    bench: Bench, share: Path
) -> None:
    # The archive read must be the one its backup lists: at another size, the task fails, nothing
    # is written on the location, and the row says no copy, the location having refused nothing.
    bench.copy_set(SHARE)
    backup_id = bench.archived(FOURTH)
    with bench.database.transaction() as session:
        session.execute(update(Backup).where(Backup.id == backup_id).values(size_bytes=1))
    task_id = bench.copied(bench.copying(), backup_id)
    assert task(bench.database, task_id).status == "failed"
    assert bench.copy_row(backup_id) == (None, None, None)
    assert list(share.iterdir()) == []
    with bench.database.transaction() as session:
        assert failed_copy(session) == FailedCopy(backup_id, SHARE, None)


@pytest.mark.parametrize("changes", [{"region": "us east"}, {"address": "http://"}])
def test_a_copy_to_a_location_the_client_cannot_open_says_it_unreachable_on_its_row(
    bench: Bench, changes: dict[str, str]
) -> None:
    # A region or an address the S3 client refuses is a location out of reach: the task fails with
    # its reason on the row of the backup and for the alert, not with a bare trace.
    bench.copy_set(BUCKET)
    backup_id = bench.archived(FOURTH)
    locations = unvalidated(bench.located(), BUCKET, **changes)
    task_id = bench.copied(bench.copying(locations), backup_id)
    assert task(bench.database, task_id).status == "failed"
    assert bench.copy_row(backup_id) == (BUCKET, FOLDER, "location_unreachable")
    with bench.database.transaction() as session:
        assert failed_copy(session) == FailedCopy(backup_id, BUCKET, "location_unreachable")


def test_a_copy_to_a_location_no_longer_declared_is_one_it_cannot_reach(bench: Bench) -> None:
    bench.copy_set("secours-paris")
    backup_id = bench.archived(FOURTH)
    task_id = bench.copied(bench.copying(), backup_id)
    assert task(bench.database, task_id).status == "failed"
    assert bench.copy_row(backup_id) == ("secours-paris", FOLDER, "location_unreachable")


def test_a_copy_removed_or_suspended_since_its_deposit_is_not_made(
    bench: Bench, share: Path
) -> None:
    # The copy is made as the schedule sets it when it runs: suspended since, the task ends with
    # nothing copied and nothing written on the row; removed, the screen says no copy.
    bench.copy_set(SHARE)
    backup_id = bench.archived(FOURTH)
    with logging_context(correlation_id=CORRELATION), bench.database.transaction() as session:
        assert deposit_copy(session, backup_id) is not None
        session.execute(update(BackupSchedule).values(external_copy_is_enabled=False))
    running = bench.copying()
    running.redeposit()
    assert running.step()
    assert bench.copy_row(backup_id) == (None, None, None)
    assert list(share.iterdir()) == []
    with bench.database.transaction() as session:
        session.execute(
            update(BackupSchedule).values(
                external_copy_is_enabled=None,
                external_copy_location=None,
                external_copy_path=None,
                external_copy_retained_count=None,
            )
        )
        assert last_copy_outcome(session) is None


def test_each_outcome_the_metrics_give_is_one_a_rule_of_the_alerts_reads() -> None:
    # #4301: the rule ``scheduled_backup_copy_failed`` reads the gauge of the copy by the name of
    # its run; every name a rule reads is one the API gives, and every one it gives a rule reads.
    rules = ALERTS.read_text(encoding="utf-8")
    read = set(re.findall(r'waterfall_last_run_success\{run="([a-z_]+)"\}', rules))
    assert "scheduled_backup_copy" in read
    assert read == set(OUTCOMES)


@pytest.fixture
def located_services(
    installation: Installation,
    queue: TaskQueue,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    located: Located,
) -> Services:
    """Give the services of an installation that declares the share and the bucket."""
    return Services(
        installation.database,
        keycloak,
        KeycloakAdmin(keycloak, realm_settings),
        queue,
        installation.bucket,
        Maintenance.of(installation.database, queue),
        external_locations=located(),
    )


@pytest.fixture
def installation_located(contract: OpenAPI, located_services: Services) -> ContractClient:
    """Serve the API on an installation that declares the share and the bucket."""
    app = create_app(located_services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


def test_a_copy_set_by_the_route_is_read_back_by_the_route_after_a_restoration(
    installation: Installation,
    take: Take,
    installation_located: ContractClient,
    realm: TestRealm,
    tmp_path: Path,
) -> None:
    # #4354, #1743: on an installation that declares its locations, ``setBackupSchedule`` sets a
    # copy to one of them after a backup is taken; the backup is restored; ``getBackupSchedule``
    # reads the copy set, kept through the restoration, and not the backup's, which had none.
    subject = f"subject-{uuid4()}"
    holding = role(installation.database, "Sauvegardes", permissions=(READ, WRITE))
    account(installation.database, "Martin", "Claire", roles=(holding,), idp_subject=subject)
    headers = bearer(realm.token(subject, KEY))
    backup_task = take()
    read = installation_located.get(SCHEDULE, headers=headers).json()
    assert "external_copy" not in read
    copy = {"is_enabled": True, "location": BUCKET, "path": FOLDER, "retained_count": 30}
    written = installation_located.put(
        SCHEDULE, headers=headers, json=read | {"external_copy": copy}
    )
    assert written.status_code == 200, written.text
    restore(installation, backup_task, tmp_path)
    after = installation_located.get(SCHEDULE, headers=headers)
    assert after.status_code == 200
    assert after.json() == written.json()
    assert after.json()["external_copy"] == copy
