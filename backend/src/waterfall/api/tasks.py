# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the family ``tasks``: a caller follows the tasks it asked for (WF-ARC-0090).

Each reads the tasks of its caller alone and asks for no permission: a task another account asked
for, or that the platform scheduled, does not exist for the caller.
"""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, BackgroundTaskStatus, PaginationMeta
from waterfall.api.queries import listed
from waterfall.platform.errors import NotFoundError
from waterfall.platform.tasks import BackgroundTask, TaskFilters, list_tasks, read_task

router = APIRouter(tags=["tasks"])

NOT_FOUND = "NOT_FOUND"


def task_ref(row: BackgroundTask) -> BackgroundTaskRef:
    """Describe a task as the contract does: no result to download yet (exports, EP-07)."""
    return BackgroundTaskRef.model_validate(
        {
            "task_id": row.id,
            "kind": row.kind,
            "status": row.status,
            "progress": row.progress,
            "submitted_at": row.submitted_at,
            "finished_at": row.finished_at,
            "problem": row.problem,
            "result_url": None,
        }
    )


def task_filters(
    status: Annotated[str | None, Query()] = None, finished_since: datetime | None = None
) -> TaskFilters:
    """Read the states kept, separated by commas, and since when the finished tasks are kept."""
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
