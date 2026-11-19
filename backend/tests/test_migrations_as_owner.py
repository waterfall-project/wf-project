# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The migrations as the owner of the tables of the production, who is no superuser (#958).

The other tests of the back migrate as the superuser of their server, which may do anything: a
migration that needs a superuser — an extension that is not trusted, an ``ALTER ROLE`` — would pass
them and break only once merged, in the trial of the production. Here a database is made as the
production makes it, by its own script (``deploy/compose/waterfall-database.sql``, run by ``psql``),
and every migration is applied as the owner that script makes ``NOSUPERUSER``.
"""

import os
import re
import stat
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from uuid import uuid4

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from waterfall.migrations.runner import alembic_config, upgrade
from waterfall.platform.database import create_database_engine, engine_url

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

pytestmark = pytest.mark.story("US-2480")

# The script the administrator of the server runs at each start of the production (US-0430).
PRODUCTION_SCRIPT = Path(__file__).parents[2] / "deploy" / "compose" / "waterfall-database.sql"

# The names the script gives the database, its owner and the role of the service.
PRODUCTION_NAME = re.compile(r"\bwaterfall(_service)?\b")

MIGRATIONS = alembic_config()
HEAD = ScriptDirectory.from_config(MIGRATIONS).get_current_head()
VERSIONS = Path(str(MIGRATIONS.get_main_option("script_location"))) / "versions"

# The SQLSTATE of PostgreSQL's ``insufficient_privilege``, which a missing right raises.
INSUFFICIENT_PRIVILEGE = "42501"


class ProductionOwner(NamedTuple):
    """The database the production script made, and its owner: their name, an engine as it."""

    name: str
    engine: Engine


def production_script(name: str) -> str:
    """Give the production script, its database and its roles renamed ``name`` and its service.

    The server of the tests is shared by every run, and the production's names would be the same
    for all of them: the database and the owner take ``name``, and the role of the service, which
    the migrations name after the database, ``<name>_service``, as the production's does. Nothing
    else of the script changes; a statement that still names a role of the production would act on
    a role of the server, and stops the test before the script runs.
    """
    script = PRODUCTION_NAME.sub(
        lambda found: name + (found.group(1) or ""), PRODUCTION_SCRIPT.read_text()
    )
    statements = (line for line in script.splitlines() if not line.lstrip().startswith("--"))
    left = {word for line in statements for word in re.findall(r"\bwaterfall\w*", line)}
    assert left <= {name, f"{name}_service"}, f"the production script names {left}"
    return script


# The client the script is run by, as the backups call /usr/bin/pg_dump (worker/backup.py).
PSQL = "/usr/bin/psql"

# The script reads the environment by ``\getenv``, which ``psql`` has since its version 15.
PSQL_MINIMUM = 15


def require_psql(psql: str) -> None:
    """Fail, saying what to install, when ``psql`` is missing or older than the script needs."""
    advice = (
        f"the production script needs psql {PSQL_MINIMUM} or later at {psql}: install"
        " postgresql-client-18 and point /usr/bin/psql at /usr/lib/postgresql/18/bin/psql"
    )
    try:
        said = subprocess.run(
            [psql, "--version"], capture_output=True, text=True, check=False
        ).stdout
    except OSError:
        pytest.fail(f"{psql} is missing: {advice}")
    found = re.search(r"\(PostgreSQL\) (\d+)", said)
    if found is None or int(found.group(1)) < PSQL_MINIMUM:
        pytest.fail(f"{psql} says {said.strip()!r}, too old or unknown: {advice}")


def run_production_script(server: str, name: str, password: str) -> None:
    """Run the production script by ``psql``, as the administrator does, on the server given.

    The password of the owner goes by the environment, as in the production, and so does the
    superuser's; ``psql`` stops at the first error, which fails the test with what it said.
    """
    require_psql(PSQL)
    address = engine_url(server)
    environment = {**os.environ, "OWNER_DATABASE_PASSWORD": password}
    if address.password is not None:
        environment["PGPASSWORD"] = str(address.password)
    libpq = address.set(drivername="postgresql", password=None)
    ran = subprocess.run(
        [
            PSQL,
            "--no-psqlrc",
            "--quiet",
            "--set=ON_ERROR_STOP=1",
            f"--dbname={libpq.render_as_string(hide_password=False)}",
            "--file=-",
        ],
        input=production_script(name),
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    # An empty password would put the mask between every character of the message.
    shown = ran.stderr.replace(password, "***") if password else ran.stderr
    if address.password:
        shown = shown.replace(str(address.password), "***")
    # Not an ``assert``: pytest would add to its message the process, and so the password unmasked.
    if ran.returncode != 0:
        pytest.fail(f"the production script failed: {shown}")


def failing_psql(monkeypatch: pytest.MonkeyPatch, stderr: str) -> None:
    """Make ``psql`` fail with ``stderr``, without running it."""

    def ran(arguments: list[str], **_options: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(arguments, 3, "", stderr)

    def found(_psql: str) -> None:
        return None

    monkeypatch.setattr(f"{__name__}.require_psql", found)
    monkeypatch.setattr(subprocess, "run", ran)


@pytest.mark.story("US-2800")
def test_the_password_of_the_owner_is_masked_in_the_message_of_a_failed_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [US-2800] #3898: what psql says may repeat the password of the owner, and of the server.
    failing_psql(monkeypatch, "FATAL: password secret-owner refused, secret-server tried")

    with pytest.raises(pytest.fail.Exception) as failed:
        run_production_script(
            "postgresql://admin:secret-server@host/db", "waterfall_x", "secret-owner"
        )

    assert "secret-owner" not in str(failed.value)
    assert "secret-server" not in str(failed.value)
    assert "FATAL: password *** refused, *** tried" in str(failed.value)


@pytest.mark.story("US-2800")
def test_an_empty_password_inserts_nothing_in_the_message_of_a_failed_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [US-2800] #3898: ``"".replace`` would put the mask between every character.
    failing_psql(monkeypatch, "FATAL: role missing")

    with pytest.raises(pytest.fail.Exception) as failed:
        run_production_script("postgresql://admin@host/db", "waterfall_x", "")

    assert "the production script failed: FATAL: role missing" in str(failed.value)
    assert "***" not in str(failed.value)

    with pytest.raises(pytest.fail.Exception) as failed_on_empty_server:
        run_production_script("postgresql://admin:@host/db", "waterfall_x", "")

    assert "***" not in str(failed_on_empty_server.value)


def fake_psql(tmp_path: Path, version: str) -> Path:
    """Write an executable that says it is the ``psql`` of ``version``."""
    psql = tmp_path / "psql"
    psql.write_text(f"#!/bin/sh\necho '{version}'\n")
    psql.chmod(psql.stat().st_mode | stat.S_IXUSR)
    return psql


@pytest.mark.parametrize(
    ("version", "said"),
    [
        pytest.param(None, "is missing", id="absent"),
        pytest.param("psql (PostgreSQL) 14.0", "too old", id="too-old"),
        pytest.param("not a client", "too old or unknown", id="unknown"),
    ],
)
def test_a_psql_missing_or_too_old_fails_saying_what_to_install(
    tmp_path: Path, version: str | None, said: str
) -> None:
    psql = tmp_path / "psql" if version is None else fake_psql(tmp_path, version)

    with pytest.raises(pytest.fail.Exception) as refused:
        require_psql(str(psql))

    assert said in str(refused.value)
    assert "install postgresql-client-18" in str(refused.value)


def test_a_psql_of_the_minimum_version_is_accepted(tmp_path: Path) -> None:
    require_psql(str(fake_psql(tmp_path, "psql (PostgreSQL) 15.2")))


@pytest.fixture
def production_owner(database_url: str) -> Iterator[ProductionOwner]:
    """Make a database by the production script, and give an engine on it as its owner.

    ``database_url`` designates the superuser of the server the tests are given, as the
    administrator of the production's: it runs the script, then drops what the script and the
    migrations made.
    """
    name, password = f"waterfall_owner_{uuid4().hex}", uuid4().hex
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    try:
        run_production_script(database_url, name, password)
        owner = engine_url(database_url).set(username=name, password=password, database=name)
        engine = create_database_engine(owner.render_as_string(hide_password=False))
        yield ProductionOwner(name, engine)
        engine.dispose()
    finally:
        with server.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{name}_service"'))
            connection.execute(text(f'DROP ROLE IF EXISTS "{name}"'))
        server.dispose()


def test_every_migration_applies_as_the_owner_the_production_script_makes(
    production_owner: ProductionOwner,
) -> None:
    with production_owner.engine.connect() as connection:
        rights = connection.execute(
            text(
                "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,"
                " datdba = pg_roles.oid FROM pg_roles, pg_database"
                " WHERE rolname = current_user AND datname = current_database()"
            )
        ).one()
    assert tuple(rights) == (False, False, False, False, False, True)

    upgrade(production_owner.engine)

    with production_owner.engine.connect() as connection:
        applied = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert applied == HEAD


# A migration of trial, above the last of the chain, in a directory of its own: never in VERSIONS.
TRIAL_MIGRATION = '''"""A migration that needs a superuser: a trial of #958, never in the chain."""

from alembic import op

revision = "trial"
down_revision = {head!r}
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute({statement!r})


def downgrade() -> None:
    pass
'''


@pytest.mark.parametrize(
    "statement",
    [
        # file_fdw reads the files of the server: no database owner may create it.
        pytest.param("CREATE EXTENSION file_fdw", id="extension-not-trusted"),
        pytest.param("ALTER ROLE CURRENT_USER CREATEROLE", id="alter-role"),
    ],
)
def test_a_migration_that_needs_a_superuser_fails_as_the_owner(
    production_owner: ProductionOwner, statement: str, tmp_path: Path
) -> None:
    (tmp_path / "trial.py").write_text(TRIAL_MIGRATION.format(head=HEAD, statement=statement))
    config = alembic_config(production_owner.engine)
    config.set_main_option("path_separator", "os")
    config.set_main_option("version_locations", os.pathsep.join([str(VERSIONS), str(tmp_path)]))

    with pytest.raises(ProgrammingError) as refused:
        command.upgrade(config, "trial")

    assert isinstance(refused.value.orig, InsufficientPrivilege), refused.value
    assert refused.value.orig.sqlstate == INSUFFICIENT_PRIVILEGE
    assert statement in str(refused.value.statement)
