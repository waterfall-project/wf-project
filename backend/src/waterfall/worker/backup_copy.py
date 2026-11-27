# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``backup_copy``: a scheduled backup copied to an external location (WF-ADM-0170).

A scheduled backup verified deposits it (``deposit_copy``, US-2910/L3). The worker reads the
archive from the bucket of the backups, writes it on the location the schedule names, in its
folder, under the name of the backup's date, reads it back — its size and its digest, against those
of the archive read —, then turns the copies of the folder to the number the schedule keeps there,
the oldest first (WF-EXP-0050). The result is written on the row of the backup, a copy refused with
its reason (``ExternalBackupFailure``). A refusal fails the task, by ``UndoneError``, its row
written: the task alone says the failure, as for the backup (#4230), which the gauge
``scheduled_backup_copy`` and the alert of the status screen read.

Nothing of a location goes to the journal but its name and the reason of a refusal: neither its
address nor its credentials (WF-OBS-0020).
"""

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from waterfall.core.backups.interface import (
    CopyMade,
    CopyToMake,
    copies_beyond,
    copy_to_make,
    record_copy,
)
from waterfall.platform.database import utc_now
from waterfall.platform.external_locations import (
    COPY_TIMEOUT,
    TIMED_OUT,
    UNREACHABLE,
    WRITE_FAILED,
    ExternalStore,
    LocationRefusedError,
    bounded,
    key_of,
    reached,
    store_of,
)
from waterfall.platform.logs import get_logger
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import UndoneError

if TYPE_CHECKING:
    import threading
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from waterfall.platform.settings import DeclaredLocation, ExternalLocations, WorkerSettings
    from waterfall.platform.tasks import Task

CHUNK = 1 << 20

logger = get_logger(__name__)


class CopyRefusedError(RuntimeError):
    """A copy the location refused: the task fails as an internal error, its reason on the row."""


class ArchiveChangedError(RuntimeError):
    """An archive the bucket gives at another size than its backup says: nothing is copied."""


@dataclass(frozen=True, slots=True)
class CopyTask:
    """Copy a backup to the location the schedule names, as the worker runs ``backup_copy``."""

    bucket: Bucket
    locations: ExternalLocations
    opened: Callable[[DeclaredLocation], ExternalStore] = store_of
    timeout: float = COPY_TIMEOUT

    @classmethod
    def of(cls, settings: WorkerSettings) -> CopyTask:
        """Copy from the bucket of the backups to the locations the settings declare.

        The writing, the reading back and the rotation take ``external_copy_timeout_seconds`` at
        most (#4656).
        """
        return cls(
            Bucket.of_backups(settings),
            settings.external_locations,
            timeout=settings.external_copy_timeout_seconds,
        )

    def __call__(self, session: Session, task: Task) -> dict[str, Any]:
        """Copy, read back, turn the copies of the folder; write the result on the backup's row."""
        backup_id = UUID(str(task.payload["backup_id"]))
        copy = copy_to_make(session, backup_id)
        if copy is None:
            logger.info("backup_copy.not_made", backup_id=str(backup_id))
            return {"backup_id": str(backup_id), "copied": False}
        try:
            removed = self._copied(copy)
        except LocationRefusedError as refused:
            made = CopyMade(utc_now(), copy.location, copy.path, refused.failure)
            raise UndoneError(CopyRefusedError(refused.failure), _trace(backup_id, made)) from None
        record_copy(session, backup_id, CopyMade(utc_now(), copy.location, copy.path))
        logger.info(
            "backup_copy.made",
            backup_id=str(backup_id),
            location=copy.location,
            removed=len(removed),
        )
        return {
            "backup_id": str(backup_id),
            "copied": True,
            "location": copy.location,
            "path": copy.path,
            "removed": len(removed),
        }

    def _copied(self, copy: CopyToMake) -> list[str]:
        """Write the archive on the location, check it read back, turn the folder; give the removed.

        A location the settings no longer declare is one the copy cannot reach; one that does not
        answer within ``timeout`` seconds is ``timed_out``.
        """
        declared = self.locations.get(copy.location)
        if declared is None:
            raise LocationRefusedError(UNREACHABLE)
        with tempfile.TemporaryDirectory(prefix="waterfall-copy-") as work:
            archive = Path(work) / copy.name
            self.bucket.download(copy.object_key, archive)
            expected = (archive.stat().st_size, _digest(archive))
            if expected[0] != copy.size_bytes:
                raise ArchiveChangedError(copy.object_key)
            return bounded(
                self.timeout,
                lambda abandoned: self._written(copy, declared, archive, expected, abandoned),
            )

    def _written(
        self,
        copy: CopyToMake,
        declared: DeclaredLocation,
        archive: Path,
        expected: tuple[int, str],
        abandoned: threading.Event,
    ) -> list[str]:
        """Write the archive, read it back and turn the folder; give the removed copies.

        Once ``abandoned`` is set — the time spent, the copy said ``timed_out`` — it goes no
        further: it does not read back, and erases no older copy.
        """
        key = key_of(copy.path, copy.name)
        with reached(declared, self.opened) as store:
            store.put(key, archive)
            _go_on(abandoned)
            if store.read_back(key) != expected:
                raise LocationRefusedError(WRITE_FAILED)
            gone = copies_beyond(store.names(copy.path), copy.retained_count)
            for name in gone:
                _go_on(abandoned)
                store.remove(key_of(copy.path, name))
        return gone


def _go_on(abandoned: threading.Event) -> None:
    """Refuse to go further once the copy has been said ``timed_out``."""
    if abandoned.is_set():
        raise LocationRefusedError(TIMED_OUT)


def _digest(path: Path) -> str:
    hashed = hashlib.sha256()
    with path.open("rb") as read:
        while chunk := read.read(CHUNK):
            hashed.update(chunk)
    return hashed.hexdigest()


def _trace(backup_id: UUID, made: CopyMade) -> Callable[[Session], None]:
    """Write a copy refused on the row of its backup, once the task's work is undone."""

    def trace(session: Session) -> None:
        record_copy(session, backup_id, made)
        logger.error(
            "backup_copy.refused",
            backup_id=str(backup_id),
            location=made.location,
            failure=made.failure,
        )

    return trace
