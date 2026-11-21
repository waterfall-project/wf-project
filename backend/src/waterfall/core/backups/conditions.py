# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a command of the backups lacks, said once for what announces it and what refuses it.

A backup announces its commands with the conditions each lacks (``available_commands``,
WF-IHM-0090); the operation a command stands for refuses the same state with 409, naming the first
condition it lacks, in the order the command lists them (``STATE_FORBIDS_OPERATION``,
``params.missing_condition``, #1035). The two read one definition, so that a command announced
available is never refused for a reason it did not give, and the other way round.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from waterfall.platform.errors import STATE_FORBIDS_OPERATION, ConflictError
from waterfall.platform.locks import BACKUP_LOCK, RESTORE_LOCK
from waterfall.platform.tasks import pending_task

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

VERIFIED = "backup_verified"
NO_BACKUP_RUNNING = "no_backup_running"
NO_RESTORE_RUNNING = "no_restore_running"


@dataclass(frozen=True, slots=True)
class Platform:
    """What the commands of every backup depend on, read once for a reading: what runs now."""

    backup_running: bool
    restore_running: bool


def platform_of(session: Session) -> Platform:
    """Read whether a backup or a restoration is queued or running."""
    return Platform(
        backup_running=pending_task(session, "backup") is not None,
        restore_running=pending_task(session, "restore") is not None,
    )


def marking_lacks(platform: Platform) -> list[str]:
    """Give what the marking of a backup lacks: no restoration running."""
    return [NO_RESTORE_RUNNING] if platform.restore_running else []


def download_lacks(verification: str) -> list[str]:
    """Give what the download of a backup lacks: a verification passed."""
    return [] if verification == "passed" else [VERIFIED]


def restoration_lacks(verification: str, platform: Platform) -> list[str]:
    """Give what the restoration of a backup lacks: a verification passed, nothing else running."""
    running = [NO_BACKUP_RUNNING] if platform.backup_running else []
    restoring = [NO_RESTORE_RUNNING] if platform.restore_running else []
    return [*download_lacks(verification), *running, *restoring]


def backup_start_lacks(platform: Platform) -> list[str]:
    """Give what the start of a backup lacks: no backup and no restoration running."""
    running = [NO_BACKUP_RUNNING] if platform.backup_running else []
    return [*running, *marking_lacks(platform)]


def lock_backup_deposit(session: Session) -> list[str]:
    """Take the locks a backup is deposited under, then give what its start lacks, read under them.

    ``BACKUP_LOCK``, then ``RESTORE_LOCK`` shared, in the order of ``waterfall.platform.locks``:
    ``startBackup`` and the planned command deposit by this one function, so that two deposits wait
    for each other, and a restoration deposited meanwhile is waited for, or seen (#4369). The locks
    are held to the end of the transaction.
    """
    session.execute(select(func.pg_advisory_xact_lock(BACKUP_LOCK)))
    session.execute(select(func.pg_advisory_xact_lock_shared(RESTORE_LOCK)))
    return backup_start_lacks(platform_of(session))


def refuse_if_lacking(lacking: list[str]) -> None:
    """Refuse (409) a command that lacks a condition, naming the first one."""
    if lacking:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": lacking[0]})
