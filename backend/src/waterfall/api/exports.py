# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exports, and the file a background task produced (WF-INTF-0050, WF-PLA-0120).

``requestExport`` and ``getBackgroundTaskResult`` (US-1430/L2); the image of the tree
(US-1440/L2).

``requestExport`` deposits the task of an export (202) under the command ``export_*`` of the
revision it names. The file the worker wrote is read by the account that asked for it alone, through
the task: streamed as an attachment and, once its last byte is sent, deleted from the storage with
the result marked consumed; a download that stops before leaves both (WF-DAT-0120).
"""

import unicodedata
from collections.abc import Iterator
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, ExportRequest
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.tasks import task_ref
from waterfall.core.exchanges.interface import (
    ExportAsked,
    consumed,
    request_export,
    result_of,
)
from waterfall.core.projects.interface import Viewer
from waterfall.platform.errors import NotFoundError
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.tasks import BackgroundTask

# Each route its tag, as the contract has them: ``exchanges`` for ``requestExport``, ``tasks`` for
# ``getBackgroundTaskResult``.
router = APIRouter()

NOT_FOUND = "NOT_FOUND"
# What a quoted file name may not carry (RFC 6266): the quote and the backslash.
UNQUOTED = {ord('"'): "'", ord("\\"): "_"}


def disposition(filename: str) -> str:
    """Give the ``Content-Disposition`` of a file downloaded as an attachment (RFC 6266, 8187).

    A name that is not in ASCII is also written in ``filename*``, percent-encoded in UTF-8, and
    ``filename`` then carries its ASCII equivalent: the letters stripped of their accents, the
    others dropped.
    """
    stripped = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode()
    plain = "".join(each if each.isprintable() else "_" for each in stripped).translate(UNQUOTED)
    if not plain or plain.startswith("."):
        # Nothing of the stem is left in ASCII: a hidden file, or no name; keep the extension.
        suffix = PurePosixPath(filename).suffix.encode("ascii", "ignore").decode()
        plain = f"export{suffix}"
    quoted = f'attachment; filename="{plain}"'
    if filename.isascii():
        return quoted
    return f"{quoted}; filename*=UTF-8''{quote(filename, safe='')}"


@router.post(
    "/projects/{project_id}/exports",
    operation_id="requestExport",
    tags=["exchanges"],
    dependencies=[Depends(RequiresProject())],
    status_code=202,
    response_model_exclude_unset=True,
)
def post_export(
    project_id: UUID,
    body: ExportRequest,
    actor: Acting,
    session: Transaction,
    services: ServicesOf,
) -> BackgroundTaskRef:
    """Deposit the export of a revision for the worker, asked for by the caller; say where it is.

    The route asks for the quality of consultation on the project alone: the permission of the kind
    is judged by the command ``export_*`` of the revision, which a refusal names (WF-CYC-0110).

    The task is written in the transaction of the request, and deposited in the queue once that is
    committed.
    """
    asked = ExportAsked(
        kind=body.kind.value,
        revision_id=body.revision_id.root,
        structure_id=None if body.structure_id is None else body.structure_id.root,
        depth=None if body.depth is None else body.depth.root,
        review_date=None if body.review_date is None else body.review_date.root,
    )
    viewer = Viewer(actor.user_id, actor.permissions)
    task_id = request_export(session, services.queue, project_id, asked, viewer)
    return task_ref(session.get_one(BackgroundTask, task_id))


@router.get(
    "/tasks/{task_id}/result",
    operation_id="getBackgroundTaskResult",
    tags=["tasks"],
    response_class=StreamingResponse,
    response_model=None,
)
def get_background_task_result(
    task_id: UUID, account: Caller, services: ServicesOf
) -> StreamingResponse:
    """Stream the file an export produced, to the account that asked for it (WF-DAT-0120).

    The task is read in a transaction of its own, closed before the file streams: no connection is
    held while the storage is read. The file is deleted, and the result marked consumed, when the
    last byte has been handed over; a stream that stops before leaves both, and is resumed.
    """
    with services.database.transaction() as session:
        found = result_of(session, task_id, account.user_id)
    try:
        chunks = services.backups.stream(found.object_key)
        length = services.backups.size(found.object_key)
    except MissingObjectError:
        # The file is gone: the result is no more, and the task no longer gives its link.
        with services.database.transaction() as session:
            consumed(session, task_id)
        raise NotFoundError(NOT_FOUND) from None

    def delivered() -> Iterator[bytes]:
        yield from chunks
        services.backups.delete(found.object_key)
        with services.database.transaction() as session:
            consumed(session, task_id)

    headers = {"Content-Disposition": disposition(found.filename)}
    if length is not None:
        headers["Content-Length"] = str(length)
    return StreamingResponse(delivered(), media_type=found.media_type, headers=headers)
