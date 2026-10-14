# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The loop of the service of the restoration: the stream of the restorations, read alone (#953).

It reads the stream of the restorations in its group of consumers, as the worker reads its own, and
takes over an entry it left unacknowledged (``XAUTOCLAIM``); at its start, and periodically, it
deposits again a restoration left queued that the stream no longer names. The task is run in the
transaction of its run, under its lock, as the worker runs one; the attempt that starts is
committed before, apart.

A restoration holds the platform in maintenance before it touches a database. From then on, its
attempts are counted in the maintenance, which keeps the task: the database it replaces may no
longer hold its row (WF-ARC-0090). An attempt interrupted — the process stopped, a database or
Keycloak out of reach — leaves the maintenance and the entry: the restoration starts again from the
beginning when the entry is taken over, and the maintenance is lifted once it has ended, its task
succeeded and committed. One whose attempts are spent leaves the platform in maintenance: the
databases it was replacing are in no state to serve, which an operator must look at. A restoration
refused before the maintenance — an archive of a newer version, one that does not read back — fails,
and nothing has changed.
"""

import dataclasses
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session

from waterfall.platform.database import Database
from waterfall.platform.errors import ServiceError
from waterfall.platform.logs import get_logger, logging_context
from waterfall.platform.maintenance import Maintenance, Restoring
from waterfall.platform.queue import Entry, TaskQueue
from waterfall.platform.tasks import BackgroundTask, Task, TaskHandler
from waterfall.worker.runner import (
    INTERNAL_ERROR,
    MAX_ATTEMPTS,
    Timing,
    Worker,
    context_of,
    end,
    failure,
    lock_run,
)

KIND = "restore"

logger = get_logger(__name__)


class Restorer(Worker):
    """The consumer of the stream of the restorations, which runs them and nothing else."""

    def __init__(
        self,
        database: Database,
        queue: TaskQueue,
        handler: TaskHandler,
        consumer: str | None = None,
        timing: Timing | None = None,
    ) -> None:
        """Run the restorations ``queue`` holds, beside it, by ``handler``, on ``database``.

        ``queue`` is the stream of the tasks of the worker: the restorations have theirs beside it,
        and the maintenance its key.
        """
        super().__init__(database, queue.restores(), {KIND: handler}, consumer, timing)
        self.maintenance = Maintenance.of(queue)
        self.succeeded = False

    def kinds(self) -> ColumnElement[bool]:
        """Say which tasks this consumer deposits again: the restorations alone."""
        return BackgroundTask.kind == KIND

    def handle(self, entry: Entry) -> None:
        """Run the restoration of an entry, and acknowledge it, unless it was interrupted.

        In maintenance too: the maintenance is the restoration's own.
        """
        if entry.task_id is None:
            logger.warning("queue.entry_unreadable", entry_id=entry.entry_id)
        else:
            try:
                ran = self.run_task(entry.task_id)
            except Exception:
                logger.exception("restore.interrupted", task_id=str(entry.task_id))
                return
            if not ran:
                return
        self.queue.acknowledge(entry.entry_id)

    def run_task(self, task_id: UUID) -> bool:
        """Run a restoration under its lock, then lift the maintenance if it has succeeded.

        Lifted once the task has succeeded and the restoration is inscribed, committed: what is
        done in the platform after the maintenance comes after the restoration in the journal.
        """
        self.succeeded = False
        with self.database.transaction() as session:
            if not lock_run(session, task_id):
                return False
            task = self.start(task_id)
            if task is None:
                return True
            with logging_context(**context_of(task)):
                logger.info("task.started", attempt=task.attempt)
                self.execute(session, task)
        if self.succeeded:
            self.maintenance.lift()
            logger.info("restore.maintenance_lifted", task_id=str(task_id))
        return True

    def start(self, task_id: UUID) -> Task | None:
        """Start one more attempt of a restoration: counted in the maintenance once it holds one."""
        restoring = self.restoring()
        if restoring is not None and restoring.task_id == task_id:
            return self.resume(restoring)
        return super().start(task_id)

    def resume(self, restoring: Restoring) -> Task | None:
        """Take up the restoration a maintenance holds; ``None`` once its attempts are spent."""
        attempt = restoring.attempts + 1
        task = Task(
            restoring.task_id,
            KIND,
            restoring.payload,
            restoring.requested_by,
            restoring.correlation_id,
            attempt,
        )
        if restoring.attempts >= MAX_ATTEMPTS:
            with logging_context(**context_of(task)):
                logger.error("task.failed", reason="attempts_spent", attempts=restoring.attempts)
            return None
        self.maintenance.hold(dataclasses.replace(restoring, attempts=attempt))
        return task

    def execute(self, session: Session, task: Task) -> None:
        """Run the restoration and end its task; once the maintenance is held, an error interrupts.

        Before the maintenance, a refusal ends the task with its code, anything else with an
        ``INTERNAL_ERROR``, and nothing has changed. Once it is held, an error leaves the task as it
        is and the maintenance held, for the restoration to start again from the beginning.
        """
        try:
            result = self.handlers[KIND](session, task)
        except Exception as error:
            held = self.restoring()
            if held is not None and held.task_id == task.task_id:
                raise
            if isinstance(error, ServiceError):
                logger.info("task.failed", reason="refused", code=error.code)
                refused = failure(error.code, error.status, task.correlation_id, error.params)
                end(session, task.task_id, problem=refused)
            else:
                logger.exception("task.failed", reason="error")
                problem = failure(INTERNAL_ERROR, 500, task.correlation_id)
                end(session, task.task_id, problem=problem)
            return
        end(session, task.task_id, result=result)
        self.succeeded = True
        logger.info("task.succeeded")

    def redeposit(self) -> None:
        """Deposit again the restorations the stream no longer names.

        In maintenance, the restoration that holds it, whose row the database may no longer hold;
        otherwise, those the database holds pending, as the worker does for its own.
        """
        restoring = self.restoring()
        if restoring is None:
            super().redeposit()
        elif restoring.task_id not in self.queue.waiting():
            self.queue.deposit(restoring.task_id)
            logger.warning("queue.redeposited", count=1)
