# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The drain of an instance of the API being stopped (US-2850, WF-EXP-0030).

Once its pod is ending, the chart writes the file ``WATERFALL_DRAIN_FILE`` names, then waits a
moment before the server is stopped. From then on, each answer closes its connection
(``Connection: close``): a client that keeps its connections to this instance — the server of the
front, whose connections the cluster keeps on the pod they were opened to — drops each once
answered, and opens the next to an instance that stays. A connection that serves nothing in the
meantime is closed idle: the server closes a connection idle for ``IDLE_SECONDS`` (uvicorn's
``timeout_keep_alive``, set by ``waterfall.api.main``; its HTTP is h11's, which sends no
``Keep-Alive`` header), fewer than the ten seconds of the wait (``waterfall.drainSeconds`` in the
chart) — and the server of the front, Node's ``fetch`` (undici 8 in Node 26), closes its own sooner,
idle for four seconds, its ``keepAliveTimeout`` by default when the server gives no ``Keep-Alive``.
By the stop, none is left open.

Without it, the server closed at its stop every connection idle at that moment: a request sent on
one just then was lost, and the front, which sends a read once more, sent it again on another
connection to the same instance, closed at the same moment — one request in a few thousand failed
during an upgrade (#5020).
"""

from typing import TYPE_CHECKING

from starlette.datastructures import MutableHeaders

if TYPE_CHECKING:
    from pathlib import Path

    from starlette.types import ASGIApp, Message, Receive, Scope, Send

IDLE_SECONDS = 5
"""The seconds the server keeps a connection idle before it closes it: fewer than the wait of the
drain, so that a connection that serves nothing once the drain has begun is closed before the stop.
"""


class DrainMiddleware:
    """Close the connection of each answer once the file of the drain exists."""

    def __init__(self, app: ASGIApp, flag: Path) -> None:
        self.app = app
        self.flag = flag

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve a request; its answer closes its connection if the drain has begun by then."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def closing(message: Message) -> None:
            # Looked at when the answer starts: a request served when the drain begins is closed.
            if message["type"] == "http.response.start" and self.flag.exists():
                MutableHeaders(scope=message)["Connection"] = "close"
            await send(message)

        await self.app(scope, receive, closing)
