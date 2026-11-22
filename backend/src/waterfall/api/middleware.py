# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The correlation of a request: its identifier, bound to its logs, handed back in a header.

The request is counted in the metrics of the process with its operation, its status and its
duration (WF-OBS-0010): the operation by its identifier in the contract, never by its path.
"""

import re
import time
from typing import TYPE_CHECKING

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request

from waterfall.api.problems import internal_error_response, problem_response
from waterfall.platform.correlation import HEADER, SCOPE_KEY, correlation_id_from
from waterfall.platform.database import is_unreachable
from waterfall.platform.logs import ANONYMOUS, get_logger, logging_context

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from waterfall.platform.metrics import ApiMetrics

logger = get_logger(__name__)

COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"

# The project a path names: the contract puts every route of a project under ``/projects/{id}``.
PROJECT_PATH = re.compile(
    r"/api/v\d+/projects/([0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12})(?:/|$)"
)


def operation_of(scope: Scope) -> str | None:
    """Name the operation of the contract a request reached, by its identifier; none if none."""
    operation: object = getattr(scope.get("route"), "operation_id", None)
    return operation if isinstance(operation, str) else None


class CorrelationMiddleware:
    """Take the identifier of the request, or make one; bind it; give it back; log and count it.

    The identifier is also kept in the scope, where the envelope of an error reads it. An
    exception nobody expected is caught here, inside the context of the request: it is logged
    once, with its correlation and its actor, and answered with a 500 from here, so that the
    framework never re-raises it into a second trace that carries neither.
    """

    def __init__(self, app: ASGIApp, metrics: ApiMetrics | None = None) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve a request of the application inside its correlation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        correlation_id = correlation_id_from(Headers(scope=scope).get(HEADER))
        scope[SCOPE_KEY] = correlation_id
        status = 500
        answered = False
        started = time.perf_counter()

        async def send_with_header(message: Message) -> None:
            nonlocal status, answered
            if message["type"] == "http.response.start":
                answered = True
                status = message["status"]
                MutableHeaders(scope=message)[HEADER] = correlation_id
            await send(message)

        context = {"correlation_id": correlation_id, "actor": ANONYMOUS}
        named = PROJECT_PATH.match(scope["path"])
        if named is not None:
            context["project_id"] = named[1].lower()
        with logging_context(**context):
            try:
                await self.app(scope, receive, send_with_header)
            except Exception as error:
                unreachable = is_unreachable(error)
                if unreachable:
                    # The component is out of reach: said by its name, with the cause in a line.
                    logger.warning(
                        "request.database_unreachable",
                        error=type(error).__name__,
                        reason=(str(error).splitlines() or [""])[0],
                    )
                else:
                    logger.exception("request.failed")
                if not answered:
                    response = (
                        problem_response(
                            Request(scope), 503, COMPONENT_UNAVAILABLE, {"component": "database"}
                        )
                        if unreachable
                        else internal_error_response(Request(scope))
                    )
                    await response(scope, receive, send_with_header)
            finally:
                seconds = time.perf_counter() - started
                logger.info(
                    "request.completed",
                    method=scope["method"],
                    path=scope["path"],
                    status=status,
                    duration_ms=round(seconds * 1000, 1),
                )
                if self.metrics is not None:
                    self.metrics.request_ended(operation_of(scope), status, seconds)
