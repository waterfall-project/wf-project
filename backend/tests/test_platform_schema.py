# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schema ``platform``: the maintenance of a restoration and its state, out of ``public``.

Its two tables hold one row each at most, which the owner alone writes and the role of the service
reads (migration 0035, ``waterfall.platform.maintenance``). A backup dumps ``public`` alone, and a
restoration replaces it alone: the maintenance it holds is there once ``public`` is replaced, and a
backup taken before the schema was made is restored with the migration applied again, without
effect on it. The same migration admits the tasks the platform schedules, and lets the report of a
reading of the accounts go with its task (#921).
"""

import dataclasses
import subprocess
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import psycopg
import pytest
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from installations import Installation, Take, restore, written_task
from sqlalchemy import Engine, delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from waterfall.api.app import create_app
from waterfall.core.users.tables import IdentitySyncReport
from waterfall.migrations.runner import alembic_config, downgrade, upgrade
from waterfall.platform.database import Base, Database, create_database_engine, utc_now
from waterfall.platform.maintenance import (
    HeldMaintenance,
    Maintenance,
    RestorationState,
    Restoring,
)
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker.backup import DATABASES
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


def test_the_owner_holds_the_maintenance_which_the_service_reads_and_may_not_write(
    database: Database, owned: Database, queue: TaskQueue
) -> None:
    # One row each, rewritten by each attempt: the service reads what the owner held, and is
    # refused the writing.
    held, read = Maintenance.of(owned, queue), Maintenance.of(database, queue)
    held.hold(HELD)
    assert read.current() == HELD
    taken_up = dataclasses.replace(HELD, attempts=2, caches_cleared=True)
    held.hold(taken_up)
    assert read.current() == taken_up
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


def test_a_backup_taken_before_the_schema_platform_is_restored_and_the_migration_leaves_it_be(
    installation: Installation, take: Take, queue: TaskQueue, held_on: Maintenance, tmp_path: Path
) -> None:
    # The backup is taken at 0034, before the schema ``platform``: the worker, which reads the
    # maintenance, finds none there. The restoration replaces ``public`` by it, then applies 0035
    # again: the schema, the maintenance it holds and the rights of the service stay as they were,
    # and ``public`` admits the kinds of the schedule.
    owner = create_database_engine(installation.owner["waterfall"])
    downgrade(owner, "0034")
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
