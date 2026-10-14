# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The restoration of the platform (FBS-1.4, WF-ADM-0160): asked for here, done by its service.

The request names the backup and the date its confirmation states; the service of the restoration
replaces both databases whole — nothing partial is offered — under a maintenance that the probe of
liveness says (#604). The task is deposited, once its transaction is committed, in the stream of
the restorations, which that service alone reads, never in the worker's (#953). It carries the key
of the archive, so that it never reads, to find it, the database it replaces. One restoration at a
time: a second one, while the first is queued or running, is refused.

The route asks for the permission to restore alone, as the contract says: a backup copied out of the
platform names none of the list. The backup of the list it names does not exist, though, for a
caller who may not read the backups (WF-ADM-0110): 404, as an unknown one, before it is read.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy import func, select

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, RestoreRequest
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.tasks import task_ref
from waterfall.core.access_roles.interface import require
from waterfall.core.backups.interface import NOT_FOUND, read_backup
from waterfall.platform.errors import BadRequestError, ConflictError, NotFoundError
from waterfall.platform.tasks import BackgroundTask, pending_task, submit

router = APIRouter(tags=["platform"])

CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
RESTORE = [Depends(Requires("platform_restore"))]
# The permission without which a backup of the list does not exist for the caller (WF-ADM-0110).
CONSULTATION = "backups.read"
# The key of the advisory lock under which a request looks for a pending restoration, then deposits.
RESTORE_LOCK = 3_700_160


@router.post(
    "/restores",
    operation_id="startRestore",
    dependencies=RESTORE,
    status_code=202,
    response_model_exclude_unset=True,
)
def post_restore(
    request: Annotated[RestoreRequest, Body()],
    account: Caller,
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> BackgroundTaskRef:
    """Deposit the restoration of a backup whose date the confirmation states, for its service.

    A backup copied out of the platform is deposited by chunks first (#350), which this lot does
    not serve yet: its identifier names no deposit (404). A backup of the list, for a caller who
    may not read the backups, is not found either (404), before it is read.
    """
    asked = request.root
    if asked.backup_id is None:
        raise NotFoundError(NOT_FOUND)
    require(actor, CONSULTATION)
    backup = read_backup(session, asked.backup_id.root)
    if backup.taken_at != asked.acknowledged_backup_taken_at.root:
        raise BadRequestError(CONFIRMATION_REQUIRED)
    session.execute(select(func.pg_advisory_xact_lock(RESTORE_LOCK)))
    if pending_task(session, "restore") is not None:
        raise ConflictError(STATE_FORBIDS_OPERATION)
    payload = {"backup_id": str(backup.backup_id), "object_key": backup.object_key}
    restores = services.queue.restores()
    task_id = submit(session, restores, "restore", account.user_id, payload)
    return task_ref(session.get_one(BackgroundTask, task_id))
