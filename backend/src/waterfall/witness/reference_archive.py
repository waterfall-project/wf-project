# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference set kept as a backup, and restored by what needs it (US-2950, #4114).

Engendered in most of an hour, the set is engendered once per version, then kept as a backup: the
paths, the measure and the exercise of recovery restore it instead (EP-13, "Le jeu de données de
référence"). Neither actor, nor route, nor token of an administrator:

- ``waterfall-api backup-reference [--projects N --revisions R --cost-lines C] --into DIR`` refuses
  a platform whose schedule sets an external copy not suspended — the copy of a scheduled backup
  would carry the archive, the secrets of the realm in it, out to its location — and one that does
  not hold the set whole, as ``check-reference`` reads it: a real installation holds no witness. It
  then deposits a backup as the schedule does, without a requester (``deposit_backup``): the worker
  takes it, verifies it and writes its manifest, as any backup the platform takes of itself, and is
  one of them: ``scheduled``, it turns the list under the retention of the schedule, is the one the
  test of a restoration elects next, and serves the occurrence of the schedule it follows
  (``backup_is_due``). Once it is verified, its archive is read from the bucket of the backups,
  downloaded under the locks of a deposit, verified again outside them, and kept in ``DIR``, its
  manifest beside it, under the name of the version and the seed (``archive_name``), readable by
  their owner alone: the archive holds the database of the identity provider, the secrets of its
  clients included.
- ``waterfall-api restore-reference [the same volumes] --from DIR`` restores that archive on a fresh
  platform, before it starts, as the test of a restoration restores a backup on its ephemeral
  platform (``waterfall.restore.fresh``).

Each ends 0; 1 on a set not whole, a backup held back, failed or not ended in time, an archive
missing or unreadable, a platform not fresh; 2 on a setting that lacks or volumes refused.
"""

import argparse
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall import __version__, schema
from waterfall.core.backups.interface import (
    lock_backup_deposit,
    read_backup,
    read_backup_schedule,
)
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import Act
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import NotFoundError, UnprocessableError
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.settings import (
    SettingsError,
    load_reference_backup_settings,
    load_reference_restore_settings,
)
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import PENDING, BackgroundTask
from waterfall.restore.fresh import NotFreshError, restore_fresh
from waterfall.restore.trial import manifest_of
from waterfall.witness import reference_check
from waterfall.witness.description import Witness
from waterfall.witness.reference_draw import PROJECTS, SEED
from waterfall.witness.reference_history import COST_LINES, MARKED, History, HistoryError
from waterfall.worker.backup import TASK_DEADLINE, verified
from waterfall.worker.schedule import deposit_backup

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from sqlalchemy.orm import Session

    from waterfall.platform.settings import ReferenceBackupSettings, ReferenceRestoreSettings

BACKUP = "backup-reference"
RESTORE = "restore-reference"
ARCHIVE = ".tar"
MANIFEST = ".manifest.json"
# Only their owner reads what the commands write: the archive holds the secrets of the realm.
PRIVATE = 0o077

logger = get_logger(__name__)


def archive_name(wanted: int, history: History) -> str:
    """Name the archive of a set: the version, the seed, and the volumes it was asked."""
    return f"reference-{__version__}-{SEED}-{wanted}-{history.marked}-{history.cost_lines}"


@dataclass(frozen=True, slots=True)
class Waiting:
    """How long the command waits for the backup: its task's deadline, and the queue before it."""

    patience: float = TASK_DEADLINE + 600.0
    pause: float = 2.0
    clock: Callable[[], float] = field(default=time.monotonic)
    sleep: Callable[[float], None] = field(default=time.sleep)


def backup_reference(
    settings: ReferenceBackupSettings,
    wanted: int,
    history: History,
    into: Path,
    waiting: Waiting | None = None,
) -> int:
    """Check the set, have it backed up, keep its archive and its manifest in ``into``."""
    schema.declared()
    witness = Witness(Path(settings.witness_path), Act(None, utc_now()))
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=DEPOSIT_TIMEOUT)
    try:
        with (
            TIME_ZONE.reading_from(stored_in(database)),
            logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM),
        ):
            if refused(
                database, lambda session: reference_check.check(session, witness, wanted, history)
            ):
                return 1
            deposited = deposit_backup(database, queue)
            if isinstance(deposited, list):
                logger.error("reference.backup_held_back", missing_condition=deposited[0])
                return 1
            result = ended(database, deposited, waiting or Waiting())
            if result is None:
                return 1
            backup_id, name = UUID(str(result["backup_id"])), archive_name(wanted, history)
            if not kept(database, Bucket.of_backups(settings), backup_id, into / name):
                return 1
            logger.info("reference.kept", backup_id=str(backup_id), archive=name)
            return 0
    finally:
        queue.close()
        database.dispose()


