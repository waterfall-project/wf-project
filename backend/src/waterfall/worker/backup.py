# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``backup``: the two databases dumped, archived, stored and verified (WF-ADM-0150).

Each database is dumped by ``pg_dump``, in its custom format and in one consistent snapshot of its
own, as the role of the backup, a member of ``pg_read_all_data`` that can neither write nor turn a
trigger off (#701, #895): Waterfall's, the journal of audit included (WF-SEC-0030, #705), and the
identity provider's. Only the schema ``public`` of each is dumped, with the extensions it uses and
the large objects of the database: the schema ``platform``, where a restoration holds the
maintenance, is the installation's and not the backup's, and a restoration replaces ``public``
alone (EP-13, US-2830); Keycloak keeps its tables in ``public``, as long as ``KC_DB_SCHEMA`` is
not set. The archive — the two dumps, and a manifest that gives the date, the version of the
application, the revision of the schema, the digest of each dump, and what the test of a restoration
compares, counted in the snapshot of each database that ``pg_dump`` then dumps
(``waterfall.worker.inventory``, US-2930, #4572) — is written to the bucket of the backups under a
key the task names, so that a task taken up again writes over what an attempt left. It is then read
back from the bucket and verified: the manifest read, each dump against its digest, each dump listed
by ``pg_restore``. The backup is recorded with the outcome of that verification, and inscribed in
the journal at its date. A backup verified turns the list: the oldest backups not marked beyond the
retention of the schedule go, and their archives with them once the transaction is committed
(WF-ADM-0170). An archive that fails its verification fails the task, manual or scheduled, by
``UndoneError``: the work is undone, then the row is written, ``failed``, with its archive; neither
the rotation nor a copy follows, and the task alone says the failure (#4230).

What the task costs is bounded (#896, #4191): a connection waits a few seconds to be made, and
``pg_dump`` a minute for a lock and hours for its dump; the folder of the task holds the dumps and
the archive made of them, then the archive read back, one dump of it at a time, never about four
times the databases; and an archive no row names is removed when the task stops by an exception
once it may be in the bucket. Two cases stay outside that guard: the validation of the
transaction that follows the task, which may still fail once the task has returned, and the death
of the worker, which leaves the archive in the bucket without a row; the task of purge removes such
an archive once it is older than a day (``waterfall.worker.purge``, #4679). The transaction of the
worker stays open for the whole task — the dumps, the upload, the reading back, the verification
—, for the lock of the run it holds (``waterfall.worker.runner``, whose closing is #4681):
``TASK_DEADLINE`` bounds the task, and not each dump alone. Each dump is given what is left of it,
and the task, checked between its steps, stops and says so (``backup.deadline_exceeded``) once it
is spent; a step in progress — an upload, a download — is not interrupted by it.
"""

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

import psycopg

from waterfall import __version__
from waterfall.core.backups.interface import (
    MANIFEST,
    TakenBackup,
    add_backup,
    deposit_copy,
    read_backup_schedule,
    rotate,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import engine_url, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import get_logger
from waterfall.platform.settings import RealmSettings
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import UndoneError
from waterfall.worker.identity_sync import after_commit
from waterfall.worker.inventory import Inventory, accounts_of, counted_in, read_while

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import datetime

    from psycopg.rows import TupleRow
    from sqlalchemy.orm import Session

    from waterfall.platform.settings import WorkerSettings
    from waterfall.platform.tasks import Task

# The form of the archive, which a restoration reads (US-0440/L2).
ARCHIVE_FORMAT = 1
CHUNK = 1 << 20
COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
# What the task spends, bounded (#896, #4191), in seconds: how long a connection to a database waits
# to be made — a database that does not answer fails the task as unavailable instead of holding it
# —, and how long a dump may last. ``pg_dump`` waits a minute for a lock on a table, by the option
# it is given. The transaction of the worker stays open for the whole task, for its lock of the run
# (``runner``, #4681): the deadline of the task, which the dumps share, is what bounds it.
CONNECT_TIMEOUT = 10
DUMP_DEADLINE = 4 * 3600
TASK_DEADLINE = 4 * 3600
# The databases of the platform, by their name in the archive: Waterfall's, the identity provider's.
DATABASES = ("waterfall", "identity_provider")
# The connection service a dump reaches its database by.
SERVICE = "backup"
# The realm of the installation, whose accounts a backup counts, unless the settings name another:
# the default of the settings, which no other place writes (#4662).
REALM = str(RealmSettings.model_fields["keycloak_realm"].default)
# The event a database the backup cannot reach writes to the journal of the service.
UNREACHED = "backup.database_unreached"

logger = get_logger(__name__)


class UnverifiedArchiveError(RuntimeError):
    """An archive that failed its verification: the task fails as an internal error (#4230)."""


class DeadlineError(RuntimeError):
    """The task lasted beyond its deadline: it stops, as an internal error (#896)."""


class DumpError(RuntimeError):
    """A database reached that pg_dump could not dump: an internal error, not an outage."""


class RevisionError(RuntimeError):
    """A database reached whose revision of the schema cannot be read: an internal error (#908)."""


class AddressError(ValueError):
    """An address a connection service file cannot hold as it is: an internal error (#908).

    It names the keyword, never the value, which may be a secret.
    """


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
    for key, value in keywords.items():
        _refuse_unwritable(key, value)
    lines = [f"[{SERVICE}]", *(f"{key}={value}" for key, value in keywords.items())]
    service_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PGSERVICEFILE": str(service_file),
        "PGSERVICE": SERVICE,
        "PGCONNECT_TIMEOUT": str(CONNECT_TIMEOUT),
    }
    if isinstance(given, str) and given:
        environment["PGPASSWORD"] = given
    return environment


def _refuse_unwritable(key: str, value: str) -> None:
    """Refuse a keyword or a value that a line of the file of services cannot carry (#908).

    A line break would add a line of the operator's choosing to the file, and libpq takes off the
    spaces at the edge of a value: either way the database reached would not be the one named.
    """
    if (
        not key
        or any(character in key for character in "=\r\n")
        or key != key.strip()
        or "\r" in value
        or "\n" in value
        or value != value.strip()
    ):
        message = f"the address holds a value the file of services cannot write: {key!r}"
        raise AddressError(message)


def unavailable_database() -> UnavailableError:
    """Refuse as the contract does when a database does not answer (503)."""
    return UnavailableError(COMPONENT_UNAVAILABLE, {"component": "database"})


def dump(
    name: str,
    address: str,
    folder: Path,
    timeout: float | None = None,
    snapshot: str | None = None,
) -> Dumped:
    """Dump a database in the custom format, in one snapshot, once it has been reached.

    ``snapshot`` is one PostgreSQL exported (``pg_export_snapshot()``) and keeps open: the dump
    reads that state, the one the backup counted (#4572). Without it, ``pg_dump`` takes its own.

    A database that stops answering while it is dumped — PostgreSQL restarted, its connections
    spent — is a component out of reach (503, #907): the dump that fails reaches the database
    again. One that still answers and that ``pg_dump`` cannot dump — a right it lacks, a version it
    does not read — is an internal error, which says why to the journal of the service.

    The dump is stopped after ``timeout`` seconds, ``DUMP_DEADLINE`` unless given.

    The tools of PostgreSQL are those of the system, which Debian and Ubuntu put in ``/usr/bin``.
    """
    allowed = DUMP_DEADLINE if timeout is None else min(timeout, DUMP_DEADLINE)
    path = folder / f"{name}.dump"
    environment = connection(address, folder / f"{name}.service")
    with path.open("wb") as written:
        try:
            done = _pg_dump(written, environment, allowed, snapshot)
        except subprocess.TimeoutExpired:
            reached(address)
            logger.exception("backup.dump_timed_out", database=name, seconds=allowed)
            raise DumpError(name) from None
    if done.returncode != 0:
        said = done.stderr.decode(errors="replace").strip()
        reached(address)
        logger.error("backup.dump_failed", database=name, said=said)
        raise DumpError(name)
    return Dumped(name, path, path.stat().st_size, digest(path))


def _pg_dump(
    written: IO[bytes], environment: Mapping[str, str], timeout: float, snapshot: str | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run pg_dump into a file: it waits for a lock for a time, and runs for a time, bounded.

    The one value it is given is the snapshot PostgreSQL exported, never one from outside.
    """
    return subprocess.run(
        [
            "/usr/bin/pg_dump",
            "--format=custom",
            "--no-password",
            "--lock-wait-timeout=60s",
            # The schema the restoration replaces, and the extensions it uses and the large
            # objects, which a dump of one schema leaves out but those named: a column of the
            # database of Keycloak holds the identifiers of some (``cluster_event``).
            "--schema=public",
            "--extension=*",
            "--large-objects",
            *([] if snapshot is None else [f"--snapshot={snapshot}"]),
        ],
        stdout=written,
        stderr=subprocess.PIPE,
        env=environment,
        timeout=timeout,
        check=False,
    )


def connect(address: str, unreached: str = UNREACHED) -> psycopg.Connection[TupleRow]:
    """Connect to a database; unavailable if the connection fails (503).

    ``unreached`` names the event the journal of the service gets then: the backup's, or the
    restoration's.
    """
    conninfo = engine_url(address).set(drivername="postgresql")
    try:
        return psycopg.connect(
            conninfo.render_as_string(hide_password=False), connect_timeout=CONNECT_TIMEOUT
        )
    except psycopg.OperationalError as error:
        logger.warning(unreached, error=type(error).__name__)
        raise unavailable_database() from error


def reached(address: str, unreached: str = UNREACHED) -> None:
    """Tell that a database answers; unavailable if it does not (503), ``unreached`` journaled."""
    with connect(address, unreached) as connection:
        connection.execute("SELECT 1")


def schema_revision(address: str) -> str:
    """Read the revision of the schema the migrations have brought the database to.

    Reading it reaches the database: unavailable if it does not answer (503), and an internal
    error if it answers and the revision cannot be read — a database that is not migrated, a right
    it lacks —, which says why to the journal of the service (#908), as a dump does.
    """
    try:
        with connect(address) as connection:
            row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    except psycopg.Error as error:
        said = str(error).strip()
        reached(address)
        logger.exception("backup.revision_unreadable", said=said)
        raise RevisionError from error
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

    Nothing of the archive is extracted but under a name chosen here, and one dump at a time: the
    copy is removed once it has been read, so that the folder never holds more than one (#896).
    """
    try:
        with tarfile.open(path) as tar:
            databases = json.loads(_member(tar, MANIFEST).read())["databases"]
            names = [database["name"] for database in databases]
            for index, database in enumerate(databases):
                copy = folder / f"verified-{index}.dump"
                try:
                    with copy.open("wb") as written:
                        shutil.copyfileobj(_member(tar, database["file"]), written, CHUNK)
                    if digest(copy) != database["sha256"] or not listed(copy):
                        return False
                finally:
                    copy.unlink(missing_ok=True)
    except tarfile.TarError, OSError, KeyError, TypeError, ValueError:
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


class Deadline:
    """What is left of the time of a task, from the moment it began."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self.began = time.monotonic()

    def left(self) -> float:
        """Give the seconds left, or stop the task, saying so, once there are none."""
        left = self.seconds - (time.monotonic() - self.began)
        if left <= 0:
            logger.error("backup.deadline_exceeded", seconds=self.seconds)
            raise DeadlineError(self.seconds)
        return left


class BackupTask:
    """Take a backup of the two databases, as the worker runs a task of the kind ``backup``."""

    def __init__(self, databases: Mapping[str, str], bucket: Bucket, realm: str = REALM) -> None:
        """Dump ``databases`` into ``bucket``; count the accounts of ``realm``, the installation."""
        self.databases = databases
        self.bucket = bucket
        self.realm = realm

    @classmethod
    def of(cls, settings: WorkerSettings) -> BackupTask:
        """Dump the databases the settings name, as the role of the backup, into its bucket."""
        reached_as = (settings.backup_database_url, settings.keycloak_database_url)
        addresses = (address.get_secret_value() for address in reached_as)
        databases: dict[str, str] = dict(zip(DATABASES, addresses, strict=True))
        return cls(databases, Bucket.of_backups(settings), settings.keycloak_realm)

    def __call__(self, session: Session, task: Task) -> dict[str, Any]:
        """Dump, archive, store, read back and verify; record the backup, and inscribe it."""
        taken_at = utc_now()
        deadline = Deadline(TASK_DEADLINE)
        key = f"backup-{task.task_id}.tar"
        with tempfile.TemporaryDirectory(prefix="waterfall-backup-") as work:
            folder = Path(work)
            revision = schema_revision(self.databases["waterfall"])
            reached(self.databases["identity_provider"])
            dumps, inventory = self._dumped(folder, deadline)
            path = folder / "backup.tar"
            archive(path, manifest(taken_at, revision, dumps, inventory), dumps)
            size_bytes = path.stat().st_size
            # The folder holds the archive and the dumps it was made of, then the archive read back:
            # what a step is done with is removed before the next, so that it never holds more than
            # about twice the dumps (#896).
            _free(folder / MANIFEST, *(dumped.path for dumped in dumps))
            try:
                deadline.left()
                self.bucket.upload(key, path)
                _free(path)
                deadline.left()
                stored = folder / "stored.tar"
                self.bucket.download(key, stored)
                deadline.left()
                is_verified = verified(stored, folder)
                deadline.left()
                taken = TakenBackup(
                    task.task_id,
                    taken_at,
                    size_bytes,
                    key,
                    __version__,
                    revision,
                    is_verified=is_verified,
                )
                if is_verified:
                    backup_id = add_backup(session, taken, Act(task.requested_by, taken_at))
                    self._rotate(session)
                    deposit_copy(session, backup_id)
                    logger.info("backup.taken", backup_id=str(backup_id), size_bytes=size_bytes)
                    return {"backup_id": str(backup_id), "verification": "passed"}
            except BaseException:
                # Any exception that stops the work once the archive may be in the bucket — the
                # deadline included — leaves no row to name it. Not the validation of the
                # transaction that follows, nor the death of the worker (#4679).
                self._discard(key)
                raise
            # The archive stays: the row the trace writes names it (#4230).
            trace = self._failed_trace(task, taken, lambda: self._discard(key))
            raise UndoneError(UnverifiedArchiveError(key), trace)

    def _dumped(self, folder: Path, deadline: Deadline) -> tuple[list[Dumped], Inventory | None]:
        """Count what each database holds, then dump it, so that the manifest says what it holds.

        The accounts are counted in the database of the identity provider, the rest in Waterfall's;
        nothing, if either does not hold what is counted.
        """
        waterfall, provider = (self.databases[name] for name in DATABASES)
        # Each database is counted and dumped in the same snapshot, which stays open: what is
        # written between the counts and the dump cannot part the manifest from the dump (#4572).
        accounts, provided = read_while(
            provider,
            lambda connection: accounts_of(connection, self.realm),
            lambda snapshot: dump(DATABASES[1], provider, folder, deadline.left(), snapshot),
        )
        inventory, dumped = read_while(
            waterfall,
            lambda connection: None if accounts is None else counted_in(connection, accounts),
            lambda snapshot: dump(DATABASES[0], waterfall, folder, deadline.left(), snapshot),
        )
        return [dumped, provided], inventory

    @staticmethod
    def _failed_trace(
        task: Task, taken: TakenBackup, discard: Callable[[], None]
    ) -> Callable[[Session], None]:
        """Write the backup whose archive failed its verification, once the task's work is undone.

        The row stays listed, ``verification`` at ``failed``, with its archive; no rotation and no
        external copy follow (WF-ADM-0170, #4230). The task itself fails as an internal error. A
        row that cannot be written leaves nothing to name the archive: ``discard`` removes it
        (#4515), and the fault goes on.
        """

        def trace(session: Session) -> None:
            try:
                backup_id = add_backup(session, taken, Act(task.requested_by, taken.taken_at))
            except BaseException:
                discard()
                raise
            logger.error(
                "backup.verification_failed",
                backup_id=str(backup_id),
                size_bytes=taken.size_bytes,
            )

        return trace

    def _rotate(self, session: Session) -> None:
        """Turn the list under the retention of the schedule; remove the archives once committed."""
        retained = read_backup_schedule(session).schedule.retained_count
        gone = rotate(session, retained)
        after_commit(session, lambda: self._remove(gone))

    def _remove(self, keys: list[str]) -> None:
        """Remove the archives of the backups the rotation deleted; a failure is only logged."""
        for key in keys:
            try:
                self.bucket.remove(key)
            except Exception:
                logger.exception("backup.archive_not_removed", key=key)

    def _discard(self, key: str) -> None:
        """Remove an archive no backup names (WF-DAT-0120); a removal that fails is logged only.

        It runs while the fault of the backup is being raised, which it must not hide.
        """
        try:
            self.bucket.remove(key)
        except Exception:
            logger.exception("backup.archive_not_removed", key=key)


def _free(*paths: Path) -> None:
    """Remove files of the folder of a task that nothing reads any more."""
    for path in paths:
        path.unlink(missing_ok=True)


def manifest(
    taken_at: datetime, revision: str, dumps: list[Dumped], inventory: Inventory | None
) -> dict[str, Any]:
    """Describe the archive: when, by which version, at which revision, each dump's digest.

    And what it holds, which the test of its restoration compares (US-2930), if it was counted.
    """
    described: dict[str, Any] = {
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
    if inventory is not None:
        described["inventory"] = inventory.described()
    return described
