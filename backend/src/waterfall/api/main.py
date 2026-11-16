# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the API service."""

import sys
from typing import TYPE_CHECKING

import uvicorn

from waterfall import __version__
from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.cache import IndicatorsCache
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import configure_logging, get_logger
from waterfall.platform.maintenance import Maintenance
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.settings import SettingsError, load_service_settings
from waterfall.platform.storage import Bucket

if TYPE_CHECKING:
    from collections.abc import Sequence

NAME = "waterfall-api"


def main(argv: Sequence[str] | None = None) -> int:
    """Start the API service, or say why it cannot start (WF-SEC-0010).

    The service takes no argument but ``--version``: any other one is refused with status 2, but
    ``install``, which ``waterfall.bootstrap`` takes before it (US-0420), and ``load-witness``,
    which ``waterfall.witness`` takes before them both (EP-05).
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
        settings = load_service_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    get_logger(__name__).info(
        "service.starting", version=__version__, host=settings.host, port=settings.port
    )
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    TIME_ZONE.read_from(stored_in(database))
    keycloak = Keycloak(settings)
    queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=DEPOSIT_TIMEOUT)
    administration = KeycloakAdmin(keycloak, settings)
    backups = Bucket.of_backups(settings)
    # The cache of the indicators of the day, in the Redis of the queue, its entries valid for the
    # time the settings read (WATERFALL_INDICATORS_CACHE_TTL); its pool is its own (US-1720/L2).
    cache = IndicatorsCache.of(queue, settings.indicators_cache_ttl)
    services = Services(
        database, keycloak, administration, queue, backups, Maintenance.of(queue), cache
    )
    try:
        uvicorn.run(
            create_app(services),
            host=settings.host,
            port=settings.port,
            log_config=None,
            access_log=False,
        )
    finally:
        cache.close()
        queue.close()
        keycloak.close()
        database.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
