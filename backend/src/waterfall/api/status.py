# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The status screen as the contract describes it (``SystemStatus``, WF-ADM-0130).

What it presents comes from three places (WF-OBS-0010): the availabilities, the spaces, the
versions and the alerts from the metrics, read by the query API of Prometheus
(``waterfall.platform.prometheus``, TFX-14); the dates and the results of the latest reading of the
accounts and of the latest backup from the database; the operating parameters from the settings of
the process, the largest avatar from the installation, where the bootstrap writes it (#3965).

Prometheus unavailable, the metrics are not presented (§4.5.4, table 12): the component ``metrics``
is said unavailable, alone, no alert is said, and the storage is the one nothing measured.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from typing import TYPE_CHECKING, Any

from waterfall import __version__
from waterfall.api.contract.models import AlertZone, Code, PlatformComponent, SystemStatus
from waterfall.platform.installation import read_settings
from waterfall.platform.prometheus import Prometheus, PrometheusError
from waterfall.platform.settings import OperatingParameters
from waterfall.platform.tasks import BackgroundTask, TaskKind, last_ended

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.platform.prometheus import FiringAlert, Observation, Space

# The components the status screen presents, in their order, Prometheus last; the front is not one
# (#4297).
PRESENTED = (
    PlatformComponent.api,
    PlatformComponent.worker,
    PlatformComponent.database,
    PlatformComponent.cache,
    PlatformComponent.object_storage,
    PlatformComponent.identity_provider,
)
# The space said when none is measured with its capacity: neither what is used nor what is left.
UNMEASURED = {"used_bytes": 0, "available_bytes": 0}


@dataclass(frozen=True, slots=True)
class StatusSources:
    """What the status screen reads besides the database: the parameters, and Prometheus.

    No Prometheus is given on the workstation and in the tests that do not ask for one: the screen
    then says the metrics unavailable.
    """

    parameters: OperatingParameters = field(default_factory=OperatingParameters)
    prometheus: Prometheus | None = None

    def observe(self) -> Observation | None:
        """Read what the metrics say; ``None`` when Prometheus is not given or does not answer."""
        if self.prometheus is None:
            return None
        try:
            return self.prometheus.observe()
        except PrometheusError:
            return None

    def close(self) -> None:
        """Close the client of Prometheus."""
        if self.prometheus is not None:
            self.prometheus.close()


def rate(space: Space) -> Fraction:
    """Give the occupancy of a space, the used over the capacity; an empty capacity is not full."""
    capacity = space.used_bytes + (space.available_bytes or 0)
    return Fraction(space.used_bytes, capacity) if capacity else Fraction(0)


def fullest(spaces: list[Space]) -> dict[str, int]:
    """Give the space closest to saturation, of those whose capacity is declared (#4128).

    At equal rates the object storage is given: the contract does not say which, and the rule only
    has to give the same answer at each reading.
    """
    measured = [space for space in spaces if space.available_bytes is not None]
    if not measured:
        return dict(UNMEASURED)
    space = max(measured, key=lambda each: (rate(each), each.component == "object_storage"))
    return {"used_bytes": space.used_bytes, "available_bytes": space.available_bytes or 0}


def alert(firing: FiringAlert) -> dict[str, Any] | None:
    """Describe an alert in progress as the contract does; ``None`` for a rule it does not name."""
    if firing.name not in Code.__members__:
        return None
    severity = firing.labels.get("severity", "")
    described: dict[str, Any] = {
        "code": firing.name,
        "since": firing.since,
        "severity": severity if severity in AlertZone.__members__ else AlertZone.alert,
    }
    component = firing.labels.get("component", "")
    if firing.name == Code.component_unavailable and component in PlatformComponent.__members__:
        described["params"] = {"component": component}
    if firing.name == Code.storage_nearly_full and firing.space is not None:
        described["params"] = {
            "used_bytes": firing.space.used_bytes,
            "available_bytes": firing.space.available_bytes or 0,
        }
    return described


def components(observation: Observation | None, now: datetime) -> list[dict[str, Any]]:
    """Give each component as the metrics say it; Prometheus unavailable, only that it is."""
    if observation is None:
        return [{"component": "metrics", "is_available": False, "checked_at": now, "version": None}]
    presented: list[dict[str, Any]] = []
    for component in PRESENTED:
        found = observation.availabilities.get(component)
        presented.append(
            {
                "component": component,
                # A component no collection has found is not said available.
                "is_available": found is not None and found.is_available,
                "checked_at": now if found is None else found.checked_at,
                "version": None if found is None else found.version,
            }
        )
    metrics = {"component": "metrics", "is_available": True, "checked_at": now}
    return [*presented, {**metrics, "version": observation.version}]


def outcome(session: Session, kind: TaskKind) -> dict[str, Any] | None:
    """Give the date and the result of the latest task of a kind, and its problem if it failed.

    The task, not the table of its object: a backup the rotation has removed still says how it
    ended, with the identifier of correlation of its failure (WF-OBS-0020).
    """
    ended = last_ended(session, kind)
    if ended is None:
        return None
    task = session.get(BackgroundTask, ended.task_id)
    problem = None if ended.succeeded or task is None else task.problem
    return {"at": ended.at, "succeeded": ended.succeeded, "problem": problem}


def parameters_of(parameters: OperatingParameters, avatar_max_bytes: int) -> dict[str, Any]:
    """Give the seven operating parameters in force, as the contract names them (§4.5.1)."""
    return {
        "cache_validity_seconds": parameters.cache_validity_seconds,
        "background_task_retention_days": parameters.background_task_retention_days,
        "avatar_max_bytes": avatar_max_bytes,
        "task_queue_age_threshold_seconds": parameters.task_queue_age_threshold_seconds,
        "storage_usage_threshold": str(parameters.storage_usage_threshold),
        "error_rate_threshold": str(parameters.error_rate_threshold),
        "error_rate_window_seconds": parameters.error_rate_window_seconds,
    }


def system_status(
    session: Session, sources: StatusSources, observation: Observation | None, now: datetime
) -> SystemStatus:
    """Describe the state of the platform from what the metrics said and what the database holds.

    The latest external copy and the latest restore test are not kept yet: null (US-2910, US-2930).
    The alerts come the latest first.
    """
    said = [] if observation is None else [alert(firing) for firing in observation.alerts]
    alerts = sorted(
        (each for each in said if each is not None),
        key=lambda each: (each["since"], each["code"]),
        reverse=True,
    )
    avatar_max_bytes = read_settings(session).avatar_max_bytes
    return SystemStatus.model_validate(
        {
            "version": __version__,
            "components": components(observation, now),
            "storage": dict(UNMEASURED) if observation is None else fullest(observation.spaces),
            "operating_parameters": parameters_of(sources.parameters, avatar_max_bytes),
            "last_identity_sync": outcome(session, "identity_sync"),
            "last_backup": outcome(session, "backup"),
            "last_backup_copy": None,
            "last_restore_test": None,
            "alerts": alerts,
        }
    )
