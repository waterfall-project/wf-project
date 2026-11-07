# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rows of the witness, loaded once by each process of the tests and laid again after.

Loading the witness goes through the rules of every module — two thousand hourly rates, each set
as the service sets it —: three seconds on a workstation, many more on a runner of the chain, for
each test that asks for it. The first test of a process loads it as the command does; its rows are
then copied, table by table, and the tests after it find them copied back, the partitions of its
projects created first (WF-DAT-0050), its triggers off for that transaction alone as when they are
deleted (``database``). The rows laid are those the command wrote: what a test reads of the
witness is what the command loaded.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from psycopg import sql

from waterfall.core.access_roles.tables import WRITTEN_BY_MIGRATION
from waterfall.platform.database import Base

if TYPE_CHECKING:
    from collections.abc import Generator

    from psycopg import Connection
    from sqlalchemy import Engine


@dataclass(frozen=True)
class WitnessRows:
    """The rows of each table the witness wrote, in the binary format of ``COPY``."""

    tables: tuple[tuple[str, tuple[str, ...], bytes], ...]
    """The name of each table, its columns, and its rows."""
    projects: tuple[str, ...]
    """The projects whose partitions the rows of the revised tables need."""


def _tables() -> list[tuple[str, tuple[str, ...]]]:
    """Name the tables the rows of a test go in, those the migrations fill left out."""
    return [
        (table.name, tuple(column.name for column in table.columns))
        for table in Base.metadata.sorted_tables
        if not table.info.get(WRITTEN_BY_MIGRATION)
    ]


@contextmanager
def _connection(owner: Engine) -> Generator[Connection]:
    """Give the connection of psycopg under one of the engine, committed, then given back."""
    raw = owner.raw_connection()
    try:
        connection = cast("Connection", raw.driver_connection)
        yield connection
        connection.commit()
    finally:
        raw.close()


def _columns(columns: tuple[str, ...]) -> sql.Composed:
    return sql.SQL(", ").join(sql.Identifier(column) for column in columns)


def copied(owner: Engine) -> WitnessRows:
    """Copy the rows the witness wrote, as the owner of the tables."""
    tables: list[tuple[str, tuple[str, ...], bytes]] = []
    with _connection(owner) as connection, connection.cursor() as cursor:
        for name, columns in _tables():
            query = sql.SQL("COPY (SELECT {} FROM {}) TO STDOUT (FORMAT BINARY)").format(
                _columns(columns), sql.Identifier(name)
            )
            with cursor.copy(query) as copy:
                rows = b"".join(bytes(block) for block in copy)
            tables.append((name, columns, rows))
        cursor.execute("SELECT id::text FROM project")
        projects = tuple(str(row[0]) for row in cursor.fetchall())
    return WitnessRows(tuple(tables), projects)


def laid(owner: Engine, rows: WitnessRows) -> None:
    """Lay the rows copied again, in one transaction of the owner, its triggers off."""
    with _connection(owner) as connection, connection.cursor() as cursor:
        cursor.execute("SET LOCAL session_replication_role = replica")
        for project in rows.projects:
            cursor.execute("SELECT create_project_partitions(%s::uuid)", (project,))
        for name, columns, data in rows.tables:
            query = sql.SQL("COPY {} ({}) FROM STDIN (FORMAT BINARY)").format(
                sql.Identifier(name), _columns(columns)
            )
            with cursor.copy(query) as copy:
                copy.write(data)
