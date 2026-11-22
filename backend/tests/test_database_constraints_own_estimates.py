# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the abandonments of an own estimate forbid (EP-30, migration 0044).

The constraints of ``own_estimate_abandonment``, one refusal each; its guard, which refuses any
write of a row of a marked revision, owner included; and its truncation refused. Every row is
written around the services of the modules, by the owner of the tables, under a current revision.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from project_rows import (
    AT,
    MARKED,
    insert_revision,
    insert_structure,
    projects_with_partitions,
    risk_row,
)
from sqlalchemy import Engine, delete, insert, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from waterfall.core.revisions.tables import OwnEstimateAbandonment, Revision
from waterfall.core.risks.tables import Risk
from waterfall.platform.database import Base, Database

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.sql import Executable

pytestmark = pytest.mark.requirement("WF-DAT-0090-A")

# What the guard says when it refuses (of the form of 0035's).
ROW_REFUSED = "a row of a marked revision is never written"


@dataclass(frozen=True)
class Parents:
    """What an abandonment names: a project, its current revision and the own estimate of a risk.

    ``other`` the main structure of a marked revision before it, of another revision than the rows.
    """

    project: UUID
    revision: UUID
    structure: UUID
    other: UUID


@pytest.fixture
def parents(database: Database, owner: Engine) -> Iterator[Parents]:
    """Write the parents of the rows a test tries, around the service."""
    del database
    with projects_with_partitions(owner) as (project,):
        former, revision, risk, own, former_main = (uuid4() for _ in range(5))
        with owner.begin() as connection:
            connection.execute(insert_revision(project, id=former))
            connection.execute(insert_structure(project, former, id=former_main))
            connection.execute(
                update(Revision)
                .where(Revision.id == former)
                .values(**{**MARKED, "version_name": "v0.9"})
            )
            connection.execute(insert_revision(project, id=revision))
            connection.execute(insert_structure(project, revision))
            connection.execute(insert(Risk).values(**risk_row(project, id=risk)))
            connection.execute(
                insert_structure(project, revision, id=own, kind="risk", risk_id=risk)
            )
        yield Parents(project, revision, own, former_main)


def valid(parents: Parents) -> dict[str, object]:
    """Give the columns of a node abandoned by the own estimate of the parents."""
    return {
        "project_id": parents.project,
        "id": uuid4(),
        "revision_id": parents.revision,
        "structure_id": parents.structure,
        "node_lineage_id": uuid4(),
        "predecessor_lineage_id": None,
        "successor_lineage_id": None,
        "created_at": AT,
        "created_by": None,
    }


def row(parents: Parents, **overrides: object) -> Executable:
    """Give the insertion of an abandonment, valid but for the changes a test asks for."""
    return insert(OwnEstimateAbandonment).values(**{**valid(parents), **overrides})


def refusal(owner: Engine, statement: Executable) -> str:
    """Run a statement the database must refuse; give its constraint, the table's."""
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(statement)
    cause = raised.value.orig
    assert isinstance(cause, psycopg.Error)
    name = cause.diag.constraint_name or ""
    with owner.connect() as connection:
        found = connection.scalar(
            text(
                "WITH RECURSIVE up(parent, name) AS (SELECT conparentid, conname "
                "FROM pg_constraint WHERE conname = :name UNION SELECT c.conparentid, c.conname "
                "FROM pg_constraint AS c JOIN up ON c.oid = up.parent) "
                "SELECT name FROM up WHERE parent = 0 LIMIT 1"
            ),
            {"name": name},
        )
        index = connection.scalar(
            text(
                "SELECT inhparent::regclass::text FROM pg_inherits "
                "WHERE inhrelid = to_regclass(:name)"
            ),
            {"name": name},
        )
    return index or found or name


