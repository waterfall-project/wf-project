# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The loop of the worker: it takes a task from the queue, runs it in one transaction, ends it.

The handler's work and the end of the task are committed together, under an advisory lock of the
task; the attempt that starts is committed before, apart. A worker stopped during a task leaves the
database as it was, but for that attempt: a worker that claims its entry finds the lock free, and
runs the task again from the start; while the task runs, the entry is left (WF-ARC-0090). A task
whose attempts are spent, or that no handler runs, fails without running.
"""

import socket
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic_core import to_jsonable_python
from redis.exceptions import ResponseError
from sqlalchemy import Integer, cast, func, select, update
from sqlalchemy.orm import Session

from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import FieldError, ServiceError
from waterfall.platform.logs import PLATFORM, get_logger, logging_context
from waterfall.platform.queue import SWEEP_START, Entry, TaskQueue
from waterfall.platform.tasks import FINISHED, PENDING, BackgroundTask, Task, TaskHandler

INTERNAL_ERROR = "INTERNAL_ERROR"
# A task fails once that many attempts have been started and none ended it.
MAX_ATTEMPTS = 3
# The first key of the advisory locks of the runs, the second being drawn from the task.
RUN_LOCK = 3_700_090

logger = get_logger(__name__)


def failure(
    code: str,
    status: int,
    correlation_id: str,
    params: Mapping[str, Any] | None = None,
    fields: tuple[FieldError, ...] = (),
) -> dict[str, Any]:
    """Say why a task failed, as the contract does (``Problem``), under the task's correlation.

    A refusal by field keeps its fields, as the envelope of an answer does.
    """
    described: dict[str, Any] = {"code": code, "status": status}
    if params:
        described["params"] = to_jsonable_python(params)
    if fields:
        described["fields"] = [field_problem(field) for field in fields]
    return {**described, "correlation_id": correlation_id}


def field_problem(field: FieldError) -> dict[str, Any]:
    """Describe the refusal of one field as the contract does (``FieldProblem``)."""
    described: dict[str, Any] = {"pointer": field.pointer, "code": field.code}
    if field.params:
        described["params"] = to_jsonable_python(field.params)
    return described


def lock_run(session: Session, task_id: UUID) -> bool:
    """Take the lock of the run of a task until the transaction ends; ``False`` if it is held."""
    key = int.from_bytes(task_id.bytes[-4:], "big", signed=True)
    locked = func.pg_try_advisory_xact_lock(cast(RUN_LOCK, Integer), cast(key, Integer))
    return session.scalar(select(locked)) is True


def end(
    session: Session,
    task_id: UUID,
    *,
    result: Mapping[str, Any] | None = None,
    problem: Mapping[str, Any] | None = None,
) -> None:
    """End a task: failed if a ``problem`` is given, succeeded with its ``result`` otherwise."""
    changes: dict[str, Any] = (
        {"status": "succeeded", "progress": 100, "result": to_jsonable_python(result)}
        if problem is None
        else {"status": "failed", "problem": dict(problem)}
    )
    session.execute(
        update(BackgroundTask)
        .where(BackgroundTask.id == task_id)
        .values(**changes, finished_at=utc_now())
    )


def context_of(task: Task) -> dict[str, str]:
    """Give what the logs of a task carry: its correlation, its requester, the task."""
    actor = PLATFORM if task.requested_by is None else str(task.requested_by)
    return {
        "correlation_id": task.correlation_id,
        "actor": actor,
        "task_id": str(task.task_id),
        "kind": task.kind,
    }


@dataclass(frozen=True, slots=True)
class Timing:
    """The delays of a worker, in seconds: to claim an idle entry, to read, to deposit again."""

    claim_after: float = 30.0
    block: float = 5.0
    redeposit_every: float = 60.0


class Worker:
    """A consumer of the queue, named after its host, which runs the kinds it has a handler for."""

    def __init__(
        self,
        database: Database,
        queue: TaskQueue,
        handlers: Mapping[str, TaskHandler],
        consumer: str | None = None,
        timing: Timing | None = None,
    ) -> None:
        self.database = database
        self.queue = queue
        self.handlers = handlers
        self.consumer = consumer or socket.gethostname()
        self.timing = timing or Timing()
        # Where the next look for the entries left pending starts: each look goes on from the last.
        self.sweep = SWEEP_START

    def run(self) -> None:
        """Take and run the tasks, until the process is stopped."""
        logger.info("worker.started", consumer=self.consumer)
        self.queue.prepare()
        self.redeposit()
        redeposited = time.monotonic()
        while True:
            self.step()
            if time.monotonic() - redeposited >= self.timing.redeposit_every:
                self.redeposit()
                redeposited = time.monotonic()

    def step(self) -> bool:
        """Handle one entry, left by a stopped worker first; ``False`` if none came.

        A stream that Redis lost is made again, and the pending tasks deposited again.
        """
        try:
            self.sweep, entries = self.queue.reclaim(
                self.consumer, round(self.timing.claim_after * 1000), self.sweep
            )
            entries = entries or self.queue.read(self.consumer, round(self.timing.block * 1000))
        except ResponseError as error:
            if not str(error).startswith("NOGROUP"):
                raise
            logger.warning("queue.lost")
            self.sweep = SWEEP_START
            self.queue.prepare()
            self.redeposit()
            return False
        for entry in entries:
            self.handle(entry)
        return bool(entries)

    def handle(self, entry: Entry) -> None:
        """Run the task of an entry, and acknowledge it unless the task runs elsewhere."""
        if entry.task_id is None:
            logger.warning("queue.entry_unreadable", entry_id=entry.entry_id)
        elif not self.run_task(entry.task_id):
            return
        self.queue.acknowledge(entry.entry_id)

    def run_task(self, task_id: UUID) -> bool:
        """Run a task, under its lock; ``False`` if another worker holds the lock."""
        with self.database.transaction() as session:
            if not lock_run(session, task_id):
                return False
            task = self.start(task_id)
            if task is None:
                return True
            with logging_context(**context_of(task)):
                logger.info("task.started", attempt=task.attempt)
                self.execute(session, task)
        return True

    def start(self, task_id: UUID) -> Task | None:
        """Start one more attempt of a task, committed, or end it if it may not run."""
        with self.database.transaction() as session:
            row = session.get(BackgroundTask, task_id, with_for_update=True)
            if row is None or row.status in FINISHED:
                return None
            attempt = row.attempts + 1
            task = Task(
                row.id, row.kind, row.payload, row.requested_by, row.correlation_id, attempt
            )
            if row.attempts >= MAX_ATTEMPTS or row.kind not in self.handlers:
                reason = "attempts_spent" if row.attempts >= MAX_ATTEMPTS else "kind_unhandled"
                with logging_context(**context_of(task)):
                    logger.error("task.failed", reason=reason, attempts=row.attempts)
                end(session, task_id, problem=failure(INTERNAL_ERROR, 500, row.correlation_id))
                return None
            row.status, row.attempts, row.started_at = "running", attempt, utc_now()
            return task

    def execute(self, session: Session, task: Task) -> None:
        """Run the handler of a task and end the task; a failed handler's work is undone.

        A refusal ends the task with its code, anything else with an ``INTERNAL_ERROR``.
        """
        try:
            with session.begin_nested():
                result = self.handlers[task.kind](session, task)
        except ServiceError as refusal:
            logger.info("task.failed", reason="refused", code=refusal.code)
            refused = failure(
                refusal.code, refusal.status, task.correlation_id, refusal.params, refusal.fields
            )
            end(session, task.task_id, problem=refused)
        except Exception:
            logger.exception("task.failed", reason="error")
            end(session, task.task_id, problem=failure(INTERNAL_ERROR, 500, task.correlation_id))
        else:
            end(session, task.task_id, result=result)
            logger.info("task.succeeded")

    def redeposit(self) -> None:
        """Deposit again the pending tasks the stream no longer names, but those that run."""
        with self.database.transaction() as session:
            pending = session.execute(
                select(BackgroundTask.id, BackgroundTask.status).where(
                    BackgroundTask.status.in_(PENDING)
                )
            ).all()
            named = self.queue.waiting()
            lost = [
                task_id
                for task_id, status in sorted(pending)
                if task_id not in named and (status == "queued" or lock_run(session, task_id))
            ]
        for task_id in lost:
            self.queue.deposit(task_id)
        if lost:
            logger.warning("queue.redeposited", count=len(lost))
