# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exports, and the file a background task produced (WF-INTF-0050, WF-PLA-0120).

``requestExport`` and ``getBackgroundTaskResult`` (US-1430/L2); the image of the tree
(US-1440/L2).

``requestExport`` deposits the task of an export (202) under the command ``export_*`` of the
revision it names. The file the worker wrote is read by the account that asked for it alone, through
the task: streamed as an attachment and, once its last byte is sent, deleted from the storage with
the result marked consumed; a download that stops before leaves both (WF-DAT-0120). "Its last
byte" is the end of the answer, accepted by the server, not the last piece of the file: a
connection that breaks while the answer closes leaves the file to be downloaded again (#3977).

What the API guarantees is the answer it gives, closed to its end towards its own peer. When the
front relays the download (``frontend/src/api/relay.ts``), that peer is the relay: the API does not
see whether the relay then hands the file to the browser, and a break between the two is not
covered (#3977, the question is put to the author).
"""

import unicodedata
from collections.abc import Callable, Iterator, Mapping
from itertools import chain
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from starlette.types import Message, Receive, Scope, Send

from waterfall.api.authentication import Caller, ServicesOf, Transaction
from waterfall.api.contract.models import BackgroundTaskRef, ExportRequest
from waterfall.api.evaluation import Acting, RequiresProject
from waterfall.api.streams import ObjectResponse
from waterfall.api.tasks import task_ref
from waterfall.core.exchanges.interface import (
    ExportAsked,
    consumed,
    request_export,
    result_of,
)
from waterfall.core.projects.interface import Viewer
from waterfall.platform.errors import NOT_FOUND, NotFoundError
from waterfall.platform.storage import MissingObjectError, ObjectStream
from waterfall.platform.tasks import BackgroundTask

# Each route its tag, as the contract has them: ``exchanges`` for ``requestExport``, ``tasks`` for
# ``getBackgroundTaskResult``.
router = APIRouter()


class DeliveredResponse(ObjectResponse):
    """A streamed answer that runs ``delivered`` only once its body was handed over whole (#3977).

    Starlette runs the background task of a response after the stream whatever became of the
    connection: with the ASGI ``spec_version`` below 2.4, a ``http.disconnect`` cancels the stream
    and the task still runs. So the end is watched here, whatever the version: every byte of the
    body was handed to the server without a send failing or being cancelled, and no
    ``http.disconnect`` came before the last of them. The client of a relay leaves as soon as it has
    the last byte, before the closing message goes out (#4985): a disconnect read after the last
    piece was sent changes nothing. The body is whole when the stream came to its end or, with the
    ``length`` known, when that many bytes were sent: the end of the stream is awaited in a thread,
    and a disconnect can cancel that wait before the thread ran. It is an ``ObjectResponse``: the
    ``chunks`` are closed on every path — whole, cut, or failed — and a failure once the answer
    began is journaled (#4680).
    """

    def __init__(
        self,
        chunks: ObjectStream,
        delivered: Callable[[], None],
        length: int | None = None,
        *,
        media_type: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.exhausted = False
        self.length = length
        super().__init__(chunks, media_type, headers, content=self.watched(chunks))
        self.delivered = delivered

    def watched(self, chunks: ObjectStream) -> Iterator[bytes]:
        """Pass the pieces on, and note that the stream came to its end (it runs in a thread)."""
        # Through a ``chain``: ``yield from chunks`` would close them with this generator, and the
        # response closes it once, on every path.
        yield from chain(chunks)
        self.exhausted = True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Stream the answer; run ``delivered`` if its body went whole to the server, only then."""
        sent = 0  # the pieces of the body handed to the server
        size = 0  # their bytes
        left_after: int | None = None  # the pieces sent when the client left, if it did
        broken = False  # a send failed or was cancelled: the bytes did not leave

        async def watched_receive() -> Message:
            nonlocal left_after
            message = await receive()
            if message["type"] == "http.disconnect" and left_after is None:
                left_after = sent
            return message

        async def watched_send(message: Message) -> None:
            nonlocal sent, size, broken
            try:
                await send(message)
            except BaseException:
                broken = True
                raise
            if message["type"] == "http.response.body" and message.get("more_body", False):
                sent += 1
                size += len(message.get("body", b""))

        await super().__call__(scope, watched_receive, watched_send)
        # A client gone before the last piece was sent got no whole file, though the server may take
        # the pieces still (uvicorn drops them): only a disconnect after all of them is harmless.
        whole = self.exhausted or (self.length is not None and size >= self.length)
        if whole and not broken and (left_after is None or left_after >= sent):
            await run_in_threadpool(self.delivered)


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
        # ``plain`` is already sanitized, so the extension taken from it is too.
        extension = plain.rpartition(".")[2]
        plain = f"export.{extension}" if extension else "export"
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
) -> DeliveredResponse:
    """Stream the file an export produced, to the account that asked for it (WF-DAT-0120).

    The task is read in a transaction of its own, closed before the file streams: no connection is
    held while the storage is read. The file is deleted, and the result marked consumed, once the
    answer has been sent to its end, the closing of the stream included: it runs after the response,
    which the server never reaches when the connection breaks before. A stream that stops before,
    or while it closes, leaves both, and is resumed (WF-DAT-0120, #3977). The API sees its own
    peer only: behind the relay of the front, the hand-over to the browser is not observed by it.
    """
    with services.database.transaction() as session:
        found = result_of(session, task_id, account.user_id)
    # The size is read before the stream is opened: a file that is gone opens nothing, and a body
    # opened is never left behind by a failure that follows (#4680).
    length = services.backups.size(found.object_key)
    chunks: ObjectStream | None = None
    if length is not None:
        try:
            chunks = services.backups.stream(found.object_key)
        except MissingObjectError:
            chunks = None
    if chunks is None:
        # The file is gone: the result is no more, and the task no longer gives its link.
        with services.database.transaction() as session:
            consumed(session, task_id)
        raise NotFoundError(NOT_FOUND) from None

    def delivered() -> None:
        services.backups.remove(found.object_key)
        with services.database.transaction() as session:
            consumed(session, task_id)

    headers = {"Content-Disposition": disposition(found.filename)}
    headers["Content-Length"] = str(length)
    return DeliveredResponse(
        chunks, delivered, length, media_type=found.media_type, headers=headers
    )
