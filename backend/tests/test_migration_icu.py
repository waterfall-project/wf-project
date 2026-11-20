# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The migration of the roles refuses a server without ICU, saying so (US-2800, #742)."""

from importlib import import_module
from typing import TYPE_CHECKING

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text

from waterfall.platform.database import EVERY_LETTER

if TYPE_CHECKING:
    from sqlalchemy import Connection, Engine

pytestmark = [pytest.mark.story("US-2800"), pytest.mark.requirement("WF-ARC-0050-A")]

ROLES = import_module("waterfall.migrations.versions.0004_access_roles")


def test_the_migration_checks_the_collation_the_search_lowers_a_text_in() -> None:
    assert ROLES.COLLATION == EVERY_LETTER


def test_a_server_that_knows_the_collation_passes(empty_engine: Engine) -> None:
    with empty_engine.connect() as connection:
        ROLES.require_collation(connection)


def test_a_server_without_the_collation_is_refused_saying_what_it_lacks(
    empty_engine: Engine,
) -> None:
    with (
        empty_engine.connect() as connection,
        pytest.raises(ROLES.CollationMissingError) as refused,
    ):
        ROLES.require_collation(connection, "absent-x-icu")
    said = str(refused.value)
    assert "'absent-x-icu'" in said
    assert "pg_collation" in said
    assert "built without ICU" in said
    assert "docs/exploitation/postgresql-fourni.md" in said


def test_the_upgrade_refuses_the_server_before_writing_anything(
    empty_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    verified = ROLES.require_collation

    def refuse(connection: Connection) -> None:
        verified(connection, "absent-x-icu")

    monkeypatch.setattr(ROLES, "require_collation", refuse)
    # Autocommit: a write made before the refusal would stay, where a transaction would hide it.
    with empty_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context), pytest.raises(ROLES.CollationMissingError):
            ROLES.upgrade()
        assert inspect(connection).get_table_names() == []
        extensions = connection.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'unaccent'")
        ).all()
        assert extensions == []
