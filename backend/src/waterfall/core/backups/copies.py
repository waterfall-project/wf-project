# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The external copy of the scheduled backups (WF-ADM-0170, WF-EXP-0050, US-2910/L3).

A scheduled backup verified, its rotation done, deposits the task ``backup_copy`` when the schedule
sets a copy and has not suspended it; a manual backup is copied out by its download (WF-ADM-0150),
and a backup whose verification failed is copied nowhere (#4230). The task reads here what to copy
and where — the schedule at the time it runs —, writes the archive under the name of its date, and
the result of the copy on the row of the backup: when, where, and why the location refused it.

The copies of a folder turn as the backups do: beyond the number the schedule keeps there — at
least the retention of the platform (WF-EXP-0050) —, the oldest go. Only the copies the platform
writes count, by the form of their name: nothing else the folder holds is ever removed.

The outcome of the latest copy is that of its task, as for the backup (#4230): the gauge of the
metrics, which the alert ``scheduled_backup_copy_failed`` reads, and the status screen say the same.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import update

from waterfall.core.backups.schedule import read_backup_schedule
from waterfall.core.backups.tables import Backup
from waterfall.platform.tasks import BackgroundTask, Outcome, last_ended, submit_after

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime

    from sqlalchemy.orm import Session

# The name of a copy: the date of its backup, universal time, so that the names sort by date.
COPY_NAME = re.compile(r"waterfall-backup-\d{8}T\d{6}Z\.tar")


@dataclass(frozen=True, slots=True)
class CopyToMake:
    """A backup to copy, and where: its archive, its size, the location, the folder, the count."""

    backup_id: UUID
    object_key: str
    size_bytes: int
    name: str
    location: str
    path: str
    retained_count: int


@dataclass(frozen=True, slots=True)
class CopyMade:
    """The result of a copy: when, to which location and folder, and why it was refused, if it was.

    ``failure`` is an ``ExternalBackupFailure`` of the contract, ``None`` for a copy made.
    """

    at: datetime
    location: str
    path: str
    failure: str | None = None


@dataclass(frozen=True, slots=True)
class FailedCopy:
    """What the alert of a failed copy names: the backup, the location, and the reason if known."""

    backup_id: UUID
    location: str | None
    failure: str | None


def copy_name(taken_at: datetime) -> str:
    """Name the copy of a backup by its date, as its download is named."""
    return f"waterfall-backup-{taken_at:%Y%m%dT%H%M%SZ}.tar"


def deposit_copy(session: Session, backup_id: UUID) -> UUID | None:
    """Deposit the copy of a backup just taken, if it is to be copied; give its task.

    Only a scheduled backup whose verification passed, under a schedule that sets a copy and has
    not suspended it (WF-ADM-0170); none otherwise. The task is written in the transaction of the
    backup, and is there only if the backup is.
    """
    row = session.get_one(Backup, backup_id)
    if row.origin != "scheduled" or row.verification != "passed":
        return None
    copy = read_backup_schedule(session).schedule.external_copy
    if copy is None or not copy.is_enabled:
        return None
    return submit_after(session, "backup_copy", {"backup_id": str(backup_id)})


def copy_to_make(session: Session, backup_id: UUID) -> CopyToMake | None:
    """Give the copy a task makes of a backup, as the schedule sets it now; ``None`` if none.

    A copy removed or suspended since the deposit, or a backup gone since, is not made.
    """
    copy = read_backup_schedule(session).schedule.external_copy
    row = session.get(Backup, backup_id)
    if copy is None or not copy.is_enabled or row is None:
        return None
    return CopyToMake(
        backup_id,
        row.object_key,
        row.size_bytes,
        copy_name(row.taken_at),
        copy.location,
        copy.path,
        copy.retained_count,
    )


def copies_beyond(names: Collection[str], retained_count: int) -> list[str]:
    """Give the copies of a folder beyond the number kept, the oldest first; never another file.

    A copy is named by the date of its backup (``copy_name``): the names sort as the dates.
    """
    copies = sorted(name for name in names if COPY_NAME.fullmatch(name))
    return copies[: max(len(copies) - retained_count, 0)]


def record_copy(session: Session, backup_id: UUID, made: CopyMade) -> None:
    """Write the result of the latest copy of a backup on its row."""
    session.execute(
        update(Backup)
        .where(Backup.id == backup_id)
        .values(
            last_copy_at=made.at,
            last_copy_location=made.location,
            last_copy_path=made.path,
            last_copy_failure=made.failure,
        )
    )


def last_copy_outcome(session: Session) -> Outcome | None:
    """Give how the latest copy ended; ``None`` when no copy is set, or none has ended yet.

    The outcome of its task, as for the backup: a copy the location refused fails its task.
    """
    if read_backup_schedule(session).schedule.external_copy is None:
        return None
    ended = last_ended(session, "backup_copy", by_platform=True)
    return None if ended is None else Outcome(ended.at, succeeded=ended.succeeded)


def failed_copy(session: Session) -> FailedCopy | None:
    """Give what the latest copy, failed, names; ``None`` if it succeeded or none has ended.

    The backup is the one its task names; the location and the reason, those its row says, when
    the location refused — a copy that failed before reaching it says no reason.
    """
    ended = last_ended(session, "backup_copy", by_platform=True)
    if ended is None or ended.succeeded:
        return None
    task = session.get_one(BackgroundTask, ended.task_id)
    backup_id = UUID(str(task.payload["backup_id"]))
    row = session.get(Backup, backup_id)
    if row is None or row.last_copy_at is None:
        copy = read_backup_schedule(session).schedule.external_copy
        return FailedCopy(backup_id, None if copy is None else copy.location, None)
    return FailedCopy(backup_id, row.last_copy_location, row.last_copy_failure)
