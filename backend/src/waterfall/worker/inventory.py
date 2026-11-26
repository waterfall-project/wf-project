# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a backup counts of the state it copies, which the test of its restoration compares.

US-2930.

The number of the projects, of the marked revisions, of the lines of cost and of the accounts of
the identity provider, and the digest of the indicators kept by a sample of the marked revisions,
the latest marked (WF-EXP-0060). A backup counts them in one state of each database, read just
before it is dumped (``reading``), so that the manifest says what the archive holds; the test of a
restoration counts them again in the databases it restored, by the same functions.

The projects, the revisions, the lines and the indicators are counted by the interfaces of their
modules. The accounts are those of the realm of the installation in the database of Keycloak, read
in its tables, the accounts of service apart: the identity provider is not a module of Waterfall,
and only its database is in the archive.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from psycopg.errors import UndefinedColumn, UndefinedTable
from sqlalchemy import exc, text
from sqlalchemy.orm import Session

from waterfall.core.costs import interface as costs_interface
from waterfall.core.indicators import interface as indicators_interface
from waterfall.core.projects import interface as projects_interface
from waterfall.core.revisions import interface as revisions_interface
from waterfall.platform.database import create_database_engine
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Mapping

    from sqlalchemy import Connection

COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"
# The event a backup writes when a database does not hold what it counts.
UNCOUNTED = "backup.inventory_not_counted"

logger = get_logger(__name__)
# How many marked revisions a backup samples, the latest marked.
SAMPLE_SIZE = 10
# The accounts of a realm of Keycloak, those of the clients' service apart.
ACCOUNTS = text(
    "SELECT count(*) FROM user_entity JOIN realm ON realm.id = user_entity.realm_id "
    "WHERE realm.name = :realm AND user_entity.service_account_client_link IS NULL"
)
# What a test compares, and the reason each one that differs gives (``RestoreTest.failure``).
COUNTED = ("projects", "marked_revisions", "cost_lines", "identity_accounts")
INDICATORS_DIFFER = "indicators_differ"


@dataclass(frozen=True, slots=True)
class Inventory:
    """What a state of the platform holds, as a backup and its test count it.

    ``sample`` gives, for each sampled marked revision — its project, then itself —, the digest of
    the indicators it kept.
    """

    projects: int
    marked_revisions: int
    cost_lines: int
    identity_accounts: int
    sample: dict[tuple[UUID, UUID], str] = field(default_factory=dict[tuple[UUID, UUID], str])

    def described(self) -> dict[str, Any]:
        """Give it as the manifest of a backup writes it."""
        return {
            **{name: getattr(self, name) for name in COUNTED},
            "indicator_sample": [
                {"project_id": str(project), "revision_id": str(revision), "sha256": digest}
                for (project, revision), digest in self.sample.items()
            ],
        }

    def differences(self, found: Inventory) -> list[str]:
        """Say what differs in ``found``, counted after a restoration, from this, the backup's.

        One reason by count that differs, ``<count>_differ``, then ``indicators_differ`` if a
        sampled revision kept other indicators, or none.
        """
        reasons = [
            f"{name}_differ" for name in COUNTED if getattr(found, name) != getattr(self, name)
        ]
        if found.sample != self.sample:
            reasons.append(INDICATORS_DIFFER)
        return reasons


def inventory_of(said: Mapping[str, Any]) -> Inventory | None:
    """Read what a manifest says it holds; ``None`` if it says nothing, as before US-2930, or ill.

    Nothing of it is trusted but numbers and identifiers.
    """
    given = said.get("inventory")
    if not isinstance(given, dict):
        return None
    described = cast("dict[str, Any]", given)
    try:
        counts: list[object] = [described[name] for name in COUNTED]
        entries = cast("list[dict[str, Any]]", described["indicator_sample"])
        sample = {
            (UUID(str(each["project_id"])), UUID(str(each["revision_id"]))): str(each["sha256"])
            for each in entries
        }
    except KeyError, TypeError, ValueError, AttributeError:
        return None
    numbers = [value for value in counts if type(value) is int and value >= 0]
    if len(numbers) != len(COUNTED):
        return None
    projects, marked_revisions, cost_lines, identity_accounts = numbers
    return Inventory(projects, marked_revisions, cost_lines, identity_accounts, sample)


