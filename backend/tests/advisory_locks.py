# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the locks of the backups share: a transaction seen waiting for a lock.

``pg_locks`` is read for the lock of one key, in the database of the test alone: the workers of
xdist share the instance, and a migration waits on a lock of its own (#4357). Waiting is proved by
what PostgreSQL says, never by a pause.
"""

import threading
from typing import TYPE_CHECKING

from sqlalchemy import text

if TYPE_CHECKING:
    from waterfall.platform.database import Database

# How many transactions wait for the advisory lock of a key, in this database.
WAITING = text(
    "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted "
    "AND database = (SELECT oid FROM pg_database WHERE datname = current_database()) "
    "AND (classid::bigint << 32) | objid::bigint = :key"
)
WITHIN = 10.0


def waits_for(database: Database, key: int, within: float = WITHIN) -> bool:
    """Tell whether a transaction waits for the advisory lock of a key, within a bound."""
    pause = threading.Event()
    for _ in range(int(within * 20)):
        with database.engine.connect() as connection:
            if connection.scalar(WAITING, {"key": key}):
                return True
        pause.wait(0.05)
    return False
