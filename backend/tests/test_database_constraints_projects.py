# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the tables of the projects and of the revisions forbid (EP-04).

The constraints of ``test_database_constraints.py`` for the nine tables of US-0910, in a file of
their own, which that one, near its bound of lines, could not hold. Every row is written around
the services of the modules, by the service or, for the partitions and the guards of a marked
revision, by the owner of the tables — whom the guards refuse as well (WF-DAT-0090, WF-REV-0020).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from project_rows import (
    AT,
    MARKED,
    STAMP,
    insert_project,
    insert_revision,
    insert_structure,
    projects_with_partitions,
    revision_row,
    structure_row,
)
from sqlalchemy import Engine, delete, insert, select, text, update
from sqlalchemy.exc import IntegrityError
from support import raw_account

from waterfall.core.cost_settings.tables import CostType
from waterfall.core.projects.tables import (
    Contributor,
    Deliverable,
    OrderItem,
    Project,
    ProjectStateTransition,
    Subproject,
    WorkPackage,
)
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Base, Database

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.sql import Executable

# The nine tables of US-0910, those that keep the columns of audit, and those with a counter.
TABLES: tuple[type[Base], ...] = (
    Project,
    ProjectStateTransition,
    Contributor,
    Subproject,
    WorkPackage,
    OrderItem,
    Deliverable,
    Revision,
    CostStructure,
)
STAMPED = (Project, Subproject, WorkPackage, OrderItem, Deliverable, Revision, CostStructure)
COUNTED = (Project, Subproject, Revision, CostStructure)

type Refusal = tuple[type[Base], dict[str, object], str]


@dataclass(frozen=True)
class Parents:
    """What a row of a test names: two projects with their partitions, and what they hold.

    The first holds its current revision, a work package and an order item; the second its own
    current revision, with its main structure already.
    """

    project: UUID
    other: UUID
    account: UUID
    revision: UUID
    other_revision: UUID
    work_package: UUID
    order_item: UUID


@pytest.fixture
def parents(database: Database, owner: Engine) -> Iterator[Parents]:
    """Write the parents of the rows a test tries, around the service."""
    with projects_with_partitions(owner, 2) as (project, other):
        account, revision, other_revision, work_package, order_item = (uuid4() for _ in range(5))
        with database.engine.begin() as connection:
            connection.execute(insert(UserAccount).values(**raw_account(id=account)))
            connection.execute(insert_revision(project, id=revision))
            connection.execute(insert_revision(other, id=other_revision))
            connection.execute(insert_structure(other, other_revision))
            connection.execute(
                insert(WorkPackage).values(
                    id=work_package, project_id=project, label="Lot", position=0, **STAMP
                )
            )
            connection.execute(
                insert(OrderItem).values(
                    id=order_item,
                    project_id=project,
                    work_package_id=work_package,
                    label="Poste",
                    position=0,
                    **STAMP,
                )
            )
        yield Parents(project, other, account, revision, other_revision, work_package, order_item)


def constraint_of(error: IntegrityError) -> str:
    """Give the name of the constraint a refusal of the database comes from."""
    cause = error.orig
    assert isinstance(cause, psycopg.Error)
    return cause.diag.constraint_name or ""


def refusal(engine: Engine, statement: Executable) -> str:
    """Run a statement the database must refuse, and give the constraint that refused it."""
    with pytest.raises(IntegrityError) as raised, engine.begin() as connection:
        connection.execute(statement)
    return constraint_of(raised.value)


def valid(table: type[Base], parents: Parents) -> dict[str, object]:
    """Give the columns of a valid row of a table, under the parents of the test."""
    project = parents.project
    element = {"id": uuid4(), "project_id": project, "label": "Élément", "position": 1, **STAMP}
    rows: dict[type[Base], dict[str, object]] = {
        Project: {},
        ProjectStateTransition: {
            "id": uuid4(),
            "project_id": project,
            "to_state": "created",
            "occurred_at": AT,
        },
        Contributor: {
            "project_id": project,
            "user_account_id": parents.account,
            "kind": "contributor",
        },
        Subproject: {
            "id": uuid4(),
            "project_id": project,
            "code": uuid4().hex[:8],
            "label": "Mécanique",
            **STAMP,
        },
        WorkPackage: element,
        OrderItem: {**element, "work_package_id": parents.work_package},
        Deliverable: {**element, "order_item_id": parents.order_item},
        Revision: revision_row(project, **{**MARKED, "version_name": f"v-{uuid4().hex}"}),
        CostStructure: structure_row(project, parents.revision),
    }
    return rows[table]


