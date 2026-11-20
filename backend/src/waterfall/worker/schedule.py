# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule: the one command the planners call, and what it deposits of itself (PBS-5.3).

``waterfall-worker schedule`` asks what is due, writes each task in the table of the background
tasks and puts it in the queue; it runs nothing. A CronJob calls it every five minutes under
Kubernetes, the service ``scheduler`` of the Compose in a loop (EP-13, "Une commande planifiée
unique"). It reaches PostgreSQL and Redis alone (TFX-10): the worker does the work, the purge of
what expired in the object storage included.

A kind is scheduled by one line of ``planned``: the kind, and what says it is due. The reading of
the accounts and the purge are due at an interval of the installation; the backup (US-2910) and
the test of a restoration (US-2930) join them, each asking the module that holds its planning.
A task of a kind is never deposited while one of that kind is queued or running, and two
schedules, run together, deposit it once: they wait on one advisory lock.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.platform.database import Database, utc_now
from waterfall.platform.logs import get_logger
from waterfall.platform.tasks import ScheduledKind, TaskKind, last_submitted, pending_task, submit

if TYPE_CHECKING:
    from collections.abc import Callable

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
        every("identity_sync", settings.identity_sync_interval),
        every("purge", settings.purge_interval),
    )


def deposit_due(database: Database, queue: TaskQueue, plan: tuple[Planned, ...]) -> list[str]:
    """Deposit the tasks due, none of a kind that has one queued or running; give their kinds.

    Each task is written in the transaction of the schedule, and put in the queue once it is
    committed; a deposit Redis refuses leaves the task queued, which the worker deposits again.
    """
    deposited: list[str] = []
    with database.transaction() as session:
        session.execute(select(func.pg_advisory_xact_lock(SCHEDULE_LOCK)))
        now = utc_now()
        for each in plan:
            pending = pending_task(session, each.kind)
            if pending is not None:
                logger.info("task.already_pending", kind=each.kind, task_id=str(pending))
            elif each.due(session, now):
                task_id = submit(session, queue, each.kind, None)
                logger.info("task.enqueued", kind=each.kind, task_id=str(task_id))
                deposited.append(each.kind)
    return deposited
