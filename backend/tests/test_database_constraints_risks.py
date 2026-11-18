# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the tables of the risks forbid, and a write of a marked revision.

The constraints of ``risk``, ``risk_evaluation``, ``risk_review`` and ``risk_reference_share``
(US-2550/L1, migration 0035), one refusal each, as ``test_database_constraints_indicators.py`` tries
those of EP-10; the guards that refuse any write of an evaluation or of a review of a marked
revision, owner included; and the truncation of the revised tables refused. Every row is written
around the services of the modules, by the owner of the tables, under a current revision.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import psycopg
import pytest
from estimate_support import write_reference
from planning_support import insert_task, node_row
from project_rows import (
    MARKED,
    insert_revision,
    insert_structure,
    projects_with_partitions,
    risk_row,
)
from risks_support import evaluation_row, review_row, share_row
from sqlalchemy import Engine, delete, insert, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from waterfall.core.planning.tables import Node
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReferenceShare, RiskReview
from waterfall.platform.database import Base, Database

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Connection
    from sqlalchemy.sql import Executable

pytestmark = pytest.mark.requirement("WF-DAT-0090-A")

TABLES: tuple[type[Base], ...] = (Risk, RiskEvaluation, RiskReview, RiskReferenceShare)
# What the guards say when they refuse (migration 0035, of the form of 0020's).
ROW_REFUSED = "a row of a marked revision is never written"


@dataclass(frozen=True)
class Parents:
    """What a row of a test names: a project, its current revision, its structures, a risk.

    The revision holds its main structure, a task of it bearing a node, and the own structure of
    the risk; the reference a category. A marked revision before it holds a node too, which no
    evaluation of the current one names (``former_node``). A second risk of the project has its own
    structure in the revision too (``other_structure``), which no evaluation of the first names.
    """

    project: UUID
    revision: UUID
    risk: UUID
    structure: UUID
    main: UUID
    node: UUID
    former_node: UUID
    category: UUID
    other_structure: UUID


def line_of(connection: Connection, project: UUID, revision: UUID, main: UUID) -> UUID:
    """Write a task of a structure bearing a line, its node; give the node."""
    task = insert_task(connection, project, revision, main)
    node = node_row(project, revision, main, parent_id=task, kind="estimate_line")
    connection.execute(insert(Node).values(**node))
    node_id = node["id"]
    assert isinstance(node_id, UUID)
    return node_id


@pytest.fixture
def parents(database: Database, owner: Engine) -> Iterator[Parents]:
    """Write the parents of the rows a test tries, around the service."""
    del database
    with projects_with_partitions(owner) as (project,):
        former, revision, risk, own, main, former_main = (uuid4() for _ in range(6))
        other, other_own = uuid4(), uuid4()
        with owner.begin() as connection:
            category = write_reference(connection).category
            connection.execute(insert_revision(project, id=former))
            connection.execute(insert_structure(project, former, id=former_main))
            former_node = line_of(connection, project, former, former_main)
            connection.execute(
                update(Revision)
                .where(Revision.id == former)
                .values(**{**MARKED, "version_name": "v0.9"})
            )
            connection.execute(insert_revision(project, id=revision))
            connection.execute(insert_structure(project, revision, id=main))
            node = line_of(connection, project, revision, main)
            connection.execute(insert(Risk).values(**risk_row(project, id=risk)))
            connection.execute(
                insert_structure(project, revision, id=own, kind="risk", risk_id=risk)
            )
            connection.execute(insert(Risk).values(**risk_row(project, id=other)))
            connection.execute(
                insert_structure(project, revision, id=other_own, kind="risk", risk_id=other)
            )
        yield Parents(project, revision, risk, own, main, node, former_node, category, other_own)


def constraint_of(owner: Engine, error: IntegrityError) -> str:
    """Give the constraint of the table a refusal comes from, that of its partition named so."""
    cause = error.orig
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


def valid(table: type[Base], parents: Parents) -> dict[str, object]:
    """Give the columns of a valid row of a table, under the parents of the test."""
    project, risk, revision = parents.project, parents.risk, parents.revision
    rows: dict[type[Base], dict[str, object]] = {
        Risk: risk_row(project),
        RiskEvaluation: evaluation_row(
            project, risk, (revision, parents.structure), parents.category
        ),
        RiskReview: review_row(project, risk, revision),
        RiskReferenceShare: share_row(project, risk, revision),
    }
    return rows[table]


def row(table: type[Base], parents: Parents, **overrides: object) -> Executable:
    """Give the insertion of a row of a table, valid but for the changes a test asks for."""
    return insert(table).values(**{**valid(table, parents), **overrides})


# A value the parents hold, resolved when the test runs: the node of a line, the node of a line of
# the marked revision, the main structure, the own structure of the other risk.
NODE, FORMER_NODE, MAIN, OTHER_OWN = "NODE", "FORMER_NODE", "MAIN", "OTHER_OWN"

type Refusal = tuple[type[Base], dict[str, object], str]


