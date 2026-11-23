# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the backups share: a backup recorded around the worker.

A backup is written with the task that took it, ended, as the worker leaves them.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import insert, select

from waterfall.core.backups.tables import Backup
from waterfall.platform.identifiers import new_id
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
    from waterfall.platform.database import Database

CORRELATION = "test-backup-rows"


@dataclass(frozen=True, slots=True)
class Row:
    """What a test varies of a backup: the rest is as the worker leaves it."""

    origin: str = "manual"
    verification: str = "passed"
    size_bytes: int = 1000
    is_retained: bool = False
    key: str | None = None


def recorded(database: Database, taken_at: datetime, row: Row | None = None) -> UUID:
    """Record a backup taken at an instant, with its task ended; give its identifier."""
    row = row or Row()
    task_id, backup_id = new_id(), new_id()
    with database.transaction() as session:
        session.execute(
            insert(BackgroundTask).values(
                id=task_id,
                kind="backup",
                status="succeeded",
                progress=100,
                payload={},
                requested_by=None,
                correlation_id=CORRELATION,
                attempts=1,
                submitted_at=taken_at,
                started_at=taken_at,
                finished_at=taken_at,
            )
        )
        session.execute(
            insert(Backup).values(
                id=backup_id,
                taken_at=taken_at,
                size_bytes=row.size_bytes,
                verification=row.verification,
                origin=row.origin,
                is_retained=row.is_retained,
                object_key=row.key or f"backup-{uuid4()}.tar",
                application_version="test",
                schema_revision="0047",
                task_id=task_id,
            )
        )
    return backup_id


def listed(database: Database) -> list[UUID]:
    """Give the identifiers of the backups the database lists, the oldest first."""
    with database.transaction() as session:
        return list(session.scalars(select(Backup.id).order_by(Backup.taken_at, Backup.id)))


def days(count: int, hour: int = 1) -> datetime:
    """Give ``hour`` o'clock, universal time, on the ``count``-th day of October 2026."""
    return datetime(2026, 10, count, hour, 0, tzinfo=UTC)
