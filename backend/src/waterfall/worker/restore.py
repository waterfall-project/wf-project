# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``restore``: both databases replaced whole by a backup, nothing partial (WF-ADM-0160).

The archive is read from the bucket of the backups, its manifest read and each dump checked against
its digest; one of a newer version than the installation is refused before anything changes. The
platform is then held in maintenance, and every session closed, of the identity provider and of the
front. What the restoration keeps — the journal of audit, the backups, a few tasks, the rights of
the role of the service — is copied aside, once (``waterfall.platform.restoration``). Each database
is then made again from its dump, as its owner (#701), without the owners and the rights of the
source; the migrations that follow the backup are applied; what was kept is written back — the
inscriptions of the journal and the backups the restored database lacks (#893, #894) —, and the
tasks the restored database holds queued or running fail (#892). The caches of Keycloak are cleared
and the sessions closed again; the restoration is inscribed in the journal, and the maintenance
lifted. Taken up after an interruption, it starts again from the beginning (WF-ARC-0090).
"""

import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from waterfall import __version__
from waterfall.core.backups.interface import (
    NOT_FOUND,
    inscribe_restoration,
    keep_for_restoration,
    write_back_after_restoration,
)
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import AuditActor
from waterfall.platform.database import create_database_engine, utc_now
from waterfall.platform.errors import NotFoundError, UnprocessableError
from waterfall.platform.logs import get_logger
from waterfall.platform.maintenance import Maintenance, Restoring
from waterfall.platform.storage import Bucket, MissingObjectError
from waterfall.platform.tasks import Task
from waterfall.worker.backup import (
    CHUNK,
    DATABASES,
    MANIFEST,
    DumpError,
    connect,
    connection,
    digest,
    reached,
)

BACKUP_FROM_NEWER_VERSION = "BACKUP_FROM_NEWER_VERSION"
FILE_FORMAT_UNREADABLE = "FILE_FORMAT_UNREADABLE"

logger = get_logger(__name__)


class IdentityProvider(Protocol):
    """What a restoration asks of the identity provider: its sessions closed, its caches cleared."""

    def close_every_session(self) -> None:
        """Close every session of the realm."""

    def clear_caches(self) -> None:
        """Forget what the provider keeps in memory of its database."""


def release(version: str) -> tuple[int, ...]:
    """Give the numbers of the release of a version, ``1.10.2`` before ``1.9`` never."""
    numbers = re.findall(r"\d+", version.split("+", maxsplit=1)[0])
    return tuple(int(number) for number in numbers[:3])


def extracted(path: Path, folder: Path) -> dict[str, Path]:
    """Read an archive: its manifest, a version no newer than the installed one, each dump checked.

    A newer version is refused (422, ``BACKUP_FROM_NEWER_VERSION``); an archive that does not read
    back whole, as unreadable (422). Nothing of the archive is extracted but under a name chosen
    here.
    """
    try:
        with tarfile.open(path) as tar:
            manifest = json.loads(_member(tar, MANIFEST).read())
            version = str(manifest["application_version"])
            if release(version) > release(__version__):
                params = {"backup_version": version, "installed_version": __version__}
                raise UnprocessableError(BACKUP_FROM_NEWER_VERSION, params)
            dumps: dict[str, Path] = {}
            for database in manifest["databases"]:
                copy = folder / f"restored-{len(dumps)}.dump"
                with copy.open("wb") as written:
                    shutil.copyfileobj(_member(tar, database["file"]), written, CHUNK)
                if digest(copy) != database["sha256"]:
                    raise UnprocessableError(FILE_FORMAT_UNREADABLE)
                dumps[str(database["name"])] = copy
    except (tarfile.TarError, OSError, KeyError, TypeError, ValueError) as error:
        raise UnprocessableError(FILE_FORMAT_UNREADABLE) from error
    if sorted(dumps) != sorted(DATABASES):
        raise UnprocessableError(FILE_FORMAT_UNREADABLE)
    return dumps


def _member(tar: tarfile.TarFile, name: str) -> Any:
    member = tar.extractfile(name)
    if member is None:
        raise KeyError(name)
    return member


def replace(name: str, dump: Path, address: str, folder: Path) -> None:
    """Make a database again from its dump, as its owner: its schema dropped, the dump restored.

    The dump is restored in one transaction, without the owners and the rights of the source: the
    role of the service of another installation has another name. A database that stops answering
    is unavailable (503), one that answers and refuses the dump an internal error (#907).
    """
    with connect(address) as session:
        session.execute("DROP SCHEMA public CASCADE")
        session.execute("CREATE SCHEMA public")
    environment = connection(address, folder / f"{name}.service")
    with dump.open("rb") as read:
        done = subprocess.run(
            [
                "/usr/bin/pg_restore",
                # The service ``connection`` writes (``SERVICE`` of the backup).
                "--dbname=service=backup",
                "--single-transaction",
                "--exit-on-error",
                "--no-owner",
                "--no-privileges",
                "--no-password",
            ],
            stdin=read,
            capture_output=True,
            env=environment,
            check=False,
        )
    if done.returncode != 0:
        reached(address)
        logger.error("restore.replace_failed", database=name, said=done.stderr.decode().strip())
        raise DumpError(name)


class RestoreTask:
    """Restore a backup of the two databases, as the worker runs a task of the kind ``restore``."""

    def __init__(
        self,
        databases: Mapping[str, str],
        bucket: Bucket,
        maintenance: Maintenance,
        provider: IdentityProvider,
        migrate: Callable[[Engine], None],
    ) -> None:
        self.databases = databases
        self.migrate = migrate
        self.bucket = bucket
        self.maintenance = maintenance
        self.provider = provider

    def __call__(self, session: Session, task: Task) -> dict[str, Any]:
        """Read the archive, hold the maintenance, replace, write back, inscribe, then lift.

        The session of the worker is not used before the databases are replaced: a lock it held
        on a table would hold up the replacement, which waits for it.
        """
        backup_id = UUID(task.payload["backup_id"])
        with tempfile.TemporaryDirectory(prefix="waterfall-restore-") as work:
            folder = Path(work)
            archive = folder / "restored.tar"
            try:
                self.bucket.download(task.payload["object_key"], archive)
            except MissingObjectError:
                raise NotFoundError(NOT_FOUND) from None
            dumps = extracted(archive, folder)
            owner = create_database_engine(self.databases["waterfall"])
            try:
                actor = self.hold(owner, task)
                self.provider.close_every_session()
                self.maintenance.close_front_sessions()
                self.keep(owner, task.task_id)
                for name in DATABASES:
                    replace(name, dumps[name], self.databases[name], folder)
                self.provider.clear_caches()
                self.migrate(owner)
                at = utc_now()
                with owner.begin() as written:
                    write_back_after_restoration(written, task.task_id, at)
            finally:
                owner.dispose()
        self.provider.close_every_session()
        self.maintenance.close_front_sessions()
        inscribe_restoration(session, backup_id, actor, at)
        self.maintenance.lift()
        logger.info("restore.done", backup_id=str(backup_id))
        return {"backup_id": str(backup_id)}

    def hold(self, owner: Engine, task: Task) -> AuditActor | None:
        """Hold the platform in maintenance, and name who asked for the restoration.

        Named as it was when it was asked for, which the maintenance keeps: the restored database
        may not hold the account, and an attempt taken up reads a database already replaced.
        """
        held = self.maintenance.current()
        if held is not None and held.task_id == task.task_id and "actor" in held.payload:
            named = held.payload["actor"]
            actor = None if named is None else AuditActor(UUID(named[0]), named[1])
        else:
            with Session(owner) as reading, reading.begin():
                actor = inscribed_actor(reading, task.requested_by)
        kept = None if actor is None else [str(actor.user_id), actor.display_name]
        self.maintenance.hold(
            Restoring(
                task.task_id,
                {**task.payload, "actor": kept},
                task.requested_by,
                task.correlation_id,
                task.attempt,
            )
        )
        return actor

    def keep(self, owner: Engine, task_id: UUID) -> None:
        """Keep, once, what the restoration writes back: the journal, the backups, their tasks."""
        with owner.begin() as kept:
            keep_for_restoration(kept, task_id)
