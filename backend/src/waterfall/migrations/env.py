# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The environment Alembic runs the migrations in.

The migrations are written by hand: this file gives them the naming convention of the
constraints, the connection, and a lock so that two instances starting together do not apply
the same migration twice. It never imports the tables of a module, which are private to it.
"""

from alembic import context
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql import text

from waterfall.platform.database import Base, create_database_engine
from waterfall.platform.settings import load_settings

# One number for the whole history: the key of the advisory lock of a migration run.
MIGRATION_LOCK = 7_240_330


def run_migrations(connection: Connection) -> None:
    """Apply the pending migrations, alone, and commit them."""
    # A lock of the session, not of the transaction: Alembic may commit between two steps, and
    # the lock must hold until the last migration is written.
    connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
    connection.commit()
    try:
        context.configure(connection=connection, target_metadata=Base.metadata)
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
        else create_database_engine(load_settings().database_url.get_secret_value())
    )
    with engine.connect() as connection:
        run_migrations(connection)
    if engine is not given:
        engine.dispose()


if context.is_offline_mode():
    message = "the migrations run against a database, never as a script"
    raise RuntimeError(message)
run()
