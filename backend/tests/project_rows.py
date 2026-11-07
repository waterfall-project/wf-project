# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Projects, revisions and structures written around the service, by the owner of the tables.

What the tests of the tables and of the partitions of EP-04 write before any story serves them:
each row valid unless a test changes it, and the partitions of a project created by their
function, then dropped, so that the database of the tests keeps none of them.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, select, table, text

from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure, Revision

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection
    from sqlalchemy.sql import Executable

AT = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)
STAMP: dict[str, object] = {"created_at": AT, "updated_at": AT}


def project_row(**overrides: object) -> dict[str, object]:
    """Give the columns of a project in its first state, with the changes a test asks for."""
    return {
        "id": uuid4(),
        "label": "Ligne de convoyage",
        "state": "created",
        "inflation_rate": Decimal(0),
        "win_probability": Decimal(0),
        **STAMP,
        **overrides,
    }


def revision_row(project_id: UUID, **overrides: object) -> dict[str, object]:
    """Give the columns of the current revision of a project, with the changes asked for."""
    revision_id = uuid4()
    return {
        "id": revision_id,
        "project_id": project_id,
        "status": "draft",
        "reference_year": 2026,
        "is_reference": False,
        "lineage_id": revision_id,
        **STAMP,
        **overrides,
    }


# What a revision marked holds besides: its name of version and the moment of its marking.
MARKED: dict[str, object] = {"status": "marked", "version_name": "v1.0", "marked_at": AT}


def structure_row(project_id: UUID, revision_id: UUID, **overrides: object) -> dict[str, object]:
    """Give the columns of the main structure of a revision, with the changes asked for."""
    structure_id = uuid4()
    return {
        "project_id": project_id,
        "id": structure_id,
        "revision_id": revision_id,
        "kind": "main",
        "label": "Principale",
        "is_merged": False,
        "lineage_id": structure_id,
        **STAMP,
        **overrides,
    }


def insert_project(**overrides: object) -> Executable:
    """Give the insertion of a project."""
    return insert(Project).values(**project_row(**overrides))


def insert_revision(project_id: UUID, **overrides: object) -> Executable:
    """Give the insertion of a revision of a project."""
    return insert(Revision).values(**revision_row(project_id, **overrides))


def insert_structure(project_id: UUID, revision_id: UUID, **overrides: object) -> Executable:
    """Give the insertion of a structure of a revision."""
    return insert(CostStructure).values(**structure_row(project_id, revision_id, **overrides))


def partition_of(project_id: UUID) -> str:
    """Name the partition of the cost structures of a project."""
    return f"cost_structure_p_{project_id.hex}"


# The revised tables, each before the tables its keys name: the partition of a table that another
# names is dropped after the other's.
REVISED = ("task_link", "task", "node", "cost_structure")
PARTITIONS_OF = text(
    "SELECT child.relname FROM pg_inherits JOIN pg_class AS child ON child.oid = inhrelid "
    "JOIN pg_class AS parent ON parent.oid = inhparent WHERE parent.relname = :parent "
    "ORDER BY child.relname"
)


def drop_partitions(connection: Connection, project_id: UUID | None = None) -> None:
    """Drop the partitions of a project, or of every project, with their rows, as a superuser.

    A partition a key of a partitioned table names — the cost structures, the nodes — is neither
    dropped nor detached while it is attached or a row names it: each is emptied, guards and keys
    off for the transaction, detached, then dropped, the tables that name it first.
    """
    connection.execute(text("SET LOCAL session_replication_role = replica"))
    for parent in REVISED:
        for name in connection.scalars(PARTITIONS_OF, {"parent": parent}).all():
            if project_id is None or name.endswith(project_id.hex):
                connection.execute(delete(table(name)))
                connection.execute(text(f'ALTER TABLE "{parent}" DETACH PARTITION "{name}"'))
                connection.execute(text(f'DROP TABLE "{name}"'))


@contextmanager
def projects_with_partitions(owner: Engine, count: int = 1) -> Generator[list[UUID]]:
    """Write projects as the owner, each with its partitions created by their function.

    The partitions are dropped afterwards, rows and all: the fixture ``database``, which the test
    asks for too, empties the tables of every row left.
    """
    projects = [uuid4() for _ in range(count)]
    with owner.begin() as connection:
        for project_id in projects:
            connection.execute(insert_project(id=project_id))
            connection.execute(select(func.create_project_partitions(project_id)))
    try:
        yield projects
    finally:
        with owner.begin() as connection:
            for project_id in projects:
                drop_partitions(connection, project_id)
