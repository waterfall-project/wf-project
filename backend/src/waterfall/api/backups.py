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

from datetime import UTC
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query
from pydantic import AwareDatetime, BaseModel, Field
from sqlalchemy import func, select

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.base import Text
from waterfall.api.contract.models import (
    BackgroundTaskRef,
    Backup,
    BackupOrigin,
    BackupRetain,
    BackupVerification,
    PaginationMeta,
    SortOrder,
)
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.queries import Offset, read_list, refuse_query
from waterfall.api.streams import ObjectResponse
from waterfall.api.tasks import task_ref
from waterfall.core.access_roles.interface import Actor
from waterfall.core.backups.interface import (
    BackupColumn,
    BackupFilters,
    BackupSort,
    BackupView,
    Platform,
    download_lacks,
    list_backups,
    lock_backup_deposit,
    mark_backup,
    marking_lacks,
    platform_of,
    read_backup,
    refuse_if_lacking,
    restoration_lacks,
)
from waterfall.platform.errors import (
    NOT_FOUND,
    FieldError,
    NotFoundError,
)
from waterfall.platform.locks import RESTORE_LOCK
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.tasks import BackgroundTask, submit

router = APIRouter(tags=["platform"])

CONSULTATION = "backups.read"
CHANGE = "backups.write"
READ = [Depends(Requires(CONSULTATION))]
CREATE = [Depends(Requires(CHANGE))]
COPY = [Depends(Requires(CONSULTATION, CHANGE))]
RESTORATION = "platform_restore"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
NUMBER_INVALID = "NUMBER_INVALID"
# The greatest integer PostgreSQL represents (``bigint``): a bound beyond it keeps what it would.
GREATEST_SIZE = 2**63 - 1


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
    listed: list[dict[str, Any]] = []
    if CHANGE in held:
        marking = "release" if view.is_retained else "retain"
        listed.append(_command(marking, marking_lacks(platform)))
    if {CONSULTATION, CHANGE} <= held:
        listed.append(_command("download", download_lacks(view.verification)))
    if RESTORATION in held:
        listed.append(_command("restore", restoration_lacks(view.verification, platform)))
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


class BackupsQuery(BaseModel):
    """The filters and the sort of the list, as the query names them."""

    since: AwareDatetime | None = Field(default=None, alias="from")
    to: AwareDatetime | None = None
    origins: Text | None = None
    verifications: Text | None = None
    is_retained: bool | None = None
    size_bytes_min: int | None = None
    size_bytes_max: int | None = None
    sort_by: BackupColumn | None = None
    sort_order: SortOrder | None = None


def _faults(query: BackupsQuery) -> list[FieldError]:
    """Name the bounds the query inverts or malforms, every one at once (422)."""
    faults: list[FieldError] = []
    if query.since is not None and query.to is not None and query.to < query.since:
        minimum = query.since.astimezone(UTC)
        faults.append(FieldError("/query/to", VALUE_OUT_OF_RANGE, {"minimum": minimum}))
    bounds = (("size_bytes_min", query.size_bytes_min), ("size_bytes_max", query.size_bytes_max))
    faults.extend(
        FieldError(f"/query/{name}", NUMBER_INVALID)
        for name, bound in bounds
        if bound is not None and bound < 0
    )
    low, high = query.size_bytes_min, query.size_bytes_max
    if not faults and low is not None and high is not None and high < low:
        faults.append(FieldError("/query/size_bytes_max", VALUE_OUT_OF_RANGE, {"minimum": low}))
    return faults


def backup_filters(query: Annotated[BackupsQuery, Query()]) -> tuple[BackupFilters, BackupSort]:
    """Read the filters and the sort of the list; a period or bounds inverted are refused (422).

    The lists are separated by commas. A period whose end precedes its start is refused at its end,
    the start named; a negative bound is a malformed number, and an upper bound under the lower one
    is out of its range, the lower one as its minimum, as the contract says. A bound beyond the
    integers of PostgreSQL, which no size reaches, is brought back to the greatest of them.
    """
    origins, origin_faults = read_list("origins", query.origins, BackupOrigin)
    verifications, verification_faults = read_list(
        "verifications", query.verifications, BackupVerification
    )
    refuse_query((*_faults(query), *origin_faults, *verification_faults))
    sizes = (query.size_bytes_min, query.size_bytes_max)
    low, high = (None if size is None else min(size, GREATEST_SIZE) for size in sizes)
    filters = BackupFilters(
        since=query.since,
        until=query.to,
        origins=None if origins is None else frozenset(each.value for each in origins),
        verifications=None
        if verifications is None
        else frozenset(each.value for each in verifications),
        is_retained=query.is_retained,
        size_min=low,
        size_max=high,
    )
    descending = None if query.sort_order is None else query.sort_order is SortOrder.desc
    return filters, BackupSort(query.sort_by, descending)


