# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The restoration of the platform (FBS-1.4, WF-ADM-0160): asked for here, done by its service.

The request names the backup and the date its confirmation states; the service of the restoration
replaces both databases whole — nothing partial is offered — under a maintenance that the probe of
liveness says (#604). The task is deposited, once its transaction is committed, in the stream of
the restorations, which that service alone reads, never in the worker's (#953). It carries the key
of the archive, so that it never reads, to find it, the database it replaces. One restoration at a
time: a second one, while the first is queued or running, is refused. A backup copied out of a
platform is restored from its deposit (#350), whose date is the one its manifest says.

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
from waterfall.platform.database import utc_now
from waterfall.platform.errors import (
    BadRequestError,
    ConflictError,
    FieldError,
    NotFoundError,
    UnprocessableError,
)
from waterfall.platform.tasks import BackgroundTask, pending_task, submit
from waterfall.platform.uploads import EXTERNAL_BACKUP, completed_upload

router = APIRouter(tags=["platform"])

CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
VALIDATION_FAILED = "VALIDATION_FAILED"
UPLOAD_PURPOSE_MISMATCH = "UPLOAD_PURPOSE_MISMATCH"
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

    A backup of the list, or one copied out of a platform and deposited here (#350). A backup of
    the list, for a caller who may not read the backups, is not found (404), before it is read; a
    deposit unknown, not completed or expired is not found either, one made for an import is
    refused (422).
    The date of a deposit is the one its manifest says, read at its completion, which refuses a
    deposit whose manifest says none; one without a date is one no confirmation names (400). The
    task carries the date confirmed, which the manifest read whole must say, before the
    maintenance. A confirmation absent or false is refused alike (400), before anything is read:
    the schema leaves it to this guard (US-0702/L3).
    """
    asked = request.root
    if not asked.confirmed:
        raise BadRequestError(CONFIRMATION_REQUIRED)
    if asked.backup_id is not None:
        require(actor, CONSULTATION)
        backup = read_backup(session, asked.backup_id.root)
        taken_at = backup.taken_at
        payload = {"backup_id": str(backup.backup_id), "object_key": backup.object_key}
    else:
        upload_id = asked.external_backup_upload_id.root
        upload = completed_upload(session, upload_id, utc_now())
        if upload is None:
            raise NotFoundError(NOT_FOUND)
        if upload.purpose != EXTERNAL_BACKUP:
            mismatch = FieldError("/external_backup_upload_id", UPLOAD_PURPOSE_MISMATCH)
            raise UnprocessableError(VALIDATION_FAILED, fields=(mismatch,))
        taken_at = upload.backup_taken_at
        payload = {
            "upload_id": str(upload.id),
            "filename": upload.filename,
            "object_key": upload.object_key,
            "backup_taken_at": asked.acknowledged_backup_taken_at.root.isoformat(),
        }
    if taken_at is None or taken_at != asked.acknowledged_backup_taken_at.root:
        raise BadRequestError(CONFIRMATION_REQUIRED)
    session.execute(select(func.pg_advisory_xact_lock(RESTORE_LOCK)))
    if pending_task(session, "restore") is not None:
        raise ConflictError(STATE_FORBIDS_OPERATION)
    restores = services.queue.restores()
    task_id = submit(session, restores, "restore", account.user_id, payload)
    return task_ref(session.get_one(BackgroundTask, task_id))
