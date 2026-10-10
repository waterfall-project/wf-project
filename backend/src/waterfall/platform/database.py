# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database: the naming of constraints, the types every table shares, the sessions.

SQLAlchemy 2 with synchronous sessions, over psycopg 3. A request is one transaction
(``Database.transaction``): it commits when the block ends and rolls back when it raises.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Engine, MetaData, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

# The name of every constraint and index, declared once: a migration that writes none gets
# these, and the tables the code declares get them too, so the two cannot drift apart.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """The base of the tables of every module of the core."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UtcDateTime(TypeDecorator[datetime]):
    """A ``timestamptz`` that is written and read in universal time (WF-DAT-0100).

    A moment without a zone is refused: it would be read as the local time of whoever sends it.
    A moment in another zone is the same moment, written and read back as universal time.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        """Convert to universal time, or refuse a moment that has no zone."""
        del dialect
        if value is None:
            return None
        if value.tzinfo is None:
            message = "a moment without a time zone cannot be stored"
            raise ValueError(message)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        """Give the moment back in universal time, whatever the zone of the session."""
        del dialect
        return None if value is None else value.astimezone(UTC)


def utc_now() -> datetime:
    """Read the clock, in universal time."""
    return datetime.now(UTC)


def engine_url(address: str) -> URL:
    """Give the SQLAlchemy URL for a database address: ``postgresql://`` means psycopg 3."""
    url = make_url(address)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


def create_database_engine(address: str) -> Engine:
    """Open the engine on the database, whose sessions keep time in universal time."""
    return create_engine(
        engine_url(address), connect_args={"options": "-c timezone=UTC"}, pool_pre_ping=True
    )


class Database:
    """The engine of a process and the sessions it hands out."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._sessions = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def transaction(self) -> Generator[Session]:
        """Run a block in one transaction: commit at its end, roll back if it raises."""
        with self._sessions() as session, session.begin():
            yield session

    def dispose(self) -> None:
        """Close the connections."""
        self.engine.dispose()
