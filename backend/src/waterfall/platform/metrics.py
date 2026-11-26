# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The metrics of a process, in the format of Prometheus, by its client library (WF-OBS-0010).

Each process holds a registry of its own (``MetricsRegistry``), never the default one of the
library: the API counts its requests in it (``ApiMetrics``), the worker its tasks and the failures
of the directories it has synchronised (``WorkerMetrics``, #917). What the API reads besides at each
collection, ``PlatformState`` reads then, and nothing keeps it between two: the availability of
each component of data and of the identity provider, probed together within a delay; the tasks
queued and the age of the oldest; the latest outcome of what the platform runs on a schedule;
whether a restoration given up keeps the platform in maintenance, for an operator (#1016); and the
space PostgreSQL and the object storage use, and what is left of the capacity the deployment
declares. A gauge that cannot be read — the database down, a capacity not declared — is left out,
never given a value it does not have. The API serves the metrics on ``getMetrics`` — and, when it
serves in TLS, in HTTP at the same path of a port of their own, shared by its processes
(``MetricsRegistry.serve_shared``, US-2840); the worker, which listens to nothing else, on a port of
its own (``MetricsRegistry.serve``).

The names below are the interface: the rules of the alerts (US-2880) and the status screen
(US-2890) read them by the query API of Prometheus. The error rate of the requests is the share of
those answered with a status of 500 or more; the failure rate of the tasks, that of the tasks ended
``failed``. No label carries what a request or a task holds: an operation is named by its
identifier in the contract, never by its path, which holds identifiers of projects; no identity, no
secret (TFX-09).

The API serves on several processes (US-2230): its counters are then written in files of a folder
the processes share, ``PROMETHEUS_MULTIPROC_DIR``, which ``shared_between_processes`` sets before
they start, and the exposition merges them. The library reads that variable once, when it is first
imported: a process imported before it was set — the API on one process — counts in memory.
"""

import os
import shutil
import tempfile
import threading
from collections.abc import Callable, Generator, Iterator, Mapping
from concurrent.futures import Future, wait
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from socketserver import ThreadingMixIn
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast, get_args, override
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.exposition import CONTENT_TYPE_PLAIN_0_0_4, start_http_server
from prometheus_client.metrics_core import GaugeMetricFamily, Metric
from prometheus_client.multiprocess import MultiProcessCollector
from sqlalchemy import Boolean, Text, column, func, select, table, true
from sqlalchemy.exc import SQLAlchemyError

from waterfall.platform.database import OBSERVATION_SECONDS, bound_lock_waits, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.keycloak import IdentityProviderError, expect
from waterfall.platform.logs import get_logger
from waterfall.platform.maintenance import abandoned_held
from waterfall.platform.storage import MissingObjectError
from waterfall.platform.tasks import waiting

if TYPE_CHECKING:
    from datetime import datetime
    from wsgiref.types import StartResponse, WSGIEnvironment

    from prometheus_client.registry import Collector
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.keycloak_admin import KeycloakAdmin
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.storage import Bucket
    from waterfall.platform.tasks import Outcome

# The variable by which the client library shares the counters of several processes.
MULTIPROCESS = "PROMETHEUS_MULTIPROC_DIR"
# The type of the exposition: the text format every version of Prometheus reads.
CONTENT_TYPE = CONTENT_TYPE_PLAIN_0_0_4

# What the API counts: its requests, by operation and status, and how long each took.
REQUESTS = "waterfall_api_requests"
REQUEST_DURATION = "waterfall_api_request_duration_seconds"
# What the worker counts: its tasks, by kind and outcome, and how long each ran.
TASKS = "waterfall_worker_tasks"
TASK_DURATION = "waterfall_worker_task_duration_seconds"
# The directories the identity provider failed to read during a reading of the accounts (#917).
DIRECTORY_SYNC_FAILURES = "waterfall_identity_directory_sync_failures"
# What the API reads at each collection.
COMPONENT_UP = "waterfall_component_up"
QUEUED_TASKS = "waterfall_queued_tasks"
OLDEST_QUEUED_TASK_AGE = "waterfall_oldest_queued_task_age_seconds"
LAST_RUN_SUCCESS = "waterfall_last_run_success"
LAST_RUN_TIMESTAMP = "waterfall_last_run_timestamp_seconds"
# Whether a restoration given up, its databases possibly changed, holds the maintenance (#1016).
RESTORATION_ABANDONED = "waterfall_restoration_abandoned"
STORAGE_USED = "waterfall_storage_used_bytes"
STORAGE_AVAILABLE = "waterfall_storage_available_bytes"
# The version each component announces, in a label, the value always 1 (WF-CMP-0020): the API's
# and the worker's their own, the others' as their probe found it.
COMPONENT_VERSION = "waterfall_component_version"

# The operation a request that reached no route is counted under: refused before, or unknown.
UNROUTED = "unrouted"
# The bounds of the durations of the tasks, in seconds: from a marking to a backup.
TASK_BUCKETS = (0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0)
# How long a collection waits for the probes, in seconds: one that has not answered is down.
PROBE_SECONDS = float(OBSERVATION_SECONDS)
# How long a reading of the database waits for a statement or a lock, at a collection.
READING_WAIT = timedelta(seconds=2)

# The catalogue of the databases of the server, read for their size.
PG_DATABASE = table(
    "pg_database", column("datname", Text), column("datistemplate", Boolean), schema="pg_catalog"
)

# The components the API probes, as the contract names them (``PlatformComponent``).
type ProbedComponent = Literal["database", "cache", "object_storage", "identity_provider"]
PROBED: tuple[ProbedComponent, ...] = get_args(ProbedComponent.__value__)
# What a probe does: ask its component, give the version it announces, if any; raise if it fails.
type Probe = Callable[[], str | None]

logger = get_logger(__name__)


class Described(Protocol):
    """What the client of Redis answers to ``INFO``, as redis-py parses it."""

    def info(self, section: str) -> Mapping[str, object]:
        """Give the fields of a section of ``INFO``."""
        ...


class MetricsRegistry:
    """The registry of one process, and how its metrics are exposed."""

    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        # What is read at each collection, beside what the process counts.
        self.read_at_collection: list[Collector] = []

    def collectors(self) -> list[Collector]:
        """Give what an exposition collects: the counters of every process, then what is read."""
        folder = os.environ.get(MULTIPROCESS)
        counted: Collector = (
            self.registry if folder is None else MultiProcessCollector(None, path=folder)
        )
        return [counted, *self.read_at_collection]

    def collect(self) -> Iterator[Metric]:
        """Collect every metric of the process, as Prometheus does at each collection."""
        for collector in self.collectors():
            yield from collector.collect()

    def expose(self) -> bytes:
        """Give the metrics in the text format of Prometheus (``CONTENT_TYPE``)."""
        return generate_latest(self)

    def serve(self, host: str, port: int) -> Callable[[], None]:
        """Serve the metrics over HTTP on a port of their own; give what stops the server."""
        server, thread = start_http_server(port, host, registry=self)

        def stop() -> None:
            server.shutdown()
            server.server_close()
            thread.join()

        return stop

    def serve_shared(self, host: str, port: int, path: str) -> Callable[[], None]:
        """Serve the metrics over HTTP at one path of a port of their own; give what stops it.

        The port is shared by every process that serves there (``SO_REUSEPORT``): each process of
        the API serves the same exposition, the counters of all of them merged, and the system
        hands each collection to one of them. Any other path, or method, is not found: the port
        serves the metrics and nothing else, in the clear (TFX-09).
        """

        def application(environ: WSGIEnvironment, start: StartResponse) -> list[bytes]:
            found = environ.get("PATH_INFO") == path and environ.get("REQUEST_METHOD") == "GET"
            body = self.expose() if found else b"not found\n"
            kind = CONTENT_TYPE if found else "text/plain; charset=utf-8"
            start(
                "200 OK" if found else "404 Not Found",
                [("Content-Type", kind), ("Content-Length", str(len(body)))],
            )
            return [body]

        server = make_server(
            host, port, application, server_class=_SharedServer, handler_class=_QuietHandler
        )
        thread = threading.Thread(target=server.serve_forever, name="metrics", daemon=True)
        thread.start()

        def stop() -> None:
            server.shutdown()
            server.server_close()
            thread.join()

        return stop


class _SharedServer(ThreadingMixIn, WSGIServer):
    """A server of the metrics on a port several processes listen on, a thread per request."""

    allow_reuse_port = True
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    """A handler that writes nothing of the requests: the collections are not events."""

    @override
    def log_message(self, format: str, *args: Any) -> None:
        """Write nothing."""


@contextmanager
def shared_between_processes() -> Generator[None]:
    """Make the processes started inside share their counters, in a folder removed after them."""
    folder = tempfile.mkdtemp(prefix="waterfall-metrics-")
    os.environ[MULTIPROCESS] = folder
    try:
        yield
    finally:
        del os.environ[MULTIPROCESS]
        shutil.rmtree(folder, ignore_errors=True)


class ApiMetrics:
    """What the API counts of its requests: how many, by operation and status, and how long."""

    def __init__(self, registry: MetricsRegistry) -> None:
        self.requests = Counter(
            REQUESTS,
            "Requests served, by operation of the contract and status of the answer.",
            ("operation", "status"),
            registry=registry.registry,
        )
        self.durations = Histogram(
            REQUEST_DURATION,
            "Time taken to answer a request, by operation of the contract.",
            ("operation",),
            registry=registry.registry,
        )

    def request_ended(self, operation: str | None, status: int, seconds: float) -> None:
        """Count a request answered, under its operation, or ``UNROUTED`` if it reached none."""
        named = operation or UNROUTED
        self.requests.labels(named, str(status)).inc()
        self.durations.labels(named).observe(seconds)


class WorkerMetrics:
    """What the worker counts: its tasks by kind and outcome, and the directories not read."""

    def __init__(self, registry: MetricsRegistry) -> None:
        self.tasks = Counter(
            TASKS,
            "Tasks ended, by kind and outcome (succeeded or failed).",
            ("kind", "outcome"),
            registry=registry.registry,
        )
        self.durations = Histogram(
            TASK_DURATION,
            "Time a task ran, from its start to its end, by kind.",
            ("kind",),
            buckets=TASK_BUCKETS,
            registry=registry.registry,
        )
        self.directory_failures = Counter(
            DIRECTORY_SYNC_FAILURES,
            "Entries of a federated directory the identity provider failed to synchronise.",
            registry=registry.registry,
        )

    def task_ended(self, kind: str, *, succeeded: bool, seconds: float | None) -> None:
        """Count a task ended; ``seconds`` is ``None`` for one that failed without running."""
        self.tasks.labels(kind, "succeeded" if succeeded else "failed").inc()
        if seconds is not None:
            self.durations.labels(kind).observe(seconds)

    def directories_failed(self, count: int) -> None:
        """Count the failures the identity provider said in synchronising its directories."""
        self.directory_failures.inc(count)


@dataclass(frozen=True, slots=True)
class Health:
    """What a probe found of a component: whether it answered, its version, and when asked."""

    component: str
    is_available: bool
    version: str | None
    checked_at: datetime


class Flights:
    """What runs beside a collection, in daemon threads, one at a time for each name.

    A call that outlasts what a collection waits for is left to end alone, and the process does not
    wait for it at exit. While it runs, a caller that asks for the same name is given the same call
    and starts none: a component that no longer answers holds one thread, however often it is asked.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: dict[str, Future[Any]] = {}

    def start(self, name: str, call: Callable[[], Any]) -> Future[Any]:
        """Give the call running under ``name``, or start ``call`` in a thread of its own."""
        with self._lock:
            running = self._running.get(name)
            if running is not None and not running.done():
                return running
            future: Future[Any] = Future()
            self._running[name] = future

        def run() -> None:
            try:
                future.set_result(call())
            except BaseException as fault:
                # Whatever ends the call ends the flight: a future left pending would hold the name
                # for the life of the process.
                logger.debug("flight.failed", name=name, exc_info=True)
                future.set_exception(fault)

        try:
            threading.Thread(target=run, name=f"flight-{name}", daemon=True).start()
        except BaseException as fault:
            logger.warning("flight.not_started", name=name, exc_info=True)
            future.set_exception(fault)
            if not isinstance(fault, Exception):
                raise  # an interrupt of the calling thread is not ours to swallow
        return future


def probe(
    probes: Mapping[str, Probe], timeout: float = PROBE_SECONDS, flights: Flights | None = None
) -> list[Health]:
    """Ask every component at once; one that fails, or has not answered within ``timeout``, is down.

    A probe that has not answered is left to end alone: the collection does not wait for it, and
    ``flights`` starts no other while it runs.
    """
    checked_at = utc_now()
    started = flights or Flights()
    asked = {component: started.start(f"probe-{component}", p) for component, p in probes.items()}
    wait(asked.values(), timeout=timeout)
    return [_health(component, answer, checked_at) for component, answer in asked.items()]


def _health(component: str, answer: Future[Any], checked_at: datetime) -> Health:
    if not answer.done():
        logger.warning("probe.timed_out", component=component)
        return Health(component, is_available=False, version=None, checked_at=checked_at)
    fault = answer.exception()
    if fault is not None:
        logger.warning("probe.failed", component=component, fault=type(fault).__name__)
        return Health(component, is_available=False, version=None, checked_at=checked_at)
    return Health(component, is_available=True, version=answer.result(), checked_at=checked_at)


def probes_of(
    database: Database,
    queue: TaskQueue,
    bucket: Bucket,
    keycloak: Keycloak,
    administration: KeycloakAdmin,
) -> dict[str, Probe]:
    """Give the probe of each component the API depends on, in the order of ``PROBED``.

    Keycloak answers when it serves the keys of the realm; its version is then read from the
    extension, as the service account (#4641). A version that cannot be read is not said, and leaves
    Keycloak available: its keys, which every request needs, are served.
    """

    def database_probe() -> str | None:
        with database.transaction() as session:
            bound_waiting(session)
            version = session.scalar(select(func.current_setting("server_version")))
        return None if version is None else str(version).split()[0]

    def cache_probe() -> str | None:
        version = cast("Described", queue.client).info("server").get("redis_version")
        return None if version is None else str(version)

    def storage_probe() -> None:
        bucket.reach()

    def identity_provider_probe() -> str | None:
        expect(keycloak.send("GET", f"{keycloak.protocol}/certs"), 200)
        try:
            return administration.server_version()
        except (UnavailableError, IdentityProviderError) as fault:
            logger.warning("probe.version_unread", component="identity_provider", fault=str(fault))
            return None

    return {
        "database": database_probe,
        "cache": cache_probe,
        "object_storage": storage_probe,
        "identity_provider": identity_provider_probe,
    }


def bound_waiting(session: Session) -> None:
    """Bound how long the statements of a transaction wait, and the locks they take."""
    statement = f"{round(READING_WAIT.total_seconds() * 1000)}ms"
    session.execute(select(func.set_config("statement_timeout", statement, true())))
    bound_lock_waits(session, READING_WAIT)


# What reads the latest outcome of one such operation in the database; ``None`` if none has ended.
type OutcomeReader = Callable[[Session], Outcome | None]


@dataclass(frozen=True, slots=True)
class Capacities:
    """The space, in bytes, the deployment declares for PostgreSQL and the object storage."""

    database: int | None = None
    object_storage: int | None = None


def database_used_bytes(session: Session) -> int:
    """Give the size of the databases of the server the service may connect to, templates aside.

    Those of Waterfall and of the identity provider when they share their server, as the Compose and
    the chart deploy them: the space the capacity declared is that of the server.
    """
    name = PG_DATABASE.c.datname
    size = func.coalesce(func.sum(func.pg_database_size(name)), 0)
    reachable = func.has_database_privilege(name, "CONNECT")
    used = session.scalar(select(size).where(PG_DATABASE.c.datistemplate.is_(False), reachable))
    return int(used or 0)


class PlatformState:
    """What the API reads of the platform at each collection, and exposes as gauges.

    ``outcomes`` names each operation the platform runs on a schedule, and reads its latest outcome:
    a module adds its own without this class changing (the external copy, US-2910). ``budget`` is
    how long, in seconds, the listing of the storage may take.
    """

    budget: float = PROBE_SECONDS

    def __init__(
        self,
        database: Database,
        probes: Mapping[str, Probe],
        storage: Bucket,
        outcomes: Mapping[str, OutcomeReader],
        capacities: Capacities,
    ) -> None:
        self.database = database
        self.probes = probes
        self.storage = storage
        self.outcomes = outcomes
        self.capacities = capacities
        # The version of the process itself, by its component; none until its entry point says it.
        self.announced: Mapping[str, str] = {}
        self.flights = Flights()

    def probe(self) -> list[Health]:
        """Ask every component whether it answers."""
        return probe(self.probes, flights=self.flights)

    def collect(self) -> Iterator[Metric]:
        """Probe, then read what the components that answered give; leave out what they do not."""
        healths = self.probe()
        up = GaugeMetricFamily(
            COMPONENT_UP,
            "Whether a component answered its probe at this collection (1) or not (0).",
            labels=("component",),
        )
        for health in healths:
            up.add_metric((health.component,), 1.0 if health.is_available else 0.0)
        yield up
        found = {health.component: health.version for health in healths if health.version}
        yield versions({**self.announced, **found})
        answering = {health.component for health in healths if health.is_available}
        used: dict[str, int] = {}
        if "database" in answering:
            abandoned = self.restoration_abandoned()
            if abandoned is not None:
                yield abandoned
            read = self.read_database()
            if read is not None:
                metrics, used["database"] = read
                yield from metrics
        if "object_storage" in answering:
            stored = self.storage_used()
            if stored is not None:
                used["object_storage"] = stored
        yield from self.spaces(used)

    def read_database(self) -> tuple[list[Metric], int] | None:
        """Read the queue, the latest outcomes and the space used, in one bounded transaction."""
        try:
            with self.database.transaction() as session:
                bound_waiting(session)
                queued = waiting(session)
                outcomes = {name: read(session) for name, read in self.outcomes.items()}
                used = database_used_bytes(session)
        except SQLAlchemyError:
            logger.warning("metrics.database_unread", exc_info=True)
            return None
        count = GaugeMetricFamily(QUEUED_TASKS, "Tasks queued, that no worker has taken yet.")
        count.add_metric((), float(queued.count))
        oldest = 0.0
        if queued.oldest_since is not None:
            oldest = max((utc_now() - queued.oldest_since).total_seconds(), 0.0)
        age = GaugeMetricFamily(
            OLDEST_QUEUED_TASK_AGE, "How long the oldest task queued has waited; 0 if none waits."
        )
        age.add_metric((), oldest)
        return [count, age, *_outcome_metrics(outcomes)], used

    def restoration_abandoned(self) -> Metric | None:
        """Read whether a restoration given up holds the maintenance, in a transaction of its own.

        Apart from the rest of the database: in that maintenance, the tables the rest reads may be
        half replaced, and unread, while the schema ``platform`` it reads is in place (#1016).
        """
        try:
            with self.database.transaction() as session:
                bound_waiting(session)
                held = abandoned_held(session)
        except SQLAlchemyError:
            logger.warning("metrics.restoration_unread", exc_info=True)
            return None
        gauge = GaugeMetricFamily(
            RESTORATION_ABANDONED,
            "Whether a restoration given up keeps the platform in maintenance (1) or not (0).",
        )
        gauge.add_metric((), 1.0 if held else 0.0)
        return gauge

    def storage_used(self) -> int | None:
        """Sum the objects of the bucket; ``None`` if the listing fails or outlasts the budget.

        The listing reads every object: once the budget of the probes is spent it is left to end
        alone, as a probe is, in a thread that does not hold the exit of the process: while it runs,
        no other listing starts, and the space is left out if it outlasts the budget.
        """
        listing = self.flights.start("storage-used", self.storage.used_bytes)
        wait([listing], timeout=self.budget)
        if not listing.done():
            logger.warning("metrics.storage_unread", reason="timed_out")
            return None
        try:
            return listing.result()
        except UnavailableError, MissingObjectError:
            logger.warning("metrics.storage_unread", exc_info=True)
            return None

    def spaces(self, used: Mapping[str, int]) -> Iterator[Metric]:
        """Give the space each component uses, and what is left of the capacity it has declared."""
        taken = GaugeMetricFamily(STORAGE_USED, "Space used, in bytes.", labels=("component",))
        left = GaugeMetricFamily(
            STORAGE_AVAILABLE,
            "Capacity the deployment declares, less the space used, in bytes.",
            labels=("component",),
        )
        declared = {
            "database": self.capacities.database,
            "object_storage": self.capacities.object_storage,
        }
        for component, size in used.items():
            taken.add_metric((component,), float(size))
            capacity = declared[component]
            if capacity is not None:
                left.add_metric((component,), float(max(capacity - size, 0)))
        yield taken
        yield left


def versions(announced: Mapping[str, str]) -> Metric:
    """Give the version of each component, in a label of a sample of value 1 (WF-CMP-0020)."""
    family = GaugeMetricFamily(
        COMPONENT_VERSION,
        "The version a component announces, in its label; always 1.",
        labels=("component", "version"),
    )
    for component, version in announced.items():
        family.add_metric((component, version), 1.0)
    return family


class Announced:
    """What a process that reads nothing of the platform announces of itself: its version."""

    def __init__(self, component: str, version: str) -> None:
        self.component = component
        self.version = version

    def collect(self) -> Iterator[Metric]:
        """Give the version of the process, as its component."""
        yield versions({self.component: self.version})


def _outcome_metrics(outcomes: Mapping[str, Outcome | None]) -> list[Metric]:
    success = GaugeMetricFamily(
        LAST_RUN_SUCCESS,
        "Whether the latest run of an operation the platform schedules succeeded (1) or not (0).",
        labels=("run",),
    )
    moment = GaugeMetricFamily(
        LAST_RUN_TIMESTAMP,
        "When the latest run of an operation the platform schedules ended, in Unix seconds.",
        labels=("run",),
    )
    for name, outcome in outcomes.items():
        if outcome is not None:
            success.add_metric((name,), 1.0 if outcome.succeeded else 0.0)
            moment.add_metric((name,), outcome.at.timestamp())
    return [success, moment]