def stamped(table: type[Base], *, changed: bool) -> list[Refusal]:
    """Give the refusals of the authors of a row: an account that does not exist."""
    name = table.__tablename__
    columns = ("created_by", "updated_by") if changed else ("created_by",)
    return [(table, {each: uuid4()}, f"fk_{name}_{each}_user_account") for each in columns]


REFUSALS: list[Refusal] = [
    (Risk, {"project_id": uuid4()}, "fk_risk_project_id_project"),
    (Risk, {"label": ""}, "ck_risk_label_length"),
    (Risk, {"label": "x" * 301}, "ck_risk_label_length"),
    (Risk, {"label": " \t"}, "ck_risk_label_not_blank"),
    (Risk, {"lock_version": -1}, "ck_risk_lock_version_not_negative"),
    *stamped(Risk, changed=True),
    # The structure with its revision and its risk: an unknown one, one of another revision, one
    # of an unknown risk, the own estimate of another risk of the revision (#3955), or one of
    # another kind than risk, is refused.
    (RiskEvaluation, {"risk_id": uuid4()}, "fk_risk_evaluation_project_id_cost_structure"),
    (RiskEvaluation, {"structure_id": uuid4()}, "fk_risk_evaluation_project_id_cost_structure"),
    (RiskEvaluation, {"revision_id": uuid4()}, "fk_risk_evaluation_project_id_cost_structure"),
    (RiskEvaluation, {"structure_id": OTHER_OWN}, "fk_risk_evaluation_project_id_cost_structure"),
    (RiskEvaluation, {"structure_id": MAIN}, "fk_risk_evaluation_project_id_cost_structure"),
    # The provision line with its revision: an unknown node, or one of another revision.
    (
        RiskEvaluation,
        {"state": "identified", "provision_node_id": uuid4()},
        "fk_risk_evaluation_project_id_node",
    ),
    (
        RiskEvaluation,
        {"state": "identified", "provision_node_id": FORMER_NODE},
        "fk_risk_evaluation_project_id_node",
    ),
    (
        RiskEvaluation,
        {"provision_subproject_id": uuid4()},
        "fk_risk_evaluation_project_id_subproject",
    ),
    (
        RiskEvaluation,
        {"provision_cost_category_id": uuid4()},
        "fk_risk_evaluation_provision_cost_category_id_cost_category",
    ),
    (RiskEvaluation, {"probability": Decimal("1.0001")}, "ck_risk_evaluation_probability_ratio"),
    (RiskEvaluation, {"probability": Decimal("-0.0001")}, "ck_risk_evaluation_probability_ratio"),
    (RiskEvaluation, {"state": "forgotten"}, "ck_risk_evaluation_state_known"),
    (RiskEvaluation, {"state": "identified"}, "ck_risk_evaluation_provision_when_identified"),
    (RiskEvaluation, {"provision_node_id": NODE}, "ck_risk_evaluation_provision_when_identified"),
    (RiskEvaluation, {"state": "occurred"}, "ck_risk_evaluation_cost_when_occurred"),
    (
        RiskEvaluation,
        {"occurrence_cost": Decimal("10.00")},
        "ck_risk_evaluation_cost_when_occurred",
    ),
    (
        RiskEvaluation,
        {"state": "occurred", "occurrence_cost": Decimal("-0.01")},
        "ck_risk_evaluation_occurrence_cost_not_negative",
    ),
    *stamped(RiskEvaluation, changed=True),
    (RiskReview, {"revision_id": uuid4()}, "fk_risk_review_project_id_revision"),
    (RiskReview, {"risk_id": uuid4()}, "fk_risk_review_project_id_risk"),
    (RiskReview, {"probability": Decimal("1.0001")}, "ck_risk_review_probability_ratio"),
    (RiskReview, {"severity": Decimal("-0.01")}, "ck_risk_review_severity_not_negative"),
    (RiskReview, {"state": "forgotten"}, "ck_risk_review_state_known"),
    *stamped(RiskReview, changed=False),
    (
        RiskReferenceShare,
        {"revision_id": uuid4()},
        "fk_risk_reference_share_project_id_revision",
    ),
    (RiskReferenceShare, {"risk_id": uuid4()}, "fk_risk_reference_share_project_id_risk"),
    (
        RiskReferenceShare,
        {"provision_amount": Decimal("-0.01")},
        "ck_risk_reference_share_provision_amount_not_negative",
    ),
    *stamped(RiskReferenceShare, changed=False),
]


def resolved(parents: Parents, overrides: dict[str, object]) -> dict[str, object]:
    """Give the changes of a refusal, the values the parents hold put in place."""
    held = {
        NODE: parents.node,
        FORMER_NODE: parents.former_node,
        MAIN: parents.main,
        OTHER_OWN: parents.other_structure,
    }
    return {
        column: held.get(value, value) if isinstance(value, str) else value
        for column, value in overrides.items()
    }


