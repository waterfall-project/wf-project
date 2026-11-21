# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Entry point of the service of the restoration, ``waterfall-restore`` (WF-ADM-0160, #953).

It runs the restorations of their stream until it is stopped, and stops at start, naming the
variable that lacks, rather than starting without its settings (WF-SEC-0010). ``waterfall-restore
test`` runs the test of a restoration beside an ephemeral platform, once (WF-EXP-0060, US-2930,
``waterfall.restore.trial``): 0 if it succeeded, 1 if it failed or could not run, 2 if a setting
lacks.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from waterfall import __version__
from waterfall.migrations.runner import upgrade
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.keycloak import Keycloak as KeycloakClient
from waterfall.platform.keycloak_admin import INSTALLATION_CLIENT, KeycloakAdmin
from waterfall.platform.logs import PLATFORM, configure_logging, get_logger, logging_context
from waterfall.platform.maintenance import Maintenance
from waterfall.platform.queue import WORKER_TIMEOUT, TaskQueue
from waterfall.platform.settings import (
    RestoreSettings,
    RestoreTestSettings,
    SettingsError,
    load_restore_settings,
    load_restore_test_settings,
)
from waterfall.platform.storage import Bucket
from waterfall.restore.provider import Keycloak, RealmRequests
from waterfall.restore.runner import Restorer
from waterfall.restore.task import RestoreTask
from waterfall.restore.trial import Ephemeral, Readiness, RestoreTrial
from waterfall.worker.backup import DATABASES
from waterfall.worker.main import serve

if TYPE_CHECKING:
    from collections.abc import Sequence

NAME = "waterfall-restore"
USAGE = f"usage: {NAME} [--version | test]\n"

logger = get_logger(__name__)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the service, or say why not; a wrong argument returns 2."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if arguments == ["test"]:
        return restore_test()
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
        return serve(Restorer(database, queue, restoration(settings, database, queue)))
    finally:
        queue.close()
        database.dispose()


def restoration(settings: RestoreSettings, database: Database, queue: TaskQueue) -> RestoreTask:
    """Restore into the databases the settings name, as their owners, from the bucket of backups.

    The maintenance is held in ``database``, that of Waterfall as its owner.
    """
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
        Maintenance.of(database, queue),
        provider,
        upgrade,
    )


def restore_test() -> int:
    """Run the test of a restoration once, under a correlation of its own; say why it could not.

    An error it does not expect — the production out of reach — ends it (1), said in the logs.
    """
    try:
        settings = load_restore_test_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    configure_logging(settings.log_level, secrets=settings.secret_values())
    production = Database(create_database_engine(settings.database_url.get_secret_value()))
    try:
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            logger.info("restore_test.starting", version=__version__)
            try:
                return 0 if trial(settings, production)() else 1
            except Exception:
                logger.exception("restore_test.not_run")
                return 1
    finally:
        production.dispose()


def trial(settings: RestoreTestSettings, production: Database) -> RestoreTrial:
    """Test the latest backup of the production on the ephemeral platform the settings name.

    The databases of the ephemeral platform are reached as their owners; its API, at its address.
    The file ``restored`` is written once they are restored, which the platform waits for to start.
    """
    owners = (settings.restore_test_database_url, settings.restore_test_keycloak_database_url)
    addresses = (address.get_secret_value() for address in owners)
    restored = Path(settings.restore_test_restored_file)
    roots = settings.restore_test_authority or settings.tls_authority
    ephemeral = Ephemeral(
        dict(zip(DATABASES, addresses, strict=True)),
        upgrade,
        restored.touch,
        Readiness.of(settings.restore_test_api_address, roots, settings.restore_test_patience),
    )
    return RestoreTrial(production, Bucket.of_backups(settings), ephemeral, settings.keycloak_realm)


if __name__ == "__main__":
    sys.exit(main())
