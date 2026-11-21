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

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.tables import CostStructure, Revision

if TYPE_CHECKING:
    from collections.abc import Collection, Generator

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
    """Give the columns of the main structure of a revision, with the changes asked for.

    A differential keeps the counter of the main structure its base was taken at (US-3050): the
    first, unless the changes say another.
    """
    structure_id = uuid4()
    differential = overrides.get("kind") == "amendment"
    return {
        "project_id": project_id,
        "id": structure_id,
        "revision_id": revision_id,
        "kind": "main",
        "label": "Principale",
        "is_merged": False,
        "lineage_id": structure_id,
        **({"main_lock_version": 1} if differential else {}),
        **STAMP,
        **overrides,
    }


def base_row(project_id: UUID, revision_id: UUID, differential_id: object) -> dict[str, object]:
    """Give the columns of the base of a differential, empty, in its revision (US-3050).

    What the reading of a differential written around the service compares it to: every node it
    holds is added.
    """
    return structure_row(
        project_id, revision_id, kind="base", label="Base", differential_id=differential_id
    )


def risk_row(project_id: UUID, **overrides: object) -> dict[str, object]:
    """Give the columns of a risk of a project, at its first counter, with the changes asked for.

    What a structure of the kind ``risk`` and a node an occurrence merged name (EP-08).
    """
    return {
        "id": uuid4(),
        "project_id": project_id,
        "label": "Retard du fournisseur",
        "description": None,
        "mitigation_notes": None,
        "lock_version": 1,
        **STAMP,
        **overrides,
    }


def delete_structure(owner: Engine, structure_id: UUID) -> None:
    """Remove a structure a test wrote, with its nodes, its tasks and its lines, as the owner.

    The one place that knows what hangs from a structure: a test that wrote one by hand calls it in
    its ``finally``, and a table that comes to depend on the nodes is added here, not in each test.
    The base of a differential goes first, which names it (US-3050).
    """
    with owner.begin() as connection:
        bases = connection.scalars(
            select(CostStructure.id).where(CostStructure.differential_id == structure_id)
        ).all()
        for each in (*bases, structure_id):
            nodes = select(Node.id).where(Node.structure_id == each)
            connection.execute(delete(EstimateLine).where(EstimateLine.node_id.in_(nodes)))
            connection.execute(delete(Task).where(Task.node_id.in_(nodes)))
            connection.execute(delete(Node).where(Node.structure_id == each))
            connection.execute(delete(CostStructure).where(CostStructure.id == each))


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
# names is dropped after the other's. The rates and the images of the estimate, and the indicators,
# name a revision alone, which is no partitioned table; the rows of the risks name the structures
# and the nodes (EP-08).
REVISED = (
    "risk_reference_share",
    "risk_review",
    "risk_evaluation",
    "revision_indicator",
    "structure_reading",
    "estimate_line",
    "revision_rate",
    "revision_role",
    "revision_calendar",
    "revision_category",
    "task_link",
    "task",
    "node",
    "cost_structure",
)
PARTITIONS_OF = text(
    "SELECT child.relname FROM pg_inherits JOIN pg_class AS child ON child.oid = inhrelid "
    "JOIN pg_class AS parent ON parent.oid = inhparent WHERE parent.relname = :parent "
    "ORDER BY child.relname"
)


# The length of the identifier of a project that ends the name of each of its partitions.
HEX = 32

# The role under which the triggers and the keys of a transaction are off, a superuser's alone.
REPLICA = text("SET LOCAL session_replication_role = replica")


def unguarded(connection: Connection) -> None:
    """Turn the triggers and the keys off for the rest of the transaction of ``connection``."""
    connection.execute(REPLICA)


def drop_partitions(connection: Connection, project_id: UUID | None = None) -> None:
    """Drop the partitions of a project, or of every project, with their rows, as a superuser.

    A partition a key of a partitioned table names — the cost structures, the nodes — is neither
    dropped nor detached while it is attached or a row names it: each is emptied, guards and keys
    off, detached, then dropped, the tables that name it first. The guards and the keys stay off for
    the rest of the transaction (``REPLICA``, set by ``unguarded``): a caller that empties other
    tables after it — the journal, whose triggers refuse a deletion — sets it itself, so as not to
    depend on this.
    """
    unguarded(connection)
    for parent in REVISED:
        for name in connection.scalars(PARTITIONS_OF, {"parent": parent}).all():
            if project_id is None or name.endswith(project_id.hex):
                connection.execute(delete(table(name)))
                connection.execute(text(f'ALTER TABLE "{parent}" DETACH PARTITION "{name}"'))
                connection.execute(text(f'DROP TABLE "{name}"'))


def partitioned_projects(connection: Connection) -> list[UUID]:
    """Give the projects that have partitions, by the suffix of their names, in their order."""
    names = [
        name for parent in REVISED for name in connection.scalars(PARTITIONS_OF, {"parent": parent})
    ]
    return sorted({UUID(hex=name[-HEX:]) for name in names})


def drop_every_partition(owner: Engine, keep: Collection[UUID] = ()) -> None:
    """Drop the partitions of every project but ``keep``'s, a transaction for each project (#4051).

    One transaction for all held a lock on every partition at once — fourteen tables a project,
    five projects a fabric of the portfolio —, beyond what the server holds; each project now holds
    its own, released at its commit. The projects kept keep theirs, empty or not: the witness's,
    that the next test that asks for it lays its rows in without creating them again.
    """
    with owner.connect() as connection:
        projects = partitioned_projects(connection)
    for project_id in projects:
        if project_id in keep:
            continue
        with owner.begin() as connection:
            drop_partitions(connection, project_id)


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
