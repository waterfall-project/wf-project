# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the tables of the estimate forbid, and any write of a marked revision.

The constraints of the five tables of US-1490/L1 (migration 0025), one refusal each, as
``test_database_constraints_planning.py`` tries those of EP-06; the cascade the design decides, a
line with its node; and the guards of the five tables, which refuse, owner included, any write of a
row of a marked revision and any truncation, as ``test_revision_immutability.py`` tries those of the
planning. Every row is written around the services of the modules, by the owner of the tables.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from estimate_support import (
    Bearer,
    LineReference,
    calendar_image_row,
    category_image_row,
    insert_line,
    line_row,
    rate_row,
    role_image_row,
    write_reference,
)
from planning_support import insert_task, node_row
from project_rows import MARKED, STAMP, insert_project, insert_revision, insert_structure
from project_rows import projects_with_partitions as with_partitions
from sqlalchemy import Engine, delete, func, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from waterfall.api.contract import models
from waterfall.core.estimate.tables import (
    COST_TYPE_KINDS,
    EstimateLine,
    RevisionCalendar,
    RevisionCategory,
    RevisionRate,
    RevisionRole,
)
from waterfall.core.planning.tables import Node
from waterfall.core.projects.tables import Subproject
from waterfall.core.revisions.tables import Revision
from waterfall.platform.database import Base, Database

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine import Connection
    from sqlalchemy.sql import Executable

# The five tables of US-1490/L1.
TABLES: tuple[type[Base], ...] = (
    EstimateLine,
    RevisionRate,
    RevisionRole,
    RevisionCalendar,
    RevisionCategory,
)
IMAGES: tuple[type[Base], ...] = (RevisionRole, RevisionCalendar, RevisionCategory)

type Refusal = tuple[type[Base], dict[str, object], str]


@dataclass(frozen=True)
class Parents:
    """What a row of a test names: a project, its current revision, its structure and a task.

    The task bears the node of a line without its facet, ``line``; the project a subproject, and
    another project one of its own; the reference a category of labour and a role.
    """

    project: UUID
    revision: UUID
    structure: UUID
    task: UUID
    line: UUID
    subproject: UUID
    foreign_subproject: UUID
    reference: LineReference


def subproject(connection: Connection, project_id: UUID, code: str) -> UUID:
    """Write a subproject of a project; give it."""
    subproject_id = uuid4()
    connection.execute(
        insert(Subproject).values(
            id=subproject_id, project_id=project_id, code=code, label=code, **STAMP
        )
    )
    return subproject_id


@pytest.fixture
def parents(database: Database, owner: Engine) -> Iterator[Parents]:
    """Write the parents of the rows a test tries, around the service."""
    del database
    with with_partitions(owner) as (project,):
        revision, structure, line, foreign = (uuid4() for _ in range(4))
        with owner.begin() as connection:
            reference = write_reference(connection)
            connection.execute(insert_revision(project, id=revision))
            connection.execute(insert_structure(project, revision, id=structure))
            task = insert_task(connection, project, revision, structure)
            node = node_row(project, revision, structure, id=line)
            connection.execute(
                insert(Node).values({**node, "kind": "estimate_line", "parent_id": task})
            )
            owned = subproject(connection, project, "SP1")
            connection.execute(insert_project(id=foreign))
            other = subproject(connection, foreign, "SP2")
        yield Parents(project, revision, structure, task, line, owned, other, reference)


def constraint_of(engine: Engine, error: IntegrityError) -> str:
    """Give the constraint of the table a refusal comes from, that of its partition named so."""
    cause = error.orig
    assert isinstance(cause, psycopg.Error)
    name = cause.diag.constraint_name or ""
    with engine.connect() as connection:
        constraint = connection.scalar(
            text(
                "WITH RECURSIVE up(oid, parent, name) AS (SELECT oid, conparentid, conname "
                "FROM pg_constraint WHERE conname = :name UNION SELECT c.oid, c.conparentid, "
                "c.conname FROM pg_constraint AS c JOIN up ON c.oid = up.parent) "
                "SELECT name FROM up WHERE parent = 0 LIMIT 1"
            ),
            {"name": name},
        )
        index = connection.scalar(
            text(
                "WITH RECURSIVE up(oid) AS (SELECT to_regclass(:name)::oid UNION "
                "SELECT inhparent FROM pg_inherits JOIN up ON inhrelid = up.oid) "
                "SELECT relname FROM pg_class JOIN up ON pg_class.oid = up.oid "
                "WHERE NOT EXISTS (SELECT 1 FROM pg_inherits WHERE inhrelid = up.oid)"
            ),
            {"name": name},
        )
    return constraint or index or name


