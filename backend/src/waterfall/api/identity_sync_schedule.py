# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedule of the readings of the accounts: ``getIdentitySyncSchedule`` and its writing.

``setIdentitySyncSchedule`` writes it (WF-ADM-0070).

Read under the permission to read the accounts, written under the one to change them, the one that
asks for a reading on demand (WF-ADM-0100). A new installation reads the shipped schedule, which
the migrations write: the reading never misses it. A writing is judged whole, every field in
default named at once (422); then written under the counter the writer read (412). The setting
applies from the next scheduled reading; one in progress is not interrupted, and a restoration does
not keep the schedule (#4126). The shape of the body is the validation's; its values, the rule's.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from waterfall.api.authentication import Caller, Transaction
from waterfall.api.contract.base import ContractModel
from waterfall.api.contract.models import Frequency, IdentitySyncSchedule, LockVersion
from waterfall.api.evaluation import Requires
from waterfall.core.users.interface import (
    SyncScheduleView,
    SyncScheduleWriting,
    judged_sync_schedule,
    read_sync_schedule,
    write_sync_schedule,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

router = APIRouter(tags=["users"])

READ = [Depends(Requires("users.read"))]
CHANGE = [Depends(Requires("users.write"))]


class IdentitySyncScheduleWrite(ContractModel):
    """``IdentitySyncSchedule`` as a writing sends it: the time and the day unjudged.

    The rule judges them together (``judged_sync_schedule``), so that one answer names every field
    in default.
    """

    is_enabled: bool
    frequency: Frequency
    at_time: str
    weekday: int | None
    lock_version: LockVersion


def identity_sync_schedule(view: SyncScheduleView) -> IdentitySyncSchedule:
    """Describe the schedule as the contract does: the time ``HH:MM``."""
    schedule = view.schedule
    return IdentitySyncSchedule.model_validate(
        {
            "is_enabled": schedule.is_enabled,
            "frequency": schedule.frequency,
            "at_time": f"{schedule.at_time:%H:%M}",
            "weekday": schedule.weekday,
            "lock_version": view.lock_version,
        }
    )


@router.get(
    "/identity-sync-schedule",
    operation_id="getIdentitySyncSchedule",
    dependencies=READ,
    response_model_exclude_unset=True,
)
def get_identity_sync_schedule(session: Transaction) -> IdentitySyncSchedule:
    """Give the schedule of the readings, the shipped one until an administrator sets another."""
    return identity_sync_schedule(read_sync_schedule(session))


@router.put(
    "/identity-sync-schedule",
    operation_id="setIdentitySyncSchedule",
    dependencies=CHANGE,
    response_model_exclude_unset=True,
)
def put_identity_sync_schedule(
    body: Annotated[IdentitySyncScheduleWrite, Body()], account: Caller, session: Transaction
) -> IdentitySyncSchedule:
    """Write the schedule whole: judged (422), then counted (412)."""
    schedule = judged_sync_schedule(
        SyncScheduleWriting(body.is_enabled, body.frequency.value, body.at_time, body.weekday)
    )
    act = Act(account.user_id, utc_now())
    view = write_sync_schedule(session, schedule, body.lock_version.root, act)
    return identity_sync_schedule(view)
