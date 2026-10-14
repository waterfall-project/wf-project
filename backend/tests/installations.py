# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the restoration share: installations of their own, backed up and restored.

Each makes an installation on the PostgreSQL of the tests — a database of Waterfall, migrated, and
one that stands for the identity provider's —, backs it up as the worker does into a bucket of the
object storage of the tests, and restores it by the functions a restoration runs. The databases
are reached as their owner, the superuser of the tests standing for it; the API and the worker
reach them as the role of the service. ``conftest`` gives ``installed`` and ``taker`` as the
fixtures ``installation`` and ``take``.
"""

import hashlib
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from access_rows import account, role
from realm import KEY, TestRealm
from sqlalchemy import ColumnElement, func, insert, select, text, update
from support import as_backup, bearer
from task_handlers import REQUEST, deposit

from waterfall.core.backups.interface import keep_for_restoration, write_back_after_restoration
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import AuditEntry, AuditObject, Inscription, record
from waterfall.platform.database import Database, create_database_engine, engine_url, utc_now
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import TaskQueue
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import BackgroundTask
from waterfall.restore.provider import RealmNotAppliedError
from waterfall.worker.backup import DATABASES, BackupTask
from waterfall.worker.restore import extracted, replace
from waterfall.worker.runner import Timing, Worker

# An account the inscriptions of these tests name, without a foreign key.
NAMED = UUID("01926f3a-7c00-7000-8000-0000000004c1")


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


def installed(
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


def taker(installation: Installation, queue: TaskQueue) -> Take:
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


def restore(
    installation: Installation, backup_task: UUID, folder: Path, removed: list[str] | None = None
) -> UUID:
    """Restore the backup a task took, as a restoration does whoever runs it; give its task.

    The restoration is a task the API deposits (``startRestore``): its row is in the database it
    replaces, which keeps it, and spares it when the tasks restored pending fail; what runs the
    restoration then ends it. ``removed``, if given, receives the subjects of the local accounts
    anonymised again, which what runs the restoration removes from the provider.
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
        subjects = write_back_after_restoration(connection, restoration, utc_now())
        spared = select(BackgroundTask.status).where(BackgroundTask.id == restoration)
        assert connection.scalar(spared) == "running"
        ended = {"status": "succeeded", "progress": 100, "finished_at": utc_now()}
        connection.execute(
            update(BackgroundTask).where(BackgroundTask.id == restoration).values(**ended)
        )
    owner.dispose()
    if removed is not None:
        removed.extend(subjects)
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


@dataclass
class Provider:
    """Stands for Keycloak: keeps what the restoration asks of it, in its order, in ``steps``.

    ``failing`` renewals fail before one succeeds, as a realm not applied again does.
    """

    steps: list[str]
    failing: int = 0
    removed: list[str] = field(default_factory=list[str])

    def close_sessions(self) -> None:
        """Keep the closing of every session."""
        self.steps.append("close_sessions")

    def prepare(self) -> None:
        """Keep the token taken before the replacement."""
        self.steps.append("prepare")

    def renew(self, name: str) -> None:
        """Keep the caches cleared and the realm applied again, or fail ``failing`` times."""
        self.steps.append("renew")
        if self.failing:
            self.failing -= 1
            message = f"not applied again ({name})"
            raise RealmNotAppliedError(message)

    def remove(self, subjects: Iterable[str]) -> None:
        """Keep the accounts removed from the realm."""
        self.removed.extend(subjects)
        self.steps.append("remove")


def restorer_headers(
    installation: Installation,
    realm: TestRealm,
    permissions: tuple[str, ...] = ("backups.read", "backups.write", "platform_restore"),
    first_name: str = "Claire",
) -> dict[str, str]:
    """Write an account that may back up and restore the installation; give its bearer.

    Or one, of another ``first_name``, that holds ``permissions`` alone.
    """
    subject = f"subject-{uuid4()}"
    held = role(installation.database, f"Restauration {first_name}", permissions=permissions)
    account(installation.database, "Martin", first_name, roles=(held,), idp_subject=subject)
    return bearer(realm.token(subject, KEY))
