# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The maintenance of a restoration, as the API serves it (WF-ADM-0160, #604).

While a restoration holds the platform in maintenance, every operation but the probe of liveness
and the metrics answers 503 ``COMPONENT_UNAVAILABLE``, the database being replaced; the probe says
the maintenance, and its end, and a restoration given up that keeps it for an operator (#1016).
The maintenance is read in the schema ``platform`` of the database,
which the restoration leaves in place (``waterfall.platform.maintenance``): Redis emptied lifts
nothing (#956). A database out of reach — refusing, mute, or its pool spent — says no
maintenance: the operations that need it say so themselves, and the probe of liveness answers.
"""

from typing import TYPE_CHECKING

from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request

from waterfall.api.problems import problem_response
from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from waterfall.platform.maintenance import Maintenance, Restoring

COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
# The path of the probe of liveness (``getLiveness``), served in maintenance; and that of the
# metrics (``getMetrics``), which depend on no component and say each one down (WF-OBS-0010).
LIVENESS = "/api/v1/health"
METRICS = "/api/v1/metrics"
SERVED_IN_MAINTENANCE = (LIVENESS, METRICS)

logger = get_logger(__name__)


def in_maintenance(maintenance: Maintenance | None) -> bool:
    """Tell whether a restoration holds the platform in maintenance; not if the database is mute."""
    return holding(maintenance) is not None


def holding(maintenance: Maintenance | None) -> Restoring | None:
    """Give the restoration that holds the platform in maintenance; none if the database is mute."""
    if maintenance is None:
        return None
    try:
        return maintenance.current()
    except (DBAPIError, PoolTimeoutError) as error:
        # The cause in a line, not its traceback: rendered with its locals, it held the probe for
        # seconds, longer than the healthcheck waits.
        logger.warning(
            "maintenance.unread", error=type(error).__name__, reason=str(error).splitlines()[0]
        )
        return None


class MaintenanceMiddleware:
    """Refuse every operation but the probe of liveness and the metrics during a maintenance."""

    def __init__(self, app: ASGIApp, maintenance: Maintenance | None) -> None:
        self.app = app
        self.maintenance = maintenance

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Serve the request, or answer 503 if the platform is held and it is not one served held.

        The refusal comes before the routing: the metrics count it as ``unrouted``, the route being
        resolved by the router of FastAPI alone, which gives no operation to a request refused
        before it.
        """
        if scope["type"] == "http" and scope["path"] not in SERVED_IN_MAINTENANCE:
            held = await run_in_threadpool(in_maintenance, self.maintenance)
            if held:
                refused = problem_response(
                    Request(scope), 503, COMPONENT_UNAVAILABLE, {"component": "database"}
                )
                await refused(scope, receive, send)
                return
        await self.app(scope, receive, send)
