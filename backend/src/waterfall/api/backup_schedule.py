# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule of the backups (FBS-1.4, WF-ADM-0170): ``getBackupSchedule``, ``setBackupSchedule``.

Read under the permission to read the backups, written under the one to change them
(WF-ADM-0100). A new installation reads the shipped schedule, which the migrations write: the
reading never misses it. A writing is judged whole, every field in default named at once (422);
then refused while a restoration is queued or running, which keeps the schedule and writes it back
after the replacement of the databases, so that a writing made meanwhile would be lost (409,
``no_restore_running``, WF-ADM-0160, #1743); then written under the counter the writer read (412).
The shape of the body is the validation's; its values, the rule's.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy import func, select

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.base import ContractModel
from waterfall.api.contract.models import BackupSchedule, Frequency, LockVersion
from waterfall.api.evaluation import Requires
from waterfall.core.backups.interface import (
    BackupScheduleView,
    ExternalCopy,
    ScheduleWriting,
    judged_schedule,
    read_backup_schedule,
    write_backup_schedule,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import (
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    UnprocessableError,
)
from waterfall.platform.locks import RESTORE_LOCK
from waterfall.platform.tasks import pending_task

router = APIRouter(tags=["platform"])

READ = [Depends(Requires("backups.read"))]
CHANGE = [Depends(Requires("backups.write"))]
NO_RESTORE_RUNNING = "no_restore_running"


class ExternalCopyWrite(ContractModel):
    """``BackupExternalCopy`` as a writing sends it: its form and its bounds are the rule's."""

    is_enabled: bool
    location: str
    path: str
    retained_count: int


class BackupScheduleWrite(ContractModel):
    """``BackupSchedule`` as a writing sends it: the time, the day and the retentions unjudged.

    The rule judges them together (``judged_schedule``), so that one answer names every field in
    default. ``external_copy`` absent removes the copy set; sent null, it is refused, as the
    contract types it not nullable.
    """

    is_enabled: bool
    frequency: Frequency
    at_time: str
    weekday: int | None
    retained_count: int
    external_copy: ExternalCopyWrite | None = None
    lock_version: LockVersion


def schedule_writing(body: BackupScheduleWrite) -> ScheduleWriting:
    """Read the schedule a body sends; refuse a copy sent null (422)."""
    if "external_copy" in body.model_fields_set and body.external_copy is None:
        raise UnprocessableError(
            VALIDATION_FAILED, fields=(FieldError("/external_copy", VALIDATION_FAILED),)
        )
    sent = body.external_copy
    copy = None
    if sent is not None:
        copy = ExternalCopy(sent.is_enabled, sent.location, sent.path, sent.retained_count)
    return ScheduleWriting(
        body.is_enabled,
        body.frequency.value,
        body.at_time,
        body.weekday,
        body.retained_count,
        copy,
    )


def backup_schedule(view: BackupScheduleView) -> BackupSchedule:
    """Describe the schedule as the contract does: the time ``HH:MM``, no copy left unset."""
    schedule = view.schedule
    described: dict[str, object] = {
        "is_enabled": schedule.is_enabled,
        "frequency": schedule.frequency,
        "at_time": f"{schedule.at_time:%H:%M}",
        "weekday": schedule.weekday,
        "retained_count": schedule.retained_count,
        "lock_version": view.lock_version,
    }
    copy = schedule.external_copy
    if copy is not None:
        described["external_copy"] = {
            "is_enabled": copy.is_enabled,
            "location": copy.location,
            "path": copy.path,
            "retained_count": copy.retained_count,
        }
    return BackupSchedule.model_validate(described)


@router.get(
    "/backup-schedule",
    operation_id="getBackupSchedule",
    dependencies=READ,
    response_model_exclude_unset=True,
)
def get_backup_schedule(session: Transaction) -> BackupSchedule:
    """Give the schedule of the backups, the shipped one until an administrator sets another."""
    return backup_schedule(read_backup_schedule(session))


@router.put(
    "/backup-schedule",
    operation_id="setBackupSchedule",
    dependencies=CHANGE,
    response_model_exclude_unset=True,
)
def put_backup_schedule(
    body: Annotated[BackupScheduleWrite, Body()],
    account: Caller,
    session: Transaction,
    services: ServicesOf,
) -> BackupSchedule:
    """Write the schedule whole: judged (422), refused during a restoration (409), counted (412).

    The copy names a location the installation declares (``listExternalBackupLocations``): one it
    does not declare is unknown, and an installation that declares none offers no copy. The
    restoration is looked for under the lock ``startRestore`` deposits one under, shared: a
    restoration deposited meanwhile waits for this writing, or this writing sees it.
    """
    declared = services.external_locations.names()
    schedule = judged_schedule(schedule_writing(body), declared)
    session.execute(select(func.pg_advisory_xact_lock_shared(RESTORE_LOCK)))
    if pending_task(session, "restore") is not None:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": NO_RESTORE_RUNNING})
    act = Act(account.user_id, utc_now())
    view = write_backup_schedule(session, schedule, body.lock_version.root, act)
    return backup_schedule(view)
