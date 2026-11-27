# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A backup of the last published version, restored then migrated by the branch (US-2850).

``make migrations-backup`` has the production platform of the last published version take a backup,
its witness loaded — marked revisions among it —, and names the archive by
``WATERFALL_TEST_EARLIER_BACKUP`` (``wftools.migrationbackup``). The branch reads it as its
restoration does (``extracted``: the manifest, a version no newer, each dump checked), makes the
database of Waterfall again from its dump (``replace``), and applies its migrations — the path of an
installation that comes back from a backup of the version before, or that is updated from it.
Before the migrations and after them, the same reading: what each table holds, and every row that
belongs to a marked revision, on the columns the version had. A migration may add a column or a
row; it removes none, and changes nothing a marked revision holds (WF-DAT-0140): its amounts, and
the indicators it kept. Without the archive, as everywhere but in the family ``migrations``, the
tests are skipped.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from migrations_support import scratch_database
from sqlalchemy import Connection, Uuid, column, exists, func, select, table, text
from support import service_role

from waterfall.migrations.runner import upgrade
from waterfall.worker.backup import DATABASES
from waterfall.worker.restore import extracted, replace

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uuid import UUID

    from sqlalchemy import ColumnClause, ColumnElement, FromClause, TableClause

pytestmark = [
    pytest.mark.requirement("WF-DAT-0140-A"),
    pytest.mark.unexecuted(
        "skipped unless WATERFALL_TEST_EARLIER_BACKUP names a backup of the last published version"
    ),
]

ARCHIVE = "WATERFALL_TEST_EARLIER_BACKUP"
WATERFALL = DATABASES[0]
TABLES = text(
    "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
    "AND relkind IN ('r', 'p') AND NOT relispartition ORDER BY relname"
)
KEYS = text(
    "SELECT key.conrelid::regclass::text, key.confrelid::regclass::text, "
    "array(SELECT attname FROM unnest(key.conkey) WITH ORDINALITY AS k(number, place) "
    "JOIN pg_attribute ON attrelid = key.conrelid AND attnum = k.number ORDER BY k.place), "
    "array(SELECT attname FROM unnest(key.confkey) WITH ORDINALITY AS k(number, place) "
    "JOIN pg_attribute ON attrelid = key.confrelid AND attnum = k.number ORDER BY k.place) "
    "FROM pg_constraint AS key WHERE key.contype = 'f' "
    "AND key.connamespace = 'public'::regnamespace AND key.conparentid = 0"
)
"""The foreign keys of the schema, each with its table, the table it names, and their columns."""
MARKED = text("SELECT id FROM revision WHERE status = 'marked' ORDER BY id")
REVISION = "revision"
OF_A_REVISION = "revision_id"
LINES_OF_COST = "estimate_line"
"""Where a revision holds its amounts: its lines of the estimate."""


@dataclass(frozen=True, slots=True)
class Owner:
    """How the rows of a table belong to a revision: by a column of their own, or through a row.

    Without ``parent``, the column of the row itself names the revision — ``revision_id``, ``id``
    for the revisions. Else the row names, by the pairs of its columns and of the other's, a row of
    ``through``, which belongs to a revision as ``parent`` says.
    """

    column: str = ""
    through: str = ""
    pairs: tuple[tuple[str, str], ...] = ()
    parent: Owner | None = None
    depth: int = 0

    def columns(self) -> set[str]:
        """Return the columns of the row its condition names."""
        return {self.column} if self.parent is None else {mine for mine, _ in self.pairs}

    def condition(self, held: FromClause, marked: list[UUID]) -> ColumnElement[bool]:
        """Return the condition on a row of the table that it belongs to a revision marked."""
        if self.parent is None:
            return held.c[self.column].in_(marked)
        named = {other for _, other in self.pairs} | self.parent.columns()
        found = table(self.through, *(_key(name) for name in sorted(named)))
        owner = found.alias(f"owner_{self.depth}")
        joined = [owner.c[other] == held.c[mine] for mine, other in self.pairs]
        return exists().where(*joined, self.parent.condition(owner, marked))


