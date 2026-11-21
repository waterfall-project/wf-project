# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule: the one command the planners call, and what it deposits of itself (PBS-5.3).

``waterfall-worker schedule`` asks what is due, writes each task in the table of the background
tasks and puts it in the queue; it runs nothing. A CronJob calls it every five minutes under
Kubernetes, the service ``scheduler`` of the Compose in a loop (EP-13, "Une commande planifiée
unique"). It reaches PostgreSQL and Redis alone (TFX-10): the worker does the work, the purge of
what expired in the object storage included.

A kind is scheduled by one line of ``planned``: the kind, and what says it is due. The reading of
the purge is due at an interval of the installation; the backup (US-2910) and the reading of the
accounts (US-3040) are due when their schedules, which an administrator sets, say so, each asking
the module that holds its planning; the test of a restoration (US-2930), under Kubernetes alone, at
an interval of the installation, once a scheduled backup is there to test. That one the schedule
starts itself rather than queue: it makes the Job of the test (``waterfall.worker.restore_test``),
and writes its task, ended.
A task of a kind is never deposited while one of that kind is queued or running, and two
schedules, run together, deposit it once: they wait on one advisory lock. A backup is deposited
as ``startBackup`` does, under the same locks in the same order (``waterfall.platform.locks``) and
under the same conditions: none is deposited while a backup or a restoration is queued or running,
and a restoration asked for meanwhile waits for it, or sees it.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.backups import interface as backups_interface
from waterfall.core.users import interface as users_interface
from waterfall.platform.database import Database, utc_now
from waterfall.platform.locks import BACKUP_LOCK, RESTORE_LOCK
from waterfall.platform.logs import get_logger
from waterfall.platform.tasks import ScheduledKind, TaskKind, last_submitted, pending_task, submit
from waterfall.worker.restore_test import start_restore_test

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ScheduleSettings

# The key of the advisory lock under which a schedule looks for a pending task, then deposits.
SCHEDULE_LOCK = 3_700_010

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Planned:
    """A kind of task the platform schedules, and what says it is due at a given moment."""

    kind: TaskKind | ScheduledKind
    due: Callable[[Session, datetime], bool]
    # What holds back a task due: the conditions the kind has besides its own pending task.
    lacks: Callable[[Session], list[str]] = lambda _session: []
    # The advisory locks of the kind, taken in order before it looks for what holds it back.
    locks: tuple[tuple[int, bool], ...] = ()
    # What starts a kind the schedule runs itself, rather than queue: it writes its task, ended,
    # and gives it; ``None`` when it did not start, which leaves it due.
    start: Callable[[Session], UUID | None] | None = None


def every(kind: TaskKind | ScheduledKind, seconds: int) -> Planned:
    """Plan a kind at an interval: due when none was deposited for that long, or ever."""
    interval = timedelta(seconds=seconds)

    def due(session: Session, now: datetime) -> bool:
        last = last_submitted(session, kind)
        return last is None or now - last >= interval

    return Planned(kind, due)


def planned(settings: ScheduleSettings) -> tuple[Planned, ...]:
    """Give the kinds the platform schedules: add one here to schedule one more."""
    return (
        Planned("identity_sync", users_interface.sync_is_due),
        every("purge", settings.purge_interval),
        Planned(
            "backup",
            backups_interface.backup_is_due,
            lacks=lambda session: backups_interface.backup_start_lacks(
                backups_interface.platform_of(session)
            ),
            locks=((BACKUP_LOCK, False), (RESTORE_LOCK, True)),
        ),
        *restore_test_planned(settings),
    )


def restore_test_planned(settings: ScheduleSettings) -> tuple[Planned, ...]:
    """Plan the test of a restoration when the installation gives its Job, else nothing.

    Without a scheduled backup verified, none is started: the test would have nothing to restore.
    The interval counts from the latest test started, whose task the purge spares.
    """
    path = settings.restore_test_job
    if path is None:
        return ()
    interval = every("restore_test", settings.restore_test_interval)
    return (
        replace(
            interval,
            lacks=backups_interface.restore_test_lacks,
            start=lambda session: start_restore_test(session, path),
        ),
    )


def deposit_due(database: Database, queue: TaskQueue, plan: tuple[Planned, ...]) -> list[str]:
    """Deposit the tasks due, none of a kind that has one queued or running; give their kinds.

    Each task is written in the transaction of the schedule, and put in the queue once it is
    committed; a deposit Redis refuses leaves the task queued, which the worker deposits again. A
    kind the schedule starts itself writes its task, ended, in the same transaction.
    """
    deposited: list[str] = []
    with database.transaction() as session:
        session.execute(select(func.pg_advisory_xact_lock(SCHEDULE_LOCK)))
        now = utc_now()
        for each in plan:
            for key, shared in each.locks:
                lock = func.pg_advisory_xact_lock_shared if shared else func.pg_advisory_xact_lock
                session.execute(select(lock(key)))
            pending = pending_task(session, each.kind)
            lacking = each.lacks(session)
            if pending is not None:
                logger.info("task.already_pending", kind=each.kind, task_id=str(pending))
            elif lacking:
                logger.info("task.held_back", kind=each.kind, missing_condition=lacking[0])
            elif each.due(session, now):
                if each.start is None:
                    task_id = submit(session, queue, each.kind, None)
                    logger.info("task.enqueued", kind=each.kind, task_id=str(task_id))
                elif each.start(session) is None:
                    continue
                deposited.append(each.kind)
    return deposited
