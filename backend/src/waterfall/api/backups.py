# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The backups of the platform (FBS-1.4): their list, one of them, a backup asked for, its copy.

A backup is taken by the worker (WF-ARC-0090): the request deposits the task and answers at once.
The list says of each its date, its size and the outcome of its verification (WF-ADM-0150), and the
commands the caller may exercise on it, each available or not with the conditions it lacks
(WF-IHM-0090): the server says what can be done, the front deduces nothing. The copy out of the
platform is the archive as the bucket of the backups keeps it, streamed, with its length. It holds
both databases whole: reading it asks for the permission to change the backups besides the one to
read them.
"""

from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, Backup, PaginationMeta
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.tasks import task_ref
from waterfall.core.access_roles.interface import Actor
from waterfall.core.backups.interface import (
    NOT_FOUND,
    BackupView,
    list_backups,
    read_backup,
)
from waterfall.platform.errors import NotFoundError
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.tasks import BackgroundTask, pending_task, submit

router = APIRouter(tags=["platform"])

CONSULTATION = "backups.read"
CHANGE = "backups.write"
READ = [Depends(Requires(CONSULTATION))]
CREATE = [Depends(Requires(CHANGE))]
COPY = [Depends(Requires(CONSULTATION, CHANGE))]
RESTORATION = "platform_restore"
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


def _command(command: str, lacking: list[str]) -> dict[str, Any]:
    return {"command": command, "is_available": not lacking, "missing_conditions": lacking}


def commands(view: BackupView, actor: Actor, platform: Platform) -> list[dict[str, Any]]:
    """List the commands of a backup the caller may exercise, in the order of `BackupCommand`.

    The marking that changes its state, under the permission to change the backups, lacking no
    restoration running; the download, under the permissions to read and to change them, lacking
    a verification passed; the restoration, under the permission to restore the platform, lacking
    a verification passed, no backup and no restoration running (WF-ADM-0100, WF-ADM-0150,
    WF-ADM-0160). A backup is running from its deposit to the end of its task.
    """
    held = set(actor.permissions)
    unverified = [] if view.verification == "passed" else [VERIFIED]
    listed: list[dict[str, Any]] = []
    if CHANGE in held:
        marking = "release" if view.is_retained else "retain"
        listed.append(_command(marking, [NO_RESTORE_RUNNING] if platform.restore_running else []))
    if {CONSULTATION, CHANGE} <= held:
        listed.append(_command("download", unverified))
    if RESTORATION in held:
        running = [NO_BACKUP_RUNNING] if platform.backup_running else []
        restoring = [NO_RESTORE_RUNNING] if platform.restore_running else []
        listed.append(_command("restore", unverified + running + restoring))
    return listed


def backup(view: BackupView, actor: Actor, platform: Platform) -> Backup:
    """Describe a backup as the contract does: both databases, whatever its origin."""
    return Backup.model_validate(
        {
            "backup_id": view.backup_id,
            "taken_at": view.taken_at,
            "size_bytes": view.size_bytes,
            "verification": view.verification,
            "is_retained": view.is_retained,
            "scope": "database",
            "origin": view.origin,
            "available_commands": commands(view, actor, platform),
        }
    )


@router.get("/backups", operation_id="listBackups", dependencies=READ, response_model=None)
def get_backups(
    session: Transaction,
    actor: Acting,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Give a page of the backups, the latest first (WF-ADM-0150)."""
    views, total = list_backups(session, limit, offset)
    platform = platform_of(session)
    return {
        "items": [backup(view, actor, platform).model_dump(mode="json") for view in views],
        "meta": PaginationMeta(limit=limit, offset=offset, total=total).model_dump(),
    }


@router.post(
    "/backups",
    operation_id="startBackup",
    dependencies=CREATE,
    status_code=202,
    response_model_exclude_unset=True,
)
def post_backup(account: Caller, session: Transaction, services: ServicesOf) -> BackgroundTaskRef:
    """Deposit a backup for the worker, asked for by the caller, and say where it stands."""
    task_id = submit(session, services.queue, "backup", account.user_id)
    return task_ref(session.get_one(BackgroundTask, task_id))


@router.get("/backups/{backup_id}", operation_id="getBackup", dependencies=READ)
def get_backup(backup_id: UUID, session: Transaction, actor: Acting) -> Backup:
    """Give a backup: its date, its size, the outcome of its verification (WF-ADM-0150)."""
    return backup(read_backup(session, backup_id), actor, platform_of(session))


@router.get("/backups/{backup_id}/content", operation_id="downloadBackup", dependencies=COPY)
def get_backup_content(backup_id: UUID, services: ServicesOf) -> StreamingResponse:
    """Stream the archive of a backup out of the platform (WF-ADM-0150).

    The backup is read in a transaction of its own, closed before the archive streams: no
    connection is held while the bucket is read. An archive the bucket no longer holds is a backup
    that cannot be copied, refused as one that does not exist (404).
    """
    with services.database.transaction() as session:
        view = read_backup(session, backup_id)
    try:
        chunks = services.backups.stream(view.object_key)
    except MissingObjectError:
        raise NotFoundError(NOT_FOUND) from None
    name = f"waterfall-backup-{view.taken_at:%Y%m%dT%H%M%SZ}.tar"
    headers = {
        "Content-Disposition": f'attachment; filename="{name}"',
        "Content-Length": str(view.size_bytes),
    }
    return StreamingResponse(chunks, media_type="application/octet-stream", headers=headers)
