# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The task ``purge``: what expired in the database and in the object storage, and the old tasks.

The schedule deposits it (``waterfall.worker.schedule``) and the worker runs it, in the one
transaction of the task, as it runs any other: the planner reaches neither the storage nor the
tables (EP-13, "Une commande planifiée unique", #3963). It purges, in this order, what the
exchanges purge — the imports expired, the deposits, the exports of more than a day (EP-06, "La
purge") —, the history of the sessions over and the plans of a paste expired, then the tasks ended
for more than the retention of their result, with the report of a reading of the accounts they
carry (WF-DAT-0080, #921); the task of a backup still listed is spared, which the rotation alone
deletes. The archives of the backups sweep too: the object of the prefix ``backup-`` that no row
names and that is older than a backup task can last, which a task left when its validation failed
or its worker died after the upload (#4679). The storage loses what the rows designated once the
transaction is committed, never before: an object is not deleted for a row a failed task keeps.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from waterfall.core.backups import interface as backups_interface
from waterfall.core.exchanges import interface as exchanges_interface
from waterfall.core.history import interface as history_interface
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import get_logger
from waterfall.platform.storage import Bucket
from waterfall.platform.tasks import purge_ended
from waterfall.worker.identity_sync import after_commit

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.platform.settings import WorkerSettings
    from waterfall.platform.tasks import Task

logger = get_logger(__name__)
# The prefix of the archives of the backups (``waterfall.worker.backup``), and how old one must be,
# with no row to name it, to be swept: well beyond the four hours a task of backup is given.
ARCHIVES_PREFIX = "backup-"
ARCHIVE_DELAY = timedelta(days=1)
ARCHIVES_LIMIT = 100


@dataclass(frozen=True, slots=True)
class PurgeTask:
    """Purge what expired, on the bucket the settings name, with the retentions they give."""

    bucket: Bucket
    undo_retention: timedelta
    task_retention: timedelta

    @classmethod
    def of(cls, settings: WorkerSettings) -> PurgeTask:
        """Purge the bucket of the backups, with the retentions of the settings."""
        return cls(
            Bucket.of_backups(settings),
            timedelta(hours=settings.undo_retention_hours),
            timedelta(days=settings.background_task_retention_days),
        )

    def __call__(self, session: Session, _task: Task) -> Mapping[str, Any]:
        """Purge, and say how much went: the objects and deposits of the storage, the tasks."""
        now = utc_now()
        stored = self.listed(session, now)
        strays = self.strays(session, now)
        purged = exchanges_interface.purge(session, now, stored)
        history_interface.purge(session, before=now - self.undo_retention, now=now)
        spared = backups_interface.backup_task_ids(session)
        tasks = purge_ended(session, now - self.task_retention, spared)
        after_commit(session, lambda: exchanges_interface.remove_purged(self.bucket, purged))
        after_commit(session, lambda: self.remove(strays))
        result = {
            "objects": len(purged.objects),
            "deposits": len(purged.deposits),
            "tasks": tasks,
            "archives": len(strays),
        }
        logger.info("purge.done", **result)
        return result

    def listed(self, session: Session, now: datetime) -> exchanges_interface.Stored:
        """List the old objects of the prefixes the purge sweeps; a storage out of reach lists none.

        Read before anything is locked, those a row names left out of the listing (#2533). The
        rows are purged all the same: what the storage keeps, the next pass sweeps.
        """
        try:
            return exchanges_interface.stored_before(self.bucket, now, session)
        except UnavailableError:
            logger.warning("purge.storage_unlisted")
            return exchanges_interface.Stored()

    def strays(self, session: Session, now: datetime) -> list[str]:
        """List the archives of backups no row names, older than ``ARCHIVE_DELAY`` (#4679).

        A storage out of reach lists none: the next pass sweeps them.
        """
        try:
            return self.bucket.keys_before(
                ARCHIVES_PREFIX,
                now - ARCHIVE_DELAY,
                ARCHIVES_LIMIT,
                lambda keys: backups_interface.archives_named(session, keys),
            )
        except UnavailableError:
            logger.warning("purge.archives_unlisted")
            return []

    def remove(self, keys: list[str]) -> None:
        """Remove the archives swept; a removal that fails is logged, the next pass sweeps it."""
        for key in keys:
            try:
                self.bucket.remove(key)
            except UnavailableError:
                logger.warning("purge.archive_not_removed", key=key)
