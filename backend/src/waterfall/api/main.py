# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the API service, and the factory of its application, once per process.

uvicorn serves the application on ``WATERFALL_API_PROCESSES`` processes (US-2230), one by default:
each builds its own by ``application``, which opens its services — the database, Keycloak, Redis,
the storage — and closes them when the process stops. What a process keeps in memory between two
requests is the same in every process, or lives in PostgreSQL or Redis (WF-ARC-0080):

- the keys of the realm (``platform.keycloak``), a copy of Keycloak's that each process reads
  again on a key it does not hold and once they are as old as an access token;
- the token of the service account (``platform.keycloak_admin``), each process's own, which the
  realm gives to any of them;
- the time zone of the installation (``platform.installation``), fixed by the bootstrap;
- the registries of the modules (``platform.registry``), filled at the import of their interface;
- what the image holds, read once: the font of the images of a tree, the names of the time zones;
- the maintenance of a restoration lives in PostgreSQL, read at each request
  (``platform.maintenance``);
- the indicators of the day are cached in Redis, not in the process (``platform.cache``);
- the counters of the metrics, in a folder the processes share when there are several, which the
  exposition of any of them merges (``platform.metrics``, WF-OBS-0010).
"""

import sys
from contextlib import ExitStack, asynccontextmanager, nullcontext
from typing import TYPE_CHECKING, cast

import uvicorn

from waterfall import __version__
from waterfall.api.app import PREFIX, create_app
from waterfall.api.authentication import Services
from waterfall.platform.cache import IndicatorsCache
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import configure_logging, get_logger
from waterfall.platform.maintenance import Maintenance
from waterfall.platform.metrics import Capacities, shared_between_processes
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.settings import SettingsError, load_api_settings
from waterfall.platform.storage import Bucket

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Sequence

    from fastapi import FastAPI

    from waterfall.api.system import Observed
    from waterfall.platform.settings import ServiceSettings

NAME = "waterfall-api"
# Where uvicorn finds the factory, in each of its processes.
FACTORY = "waterfall.api.main:application"

logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Start the API service, or say why it cannot start (WF-SEC-0010).

    The service takes no argument but ``--version``: any other one is refused with status 2, but
    ``install``, which ``waterfall.bootstrap`` takes before it (US-0420), and ``load-witness``,
    which ``waterfall.witness`` takes before them both (EP-05). The settings are read here before
    any process starts, so that a missing one stops the service with status 2, naming it.
    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if arguments:
        sys.stderr.write(
            f"usage: {NAME} [--version | install | load-witness]\n"
            f"{NAME}: unexpected argument: {arguments[0]}\n"
        )
        return 2
    try:
        settings = load_api_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    logger.info(
        "service.starting",
        version=__version__,
        host=settings.host,
        port=settings.port,
        processes=settings.api_processes,
    )
    # Several processes share their counters in a folder of their own (WF-OBS-0010); one keeps them.
    shared = shared_between_processes() if settings.api_processes > 1 else nullcontext()
    with shared:
        uvicorn.run(
            FACTORY,
            factory=True,
            workers=settings.api_processes,
            host=settings.host,
            port=settings.port,
            log_config=None,
            access_log=False,
            # In TLS alone when the settings give its certificate (US-2840, TFX-02).
            ssl_certfile=settings.tls_certificate,
            ssl_keyfile=settings.tls_key,
        )
    return 0


def application() -> FastAPI:
    """Build the application of one process, on services of its own, closed when it stops.

    Called by uvicorn in each of its processes: a process started apart reads its settings and
    sets its logs again, as the first did.
    """
    settings = load_api_settings()
    configure_logging(settings.log_level, secrets=settings.secret_values())
    services, opened = open_services(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        try:
            with ExitStack() as served:
                served.callback(opened.close)
                if settings.metrics_port is not None:
                    served.callback(serve_metrics(app, settings.host, settings.metrics_port))
                yield
        finally:
            logger.info("service.stopped")

    capacities = Capacities(settings.database_capacity_bytes, settings.storage_capacity_bytes)
    return create_app(services, lifespan, capacities)


def serve_metrics(app: FastAPI, host: str, port: int) -> Callable[[], None]:
    """Serve ``getMetrics`` of an application over HTTP on a port of its own; give what stops it.

    The API serving in TLS (US-2840), its metrics stay in HTTP, on a port neither the door nor the
    ingress routes (TFX-09), at the path of the operation: the same exposition, and nothing else.
    """
    observed = cast("Observed", app.state.observed)
    return observed.registry.serve_shared(host, port, f"{PREFIX}/metrics")


def open_services(settings: ServiceSettings) -> tuple[Services, ExitStack]:
    """Open the services of a process, and give what closes them, the last opened first.

    Nothing is reached yet: the database, Keycloak, Redis and the storage are asked when a request
    needs them.
    A service that cannot be opened closes those opened before it. The time zone of the
    installation is read, the first time a request needs it, from this database (US-2200).
    """
    with ExitStack() as opened:
        database = Database(create_database_engine(settings.database_url.get_secret_value()))
        opened.callback(database.dispose)
        keycloak = Keycloak(settings)
        opened.callback(keycloak.close)
        queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=DEPOSIT_TIMEOUT)
        opened.callback(queue.close)
        backups = Bucket.of_backups(settings)
        opened.callback(backups.client.close)
        # The cache of the indicators of the day, in the Redis of the queue, its entries valid for
        # the time the settings read (WATERFALL_INDICATORS_CACHE_TTL); its pool is its own
        # (US-1720/L2).
        cache = IndicatorsCache.of(queue, settings.indicators_cache_ttl)
        opened.callback(cache.close)
        services = Services(
            database,
            keycloak,
            KeycloakAdmin(keycloak, settings),
            queue,
            backups,
            Maintenance.of(database, queue),
            cache,
        )
        TIME_ZONE.read_from(stored_in(database))
        return services, opened.pop_all()


if __name__ == "__main__":
    sys.exit(main())
