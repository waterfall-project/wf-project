# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the backups offer to the API, the worker and the restoration (FBS-1.4, WF-ADM-0150, 0160).

The list of the backups, the latest first, and one backup read; a backup taken by the worker,
recorded with the outcome of its verification and inscribed in the journal of audit at its date,
the instant of the state it copies (WF-SEC-0030). Around the replacement of the databases, a
restoration keeps the journal, the list of the backups and their tasks, and writes back what the
restored database lacks: the archives of the backups taken since stay in the bucket, and stay
listed (#893).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Connection, func, insert, select
from sqlalchemy.orm import Session

from waterfall.core.backups.tables import Backup
from waterfall.core.users.interface import inscribed_actor
from waterfall.platform.audit import Act, AuditEntry, AuditObject, Inscription, record
from waterfall.platform.errors import NotFoundError
from waterfall.platform.identifiers import new_id
from waterfall.platform.restoration import begin_keeping, end_keeping, is_kept, keep, write_back
from waterfall.platform.tasks import keep_tasks, write_back_tasks

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

    A backup the platform takes of itself is scheduled; one an account asks for, manual. The
    inscription carries no parameter: the contract gives a backup an empty ``params`` until the
    EPIC that realises its data, the row keeping its verification and its origin.
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
    audited = AuditObject("backup", backup_id, None)
    actor = inscribed_actor(session, act.author)
    record(session, Inscription("backup", actor, audited, act.at))
    return backup_id


def keep_for_restoration(connection: Connection, restoration: UUID) -> None:
    """Keep, once, what a restoration writes back once it has replaced the databases.

    The journal of audit (WF-ADM-0160, #894), the list of the backups (#893), the task of the
    restoration and those of the backups, and the rights of the role of the service, copied aside
    in the database the restoration replaces; a restoration taken up finds them kept already, and
    does not read again a database half replaced.
    """
    if is_kept(connection):
        return
    begin_keeping(connection)
    keep(connection, AuditEntry)
    keep(connection, Backup)
    keep_tasks(connection, [restoration, *connection.scalars(select(Backup.task_id))])


def write_back_after_restoration(connection: Connection, restoration: UUID, at: datetime) -> None:
    """Write back, in the restored database, what ``keep_for_restoration`` kept, then forget it.

    The tasks first, which the backups name; the backups and the inscriptions the restored
    database lacks, by their identifier — an inscription made while the database was dumped is in
    the dump already, and is not written twice —; the tasks restored pending fail (#892), and the
    role of the service gets its rights back. ``at`` ends the tasks that fail.
    """
    write_back_tasks(connection, restoration, at)
    write_back(connection, Backup)
    write_back(connection, AuditEntry)
    end_keeping(connection)
