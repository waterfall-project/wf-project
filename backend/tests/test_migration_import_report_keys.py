# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The keys of an import to its structure and its revision: 0040, 0041 (US-3060/L5, #4139)."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from costs_support import report_row
from migrations_support import partition_parts
from project_rows import insert_project, insert_revision, insert_structure
from sqlalchemy import delete, func, insert, select

from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.revisions.tables import CostStructure
from waterfall.migrations.runner import downgrade, upgrade

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection


def imported(connection: Connection, project_id: UUID, **aimed: UUID | None) -> UUID:
    """Write an import of an estimate of a project, aiming at what ``aimed`` names; give it."""
    row = report_row(project_id, kind="estimate", period_from=None, period_to=None, **aimed)
    connection.execute(insert(ImportReport).values(**row))
    return UUID(str(row["id"]))


def imports(engine: Engine) -> set[UUID]:
    """Give the imports the database keeps."""
    with engine.connect() as connection:
        return set(connection.scalars(select(ImportReport.id)))


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_imports_of_what_is_gone_are_deleted_and_the_others_follow_their_structure(
    empty_engine: Engine,
) -> None:
    # Propre à l'US (#4139) : une migration traite les pointeurs morts déjà en base — l'import
    # d'une structure disparue, d'une révision disparue, ou de celles d'un autre projet, est
    # supprimé (0040) ; celui qui ne nomme rien, ou ce qui existe, reste. Avec les clés (0041), les
    # partitions d'un projet d'avant ont celles d'un projet d'après, et l'import suit sa structure.
    # La descente de 0041 retire les clés, et un pointeur mort s'écrit de nouveau.
    upgrade(empty_engine, "0039")
    project, other, created = uuid4(), uuid4(), uuid4()
    revision, structure = uuid4(), uuid4()
    with empty_engine.begin() as connection:
        for each in (project, other):
            connection.execute(insert_project(id=each))
            connection.execute(select(func.create_project_partitions(each)))
        connection.execute(insert_revision(project, id=revision))
        connection.execute(insert_structure(project, revision, id=structure))
        kept = {
            imported(connection, project, structure_id=structure, revision_id=revision),
            imported(connection, project),
        }
        imported(connection, project, structure_id=uuid4(), revision_id=revision)
        imported(connection, project, structure_id=structure, revision_id=uuid4())
        imported(connection, other, structure_id=structure)
        imported(connection, other, revision_id=revision)
    upgrade(empty_engine, "0040")
    assert imports(empty_engine) == kept
    upgrade(empty_engine, "0041")
    with empty_engine.begin() as connection:
        connection.execute(insert_project(id=created))
        connection.execute(select(func.create_project_partitions(created)))
        assert partition_parts(connection, project) == partition_parts(connection, created)
        connection.execute(delete(CostStructure).where(CostStructure.id == structure))
    assert len(imports(empty_engine)) == 1
    downgrade(empty_engine, "0040")
    with empty_engine.begin() as connection:
        imported(connection, project, structure_id=uuid4(), revision_id=uuid4())
    assert len(imports(empty_engine)) == 2
    downgrade(empty_engine, "0039")
