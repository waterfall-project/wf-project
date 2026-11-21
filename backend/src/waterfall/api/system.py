# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The operations of the system family of the contract: the probes, the metrics, the installation.

The readiness of an instance and its metrics probe the same components, by the same probes
(``waterfall.platform.metrics``). An instance is ready when the database answers: without it,
nothing is served (§4.5.4, table 12), whereas without Redis, the object storage or the identity
provider an instance still serves what does not need them — the calls that carry a valid token,
the consultation and the entry (WF-EXP-0040). The others are said all the same, and never as
available when they are not.

The status screen reads Prometheus and the database (``waterfall.api.status``).
"""

from dataclasses import dataclass
from typing import Any, cast

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from waterfall import __version__
from waterfall.api.authentication import Services, ServicesOf, Transaction
from waterfall.api.contract.models import ComponentHealth, Installation, SystemStatus
from waterfall.api.evaluation import Requires
from waterfall.api.maintenance import in_maintenance
from waterfall.api.status import StatusSources, system_status
from waterfall.core.backups import interface as backups_interface
from waterfall.platform.database import Database, create_observation_engine, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.installation import read_settings
from waterfall.platform.metrics import (
    CONTENT_TYPE,
    ApiMetrics,
    Capacities,
    Health,
    MetricsRegistry,
    OutcomeReader,
    PlatformState,
    probes_of,
)
from waterfall.platform.tasks import Outcome, last_ended

router = APIRouter(tags=["system"])

COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
# The components without which an instance serves nothing (§4.5.4, table 12).
NEEDED = ("database",)


def identity_sync_outcome(session: Session) -> Outcome | None:
    """Give how the latest reading of the accounts ended, asked or scheduled (WF-ADM-0070)."""
    ended = last_ended(session, "identity_sync")
    return None if ended is None else Outcome(ended.at, succeeded=ended.succeeded)


# The operations the platform runs on a schedule whose latest outcome the metrics give, by the name
# the rules of the alerts read (WF-OBS-0030): a test compares these names to the rules (#4301).
OUTCOMES: dict[str, OutcomeReader] = {
    "scheduled_backup": backups_interface.last_scheduled_outcome,
    "scheduled_backup_copy": backups_interface.last_copy_outcome,
    "identity_sync": identity_sync_outcome,
}


@dataclass(frozen=True, slots=True)
class Observed:
    """The metrics of a process of the API: its registry, its requests, the state it reads."""

    registry: MetricsRegistry
    requests: ApiMetrics
    state: PlatformState
    # The connection of the observation, apart from the pool of the requests.
    database: Database
    # What the status screen reads besides the database.
    sources: StatusSources

    def close(self) -> None:
        """Close the connection of the observation, and the client of Prometheus."""
        self.database.dispose()
        self.sources.close()


def observed(services: Services, capacities: Capacities, sources: StatusSources) -> Observed:
    """Make the registry of a process of the API, on the components its services reach.

    The database is probed and read on a connection of its own, on the same database as the
    requests: saturated, their pool does not make the database look down. The process announces
    its own version beside those its probes find (WF-CMP-0020).
    """
    registry = MetricsRegistry()
    database = Database(create_observation_engine(services.database.engine.url))
    probes = probes_of(database, services.queue, services.backups, services.keycloak)
    state = PlatformState(database, probes, services.backups, OUTCOMES, capacities)
    state.announced = {"api": __version__}
    registry.read_at_collection.append(state)
    return Observed(registry, ApiMetrics(registry), state, database, sources)


def observed_of(request: Request) -> Observed:
    """Give the metrics of the application that serves the request."""
    return cast("Observed", request.app.state.observed)


@router.get("/health", operation_id="getLiveness")
def get_liveness(services: ServicesOf) -> dict[str, str]:
    """Answer as soon as the process is up; say a maintenance.

    A restoration that holds the platform in maintenance is said, and its end, which the front
    waits for (#604): the process is alive all the same. The maintenance is the one row of the
    database it reads; a database out of reach says none (``waterfall.api.maintenance``).
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


@router.get(
    "/system/status",
    operation_id="getSystemStatus",
    dependencies=[Depends(Requires("system_status.read"))],
    response_model_exclude_unset=True,
)
def get_system_status(request: Request, services: ServicesOf) -> SystemStatus:
    """Give the state of the platform, to whoever may view it, without any project (WF-ADM-0130).

    Prometheus is asked before the transaction opens: no connection is held while it answers.
    """
    sources = observed_of(request).sources
    now = utc_now()
    observation = sources.observe()
    with services.database.transaction() as session:
        return system_status(session, sources, observation, now)
