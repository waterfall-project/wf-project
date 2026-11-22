# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The maintenance of a restoration, kept out of what the restoration replaces (#604, #956).

While a restoration replaces the databases, the platform is in maintenance: the API answers every
operation but its probe of liveness with 503, and the worker runs no task. The maintenance and the
state of the restoration that holds it live in the schema ``platform`` of the database of
Waterfall, beside ``public``: a backup dumps ``public`` alone, and a restoration replaces it alone,
so both survive the replacement (WF-ARC-0090). The service of the restoration sets them before it
touches a database, reads them to take up a restoration whose row the database no longer holds —
replaced, or not yet written back —, and removes them last. Redis holds none of it: emptied during a
restoration, it lifts nothing (#956).

Each table holds one row at most. The role of the service reads them, which the API and the worker
do; the owner alone writes them, which the service of the restoration is. Each reading and each
writing is a transaction of its own, committed at once: the API and the worker see a maintenance as
soon as it is held, whatever the transaction of the restoration holds open meanwhile. The sessions
of the front, which Redis keeps under keys of its own, are closed by deleting them.

The maintenance is read at the entry of a request, which a write admitted just before it is held
has passed already. The lock of the drain closes that gap (#2229, #1014): each transaction of the
API and of the worker takes it shared at its first write (``guard_writes``), then reads the
maintenance, and is refused if it is held; the service of the restoration takes it exclusively once
the maintenance is held, before it keeps anything (``drained``). Every write admitted before has
then committed, and none commits after: what the restoration keeps is all that was written, read
at one instant. A write never waits for the lock: it tries it, and a lock held or asked
exclusively is a restoration under way, which refuses the write as the maintenance does — two
transactions of one request, the first holding the lock, would otherwise wait for each other
unseen. The invariant of the minimal reference (``REFERENCE_LOCK``, #2301) holds by it as well: no
creation of a project, nor any of the writings that could empty the reference, commits once a
restoration has drained the writes, until it lifts the maintenance.

A restoration holds the maintenance for ``DEADLINE`` at most, from its first attempt (#1016).
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Self, cast
from uuid import UUID

from psycopg.errors import UndefinedTable
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    SmallInteger,
    Text,
    delete,
    event,
    func,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import Base, UtcDateTime, utc_now
from waterfall.platform.errors import UnavailableError

if TYPE_CHECKING:
    from collections.abc import Generator

    from redis import Redis
    from sqlalchemy import Connection, Engine
    from sqlalchemy.engine.interfaces import DBAPICursor

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

# The schema of what a restoration leaves in place (migration 0035).
SCHEMA = "platform"
# The key of the one row of each table.
THE_ROW = 1
# The keys under which the front keeps its sessions and its sign-ins (``frontend/src/session``).
FRONT_SESSIONS = "wf:*"
# Delete the keys a pattern matches, page by page, in Redis itself.
FORGET_SESSIONS = """
local cursor, deleted = "0", 0
repeat
    local page = redis.call("SCAN", cursor, "MATCH", ARGV[1], "COUNT", 500)
    cursor = page[1]
    for _, key in ipairs(page[2]) do deleted = deleted + redis.call("DEL", key) end
until cursor == "0"
return deleted
"""
# The key of the lock of the drain: shared by each write of the API and of the worker, exclusive by
# the restoration, between the maintenance held and what it keeps.
DRAIN_LOCK = 3_700_170
# The longest a restoration holds the platform in maintenance before it is given up: the delay of
# putting the platform back in service from a backup, a new platform deployed included
# (WF-EXP-0050).
DEADLINE = timedelta(hours=4)
# What a write refused in maintenance says: what the API answers in maintenance.
COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
REFUSED = {"component": "database"}
# Where a connection keeps how many savepoints its transaction is in, at which of them it took the
# lock of the drain, and whether its database has the table of the maintenance (``guard_writes``).
DEPTH = "waterfall.savepoints"
ADMITTED = "waterfall.drain_admitted"
PLATFORM_SEEN = "waterfall.platform_seen"
# The first words of the statements that write nothing: any other is taken for a write.
READING = frozenset(
    {
        "BEGIN",
        "CLOSE",
        "COMMIT",
        "DECLARE",
        "DISCARD",
        "EXPLAIN",
        "FETCH",
        "MOVE",
        "RELEASE",
        "RESET",
        "ROLLBACK",
        "SAVEPOINT",
        "SELECT",
        "SET",
        "SHOW",
        "START",
        "TABLE",
        "VALUES",
    }
)
# The statements of the admission of a write, run on a cursor of their own.
TRY_DRAIN = "SELECT pg_try_advisory_xact_lock_shared(%s)"
HAS_PLATFORM = "SELECT to_regclass('platform.maintenance') IS NOT NULL"
IS_HELD = "SELECT EXISTS (SELECT FROM platform.maintenance)"


class HeldMaintenance(Base):
    """The maintenance held: the task of the restoration that holds it."""

    __tablename__ = "maintenance"
    __table_args__ = (
        CheckConstraint(f"id = {THE_ROW}", name="single_row"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    # No foreign key: the row of the task is in ``public``, which the restoration replaces.
    task_id: Mapped[UUID] = mapped_column()


class RestorationState(Base):
    """Where the restoration that holds the maintenance stands: its task, its source, its step.

    ``payload`` is that of its task — the backup or the deposit restored, the date confirmed —, and
    the requester as they were named when it was asked; ``attempts``, ``caches_cleared`` and
    ``abandoned`` its step, ``held_at`` since when it holds the maintenance (``Restoring``).
    """

    __tablename__ = "restoration"
    __table_args__ = (
        CheckConstraint(f"id = {THE_ROW}", name="single_row"),
        CheckConstraint("attempts >= 1", name="attempts_positive"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_object"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    task_id: Mapped[UUID] = mapped_column()
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # No foreign key: the database restored may not hold the account.
    requested_by: Mapped[UUID | None] = mapped_column()
    correlation_id: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(SmallInteger)
    caches_cleared: Mapped[bool] = mapped_column(Boolean)
    abandoned: Mapped[bool] = mapped_column(Boolean)
    held_at: Mapped[datetime] = mapped_column(UtcDateTime, server_default=func.now())


@dataclass(frozen=True, slots=True)
class Restoring:
    """The task of the restoration that holds the platform in maintenance, and its attempts.

    ``caches_cleared`` once an attempt may have changed the databases — about to replace the first,
    or taking over what another restoration kept and never wrote back —: from then on, Keycloak may
    serve the realm of the backup, whose secrets are not the installation's, until the realm of the
    installation is applied again, whether the caches were cleared or Keycloak restarted alone
    (#1017); and the databases may no longer be the installation's. ``abandoned`` for a maintenance
    held without its state, or a restoration abandoned by a version that left it for an operator:
    nothing takes it up, its service gives it up (#1016). ``held_at`` since when it holds the
    maintenance, ``None`` until it is held: one held longer than ``DEADLINE`` is given up.
    """

    task_id: UUID
    payload: dict[str, Any]
    requested_by: UUID | None
    correlation_id: str
    attempts: int
    caches_cleared: bool = False
    abandoned: bool = False
    held_at: datetime | None = field(default=None, compare=False)

    def left(self, now: datetime) -> timedelta:
        """Give the time left before the deadline; all of it while the maintenance is not held."""
        return DEADLINE if self.held_at is None else self.held_at + DEADLINE - now

    def overdue(self, now: datetime) -> bool:
        """Tell whether the restoration has held the maintenance longer than its deadline."""
        return self.left(now) <= timedelta(0)


class MaintenanceHeldError(UnavailableError):
    """A write refused: a restoration holds the platform in maintenance (503)."""

    def __init__(self) -> None:
        super().__init__(COMPONENT_UNAVAILABLE, REFUSED)


class Maintenance:
    """The maintenance of the platform, as the service of the restoration sets and lifts it."""

    def __init__(self, database: Database, client: Redis, sessions: str = FRONT_SESSIONS) -> None:
        """Keep the maintenance in ``database``; close the sessions of the front in ``client``.

        ``database`` is reached as the owner by the service of the restoration, which writes, and
        as the role of the service by the API and the worker, which read.
        """
        self.database = database
        self.client = client
        self.sessions = sessions

    @classmethod
    def of(cls, database: Database, queue: TaskQueue, sessions: str = FRONT_SESSIONS) -> Self:
        """Keep the maintenance in a database, the sessions of the front in the Redis of a queue."""
        return cls(database, queue.client, sessions)

    def current(self) -> Restoring | None:
        """Give the restoration that holds the platform in maintenance, if one does.

        A database the migrations have not brought to the schema ``platform`` yet holds none: the
        code of a version runs on the schema of the one before for the time of an update
        (``docs/dev/sql.md``), and a restoration reads a backup of an earlier revision there.

        A maintenance held whose state is missing is still held: it is given as a restoration
        abandoned, which nothing takes up and which its service gives up, rather than as none,
        which would lift it unseen; its databases may have changed, for all it says.
        """
        held = select(HeldMaintenance.task_id, RestorationState).outerjoin(
            RestorationState, HeldMaintenance.task_id == RestorationState.task_id
        )
        try:
            with self.database.transaction() as session:
                row = session.execute(held).one_or_none()
        except ProgrammingError as error:
            if isinstance(error.orig, UndefinedTable):
                return None
            raise
        if row is None:
            return None
        task_id = row[0]
        # The outer join gives no state where the table of the states lacks the row.
        state = cast("RestorationState | None", row[1])
        if state is None:
            return Restoring(task_id, {}, None, "", 1, caches_cleared=True, abandoned=True)
        return Restoring(
            state.task_id,
            state.payload,
            state.requested_by,
            state.correlation_id,
            state.attempts,
            caches_cleared=state.caches_cleared,
            abandoned=state.abandoned,
            held_at=state.held_at,
        )

    def hold(self, restoring: Restoring) -> Restoring:
        """Put the platform in maintenance for a restoration, or say one more of its attempts.

        Gives what it holds: dated now if ``restoring`` is not dated yet, its first attempt.
        """
        held = restoring if restoring.held_at is not None else _dated(restoring)
        state = {
            "task_id": held.task_id,
            "payload": held.payload,
            "requested_by": held.requested_by,
            "correlation_id": held.correlation_id,
            "attempts": held.attempts,
            "caches_cleared": held.caches_cleared,
            "abandoned": held.abandoned,
            "held_at": held.held_at,
        }
        maintenance = insert(HeldMaintenance).values(id=THE_ROW, task_id=held.task_id)
        stated = insert(RestorationState).values(id=THE_ROW, **state)
        with self.database.transaction() as session:
            session.execute(
                maintenance.on_conflict_do_update(
                    index_elements=[HeldMaintenance.id], set_={"task_id": held.task_id}
                )
            )
            session.execute(
                stated.on_conflict_do_update(index_elements=[RestorationState.id], set_=state)
            )
        return held

    def lift(self) -> None:
        """End the maintenance: the platform serves its operations again."""
        with self.database.transaction() as session:
            session.execute(delete(RestorationState))
            session.execute(delete(HeldMaintenance))

    def close_front_sessions(self) -> int:
        """Delete every session and sign-in the front keeps, and say how many keys went."""
        return int(cast("int", self.client.eval(FORGET_SESSIONS, 0, self.sessions)))


def _dated(restoring: Restoring) -> Restoring:
    return Restoring(
        restoring.task_id,
        restoring.payload,
        restoring.requested_by,
        restoring.correlation_id,
        restoring.attempts,
        caches_cleared=restoring.caches_cleared,
        abandoned=restoring.abandoned,
        held_at=utc_now(),
    )


def guard_writes(engine: Engine) -> None:
    """Make each transaction of ``engine`` take the lock of the drain shared at its first write.

    For the API and the worker, which reach the database as the role of the service; never for the
    service of the restoration, whose writes are the maintenance itself. The first statement that
    may write (``writes``) tries the lock, then reads the maintenance: the lock not granted, or the
    maintenance held, the statement is refused (``MaintenanceHeldError``), and the transaction
    writes nothing more. The lock is held until the transaction ends, and tried again after the
    savepoint it was taken in is rolled back, which released it. The maintenance is read by a
    statement of its own, once the lock is granted: in ``READ COMMITTED``, the isolation of every
    transaction that writes here, it sees a maintenance held before the restoration asked for the
    lock. A database the migrations have not brought to the schema ``platform`` holds no
    maintenance.
    """
    event.listen(engine, "begin", _begun)
    event.listen(engine, "savepoint", _saved)
    event.listen(engine, "release_savepoint", _released)
    event.listen(engine, "rollback_savepoint", _rolled_back)
    event.listen(engine, "before_cursor_execute", _admit)


def _begun(connection: Connection) -> None:
    connection.info[DEPTH] = 0
    connection.info.pop(ADMITTED, None)


def _saved(connection: Connection, _name: str) -> None:
    connection.info[DEPTH] = connection.info.get(DEPTH, 0) + 1


def _released(connection: Connection, _name: str, _context: object) -> None:
    # The locks a savepoint released took pass to the one around it.
    depth = connection.info[DEPTH] = connection.info.get(DEPTH, 1) - 1
    if connection.info.get(ADMITTED, -1) > depth:
        connection.info[ADMITTED] = depth


def _rolled_back(connection: Connection, _name: str, _context: object) -> None:
    # The locks a savepoint rolled back took are released with it.
    depth = connection.info[DEPTH] = connection.info.get(DEPTH, 1) - 1
    if connection.info.get(ADMITTED, -1) > depth:
        connection.info.pop(ADMITTED)


def _admit(
    connection: Connection,
    _cursor: DBAPICursor,
    statement: str,
    _parameters: object,
    _context: object,
    _executemany: object,
) -> None:
    if ADMITTED in connection.info or not writes(statement):
        return
    _take_drain(connection)


def admitted(connection: Connection) -> bool:
    """Take the lock of the drain shared for the transaction, and tell whether it may write.

    As the first write does (``guard_writes``), but asked: ``False`` if the lock is not granted or
    the maintenance is held. What the worker asks once it holds the lock of a run, before it runs
    anything: a run admitted holds the lock until it ends.
    """
    try:
        _take_drain(connection)
    except MaintenanceHeldError:
        return False
    return True


def _take_drain(connection: Connection) -> None:
    dbapi = connection.connection.dbapi_connection
    if dbapi is None:
        return
    cursor = dbapi.cursor()
    try:
        cursor.execute(TRY_DRAIN, (DRAIN_LOCK,))
        if not _answer(cursor):
            raise MaintenanceHeldError
        if not connection.info.get(PLATFORM_SEEN):
            cursor.execute(HAS_PLATFORM)
            connection.info[PLATFORM_SEEN] = _answer(cursor)
        if connection.info[PLATFORM_SEEN]:
            cursor.execute(IS_HELD)
            if _answer(cursor):
                raise MaintenanceHeldError
    finally:
        cursor.close()
    connection.info[ADMITTED] = connection.info.get(DEPTH, 0)


def _answer(cursor: DBAPICursor) -> bool:
    row = cursor.fetchone()
    return bool(row and row[0])


def writes(statement: str) -> bool:
    """Tell whether a statement may write, by its first word: one ``READING`` does not name.

    An insertion, an update, a deletion, a definition write; so may a ``WITH``, a ``CALL``, a word
    unknown. A reading that writes by a function — ``nextval``, a large object — is a reading here.
    """
    words = statement.lstrip(" \t\r\n(").split(maxsplit=1)
    return not words or words[0].upper() not in READING


@contextmanager
def drained(engine: Engine, patience: timedelta) -> Generator[None]:
    """Hold the lock of the drain exclusively while the block runs, the maintenance held first.

    Each write admitted before has then committed, and each one after reads the maintenance and is
    refused. The lock is waited for ``patience`` at most, then the wait fails
    (``LockNotAvailable``): a restoration does not wait without end for a write that does not end.
    """
    with engine.begin() as connection:
        bound_waits(connection, patience)
        connection.execute(select(func.pg_advisory_xact_lock(DRAIN_LOCK)))
        yield


def bound_waits(connection: Connection, patience: timedelta) -> None:
    """Bound each wait for a lock of a transaction to ``patience``, a millisecond at least."""
    waited = max(1, int(patience.total_seconds() * 1000))
    connection.execute(select(func.set_config("lock_timeout", f"{waited}ms", true())))
