# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The aids of the tests of the migrations: a database of their own, the partitions described."""

import re
from contextlib import contextmanager
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import text
from support import service_role

from waterfall.platform.database import create_database_engine, engine_url

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection


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


# What the catalogue says of the partitions of a project (``:suffix``): their relation, columns,
# constraints and keys, those of other tables that name them, their indexes and triggers.
PARTITION_PARTS = text(
    "WITH part AS (SELECT oid FROM pg_class WHERE relname LIKE '%' || :suffix "
    "AND relnamespace = 'public'::regnamespace AND relkind = 'r') "
    "SELECT 'relation', c.oid::regclass::text, concat_ws(' ', c.relpersistence, "
    "c.relreplident, c.reloptions, pg_get_userbyid(c.relowner), c.relacl, "
    "pg_get_expr(c.relpartbound, c.oid), (SELECT inhparent::regclass::text FROM pg_inherits "
    "WHERE inhrelid = c.oid)) FROM pg_class AS c JOIN part USING (oid) "
    "UNION ALL SELECT 'column', a.attrelid::regclass::text || '.' || a.attname, "
    "concat_ws(' ', a.attnum, format_type(a.atttypid, a.atttypmod), a.attnotnull, a.attislocal, "
    "a.attinhcount, a.attstorage, a.attcompression, a.attcollation, "
    "pg_get_expr(d.adbin, d.adrelid)) FROM pg_attribute AS a JOIN part ON part.oid = a.attrelid "
    "LEFT JOIN pg_attrdef AS d ON d.adrelid = a.attrelid AND d.adnum = a.attnum "
    "WHERE a.attnum > 0 AND NOT a.attisdropped "
    "UNION ALL SELECT 'constraint', k.conname, concat_ws(' ', k.conrelid::regclass::text, "
    "k.contype, k.conislocal, k.coninhcount, k.connoinherit, k.convalidated, "
    "k.conparentid <> 0, pg_get_constraintdef(k.oid)) FROM pg_constraint AS k "
    "JOIN part ON part.oid = k.conrelid OR part.oid = k.confrelid "
    "UNION ALL SELECT 'index', i.indexrelid::regclass::text, concat_ws(' ', "
    "EXISTS (SELECT FROM pg_inherits WHERE inhrelid = i.indexrelid), "
    "pg_get_indexdef(i.indexrelid)) FROM pg_index AS i JOIN part ON part.oid = i.indrelid "
    "UNION ALL SELECT 'trigger', t.tgname, concat_ws(' ', t.tgenabled, t.tgisinternal, "
    "t.tgparentid <> 0, pg_get_triggerdef(t.oid)) FROM pg_trigger AS t "
    "JOIN part ON part.oid = t.tgrelid"
)


def partition_parts(connection: Connection, project_id: UUID) -> list[tuple[str, str, str]]:
    """Describe the partitions of a project, but for their names.

    The identifier of the project, whole or cut short in the name of an index, becomes ``P``; the
    number the server gives a name — of a key that names a partition, of an internal trigger —
    becomes ``N``.
    """
    suffix = f"_p_{project_id.hex}"

    def unnamed(value: str) -> str:
        value = value.replace(str(project_id), "P")
        return re.sub(r"_\d+\b", "_N", re.sub(r"_p_[0-9a-f]{1,32}", "_p_P", value))

    rows = connection.execute(PARTITION_PARTS, {"suffix": suffix})
    return sorted((part, unnamed(name), unnamed(form)) for part, name, form in rows)