def valid(table: type[Base], parents: Parents) -> dict[str, object]:
    """Give the columns of a valid row of a table, under the parents of the test."""
    project, revision, reference = parents.project, parents.revision, parents.reference
    rows: dict[type[Base], dict[str, object]] = {
        EstimateLine: line_row(project, parents.line, reference),
        RevisionRate: rate_row(project, revision, reference.category),
        RevisionRole: role_image_row(project, revision, reference),
        RevisionCalendar: calendar_image_row(project, revision, reference),
        RevisionCategory: category_image_row(project, revision, reference),
    }
    return rows[table]


def row(table: type[Base], parents: Parents, **overrides: object) -> Executable:
    """Give the insertion of a row of a table, valid but for the changes a test asks for."""
    return insert(table).values(**{**valid(table, parents), **overrides})


def bounds(table: type[Base], column: str, longest: int) -> list[Refusal]:
    """Give the three refusals of a bounded text: empty, too long, blank."""
    name = table.__tablename__
    return [
        (table, {column: ""}, f"ck_{name}_{column}_length"),
        (table, {column: "x" * (longest + 1)}, f"ck_{name}_{column}_length"),
        (table, {column: " \t"}, f"ck_{name}_{column}_not_blank"),
    ]


def of_a_revision(table: type[Base]) -> list[Refusal]:
    """Give the refusals of a rate or an image: an unknown revision, a second row of the object."""
    name = table.__tablename__
    return [
        (table, {"revision_id": uuid4()}, f"fk_{name}_project_id_revision"),
        (table, {"revision_id": TAKEN}, f"uq_{name}_revision_id"),
    ]


# A value the parents hold: the task, which never bears a line, a subproject of the project, one of
# another project, a revision already holding the row tried.
TAKEN = "TAKEN"
TASK = "TASK"
OWN = "OWN"
FOREIGN = "FOREIGN"
# A line of another kind than labour: a disbursement, neither role nor hours.
DISBURSEMENT = {"resource_role_id": None, "hours": None, "unit_disbursement": Decimal("120.00")}

REFUSALS: list[Refusal] = [
    (EstimateLine, {"node_id": TASK}, "fk_estimate_line_project_id_node"),
    (EstimateLine, {"kind": "task"}, "ck_estimate_line_kind_estimate_line"),
    *bounds(EstimateLine, "label", 300),
    (EstimateLine, {"quantity": Decimal(-1)}, "ck_estimate_line_quantity_not_negative"),
    (EstimateLine, {"hours": Decimal(-1)}, "ck_estimate_line_hours_not_negative"),
    (
        EstimateLine,
        {**DISBURSEMENT, "unit_disbursement": Decimal(-1)},
        "ck_estimate_line_unit_disbursement_not_negative",
    ),
    (EstimateLine, {"payment_delay_days": -1}, "ck_estimate_line_payment_delay_days_not_negative"),
    (EstimateLine, {"hours": None}, "ck_estimate_line_hours_of_a_role"),
    (EstimateLine, {**DISBURSEMENT, "hours": Decimal(1)}, "ck_estimate_line_hours_of_a_role"),
    (
        EstimateLine,
        {"unit_disbursement": Decimal(1)},
        "ck_estimate_line_unit_disbursement_without_role",
    ),
    (
        EstimateLine,
        {**DISBURSEMENT, "unit_disbursement": None},
        "ck_estimate_line_unit_disbursement_without_role",
    ),
    (EstimateLine, {"consumption_year": 1999}, "ck_estimate_line_consumption_year_bound"),
    (EstimateLine, {"consumption_year": 2101}, "ck_estimate_line_consumption_year_bound"),
    (EstimateLine, {"lock_version": -1}, "ck_estimate_line_lock_version_not_negative"),
    (
        EstimateLine,
        {"cost_category_id": uuid4()},
        "fk_estimate_line_cost_category_id_cost_category",
    ),
    (
        EstimateLine,
        {"resource_role_id": uuid4()},
        "fk_estimate_line_resource_role_id_resource_role",
    ),
    (EstimateLine, {"subproject_id": FOREIGN}, "fk_estimate_line_project_id_subproject"),
    (EstimateLine, {"created_by": uuid4()}, "fk_estimate_line_created_by_user_account"),
    (EstimateLine, {"updated_by": uuid4()}, "fk_estimate_line_updated_by_user_account"),
    *of_a_revision(RevisionRate),
    (RevisionRate, {"origin": "entered"}, "ck_revision_rate_origin_known"),
    (RevisionRate, {"amount": Decimal(0)}, "ck_revision_rate_amount_positive"),
    *of_a_revision(RevisionRole),
    (RevisionRole, {"lock_version": -1}, "ck_revision_role_lock_version_not_negative"),
    *of_a_revision(RevisionCalendar),
    (RevisionCalendar, {"lock_version": -1}, "ck_revision_calendar_lock_version_not_negative"),
    *of_a_revision(RevisionCategory),
    (RevisionCategory, {"lock_version": -1}, "ck_revision_category_lock_version_not_negative"),
    (RevisionCategory, {"cost_type_kind": "other"}, "ck_revision_category_cost_type_kind_known"),
]