@router.get("/backups", operation_id="listBackups", dependencies=READ, response_model=None)
def get_backups(
    session: Transaction,
    actor: Acting,
    read: Annotated[tuple[BackupFilters, BackupSort], Depends(backup_filters)],
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Offset = 0,
) -> dict[str, Any]:
    """Give a page of the backups, filtered and sorted by the server, by date without a sort."""
    filters, sort = read
    views, total = list_backups(session, filters, sort, limit, offset)
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
    """Deposit a backup for the worker, asked for by the caller, and say where it stands.

    Refused (409) while a backup or a restoration is queued or running, the condition it lacks
    named (#1035). Two requests that ask at once wait for each other, and a restoration deposited
    meanwhile is waited for, or seen.
    """
    refuse_if_lacking(lock_backup_deposit(session))
    task_id = submit(session, services.queue, "backup", account.user_id)
    return task_ref(session.get_one(BackgroundTask, task_id))


@router.patch(
    "/backups/{backup_id}",
    operation_id="retainBackup",
    dependencies=CREATE,
    response_model=None,
)
def patch_backup(
    backup_id: UUID,
    body: Annotated[BackupRetain, Body()],
    session: Transaction,
    actor: Acting,
) -> dict[str, Any]:
    """Mark a backup to keep, or release it: the rotation spares a marked backup (WF-ADM-0170).

    An unknown backup is not found (404). Refused (409) while a restoration is queued or running,
    which replaces the database the mark would be written in: the restoration is looked for under
    the lock it is deposited under, shared, so that one deposited meanwhile waits for this writing,
    or this writing sees it. Without a counter, by decided exception: the mark sets the state
    intended (WF-IHM-0110).
    """
    session.execute(select(func.pg_advisory_xact_lock_shared(RESTORE_LOCK)))
    platform = platform_of(session)
    read_backup(session, backup_id)
    refuse_if_lacking(marking_lacks(platform))
    view = mark_backup(session, backup_id, is_retained=body.is_retained)
    return backup(view, actor, platform).model_dump(mode="json")


@router.get("/backups/{backup_id}", operation_id="getBackup", dependencies=READ)
def get_backup(backup_id: UUID, session: Transaction, actor: Acting) -> Backup:
    """Give a backup: its date, its size, the outcome of its verification (WF-ADM-0150)."""
    return backup(read_backup(session, backup_id), actor, platform_of(session))


@router.get("/backups/{backup_id}/content", operation_id="downloadBackup", dependencies=COPY)
def get_backup_content(backup_id: UUID, services: ServicesOf) -> ObjectResponse:
    """Stream the archive of a backup out of the platform (WF-ADM-0150).

    The backup is read in a transaction of its own, closed before the archive streams: no
    connection is held while the bucket is read. An archive the bucket no longer holds is a backup
    that cannot be copied, refused as one that does not exist (404); a backup whose verification
    has not passed is not copied (409, ``backup_verified``, #1035). The stream is closed when the
    response ends, a client that disconnects included, and a failure once it began is journaled
    (#897).
    """
    with services.database.transaction() as session:
        view = read_backup(session, backup_id)
    refuse_if_lacking(download_lacks(view.verification))
    try:
        stream = services.backups.stream(view.object_key)
    except MissingObjectError:
        raise NotFoundError(NOT_FOUND) from None
    name = f"waterfall-backup-{view.taken_at:%Y%m%dT%H%M%SZ}.tar"
    # The length the storage gives the object, which is what is sent; the row's, if it gives none.
    length = view.size_bytes if stream.length is None else stream.length
    headers = {
        "Content-Disposition": f'attachment; filename="{name}"',
        "Content-Length": str(length),
    }
    return ObjectResponse(stream, "application/octet-stream", headers)