LINK = {"node_lineage_id": None, "predecessor_lineage_id": uuid4(), "successor_lineage_id": uuid4()}
NODE_OR_LINK = "ck_own_estimate_abandonment_node_or_link"
# A value the parents hold, resolved when the test runs: a structure of the marked revision.
OTHER = "OTHER"
REFUSALS: list[tuple[dict[str, object], str]] = [
    # Nothing abandoned, a node and a link at once, a link of one task.
    ({"node_lineage_id": None}, NODE_OR_LINK),
    ({"predecessor_lineage_id": uuid4(), "successor_lineage_id": uuid4()}, NODE_OR_LINK),
    ({"node_lineage_id": None, "predecessor_lineage_id": uuid4()}, NODE_OR_LINK),
    ({"node_lineage_id": None, "successor_lineage_id": uuid4()}, NODE_OR_LINK),
    # The structure with its revision: an unknown one, or one of another revision.
    ({"structure_id": uuid4()}, "fk_own_estimate_abandonment_project_id_cost_structure"),
    ({"structure_id": OTHER}, "fk_own_estimate_abandonment_project_id_cost_structure"),
    ({"created_by": uuid4()}, "fk_own_estimate_abandonment_created_by_user_account"),
]


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    REFUSALS,
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_an_abandonment_that_breaks_a_rule(
    parents: Parents, owner: Engine, overrides: dict[str, object], constraint: str
) -> None:
    held = {OTHER: parents.other}
    changes = {
        column: held.get(value, value) if isinstance(value, str) else value
        for column, value in overrides.items()
    }
    assert refusal(owner, row(parents, **changes)) == constraint


@pytest.mark.parametrize("abandoned", [{"node_lineage_id": uuid4()}, LINK])
def test_the_database_refuses_an_abandonment_told_twice(
    parents: Parents, owner: Engine, abandoned: dict[str, object]
) -> None:
    # A node, or a link, is abandoned once by an own estimate: told twice, the second is refused.
    with owner.begin() as connection:
        connection.execute(row(parents, **abandoned))
    refused = refusal(owner, row(parents, **abandoned))
    led = "node_lineage_id" if abandoned.get("node_lineage_id") else "predecessor_lineage_id"
    assert refused == f"uq_own_estimate_abandonment_{led}"


def test_every_named_constraint_of_the_abandonments_has_its_refusal_tried() -> None:
    table = Base.metadata.tables[OwnEstimateAbandonment.__tablename__]
    named = {
        str(constraint.name)
        for constraint in table.constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    }
    tried = {constraint for _, constraint in REFUSALS} | {
        "uq_own_estimate_abandonment_node_lineage_id",
        "uq_own_estimate_abandonment_predecessor_lineage_id",
    }
    assert named == tried


@pytest.mark.requirement("WF-REV-0020-A")
def test_an_abandonment_of_a_marked_revision_is_never_written(
    parents: Parents, owner: Engine
) -> None:
    # Written while its revision is current, then the revision marked: a change, a deletion and a
    # new row of it are refused, owner included, by the guard of the form of the risks'.
    with owner.begin() as connection:
        connection.execute(row(parents))
        connection.execute(update(Revision).where(Revision.id == parents.revision).values(**MARKED))
    of_revision = OwnEstimateAbandonment.revision_id == parents.revision
    for statement in (
        update(OwnEstimateAbandonment).where(of_revision).values(node_lineage_id=uuid4()),
        delete(OwnEstimateAbandonment).where(of_revision),
        row(parents),
    ):
        with pytest.raises(DBAPIError, match=ROW_REFUSED), owner.begin() as connection:
            connection.execute(statement)


@pytest.mark.requirement("WF-DAT-0050-A")
def test_the_abandonments_are_never_truncated(parents: Parents, owner: Engine) -> None:
    table = OwnEstimateAbandonment.__tablename__
    for truncated in (table, f"{table}_p_{parents.project.hex}"):
        with pytest.raises(DBAPIError, match="never truncated"), owner.begin() as connection:
            connection.execute(text(f'TRUNCATE TABLE "{truncated}" CASCADE'))