def belonging(connection: Connection) -> dict[str, Owner]:
    """Say, for each table, how its rows belong to a marked revision.

    The revisions marked themselves; the rows of a table whose ``revision_id`` names one — its
    structure, its rates, the indicators it kept —; then, from one to the next, those of a table
    whose foreign key names such a row — the nodes of its structure, the lines of its nodes. Read
    from the catalogue of the version, before any migration, and asked again after: a column a
    migration dropped fails the reading after.
    """
    keys = [
        (source, target, list(columns), list(named))
        for source, target, columns, named in connection.execute(KEYS)
    ]
    owners = {REVISION: Owner("id")}
    for source, target, columns, _ in keys:
        if target == REVISION and source != REVISION and OF_A_REVISION in columns:
            owners[source] = Owner(OF_A_REVISION)
    found = True
    while found:
        found = False
        for source, target, columns, named in keys:
            if target != REVISION and target in owners and source not in owners:
                parent = owners[target]
                pairs = tuple(zip(columns, named, strict=True))
                owners[source] = Owner("", target, pairs, parent, parent.depth + 1)
                found = True
    return owners


def _key(name: str) -> ColumnClause[UUID]:
    """Name a column of keys: an identifier, of a revision or of a row of it."""
    return column(name, Uuid())


def _held(name: str, owner: Owner) -> TableClause:
    """Return the table of a reading, with the columns its condition names."""
    return table(name, *(_key(each) for each in sorted(owner.columns())))


class Reading:
    """What a database holds: the rows of each table, and those of the marked revisions."""

    def __init__(self, connection: Connection, owners: dict[str, Owner]) -> None:
        tables = list(connection.execute(TABLES).scalars())
        self.counts = {
            name: connection.execute(select(func.count()).select_from(table(name))).scalar_one()
            for name in tables
        }
        self.marked = list(connection.execute(MARKED).scalars())
        self.rows: dict[str, list[dict[str, Any]]] = {}
        for name, owner in owners.items():
            held = _held(name, owner).alias("held")
            selected = select(func.to_jsonb(held.table_valued())).where(
                owner.condition(held, self.marked)
            )
            self.rows[name] = list(connection.execute(selected).scalars())

    def held(self, table: str, columns: set[str]) -> list[str]:
        """Give the rows of the marked revisions in a table, on the columns named, in one order."""
        return sorted(
            json.dumps({column: row[column] for column in columns if column in row}, sort_keys=True)
            for row in self.rows.get(table, [])
        )


@pytest.fixture(scope="module")
def migrated(
    process_database_url: str, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[tuple[Reading, Reading]]:
    """Restore the backup in a database of its own, read it, migrate it, and read it again."""
    named = os.environ.get(ARCHIVE)
    if not named:
        pytest.skip(f"{ARCHIVE} names no backup of the last published version")
    folder = tmp_path_factory.mktemp("earlier-backup")
    dumps = extracted(Path(named), folder)
    with scratch_database(process_database_url, "waterfall_earlier") as engine:
        # The role of the service of the installation, which its migrations granted the tables to:
        # an installation restored keeps it (``replace`` restores without the rights of the source).
        with engine.begin() as connection:
            connection.execute(text(f'CREATE ROLE "{service_role(engine.url)}" NOLOGIN'))
        address = engine.url.render_as_string(hide_password=False)
        replace(WATERFALL, dumps[WATERFALL], address, folder)
        with engine.connect() as connection:
            owners = belonging(connection)
            before = Reading(connection, owners)
        upgrade(engine)
        with engine.connect() as connection:
            after = Reading(connection, owners)
        yield before, after


def test_the_backup_holds_marked_revisions_and_their_amounts(
    migrated: tuple[Reading, Reading],
) -> None:
    before, _ = migrated
    assert before.marked
    assert before.rows.get(LINES_OF_COST)


def test_a_backup_of_the_last_published_version_migrated_by_the_branch_loses_no_row(
    migrated: tuple[Reading, Reading],
) -> None:
    before, after = migrated
    lost = {
        table: (count, after.counts.get(table))
        for table, count in before.counts.items()
        if after.counts.get(table, -1) < count
    }
    assert lost == {}


def test_the_rows_of_a_marked_revision_are_unchanged_by_the_migrations_of_the_branch(
    migrated: tuple[Reading, Reading],
) -> None:
    before, after = migrated
    assert after.marked == before.marked
    changed = [
        table
        for table, rows in before.rows.items()
        if after.held(table, set(rows[0]) if rows else set())
        != before.held(table, set(rows[0]) if rows else set())
    ]
    assert changed == []
