# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``backup``: the two databases dumped, archived, stored and verified (WF-ADM-0150).

Each database is dumped by ``pg_dump``, in its custom format and in one consistent snapshot of its
own, as the role of the backup, a member of ``pg_read_all_data`` that can neither write nor turn a
trigger off (#701, #895): Waterfall's, the journal of audit included (WF-SEC-0030, #705), and the
identity provider's. The archive — the two dumps, and a manifest that gives the date, the version of
the application, the revision of the schema and the digest of each dump — is written to the bucket
of the backups under a key the task names, so that a task taken up again writes over what an
attempt left. It is then read back from the bucket and verified: the manifest read, each dump
against its digest, each dump listed by ``pg_restore``. The backup is recorded with the outcome of
that verification, and inscribed in the journal at its date.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO, Any

import psycopg
from psycopg.rows import TupleRow
from sqlalchemy.orm import Session

from waterfall import __version__
from waterfall.core.backups.interface import TakenBackup, add_backup
from waterfall.core.users.interface import read_author
from waterfall.platform.audit import Act, AuditActor
from waterfall.platform.database import engine_url, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import get_logger
from waterfall.platform.settings import WorkerSettings
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import Task

# The form of the archive, which a restoration reads (US-0440/L2).
ARCHIVE_FORMAT = 1
MANIFEST = "manifest.json"
CHUNK = 1 << 20
COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
# The databases of the platform, by their name in the archive: Waterfall's, the identity provider's.
DATABASES = ("waterfall", "identity_provider")
# The connection service a dump reaches its database by.
SERVICE = "backup"

logger = get_logger(__name__)


class DumpError(RuntimeError):
    """A database reached that pg_dump could not dump: an internal error, not an outage."""


@dataclass(frozen=True, slots=True)
class Dumped:
    """A database dumped: its name in the archive, its file, its size and its digest."""

    name: str
    path: Path
    size_bytes: int
    sha256: str


def digest(path: Path) -> str:
    """Give the SHA-256 of a file, read by chunks."""
    hashed = hashlib.sha256()
    with path.open("rb") as read:
        while chunk := read.read(CHUNK):
            hashed.update(chunk)
    return hashed.hexdigest()


def connection(address: str, service_file: Path) -> dict[str, str]:
    """Give the tools of PostgreSQL a database by their environment: nothing on a command line.

    The address goes whole, its query included — ``sslmode``, ``sslrootcert``, a ``host`` that
    names a socket —, to a file of connection services that the environment names; the password,
    in the address or in its query, goes by ``PGPASSWORD``. A listing of the processes shows
    neither, and the command the worker runs is its own, never a value it was given.
    """
    url = engine_url(address)
    given = url.password if url.password is not None else url.query.get("password")
    named = {"host": url.host, "port": url.port, "dbname": url.database, "user": url.username}
    keywords = {key: str(value) for key, value in named.items() if value is not None}
    # A keyword given twice takes its last value, as libpq does.
    for key, values in url.normalized_query.items():
        if key != "password":
            keywords[key] = values[-1]
    lines = [f"[{SERVICE}]", *(f"{key}={value}" for key, value in keywords.items())]
    service_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PGSERVICEFILE": str(service_file),
        "PGSERVICE": SERVICE,
    }
    if isinstance(given, str) and given:
        environment["PGPASSWORD"] = given
    return environment


def unavailable_database() -> UnavailableError:
    """Refuse as the contract does when a database does not answer (503)."""
    return UnavailableError(COMPONENT_UNAVAILABLE, {"component": "database"})


def dump(name: str, address: str, folder: Path) -> Dumped:
    """Dump a database in the custom format, in one snapshot, once it has been reached.

    A database reached that ``pg_dump`` cannot dump — a right it lacks, a version it does not read
    — is not a component out of reach: the dump fails as an internal error, and says why to the
    journal of the service.

    The tools of PostgreSQL are those of the system, which Debian and Ubuntu put in ``/usr/bin``.
    """
    path = folder / f"{name}.dump"
    environment = connection(address, folder / f"{name}.service")
    with path.open("wb") as written:
        done = subprocess.run(
            ["/usr/bin/pg_dump", "--format=custom", "--no-password"],
            stdout=written,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )
    if done.returncode != 0:
        said = done.stderr.decode(errors="replace").strip()
        logger.error("backup.dump_failed", database=name, said=said)
        raise DumpError(name)
    return Dumped(name, path, path.stat().st_size, digest(path))


def connect(address: str) -> psycopg.Connection[TupleRow]:
    """Connect to a database to back it up; unavailable if the connection fails (503)."""
    conninfo = engine_url(address).set(drivername="postgresql")
    try:
        return psycopg.connect(conninfo.render_as_string(hide_password=False))
    except psycopg.OperationalError as error:
        logger.warning("backup.database_unreached", error=type(error).__name__)
        raise unavailable_database() from error