def row(table: type[Base], parents: Parents, **overrides: object) -> Executable:
    """Give the insertion of a row of a table, valid but for the changes a test asks for."""
    if table is Project:
        return insert_project(**overrides)
    return insert(table).values(**{**valid(table, parents), **overrides})


def audit_refusals() -> list[Refusal]:
    """Give, for each table with them, the refusals the columns of audit and the counter bring."""
    refused: list[Refusal] = []
    for table in STAMPED:
        name = table.__tablename__
        refused.append((table, {"created_by": uuid4()}, f"fk_{name}_created_by_user_account"))
        refused.append((table, {"updated_by": uuid4()}, f"fk_{name}_updated_by_user_account"))
    refused.extend(
        (table, {"lock_version": -1}, f"ck_{table.__tablename__}_lock_version_not_negative")
        for table in COUNTED
    )
    return refused


def bounds(table: type[Base], column: str, longest: int) -> list[Refusal]:
    """Give the three refusals of a bounded text: empty, too long, blank."""
    name = table.__tablename__
    return [
        (table, {column: ""}, f"ck_{name}_{column}_length"),
        (table, {column: "x" * (longest + 1)}, f"ck_{name}_{column}_length"),
        (table, {column: " \t"}, f"ck_{name}_{column}_not_blank"),
    ]


# A held value: what a row already written takes from the one tried (``held``, below).
TAKEN = "TAKEN"
RATIO_ABOVE, RATIO_BELOW = Decimal("1.0001"), Decimal("-0.0001")

REFUSALS: list[Refusal] = [
    *bounds(Project, "label", 300),
    *bounds(Project, "code", 50),
    (Project, {"code": "PRJ/001"}, "ck_project_code_without_slash"),
    (Project, {"code": TAKEN}, "uq_project_code"),
    *bounds(Project, "client", 300),
    (Project, {"state": "archived"}, "ck_project_state_known"),
    (Project, {"inflation_rate": RATIO_ABOVE}, "ck_project_inflation_rate_between_zero_and_one"),
    (Project, {"inflation_rate": RATIO_BELOW}, "ck_project_inflation_rate_between_zero_and_one"),
    (Project, {"win_probability": RATIO_ABOVE}, "ck_project_win_probability_between_zero_and_one"),
    (Project, {"win_probability": RATIO_BELOW}, "ck_project_win_probability_between_zero_and_one"),
    (
        Project,
        {"contributors_lock_version": -1},
        "ck_project_contributors_lock_version_not_negative",
    ),
    (
        Project,
        {"work_breakdown_lock_version": -1},
        "ck_project_work_breakdown_lock_version_not_negative",
    ),
    (Project, {"reference_revision_id": uuid4()}, "fk_project_reference_revision_id_revision"),
    (Project, {"current_revision_id": uuid4()}, "fk_project_current_revision_id_revision"),
    (
        ProjectStateTransition,
        {"from_state": "archived"},
        "ck_project_state_transition_from_state_known",
    ),
    (ProjectStateTransition, {"to_state": "closed"}, "ck_project_state_transition_to_state_known"),
    (
        ProjectStateTransition,
        {"project_id": uuid4()},
        "fk_project_state_transition_project_id_project",
    ),
    (
        ProjectStateTransition,
        {"actor_user_id": uuid4()},
        "fk_project_state_transition_actor_user_id_user_account",
    ),
    (Contributor, {"kind": "observer"}, "ck_contributor_kind_known"),
    (Contributor, {"project_id": uuid4()}, "fk_contributor_project_id_project"),
    (Contributor, {"user_account_id": uuid4()}, "fk_contributor_user_account_id_user_account"),
    (Subproject, {"code": TAKEN}, "uq_subproject_project_id"),
    *bounds(Subproject, "code", 31),
    *(
        (Subproject, {"code": f"SP{character}1"}, "ck_subproject_code_form")
        for character in (":", "\\", "/", "?", "*", "[", "]")
    ),
    *bounds(Subproject, "label", 300),
    (Subproject, {"project_id": uuid4()}, "fk_subproject_project_id_project"),
    *bounds(WorkPackage, "label", 300),
    (WorkPackage, {"position": -1}, "ck_work_package_position_not_negative"),
    (WorkPackage, {"position": 0}, "uq_work_package_position"),
    (WorkPackage, {"project_id": uuid4()}, "fk_work_package_project_id_project"),
    *bounds(OrderItem, "label", 300),
    (OrderItem, {"position": -1}, "ck_order_item_position_not_negative"),
    (OrderItem, {"position": 0}, "uq_order_item_position"),
    (OrderItem, {"project_id": uuid4()}, "fk_order_item_project_id_project"),
    (OrderItem, {"work_package_id": uuid4()}, "fk_order_item_work_package_id_work_package"),
    *bounds(Deliverable, "label", 300),
    (Deliverable, {"position": -1}, "ck_deliverable_position_not_negative"),
    (Deliverable, {"position": 0}, "uq_deliverable_position"),
    (Deliverable, {"project_id": uuid4()}, "fk_deliverable_project_id_project"),
    (Deliverable, {"order_item_id": uuid4()}, "fk_deliverable_order_item_id_order_item"),
    (
        Revision,
        {"status": "frozen", "version_name": None, "marked_at": None},
        "ck_revision_status_known",
    ),
    *bounds(Revision, "version_name", 100),
    (Revision, {"version_name": None}, "ck_revision_version_name_when_marked"),
    (Revision, {"marked_at": None}, "ck_revision_marked_at_when_marked"),
    (Revision, {"status": "draft", "version_name": None}, "ck_revision_marked_at_when_marked"),
    (Revision, {"reference_year": 1999}, "ck_revision_reference_year_bound"),
    (Revision, {"reference_year": 2101}, "ck_revision_reference_year_bound"),
    (Revision, {"status": "draft", "version_name": None, "marked_at": None}, "uq_revision_draft"),
    (Revision, {"version_name": TAKEN}, "uq_revision_version_name"),
    (Revision, {"is_reference": True}, "uq_revision_reference"),
    (Revision, {"project_id": uuid4()}, "fk_revision_project_id_project"),
    (Revision, {"source_revision_id": uuid4()}, "fk_revision_source_revision_id_revision"),
    (CostStructure, {"kind": "amendment"}, "ck_cost_structure_kind_known"),
    *bounds(CostStructure, "label", 300),
    (CostStructure, {"revision_id": uuid4()}, "fk_cost_structure_project_id_revision"),
]
# The main structure tried in the revision of the second project, which has one already.
MAIN = "uq_cost_structure_main"


