# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The correlation of a request: its identifier, bound to its logs, handed back in a header."""

import time

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from waterfall.platform.correlation import HEADER, correlation_id_from
from waterfall.platform.logs import ANONYMOUS, get_logger, logging_context

SCOPE_KEY = "correlation_id"

logger = get_logger(__name__)


class CorrelationMiddleware:
    """Take the identifier of the request, or make one; bind it; give it back; log the request.

    The identifier is also kept in the scope: the handler of an unexpected exception runs
    outside this middleware, and reads it there.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve a request of the application inside its correlation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        correlation_id = correlation_id_from(Headers(scope=scope).get(HEADER))
        scope[SCOPE_KEY] = correlation_id
        status = 500
        started = time.perf_counter()

        async def send_with_header(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)[HEADER] = correlation_id
            await send(message)

        with logging_context(correlation_id=correlation_id, actor=ANONYMOUS):
            try:
                await self.app(scope, receive, send_with_header)
            finally:
                logger.info(
                    "request.completed",
                    method=scope["method"],
                    path=scope["path"],
                    status=status,
                    duration_ms=round((time.perf_counter() - started) * 1000, 1),
                )
