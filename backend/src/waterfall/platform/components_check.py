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

Keycloak announces its version to the administrator of its master realm alone
(``/admin/serverinfo``): the command signs in as that administrator, with the password of the
deployment, in ``admin-cli``.
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
from waterfall.platform.keycloak import trusted
from waterfall.platform.settings import ComponentsSettings, SettingsError, load_components_settings

if TYPE_CHECKING:
    from collections.abc import Sequence

    from waterfall.platform.metrics import Described

NAME = "waterfall-check-components"
USAGE = f"usage: {NAME} [--version]\n"
# How long a component is waited for, and the client of the master realm that signs in by password.
WAIT_SECONDS = 10.0
ADMIN_CLIENT = "admin-cli"


def check_database(settings: ComponentsSettings) -> tuple[str, list[str]]:
    """Read the state of PostgreSQL: what it is, and why it does not fit."""
    database = Database(create_database_engine(settings.database_url.get_secret_value()))
    try:
        version_number, locks = database_state(database)
    except SQLAlchemyError as error:
        return "PostgreSQL", [f"PostgreSQL does not answer: {type(error).__name__}"]
    finally:
        database.dispose()
    described = f"PostgreSQL {version_number // 10_000} ({locks} locks per transaction)"
    return described, database_faults(version_number, locks)


def check_redis(settings: ComponentsSettings) -> tuple[str, list[str]]:
    """Read the state of Redis: what it is, and why it does not fit."""
    client = redis.from_url(
        settings.redis_url.get_secret_value(),
        decode_responses=True,
        socket_timeout=WAIT_SECONDS,
        socket_connect_timeout=WAIT_SECONDS,
    )
    described = cast("Described", client)
    try:
        information = {**described.info("server"), **described.info("cluster")}
    except RedisError as error:
        return "Redis", [f"Redis does not answer: {type(error).__name__}"]
    finally:
        client.close()
    mode = "cluster" if str(information.get("cluster_enabled", 0)) == "1" else "standalone"
    return f"Redis {information.get('redis_version')} ({mode})", redis_faults(information)


def keycloak_version(settings: ComponentsSettings) -> str | None:
    """Ask Keycloak its version as the administrator of its master realm; none if it says none."""
    base = (settings.keycloak_backchannel or settings.keycloak_address).rstrip("/")
    with httpx2.Client(
        base_url=base, timeout=WAIT_SECONDS, verify=trusted(settings.tls_authority)
    ) as http:
        token = http.post(
            "/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": ADMIN_CLIENT,
                "username": settings.keycloak_admin_user,
                "password": settings.keycloak_admin_password.get_secret_value(),
            },
        )
        token.raise_for_status()
        granted = {"Authorization": f"Bearer {token.json()['access_token']}"}
        information = http.get("/admin/serverinfo", headers=granted)
        information.raise_for_status()
        version = information.json().get("systemInfo", {}).get("version")
    return None if version is None else str(version)


def check_keycloak(settings: ComponentsSettings) -> tuple[str, list[str]]:
    """Read the version of Keycloak: what it is, and why it does not fit."""
    try:
        version = keycloak_version(settings)
    except (httpx2.HTTPError, KeyError, ValueError) as error:
        return "Keycloak", [f"Keycloak does not answer as expected: {type(error).__name__}"]
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
