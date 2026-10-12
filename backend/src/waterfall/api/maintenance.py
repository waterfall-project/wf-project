# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The maintenance of a restoration, as the API serves it (WF-ADM-0160, #604).

While a restoration holds the platform in maintenance, every operation but the probe of liveness
answers 503 ``COMPONENT_UNAVAILABLE``, the database being replaced; the probe says the maintenance,
and its end. A Redis out of reach says no maintenance: the operations that need it say so
themselves, and the others are served.
"""

from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from waterfall.api.problems import problem_response
from waterfall.platform.logs import get_logger
from waterfall.platform.maintenance import Maintenance

COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
# The path of the probe of liveness (``getLiveness``), served in maintenance.
LIVENESS = "/api/v1/health"

logger = get_logger(__name__)


def in_maintenance(maintenance: Maintenance | None) -> bool:
    """Tell whether a restoration holds the platform in maintenance; not if Redis does not say."""
    if maintenance is None:
        return False
    try:
        return maintenance.current() is not None
    except RedisError:
        logger.warning("maintenance.unread", exc_info=True)
        return False


class MaintenanceMiddleware:
    """Refuse every operation but the probe of liveness while the platform is in maintenance."""

    def __init__(self, app: ASGIApp, maintenance: Maintenance | None) -> None:
        self.app = app
        self.maintenance = maintenance

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve the request, or answer 503 if it is not the probe and the platform is held."""
        if scope["type"] == "http" and scope["path"] != LIVENESS:
            held = await run_in_threadpool(in_maintenance, self.maintenance)
            if held:
                refused = problem_response(
                    Request(scope), 503, COMPONENT_UNAVAILABLE, {"component": "database"}
                )
                await refused(scope, receive, send)
                return
        await self.app(scope, receive, send)