def refused(database: Database, checked: Callable[[Session], reference_check.Report]) -> bool:
    """Tell whether the platform is refused, before anything is deposited, and say why in the logs.

    Refused, a platform whose schedule sets an external copy not suspended: the worker would
    deposit the copy of the backup (``deposit_copy``), the secrets of the realm in its archive. A
    copy set or resumed while the backup runs is not seen: the platform holds the reference set, no
    real installation does. Refused, then, a platform that does not hold the set whole
    (``checked``).
    """
    with database.transaction() as session:
        copy = read_backup_schedule(session).schedule.external_copy
        if copy is not None and copy.is_enabled:
            logger.error("reference.external_copy_set", location=copy.location)
            return True
        faults = checked(session).faults
    if faults:
        logger.error("reference.not_whole", faults=len(faults), first=faults[0])
        return True
    return False


def ended(database: Database, task_id: UUID, waiting: Waiting) -> dict[str, Any] | None:
    """Wait for the task of the backup to end; give its result, or ``None`` if it did not succeed.

    A task that failed, or that has not ended once ``waiting`` is spent, is said in the logs.
    """
    deadline = waiting.clock() + waiting.patience
    while True:
        with database.transaction() as session:
            task = session.get(BackgroundTask, task_id)
            status = None if task is None else task.status
            result = None if task is None else task.result
        if status == "succeeded" and result is not None:
            return result
        if status not in PENDING:
            logger.error("reference.backup_failed", task_id=str(task_id), status=status)
            return None
        if waiting.clock() >= deadline:
            logger.error("reference.backup_not_ended", task_id=str(task_id), status=status)
            return None
        waiting.sleep(waiting.pause)


def kept(
    database: Database,
    bucket: Bucket,
    backup_id: UUID,
    named: Path,
    waiting: Waiting | None = None,
) -> bool:
    """Read the archive of a backup into ``named``, its manifest beside it, for their owner alone.

    It is downloaded under the locks of a deposit (``lock_backup_deposit``), none pending: no backup
    runs nor is deposited meanwhile, whose rotation would delete it — with a retention of one, the
    next scheduled backup would. The locks are held to the end of the download alone, a transaction
    that holds them while the archive is verified would hold back a ``startBackup``, the scheduled
    backup and the deposit of a restoration for as long: the file is local, the rotation can no
    longer touch it. A backup deposited between its end and the download (``ended``, then here)
    holds the archive back; it is taken once more after a pause (``waiting``), then said. Then the
    archive is verified again, as the worker verified it (``verified``): an object cut short, or
    unlike its manifest, keeps nothing. Each is written under a name of its own, then renamed, the
    archive last: an archive present is whole, and its manifest is there. Gives whether they are
    kept; why not is said in the logs.
    """
    waiting = waiting or Waiting()
    into, name = named.parent, named.name
    archive, manifest = into / f"{name}{ARCHIVE}", into / f"{name}{MANIFEST}"
    writing = into / f".{name}{ARCHIVE}.writing"
    described = into / f".{name}{MANIFEST}.writing"
    before = os.umask(PRIVATE)
    try:
        writing.unlink(missing_ok=True)
        lacking = downloaded(database, bucket, backup_id, writing)
        if lacking:
            logger.info("reference.archive_not_read_yet", missing_condition=lacking[0])
            waiting.sleep(waiting.pause)
            lacking = downloaded(database, bucket, backup_id, writing)
        if lacking:
            logger.error("reference.archive_not_read", missing_condition=lacking[0])
            return False
        if not writing.exists():
            logger.error("reference.backup_gone", backup_id=str(backup_id))
            return False
        with tempfile.TemporaryDirectory(prefix=".reference-", dir=into) as work:
            if not verified(writing, Path(work)):
                logger.error("reference.archive_unverified", backup_id=str(backup_id))
                return False
        described.write_text(json.dumps(manifest_of(writing), indent=2), encoding="utf-8")
        described.replace(manifest)
        writing.replace(archive)
        return True
    finally:
        os.umask(before)
        writing.unlink(missing_ok=True)
        described.unlink(missing_ok=True)


