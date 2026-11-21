# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the backups share: a worker that runs them, and a bucket that damages them.

And what stands for the database of the identity provider: the tables of Keycloak a backup reads,
its realms and its accounts, reduced to the columns it reads (US-2930).
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import text

from waterfall.platform.storage import Bucket
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from uuid import UUID

    from sqlalchemy import Connection

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue
    from waterfall.worker.backup import BackupTask


type Run = Callable[[BackupTask], UUID]


def worker_of(database: Database, queue: TaskQueue, taking: BackupTask) -> Worker:
    """Give a worker of the queue of the test that runs the backups."""
    queue.prepare()
    return Worker(database, queue, {"backup": taking}, "worker-backup", Timing(0, 0.1))


class Corrupting(Bucket):
    """A bucket that gives back every object with bytes of its middle overwritten."""

    def download(self, key: str, path: Path) -> None:
        super().download(key, path)
        damaged = bytearray(path.read_bytes())
        middle = len(damaged) // 2
        damaged[middle : middle + 16] = b"\xff" * 16
        path.write_bytes(bytes(damaged))


def stand_in_realm(connection: Connection, accounts: int = 0) -> None:
    """Make the realm of the installation and its accounts as Keycloak keeps them, a few columns.

    ``accounts`` are the people of the realm; an account of service is added, which none counts.
    """
    connection.execute(text("CREATE TABLE realm (id text PRIMARY KEY, name text)"))
    connection.execute(text("INSERT INTO realm VALUES ('waterfall', 'waterfall')"))
    connection.execute(
        text(
            "CREATE TABLE user_entity (id text PRIMARY KEY, realm_id text NOT NULL, "
            "service_account_client_link text)"
        )
    )
    add_accounts(connection, accounts)
    connection.execute(
        text("INSERT INTO user_entity VALUES (:id, 'waterfall', 'client')"), {"id": str(uuid4())}
    )


def add_accounts(connection: Connection, accounts: int) -> None:
    """Add people to the realm of the installation."""
    for _ in range(accounts):
        connection.execute(
            text("INSERT INTO user_entity VALUES (:id, 'waterfall', NULL)"), {"id": str(uuid4())}
        )