@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    REFUSALS,
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_row_of_the_risks_that_breaks_a_rule(
    parents: Parents,
    owner: Engine,
    table: type[Base],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    with pytest.raises(IntegrityError) as refused, owner.begin() as connection:
        connection.execute(row(table, parents, **resolved(parents, overrides)))
    assert constraint_of(owner, refused.value) == constraint


# The unique constraints, tried apart: each needs a row written first, the evaluation of the risk
# of the parents, identified, its line the node of the parents. A second risk then names its own
# structure, or its provision line (``OWN``, ``LINE``).
OWN, LINE = "OWN", "LINE"
UNIQUE = {
    "uq_risk_evaluation_structure_id": {OWN: False, LINE: False},
    "uq_risk_evaluation_provision_node_id": {OWN: True, LINE: True},
}


@pytest.mark.parametrize(("constraint", "second"), UNIQUE.items())
def test_a_revision_names_an_own_structure_and_a_provision_line_for_one_risk_alone(
    parents: Parents, owner: Engine, constraint: str, second: dict[str, bool]
) -> None:
    # The own estimate of a risk is its own, and so is its provision line: a second risk of the
    # revision naming the structure of the first, or its line, is refused.
    other, structure = uuid4(), uuid4()
    with owner.begin() as connection:
        connection.execute(insert(Risk).values(**risk_row(parents.project, id=other)))
        connection.execute(
            insert_structure(
                parents.project, parents.revision, id=structure, kind="risk", risk_id=other
            )
        )
        connection.execute(
            row(RiskEvaluation, parents, state="identified", provision_node_id=parents.node)
        )
    line = {"state": "identified", "provision_node_id": parents.node} if second[LINE] else {}
    tried = row(
        RiskEvaluation,
        parents,
        risk_id=other,
        structure_id=structure if second[OWN] else parents.structure,
        **line,
    )
    with pytest.raises(IntegrityError) as refused, owner.begin() as connection:
        connection.execute(tried)
    assert constraint_of(owner, refused.value) == constraint


def test_every_named_constraint_of_the_risks_has_its_refusal_tried() -> None:
    # The unique indexes and constraints count; what a key names — a risk with its project — is
    # unique as its key is, and is never broken without it.
    tables = [Base.metadata.tables[table.__tablename__] for table in TABLES]
    named = {
        str(constraint.name)
        for table in tables
        for constraint in table.constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    } | {str(index.name) for table in tables for index in table.indexes if index.unique}
    tried = {constraint for _, _, constraint in REFUSALS} | UNIQUE.keys()
    assert named - {"uq_risk_project_id"} == tried


@pytest.mark.requirement("WF-REV-0020-A")
@pytest.mark.parametrize("table", [RiskEvaluation, RiskReview])
def test_an_evaluation_or_a_review_of_a_marked_revision_is_never_written(
    parents: Parents, owner: Engine, table: type[Base]
) -> None:
    # Written while its revision is current, then the revision marked: a change, a deletion and a
    # new row of it are refused, owner included, by the guard of the form of the structures'.
    with owner.begin() as connection:
        connection.execute(row(table, parents))
        connection.execute(update(Revision).where(Revision.id == parents.revision).values(**MARKED))
    of_revision = table.__table__.c.revision_id
    for statement in (
        update(table).where(of_revision == parents.revision).values(probability=Decimal("0.5")),
        delete(table).where(of_revision == parents.revision),
    ):
        with pytest.raises(DBAPIError, match=ROW_REFUSED), owner.begin() as connection:
            connection.execute(statement)
    other = risk_row(parents.project)
    with owner.begin() as connection:
        connection.execute(insert(Risk).values(**other))
    with pytest.raises(DBAPIError, match=ROW_REFUSED), owner.begin() as connection:
        connection.execute(row(table, parents, risk_id=other["id"]))


@pytest.mark.requirement("WF-DAT-0050-A")
def test_a_share_of_a_marked_revision_is_written_and_deleted(
    parents: Parents, owner: Engine
) -> None:
    # A share is written when a revision becomes the reference — a marked one — and deleted when a
    # designation is corrected: no guard refuses it.
    with owner.begin() as connection:
        connection.execute(update(Revision).where(Revision.id == parents.revision).values(**MARKED))
        connection.execute(row(RiskReferenceShare, parents))
        connection.execute(
            delete(RiskReferenceShare).where(RiskReferenceShare.revision_id == parents.revision)
        )


@pytest.mark.requirement("WF-DAT-0050-A")
@pytest.mark.parametrize("table", ["risk_evaluation", "risk_review", "risk_reference_share"])
def test_a_revised_table_of_the_risks_is_never_truncated(
    parents: Parents, owner: Engine, table: str
) -> None:
    for truncated in (table, f"{table}_p_{parents.project.hex}"):
        with pytest.raises(DBAPIError, match="never truncated"), owner.begin() as connection:
            connection.execute(text(f'TRUNCATE TABLE "{truncated}" CASCADE'))