def counted(
    session: Session, identity_accounts: int, sampled: list[tuple[UUID, UUID]]
) -> Inventory:
    """Count the database of Waterfall ``session`` reads, the accounts counted apart.

    ``sampled`` are the revisions whose kept indicators are digested: those the backup sampled,
    when its test counts again.
    """
    return Inventory(
        projects=projects_interface.count_projects(session),
        marked_revisions=revisions_interface.count_marked_revisions(session),
        cost_lines=costs_interface.count_cost_lines(session),
        identity_accounts=identity_accounts,
        sample={
            (project, revision): indicators_interface.kept_indicators_digest(
                session, project, revision
            )
            for project, revision in sampled
        },
    )


def sample_of(session: Session) -> list[tuple[UUID, UUID]]:
    """Give the marked revisions a backup samples: the latest marked."""
    return revisions_interface.sampled_marked_revisions(session, SAMPLE_SIZE)


def accounts_of(connection: Connection, realm: str) -> int:
    """Count the accounts of a realm in the database of Keycloak ``connection`` reads."""
    return connection.scalar(ACCOUNTS, {"realm": realm}) or 0


@dataclass(frozen=True, slots=True)
class Reading:
    """A transaction that reads one state of a database, and the snapshot it exported of it."""

    connection: Connection
    snapshot: str


@contextmanager
def reading(address: str) -> Generator[Reading]:
    """Open a transaction that reads one state of a database, alone (503 if it does not answer).

    It exports its snapshot (``pg_export_snapshot()``) and stays open while the caller needs it:
    the backup counts in it, then ``pg_dump`` dumps the very same state by ``--snapshot``, so that
    nothing written between the counts and the dump leaves the manifest at odds with it (#4572).
    """
    engine = create_database_engine(address)
    try:
        with engine.connect() as opened:
            connection = opened.execution_options(isolation_level="REPEATABLE READ")
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                snapshot = str(connection.scalar(text("SELECT pg_export_snapshot()")))
                yield Reading(connection, snapshot)
    except exc.OperationalError as error:
        raise UnavailableError(COMPONENT_UNAVAILABLE, {"component": "database"}) from error
    finally:
        engine.dispose()


def read_or_none[Read](address: str, read: Callable[[Connection], Read]) -> Read | None:
    """Read in one state of a database; ``None`` if it lacks a table or a column the reading names.

    A database of an earlier revision than the code — taken mid-update — is backed up all the
    same, its manifest without what it holds: its test of a restoration then says so. Any other
    refusal — a right the role lacks (42501) — fails the backup: it would hold a manifest without
    inventory for a fault no earlier revision explains.
    """
    return read_while(address, read, lambda _: None)[0]


def read_while[Read, Done](
    address: str, read: Callable[[Connection], Read], then: Callable[[str], Done]
) -> tuple[Read | None, Done]:
    """Read in one state of a database as ``read_or_none`` does, then run ``then`` in that state.

    ``then`` is given the snapshot the transaction exported, which stays open until it returns:
    the backup dumps the database in it. A reading that fails on a table or a column that is
    missing is rolled back to its savepoint, so that the snapshot stays and ``then`` still runs.
    """
    with reading(address) as opened:
        value: Read | None
        try:
            with opened.connection.begin_nested():
                value = read(opened.connection)
        except exc.ProgrammingError as error:
            if not isinstance(error.orig, UndefinedTable | UndefinedColumn):
                raise
            logger.warning(UNCOUNTED, error=type(error.orig).__name__)
            value = None
        return value, then(opened.snapshot)


def counted_in(connection: Connection, identity_accounts: int) -> Inventory:
    """Count the database of Waterfall ``connection`` reads, the latest marked revisions sampled."""
    with Session(bind=connection) as session:
        return counted(session, identity_accounts, sample_of(session))
