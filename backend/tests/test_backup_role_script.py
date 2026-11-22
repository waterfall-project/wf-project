# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The script of the role of the backup lets it read the large objects of Keycloak (#4170).

``pg_read_all_data`` reads the tables, the views and the sequences, not the large objects: a
``pg_dump`` of a database that holds one fails as that role, and the whole backup with it. The
script the platform runs at each start (``deploy/compose/backup-database-role.sql``) grants the
right, by ``psql``, as the administrator does. Here it runs on the server of the tests, its roles
and its database renamed for the run, on a database that stands for Keycloak's.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import text
from test_migrations_as_owner import PSQL, require_psql

from waterfall.platform.database import create_database_engine, engine_url
from waterfall.worker.backup import DumpError, connect, dump

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.story("US-2940")

SCRIPT = Path(__file__).parents[2] / "deploy" / "compose" / "backup-database-role.sql"
# The names the script gives, which the server of the tests shares with every run.
NAMES = re.compile(r"\b(waterfall_backup|keycloak)\b")
PASSWORD = "backup-" + uuid4().hex


class Stand:
    """A database that stands for Keycloak's, and the names the script is renamed to."""

    def __init__(self, server: str, name: str) -> None:
        self.server = server
        self.name = name
        self.backup = f"{name}_backup"
        self.keycloak = f"{name}_keycloak"

    def address(self, role: str, password: str) -> str:
        """Give the address of the database as one of its roles reaches it."""
        url = engine_url(self.server).set(username=role, password=password, database=self.keycloak)
        return url.render_as_string(hide_password=False)

    def as_keycloak(self) -> str:
        """Give the address of the database as its owner, Keycloak, reaches it."""
        return self.address(self.keycloak, self.keycloak)

    def as_backup(self) -> str:
        """Give the address of the database as the role of the backup reaches it."""
        return self.address(self.backup, PASSWORD)

    def run_script(self) -> None:
        """Run the script of the role of the backup by ``psql``, as the administrator does."""
        require_psql(PSQL)
        script = NAMES.sub(
            lambda found: self.backup if found.group(1) == "waterfall_backup" else self.keycloak,
            SCRIPT.read_text(encoding="utf-8"),
        )
        address = engine_url(self.server).set(drivername="postgresql", database="postgres")
        ran = subprocess.run(
            [
                PSQL,
                "--no-psqlrc",
                "--quiet",
                "--set=ON_ERROR_STOP=1",
                f"--dbname={address.render_as_string(hide_password=False)}",
                "--file=-",
            ],
            input=script,
            env={**os.environ, "BACKUP_DATABASE_PASSWORD": PASSWORD},
            capture_output=True,
            text=True,
            check=False,
        )
        assert ran.returncode == 0, ran.stderr.replace(PASSWORD, "***")


@pytest.fixture
def stand(database_url: str) -> Iterator[Stand]:
    """Make a role and a database of Keycloak's, as its own, and remove them after the test."""
    made = Stand(database_url, f"wf_lo_{uuid4().hex[:12]}")
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        role = f"CREATE ROLE \"{made.keycloak}\" LOGIN PASSWORD '{made.keycloak}'"
        connection.execute(text(role))
        connection.execute(text(f'CREATE DATABASE "{made.keycloak}" OWNER "{made.keycloak}"'))
    yield made
    with server.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{made.keycloak}" WITH (FORCE)'))
        connection.execute(text(f'DROP ROLE IF EXISTS "{made.backup}"'))
        connection.execute(text(f'DROP ROLE "{made.keycloak}"'))
    server.dispose()


def written_by_keycloak(stand: Stand, content: str) -> int:
    """Write a large object as Keycloak does, in a column of its own; give its identifier."""
    with connect(stand.as_keycloak()) as session:
        session.execute("CREATE TABLE IF NOT EXISTS cluster_event (id text, event_data oid)")
        made = session.execute("SELECT lo_from_bytea(0, %s::bytea)", (content.encode(),))
        found = made.fetchone()
        assert found is not None
        session.execute("INSERT INTO cluster_event VALUES (%s, %s)", (content, found[0]))
        return int(found[0])


def read_by_the_backup(stand: Stand, oid: int) -> bytes:
    """Read a large object as the role of the backup."""
    with connect(stand.as_backup()) as session:
        found = session.execute("SELECT lo_get(%s)", (oid,)).fetchone()
        assert found is not None
        return bytes(found[0])


def test_the_role_of_the_backup_reads_the_large_objects_keycloak_wrote_before_and_after(
    stand: Stand, tmp_path: Path
) -> None:
    # [US-2940] #4170: a database of Keycloak that holds a large object fails the dump of the role
    # of the backup, a member of pg_read_all_data alone; the script grants it the right on the
    # objects there at each start, and on those Keycloak writes after, by default privileges. It
    # runs at each start of the platform: a second time changes nothing and fails nothing.
    before = written_by_keycloak(stand, "before")
    # The script creates the role; until it ran, none can read.
    stand.run_script()
    assert read_by_the_backup(stand, before) == b"before"
    after = written_by_keycloak(stand, "after")
    assert read_by_the_backup(stand, after) == b"after"
    dumped = dump("identity_provider", stand.as_backup(), tmp_path)
    assert dumped.size_bytes > 0
    stand.run_script()
    assert read_by_the_backup(stand, after) == b"after"


def test_without_the_grant_the_dump_of_a_database_with_a_large_object_fails(
    stand: Stand, tmp_path: Path
) -> None:
    # [US-2940] #4170: what the script fixes, so that the test above proves something: the same
    # database, the role of the backup a member of pg_read_all_data and nothing more.
    written_by_keycloak(stand, "unreadable")
    server = create_database_engine(stand.server).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        role = f"CREATE ROLE \"{stand.backup}\" LOGIN PASSWORD '{PASSWORD}'"
        connection.execute(text(f"{role} IN ROLE pg_read_all_data"))
    server.dispose()
    with pytest.raises(DumpError):
        dump("identity_provider", stand.as_backup(), tmp_path)
