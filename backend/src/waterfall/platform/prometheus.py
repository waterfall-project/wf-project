# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The client of the query API of Prometheus, which the status screen reads (TFX-14, WF-ADM-0130).

The screen presents what the metrics say (WF-OBS-0010): the availability of each component and the
date of its last collection, the spaces of PostgreSQL and of the object storage, the version each
component announces, and the alerts in progress, which the rules of Prometheus raise and end
(WF-OBS-0030). It reads them here, in one observation; whatever fails of it — Prometheus out of
reach, an answer it should not give — makes the whole observation fail, ``PrometheusError``: the
screen then says the metrics unavailable (§4.5.4, table 12), and presents none of what they say
rather than a part of it.

The API and the worker are available when one of their instances answers the collection, ``up``;
the components the API probes, when one replica of it found them answering,
``waterfall_component_up`` — each the highest of its series, as the rules of the alerts read them.
Prometheus is reached in HTTPS, its certificate checked against the roots of the platform when the
settings give them (US-2840).
"""

import math
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, cast

import httpx2

from waterfall.platform.keycloak import trusted
from waterfall.platform.logs import get_logger
from waterfall.platform.metrics import (
    COMPONENT_UP,
    COMPONENT_VERSION,
    STORAGE_AVAILABLE,
    STORAGE_USED,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

TIMEOUT_SECONDS = 2.0
# How long a whole observation may take, whatever the number of its requests.
OBSERVATION_SECONDS = 8.0
# The processes Prometheus collects, by the name of their job, which is that of their component.
PROCESSES = 'up{job=~"api|worker"}'
# The availability of each component, and the date of its last collection: the processes by ``up``,
# their job taken as their component, the others by what the API probed.
AVAILABILITY = (
    f'max by (component) (label_replace({PROCESSES}, "component", "$1", "job", "(.*)"))'
    f" or max by (component) ({COMPONENT_UP})"
)
CHECKED = (
    f'max by (component) (label_replace(timestamp({PROCESSES}), "component", "$1", "job", "(.*)"))'
    f" or max by (component) (timestamp({COMPONENT_UP}))"
)
VERSIONS = f"max by (component, version) ({COMPONENT_VERSION})"
USED = f"max by (component) ({STORAGE_USED})"
AVAILABLE = f"max by (component) ({STORAGE_AVAILABLE})"
# The alert whose parameters are the space of its component when it was raised (``Alert.params``).
STORAGE_NEARLY_FULL = "storage_nearly_full"

logger = get_logger(__name__)

# A sample of an instant vector: its labels, and its value.
type Sample = tuple[dict[str, str], float]


class PrometheusError(Exception):
    """Prometheus did not answer, or not as its query API does."""


@dataclass(frozen=True, slots=True)
class Space:
    """The space a component uses, and what is left of the capacity it declares, if it does."""

    component: str
    used_bytes: int
    available_bytes: int | None


@dataclass(frozen=True, slots=True)
class Availability:
    """Whether a component answered its last collection, when it was, and the version it says."""

    component: str
    is_available: bool
    checked_at: datetime
    version: str | None


@dataclass(frozen=True, slots=True)
class FiringAlert:
    """An alert in progress: its name, its labels, since when, and the space it was raised on."""

    name: str
    labels: Mapping[str, str]
    since: datetime
    space: Space | None = None


@dataclass(frozen=True, slots=True)
class Observation:
    """What the metrics say of the platform, read at once.

    ``availabilities`` holds only the components Prometheus knows of; ``version`` is that of
    Prometheus itself.
    """

    availabilities: Mapping[str, Availability]
    spaces: list[Space]
    alerts: list[FiringAlert]
    version: str | None


def _moment(seconds: object) -> datetime:
    return datetime.fromtimestamp(float(cast("float", seconds)), UTC)


class Prometheus:
    """The query API of a Prometheus, as the API reaches it."""

    def __init__(
        self, address: str, authority: str | None = None, *, timeout: float = TIMEOUT_SECONDS
    ) -> None:
        """Prepare the client; nothing is asked before a reading."""
        self._timeout = timeout
        # When the observation in progress must be over, if one is.
        self._observing = threading.local()
        self._http = httpx2.Client(
            base_url=address.rstrip("/"), timeout=timeout, verify=trusted(authority)
        )

    def close(self) -> None:
        """Close the connections to Prometheus."""
        self._http.close()

    def _data(self, path: str, **parameters: str) -> Any:
        """Give the data of an answer of the API, or raise ``PrometheusError``."""
        deadline: float | None = getattr(self._observing, "deadline", None)
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0:
            logger.warning("prometheus.too_slow")
            raise PrometheusError
        try:
            answer = self._http.get(
                path,
                params=parameters,
                timeout=self._timeout if remaining is None else min(self._timeout, remaining),
            )
            document: object = answer.json() if answer.status_code == HTTPStatus.OK else None
        except (httpx2.HTTPError, ValueError) as error:
            logger.warning("prometheus.unreachable", fault=type(error).__name__)
            raise PrometheusError from None
        found = cast("dict[str, Any]", document) if isinstance(document, dict) else {}
        if found.get("status") != "success":
            logger.warning("prometheus.failed", status=answer.status_code)
            raise PrometheusError
        return found.get("data")

    def query(self, expression: str, at: datetime | None = None) -> list[Sample]:
        """Evaluate an expression now, or at a moment: each sample of the vector it gives."""
        parameters = {"query": expression}
        if at is not None:
            parameters["time"] = f"{at.timestamp():.3f}"
        data = self._data("/api/v1/query", **parameters)
        try:
            vector = [
                (dict(sample["metric"]), float(sample["value"][1])) for sample in data["result"]
            ]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            logger.warning("prometheus.unread", fault=type(error).__name__)
            raise PrometheusError from None
        # NaN and the infinities are values Prometheus may say, that no space or moment holds.
        if not all(math.isfinite(value) for _, value in vector):
            logger.warning("prometheus.unread", fault="NonFinite")
            raise PrometheusError
        return vector

    def firing(self) -> list[FiringAlert]:
        """Give the alerts in progress, since the moment their rule found them true."""
        data = self._data("/api/v1/alerts")
        try:
            return [
                FiringAlert(alert["labels"]["alertname"], alert["labels"], _instant(alert))
                for alert in data["alerts"]
                if alert["state"] == "firing"
            ]
        except (KeyError, TypeError, ValueError) as error:
            logger.warning("prometheus.unread", fault=type(error).__name__)
            raise PrometheusError from None

    def version(self) -> str | None:
        """Give the version of Prometheus, if it says it."""
        data: object = self._data("/api/v1/status/buildinfo")
        found = cast("dict[str, Any]", data) if isinstance(data, dict) else {}
        version: object = found.get("version")
        return str(version) if version else None

    def spaces(self, at: datetime | None = None) -> list[Space]:
        """Give the space of each component the metrics measure, now or at a moment."""
        left = {labels.get("component", ""): value for labels, value in self.query(AVAILABLE, at)}
        return [
            Space(component, int(used), None if component not in left else int(left[component]))
            for labels, used in self.query(USED, at)
            if (component := labels.get("component"))
        ]

    def observe(self) -> Observation:
        """Read at once what the status screen presents of the metrics; raise if any of it fails.

        The whole reading is bounded by ``OBSERVATION_SECONDS``, not only each request of it, but
        only roughly: httpx applies the timeout of a request to each phase (connection, read,
        write, pool), not to the request as a whole, so a slow one can overrun the deadline
        a little.
        """
        self._observing.deadline = time.monotonic() + OBSERVATION_SECONDS
        try:
            return self._observe()
        finally:
            self._observing.deadline = None

    def _observe(self) -> Observation:
        checked = {labels.get("component"): value for labels, value in self.query(CHECKED)}
        said: dict[str, list[str]] = {}
        for labels, _ in self.query(VERSIONS):
            said.setdefault(labels.get("component", ""), []).append(labels.get("version", ""))
        availabilities = {
            component: Availability(
                component,
                is_available=value >= 1,
                checked_at=_moment(checked.get(component, 0)),
                # Two versions while an update replaces the instances one by one: both are said.
                version=", ".join(sorted(said[component])) if component in said else None,
            )
            for labels, value in self.query(AVAILABILITY)
            if (component := labels.get("component"))
        }
        alerts = [self._with_space(alert) for alert in self.firing()]
        return Observation(availabilities, self.spaces(), alerts, self.version())

    def _with_space(self, alert: FiringAlert) -> FiringAlert:
        """Give a storage nearly full the space of its component when the alert was raised."""
        if alert.name != STORAGE_NEARLY_FULL:
            return alert
        component = alert.labels.get("component")
        found = [space for space in self.spaces(alert.since) if space.component == component]
        return FiringAlert(alert.name, alert.labels, alert.since, found[0] if found else None)


def _instant(alert: Mapping[str, Any]) -> datetime:
    """Read the moment an alert became true, as Prometheus writes it (RFC 3339)."""
    return datetime.fromisoformat(str(alert["activeAt"])).astimezone(UTC)
