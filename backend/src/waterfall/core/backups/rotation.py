# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rotation of the backups, and the mark that spares one of it (WF-ADM-0170).

A backup verified turns the list: the oldest backups not marked and verified beyond the retention
of the schedule go, manual and scheduled counted together, and so do those whose verification
failed, first; the last backup verified is never deleted; a backup marked is never counted, and
never deleted. Only the rotation deletes a backup, and the task it took goes after it (the purge
of the tasks, which spares that of each backup listed). The archive of a backup deleted is the
caller's to remove from the bucket, once its transaction is committed.
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
    """Turn the list: delete what falls beyond the retention; give the archives' keys.

    The retention keeps the most recent backups not marked whose verification passed; the last of
    them is never deleted, whatever the retention (#4366). A backup not marked whose verification
    failed is not counted, and goes first, the oldest first, with no ceiling; a backup marked is
    neither counted nor deleted. The rule is the verification's, not the task's: it holds however
    the failure is represented. The mark is judged again by the deletion: a backup marked meanwhile
    survives it.

    This deviates deliberately from the letter of WF-ADM-0170-A ("the oldest backups not marked
    beyond the retention"), which counted the failed ones: with a retention of seven and seven
    failures newer than a good backup, the last restorable one would go.
    """
    unmarked = ~Backup.is_retained
    passed = Backup.verification == "passed"
    failed = session.execute(
        select(Backup.id, Backup.object_key)
        .where(unmarked, ~passed)
        .order_by(Backup.taken_at, Backup.id)
    ).all()
    beyond = session.execute(
        select(Backup.id, Backup.object_key)
        .where(unmarked, passed)
        .order_by(Backup.taken_at.desc(), Backup.id.desc())
        .offset(max(retained_count, 1))
    ).all()
    # The oldest of each kind first: the failed ones, then the verified ones beyond the retention.
    doomed = [*failed, *reversed(beyond)]
    gone = set(
        session.scalars(
            delete(Backup)
            .where(Backup.id.in_([row.id for row in doomed]), unmarked)
            .returning(Backup.id)
        )
    )
    return [row.object_key for row in doomed if row.id in gone]


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
