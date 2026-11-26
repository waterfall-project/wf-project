# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The components Waterfall requires, and the refusal of one that does not fit (WF-CMP-0020-A).

The specification asks for PostgreSQL in its major version 18, set for at least 1 024 locks per
transaction, Redis in a version at least 8, and Keycloak in a version at least 26. The tool that
saves the databases is the client of version 18, which refuses a server of a later major; the
restoration locks, in one transaction, one partition of each partitioned table per project, and
fails on the default of 64 locks from a few hundred projects. Redis Cluster is not supported: no
client of Waterfall speaks it (#4963).

Two places say so. The command ``waterfall-check-components`` (``components_check``) runs before the
migrations of a deployment and refuses a component that does not fit. Each process that opens the
database — the API, the worker, the service of the restoration — runs ``database_accepted`` at its
start, and stops there, naming the cause, on a server of the wrong major version or set for fewer
locks. A server that does not answer is not judged: the process says so and goes on, as it does
when the database goes away after it started.
"""

import sys
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from collections.abc import Mapping

    from waterfall.platform.database import Database

# The major version of PostgreSQL that Waterfall requires, and the locks per transaction it needs.
POSTGRESQL_MAJOR = 18
POSTGRESQL_LOCKS = 1024
# The least versions of Redis and of Keycloak (majors) that Waterfall requires.
REDIS_MAJOR = 8
KEYCLOAK_MAJOR = 26
# ``server_version_num`` of PostgreSQL from 10 on: the major version times 10 000, then the minor.
MAJOR_STEP = 10_000

logger = get_logger(__name__)


def major_of(version: str) -> int | None:
    """Read the major version of a version as Redis and Keycloak write it, ``8.2.1``; else none."""
    head = version.strip().partition(".")[0]
    return int(head) if head.isascii() and head.isdigit() else None


def database_faults(version_number: int, locks: int) -> list[str]:
    """Say why a PostgreSQL does not fit, by its ``server_version_num`` and its locks."""
    faults: list[str] = []
    major = version_number // MAJOR_STEP
    if major != POSTGRESQL_MAJOR:
        faults.append(
            f"PostgreSQL {major} is not the major version {POSTGRESQL_MAJOR} Waterfall requires"
        )
    if locks < POSTGRESQL_LOCKS:
        faults.append(
            f"PostgreSQL is set for {locks} locks per transaction (max_locks_per_transaction), "
            f"fewer than the {POSTGRESQL_LOCKS} that Waterfall requires"
        )
    return faults


def redis_faults(information: Mapping[str, object]) -> list[str]:
    """Say why a Redis does not fit, by the fields of its ``INFO``: version and cluster mode."""
    faults: list[str] = []
    version = str(information.get("redis_version", ""))
    major = major_of(version)
    if major is None:
        faults.append(f"the version of Redis, {version or 'not announced'}, cannot be read")
    elif major < REDIS_MAJOR:
        faults.append(
            f"Redis {version} is older than the version {REDIS_MAJOR} that Waterfall requires"
        )
    if str(information.get("cluster_enabled", 0)) == "1":
        faults.append(
            "Redis runs in cluster mode (cluster_enabled:1), which Waterfall does not support: "
            "give it a standalone Redis, with or without replicas"
        )
    return faults


def keycloak_faults(version: str | None) -> list[str]:
    """Say why a Keycloak does not fit, by the version it announces."""
    major = None if version is None else major_of(version)
    if major is None:
        return [f"the version of Keycloak, {version or 'not announced'}, cannot be read"]
    if major < KEYCLOAK_MAJOR:
        return [
            f"Keycloak {version} is older than the version {KEYCLOAK_MAJOR} that Waterfall requires"
        ]
    return []


def database_state(database: Database) -> tuple[int, int]:
    """Read ``server_version_num`` and ``max_locks_per_transaction`` of the server of a database."""
    with database.transaction() as session:
        row = session.execute(
            select(
                func.current_setting("server_version_num"),
                func.current_setting("max_locks_per_transaction"),
            )
        ).one()
    return int(row[0]), int(row[1])


def database_accepted(database: Database, name: str) -> bool:
    """Tell whether a process ``name`` may start on its database; say why not, on its error output.

    Refused for a server of another major version than 18 or set for fewer than 1 024 locks per
    transaction, naming each cause. A server out of reach is not judged here: it is logged, and the
    process starts as it would, since the database may come back.
    """
    try:
        version_number, locks = database_state(database)
    except OperationalError:
        logger.warning("database.not_checked", reason="unreachable")
        return True
    faults = database_faults(version_number, locks)
    for fault in faults:
        sys.stderr.write(f"{name}: {fault} (WF-CMP-0020)\n")
    return not faults
