# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``waterfall-check-components``: the components of a deployment, checked before its migrations.

The Compose of production runs it before ``waterfall-migrate`` and goes no further when it fails
(WF-CMP-0020-A: « Le déploiement échoue en le disant si un composant est d'une version antérieure à
celle exigée »). It reads the version of PostgreSQL, of Redis and of Keycloak, and refuses one that
is older than the version required, a PostgreSQL of another major version than 18 or set for fewer
than 1 024 locks per transaction (the rule of the start of each process, ``components``), and a
Redis in cluster mode. It says every cause it finds, not the first alone, and what it read when all
fit. Status 0 when they fit, 1 when one does not, or does not answer, 2 for a setting that lacks.

Keycloak announces its version to the service account of its realm, through its extension
(``KeycloakAdmin.server_version``): the command holds no password of the administrator of
``master``. It runs once the realm is applied, which creates that account and its role.
"""

import sys
from typing import TYPE_CHECKING, cast

import httpx2
import redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from waterfall import __version__
from waterfall.platform.components import (
    database_faults,
    database_state,
    keycloak_faults,
    redis_faults,
)
from waterfall.platform.database import Database, create_database_engine
from waterfall.platform.keycloak import IdentityProviderError, Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.settings import ComponentsSettings, SettingsError, load_components_settings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from waterfall.platform.metrics import Described

NAME = "waterfall-check-components"
USAGE = f"usage: {NAME} [--version]\n"
# How long a component is waited for.
WAIT_SECONDS = 10.0


def check_database(settings: ComponentsSettings) -> tuple[str, list[str]]:
    """Read the state of PostgreSQL: what it is, and why it does not fit."""
    database: Database | None = None
    try:
        database = Database(create_database_engine(settings.database_url.get_secret_value()))
        version_number, locks = database_state(database)
    except SQLAlchemyError as error:
        return "PostgreSQL", [f"PostgreSQL does not answer: {type(error).__name__}"]
    finally:
        if database is not None:
            database.dispose()
    described = f"PostgreSQL {version_number // 10_000} ({locks} locks per transaction)"
    return described, database_faults(version_number, locks)


def check_redis(settings: ComponentsSettings) -> tuple[str, list[str]]:
    """Read the state of Redis: what it is, and why it does not fit."""
    client = None
    try:
        client = redis.from_url(
            settings.redis_url.get_secret_value(),
            decode_responses=True,
            socket_timeout=WAIT_SECONDS,
            socket_connect_timeout=WAIT_SECONDS,
        )
        described = cast("Described", client)
        information = {**described.info("server"), **described.info("cluster")}
    except (RedisError, ValueError) as error:
        return "Redis", [f"Redis does not answer: {type(error).__name__}"]
    finally:
        if client is not None:
            client.close()
    mode = "cluster" if str(information.get("cluster_enabled", 0)) == "1" else "standalone"
    return f"Redis {information.get('redis_version')} ({mode})", redis_faults(information)


def check_keycloak(settings: ComponentsSettings) -> tuple[str, list[str]]:
    """Read the version of Keycloak: what it is, and why it does not fit."""
    keycloak = Keycloak(settings, timeout=WAIT_SECONDS)
    try:
        version = KeycloakAdmin(keycloak, settings).server_version()
    except (IdentityProviderError, httpx2.HTTPError, KeyError, ValueError, TypeError) as error:
        return "Keycloak", [f"Keycloak does not answer as expected: {type(error).__name__}"]
    finally:
        keycloak.close()
    return f"Keycloak {version}", keycloak_faults(version)


def main(argv: Sequence[str] | None = None) -> int:
    """Check every component, and say what is wrong with those that do not fit."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--version"]:
        sys.stdout.write(f"{NAME} {__version__}\n")
        return 0
    if arguments:
        sys.stderr.write(f"{USAGE}{NAME}: unexpected arguments: {' '.join(arguments)}\n")
        return 2
    try:
        settings = load_components_settings()
    except SettingsError as error:
        sys.stderr.write(f"{NAME}: {error}\n")
        return 2
    found = [check_database(settings), check_redis(settings), check_keycloak(settings)]
    faults = [fault for _, component in found for fault in component]
    for fault in faults:
        sys.stderr.write(f"{NAME}: {fault} (WF-CMP-0020)\n")
    if faults:
        return 1
    sys.stdout.write(f"{NAME}: {', '.join(described for described, _ in found)}: all fit\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
