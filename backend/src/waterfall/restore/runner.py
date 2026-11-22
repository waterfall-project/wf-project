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
succeeded and committed. One whose attempts are spent, one that has held the maintenance beyond
its deadline (``DEADLINE``), and a maintenance held without its state are given up, at the next
attempt, at the start of the service or periodically after: the task fails (#1016). Given up before
the replacement began, the maintenance is lifted, the databases as they were; once it may have
begun (``caches_cleared``), the maintenance is kept, the restoration marked ``abandoned``, and left
to an operator, who restores again or lifts it once the databases are checked (decision of the
author of 2026-11-22, #1016): lifted, the platform would serve databases half replaced
(WF-ARC-0090). A restoration refused before the maintenance — an archive of a newer version, one
that does not read back — fails, and nothing has changed.
"""

import dataclasses
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, inspect, select

from waterfall.platform.database import utc_now
from waterfall.platform.errors import ServiceError
from waterfall.platform.logs import get_logger, logging_context
from waterfall.platform.restoration import forget_keeping, kept_for
from waterfall.platform.tasks import PENDING, BackgroundTask, Task, TaskHandler
from waterfall.worker.runner import (
    INTERNAL_ERROR,
    MAX_ATTEMPTS,
    WAITS,
    Timing,
    Worker,
    context_of,
    end,
    failure,
    lock_run,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database
    from waterfall.platform.maintenance import Restoring
    from waterfall.platform.queue import Entry, TaskQueue

KIND = "restore"
# What the operator does once a restoration that may have changed the databases is given up.
RECOURSE = (
    "the maintenance is kept: restore again, or lift it once the databases are checked "
    "(deploy/compose/README.md, Restaurer)"
)

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

        ``queue`` is the stream of the tasks of the worker: the restorations have theirs beside it.
        ``database`` is reached as its owner, who alone writes the maintenance.
        """
        super().__init__(database, queue.restores(), {KIND: handler}, consumer, timing)
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
            if task == WAITS:
                return False
            if task is None:
                return True
            with logging_context(**context_of(task)):
                logger.info("task.started", attempt=task.attempt)
                self.execute(session, task)
        if self.succeeded:
            self.lift(task_id, task.correlation_id)
        return True

    def lift(self, task_id: UUID, correlation_id: str) -> None:
        """Lift the maintenance of a restoration, and say it under its correlation (WF-OBS-0020)."""
        self.maintenance.lift()
        with logging_context(correlation_id=correlation_id, task_id=str(task_id)):
            logger.info("restore.maintenance_lifted")

    def start(self, task_id: UUID) -> Task | Literal["waits"] | None:
        """Start one more attempt of a restoration: counted in the maintenance once it holds one.

        A restoration whose task has succeeded already, the maintenance not lifted after — the
        database out of reach, the process stopped —, lifts it and runs nothing again.
        """
        restoring = self.restoring()
        if restoring is not None and restoring.task_id == task_id:
            if self.succeeded_already(task_id):
                self.lift(task_id, restoring.correlation_id)
                return None
            return self.resume(restoring)
        return super().start(task_id)

    def succeeded_already(self, task_id: UUID) -> bool:
        """Tell whether the task of a restoration has succeeded, as the database says it.

        A database being replaced, its tables not made again, holds no task.
        """
        with self.database.transaction() as session:
            if not inspect(session.connection()).has_table(BackgroundTask.__tablename__):
                return False
            status = session.scalar(
                select(BackgroundTask.status).where(BackgroundTask.id == task_id)
            )
        return status == "succeeded"

    def resume(self, restoring: Restoring) -> Task | None:
        """Take up the restoration a maintenance holds; ``None`` once it is given up.

        Given up once its attempts are spent, once it has held the maintenance beyond its deadline,
        or held without its state (``give_up``); one abandoned already is left to the operator.
        """
        if restoring.abandoned:
            return None
        reason = self.reason_to_give_up(restoring)
        if reason is None and restoring.attempts >= MAX_ATTEMPTS:
            reason = "attempts_spent"
        if reason is not None:
            self.give_up(restoring, reason)
            return None
        attempt = restoring.attempts + 1
        self.maintenance.hold(dataclasses.replace(restoring, attempts=attempt))
        return task_of(restoring, attempt)

    @staticmethod
    def reason_to_give_up(restoring: Restoring) -> str | None:
        """Say why a restoration no attempt runs is given up, if it is: no state, or overdue."""
        if restoring.stateless:
            return "no_state"
        if restoring.overdue(utc_now()):
            return "deadline_passed"
        return None

    def give_up(self, restoring: Restoring, reason: str) -> None:
        """Fail the task of a restoration that holds the maintenance; lift it, or keep it (#1016).

        Its task fails, if the database holds it pending. If the databases have not changed, what
        the restoration kept is dropped and the maintenance lifted: the platform serves them as
        they were, and a restoration asked later keeps them again, rather than take over what this
        one kept. If they may have changed, what it kept stays, which a restoration taken up again
        takes over, and the maintenance is kept, the restoration marked ``abandoned``: the log says
        what the operator does, and nothing takes it up before they do.
        """
        changed = restoring.caches_cleared
        with logging_context(**context_of(task_of(restoring, restoring.attempts))):
            logger.error(
                "task.failed",
                reason=reason,
                attempts=restoring.attempts,
                databases_changed=changed,
                **({"action": RECOURSE} if changed else {}),
            )
        with self.database.transaction() as session:
            fail_pending(session, restoring.task_id, restoring.correlation_id)
            if not changed and kept_for(session.connection()) == restoring.task_id:
                forget_keeping(session.connection())
        if changed:
            self.maintenance.hold(dataclasses.replace(restoring, abandoned=True, stateless=False))
        else:
            self.lift(restoring.task_id, restoring.correlation_id)

    def execute(self, session: Session, task: Task) -> bool:
        """Run the restoration, end its task, tell whether it succeeded; once held, an error stops.

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
            return False
        end(session, task.task_id, result=result)
        self.succeeded = True
        logger.info("task.succeeded")
        return True

    def redeposit(self) -> None:
        """Deposit again the restorations the stream no longer names; give up one that is done for.

        At the start of the service, then periodically, between two attempts (#1016): a maintenance
        held without its state, or beyond its deadline, is given up (``give_up``); one held by a
        restoration abandoned is left to the operator; one held by a restoration that goes on is
        deposited again, its row the database may no longer hold. Out of maintenance, those the
        database holds pending, as the worker does for its own.
        """
        restoring = self.restoring()
        if restoring is None:
            super().redeposit()
            return
        if restoring.abandoned:
            return
        reason = self.reason_to_give_up(restoring)
        if reason is not None:
            self.give_up(restoring, reason)
        elif restoring.task_id not in self.queue.waiting():
            self.queue.deposit(restoring.task_id)
            logger.warning("queue.redeposited", count=1)


def task_of(restoring: Restoring, attempt: int) -> Task:
    """Give the task of the restoration a maintenance holds, at an attempt."""
    return Task(
        restoring.task_id,
        KIND,
        restoring.payload,
        restoring.requested_by,
        restoring.correlation_id,
        attempt,
    )


def fail_pending(session: Session, task_id: UUID, correlation_id: str) -> None:
    """Fail a task the database holds pending, as an internal error; leave any other as it is.

    A database replaced, its tables not made again, holds no task.
    """
    if not inspect(session.connection()).has_table(BackgroundTask.__tablename__):
        return
    status = session.scalar(select(BackgroundTask.status).where(BackgroundTask.id == task_id))
    if status in PENDING:
        end(session, task_id, problem=failure(INTERNAL_ERROR, 500, correlation_id))
