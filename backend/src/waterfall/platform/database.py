# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database: the naming of constraints, the types every table shares, the sessions.

SQLAlchemy 2 with synchronous sessions, over psycopg 3. A request is one transaction
(``Database.transaction``): it commits when the block ends and rolls back when it raises. A task
that reads a whole structure to turn it into a file or a report reads it in a transaction of its
own, frozen (``frozen_reading``). A text
a table sorts is compared code point by code point, and a search ignores case and accents
(contract, README; sql.md, "Trier et chercher un texte"): both are said here once.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from psycopg import OperationalError as DriverOperationalError
from psycopg.errors import UniqueViolation
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    ColumnElement,
    DateTime,
    Engine,
    MetaData,
    SQLColumnExpression,
    Table,
    Text,
    Uuid,
    any_,
    bindparam,
    column,
    create_engine,
    func,
    literal,
)
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable, Mapping
    from uuid import UUID

    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.sql.selectable import TableValuedAlias

# The name of every constraint and index, declared once: a migration that writes none gets
# these, and the tables the code declares get them too, so the two cannot drift apart.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


# The key, in the ``info`` of a table, of the values of the one row the migrations write and the
# service then changes — a schedule (EP-13) —: the tests, which empty every other table after each,
# write that row back at these values.
SHIPPED_ROW = "shipped_row"

# The collation of a text a table sorts: the order of the code points, accents and case included.
CODE_POINTS = "C"
# The collation a search lowers a text in: one that knows every letter, where ``C`` lowers the
# ASCII ones alone.
EVERY_LETTER = "und-x-icu"


def folded(text: SQLColumnExpression[str | None]) -> ColumnElement[str]:
    """Give a text as a search compares it: transliterated by ``unaccent``, then lowered."""
    return func.lower(func.unaccent(text).collate(EVERY_LETTER))


def contains(text: SQLColumnExpression[str | None], searched: str) -> ColumnElement[bool]:
    """Tell whether a text holds the one searched, whatever their case and accents.

    By ``strpos`` and not ``LIKE``: a ``%`` or a ``_`` searched is a letter like another. A null
    text — the name of an anonymised account — holds nothing.
    """
    return func.strpos(folded(text), folded(literal(searched, Text))) > 0


def among(column: SQLColumnExpression[UUID | None], values: Iterable[UUID]) -> ColumnElement[bool]:
    """Tell whether an identifier is one of those named, given as one array parameter.

    The condition ``IN`` would ask, but whatever their number one parameter and one text: a list
    of thousands of identifiers — the lines of a structure — costs, each time, a text to render
    and a statement to parse on both sides, which a reading of a whole structure paid several
    times over (#3048).
    """
    return column == any_(bindparam(None, list(values), type_=ARRAY(Uuid())))


def copies(mapping: Mapping[UUID, UUID], name: str) -> TableValuedAlias:
    """Give identifiers and those of their copies as a table named ``name``: ``source``, ``copy``.

    Two array parameters, unnested side by side: a copy of thousands of rows is then one
    ``INSERT … SELECT`` that joins it, the rows never leaving the database, where sending them one
    by one cost the opening of a revision most of its ten seconds (US-2240, #3102).
    """
    return (
        func.unnest(
            bindparam(None, list(mapping), type_=ARRAY(Uuid())),
            bindparam(None, list(mapping.values()), type_=ARRAY(Uuid())),
        )
        .table_valued(column("source", Uuid()), column("copy", Uuid()))
        .render_derived(name=name)
    )


def copied_columns(
    table: Table, replaced: Mapping[str, ColumnElement[Any]]
) -> tuple[list[str], list[ColumnElement[Any]]]:
    """Give the columns of a table, and what a copy of its rows writes in each, for ``from_select``.

    Each column as it is, but those ``replaced`` names: a column added to the table later is copied
    too, without a word here.
    """
    names = [each.name for each in table.columns]
    return names, [replaced.get(name, table.c[name]) for name in names]


def unique_violated(error: IntegrityError) -> str | None:
    """Name the unique constraint or index a write broke, ``None`` if it broke another rule."""
    cause = error.orig
    return cause.diag.constraint_name if isinstance(cause, UniqueViolation) else None


def bounded(column: str, longest: int) -> tuple[CheckConstraint, CheckConstraint]:
    """Bound a text from 1 to ``longest`` characters, and refuse it blank: a code, a label."""
    return (
        CheckConstraint(f"char_length({column}) BETWEEN 1 AND {longest}", name=f"{column}_length"),
        CheckConstraint(f"{column} ~ '\\S'", name=f"{column}_not_blank"),
    )


def counted() -> CheckConstraint:
    """Refuse a negative counter of the writes: a constraint of each table that has one."""
    return CheckConstraint("lock_version >= 0", name="lock_version_not_negative")


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


