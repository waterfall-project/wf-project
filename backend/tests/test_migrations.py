# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The migrations: chained, applied once, mirrored, and the schema the code declares."""

import subprocess
import sys
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import DBAPIError
from support import service_role

from waterfall.core.users.tables import UserAccount
from waterfall.migrations.runner import alembic_config, downgrade, main, upgrade
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Base, create_database_engine, engine_url
from waterfall.platform.installation import Installation

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


def test_the_descent_of_the_journal_and_of_the_role_takes_back_what_they_granted(
    empty_engine: Engine,
) -> None:
    upgrade(empty_engine)
    downgrade(empty_engine, "0001")
    with empty_engine.connect() as connection:
        granted = connection.execute(
            text("SELECT count(*) FROM information_schema.role_table_grants WHERE grantee = :role"),
            {"role": service_role(empty_engine.url)},
        ).scalar_one()
        journal = connection.execute(text("SELECT to_regclass('audit_entry')")).scalar_one()
        assert (granted, journal) == (0, None)
    upgrade(empty_engine)
    with empty_engine.connect() as connection:
        assert applied(connection) == [HEAD]


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
        assert (privileges(first, other), privileges(second, own)) == (set(), set())


def test_a_database_whose_role_of_the_service_would_be_cut_short_is_refused(
    database_url: str,
) -> None:
    with (
        scratch_database(database_url, prefix="w" * 23) as long_named,
        pytest.raises(DBAPIError, match="longer than an identifier"),
    ):
        upgrade(long_named)
