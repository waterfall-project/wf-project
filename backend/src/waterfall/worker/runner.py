# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The loop of the worker: it takes a task from the queue, runs it in one transaction, ends it.

The handler's work and the end of the task are committed together, under an advisory lock of the
task; the attempt that starts is committed before, apart. A worker stopped during a task leaves the
database as it was, but for that attempt: a worker that claims its entry finds the lock free, and
runs the task again from the start; while the task runs, the entry is left (WF-ARC-0090). A task
whose attempts are spent fails without running. A task of a kind no handler runs is left too,
unacknowledged and without an attempt counted, so that a newer worker, which knows the kind, claims
it during a rolling update (WF-EXP-0030); it fails only once it has waited ``unknown_kind_wait``
since it was submitted (#809). A handler that stalls on a failure that may pass (``RetriedError``)
is undone and left pending, to run again, until its last attempt, which fails it. A handler that
fails is undone; one whose failure leaves a trace on its own rows — an import passed ``failed`` or
``refused`` (EP-06) — raises ``UndoneError``, and the trace is written with the end of the task.

While a restoration holds the platform in maintenance — read in the database, not in Redis
(``waterfall.platform.maintenance``) —, the worker runs no task: the entries it reads are left,
unacknowledged, and it claims them again once idle, after the maintenance (WF-ADM-0160).
It never runs a restoration, which the service of the restoration takes from a stream of its own
(#953), nor deposits one again; that service waits for the run of each task the worker started
before the maintenance to end, by its lock (``await_run``), before it keeps anything.

Each task ended is counted in the metrics of the worker, by kind and outcome, with how long it ran
(WF-OBS-0010).
"""

import socket
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic_core import to_jsonable_python
from redis.exceptions import ResponseError
from sqlalchemy import ColumnElement, Integer, cast, func, select, update

from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import FieldError, ServiceError
from waterfall.platform.logs import PLATFORM, get_logger, logging_context
from waterfall.platform.maintenance import (
    Maintenance,
    MaintenanceHeldError,
    Restoring,
    admitted,
)
from waterfall.platform.queue import SWEEP_START, Entry, TaskQueue
from waterfall.platform.tasks import (
    FINISHED,
    PENDING,
    PROJECT,
    BackgroundTask,
    RetriedError,
    Task,
    TaskHandler,
    UndoneError,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.metrics import WorkerMetrics

INTERNAL_ERROR = "INTERNAL_ERROR"
# A task fails once that many attempts have been started and none ended it.
MAX_ATTEMPTS = 3
# The first key of the advisory locks of the runs, the second being drawn from the task.
RUN_LOCK = 3_700_090
# What ``Worker.start`` gives for a task that waits for a worker that knows its kind.
WAITS: Literal["waits"] = "waits"
# What ``Worker.execute`` gives for a task left to run again, its failure one that may pass.
RETRIED: Literal["retried"] = "retried"

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


def _code_of(error: Exception) -> str | None:
    """Give the code of a refusal, ``None`` for any other error."""
    return error.code if isinstance(error, ServiceError) else None


def _run_key(task_id: UUID) -> tuple[ColumnElement[int], ColumnElement[int]]:
    key = int.from_bytes(task_id.bytes[-4:], "big", signed=True)
    return cast(RUN_LOCK, Integer), cast(key, Integer)


def lock_run(session: Session, task_id: UUID) -> bool:
    """Take the lock of the run of a task until the transaction ends; ``False`` if it is held."""
    return session.scalar(select(func.pg_try_advisory_xact_lock(*_run_key(task_id)))) is True


def await_run(session: Session, task_id: UUID) -> None:
    """Wait until no worker runs a task, by the lock of its run, held until the transaction ends."""
    session.execute(select(func.pg_advisory_xact_lock(*_run_key(task_id))))


def end(
    session: Session,
    task_id: UUID,
    *,
    result: Mapping[str, Any] | None = None,
    problem: Mapping[str, Any] | None = None,
) -> None:
    """End a task: failed if a ``problem`` is given, succeeded with its ``result`` otherwise.

    A task that succeeds carries no problem: a restoration given up, failed, then restored again by
    the operator, had one (#1016).
    """
    changes: dict[str, Any] = (
        {
            "status": "succeeded",
            "progress": 100,
            "result": to_jsonable_python(result),
            "problem": None,
        }
        if problem is None
        else {"status": "failed", "problem": dict(problem)}
    )
    session.execute(
        update(BackgroundTask)
        .where(BackgroundTask.id == task_id)
        .values(**changes, finished_at=utc_now())
    )


def context_of(task: Task) -> dict[str, str]:
    """Give what the logs of a task carry: its correlation, its requester, the task, its project.

    The project is the one the payload names, if it does; a task that learns it later binds it
    (``bind_logging``).
    """
    actor = PLATFORM if task.requested_by is None else str(task.requested_by)
    context = {
        "correlation_id": task.correlation_id,
        "actor": actor,
        "task_id": str(task.task_id),
        "kind": task.kind,
    }
    project = task.payload.get(PROJECT)
    if project is not None:
        context["project_id"] = str(project)
    return context


@dataclass(frozen=True, slots=True)
class Timing:
    """The delays of a worker, in seconds: to claim an idle entry, to read, to deposit again.

    ``unknown_kind_wait`` is how long a task of a kind the worker does not run may wait for a
    worker that does, since it was submitted: an hour by default.
    """

    claim_after: float = 30.0
    block: float = 5.0
    redeposit_every: float = 60.0
    unknown_kind_wait: float = 3600.0


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
        # Where the tasks it ends are counted, if anywhere (``count_in``).
        self.metrics: WorkerMetrics | None = None
        self.maintenance = Maintenance.of(database, queue)
        # Where the next look for the entries left pending starts: each look goes on from the last.
        self.sweep = SWEEP_START

    def count_in(self, metrics: WorkerMetrics) -> Self:
        """Count the tasks this worker ends in the metrics of its process (WF-OBS-0010)."""
        self.metrics = metrics
        return self

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

    def restoring(self) -> Restoring | None:
        """Give the restoration that holds the platform in maintenance, if one does."""
        return self.maintenance.current()

    def handle(self, entry: Entry) -> None:
        """Run the task of an entry, and acknowledge it unless the task runs elsewhere.

        In maintenance, or for a task of a kind it does not run yet, the entry is left,
        unacknowledged.
        """
        if self.restoring() is not None:
            return
        if entry.task_id is None:
            logger.warning("queue.entry_unreadable", entry_id=entry.entry_id)
        elif not self.run_task(entry.task_id):
            return
        self.queue.acknowledge(entry.entry_id)

    def run_task(self, task_id: UUID) -> bool:
        """Run a task, under its lock; ``False`` if another worker holds the lock or it runs again.

        Or if the kind of the task has no handler here, and may still wait for a worker that has.

        Or if a maintenance began meanwhile, read in the database, which a Redis out of reach or
        emptied does not change (#956): the service of the restoration, once it holds it, waits for
        the lock of each pending task, then drains the writes, before it keeps anything; a worker
        that takes the lock of the run after it does leaves the task. The run is admitted by the
        lock of the drain, held shared until it ends (``admitted``, #2229).
        """
        with self.database.transaction() as session:
            if not lock_run(session, task_id) or not admitted(session.connection()):
                return False
            try:
                task = self.start(task_id)
            except MaintenanceHeldError:
                return False
            if task == WAITS:
                return False
            if task is None:
                return True
            started = time.perf_counter()
            with logging_context(**context_of(task)):
                logger.info("task.started", attempt=task.attempt)
                outcome = self.execute(session, task)
                if outcome == RETRIED:
                    return False
        # Counted once its end is committed: a task whose end is lost runs again (WF-OBS-0010).
        self.ended(task.kind, succeeded=outcome, seconds=time.perf_counter() - started)
        return True

    def ended(self, kind: str, *, succeeded: bool, seconds: float | None) -> None:
        """Count a task ended in the metrics of the worker, if it has any."""
        if self.metrics is not None:
            self.metrics.task_ended(kind, succeeded=succeeded, seconds=seconds)

    def start(self, task_id: UUID) -> Task | Literal["waits"] | None:
        """Start one more attempt of a task, committed, or end it if it may not run.

        A task of a kind with no handler here starts nothing and counts no attempt while it may
        wait for a worker that has one: ``WAITS``.
        """
        with self.database.transaction() as session:
            row = session.get(BackgroundTask, task_id, with_for_update=True)
            if row is None or row.status in FINISHED:
                return None
            attempt = row.attempts + 1
            task = Task(
                row.id, row.kind, row.payload, row.requested_by, row.correlation_id, attempt
            )
            unhandled = row.kind not in self.handlers
            if unhandled and row.attempts < MAX_ATTEMPTS and self.may_wait(row.submitted_at):
                with logging_context(**context_of(task)):
                    logger.info("task.left", reason="kind_unhandled")
                return WAITS
            if row.attempts >= MAX_ATTEMPTS or unhandled:
                reason = "attempts_spent" if row.attempts >= MAX_ATTEMPTS else "kind_unhandled"
                with logging_context(**context_of(task)):
                    logger.error("task.failed", reason=reason, attempts=row.attempts)
                end(session, task_id, problem=failure(INTERNAL_ERROR, 500, row.correlation_id))
            else:
                row.status, row.attempts, row.started_at = "running", attempt, utc_now()
                return task
        # Failed without running, counted once its end is committed.
        self.ended(task.kind, succeeded=False, seconds=None)
        return None

    def may_wait(self, submitted_at: datetime) -> bool:
        """Tell whether a task submitted at that moment is still within the wait of its kind."""
        return utc_now() - submitted_at < timedelta(seconds=self.timing.unknown_kind_wait)

    def execute(self, session: Session, task: Task) -> bool | Literal["retried"]:
        """Run the handler of a task and end the task; tell whether it succeeded.

        ``RETRIED`` if the task stalled on a failure that may pass, and is left to run again: its
        entry stays pending, as after a worker stopped; on its last attempt, it fails.

        A failed handler's work is undone. A refusal ends the task with its code, anything else
        with an ``INTERNAL_ERROR``. A handler that leaves a trace of its failure (``UndoneError``)
        has it written once its work is undone.
        """
        try:
            with session.begin_nested():
                result = self.handlers[task.kind](session, task)
        except RetriedError as stalled:
            if task.attempt < MAX_ATTEMPTS:
                # The trace is the stall's, chained to the failure it came from: a defect of the
                # reading is not left without one.
                logger.warning(
                    "task.retried",
                    attempt=task.attempt,
                    code=_code_of(stalled.cause),
                    exc_info=stalled,
                )
                return RETRIED
            stalled.trace(session)
            self.fail(session, task, stalled.cause)
        except UndoneError as undone:
            undone.trace(session)
            self.fail(session, task, undone.cause)
        except ServiceError as refusal:
            self.fail(session, task, refusal)
        except Exception:
            logger.exception("task.failed", reason="error")
            end(session, task.task_id, problem=failure(INTERNAL_ERROR, 500, task.correlation_id))
        else:
            end(session, task.task_id, result=result)
            logger.info("task.succeeded")
            return True
        return False

    def fail(self, session: Session, task: Task, error: Exception) -> None:
        """End a task that failed: a refusal with its code, anything else as an internal error."""
        if isinstance(error, ServiceError):
            logger.info("task.failed", reason="refused", code=error.code)
            refused = failure(
                error.code, error.status, task.correlation_id, error.params, error.fields
            )
            end(session, task.task_id, problem=refused)
            return
        logger.error("task.failed", reason="error", exc_info=error)
        end(session, task.task_id, problem=failure(INTERNAL_ERROR, 500, task.correlation_id))

    def kinds(self) -> ColumnElement[bool]:
        """Say which tasks this consumer deposits again: all but the restorations (#953)."""
        return BackgroundTask.kind != "restore"

    def redeposit(self) -> None:
        """Deposit again the pending tasks the stream no longer names, but those that run.

        Not in maintenance: the database is being replaced.
        """
        if self.restoring() is not None:
            return
        with self.database.transaction() as session:
            pending = session.execute(
                select(BackgroundTask.id, BackgroundTask.status).where(
                    BackgroundTask.status.in_(PENDING), self.kinds()
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