# The reserve of connections of a process, fifteen in all (deploy/compose/README.md, « Les
# processus de l'API »): five kept and eight more while they are all taken, for the requests; two
# for what observes the platform (``create_observation_engine``): a slow reading of the state does
# not make a request of availability fail. The calculation of
# ``max_connections`` counts fifteen per process.
POOL_SIZE = 5
POOL_OVERFLOW = 8
OBSERVATION_CONNECTIONS = 2
CONNECTIONS_PER_ENGINE = POOL_SIZE + POOL_OVERFLOW + OBSERVATION_CONNECTIONS
# How long what observes the platform waits for a connection to open or to be lent, in whole
# seconds: a pool of the requests saturated must not make the database look down.
OBSERVATION_SECONDS = 3
# The seconds a connection to the server may take, libpq's shortest: a server that answers no more
# holds its caller, the probe of liveness first, for that long and not for ever.
CONNECT_TIMEOUT = 2
# How long a request waits for a connection of its pool to be lent: no longer than a connection
# takes to open, so that the probe of liveness, which reads the maintenance through that pool, says
# so within what the healthcheck waits when the pool is spent (#4189). The bound is the one of the
# engine ``create_database_engine`` makes — the worker's, the restoration's, the bootstrap's, the
# witness's, the migrations' —, a choice kept on purpose: a burst that holds the reserve longer
# than this is a database refused naming ``database`` (``is_unreachable``), not a request that
# waits thirty seconds behind it.
POOL_TIMEOUT = CONNECT_TIMEOUT


# The SQLSTATE of a server that does not answer: a connection exception (class 08) and the shutdown
# or the start of the server (57P01 to 57P03). A statement the server judged — a lock refused, a
# deadlock, a statement cancelled — has another, and is not the database out of reach. So does 53300
# (too many connections): the server answers and refuses, it is full, not out of reach.
UNREACHABLE_STATES = frozenset({"57P01", "57P02", "57P03"})


def is_unreachable(error: BaseException) -> bool:
    """Tell whether an error is the database not answering, rather than a statement it refused.

    A connection that fails to open or is lost — the driver says none of the SQLSTATE of a statement
    refused —, a server that shuts down or starts, a pool whose every connection stays taken past
    ``POOL_TIMEOUT``: each is the component out of reach (WF-EXP-0040, §4.5.4, table 12), and a
    request that meets one is refused naming the database, not answered as an internal error.
    """
    seen: BaseException | None = error
    while seen is not None:
        if isinstance(seen, PoolTimeoutError):
            return True
        if isinstance(seen, DBAPIError):
            driver = seen.orig
            if seen.connection_invalidated:
                return True
            if isinstance(driver, DriverOperationalError):
                state = driver.sqlstate
                return state is None or state.startswith("08") or state in UNREACHABLE_STATES
            return False
        seen = seen.__cause__
    return False


def utc_now() -> datetime:
    """Read the clock, in universal time."""
    return datetime.now(UTC)


def engine_url(address: str) -> URL:
    """Give the SQLAlchemy URL for a database address: ``postgresql://`` means psycopg 3."""
    url = make_url(address)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    return url


def connect_timeout_of(url: URL) -> int:
    """Give the seconds a connection may take: the address's ``connect_timeout``, else the default.

    An operator who writes ``?connect_timeout=10`` in the address (TLS, a remote server) is
    obeyed, not overridden by ``CONNECT_TIMEOUT`` (#4190).
    """
    given = url.query.get("connect_timeout")
    if given is None:
        return CONNECT_TIMEOUT
    last = given if isinstance(given, str) else given[-1]
    # libpq reads zero as « without a bound » and ignores a negative or a non-number: none of them
    # may leave the connection unbounded, so each falls back to the default.
    try:
        seconds = int(last)
    except ValueError:
        return CONNECT_TIMEOUT
    return seconds if seconds > 0 else CONNECT_TIMEOUT


def create_database_engine(address: str) -> Engine:
    """Open the engine on the database, whose sessions keep time in universal time.

    Its reserve holds ``POOL_SIZE`` connections, and opens ``POOL_OVERFLOW`` more while they are
    all taken; with the two of the observation, ``CONNECTIONS_PER_ENGINE`` at most, which
    ``max_connections`` of the server carries for each process of the platform (US-2230).
    """
    url = engine_url(address)
    return create_engine(
        url,
        connect_args={"options": "-c timezone=UTC", "connect_timeout": connect_timeout_of(url)},
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=POOL_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
    )


def create_observation_engine(url: URL) -> Engine:
    """Open an engine of two connections, apart from the pool of the requests, on the same database.

    What observes the platform — the probe of the database, the reading of its state at a
    collection — must answer when every connection of the requests is taken: it waits
    ``OBSERVATION_SECONDS`` at most, for a connection to open or to be lent, then fails. Its
    connection is the ``OBSERVATION_CONNECTIONS`` of ``CONNECTIONS_PER_ENGINE``.
    """
    return create_engine(
        url,
        connect_args={"options": "-c timezone=UTC", "connect_timeout": OBSERVATION_SECONDS},
        pool_pre_ping=True,
        pool_size=OBSERVATION_CONNECTIONS,
        max_overflow=0,
        pool_timeout=OBSERVATION_SECONDS,
    )


@contextmanager
def frozen_reading(session: Session) -> Generator[Session]:
    """Read beside ``session`` in a transaction of its own, frozen at its first read, read only.

    ``REPEATABLE READ``: every read sees the database as it stood at the first, whatever commits
    meanwhile — a link created between the reading of a tree and that of its links is not seen
    (#2679). A transaction already begun cannot change its isolation, and the worker's, which ends
    the task, writes a row the attempt committed after its first read, which a frozen one would
    refuse: the reading takes a connection of its own, rolled back at the end of the block. It
    sees nothing ``session`` has not committed.
    """
    bind = session.get_bind()
    engine = bind if isinstance(bind, Engine) else bind.engine
    frozen = engine.connect().execution_options(
        isolation_level="REPEATABLE READ", postgresql_readonly=True
    )
    with frozen, Session(frozen) as reading:
        yield reading


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