def resolved(parents: Parents, overrides: dict[str, object]) -> dict[str, object]:
    """Give the values a refusal tries, the ones the parents hold put in."""
    named: dict[object, object] = {
        TASK: parents.task,
        OWN: parents.subproject,
        FOREIGN: parents.foreign_subproject,
        TAKEN: parents.revision,
    }
    return {
        column: named.get(value, value) if isinstance(value, str) else value
        for column, value in overrides.items()
    }


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    REFUSALS,
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_row_of_the_estimate_that_breaks_a_rule(
    owner: Engine,
    parents: Parents,
    table: type[Base],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    if overrides.get("revision_id") == TAKEN:
        with owner.begin() as connection:
            connection.execute(row(table, parents))
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(row(table, parents, **resolved(parents, overrides)))
    assert constraint_of(owner, raised.value) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_a_line_of_labour_and_a_line_of_disbursement_of_the_project_are_written(
    owner: Engine, parents: Parents
) -> None:
    # The two forms of a line the constraints admit, the second under a subproject of its project.
    with owner.begin() as connection:
        bearer = Bearer(parents.project, parents.revision, parents.structure, parents.task)
        insert_line(connection, bearer, parents.reference, rank=2)
        connection.execute(
            row(EstimateLine, parents, subproject_id=parents.subproject, **DISBURSEMENT)
        )
        held = connection.execute(
            select(EstimateLine.resource_role_id, EstimateLine.subproject_id).order_by(
                EstimateLine.hours.desc().nulls_last()
            )
        ).all()
    assert [tuple(found) for found in held] == [
        (parents.reference.role, None),
        (None, parents.subproject),
    ]


@pytest.mark.requirement("WF-DAT-0090-A")
def test_every_named_constraint_of_the_estimate_has_its_refusal_tried() -> None:
    tables = [Base.metadata.tables[table.__tablename__] for table in TABLES]
    named = {
        str(constraint.name)
        for table in tables
        for constraint in table.constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    } | {str(index.name) for table in tables for index in table.indexes if index.unique}
    tried = {constraint for _, _, constraint in REFUSALS}
    assert named == tried


def count(owner: Engine, table: type[Base]) -> int:
    """Count the rows of a table."""
    with owner.connect() as connection:
        return connection.execute(select(func.count()).select_from(table)).scalar_one()


@pytest.mark.requirement("WF-DAT-0090-A")
def test_inside_a_current_revision_a_task_takes_its_lines_with_it(
    owner: Engine, parents: Parents
) -> None:
    # The cascade the design decides (EP-07, "Tables et migrations"): a line follows its node, which
    # follows its task; the rates and the images, which name the revision alone, stay.
    with owner.begin() as connection:
        connection.execute(row(EstimateLine, parents))
        connection.execute(row(RevisionRate, parents))
        connection.execute(delete(Node).where(Node.id == parents.task))
    assert [count(owner, table) for table in (Node, EstimateLine, RevisionRate)] == [0, 0, 1]


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_kinds_of_a_nature_an_image_keeps_are_the_enumeration_of_the_contract(
    owner: Engine,
) -> None:
    values = [member.value for member in models.CostTypeKind]
    enumeration: type[StrEnum] = models.CostTypeKind
    assert issubclass(enumeration, StrEnum)
    with owner.connect() as connection:
        definition = connection.scalar(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'ck_revision_category_cost_type_kind_known'"
            )
        )
    assert list(COST_TYPE_KINDS) == values
    assert re.findall(r"'([^']*)'::text", str(definition)) == values


# What the guards say when they refuse (migration 0025, as 0020).
ROW_REFUSED = "a row of a marked revision is never written"


