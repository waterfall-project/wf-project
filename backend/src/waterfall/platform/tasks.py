# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The background tasks: their table, their submission, their reading (WF-ARC-0090).

``background_task`` is the authority on a task, which a request writes in its transaction, and
deposits in the queue once that is committed; a task whose deposit was lost stays queued, and the
worker deposits it again. A task carries the correlation of what submitted it (WF-OBS-0020); its
requester is an account (the module of the accounts declares the key), or the platform (PBS-5.3).
"""

from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, get_args
from uuid import UUID

from pydantic_core import to_jsonable_python
from redis.exceptions import RedisError
from sqlalchemy import (
    CheckConstraint,
    Connection,
    SmallInteger,
    Text,
    event,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, mapped_column
from structlog.contextvars import get_contextvars

from waterfall.platform.database import Base, UtcDateTime, utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import get_logger
from waterfall.platform.queue import TaskQueue
from waterfall.platform.restoration import keep, keep_more, overwrite, write_back

# The kinds and the states of the contract (``BackgroundTaskRef.kind``, ``BackgroundTaskStatus``),
# in its order; a new one is a change of the contract, then a migration of the constraint.
type TaskKind = Literal[
    "import_analysis",
    "import_apply",
    "revision_mark",
    "structure_merge",
    "risk_occurrence",
    "export",
    "backup",
    "restore",
    "identity_sync",
]
KINDS: tuple[str, ...] = get_args(TaskKind.__value__)
STATUSES = ("queued", "running", "succeeded", "failed")
PENDING = ("queued", "running")
FINISHED = ("succeeded", "failed")
# Why a task that a restoration finds pending in the restored database fails (#892).
INTERRUPTED = {"code": "TASK_INTERRUPTED_BY_RESTORE", "status": 409}

logger = get_logger(__name__)


def _one_of(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class BackgroundTask(Base):
    """A task asked of the worker: what, for whom, where it stands, and how it ended."""

    __tablename__ = "background_task"
    __table_args__ = (
        CheckConstraint(_one_of("kind", KINDS), name="kind_known"),
        CheckConstraint(_one_of("status", STATUSES), name="status_known"),
        CheckConstraint("progress BETWEEN 0 AND 100", name="progress_bound"),
        CheckConstraint("attempts >= 0", name="attempts_not_negative"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
        CheckConstraint("(problem IS NOT NULL) = (status = 'failed')", name="problem_of_a_failure"),
        CheckConstraint(
            f"(finished_at IS NOT NULL) = ({_one_of('status', FINISHED)})", name="finished_at_end"
        ),
        CheckConstraint("correlation_id ~ '^[A-Za-z0-9._-]{1,64}$'", name="correlation_id_form"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    # The worker looks for the pending tasks, and so does the schedule.
    status: Mapped[str] = mapped_column(Text, index=True)
    progress: Mapped[int] = mapped_column(SmallInteger)
    # An absent result or problem is SQL's null, not JSON's.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    problem: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    # Null for the platform; a caller lists its own.
    requested_by: Mapped[UUID | None] = mapped_column(index=True)
    correlation_id: Mapped[str] = mapped_column(Text)
    # The attempts started: one more each time a worker takes the task up.
    attempts: Mapped[int] = mapped_column(SmallInteger)
    submitted_at: Mapped[datetime] = mapped_column(UtcDateTime)
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


@dataclass(frozen=True, slots=True)
class Task:
    """A task as its handler receives it: what to do, for whom, and which attempt this is."""

    task_id: UUID
    kind: str
    payload: Mapping[str, Any]
    requested_by: UUID | None
    correlation_id: str
    attempt: int


# What runs a task of one kind, in the transaction of the worker, and what it produced, if anything
# to keep. A refusal is a ``ServiceError``, whose code and parameters the task fails with.
type TaskHandler = Callable[[Session, Task], Mapping[str, Any] | None]


class TaskError(Exception):
    """A task submitted outside a request or a command, without a correlation: a defect."""


def submit(
    session: Session,
    queue: TaskQueue,
    kind: TaskKind,
    requested_by: UUID | None,
    payload: Mapping[str, Any] | None = None,
) -> UUID:
    """Write a task, queued, in the transaction of ``session``, and deposit it once committed.

    The deposit never fails the transaction, which is already committed: if Redis refuses it, the
    task stays queued, and the worker deposits it again.
    """
    correlation_id = get_contextvars().get("correlation_id")
    if not isinstance(correlation_id, str):
        message = "a task is submitted inside a request or a command, under its correlation"
        raise TaskError(message)
    task_id = new_id()
    session.execute(
        insert(BackgroundTask).values(
            id=task_id,
            kind=kind,
            status="queued",
            progress=0,
            payload=to_jsonable_python(payload or {}),
            requested_by=requested_by,
            correlation_id=correlation_id,
            attempts=0,
            submitted_at=utc_now(),
        )
    )

    def deposit(_session: Session) -> None:
        try:
            queue.deposit(task_id)
        except RedisError:
            logger.warning("task.deposit_failed", task_id=str(task_id), exc_info=True)

    event.listen(session, "after_commit", deposit, once=True)
    return task_id


def pending_task(session: Session, kind: TaskKind) -> UUID | None:
    """Give a task of a kind that is queued or running, if there is one."""
    pending = (BackgroundTask.kind == kind) & BackgroundTask.status.in_(PENDING)
    return session.scalar(select(BackgroundTask.id).where(pending).limit(1))


def read_task(session: Session, task_id: UUID, requested_by: UUID) -> BackgroundTask | None:
    """Give a task its requester asked for; ``None`` if there is none, or another asked for it."""
    row = session.get(BackgroundTask, task_id)
    return None if row is None or row.requested_by != requested_by else row


@dataclass(frozen=True, slots=True)
class TaskFilters:
    """Which tasks of a requester a list keeps: of these states, finished since this moment."""

    statuses: Collection[str] | None = None
    finished_since: datetime | None = None


def list_tasks(
    session: Session, requested_by: UUID, filters: TaskFilters, limit: int, offset: int
) -> tuple[list[BackgroundTask], int]:
    """Give a page of the tasks of a requester, the latest first, and how many the filters keep.

    A task that runs is kept whatever the moment given; one that has ended, if it ended since.
    """
    kept = [BackgroundTask.requested_by == requested_by]
    if filters.statuses is not None:
        kept.append(BackgroundTask.status.in_(filters.statuses))
    if filters.finished_since is not None:
        finished = BackgroundTask.finished_at
        kept.append(finished.is_(None) | (finished >= filters.finished_since))
    total = session.scalar(select(func.count()).select_from(BackgroundTask).where(*kept))
    latest = (BackgroundTask.submitted_at.desc(), BackgroundTask.id.desc())
    page = select(BackgroundTask).where(*kept).order_by(*latest).limit(limit).offset(offset)
    return list(session.scalars(page)), total or 0


def keep_tasks(connection: Connection, task_ids: Collection[UUID]) -> None:
    """Keep, before a restoration, the tasks it writes back: its own, and the backups' (#893)."""
    keep(connection, BackgroundTask, BackgroundTask.id.in_(task_ids))