def held(table: type[Base], parents: Parents) -> Executable | None:
    """Give the row already written that a refusal of uniqueness collides with, if it needs one.

    The work package and the order item of the parents hold the position 0 already.
    """
    if table is Project:
        return insert_project(code=TAKEN)
    if table is Subproject:
        return row(Subproject, parents, code=TAKEN)
    if table is Deliverable:
        return row(Deliverable, parents, position=0)
    if table is Revision:
        return row(Revision, parents, version_name=TAKEN, is_reference=True)
    return None


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    [*REFUSALS, *audit_refusals()],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_row_of_a_project_or_of_a_revision_that_breaks_a_rule(
    database: Database,
    parents: Parents,
    table: type[Base],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    first = held(table, parents)
    if first is not None:
        with database.engine.begin() as connection:
            connection.execute(first)
    assert refusal(database.engine, row(table, parents, **overrides)) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_database_refuses_a_second_main_structure_in_a_revision(
    database: Database, parents: Parents
) -> None:
    # A revised table is partitioned: the refusal names the index of the partition, whose parent
    # is the index of the table — what a service that names the refusal reads.
    second = row(
        CostStructure, parents, project_id=parents.other, revision_id=parents.other_revision
    )
    refused = refusal(database.engine, second)
    with database.engine.connect() as connection:
        parent = connection.execute(
            text(
                "SELECT inhparent::regclass::text FROM pg_inherits "
                "WHERE inhrelid = to_regclass(:index)"
            ),
            {"index": refused},
        ).scalar_one()
    assert parent == MAIN


@pytest.mark.requirement("WF-DAT-0090-A")
def test_every_named_constraint_of_the_projects_and_revisions_has_its_refusal_tried() -> None:
    # The unique indexes count, as the constraints do; the pair that the structures name of a
    # revision is unique as its key is, and is never broken without it.
    tables = [Base.metadata.tables[table.__tablename__] for table in TABLES]
    named = {
        str(constraint.name)
        for table in tables
        for constraint in table.constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    } | {str(index.name) for table in tables for index in table.indexes if index.unique}
    tried = {MAIN} | {constraint for _, _, constraint in (*REFUSALS, *audit_refusals())}
    assert named - {"uq_revision_project_id"} == tried


@pytest.mark.requirement("WF-DAT-0090-A")
def test_an_element_marked_deleted_leaves_its_position_to_another(
    database: Database, parents: Parents
) -> None:
    with database.engine.begin() as connection:
        connection.execute(
            update(WorkPackage).where(WorkPackage.id == parents.work_package).values(deleted_at=AT)
        )
        connection.execute(row(WorkPackage, parents, position=0))
        first = select(WorkPackage.deleted_at).where(WorkPackage.position == 0)
        held = connection.execute(first.order_by(WorkPackage.deleted_at)).scalars().all()
    assert held == [AT, None]


def audit_columns(table: type[Base]) -> dict[str, tuple[object, ...]]:
    """Give the audit columns of a table: type, nullability, default, and the key each names."""
    columns = table.__table__.columns
    return {
        name: (
            repr(columns[name].type),
            columns[name].nullable,
            str(columns[name].server_default),
            sorted((key.target_fullname, key.ondelete) for key in columns[name].foreign_keys),
        )
        for name in ("lock_version", "created_at", "created_by", "updated_at", "updated_by")
    }


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_audit_columns_of_the_projects_and_the_revisions_are_those_of_the_reference() -> None:
    # Each module declares its own (a module imports no table of another, WF-ARC-0010).
    assert audit_columns(Project) == audit_columns(Revision) == audit_columns(CostType)


# The code of a project and its references (WF-DAT-0060).


@pytest.mark.requirement("WF-DAT-0060-A")
def test_every_row_refers_to_a_project_and_to_a_revision_by_its_identifier_never_by_its_code(
    database: Database,
) -> None:
    # « … le code d'un projet est une contrainte d'unicité, jamais une clé » : every key that names
    # a project names its identifier, every key that names a revision its identifier, with its
    # project for a revised row.
    with database.engine.connect() as connection:
        keys = connection.execute(
            text(
                "SELECT conrelid::regclass::text, confrelid::regclass::text, ARRAY(SELECT "
                "attname::text FROM unnest(confkey) WITH ORDINALITY AS k(attnum, rank) JOIN "
                "pg_attribute ON attrelid = confrelid AND pg_attribute.attnum = k.attnum "
                "ORDER BY rank) FROM pg_constraint WHERE contype = 'f' AND conparentid = 0 "
                "AND confrelid IN ('project'::regclass, 'revision'::regclass)"
            )
        ).all()
    targets = {(table, target, tuple(columns)) for table, target, columns in keys}
    assert {target[1:] for target in targets} == {
        ("project", ("id",)),
        ("revision", ("id",)),
        ("revision", ("project_id", "id")),
    }
    assert {table for table, _, _ in targets} >= {
        "project_state_transition",
        "contributor",
        "subproject",
        "work_package",
        "revision",
        "cost_structure",
    }


@pytest.mark.requirement("WF-DAT-0060-A")
def test_changing_the_code_of_a_project_leaves_the_rows_that_refer_to_it_as_they_are(
    database: Database, parents: Parents
) -> None:
    # « La modification du code d'un projet … n'affecte aucune ligne qui les référence. »
    tables = (Revision, Contributor, Subproject, WorkPackage, OrderItem, CostStructure)
    with database.engine.begin() as connection:
        connection.execute(row(Contributor, parents))
        connection.execute(row(Subproject, parents))
        connection.execute(row(CostStructure, parents))
        connection.execute(update(Project).where(Project.id == parents.project).values(code="A1"))
    with database.engine.connect() as connection:
        before = {table: connection.execute(select(table)).all() for table in tables}
    with database.engine.begin() as connection:
        connection.execute(update(Project).where(Project.id == parents.project).values(code="B2"))
    with database.engine.connect() as connection:
        after = {table: connection.execute(select(table)).all() for table in tables}
        code = connection.scalar(select(Project.code).where(Project.id == parents.project))
    assert all(before.values())
    assert (after, code) == (before, "B2")


@pytest.mark.requirement("WF-DAT-0060-A")
def test_the_identifiers_of_the_projects_and_revisions_are_drawn_by_the_service(
    database: Database,
) -> None:
    # « Deux instances … ne produisent jamais le même identifiant » : a version 7 identifier drawn
    # by the service (EP-03), never a default of the database, which would be a sequence.
    with database.engine.connect() as connection:
        columns = connection.execute(
            text(
                "SELECT table_name, data_type, column_default FROM information_schema.columns "
                "WHERE column_name = 'id' AND table_name = ANY(:tables)"
            ),
            {"tables": [table.__tablename__ for table in TABLES if table is not Contributor]},
        ).all()
    assert {(data, default) for _, data, default in columns} == {("uuid", None)}
    assert len(columns) == len(TABLES) - 1


# What the database refuses of a marked revision, owner included (WF-REV-0020).


def guard_refusal(owner: Engine, statement: Executable) -> None:
    """Run as the owner a write a guard of a marked revision must refuse."""
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(statement)
    assert isinstance(raised.value.orig, psycopg.errors.RestrictViolation)


@pytest.fixture
def marked(database: Database, owner: Engine, parents: Parents) -> UUID:
    """Mark the current revision of the first project, its main structure in it, as the owner."""
    del database
    with owner.begin() as connection:
        connection.execute(insert_structure(parents.project, parents.revision))
        connection.execute(update(Revision).where(Revision.id == parents.revision).values(**MARKED))
    return parents.revision


@pytest.mark.requirement("WF-REV-0020-A")
@pytest.mark.parametrize(
    "change",
    [
        {"status": "draft", "version_name": None, "marked_at": None},
        {"version_name": "v2.0"},
        {"description": "Corrigée"},
        {"reference_year": 2027},
        {"lineage_id": uuid4()},
        {"source_revision_id": uuid4()},
    ],
    ids="-".join,
)
def test_a_marked_revision_is_neither_taken_back_nor_changed_by_anyone(
    owner: Engine, marked: UUID, change: dict[str, object]
) -> None:
    guard_refusal(owner, update(Revision).where(Revision.id == marked).values(**change))


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_marked_revision_keeps_the_source_it_was_copied_from_and_cannot_be_deleted_while_copied(
    owner: Engine, parents: Parents, marked: UUID
) -> None:
    # The source is a marked revision; the copy names it and keeps it after its own marking.
    copy = revision_row(parents.project, source_revision_id=marked)
    with owner.begin() as connection:
        connection.execute(insert(Revision).values(**copy))
    guard_refusal(owner, delete(Revision).where(Revision.id == marked))
    with owner.connect() as connection:
        kept = connection.scalar(
            select(Revision.source_revision_id).where(Revision.id == copy["id"])
        )
    assert kept == marked


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_marked_revision_changes_in_its_designation_its_counter_and_its_audit_alone(
    owner: Engine, marked: UUID
) -> None:
    designated = {"is_reference": True, "lock_version": 1, "updated_at": AT, "updated_by": None}
    with owner.begin() as connection:
        connection.execute(update(Revision).where(Revision.id == marked).values(**designated))
        reference = connection.scalar(select(Revision.is_reference).where(Revision.id == marked))
    assert reference is True
    guard_refusal(owner, delete(Revision).where(Revision.id == marked))


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_structure_of_a_marked_revision_is_neither_written_changed_nor_deleted(
    owner: Engine, parents: Parents, marked: UUID
) -> None:
    structures = select(CostStructure.id).where(CostStructure.revision_id == marked)
    changed = update(CostStructure).where(CostStructure.revision_id == marked)
    guard_refusal(owner, changed.values(label="Autre"))
    guard_refusal(owner, delete(CostStructure).where(CostStructure.revision_id == marked))
    guard_refusal(owner, insert_structure(parents.project, marked, kind="main"))
    with owner.connect() as connection:
        assert len(connection.execute(structures).all()) == 1


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_current_revision_and_its_structures_are_changed_and_abandoned_freely(
    owner: Engine, parents: Parents
) -> None:
    # The abandonment of a current revision deletes its rows, then the revision: never marked, the
    # guards let it pass. The revision of the second project, then marked, passes its guard too.
    revision = parents.other_revision
    with owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.revision_id == revision).values(label="B")
        )
        connection.execute(delete(CostStructure).where(CostStructure.revision_id == revision))
        connection.execute(insert_revision(parents.other, **MARKED))
        connection.execute(delete(Revision).where(Revision.id == revision))
        connection.execute(update(Revision).where(Revision.id == parents.revision).values(**MARKED))
        left = select(Revision.status).where(Revision.project_id == parents.other)
        statuses = connection.execute(left).scalars().all()
    assert statuses == ["marked"]


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_temporary_table_named_revision_does_not_open_a_structure_of_a_marked_revision(
    database: Database, marked: UUID
) -> None:
    # An unqualified name is looked for in pg_temp first: the guard reads public.revision under its
    # own search path, so a table of the service's session that shadows it leaves the refusal whole.
    with database.engine.connect() as connection:
        temporary = connection.scalar(
            text("SELECT has_database_privilege(current_database(), 'TEMPORARY')")
        )
    assert temporary is True, "the role of the service has no TEMPORARY: the scenario is not tried"
    changed = update(CostStructure).where(CostStructure.revision_id == marked).values(label="Autre")
    with database.engine.connect() as connection:
        # Created in the transaction, the table goes with its rollback.
        connection.execute(text("CREATE TEMP TABLE revision (id uuid, status text)"))
        with pytest.raises(IntegrityError) as raised:
            connection.execute(changed)
        connection.rollback()
    assert isinstance(raised.value.orig, psycopg.errors.RestrictViolation)
