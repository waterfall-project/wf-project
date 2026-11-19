# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the system family of the contract: the probes, the metrics, the installation.

The readiness of an instance and its metrics probe the same components, by the same probes
(``waterfall.platform.metrics``). An instance is ready when the database answers: without it,
nothing is served (§4.5.4, table 12), whereas without Redis, the object storage or the identity
provider an instance still serves what does not need them — the calls that carry a valid token,
the consultation and the entry (WF-EXP-0040). The others are said all the same, and never as
available when they are not.
"""

from dataclasses import dataclass
from typing import Any, cast

from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session

from waterfall import __version__
from waterfall.api.authentication import Services, ServicesOf, Transaction
from waterfall.api.contract.models import ComponentHealth, Installation
from waterfall.api.maintenance import in_maintenance
from waterfall.core.backups import interface as backups_interface
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.installation import read_settings
from waterfall.platform.metrics import (
    CONTENT_TYPE,
    ApiMetrics,
    Capacities,
    Health,
    MetricsRegistry,
    Outcome,
    OutcomeReader,
    PlatformState,
    probes_of,
)
from waterfall.platform.tasks import last_ended

router = APIRouter(tags=["system"])

COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
# The components without which an instance serves nothing (§4.5.4, table 12).
NEEDED = ("database",)


def identity_sync_outcome(session: Session) -> Outcome | None:
    """Give how the latest reading of the accounts ended, asked or scheduled (WF-ADM-0070)."""
    ended = last_ended(session, "identity_sync")
    return None if ended is None else Outcome(ended.at, succeeded=ended.succeeded)


# The operations the platform runs on a schedule whose latest outcome the metrics give, by the name
# the rules of the alerts read (WF-OBS-0030); the external copy of a backup comes with US-2910.
OUTCOMES: dict[str, OutcomeReader] = {
    "scheduled_backup": backups_interface.last_scheduled_outcome,
    "identity_sync": identity_sync_outcome,
}


@dataclass(frozen=True, slots=True)
class Observed:
    """The metrics of a process of the API: its registry, its requests, the state it reads."""

    registry: MetricsRegistry
    requests: ApiMetrics
    state: PlatformState


def observed(services: Services, capacities: Capacities) -> Observed:
    """Make the registry of a process of the API, on the components its services reach."""
    registry = MetricsRegistry()
    probes = probes_of(services.database, services.queue, services.backups, services.keycloak)
    state = PlatformState(services.database, probes, services.backups, OUTCOMES, capacities)
    registry.read_at_collection.append(state)
    return Observed(registry, ApiMetrics(registry), state)


def observed_of(request: Request) -> Observed:
    """Give the metrics of the application that serves the request."""
    return cast("Observed", request.app.state.observed)


@router.get("/health", operation_id="getLiveness")
def get_liveness(services: ServicesOf) -> dict[str, str]:
    """Answer as soon as the process is up, touching no component of data; say a maintenance.

    A restoration that holds the platform in maintenance is said, and its end, which the front
    waits for (#604): the process is alive all the same.
    """
    return {"status": "maintenance" if in_maintenance(services.maintenance) else "ok"}


def _described(health: Health) -> ComponentHealth:
    return ComponentHealth.model_validate(
        {
            "component": health.component,
            "is_available": health.is_available,
            "checked_at": health.checked_at,
            "version": health.version,
        }
    )


@router.get("/health/ready", operation_id="getReadiness")
def get_readiness(request: Request) -> dict[str, Any]:
    """Answer when the components the instance needs answer; refuse naming the first that does not.

    Each component is said as its probe found it, the instance itself first (WF-EXP-0040).
    """
    probed = observed_of(request).state.probe()
    for health in probed:
        if health.component in NEEDED and not health.is_available:
            raise UnavailableError(COMPONENT_UNAVAILABLE, {"component": health.component})
    instance = Health("api", is_available=True, version=__version__, checked_at=utc_now())
    return {"status": "ready", "components": [_described(each) for each in [instance, *probed]]}


@router.get("/metrics", operation_id="getMetrics")
def get_metrics(request: Request) -> Response:
    """Give the metrics in the format of Prometheus, whatever answers (WF-OBS-0010, TFX-09).

    The counters of every process of the API, and what is read of the platform at this collection.
    """
    return Response(observed_of(request).registry.expose(), media_type=CONTENT_TYPE)


@router.get("/installation", operation_id="getInstallation")
def get_installation(session: Transaction) -> Installation:
    """Give what the front must know of the installation before any session, to anybody.

    Its language by default, which the front falls back on (WF-INTF-0160), its time zone, in which
    the front proposes the current day (WF-PLA-0130, US-2200), and the bounds of what it lets pass;
    refused while the installation is not bootstrapped (503).
    """
    settings = read_settings(session)
    return Installation.model_validate(
        {
            "default_language": settings.default_language,
            "time_zone": settings.time_zone,
            "avatar_max_bytes": settings.avatar_max_bytes,
            "external_backup_max_bytes": settings.external_backup_max_bytes,
        }
    )
