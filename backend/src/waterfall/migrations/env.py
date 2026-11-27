# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The environment Alembic runs the migrations in.

The migrations are written by hand: this file gives them the naming convention of the
constraints, the connection, and a lock so that two instances starting together do not apply
the same migration twice. It never imports the tables of a module, which are private to it.
"""

import logging
import time

from alembic import context
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql import text

from waterfall import schema
from waterfall.platform.database import create_database_engine
from waterfall.platform.settings import load_platform_settings

logger = logging.getLogger(__name__)

# One number for the whole history: the key of the advisory lock of a migration run.
MIGRATION_LOCK = 7_240_330
# The pause between two tries of that lock, while another instance migrates.
LOCK_RETRY_SECONDS = 0.2


def take_lock(connection: Connection) -> None:
    """Take the lock of a migration run, waiting for it out of any transaction.

    A lock of the session, not of the transaction: Alembic may commit between two steps, and the
    lock must hold until the last migration is written. It is tried, not awaited by
    ``pg_advisory_lock``: an instance that waited in that statement would hold its snapshot all the
    while, and an index created ``CONCURRENTLY`` (``0056``) by the instance that holds the lock
    waits for every older snapshot of the database — each would wait for the other, a deadlock.
    """
    while True:
        held = connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": MIGRATION_LOCK}
        ).scalar_one()
        connection.commit()
        if held:
            return
        logger.warning(
            "migration lock refused: advisory lock %s held by another instance, "
            "step %s, retrying in %ss",
            MIGRATION_LOCK,
            "lock of the migration run",
            LOCK_RETRY_SECONDS,
        )
        time.sleep(LOCK_RETRY_SECONDS)


def run_migrations(connection: Connection) -> None:
    """Apply the pending migrations, alone, and commit them."""
    take_lock(connection)
    try:
        context.configure(connection=connection, target_metadata=schema.declared())
        with context.begin_transaction():
            context.run_migrations()
        connection.commit()
    finally:
        connection.rollback()
        connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
        connection.commit()


def run() -> None:
    """Run on the engine a caller gave, or on the database the settings designate."""
    given = context.config.attributes.get("engine")
    engine = (
        given
        if isinstance(given, Engine)
        else create_database_engine(load_platform_settings().database_url.get_secret_value())
    )
    with engine.connect() as connection:
        run_migrations(connection)
    if engine is not given:
        engine.dispose()


if context.is_offline_mode():
    message = "the migrations run against a database, never as a script"
    raise RuntimeError(message)
run()
