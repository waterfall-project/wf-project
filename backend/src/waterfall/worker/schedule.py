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
and writes its task, ended. The filling of the reserve of partitions is due while the reserve holds
fewer sets than its size (US-2830/L4): a creation that takes one deposits it too.
A task of a kind is never deposited while one of that kind is queued or running, and two
schedules, run together, deposit it once: they wait on one advisory lock. A backup is deposited
as ``startBackup`` does, by the same function that takes the same locks in the same order and
reads the same conditions (``lock_backup_deposit``, #4369): none is deposited while a backup or a
restoration is queued or running, and a restoration asked for meanwhile waits for it, or sees it.
The locks of a kind are taken only once it is due, and what is due is read again under them.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.core.backups import interface as backups_interface
from waterfall.core.projects import interface as projects_interface
from waterfall.core.users import interface as users_interface
from waterfall.platform.database import Database, utc_now
from waterfall.platform.locks import SCHEDULE_LOCK
from waterfall.platform.logs import get_logger
from waterfall.platform.tasks import ScheduledKind, TaskKind, last_submitted, pending_task, submit
from waterfall.worker.restore_test import start_restore_test

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ScheduleSettings

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Planned:
    """A kind of task the platform schedules, and what says it is due at a given moment."""

    kind: TaskKind | ScheduledKind
    due: Callable[[Session, datetime], bool]
    # What holds back a task due, besides its own pending task: the kind takes its locks, then
    # gives the conditions it lacks, read under them. Called only once the kind is due.
    held: Callable[[Session], list[str]] = lambda _session: []
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
            held=backups_interface.lock_backup_deposit,
        ),
        Planned("partition_reserve", reserve_short(settings.partition_reserve_size)),
        *restore_test_planned(settings),
    )


def reserve_short(size: int) -> Callable[[Session, datetime], bool]:
    """Say the filling of the reserve of partitions due while it holds fewer sets than ``size``."""

    def due(session: Session, _now: datetime) -> bool:
        return projects_interface.partition_reserve_short(session, size)

    return due


def restore_test_planned(settings: ScheduleSettings) -> tuple[Planned, ...]:
    """Plan the test of a restoration when the installation gives its Job, else nothing.

    Without a scheduled backup verified, none is started: the test would have nothing to restore.
    The interval counts from the latest test started, whose task the purge spares.
    """
    path = settings.restore_test_job
    if path is None:
        return ()
    interval = every("restore_test", settings.restore_test_interval)

    def start(session: Session) -> UUID | None:
        return start_restore_test(session, path)

    return (replace(interval, held=backups_interface.restore_test_lacks, start=start),)


def deposit_due(database: Database, queue: TaskQueue, plan: tuple[Planned, ...]) -> list[str]:
    """Deposit the tasks due, none of a kind that has one queued or running; give their kinds.

    A kind pending or not due takes none of its locks; a kind due takes them, then reads again
    whether one is pending, what holds it back and whether it is still due: a deposit made
    meanwhile by another — ``startBackup`` — is seen under them. Each task is written in the
    transaction of the schedule, and put in the queue once it is committed; a deposit Redis
    refuses leaves the task queued, which the worker deposits again. A kind the schedule starts
    itself writes its task, ended, in the same transaction.
    """
    deposited: list[str] = []
    with database.transaction() as session:
        session.execute(select(func.pg_advisory_xact_lock(SCHEDULE_LOCK)))
        now = utc_now()
        for each in plan:
            pending = pending_task(session, each.kind)
            lacking: list[str] = []
            if pending is None:
                if not each.due(session, now):
                    continue
                lacking = each.held(session)
                pending = pending_task(session, each.kind)
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
