# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the service of the restoration, ``waterfall-restore`` (WF-ADM-0160, #953).

It runs the restorations of their stream until it is stopped, and stops at start, naming the
variable that lacks, rather than starting without its settings (WF-SEC-0010).
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from waterfall import __version__
from waterfall.migrations.runner import upgrade
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.keycloak import Keycloak as KeycloakClient
from waterfall.platform.keycloak_admin import INSTALLATION_CLIENT, KeycloakAdmin
from waterfall.platform.logs import configure_logging, get_logger
from waterfall.platform.maintenance import Maintenance
from waterfall.platform.queue import WORKER_TIMEOUT, TaskQueue
from waterfall.platform.settings import RestoreSettings, SettingsError, load_restore_settings
from waterfall.platform.storage import Bucket
from waterfall.restore.provider import Keycloak, RealmRequests
from waterfall.restore.runner import Restorer
from waterfall.restore.task import RestoreTask
from waterfall.worker.backup import DATABASES
from waterfall.worker.main import serve

NAME = "waterfall-restore"
USAGE = f"usage: {NAME} [--version]\n"

logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the service, or say why not; a wrong argument returns 2."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if arguments:
        sys.stderr.write(f"{USAGE}{NAME}: unexpected arguments: {' '.join(arguments)}\n")
        return 2
    try:
        settings = load_restore_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    logger.info("restore.starting", version=__version__)
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    queue = TaskQueue.connect(settings.redis_url.get_secret_value(), timeout=WORKER_TIMEOUT)
    try:
        return serve(Restorer(database, queue, restoration(settings, queue)))
    finally:
        queue.close()
        database.dispose()


def restoration(settings: RestoreSettings, queue: TaskQueue) -> RestoreTask:
    """Restore into the databases the settings name, as their owners, from the bucket of backups."""
    owners = (settings.database_url, settings.keycloak_database_url)
    addresses = (address.get_secret_value() for address in owners)
    keycloak = KeycloakClient(settings)
    installation = (INSTALLATION_CLIENT, settings.installation_client_secret)
    provider = Keycloak(
        KeycloakAdmin(keycloak, settings),
        KeycloakAdmin(keycloak, settings, client=installation),
        RealmRequests(Path(settings.realm_requests)),
    )
    return RestoreTask(
        dict(zip(DATABASES, addresses, strict=True)),
        Bucket.of_backups(settings),
        Maintenance.of(queue),
        provider,
        upgrade,
    )


if __name__ == "__main__":
    sys.exit(main())
