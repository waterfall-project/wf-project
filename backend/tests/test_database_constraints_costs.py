# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the tables of the actual costs forbid, and holds their idempotence.

The constraints of the two tables of US-1580/L1 (migration 0027), one refusal each, as
``test_database_constraints_estimate.py`` tries those of EP-07; and the uniqueness of a line on its
project, its document and its item, a null item a value like any other, which the base holds
whatever path writes it (WF-DAT-0110, #1340). Every row is written around the services of the
modules, by the owner of the tables.
"""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from costs_support import (
    Imported,
    cost_import_row,
    cost_line_row,
    insert_cost_line,
    report_row,
    write_import,
)
from project_rows import STAMP, insert_project
from sqlalchemy import Engine, func, insert, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.costs.tables import CostImport, CostLine
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.projects.tables import Subproject
from waterfall.platform.database import Base, Database

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection
    from sqlalchemy.sql import Executable

# The two tables of the actual costs (US-1580/L1).
TABLES: tuple[type[Base], ...] = (CostLine, CostImport)

type Refusal = tuple[type[Base], dict[str, object], str]


@dataclass(frozen=True)
class Parents:
    """What a row of a test names: an import applied on a project, a subproject of it.

    ``foreign_subproject`` is one of another project; ``report`` an import of the exchanges no entry
    of the log names yet.
    """

    imported: Imported
    subproject: UUID
    foreign_subproject: UUID
    report: UUID


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
def parents(database: Database, owner: Engine) -> Parents:
    """Write the parents of the rows a test tries, around the service."""
    del database
    project, foreign, report = uuid4(), uuid4(), uuid4()
    with owner.begin() as connection:
        connection.execute(insert_project(id=project))
        connection.execute(insert_project(id=foreign))
        imported = write_import(connection, project)
        owned = subproject(connection, project, "SP1")
        other = subproject(connection, foreign, "SP2")
        connection.execute(insert(ImportReport).values(**report_row(project, id=report)))
    return Parents(imported, owned, other, report)


def constraint_of(error: IntegrityError) -> str:
    """Give the constraint a refusal names."""
    cause = error.orig
    assert isinstance(cause, psycopg.Error)
    return cause.diag.constraint_name or ""


def valid(table: type[Base], parents: Parents) -> dict[str, object]:
    """Give the columns of a valid row of a table, under the parents of the test."""
    imported = parents.imported
    if table is CostLine:
        return cost_line_row(imported.project_id, imported.cost_import_id)
    return cost_import_row(imported.project_id, parents.report, imported.account_id)


def row(table: type[Base], parents: Parents, **overrides: object) -> Executable:
    """Give the insertion of a row of a table, valid but for the changes a test asks for."""
    return insert(table).values(**{**valid(table, parents), **overrides})


# A value the parents hold: a subproject of the project, one of another project, an import of the
# exchanges an entry of the log names already.
OWN = "OWN"
FOREIGN = "FOREIGN"
TAKEN = "TAKEN"
# A line imputed to a subproject, by its code.
IMPUTED = {"subproject_id": OWN, "subproject_code": "SP1"}

REFUSALS: list[Refusal] = [
    (CostLine, {"project_id": uuid4()}, "fk_cost_line_project_id_project"),
    (
        CostLine,
        {"subproject_id": FOREIGN, "subproject_code": "SP2"},
        "fk_cost_line_project_id_subproject",
    ),
    (CostLine, {"last_import_id": uuid4()}, "fk_cost_line_last_import_id_cost_import"),
    (CostLine, {"created_by": uuid4()}, "fk_cost_line_created_by_user_account"),
    (CostLine, {"updated_by": uuid4()}, "fk_cost_line_updated_by_user_account"),
    (CostLine, {"document_number": ""}, "ck_cost_line_document_number_length"),
    (CostLine, {"document_number": "9" * 201}, "ck_cost_line_document_number_length"),
    (CostLine, {"document_number": " \t"}, "ck_cost_line_document_number_not_blank"),
    (CostLine, {"subproject_code": "S" * 51}, "ck_cost_line_subproject_code_length"),
    (
        CostLine,
        {"excluded_reason": "Réception du client"},
        "ck_cost_line_excluded_reason_when_excluded",
    ),
    (
        CostLine,
        {**IMPUTED, "subproject_code": None},
        "ck_cost_line_subproject_code_when_imputed",
    ),
    (CostLine, {"passthrough": {"Quantité": 3}}, "ck_cost_line_passthrough_texts"),
    (CostLine, {"passthrough": ["Fournisseur"]}, "ck_cost_line_passthrough_texts"),
    (CostLine, {"document_number": TAKEN}, "uq_cost_line_project_id"),
    (CostImport, {"project_id": uuid4()}, "fk_cost_import_project_id_project"),
    (CostImport, {"import_report_id": uuid4()}, "fk_cost_import_import_report_id_import_report"),
    (CostImport, {"requested_by": uuid4()}, "fk_cost_import_requested_by_user_account"),
    (
        CostImport,
        {"period_from": date(2026, 5, 1), "period_to": date(2026, 4, 30)},
        "ck_cost_import_period_ordered",
    ),
    (CostImport, {"created_count": -1}, "ck_cost_import_created_count_not_negative"),
    (CostImport, {"updated_count": -1}, "ck_cost_import_updated_count_not_negative"),
    (CostImport, {"unchanged_count": -1}, "ck_cost_import_unchanged_count_not_negative"),
    (CostImport, {"rejected_count": -1}, "ck_cost_import_rejected_count_not_negative"),
    (
        CostImport,
        {"passthrough_columns": {"Fournisseur": "Fournisseur"}},
        "ck_cost_import_passthrough_columns_texts",
    ),
    (
        CostImport,
        {"passthrough_columns": ["Fournisseur", 2]},
        "ck_cost_import_passthrough_columns_texts",
    ),
    (CostImport, {"import_report_id": TAKEN}, "uq_cost_import_import_report_id"),
]


def resolved(parents: Parents, overrides: dict[str, object]) -> dict[str, object]:
    """Give the values a refusal tries, the ones the parents hold put in."""
    imported = parents.imported
    named: dict[str, object] = {OWN: parents.subproject, FOREIGN: parents.foreign_subproject}
    taken: dict[str, object] = {
        # The document of the line the import brought, without an item as it.
        "document_number": cost_line_row(imported.project_id, imported.cost_import_id)[
            "document_number"
        ],
        "import_report_id": imported.report_id,
    }
    return {
        column: (taken[column] if value == TAKEN else named.get(value, value))
        if isinstance(value, str)
        else value
        for column, value in overrides.items()
    }


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    REFUSALS,
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_row_of_the_actual_costs_that_breaks_a_rule(
    owner: Engine,
    parents: Parents,
    table: type[Base],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    if table is CostLine and overrides.get("document_number") == TAKEN:
        with owner.begin() as connection:
            insert_cost_line(connection, parents.imported)
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(row(table, parents, **resolved(parents, overrides)))
    assert constraint_of(raised.value) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_every_named_constraint_of_the_actual_costs_has_its_refusal_tried() -> None:
    tables = [Base.metadata.tables[table.__tablename__] for table in TABLES]
    named = {
        str(constraint.name)
        for table in tables
        for constraint in table.constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    }
    tried = {constraint for _, _, constraint in REFUSALS}
    assert named == tried


@pytest.mark.requirement("WF-DAT-0090-A")
def test_a_line_imputed_excluded_with_its_reason_and_an_entry_without_a_period_are_written(
    owner: Engine, parents: Parents
) -> None:
    # The forms the constraints admit besides the valid rows: a line imputed to a subproject of its
    # project and excluded with a reason, a line keeping an unknown code, a negative amount; an
    # entry of the log that declared no period, whose columns kept are none.
    imported = parents.imported
    with owner.begin() as connection:
        connection.execute(
            row(
                CostImport,
                parents,
                period_from=None,
                period_to=None,
                passthrough_columns=[],
            )
        )
        insert_cost_line(
            connection,
            imported,
            subproject_id=parents.subproject,
            subproject_code="SP1",
            is_in_tracked_scope=False,
            excluded_reason="Réception du client",
        )
        insert_cost_line(
            connection,
            imported,
            document_number="5100001235",
            subproject_code="SP9",
            amount=-125,
            passthrough={},
        )
        held = connection.execute(
            select(CostLine.subproject_id, CostLine.subproject_code, CostLine.excluded_reason)
            .where(CostLine.project_id == imported.project_id)
            .order_by(CostLine.document_number)
        ).all()
    assert [tuple(found) for found in held] == [
        (parents.subproject, "SP1", "Réception du client"),
        (None, "SP9", None),
    ]


@pytest.mark.requirement("WF-DAT-0110-A")
def test_two_lines_of_one_document_and_item_are_refused_and_of_two_items_written(
    owner: Engine, parents: Parents
) -> None:
    # « L'insertion directe en base de deux lignes de coût de même projet, de même numéro de pièce
    # et de même poste est rejetée ; de postes différents, elle aboutit. » : the owner writes around
    # the service; a document without an item is one item like another, refused twice too (#1340).
    imported = parents.imported
    with owner.begin() as connection:
        for item in ("10", "20", None):
            insert_cost_line(connection, imported, document_item=item)
    for item in ("10", None):
        with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
            insert_cost_line(connection, imported, document_item=item)
        assert constraint_of(raised.value) == "uq_cost_line_project_id"
    with owner.connect() as connection:
        items = connection.scalars(
            select(CostLine.document_item).order_by(CostLine.document_item.nulls_last())
        ).all()
    assert items == ["10", "20", None]


@pytest.mark.requirement("WF-DAT-0110-A")
def test_one_document_and_item_in_two_projects_are_two_lines(
    owner: Engine, parents: Parents
) -> None:
    # The triplet names the project: another project's extraction may carry the same document.
    with owner.begin() as connection:
        foreign = connection.scalar(
            select(Subproject.project_id).where(Subproject.id == parents.foreign_subproject)
        )
        assert foreign is not None
        insert_cost_line(connection, parents.imported)
        insert_cost_line(connection, write_import(connection, foreign))
        count = connection.scalar(select(func.count()).select_from(CostLine))
    assert count == 2
