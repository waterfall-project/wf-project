# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the anonymisation of a copy look for in a database, whatever its tables.

(US-2960.) A text found anywhere — any column of text or of JSON of any table of any schema but
PostgreSQL's own —, whatever its case; and what each table holds, to tell what the anonymisation
left as it was.
"""

import hashlib
from typing import TYPE_CHECKING

from sqlalchemy import Text, cast, column, func, or_, select, table, text

if TYPE_CHECKING:
    from collections.abc import Collection

    from sqlalchemy import ColumnElement, Connection, Engine, TableClause

# The columns that may hold a text: the texts, and the documents of JSON.
COLUMNS = text(
    "SELECT columns.table_schema, columns.table_name, columns.column_name "
    "FROM information_schema.columns AS columns "
    "JOIN information_schema.tables AS tables USING (table_schema, table_name) "
    "WHERE tables.table_type = 'BASE TABLE' "
    "AND columns.table_schema NOT IN ('pg_catalog', 'information_schema') "
    "AND columns.data_type IN ('text', 'character varying', 'character', 'json', 'jsonb') "
    "ORDER BY 1, 2, 3"
)
TABLES = text(
    "SELECT table_schema, table_name FROM information_schema.tables "
    "WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema') "
    "ORDER BY 1, 2"
)


def found(engine: Engine, needles: Collection[str]) -> dict[str, list[str]]:
    """Give, by column (``schema.table.column``), the needles a database holds, whatever their case.

    A column none of them is in is not given: an empty result says none is anywhere.
    """
    lowered = sorted({needle.lower() for needle in needles if needle})
    held: dict[str, list[str]] = {}
    with engine.connect() as connection:
        for schema, name, column_name in connection.execute(COLUMNS).all():
            held_in = column(column_name, Text)
            searched = table(name, held_in, schema=schema)
            value = func.lower(cast(held_in, Text))
            for needle in _in_column(connection, searched, value, lowered):
                held.setdefault(f"{schema}.{name}.{column_name}", []).append(needle)
    return held


def _in_column(
    connection: Connection, searched: TableClause, value: ColumnElement[str], needles: list[str]
) -> list[str]:
    """Give the needles a column holds: none, as most columns, asked in one query."""
    if not needles:
        return []
    count = select(func.count()).select_from(searched)
    anywhere = or_(*(func.strpos(value, needle) > 0 for needle in needles))
    if connection.execute(count.where(anywhere)).scalar_one() == 0:
        return []
    return [
        needle
        for needle in needles
        if connection.execute(count.where(func.strpos(value, needle) > 0)).scalar_one()
    ]


def held_by_table(engine: Engine, but: Collection[str] = ()) -> dict[str, str]:
    """Give, for each table but those named (``schema.table``), a digest of every row it holds."""
    digests: dict[str, str] = {}
    with engine.connect() as connection:
        for schema, name in connection.execute(TABLES).all():
            if f"{schema}.{name}" in but:
                continue
            rows = connection.execute(select(text("*")).select_from(table(name, schema=schema)))
            lines = sorted(repr(tuple(row)) for row in rows)
            digests[f"{schema}.{name}"] = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    return digests
