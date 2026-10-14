# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The deposit by parts of a backup copied out of a platform, to restore here (#350, WF-ADM-0160).

A backup of several gibibytes passes no request the front carries whole: a deposit opens, says in
how many parts the file is cut, receives each part — written to the object storage before the
answer —, and is completed, the parts assembled there into one file, whose deposit
``startRestore`` then names. Under the permission to restore the platform, as ``startRestore``.
The object storage is asked out of any transaction: a deposit is recorded once the storage has
opened it, and completed once the storage has assembled it.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Request

from waterfall.api.authentication import Caller, ServicesOf
from waterfall.api.contract.models import ChunkedUpload, ChunkedUploadOpen, FileUpload
from waterfall.api.evaluation import Requires
from waterfall.core.backups.interface import MANIFEST_HEAD, archive_taken_at
from waterfall.platform.database import utc_now
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id
from waterfall.platform.installation import read_settings
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.uploads import (
    EXTERNAL_BACKUP,
    LARGEST_PART,
    Cut,
    Opened,
    complete_upload,
    cut,
    object_key_of,
    open_upload,
    record_upload,
)
from waterfall.platform.uploads import (
    FileUpload as Deposit,
)

router = APIRouter(tags=["exchanges"])

RESTORE = [Depends(Requires("platform_restore"))]
FILE_TOO_LARGE = "FILE_TOO_LARGE"
NOT_FOUND = "NOT_FOUND"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"


def chunked(row: Deposit, received: list[int]) -> ChunkedUpload:
    """Describe a deposit open as the contract does, with the parts it has received."""
    return ChunkedUpload.model_validate(
        {
            "chunked_upload_id": row.id,
            "filename": row.filename,
            "size_bytes": row.size_bytes,
            "part_size_bytes": row.part_size_bytes,
            "part_count": row.part_count,
            "received_parts": received,
            "expires_at": row.expires_at,
        }
    )


@router.post(
    "/chunked-uploads", operation_id="openChunkedUpload", dependencies=RESTORE, status_code=201
)
def post_chunked_upload(
    body: Annotated[ChunkedUploadOpen, Body()], account: Caller, services: ServicesOf
) -> ChunkedUpload:
    """Open the deposit of a backup: refused beyond the bound of the installation (413).

    A size that 10 000 parts of 10 MiB cannot hold is refused likewise, before any part is sent.
    """
    with services.database.transaction() as session:
        bound = read_settings(session).external_backup_max_bytes
    parts = cut(body.size_bytes)
    if body.size_bytes > bound or parts is None:
        raise PayloadTooLargeError(FILE_TOO_LARGE)
    upload_id = new_id()
    key = object_key_of(upload_id)
    deposit = services.backups.open_parts(key)
    opened = Opened(
        EXTERNAL_BACKUP, body.filename, body.size_bytes, parts, key, deposit, account.user_id
    )
    with services.database.transaction() as session:
        row = record_upload(session, upload_id, opened, utc_now())
        return chunked(row, [])


async def received_part(request: Request) -> bytes:
    """Read the part a request carries, 10 MiB at most: a part is never larger.

    One that says it is larger, or whose bytes pass it, is refused as one of the wrong size (422),
    without being read further.
    """
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > LARGEST_PART:
        raise wrong_size(None)
    part = bytearray()
    async for chunk in request.stream():
        part += chunk
        if len(part) > LARGEST_PART:
            raise wrong_size(None)
    return bytes(part)


def wrong_size(expected: int | None) -> UnprocessableError:
    """Refuse a part of the wrong size, naming the size expected when it is known (422)."""
    params = {} if expected is None else {"minimum": expected, "maximum": expected}
    return UnprocessableError(
        VALIDATION_FAILED, fields=(FieldError("/body", VALUE_OUT_OF_RANGE, params),)
    )


@router.put(
    "/chunked-uploads/{chunked_upload_id}/parts/{part_number}",
    operation_id="uploadChunk",
    dependencies=RESTORE,
)
def put_chunk(
    chunked_upload_id: UUID,
    part_number: Annotated[int, Path(ge=1)],
    part: Annotated[bytes, Depends(received_part)],
    services: ServicesOf,
) -> ChunkedUpload:
    """Receive a part, written to the storage before the answer; one received again replaces it.

    A number the deposit does not count, or a deposit completed, expired or unknown, is not found
    (404); a part of another size than the one expected is refused (422), and nothing is received.
    """
    with services.database.transaction() as session:
        row = open_upload(session, chunked_upload_id, utc_now())
        if row is None or part_number > row.part_count or row.deposit is None:
            raise NotFoundError(NOT_FOUND)
        session.expunge(row)
    expected = Cut(row.part_size_bytes, row.part_count).expected(part_number, row.size_bytes)
    if len(part) != expected:
        raise wrong_size(expected)
    try:
        services.backups.put_part(row.object_key, row.deposit, part_number, part)
        received = services.backups.parts(row.object_key, row.deposit)
    except MissingObjectError:
        raise NotFoundError(NOT_FOUND) from None
    return chunked(row, sorted(received))


@router.post(
    "/chunked-uploads/{chunked_upload_id}/completion",
    operation_id="completeChunkedUpload",
    dependencies=RESTORE,
    status_code=201,
)
def post_completion(chunked_upload_id: UUID, services: ServicesOf) -> FileUpload:
    """Assemble the parts into one file, and give the deposit a restoration names.

    Refused while a part lacks (409, ``params.missing_parts``), nothing assembled; a deposit
    completed, expired or unknown is not found (404). The date of the backup is read from the head
    of the file assembled, and given, so that the confirmation of the restoration names it (#1006).
    """
    with services.database.transaction() as session:
        row = open_upload(session, chunked_upload_id, utc_now())
        if row is None or row.deposit is None:
            raise NotFoundError(NOT_FOUND)
        session.expunge(row)
    try:
        received = services.backups.parts(row.object_key, row.deposit)
        missing = [number for number in range(1, row.part_count + 1) if number not in received]
        if missing:
            raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_parts": missing})
        services.backups.assemble(row.object_key, row.deposit, received)
        taken_at = archive_taken_at(services.backups.head(row.object_key, MANIFEST_HEAD))
    except MissingObjectError:
        # Completed meanwhile by another request, which the storage has assembled already.
        raise NotFoundError(NOT_FOUND) from None
    with services.database.transaction() as session:
        completed = complete_upload(session, chunked_upload_id, utc_now(), taken_at)
        if completed is None:
            raise NotFoundError(NOT_FOUND)
        return FileUpload.model_validate(
            {
                "upload_id": completed.id,
                "purpose": completed.purpose,
                "filename": completed.filename,
                "size_bytes": completed.size_bytes,
                "uploaded_at": completed.completed_at,
                "expires_at": completed.expires_at,
                "backup_taken_at": completed.backup_taken_at,
            }
        )