def keep_more_tasks(connection: Connection, task_ids: Collection[UUID]) -> None:
    """Add tasks to those a restoration keeps, if the database still holds them."""
    keep_more(connection, BackgroundTask, BackgroundTask.id.in_(task_ids))


def write_back_tasks(connection: Connection, restoration: UUID, at: datetime) -> None:
    """Write back the tasks kept, as they were kept; fail the other tasks restored pending.

    A task kept — the restoration's, a backup's — is later than the backup: the restored database
    lacks it, or holds an earlier state of it, the backup that the dump caught running, which is
    listed and verified since; it comes back as it was kept (#987), without its requester where the
    restored database lacks the account. Every other task the restored database holds queued or
    running fails, under its own correlation, but the restoration's (#892): run again, a backup the
    dump caught running would write over its archive.
    """
    write_back(connection, BackgroundTask, unsure={"requested_by"})
    overwrite(connection, BackgroundTask, unsure={"requested_by"})
    problem = func.jsonb_build_object(
        "code",
        INTERRUPTED["code"],
        "status",
        INTERRUPTED["status"],
        "correlation_id",
        BackgroundTask.correlation_id,
    )
    connection.execute(
        update(BackgroundTask)
        .where(BackgroundTask.status.in_(PENDING), BackgroundTask.id != restoration)
        .values(status="failed", problem=problem, finished_at=at)
    )
