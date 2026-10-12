# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The migrations: chained, applied once, mirrored, and the schema the code declares."""

import subprocess
import sys
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, insert, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from support import raw_account, service_role

from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.core.backups.tables import Backup
from waterfall.core.users.tables import IdentitySyncReport, UserAccount
from waterfall.migrations.runner import alembic_config, downgrade, main, upgrade
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Base, Database, create_database_engine, engine_url
from waterfall.platform.installation import Installation
from waterfall.platform.tasks import BackgroundTask

# The last revision of the chain, which a migrated database says it has applied.
HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()


@contextmanager
def scratch_database(database_url: str, prefix: str = "waterfall_migration") -> Generator[Engine]:
    """Give an engine on a database of its own, without a table, dropped with its role after."""
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    name = f"{prefix}_{uuid4().hex}"
    with server.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_database_engine(
        engine_url(database_url).set(database=name).render_as_string(hide_password=False)
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with server.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{service_role(engine.url)}"'))
        server.dispose()


@pytest.fixture
def empty_engine(database_url: str) -> Iterator[Engine]:
    """Give an engine on a database of its own, without a table."""
    with scratch_database(database_url) as engine:
        yield engine


def start_migration(engine: Engine) -> subprocess.Popen[str]:
    """Start the command that applies the migrations, as an instance of the service does."""
    return subprocess.Popen(
        [sys.executable, "-m", "waterfall.migrations.runner"],
        env={
            "WATERFALL_DATABASE_URL": engine.url.render_as_string(hide_password=False),
            "WATERFALL_REDIS_URL": "redis://redis:6379/0",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def applied(connection: Connection) -> list[str]:
    """List the revisions the database says it has applied."""
    rows = connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
    return list(rows)


def test_the_history_of_the_schema_is_one_chain_with_one_head() -> None:
    script = ScriptDirectory.from_config(alembic_config())
    revisions = list(script.walk_revisions())
    assert len(script.get_heads()) == 1
    assert [revision.down_revision for revision in revisions].count(None) == 1
    assert all(
        revision.down_revision is None or isinstance(revision.down_revision, str)
        for revision in revisions
    )
    assert [revision.revision for revision in revisions][-1] == "0001"


@pytest.mark.requirement("WF-DAT-0140-A")
def test_a_migration_that_is_applied_is_not_replayed(empty_engine: Engine) -> None:
    upgrade(empty_engine)
    with empty_engine.begin() as connection:
        connection.execute(text("INSERT INTO installation VALUES (1, 'fr', 1000, 1000, now())"))
    upgrade(empty_engine)
    with empty_engine.connect() as connection:
        assert applied(connection) == [HEAD]
        assert connection.execute(text("SELECT count(*) FROM installation")).scalar_one() == 1


@pytest.mark.requirement("WF-DAT-0140-A")
def test_four_instances_that_start_together_apply_each_migration_once(
    empty_engine: Engine,
) -> None:
    instances = [start_migration(empty_engine) for _ in range(4)]
    results = [instance.communicate(timeout=60) for instance in instances]
    assert [
        (instance.returncode, errors)
        for instance, (_, errors) in zip(instances, results, strict=True)
    ] == [(0, "")] * 4
    with empty_engine.connect() as connection:
        assert applied(connection) == [HEAD]


def test_the_command_that_applies_the_migrations_names_the_secret_it_lacks() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "waterfall.migrations.runner"],
        env={},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 2
    assert "WATERFALL_DATABASE_URL: is missing" in result.stderr
    assert "waterfall-migrate" in result.stderr


def test_the_command_that_applies_the_migrations_takes_no_argument() -> None:
    assert main(["--now"]) == 2
    assert main(["--version"]) == 0


@pytest.mark.requirement("WF-DAT-0140-A")
def test_the_command_applies_the_migrations_to_the_database_of_the_settings(
    empty_engine: Engine,
) -> None:
    result = start_migration(empty_engine)
    _, errors = result.communicate(timeout=60)
    assert (result.returncode, errors) == (0, "")
    with empty_engine.connect() as connection:
        assert applied(connection) == [HEAD]


def test_each_migration_is_undone_by_its_mirror_and_applied_again(empty_engine: Engine) -> None:
    upgrade(empty_engine)
    downgrade(empty_engine, "base")
    with empty_engine.connect() as connection:
        tables = (
            connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            .scalars()
            .all()
        )
        assert tables == ["alembic_version"]
        functions = connection.execute(
            text("SELECT count(*) FROM pg_proc WHERE pronamespace = 'public'::regnamespace")
        ).scalar_one()
        assert functions == 0
    upgrade(empty_engine)
    with empty_engine.connect() as connection:
        assert applied(connection) == [HEAD]


def describe_schema(engine: Engine) -> dict[str, list[tuple[object, ...]]]:
    """Read what the catalogue says of the tables: constraints, indexes and columns."""
    queries = {
        "constraints": (
            "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) "
            "FROM pg_constraint WHERE connamespace = 'public'::regnamespace "
            "AND conrelid::regclass::text <> 'alembic_version'"
        ),
        "indexes": (
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        ),
        "columns": (
            "SELECT table_name, column_name, data_type, collation_name, is_nullable, "
            "column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
        ),
    }
    with engine.connect() as connection:
        return {
            name: sorted((tuple(row) for row in connection.execute(text(query))), key=repr)
            for name, query in queries.items()
        }


def test_the_migrations_build_the_schema_the_tables_of_the_code_declare(
    database_url: str, empty_engine: Engine
) -> None:
    """Compare the migrated database with one the tables of the code create, in the catalogue.

    ``compare_metadata`` sees the columns, the keys and the indexes; the check constraints and
    the defaults of the server it leaves to the catalogue, which is read on both databases.
    """
    declared = {table.name for table in Base.metadata.sorted_tables}
    assert declared == {
        Installation.__tablename__,
        UserAccount.__tablename__,
        AuditEntry.__tablename__,
        Permission.__tablename__,
        AccessRole.__tablename__,
        AccessRolePermission.__tablename__,
        UserAccessRole.__tablename__,
        BackgroundTask.__tablename__,
        Backup.__tablename__,
        IdentitySyncReport.__tablename__,
    }
    upgrade(empty_engine)
    with empty_engine.connect() as connection:
        differences = compare_metadata(
            MigrationContext.configure(connection, opts={"compare_server_default": True}),
            Base.metadata,
        )
    assert differences == []
    with scratch_database(database_url) as created:
        Base.metadata.create_all(created)
        from_the_code = describe_schema(created)
    from_the_migrations = describe_schema(empty_engine)
    assert all(from_the_migrations.values())
    assert from_the_migrations == from_the_code


def granted_to(engine: Engine, role: str) -> tuple[int, bool]:
    """Count the rights a role holds on the tables, and tell whether it was granted the schema.

    Granted to the role itself: every role may use ``public`` through ``PUBLIC`` besides.
    """
    with engine.connect() as connection:
        held, usage = connection.execute(
            text(
                "SELECT (SELECT count(*) FROM information_schema.role_table_grants "
                "WHERE grantee = :role), EXISTS (SELECT FROM pg_namespace, "
                "aclexplode(nspacl) AS acl WHERE nspname = 'public' "
                "AND acl.grantee = to_regrole(:role) AND acl.privilege_type = 'USAGE')"
            ),
            {"role": role},
        ).one()
    return int(held), bool(usage)


def test_the_descent_of_the_journal_and_of_the_role_takes_back_what_they_granted(
    empty_engine: Engine,
) -> None:
    # The rights are counted before the descent: none after it would prove nothing of a role
    # misnamed, which never held any.
    role = service_role(empty_engine.url)
    upgrade(empty_engine)
    held, usage = granted_to(empty_engine, role)
    assert (held > 0, usage) == (True, True)
    downgrade(empty_engine, "0001")
    assert granted_to(empty_engine, role) == (0, False)
    with empty_engine.connect() as connection:
        journal = connection.execute(text("SELECT to_regclass('audit_entry')")).scalar_one()
        assert journal is None
    upgrade(empty_engine)
    with empty_engine.connect() as connection:
        assert applied(connection) == [HEAD]


# What the service needs on each table, and why; a table the code declares and this does not
# fails the test below, which says so (docs/dev/sql.md, "Le rôle du service").
SERVICE_RIGHTS: dict[str, set[str]] = {
    # Read by getInstallation, its settings changed by an administrator; its row inserted by the
    # bootstrap, as the owner (US-0420, #701); never deleted: it is the installation.
    "installation": {"SELECT", "UPDATE"},
    # Created, read, changed, deactivated; never deleted (WF-DAT-0080).
    "user_account": {"SELECT", "INSERT", "UPDATE"},
    # Inscribed and read; never deleted, and changed only in the two labels that name an account,
    # a grant on those columns alone that test_audit_journal.py checks (WF-SEC-0030).
    "audit_entry": {"SELECT", "INSERT"},
    # The catalogue, written by the migrations alone and read by the service (WF-ADM-0100).
    "permission": {"SELECT"},
    # Created, read, changed, marked deleted; never removed (WF-DAT-0080).
    "access_role": {"SELECT", "INSERT", "UPDATE"},
    # Two associations of two keys: a row is added or removed, never changed.
    "access_role_permission": {"SELECT", "INSERT", "DELETE"},
    "user_access_role": {"SELECT", "INSERT", "DELETE"},
    # Submitted, followed, run and ended; never deleted by the service until a rule of retention
    # comes (§4.4.1).
    "background_task": {"SELECT", "INSERT", "UPDATE"},
    # Recorded by the worker and read; neither marked nor deleted until EP-13 (WF-ADM-0170).
    "backup": {"SELECT", "INSERT"},
    # The report of a reading of the accounts, kept and read; neither changed nor deleted.
    "identity_sync_report": {"SELECT", "INSERT"},
}


def test_the_role_of_the_service_holds_what_each_table_declares(database: Database) -> None:
    service = service_role(database.engine.url)
    with database.engine.connect() as connection:
        grants = connection.execute(
            text(
                "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
                "WHERE grantee = :role"
            ),
            {"role": service},
        ).all()
    held: dict[str, set[str]] = {}
    for table, privilege in grants:
        held.setdefault(table, set()).add(privilege)
    tables = {table.name for table in Base.metadata.sorted_tables}
    undeclared = tables - SERVICE_RIGHTS.keys()
    assert not undeclared, f"declare in SERVICE_RIGHTS what the service needs on {undeclared}"
    assert held == {name: SERVICE_RIGHTS[name] for name in tables}


def privileges(engine: Engine, role: str) -> set[tuple[str, str]]:
    """List the tables of the database of the engine and what the role may do on each."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT relname, privilege FROM pg_class CROSS JOIN unnest(ARRAY['SELECT', "
                "'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']) AS privilege WHERE relkind = 'r' "
                "AND relnamespace = 'public'::regnamespace "
                "AND has_table_privilege(:role, pg_class.oid, privilege)"
            ),
            {"role": role},
        )
        return {(table, privilege) for table, privilege in rows}


def test_two_databases_of_one_server_share_no_role_of_the_service(database_url: str) -> None:
    with scratch_database(database_url) as first, scratch_database(database_url) as second:
        upgrade(first)
        upgrade(second)
        own, other = service_role(first.url), service_role(second.url)
        assert own != other
        assert ("audit_entry", "INSERT") in privileges(first, own)
        assert ("audit_entry", "INSERT") in privileges(second, other)
        assert ("user_account", "DELETE") not in privileges(first, own)
        assert (privileges(first, other), privileges(second, own)) == (set(), set())


def test_a_database_of_fifty_five_bytes_has_its_role_of_the_service(database_url: str) -> None:
    # The longest name a database may have: with its suffix, the role's is 63 bytes, the most an
    # identifier holds.
    with scratch_database(database_url, prefix="w" * 22) as longest:
        assert len(longest.url.database or "") == 55
        upgrade(longest)
        assert granted_to(longest, service_role(longest.url))[1]


def test_a_database_whose_role_of_the_service_would_be_cut_short_is_refused(
    database_url: str,
) -> None:
    with (
        scratch_database(database_url, prefix="w" * 23) as long_named,
        pytest.raises(DBAPIError, match="longer than an identifier"),
    ):
        upgrade(long_named)


def kept_report(connection: Connection, skipped: list[dict[str, Any]]) -> UUID:
    """Keep the report of a reading around the service, with what it skipped; give its task."""
    task_id = uuid4()
    at = datetime(2026, 10, 12, 2, tzinfo=UTC)
    task: dict[str, object] = {"kind": "identity_sync", "status": "succeeded", "progress": 100}
    connection.execute(
        insert(BackgroundTask).values(
            id=task_id,
            payload={},
            correlation_id="c",
            attempts=1,
            submitted_at=at,
            finished_at=at,
            **task,
        )
    )
    counts = dict.fromkeys(("created", "updated", "deactivated"), 0)
    connection.execute(
        insert(IdentitySyncReport).values(
            task_id=task_id, finished_at=at, skipped=skipped, removed=[], **counts
        )
    )
    return task_id


def skipped_of(engine: Engine, task_id: UUID) -> list[dict[str, Any]]:
    """Read what the report of a reading skipped."""
    with engine.connect() as connection:
        found = select(IdentitySyncReport.skipped).where(IdentitySyncReport.task_id == task_id)
        return connection.scalars(found).one()


def test_the_reports_kept_name_an_account_of_waterfall_by_its_identifier_alone(
    empty_engine: Engine,
) -> None:
    # The last administrator kept by the account that bears its address, whatever its case; a
    # person whose address an account bears, by her subject and that account, nothing personal
    # kept; an entry that named a person by her address alone, or an account none bears any more,
    # dropped (#920). The descent names again by an address each entry that has one.
    upgrade(empty_engine, "0015")
    kept = raw_account(email="Dominique.Bernard@example.org", origin="directory")
    camille = {"kind": "person", "subject": "kc-camille", "last_name": "Roux", "first_name": "Cam"}
    with empty_engine.begin() as connection:
        connection.execute(insert(UserAccount).values(**kept))
        former = kept_report(
            connection,
            [
                {"email": "camille@external.test", "code": "ALREADY_EXISTS"},
                {"email": "dominique.bernard@EXAMPLE.org", "code": "LAST_ADMINISTRATOR"},
                {"email": "gone@example.org", "code": "LAST_ADMINISTRATOR"},
                {**camille, "email": "DOMINIQUE.bernard@example.org", "code": "ALREADY_EXISTS"},
                {**camille, "email": "gone@example.org", "code": "ALREADY_EXISTS"},
            ],
        )
    upgrade(empty_engine)
    by_identifier = {"kind": "account", "user_id": str(kept["id"]), "code": "LAST_ADMINISTRATOR"}
    held_by = {
        "kind": "person",
        "subject": "kc-camille",
        "user_id": str(kept["id"]),
        **dict.fromkeys(("last_name", "first_name", "email")),
        "code": "ALREADY_EXISTS",
    }
    assert skipped_of(empty_engine, former) == [by_identifier, held_by]
    hugo = {"kind": "person", "subject": "kc-hugo", "last_name": "Garnier", "first_name": "Hugo"}
    with empty_engine.begin() as connection:
        latest = kept_report(
            connection,
            [
                {**hugo, "email": None, "code": "EMAIL_MISSING"},
                by_identifier,
                {**hugo, "email": "hugo@example.org", "code": "VALIDATION_FAILED"},
                {**held_by, "user_id": None},
            ],
        )
    downgrade(empty_engine, "0015")
    named = {"email": "Dominique.Bernard@example.org", "code": "LAST_ADMINISTRATOR"}
    taken = {"email": "Dominique.Bernard@example.org", "code": "ALREADY_EXISTS"}
    assert skipped_of(empty_engine, former) == [named, taken]
    again = [named, {"email": "hugo@example.org", "code": "VALIDATION_FAILED"}]
    assert skipped_of(empty_engine, latest) == again
