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
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, cast
from uuid import UUID

from psycopg.errors import UndefinedTable
from sqlalchemy import Boolean, CheckConstraint, SmallInteger, Text, delete, select
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import Base

if TYPE_CHECKING:
    from redis import Redis

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
    ``abandoned`` its step (``Restoring``).
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


@dataclass(frozen=True, slots=True)
class Restoring:
    """The task of the restoration that holds the platform in maintenance, and its attempts.

    ``caches_cleared`` once an attempt has asked Keycloak to clear its caches: from then on, it may
    serve the realm of the backup, whose secrets are not the installation's, until the realm of
    the installation is applied again. ``abandoned`` once its attempts are spent: nothing takes it
    up again, and the maintenance stays, for an operator.
    """

    task_id: UUID
    payload: dict[str, Any]
    requested_by: UUID | None
    correlation_id: str
    attempts: int
    caches_cleared: bool = False
    abandoned: bool = False


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
        """
        held = select(RestorationState).join(
            HeldMaintenance, HeldMaintenance.task_id == RestorationState.task_id
        )
        try:
            with self.database.transaction() as session:
                state = session.scalars(held).one_or_none()
        except ProgrammingError as error:
            if isinstance(error.orig, UndefinedTable):
                return None
            raise
        if state is None:
            return None
        return Restoring(
            state.task_id,
            state.payload,
            state.requested_by,
            state.correlation_id,
            state.attempts,
            caches_cleared=state.caches_cleared,
            abandoned=state.abandoned,
        )

    def hold(self, restoring: Restoring) -> None:
        """Put the platform in maintenance for a restoration, or say one more of its attempts."""
        state = {
            "task_id": restoring.task_id,
            "payload": restoring.payload,
            "requested_by": restoring.requested_by,
            "correlation_id": restoring.correlation_id,
            "attempts": restoring.attempts,
            "caches_cleared": restoring.caches_cleared,
            "abandoned": restoring.abandoned,
        }
        held = insert(HeldMaintenance).values(id=THE_ROW, task_id=restoring.task_id)
        stated = insert(RestorationState).values(id=THE_ROW, **state)
        with self.database.transaction() as session:
            session.execute(
                held.on_conflict_do_update(
                    index_elements=[HeldMaintenance.id], set_={"task_id": restoring.task_id}
                )
            )
            session.execute(
                stated.on_conflict_do_update(index_elements=[RestorationState.id], set_=state)
            )

    def lift(self) -> None:
        """End the maintenance: the platform serves its operations again."""
        with self.database.transaction() as session:
            session.execute(delete(RestorationState))
            session.execute(delete(HeldMaintenance))

    def close_front_sessions(self) -> int:
        """Delete every session and sign-in the front keeps, and say how many keys went."""
        return int(cast("int", self.client.eval(FORGET_SESSIONS, 0, self.sessions)))
