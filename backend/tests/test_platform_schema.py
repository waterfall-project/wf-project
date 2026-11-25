# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schema ``platform``: the maintenance of a restoration and its state, out of ``public``.

Its two tables hold one row each at most, which the owner alone writes and the role of the service
reads (migration 0048, ``waterfall.platform.maintenance``). A backup dumps ``public`` alone, and a
restoration replaces it alone: the maintenance it holds is there once ``public`` is replaced, and a
backup taken before the schema was made is restored with the migration applied again, without
effect on it, as is one of whole databases, which the backups dumped before EP-13. Nothing of the
database of the identity provider is lost on the way. The same migration admits the tasks the
platform schedules, and lets the report of a reading of the accounts go with its task (#921).
"""

import dataclasses
import socket
import subprocess
import time
from typing import TYPE_CHECKING, Any, LiteralString
from uuid import UUID, uuid4

import psycopg
import pytest
from access_rows import role
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from installations import (
    Installation,
    Take,
    before_the_schedule_of_the_backups,
    restore,
    written_task,
)
from psycopg import sql
from sqlalchemy import Engine, create_engine, delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from waterfall.api.app import create_app
from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.users.tables import IdentitySyncReport
from waterfall.migrations.runner import alembic_config, downgrade, upgrade
from waterfall.platform.database import (
    CONNECT_TIMEOUT,
    Base,
    Database,
    create_database_engine,
    engine_url,
    utc_now,
)
from waterfall.platform.maintenance import (
    HeldMaintenance,
    Maintenance,
    RestorationState,
    Restoring,
)
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.backup import (
    DATABASES,
    Dumped,
    archive,
    connect,
    connection,
    digest,
    manifest,
)
from waterfall.worker.inventory import Inventory
from waterfall.worker.restore import extracted

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from waterfall.api.authentication import Services
    from waterfall.platform.queue import TaskQueue

# The restoration that holds the maintenance in these tests.
HELD = Restoring(uuid4(), {"backup_id": str(uuid4()), "actor": None}, uuid4(), "request-3f6a", 1)
# The revision of the schema of the installation, to which a restoration migrates.
HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()
# The two tables of the schema, in the order they are counted.
TABLES = (HeldMaintenance, RestorationState)
# A database no server answers for.
UNREACHABLE = "postgresql://nobody:nothing@127.0.0.1:9/nowhere"


@pytest.fixture
def owned(owner: Engine) -> Database:
    """Give the database as its owner reaches it, who alone writes the maintenance."""
    return Database(owner)


def refusal(engine: Engine, statement: Any) -> str:
    """Run a statement the database must refuse, and give the constraint that refused it."""
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        connection.execute(statement)
    cause = raised.value.orig
    assert isinstance(cause, psycopg.Error)
    return cause.diag.constraint_name or ""


@pytest.mark.requirement("WF-ARC-0090-A")
def test_the_owner_holds_the_maintenance_which_the_service_reads_and_may_not_write(
    database: Database, owned: Database, queue: TaskQueue
) -> None:
    # One row each, rewritten by each attempt: the service reads what the owner held, and is
    # refused the writing.
    held, read = Maintenance.of(owned, queue), Maintenance.of(database, queue)
    first = held.hold(HELD)
    assert read.current() == HELD
    taken_up = dataclasses.replace(first, attempts=2, caches_cleared=True)
    held.hold(taken_up)
    current = read.current()
    assert current == taken_up
    # Dated at its first attempt, the date kept by the next: its deadline counts from it (#1016).
    assert current is not None
    assert first.held_at is not None
    assert current.held_at == first.held_at
    with owned.engine.connect() as connection:
        rows = [connection.scalar(select(func.count()).select_from(table)) for table in TABLES]
    assert rows == [1, 1]
    for writing in (lambda: read.hold(HELD), read.lift):
        with pytest.raises(ProgrammingError, match="permission denied"):
            writing()
    held.lift()
    assert read.current() is None


VALID: dict[type[Base], dict[str, object]] = {
    HeldMaintenance: {"id": 1, "task_id": uuid4()},
    RestorationState: {
        "id": 1,
        "task_id": uuid4(),
        "payload": {},
        "requested_by": None,
        "correlation_id": "request-3f6a",
        "attempts": 1,
        "caches_cleared": False,
        "abandoned": False,
    },
}


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.usefixtures("database")
@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    [
        (HeldMaintenance, {"id": 2}, "ck_maintenance_single_row"),
        (HeldMaintenance, {}, "pk_maintenance"),
        (RestorationState, {"id": 2}, "ck_restoration_single_row"),
        (RestorationState, {}, "pk_restoration"),
        (RestorationState, {"attempts": 0}, "ck_restoration_attempts_positive"),
        (RestorationState, {"payload": []}, "ck_restoration_payload_object"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_second_maintenance_or_a_state_that_breaks_a_rule(
    owner: Engine,
    table: type[Base],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    # The service writes none: the rows are the owner's, around the code.
    with owner.begin() as connection:
        connection.execute(insert(table).values(**VALID[table]))
    assert refusal(owner, insert(table).values(**{**VALID[table], **overrides})) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_tasks_the_platform_schedules_are_of_known_kinds(database: Database) -> None:
    kinds = ("purge", "backup_copy", "restore_test")
    written = {kind: written_task(database, kind, "queued") for kind in kinds}
    with database.transaction() as session:
        rows = session.execute(select(BackgroundTask.kind, BackgroundTask.id))
        read = {row.kind: row.id for row in rows}
    assert read == written


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_report_of_a_reading_of_the_accounts_goes_with_its_task(
    database: Database, owner: Engine
) -> None:
    # #921: the purge of the tasks, which the owner's rights stand for here, takes the report of a
    # reading with its task; the other report stays.
    purged, kept = (written_task(database, "identity_sync", "queued") for _ in range(2))
    report = {"finished_at": utc_now(), "created": 0, "updated": 0, "deactivated": 0}
    with owner.begin() as connection:
        for task_id in (purged, kept):
            values: dict[str, object] = {**report, "task_id": task_id, "skipped": [], "removed": []}
            connection.execute(insert(IdentitySyncReport).values(**values))
        connection.execute(delete(BackgroundTask).where(BackgroundTask.id == purged))
        left = connection.scalars(select(IdentitySyncReport.task_id)).all()
    assert left == [kept]


def dumped(installation: Installation, backup_task: Any, folder: Path) -> list[str]:
    """List what the dump of the database of Waterfall of a backup holds, as pg_restore lists it."""
    archive = folder / "listed.tar"
    installation.bucket.download(f"backup-{backup_task}.tar", archive)
    dumps = extracted(archive, folder)
    assert sorted(dumps) == sorted(DATABASES)
    listed = subprocess.run(
        ["/usr/bin/pg_restore", "--list", str(dumps["waterfall"])],
        capture_output=True,
        check=True,
    )
    return listed.stdout.decode().splitlines()


@pytest.fixture
def held_on(installation: Installation, queue: TaskQueue) -> Iterator[Maintenance]:
    """Give the maintenance of an installation, as its owner holds it."""
    owner = Database(create_database_engine(installation.owner["waterfall"]))
    yield Maintenance.of(owner, queue)
    owner.dispose()


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_backup_dumps_public_alone_and_a_restoration_leaves_the_maintenance_in_place(
    installation: Installation, take: Take, queue: TaskQueue, held_on: Maintenance, tmp_path: Path
) -> None:
    # A backup holds nothing of the schema ``platform`` but the extension ``public`` uses; a
    # restoration, which holds the maintenance before it replaces anything, finds it there after,
    # and the role of the service still reads it.
    backup_task = take()
    listed = dumped(installation, backup_task, tmp_path)
    assert not [line for line in listed if " platform " in line]
    assert [line for line in listed if " EXTENSION - unaccent " in line]
    held_on.hold(HELD)
    restore(installation, backup_task, tmp_path)
    assert Maintenance.of(installation.database, queue).current() == HELD


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_backup_taken_before_the_schema_platform_is_restored_and_the_migration_leaves_it_be(
    installation: Installation, take: Take, queue: TaskQueue, held_on: Maintenance, tmp_path: Path
) -> None:
    # The backup is taken at 0047, before the schema ``platform``: the worker, which reads the
    # maintenance, finds none there. The restoration replaces ``public`` by it, then applies 0048
    # again: the schema, the maintenance it holds and the rights of the service stay as they were,
    # and ``public`` admits the kinds of the schedule.
    owner = create_database_engine(installation.owner["waterfall"])
    downgrade(owner, "0047")
    with before_the_schedule_of_the_backups():
        backup_task = take()
    upgrade(owner)
    held_on.hold(HELD)
    restore(installation, backup_task, tmp_path)
    with owner.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    owner.dispose()
    assert revision == HEAD
    assert Maintenance.of(installation.database, queue).current() == HELD
    assert written_task(installation.database, "purge", "queued")


def whole(name: str, address: str, folder: Path) -> Dumped:
    """Dump a whole database as the backups did before EP-13: every schema, nothing named."""
    path = folder / f"{name}.dump"
    with path.open("wb") as written:
        subprocess.run(
            ["/usr/bin/pg_dump", "--format=custom", "--no-password"],
            stdout=written,
            env=connection(address, folder / f"{name}.service"),
            check=True,
        )
    return Dumped(name, path, path.stat().st_size, digest(path))


def taken_whole(installation: Installation, folder: Path) -> UUID:
    """Store a backup of whole databases, as one taken before EP-13; give the task it names."""
    folder.mkdir()
    dumps = [whole(name, installation.backup[name], folder) for name in DATABASES]
    path = folder / "backup.tar"
    archive(path, manifest(utc_now(), "0047", dumps, Inventory(0, 0, 0, 0)), dumps)
    backup_task = uuid4()
    installation.bucket.upload(f"backup-{backup_task}.tar", path)
    return backup_task


def provided(installation: Installation, *statements: LiteralString) -> None:
    """Run statements on the database of the identity provider, as its owner, and commit them."""
    with connect(installation.owner["identity_provider"]) as session:
        for statement in statements:
            session.execute(statement)


def labels(installation: Installation) -> list[str]:
    """Give the labels of the roles of the database of Waterfall, sorted."""
    with installation.database.transaction() as session:
        return sorted(session.scalars(select(AccessRole.label)).all())


@pytest.mark.requirement("WF-ADM-0160-A")
def test_a_backup_of_whole_databases_taken_before_ep13_is_restored_with_the_maintenance_in_place(
    installation: Installation, queue: TaskQueue, held_on: Maintenance, tmp_path: Path
) -> None:
    # The backups taken before EP-13 dumped each database whole, at 0047: no schema ``platform``,
    # and ``public`` left to the database. Restored, each database holds what it held then and
    # nothing written since; the maintenance held in ``platform`` stays, and the service reads it.
    owner = create_database_engine(installation.owner["waterfall"])
    downgrade(owner, "0047")
    before = labels(installation)
    role(installation.database, "Sauvegardé")
    provided(installation, "INSERT INTO realm VALUES ('backed-up')")
    backup_task = taken_whole(installation, tmp_path / "whole")
    upgrade(owner)
    role(installation.database, "Écrit après")
    provided(
        installation,
        "DELETE FROM realm WHERE id = 'waterfall'",
        "INSERT INTO realm VALUES ('after')",
    )
    held_on.hold(HELD)
    restore(installation, backup_task, tmp_path)
    with owner.connect() as connected:
        revision = connected.scalar(text("SELECT version_num FROM alembic_version"))
    owner.dispose()
    with connect(installation.owner["identity_provider"]) as session:
        realms = sorted(str(row[0]) for row in session.execute("SELECT id FROM realm"))
    assert revision == HEAD
    assert labels(installation) == sorted([*before, "Sauvegardé"])
    assert realms == ["backed-up", "waterfall"]
    assert Maintenance.of(installation.database, queue).current() == HELD
    installation.bucket.remove(f"backup-{backup_task}.tar")


# What the database of Keycloak holds beside its tables: a column of large objects, as its
# ``cluster_event``, a sequence, a column of identity and an extension, made before the backup.
KEYCLOAK = (
    "CREATE EXTENSION citext",
    "CREATE TABLE client (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, name citext UNIQUE)",
    "CREATE SEQUENCE event_order START 40",
    "CREATE TABLE cluster_event (id text PRIMARY KEY, event_data oid NOT NULL)",
    "INSERT INTO client (name) VALUES ('waterfall-front'), ('waterfall-api')",
    "SELECT nextval('event_order')",
    "INSERT INTO cluster_event VALUES ('sessions', lo_from_bytea(0, '\\x7b2273223a317d'))",
)
# What Keycloak changes after the backup, which the restoration undoes.
CHANGED = (
    "INSERT INTO client (name) VALUES ('written-after')",
    "SELECT nextval('event_order')",
    "SELECT lo_unlink(event_data) FROM cluster_event",
    "UPDATE cluster_event SET event_data = lo_from_bytea(0, '\\x7b7d')",
    "CREATE TABLE made_after (id text)",
    "DROP EXTENSION citext CASCADE",
)


def readable_by_the_backup(installation: Installation) -> None:
    """Let the role of the backup read the large objects, which ``pg_read_all_data`` does not.

    The role of the tests is made without the script of the platform, which grants that right
    (``backup-database-role.sql``, #4170, tested by ``test_backup_role_script``): without it, a
    backup of a database that holds one fails.
    """
    backup = engine_url(installation.backup["identity_provider"]).username or ""
    with connect(installation.owner["identity_provider"]) as session:
        held = session.execute("SELECT oid::bigint FROM pg_largeobject_metadata").fetchall()
        for (oid,) in held:
            granted = sql.SQL("GRANT SELECT ON LARGE OBJECT {} TO {}")
            session.execute(granted.format(sql.Literal(oid), sql.Identifier(backup)))


# What is read of the database of the identity provider, compared before and after.
STATE: dict[str, LiteralString] = {
    "schemas": "SELECT nspname FROM pg_namespace"
    " WHERE nspname NOT LIKE 'pg\\_%' AND nspname <> 'information_schema' ORDER BY 1",
    "tables": "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1",
    "columns": "SELECT table_name, column_name, data_type, is_identity"
    " FROM information_schema.columns WHERE table_schema = 'public' ORDER BY 1, 2",
    "sequences": "SELECT schemaname, sequencename, last_value FROM pg_sequences ORDER BY 1, 2",
    "extensions": "SELECT extname, extversion, extnamespace::regnamespace::text"
    " FROM pg_extension ORDER BY 1",
    "large_objects": "SELECT oid::bigint, lo_get(oid) FROM pg_largeobject_metadata ORDER BY 1",
}


def provider_state(installation: Installation) -> dict[str, list[tuple[Any, ...]]]:
    """Read the database of the identity provider whole, its large objects included.

    Its schemas, its tables, their columns and their rows, its sequences and its extensions.
    """
    with connect(installation.owner["identity_provider"]) as session:
        state = {name: session.execute(query).fetchall() for name, query in STATE.items()}
        for (table,) in state["tables"]:
            read = sql.SQL("SELECT * FROM {} ORDER BY 1").format(sql.Identifier("public", table))
            state[f"rows of {table}"] = session.execute(read).fetchall()
    return state


@pytest.mark.requirement("WF-ADM-0150-A")
@pytest.mark.requirement("WF-ADM-0160-A")
def test_the_database_of_the_identity_provider_is_restored_without_a_loss(
    installation: Installation, take: Take, tmp_path: Path
) -> None:
    # A backup dumps ``public`` alone, where Keycloak keeps its tables: its sequences, its
    # extensions and its large objects, which belong to no schema, come with it. Restored after
    # Keycloak has changed all of them, the database is as it was at the backup.
    provided(installation, *KEYCLOAK)
    readable_by_the_backup(installation)
    backed_up = provider_state(installation)
    backup_task = take()
    provided(installation, *CHANGED)
    assert provider_state(installation) != backed_up
    restore(installation, backup_task, tmp_path)
    restored = provider_state(installation)
    assert backed_up["large_objects"]
    assert restored == backed_up


@pytest.mark.requirement("WF-ARC-0090-A")
def test_the_probe_of_liveness_answers_when_the_maintenance_cannot_be_read(
    services: Services, queue: TaskQueue
) -> None:
    # A database out of reach says no maintenance: the probe answers, as it did when the
    # maintenance was in Redis; the operations that need the database say so themselves.
    unreached = Database(create_database_engine(UNREACHABLE))
    served = dataclasses.replace(services, maintenance=Maintenance.of(unreached, queue))
    try:
        answer = TestClient(create_app(served)).get("/api/v1/health")
    finally:
        unreached.dispose()
    assert (answer.status_code, answer.json()) == (200, {"status": "ok"})


@pytest.mark.requirement("WF-ARC-0090-A")
def test_the_probe_of_liveness_answers_within_a_bound_when_the_database_does_not_answer(
    services: Services, queue: TaskQueue
) -> None:
    # A server that takes the connection and never speaks (lost packets, not a refusal) holds the
    # probe for the time of the connection and no longer: the healthcheck of Compose waits no more.
    with socket.socket() as mute:
        mute.bind(("127.0.0.1", 0))
        mute.listen()
        address = f"postgresql://nobody:nothing@127.0.0.1:{mute.getsockname()[1]}/nowhere"
        unreached = Database(create_database_engine(address))
        served = dataclasses.replace(services, maintenance=Maintenance.of(unreached, queue))
        began = time.monotonic()
        try:
            answer = TestClient(create_app(served)).get("/api/v1/health")
        finally:
            unreached.dispose()
        elapsed = time.monotonic() - began
    assert (answer.status_code, answer.json()) == (200, {"status": "ok"})
    assert elapsed < CONNECT_TIMEOUT + 2


@pytest.mark.requirement("WF-ARC-0090-A")
def test_the_probe_of_liveness_answers_when_the_pool_of_connections_is_spent(
    services: Services, database: Database, queue: TaskQueue
) -> None:
    # The pool waits for a connection and gives up: not a 500, the probe answers.
    spent = Database(
        create_engine(database.engine.url, pool_size=1, max_overflow=0, pool_timeout=0.2)
    )
    served = dataclasses.replace(services, maintenance=Maintenance.of(spent, queue))
    try:
        with spent.engine.connect():
            answer = TestClient(create_app(served)).get("/api/v1/health")
    finally:
        spent.dispose()
    assert (answer.status_code, answer.json()) == (200, {"status": "ok"})


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_maintenance_held_without_its_state_stays_held_and_is_said_without_it(
    database: Database, owned: Database, queue: TaskQueue
) -> None:
    # The state missing while the maintenance is held is an inconsistency to see, not a platform
    # to serve: the maintenance stays, said without its state, its databases possibly changed,
    # which its service gives up and keeps for an operator (#1016).
    with owned.transaction() as session:
        session.execute(insert(HeldMaintenance).values(**VALID[HeldMaintenance]))
    try:
        current = Maintenance.of(database, queue).current()
    finally:
        with owned.transaction() as session:
            session.execute(delete(HeldMaintenance))
    assert current is not None
    assert (current.task_id, current.stateless, current.caches_cleared) == (
        VALID[HeldMaintenance]["task_id"],
        True,
        True,
    )


@pytest.mark.requirement("WF-ARC-0090-A")
def test_the_migration_completes_a_schema_made_by_hand_without_its_tables(
    installation: Installation, queue: TaskQueue
) -> None:
    # A schema ``platform`` made without its tables is completed by the migration, with the rights
    # of the service; applied again over a complete one, it leaves the maintenance it holds. Applied
    # again alone: the migrations after it create tables of ``public``, which a restoration replaces
    # before it applies them, and which this database still holds.
    owner = create_database_engine(installation.owner["waterfall"])
    try:
        downgrade(owner, "0047")
        with owner.begin() as connection:
            connection.execute(text("CREATE SCHEMA platform"))
        upgrade(owner)
        read = Maintenance.of(installation.database, queue)
        assert read.current() is None
        Maintenance.of(Database(owner), queue).hold(HELD)
        with owner.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = '0047'"))
        upgrade(owner, "0048")
        assert read.current() == HELD
    finally:
        owner.dispose()
