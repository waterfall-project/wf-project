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
from typing import TYPE_CHECKING, Any, Literal, get_args
from uuid import UUID

from pydantic_core import to_jsonable_python
from redis.exceptions import RedisError
from sqlalchemy import (
    CheckConstraint,
    Connection,
    SmallInteger,
    Text,
    delete,
    event,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, Session, aliased, mapped_column
from structlog.contextvars import get_contextvars

from waterfall.platform.database import Base, UtcDateTime, utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import get_logger
from waterfall.platform.restoration import keep, keep_more, overwrite, write_back

if TYPE_CHECKING:
    from waterfall.platform.queue import TaskQueue

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
# The kinds the platform schedules (EP-13): requested by nobody, so listed to nobody, they are not
# the contract's (migration 0035).
type ScheduledKind = Literal["purge", "backup_copy", "restore_test"]
CONTRACT_KINDS: tuple[str, ...] = get_args(TaskKind.__value__)
SCHEDULED_KINDS: tuple[str, ...] = get_args(ScheduledKind.__value__)
KINDS = (*CONTRACT_KINDS, *SCHEDULED_KINDS)
STATUSES = ("queued", "running", "succeeded", "failed")
PENDING = ("queued", "running")
# The kinds the platform deposits of itself, whose latest the purge spares: those the planned
# command schedules (``waterfall.worker.schedule.planned``), and the two it does not schedule yet,
# ``backup_copy``, which a backup deposits, and ``restore_test``, whose planning US-2930 adds. A
# test compares this list to ``planned``, those two excepted.
PLANNED_KINDS: tuple[str, ...] = ("identity_sync", "backup", *SCHEDULED_KINDS)
FINISHED = ("succeeded", "failed")
# The key of the payload of a task that names the project it aims at, which waits for it.
PROJECT = "project_id"
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


class UndoneError(Exception):
    """A task that fails, its work undone, and what it leaves written in its place.

    A handler whose failure must leave a trace on its own rows — the import passed ``failed`` or
    ``refused``, its file to delete once committed (EP-06) — raises this from the cause of its
    failure: the worker undoes the handler's work, then writes ``trace`` in the transaction of the
    task, and fails the task as the cause says, a refusal with its code, anything else as an
    internal error. The trace is written with the end of the task, or not at all.
    """

    def __init__(self, cause: Exception, trace: Callable[[Session], None]) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.trace = trace


def _written(
    session: Session,
    kind: TaskKind | ScheduledKind,
    requested_by: UUID | None,
    payload: Mapping[str, Any] | None,
) -> UUID:
    """Write a task, queued, under the correlation of what submits it; give its identifier."""
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
    return task_id


def submit_after(
    session: Session, kind: ScheduledKind, payload: Mapping[str, Any] | None = None
) -> UUID:
    """Write a task the platform deposits after another, in the transaction of the one that runs.

    The worker that runs the first puts it in the queue: it deposits again, at its start and at
    each sweep (``Worker.redeposit``, a minute apart), every task queued that the queue does not
    name. A handler holds no queue of its own, and the task waits that long at most; the copy of
    a backup, which follows it, is one (EP-13, "Les sauvegardes").
    """
    return _written(session, kind, None, payload)


def submit(
    session: Session,
    queue: TaskQueue,
    kind: TaskKind | ScheduledKind,
    requested_by: UUID | None,
    payload: Mapping[str, Any] | None = None,
) -> UUID:
    """Write a task, queued, in the transaction of ``session``, and deposit it once committed.

    The deposit never fails the transaction, which is already committed: if Redis refuses it, the
    task stays queued, and the worker deposits it again.
    """
    task_id = _written(session, kind, requested_by, payload)

    def deposit(_session: Session) -> None:
        try:
            queue.deposit(task_id)
        except RedisError:
            logger.warning("task.deposit_failed", task_id=str(task_id), exc_info=True)

    event.listen(session, "after_commit", deposit, once=True)
    return task_id


def pending_task(session: Session, kind: TaskKind | ScheduledKind) -> UUID | None:
    """Give a task of a kind that is queued or running, if there is one."""
    pending = (BackgroundTask.kind == kind) & BackgroundTask.status.in_(PENDING)
    return session.scalar(select(BackgroundTask.id).where(pending).limit(1))


def last_submitted(session: Session, kind: TaskKind | ScheduledKind) -> datetime | None:
    """Give when the latest task of a kind the platform deposited of itself was submitted.

    Whatever its state: the schedule waits an interval from the last deposit, not from its end.
    """
    kept = (BackgroundTask.kind == kind, BackgroundTask.requested_by.is_(None))
    return session.scalar(select(func.max(BackgroundTask.submitted_at)).where(*kept))


def purge_ended(session: Session, before: datetime, spared: Collection[UUID]) -> int:
    """Delete the tasks ended before ``before``, ``spared`` apart, and give how many went.

    A task is kept for the retention of its result (§4.4.1, WF-DAT-0080); the report of a reading
    of the accounts goes with its task (#921). ``spared`` are the tasks another table still names
    and refuses to lose — the task of a backup — which the module of that table gives. The latest
    task the platform deposited of each planned kind is spared as well, however old: the schedule
    reads when it was submitted to know the next is due, and an interval longer than the retention
    would else be due again at each purge.
    """
    ended = BackgroundTask.status.in_(FINISHED) & (BackgroundTask.finished_at < before)
    newer = aliased(BackgroundTask)
    superseded = (
        select(newer.id)
        .where(
            newer.kind == BackgroundTask.kind,
            newer.requested_by.is_(None),
            newer.submitted_at > BackgroundTask.submitted_at,
        )
        .exists()
    )
    latest = BackgroundTask.kind.in_(PLANNED_KINDS) & BackgroundTask.requested_by.is_(None)
    gone = session.execute(
        delete(BackgroundTask)
        .where(ended, BackgroundTask.id.not_in(spared), ~latest | superseded)
        .returning(BackgroundTask.id)
    )
    return len(gone.all())


@dataclass(frozen=True, slots=True)
class Ended:
    """The end of a task: which, when, and whether it succeeded."""

    task_id: UUID
    at: datetime
    succeeded: bool


@dataclass(frozen=True, slots=True)
class Outcome:
    """How the latest run of an operation the platform runs on a schedule ended, and when."""

    at: datetime
    succeeded: bool


def last_ended(
    session: Session, kind: TaskKind | ScheduledKind, *, by_platform: bool = False
) -> Ended | None:
    """Give the latest task of a kind that has ended, or ``None`` if none has yet.

    ``by_platform`` keeps only the tasks the platform deposited of itself, without a requester:
    those it schedules (PBS-5.3).
    """
    kept = [BackgroundTask.kind == kind, BackgroundTask.status.in_(FINISHED)]
    if by_platform:
        kept.append(BackgroundTask.requested_by.is_(None))
    latest = (BackgroundTask.finished_at.desc(), BackgroundTask.id.desc())
    columns = (BackgroundTask.id, BackgroundTask.finished_at, BackgroundTask.status)
    row = session.execute(select(*columns).where(*kept).order_by(*latest).limit(1)).first()
    if row is None or row.finished_at is None:
        return None
    return Ended(row.id, row.finished_at, row.status == "succeeded")


@dataclass(frozen=True, slots=True)
class Waiting:
    """The tasks queued that no worker has taken yet: how many, and since when the oldest waits."""

    count: int
    oldest_since: datetime | None


def waiting(session: Session) -> Waiting:
    """Count the tasks queued, and give the moment the oldest of them was submitted."""
    queued = BackgroundTask.status == "queued"
    count, oldest = session.execute(
        select(func.count(), func.min(BackgroundTask.submitted_at)).where(queued)
    ).one()
    return Waiting(count, oldest)


def project_task_pending(session: Session, project_id: UUID, besides: UUID | None = None) -> bool:
    """Tell whether a task that aims at a project is queued or running, ``besides`` apart.

    A task aims at a project when its payload names it under ``PROJECT``, as the marking of a
    revision does (US-0970); this module knows no table of the projects. ``besides`` is the task
    that asks, running itself: the application of an import, which opens the current revision it
    writes in, is not refused by its own run (EP-06, "L'import en deux temps").
    """
    aimed = BackgroundTask.payload[PROJECT].astext == str(project_id)
    pending = select(BackgroundTask.id).where(BackgroundTask.status.in_(PENDING), aimed)
    if besides is not None:
        pending = pending.where(BackgroundTask.id != besides)
    return session.scalar(pending.limit(1)) is not None


def projects_with_task_pending(session: Session, project_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, among ``project_ids``, those a task that is queued or running aims at, in one query."""
    if not project_ids:
        return frozenset()
    named = BackgroundTask.payload[PROJECT].astext
    wanted = [str(project_id) for project_id in project_ids]
    rows = session.scalars(
        select(named).where(BackgroundTask.status.in_(PENDING), named.in_(wanted)).distinct()
    )
    return frozenset(UUID(value) for value in rows)


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
