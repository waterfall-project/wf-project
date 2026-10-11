# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The backups of the platform (FBS-1.4): their list, one of them, a backup asked for, its copy.

A backup is taken by the worker (WF-ARC-0090): the request deposits the task and answers at once.
The list says of each its date, its size and the outcome of its verification (WF-ADM-0150); the copy
out of the platform is the archive as the bucket of the backups keeps it, streamed. It holds both
databases whole: reading it asks for the permission to change the backups besides the one to read
them.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, Backup, PaginationMeta
from waterfall.api.evaluation import Requires
from waterfall.api.tasks import task_ref
from waterfall.core.backups.interface import (
    NOT_FOUND,
    BackupView,
    list_backups,
    read_backup,
)
from waterfall.platform.errors import NotFoundError
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.tasks import BackgroundTask, submit

router = APIRouter(tags=["platform"])

CONSULTATION = "backups.read"
CHANGE = "backups.write"
READ = [Depends(Requires(CONSULTATION))]
CREATE = [Depends(Requires(CHANGE))]
COPY = [Depends(Requires(CONSULTATION, CHANGE))]


def backup(view: BackupView) -> Backup:
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
        }
    )


@router.get("/backups", operation_id="listBackups", dependencies=READ, response_model=None)
def get_backups(
    session: Transaction,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Give a page of the backups, the latest first (WF-ADM-0150)."""
    views, total = list_backups(session, limit, offset)
    return {
        "items": [backup(view).model_dump(mode="json") for view in views],
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
def get_backup(backup_id: UUID, session: Transaction) -> Backup:
    """Give a backup: its date, its size, the outcome of its verification (WF-ADM-0150)."""
    return backup(read_backup(session, backup_id))


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
    headers = {"Content-Disposition": f'attachment; filename="{name}"'}
    return StreamingResponse(chunks, media_type="application/octet-stream", headers=headers)
