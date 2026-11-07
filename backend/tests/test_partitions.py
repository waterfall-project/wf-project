# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revised tables, partitioned by project (WF-DAT-0050; EP-04, "Tables et migrations").

One partition per project, by list on its identifier, created by the function of the owner in the
transaction that creates the project; the plan of a reading of a revision reads the partition of
its project alone. The rows are written around the service, by the owner; the volumes, six hundred
projects, are EP-13's.
"""

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from project_rows import (
    drop_partitions,
    insert_project,
    insert_revision,
    insert_structure,
    partition_of,
    projects_with_partitions,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from waterfall.core.revisions.interface import create_project_partitions

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-DAT-0050-A")


def scanned(plan: Any) -> set[str]:
    """Give the relations a plan of PostgreSQL reads, in its whole tree."""
    found: set[str] = {plan["Relation Name"]} if "Relation Name" in plan else set()
    for child in plan.get("Plans", []):
        found |= scanned(child)
    return found


def plan_of(connection: Connection, query: str, **values: UUID) -> set[str]:
    """Give the relations the plan of a query reads."""
    explained = connection.execute(text(f"EXPLAIN (FORMAT JSON) {query}"), values).scalar_one()
    return scanned(explained[0]["Plan"])


def partitions(connection: Connection) -> set[str]:
    """Name the partitions of the cost structures."""
    rows = connection.execute(
        text(
            "SELECT inhrelid::regclass::text FROM pg_inherits "
            "WHERE inhparent = 'cost_structure'::regclass"
        )
    )
    return set(rows.scalars())


def test_the_plan_of_a_reading_of_a_revision_reads_the_partition_of_its_project_alone(
    database: Database, owner: Engine
) -> None:
    # « Le plan d'exécution d'une lecture de révision ne parcourt que la partition du projet. » A
    # reading by the revision alone would read every partition: the plan says which it reads.
    del database
    with projects_with_partitions(owner, 3) as projects, owner.begin() as connection:
        revisions: dict[UUID, UUID] = {}
        for project_id in projects:
            revisions[project_id] = uuid4()
            connection.execute(insert_revision(project_id, id=revisions[project_id]))
            connection.execute(insert_structure(project_id, revisions[project_id]))
        connection.execute(text("ANALYZE cost_structure"))
        first = projects[0]
        reading = (
            "SELECT * FROM cost_structure WHERE project_id = :project AND revision_id = :revision"
        )
        assert plan_of(connection, reading, project=first, revision=revisions[first]) == {
            partition_of(first)
        }
        everywhere = "SELECT * FROM cost_structure WHERE revision_id = :revision"
        assert plan_of(connection, everywhere, revision=revisions[first]) == {
            partition_of(project_id) for project_id in projects
        }


def test_the_service_creates_the_partitions_of_a_project_in_the_transaction_that_creates_it(
    database: Database, owner: Engine
) -> None:
    # Through the interface of the revisions, as the creation of a project will: rolled back with
    # its transaction, written with it; a second time, refused.
    project_id = uuid4()
    with Session(database.engine) as session:
        session.execute(insert_project(id=project_id))
        create_project_partitions(session, project_id)
        assert partition_of(project_id) in partitions(session.connection())
        session.rollback()
    try:
        with database.engine.connect() as connection:
            assert partition_of(project_id) not in partitions(connection)
        with database.transaction() as session:
            session.execute(insert_project(id=project_id))
            create_project_partitions(session, project_id)
        with pytest.raises(DBAPIError) as twice, database.transaction() as session:
            create_project_partitions(session, project_id)
        assert getattr(twice.value.orig, "sqlstate", None) == "42P07"
    finally:
        with owner.begin() as connection:
            drop_partitions(connection, project_id)


def test_a_row_of_a_project_without_its_partitions_is_refused(
    database: Database, owner: Engine
) -> None:
    # Each project has its partition, or no revised row: none holds the rows of several projects.
    project_id = uuid4()
    with owner.begin() as connection:
        connection.execute(insert_project(id=project_id))
        revision_id = uuid4()
        connection.execute(insert_revision(project_id, id=revision_id))
    with pytest.raises(IntegrityError) as refused, database.engine.begin() as connection:
        connection.execute(insert_structure(project_id, revision_id))
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"