def reached(address: str) -> None:
    """Tell, before its dump, that a database answers; unavailable if it does not (503)."""
    with connect(address) as connection:
        connection.execute("SELECT 1")


def schema_revision(address: str) -> str:
    """Read the revision of the schema the migrations have brought the database to.

    Reading it reaches the database: unavailable if it does not answer (503), and an internal
    error if it answers and the revision cannot be read.
    """
    with connect(address) as connection:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    return "" if row is None else str(row[0])


def archive(path: Path, manifest: Mapping[str, Any], dumps: list[Dumped]) -> None:
    """Write the archive: the manifest first, then each dump under its name."""
    folder = path.parent
    (folder / MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    with tarfile.open(path, "w", format=tarfile.PAX_FORMAT) as tar:
        tar.add(folder / MANIFEST, arcname=MANIFEST)
        for dumped in dumps:
            tar.add(dumped.path, arcname=dumped.path.name)


def verified(path: Path, folder: Path) -> bool:
    """Read an archive back: its manifest, each dump against its digest and listed by pg_restore.

    Nothing of the archive is extracted but under a name chosen here.
    """
    try:
        with tarfile.open(path) as tar:
            databases = json.loads(_member(tar, MANIFEST).read())["databases"]
            names = [database["name"] for database in databases]
            for index, database in enumerate(databases):
                copy = folder / f"verified-{index}.dump"
                with copy.open("wb") as written:
                    shutil.copyfileobj(_member(tar, database["file"]), written, CHUNK)
                if digest(copy) != database["sha256"] or not listed(copy):
                    return False
    except (tarfile.TarError, OSError, KeyError, TypeError, ValueError):
        return False
    return names == list(DATABASES)


def listed(path: Path) -> bool:
    """Tell whether pg_restore reads the table of contents of a dump."""
    with path.open("rb") as read:
        done = subprocess.run(
            ["/usr/bin/pg_restore", "--list"], stdin=read, capture_output=True, check=False
        )
    return done.returncode == 0


def _member(tar: tarfile.TarFile, name: str) -> IO[bytes]:
    member = tar.extractfile(name)
    if member is None:
        raise KeyError(name)
    return member


class BackupTask:
    """Take a backup of the two databases, as the worker runs a task of the kind ``backup``."""

    def __init__(self, databases: Mapping[str, str], bucket: Bucket) -> None:
        self.databases = databases
        self.bucket = bucket

    @classmethod
    def of(cls, settings: WorkerSettings) -> "BackupTask":
        """Dump the databases the settings name, as the role of the backup, into its bucket."""
        reached_as = (settings.backup_database_url, settings.keycloak_database_url)
        addresses = (address.get_secret_value() for address in reached_as)
        return cls(dict(zip(DATABASES, addresses, strict=True)), Bucket.of_backups(settings))

    def __call__(self, session: Session, task: Task) -> dict[str, Any]:
        """Dump, archive, store, read back and verify; record the backup, and inscribe it."""
        taken_at = utc_now()
        key = f"backup-{task.task_id}.tar"
        with tempfile.TemporaryDirectory(prefix="waterfall-backup-") as work:
            folder = Path(work)
            revision = schema_revision(self.databases["waterfall"])
            reached(self.databases["identity_provider"])
            dumps = [dump(name, self.databases[name], folder) for name in DATABASES]
            path = folder / "backup.tar"
            archive(path, manifest(taken_at, revision, dumps), dumps)
            self.bucket.upload(key, path)
            stored = folder / "stored.tar"
            self.bucket.download(key, stored)
            is_verified = verified(stored, folder)
            size_bytes = path.stat().st_size
        taken = TakenBackup(
            task.task_id, taken_at, size_bytes, key, __version__, revision, is_verified=is_verified
        )
        author = read_author(session, task.requested_by)
        actor = None if author is None else AuditActor(author.user_id, author.display_name)
        backup_id = add_backup(session, taken, Act(actor, taken_at))
        logger.info(
            "backup.taken", backup_id=str(backup_id), size_bytes=size_bytes, verified=is_verified
        )
        return {"backup_id": str(backup_id), "verification": "passed" if is_verified else "failed"}


def manifest(taken_at: datetime, revision: str, dumps: list[Dumped]) -> dict[str, Any]:
    """Describe the archive: when, by which version, at which revision, and each dump's digest."""
    return {
        "format": ARCHIVE_FORMAT,
        "taken_at": taken_at.isoformat(),
        "application_version": __version__,
        "schema_revision": revision,
        "databases": [
            {
                "name": dumped.name,
                "file": dumped.path.name,
                "size_bytes": dumped.size_bytes,
                "sha256": dumped.sha256,
            }
            for dumped in dumps
        ],
    }
