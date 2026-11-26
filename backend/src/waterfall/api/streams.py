# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The response that streams an object of the storage, and closes what it reads (#897).

A reader that leaves — the client that disconnects, a stream that fails — leaves the body of the
object open, and with it a connection to the storage, until the garbage collector comes: nothing in
the framework closes the iterator it was given. This response closes the stream when its work ends,
by whichever way, and journals the stream that failed once the answer had begun, which no status
can say any more: the connection is cut short, and the client sees a body shorter than its length.

Only a ``ServiceError`` is journaled here, as ``download.interrupted``: any other exception met
while the stream is read — a fault of the framework, of the code — goes up unchanged, the stream
closed, to the server, which journals it as it does any unhandled fault. The closing is shielded
from the cancellation of the task (a server that stops, a timeout): under a cancel scope every
``await`` raises again, and a closing awaited unshielded would never run.
"""

from typing import TYPE_CHECKING

import anyio
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from waterfall.platform.errors import ServiceError
from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from starlette.types import Receive, Scope, Send

    from waterfall.platform.storage import ObjectStream

logger = get_logger(__name__)


class ObjectResponse(StreamingResponse):
    """Stream an object of the storage as it is read; close it when the response ends."""

    def __init__(
        self,
        stream: ObjectStream,
        media_type: str | None = None,
        headers: Mapping[str, str] | None = None,
        content: Iterable[bytes] | None = None,
    ) -> None:
        """Serve ``stream``, or ``content`` read from it, which the response closes either way."""
        body = stream if content is None else content
        super().__init__(body, media_type=media_type, headers=headers)
        self.stream = stream

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Send the object; close its stream however the response ends."""
        try:
            await super().__call__(scope, receive, send)
        except ServiceError as error:
            # The answer began: no envelope can be sent, the connection ends with the stream.
            logger.exception("download.interrupted", key=self.stream.key, code=error.code)
            raise
        finally:
            with anyio.CancelScope(shield=True):
                await run_in_threadpool(self.stream.close)
