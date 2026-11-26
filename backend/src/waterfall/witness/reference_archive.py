# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reference set kept as a backup, and restored by what needs it (US-2950, #4114).

Engendered in most of an hour, the set is engendered once per version, then kept as a backup: the
paths, the measure and the exercise of recovery restore it instead (EP-13, "Le jeu de données de
référence"). Neither actor, nor route, nor token of an administrator:

- ``waterfall-api backup-reference [--projects N --revisions R --cost-lines C] --into DIR`` checks
  that the platform holds the set whole, as ``check-reference`` does — a real installation holds no
  witness, and is refused —, then deposits a backup as the schedule does, without a requester
  (``deposit_backup``): the worker takes it, verifies it and writes its manifest, as any backup the
  platform takes of itself. Once it is verified, its archive is read from the bucket of the backups
  into ``DIR``, its manifest beside it, under the name of the version and the seed
  (``archive_name``), readable by their owner alone: the archive holds the database of the identity
  provider, the secrets of its clients included.
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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall import __version__, schema
from waterfall.core.backups.interface import read_backup
from waterfall.migrations.runner import upgrade
from waterfall.platform.audit import Act
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine, utc_now
from waterfall.platform.errors import UnprocessableError
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
from waterfall.worker.backup import TASK_DEADLINE
from waterfall.worker.schedule import deposit_backup

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

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
            with database.transaction() as session:
                faults = reference_check.check(session, witness, wanted, history).faults
            if faults:
                logger.error("reference.not_whole", faults=len(faults), first=faults[0])
                return 1
            deposited = deposit_backup(database, queue)
            if isinstance(deposited, list):
                logger.error("reference.backup_held_back", missing_condition=deposited[0])
                return 1
            result = ended(database, deposited, waiting or Waiting())
            if result is None:
                return 1
            with database.transaction() as session:
                backup = read_backup(session, UUID(str(result["backup_id"])))
            name = archive_name(wanted, history)
            kept(Bucket.of_backups(settings), backup.object_key, into, name)
            logger.info("reference.kept", backup_id=str(backup.backup_id), archive=name)
            return 0
    finally:
        queue.close()
        database.dispose()


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


def kept(bucket: Bucket, key: str, into: Path, name: str) -> None:
    """Read an archive from the bucket into ``into``, its manifest beside it, for their owner alone.

    Each is written under a name of its own, then renamed, the archive last: an archive present is
    whole, and its manifest is there.
    """
    archive, manifest = into / f"{name}{ARCHIVE}", into / f"{name}{MANIFEST}"
    writing = into / f".{name}{ARCHIVE}.writing"
    described = into / f".{name}{MANIFEST}.writing"
    before = os.umask(PRIVATE)
    try:
        bucket.download(key, writing)
        described.write_text(json.dumps(manifest_of(writing), indent=2), encoding="utf-8")
        described.replace(manifest)
        writing.replace(archive)
    finally:
        os.umask(before)
        writing.unlink(missing_ok=True)
        described.unlink(missing_ok=True)


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
        except NotFreshError:
            logger.exception("reference.platform_not_fresh")
            return 1
        except UnprocessableError as error:
            # An archive refused before anything changed: a state to say, not a trace.
            refused = error.code
        else:
            logger.info("reference.restored", archive=archive.name)
            return 0
    logger.error("reference.archive_refused", archive=archive.name, code=refused)
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
