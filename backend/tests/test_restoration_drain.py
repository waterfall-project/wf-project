# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lock of the drain: no write admitted before the maintenance is lost, none after commits.

Each write of the API and of the worker takes the lock shared, then reads the maintenance; the
restoration takes it exclusively once the maintenance is held, before it keeps anything (#2229,
#1014). The minimal reference is ordered with the restoration by it (#2301). Each test makes an
installation of its own (``installations``), whose database the role of the service reaches
guarded, as the API and the worker reach theirs.
"""

import threading
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from advisory_locks import waits_for
from fastapi.testclient import TestClient
from installations import Installation, Provider, restorer_headers
from project_rows import insert_project
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from support import ContractClient
from task_handlers import REQUEST, Runs, deposit

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.interface import share_reference
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import AuditEntry, AuditObject, Inscription, record
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.maintenance import (
    DRAIN_LOCK,
    Maintenance,
    MaintenanceHeldError,
    Restoring,
    admitted,
    drained,
    guard_writes,
    writes,
)
from waterfall.platform.restoration import kept, table_of
from waterfall.platform.tasks import BackgroundTask
from waterfall.restore import task as restoration
from waterfall.restore.task import RestoreTask
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uuid import UUID

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Connection, Engine
    from sqlalchemy.orm import Session

    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

PATIENCE = timedelta(seconds=30)
# Whether a transaction holds the advisory lock of a key exclusively, in this database.
DRAINING = text(
    "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted "
    "AND mode = 'ExclusiveLock' "
    "AND database = (SELECT oid FROM pg_database WHERE datname = current_database()) "
    "AND (classid::bigint << 32) | objid::bigint = :key"
)


@pytest.fixture
def guarded(installation: Installation) -> Database:
    """Give the database of the installation as the API and the worker reach it: guarded."""
    guard_writes(installation.database.engine)
    return installation.database


@pytest.fixture
def owner(installation: Installation) -> Iterator[Engine]:
    """Give the database of the installation as its owner, the service of the restoration."""
    engine = create_database_engine(installation.owner["waterfall"])
    yield engine
    engine.dispose()


@pytest.fixture
def maintenance(owner: Engine, queue: TaskQueue) -> Iterator[Maintenance]:
    """Give the maintenance as the service of the restoration holds it; lifted after the test."""
    held = Maintenance.of(Database(owner), queue)
    yield held
    held.lift()


@pytest.fixture
def unheld_api(
    installation: Installation,
    queue: TaskQueue,
    contract: OpenAPI,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
) -> ContractClient:
    """Serve the API on the installation guarded, its middleware reading no maintenance."""
    guard_writes(installation.database.engine)
    services = Services(
        installation.database,
        keycloak,
        KeycloakAdmin(keycloak, realm_settings),
        queue,
        installation.bucket,
    )
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


def inscribe(session: Session, label: str) -> UUID:
    """Inscribe the update of an account by the platform, in a transaction the caller holds."""
    audited = AuditObject("user", uuid4(), label)
    with logging_context(correlation_id=REQUEST):
        return record(session, Inscription("user_update", None, audited, utc_now()))


def inscribed(database: Database, label: str) -> int:
    """Count the inscriptions of a label in a database."""
    with database.transaction() as session:
        where = AuditEntry.object_label == label
        return session.scalar(select(func.count()).select_from(AuditEntry).where(where)) or 0


def held_restoration(maintenance: Maintenance) -> Restoring:
    """Hold the platform in maintenance for a restoration, as its first attempt does."""
    return maintenance.hold(Restoring(uuid4(), {}, None, REQUEST, 1))


@pytest.mark.story("US-2940")
@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_write_admitted_before_the_maintenance_is_kept_and_one_after_is_refused(
    installation: Installation, guarded: Database, owner: Engine, maintenance: Maintenance
) -> None:
    # « Une inscription faite après la sauvegarde est encore présente après la restauration »
    # (#2229): a write admitted before the maintenance, held between it and its commit — an
    # account deactivated while Keycloak answers —, is waited for by the restoration, which keeps
    # its inscription once it has committed. A write after is refused, and nothing is written.
    label, later = f"before-{uuid4().hex}", f"after-{uuid4().hex}"
    writing, release = threading.Event(), threading.Event()

    def admitted_before() -> None:
        with guarded.transaction() as session:
            inscribe(session, label)
            writing.set()
            release.wait(30)

    writer = threading.Thread(target=admitted_before)
    writer.start()
    assert writing.wait(30)
    held = held_restoration(maintenance)
    restoring = RestoreTask(
        installation.owner, installation.bucket, maintenance, Provider([]), upgrade
    )
    keeper = threading.Thread(target=restoring.keep, args=(owner, held))
    keeper.start()
    try:
        assert waits_for(Database(owner), DRAIN_LOCK)
        assert keeper.is_alive()
    finally:
        release.set()
        writer.join()
        keeper.join()
    copy = kept(table_of(AuditEntry))
    with owner.connect() as connection:
        labels = connection.scalars(select(copy.c.object_label)).all()
    assert label in labels
    with pytest.raises(MaintenanceHeldError) as refused, guarded.transaction() as session:
        inscribe(session, later)
    assert (refused.value.status, refused.value.code) == (503, "COMPONENT_UNAVAILABLE")
    assert inscribed(installation.database, later) == 0


@pytest.mark.story("US-2940")
def test_what_the_restoration_keeps_is_read_at_one_instant_once_the_writes_are_drained(
    installation: Installation,
    owner: Engine,
    maintenance: Maintenance,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # #2229: the journal, the backups, the deposits and the tasks are kept in one transaction,
    # frozen at its first read (« the rows kept are then those of one instant »), which runs while
    # the restoration holds the lock of the drain exclusively.
    seen: list[tuple[str, bool]] = []
    keep = restoration.keep_for_restoration

    def keeping(connection: Connection, task_id: UUID) -> None:
        isolation = str(connection.scalar(text("SHOW transaction_isolation")))
        with owner.connect() as probe:
            draining = probe.scalar(DRAINING, {"key": DRAIN_LOCK})
        seen.append((isolation, bool(draining)))
        keep(connection, task_id)

    monkeypatch.setattr(restoration, "keep_for_restoration", keeping)
    held = held_restoration(maintenance)
    restoring = RestoreTask(
        installation.owner, installation.bucket, maintenance, Provider([]), upgrade
    )
    restoring.keep(owner, held)
    assert seen == [("repeatable read", True)]


@pytest.mark.story("US-2940")
def test_a_write_never_waits_for_the_drain_it_is_refused_while_the_restoration_holds_it(
    guarded: Database, owner: Engine
) -> None:
    # Two transactions of one request, the first holding the lock, would wait for each other unseen
    # behind a restoration that asks for it: a write tries the lock, and a lock held exclusively
    # refuses it at once, as the maintenance does.
    with drained(owner, PATIENCE):
        with pytest.raises(MaintenanceHeldError), guarded.transaction() as session:
            inscribe(session, f"held-{uuid4().hex}")
        with guarded.transaction() as session:
            assert session.scalar(select(func.count()).select_from(AuditEntry)) is not None


@pytest.mark.story("US-2940")
def test_the_drain_waits_for_a_write_its_patience_at_most(guarded: Database, owner: Engine) -> None:
    # A write that does not end does not hold a restoration without end: the wait fails, and the
    # attempt is taken up later, within its deadline.
    with guarded.transaction() as session:
        inscribe(session, f"long-{uuid4().hex}")
        with (
            pytest.raises(OperationalError, match="lock timeout"),
            drained(owner, timedelta(milliseconds=200)),
        ):
            pass


@pytest.mark.story("US-2940")
def test_a_savepoint_rolled_back_releases_the_lock_it_took_and_the_next_write_asks_again(
    guarded: Database, maintenance: Maintenance
) -> None:
    # The lock taken in a savepoint is released with it: the next write asks again, and reads the
    # maintenance held meanwhile. Taken before the savepoint, it stays, and the transaction goes on
    # writing: admitted before the maintenance, its writes are waited for.

    def rolled_back_then_held() -> None:
        with guarded.transaction() as session:
            with session.begin_nested() as nested:
                inscribe(session, f"rolled-{uuid4().hex}")
                nested.rollback()
            held_restoration(maintenance)
            inscribe(session, f"refused-{uuid4().hex}")

    with pytest.raises(MaintenanceHeldError):
        rolled_back_then_held()
    maintenance.lift()
    label = f"admitted-{uuid4().hex}"
    with guarded.transaction() as session:
        inscribe(session, f"first-{uuid4().hex}")
        held_restoration(maintenance)
        with session.begin_nested() as nested:
            inscribe(session, f"rolled-{uuid4().hex}")
            nested.rollback()
        inscribe(session, label)
    assert inscribed(guarded, label) == 1


@pytest.mark.story("US-2940")
def test_no_project_is_created_once_a_restoration_has_drained_the_writes(
    guarded: Database, owner: Engine, maintenance: Maintenance
) -> None:
    # #2301: the creation of a project shares the lock of the reference, then writes; once the
    # maintenance is held and the writes drained, it is refused, as every writing that could
    # empty the reference: the restoration replaces the reference without that lock.
    held_restoration(maintenance)
    with drained(owner, PATIENCE):
        pass

    def create() -> None:
        with guarded.transaction() as session:
            share_reference(session)
            session.execute(insert_project())

    with pytest.raises(MaintenanceHeldError):
        create()
    with guarded.transaction() as session:
        assert session.scalar(select(func.count()).select_from(Project)) == 0


@pytest.mark.story("US-2940")
@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_write_the_maintenance_catches_past_the_entry_of_its_request_answers_503(
    installation: Installation,
    unheld_api: ContractClient,
    maintenance: Maintenance,
    realm: TestRealm,
) -> None:
    # The request passed the entry before the maintenance was held — the middleware reads none
    # here —: its write is refused as the maintenance refuses a request, 503 and the component
    # named, and the backup it asked for is not deposited.
    headers = restorer_headers(installation, realm)
    held_restoration(maintenance)
    api = unheld_api
    answer = api.post("/api/v1/backups", headers=headers)
    assert answer.status_code == 503
    assert (answer.json()["code"], answer.json()["params"]) == (
        "COMPONENT_UNAVAILABLE",
        {"component": "database"},
    )
    with installation.database.transaction() as session:
        backups = (
            select(func.count()).select_from(BackgroundTask).where(BackgroundTask.kind == "backup")
        )
        assert session.scalar(backups) == 0


@pytest.mark.story("US-2940")
@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_run_of_the_worker_is_admitted_by_the_drain_and_waited_for_until_it_ends(
    guarded: Database, owner: Engine, queue: TaskQueue
) -> None:
    # A run admitted holds the lock shared until it ends: the restoration waits for it. One that
    # takes the lock of its run once the writes are drained is not admitted, and runs nothing.
    task_id = deposit(guarded, queue)

    def drain() -> None:
        with drained(owner, PATIENCE):
            pass

    with guarded.transaction() as session:
        assert admitted(session.connection())
        draining = threading.Thread(target=drain)
        draining.start()
        assert waits_for(Database(owner), DRAIN_LOCK)
    draining.join()
    runs = Runs()
    worker = Worker(guarded, queue, {"identity_sync": runs}, "worker-test", Timing(0, 0.1))
    with drained(owner, PATIENCE):
        assert not worker.run_task(task_id)
    assert runs == []
    assert worker.run_task(task_id)
    assert runs == [task_id]


@pytest.mark.story("US-2940")
@pytest.mark.parametrize(
    ("statement", "written"),
    [
        ("SELECT 1", False),
        ("  (SELECT 1)", False),
        ("savepoint sa_savepoint_1", False),
        ("INSERT INTO t VALUES (1)", True),
        ("WITH gone AS (DELETE FROM t RETURNING id) SELECT id FROM gone", True),
        ("\n  update t set a = 1", True),
        ("", True),
    ],
)
def test_a_statement_is_a_write_unless_its_first_word_says_a_reading(
    statement: str, *, written: bool
) -> None:
    # Any statement whose first word says no reading is taken for a write: the lock is asked for
    # rather than a write missed.
    assert writes(statement) is written


@pytest.mark.story("US-2940")
def test_a_transaction_repeatable_read_of_the_repository_never_writes() -> None:
    # The proof of ``guard_writes`` holds in READ COMMITTED: a REPEATABLE READ transaction that
    # wrote would see a maintenance older than its snapshot. The restoration, unguarded, is
    # the one exception.
    source = Path(restoration.__file__).parents[1]
    for path in source.rglob("*.py"):
        text_of = path.read_text(encoding="utf-8")
        if 'isolation_level="REPEATABLE READ"' not in text_of or path.parent.name == "restore":
            continue
        assert "READ ONLY" in text_of.upper() or "postgresql_readonly=True" in text_of, path
