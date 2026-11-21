# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rotation of the backups, and the mark that spares one of it (WF-ADM-0170).

A backup verified turns the list: the oldest backups not marked beyond the retention of the
schedule go, manual and scheduled counted together; a backup marked is never counted, and never
deleted. Only the rotation deletes a backup, and the task it took goes after it (the purge of the
tasks, which spares that of each backup listed). The archive of a backup deleted is the caller's to
remove from the bucket, once its transaction is committed.
"""

from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from waterfall.core.backups.listing import BackupView, view_of
from waterfall.core.backups.tables import Backup
from waterfall.platform.errors import NOT_FOUND, NotFoundError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session


def rotate(session: Session, retained_count: int) -> list[str]:
    """Delete the oldest backups not marked beyond ``retained_count``; give their archives' keys.

    The mark is judged again by the deletion: a backup marked meanwhile survives it.
    """
    unmarked = ~Backup.is_retained
    oldest = (
        select(Backup.id)
        .where(unmarked)
        .order_by(Backup.taken_at.desc(), Backup.id.desc())
        .offset(retained_count)
    )
    gone = session.execute(
        delete(Backup).where(Backup.id.in_(oldest), unmarked).returning(Backup.object_key)
    )
    return list(gone.scalars())


def mark_backup(session: Session, backup_id: UUID, *, is_retained: bool) -> BackupView:
    """Mark a backup to keep, or release it; give it as marked, or refuse one unknown (404).

    The row is locked, then written: the rotation that deletes it waits for the mark.
    """
    locked = select(Backup).where(Backup.id == backup_id).with_for_update()
    row = session.scalars(locked.execution_options(populate_existing=True)).one_or_none()
    if row is None:
        raise NotFoundError(NOT_FOUND)
    row.is_retained = is_retained
    session.flush()
    return view_of(row)
