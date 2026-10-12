# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the backups offer to the API and to the worker (FBS-1.4, WF-ADM-0150).

The list of the backups, the latest first, and one backup read; a backup taken by the worker,
recorded with the outcome of its verification and inscribed in the journal of audit at its date,
the instant of the state it copies (WF-SEC-0030).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from waterfall.core.backups.tables import Backup
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import Act, AuditObject, Inscription, record
from waterfall.platform.errors import NotFoundError
from waterfall.platform.identifiers import new_id

NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True, slots=True)
class BackupView:
    """A backup as the API gives it, and the key of its archive in the bucket of the backups."""

    backup_id: UUID
    taken_at: datetime
    size_bytes: int
    verification: str
    origin: str
    is_retained: bool
    object_key: str


@dataclass(frozen=True, slots=True)
class TakenBackup:
    """A backup the worker has stored and verified: what the row and the journal keep of it."""

    task_id: UUID
    taken_at: datetime
    size_bytes: int
    object_key: str
    application_version: str
    schema_revision: str
    is_verified: bool


def _view(row: Backup) -> BackupView:
    return BackupView(
        row.id,
        row.taken_at,
        row.size_bytes,
        row.verification,
        row.origin,
        row.is_retained,
        row.object_key,
    )


def list_backups(session: Session, limit: int, offset: int) -> tuple[list[BackupView], int]:
    """Give a page of the backups, the latest first, and how many there are."""
    total = session.scalar(select(func.count()).select_from(Backup))
    latest = select(Backup).order_by(Backup.taken_at.desc(), Backup.id.desc())
    rows = session.scalars(latest.limit(limit).offset(offset))
    return [_view(row) for row in rows], total or 0


def read_backup(session: Session, backup_id: UUID) -> BackupView:
    """Give a backup, or refuse it as an object that does not exist (404)."""
    row = session.get(Backup, backup_id)
    if row is None:
        raise NotFoundError(NOT_FOUND)
    return _view(row)


def add_backup(session: Session, taken: TakenBackup, act: Act) -> UUID:
    """Record a backup taken, and inscribe it at its date by whom asked for it, or the platform.

    A backup the platform takes of itself is scheduled; one an account asks for, manual.
    """
    backup_id = new_id()
    verification = "passed" if taken.is_verified else "failed"
    origin = "scheduled" if act.author is None else "manual"
    session.execute(
        insert(Backup).values(
            id=backup_id,
            taken_at=taken.taken_at,
            size_bytes=taken.size_bytes,
            verification=verification,
            origin=origin,
            is_retained=False,
            object_key=taken.object_key,
            application_version=taken.application_version,
            schema_revision=taken.schema_revision,
            task_id=taken.task_id,
        )
    )
    params = {"verification": verification, "origin": origin}
    audited = AuditObject("backup", backup_id, None)
    actor = inscribed_actor(session, act.author)
    record(session, Inscription("backup", actor, audited, act.at, params=params))
    return backup_id