def downloaded(database: Database, bucket: Bucket, backup_id: UUID, into: Path) -> list[str]:
    """Download the archive of a backup into ``into``, under the locks of a deposit.

    Gives what holds the deposit back, nothing downloaded; empty otherwise. A backup the list does
    not hold leaves ``into`` absent: the caller says it gone.
    """
    with database.transaction() as session:
        lacking = lock_backup_deposit(session)
        if lacking:
            return lacking
        try:
            key: str | None = read_backup(session, backup_id).object_key
        except NotFoundError:
            key = None
        if key is not None:
            bucket.download(key, into)
    return []


def restore_reference(settings: ReferenceRestoreSettings, archive: Path) -> int:
    """Restore the archive of a set on the fresh platform the settings name, before it starts."""
    databases = {
        "waterfall": settings.database_url.get_secret_value(),
        "identity_provider": settings.keycloak_database_url.get_secret_value(),
    }
    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        if not archive.is_file():
            logger.error("reference.archive_missing", archive=archive.name)
            return 1
        try:
            restore_fresh(archive, databases, upgrade)
        # A platform not fresh, an archive refused, each before anything changed: a state to say,
        # not a trace.
        except NotFreshError as error:
            event, said = "reference.platform_not_fresh", {"reason": str(error)}
        except UnprocessableError as error:
            event, said = "reference.archive_refused", {"archive": archive.name, "code": error.code}
        else:
            logger.info("reference.restored", archive=archive.name)
            return 0
        logger.error(event, **said)
    return 1


def main(command: str, arguments: Sequence[str]) -> int:
    """Run ``backup-reference`` or ``restore-reference``; a fault of the arguments ends it (2)."""
    backing_up = command == BACKUP
    parser = argparse.ArgumentParser(
        prog=f"waterfall-api {command}",
        description="Keep the reference set as a backup, out of the platform."
        if backing_up
        else "Restore the reference set kept, on a fresh platform, before it starts.",
    )
    parser.add_argument("--projects", type=int, default=PROJECTS)
    parser.add_argument("--revisions", type=int, default=MARKED)
    parser.add_argument("--cost-lines", type=int, default=COST_LINES)
    folder_option = "--into" if backing_up else "--from"
    parser.add_argument(folder_option, dest="folder", type=Path, required=True)
    parsed = parser.parse_args(arguments)
    folder: Path = parsed.folder
    if not folder.is_dir():
        sys.stderr.write(f"waterfall-api {command}: {folder}: is not a directory\n")
        return 2
    asked = (parsed.projects, History(parsed.revisions, parsed.cost_lines))
    try:
        return _backed_up(asked, folder) if backing_up else _restored(asked, folder)
    except SettingsError as error:
        sys.stderr.write(f"waterfall-api {command}: {error}\n")
    except HistoryError as refused:
        sys.stderr.write(f"waterfall-api {command}: {refused}\n")
    return 2


def _backed_up(asked: tuple[int, History], folder: Path) -> int:
    settings = load_reference_backup_settings()
    configure_logging(settings.log_level, secrets=settings.secret_values())
    status = backup_reference(settings, *asked, folder)
    if status == 0:
        sys.stdout.write(f"{archive_name(*asked)}{ARCHIVE}\n")
    return status


def _restored(asked: tuple[int, History], folder: Path) -> int:
    settings = load_reference_restore_settings()
    configure_logging(settings.log_level, secrets=settings.secret_values())
    return restore_reference(settings, folder / f"{archive_name(*asked)}{ARCHIVE}")