@dataclass(frozen=True)
class Marked:
    """A revision marked around the service, holding a line, a rate and an image of each object.

    ``bare`` is the node of a line written without its facet before the marking.
    """

    parents: Parents
    bare: UUID


@pytest.fixture
def marked(owner: Engine, parents: Parents) -> Marked:
    """Fill the revision of the parents, then mark it around the service."""
    bare = uuid4()
    with owner.begin() as connection:
        for table in TABLES:
            connection.execute(row(table, parents))
        node = node_row(parents.project, parents.revision, parents.structure, id=bare, rank=2)
        connection.execute(
            insert(Node).values({**node, "kind": "estimate_line", "parent_id": parents.task})
        )
        connection.execute(update(Revision).where(Revision.id == parents.revision).values(**MARKED))
    return Marked(parents, bare)


def writes_of(table: type[Base], marked: Marked) -> list[Executable]:
    """Give an update, a deletion and an insertion of a row of a table of the estimate."""
    parents = marked.parents
    held = Base.metadata.tables[table.__tablename__]
    if table is EstimateLine:
        added = row(EstimateLine, parents, node_id=marked.bare)
    else:
        # Another object of the same kind, which the unique key of the revision admits.
        objects: dict[type[Base], str] = {
            RevisionRate: "cost_category_id",
            RevisionRole: "resource_role_id",
            RevisionCalendar: "calendar_id",
            RevisionCategory: "cost_category_id",
        }
        other = objects[table]
        added = row(table, parents, **{other: uuid4()})
    # A rate changes in its amount, a line and an image in their counter.
    changed = {"amount": Decimal("70.00")} if table is RevisionRate else {"lock_version": 7}
    return [
        update(held).where(held.c.project_id == parents.project).values(changed),
        delete(held).where(held.c.project_id == parents.project),
        added,
    ]


def rows_of(owner: Engine, project_id: UUID) -> list[tuple[object, ...]]:
    """Read every row of the estimate of a project, every column, in a stable order."""
    with owner.connect() as connection:
        return [
            tuple(found)
            for table in (Base.metadata.tables[kept.__tablename__] for kept in TABLES)
            for found in connection.execute(
                select(table).where(table.c.project_id == project_id).order_by(*table.primary_key)
            )
        ]


@pytest.mark.requirement("WF-DAT-0020-A")
@pytest.mark.parametrize("table", TABLES, ids=[table.__tablename__ for table in TABLES])
def test_a_line_a_rate_or_an_image_of_a_marked_revision_written_directly_is_refused(
    owner: Engine, marked: Marked, table: type[Base]
) -> None:
    # « Une mise à jour ou une suppression exécutée directement en base sur une tâche, une ligne de
    # devis ou une valeur de référentiel d'une révision marquée est rejetée par la base. » : a line,
    # a rate kept and the image of an object of the reference, written by the owner around the
    # service; an insertion too.
    before = rows_of(owner, marked.parents.project)
    for statement in writes_of(table, marked):
        with pytest.raises(DBAPIError, match=ROW_REFUSED), owner.begin() as connection:
            connection.execute(statement)
    assert rows_of(owner, marked.parents.project) == before


@pytest.mark.requirement("WF-DAT-0020-A")
def test_the_owner_may_not_truncate_the_tables_of_the_estimate_nor_a_partition_of_them(
    owner: Engine, marked: Marked
) -> None:
    project_id = marked.parents.project
    before = rows_of(owner, project_id)
    for table in TABLES:
        name = table.__tablename__
        for truncated in (name, f"{name}_p_{project_id.hex}"):
            statement = text(f'TRUNCATE TABLE "{truncated}" CASCADE')
            with pytest.raises(DBAPIError, match="never truncated"), owner.begin() as connection:
                connection.execute(statement)
    assert rows_of(owner, project_id) == before


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_line_and_a_rate_of_a_current_revision_are_changed_and_deleted(
    owner: Engine, parents: Parents
) -> None:
    # The guards refuse a marked revision alone: in a current one, a line and a rate change and go.
    with owner.begin() as connection:
        connection.execute(row(EstimateLine, parents))
        connection.execute(row(RevisionRate, parents))
        connection.execute(update(EstimateLine).values(label="Changée"))
        connection.execute(update(RevisionRate).values(amount=Decimal("70.00")))
        assert connection.scalar(select(EstimateLine.label)) == "Changée"
        connection.execute(delete(EstimateLine))
        connection.execute(delete(RevisionRate))
    assert (count(owner, EstimateLine), count(owner, RevisionRate)) == (0, 0)
