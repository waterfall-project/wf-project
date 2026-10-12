# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the family ``tasks``: a caller follows the tasks it asked for (WF-ARC-0090).

Each reads the tasks of its caller alone and asks for no permission: a task another account asked
for, or that the platform scheduled, does not exist for the caller.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime

from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import Text
from waterfall.api.contract.models import BackgroundTaskRef, BackgroundTaskStatus, PaginationMeta
from waterfall.api.queries import listed
from waterfall.platform.errors import NotFoundError
from waterfall.platform.tasks import BackgroundTask, TaskFilters, list_tasks, read_task

router = APIRouter(tags=["tasks"])

NOT_FOUND = "NOT_FOUND"


# Where a task that succeeded gives its result, by its kind: the backup it took, the report of the
# reading of the accounts. The exports, whose result is a file to download, add theirs (EP-07).
BACKUPS = "/api/v1/backups"
IDENTITY_SYNC_REPORT = "/api/v1/identity-syncs/latest"


def result_url(row: BackgroundTask) -> str | None:
    """Give where to read the result of a task, once it has succeeded and if it gives one."""
    if row.status != "succeeded":
        return None
    if row.kind == "backup" and row.result is not None:
        return f"{BACKUPS}/{row.result['backup_id']}"
    return IDENTITY_SYNC_REPORT if row.kind == "identity_sync" else None


def task_ref(row: BackgroundTask) -> BackgroundTaskRef:
    """Describe a task as the contract does, with where to read its result if it gives one."""
    return BackgroundTaskRef.model_validate(
        {
            "task_id": row.id,
            "kind": row.kind,
            "status": row.status,
            "progress": row.progress,
            "submitted_at": row.submitted_at,
            "finished_at": row.finished_at,
            "problem": row.problem,
            "result_url": result_url(row),
        }
    )


def task_filters(
    status: Text | None = None, finished_since: AwareDatetime | None = None
) -> TaskFilters:
    """Read the states kept, separated by commas, and since when the finished tasks are kept.

    The moment is an instant: a date alone, or an hour without its offset, is refused (422).
    """
    return TaskFilters(listed("status", status, BackgroundTaskStatus), finished_since)


@router.get("/tasks", operation_id="listBackgroundTasks")
def get_background_tasks(
    account: Caller,
    session: Transaction,
    filters: Annotated[TaskFilters, Depends(task_filters)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """Give a page of the tasks of the caller, the latest first."""
    rows, total = list_tasks(session, account.user_id, filters, limit, offset)
    return {
        "items": [task_ref(row).model_dump(mode="json", exclude_unset=True) for row in rows],
        "meta": PaginationMeta(limit=limit, offset=offset, total=total).model_dump(),
    }


# A problem says only what it has: its absent fields stay absent, not null.
@router.get("/tasks/{task_id}", operation_id="getBackgroundTask", response_model_exclude_unset=True)
def get_background_task(task_id: UUID, account: Caller, session: Transaction) -> BackgroundTaskRef:
    """Give a task of the caller: where it stands, and why it failed if it did."""
    row = read_task(session, task_id, account.user_id)
    if row is None:
        raise NotFoundError(NOT_FOUND)
    return task_ref(row)
