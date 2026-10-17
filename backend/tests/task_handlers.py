# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the worker share: a handler they register, and the work it leaves.

The handler does what the reading of the accounts will do (US-0370/L2): it writes in the database
as the platform, and inscribes it in the journal, under the correlation of its task.
"""

from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from waterfall.platform.audit import AuditEntry, AuditObject, Inscription, record
from waterfall.platform.database import Database, utc_now
from waterfall.platform.logs import logging_context
from waterfall.platform.queue import TaskQueue
from waterfall.platform.tasks import BackgroundTask, Task, TaskKind, submit
from waterfall.worker.runner import lock_run

# The account the handler says it updated: an inscription names it without a foreign key.
UPDATED = UUID("01926f3a-7c00-7000-8000-0000000003a7")
# The correlation of the request that deposits a task, as the API binds it to its logs.
REQUEST = "request-3f6a"


class Runs(list[UUID]):
    """A handler that keeps the tasks it runs, in their order."""

    def __call__(self, _session: Session, task: Task) -> None:
        """Run a task: keep it."""
        self.append(task.task_id)


def inscribe(session: Session, task: Task) -> None:
    """Inscribe the update of an account by the platform, as the reading of the accounts does."""
    audited = AuditObject("user", UPDATED, "Claire Martin")
    params = {"task_id": str(task.task_id)}
    record(session, Inscription("user_update", None, audited, utc_now(), params=params))


def deposit(
    database: Database,
    queue: TaskQueue,
    kind: TaskKind = "identity_sync",
    requested_by: UUID | None = None,
    correlation_id: str = REQUEST,
) -> UUID:
    """Submit a task as a request does: under its correlation, deposited once committed."""
    with logging_context(correlation_id=correlation_id), database.transaction() as session:
        return submit(session, queue, kind, requested_by)


def inscriptions(database: Database) -> list[AuditEntry]:
    """Read the inscriptions of the journal."""
    with database.transaction() as session:
        return list(session.scalars(select(AuditEntry)))


def task(database: Database, task_id: UUID) -> BackgroundTask:
    """Read a task as the database holds it."""
    with database.transaction() as session:
        found = session.get(BackgroundTask, task_id)
        assert found is not None
        return found


@contextmanager
def held_run(database: Database, task_id: UUID) -> Generator[None]:
    """Hold the lock of the run of a task, as a worker that runs it does, for the block."""
    with database.transaction() as session:
        assert lock_run(session, task_id)
        yield
