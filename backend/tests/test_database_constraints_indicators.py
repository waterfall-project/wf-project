# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the table of the indicators forbids, and a row outside a marking.

The constraints of ``revision_indicator`` (US-1660/L1, migration 0032), one refusal each, as
``test_database_constraints_costs.py`` tries those of EP-09; and the trigger that refuses a row
written outside the marking of its revision, judged at the end of the transaction that wrote it.
The guard of a marked revision is tried with the others, in ``test_revision_immutability.py``.
Every row is written around the services of the modules, by the owner of the tables, under a
current revision.
"""

import re
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any, get_args
from uuid import UUID, uuid4

import psycopg
import pytest
from indicators_support import indicator_row
from project_rows import AT, insert_revision
from project_rows import projects_with_partitions as with_partitions
from sqlalchemy import Engine, event, insert, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from waterfall.core.indicators.interface import IndicatorKind, stored_document
from waterfall.core.indicators.tables import KINDS, RevisionIndicator
from waterfall.core.revisions.tables import Revision
from waterfall.platform.database import Database

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.sql import Executable

# What the trigger says when a row is written outside the marking of its revision.
OUTSIDE = "the indicators of a revision are written by its marking alone"


@dataclass(frozen=True)
class Parents:
    """What a row of a test names: a project, its current revision, and another project."""

    project_id: UUID
    revision_id: UUID
    other_project_id: UUID


@pytest.fixture
def parents(database: Database, owner: Engine) -> Iterator[Parents]:
    """Write two projects with their partitions, and a current revision of the first."""
    del database
    revision_id = uuid4()
    with with_partitions(owner, 2) as (project_id, other):
        with owner.begin() as connection:
            connection.execute(insert_revision(project_id, id=revision_id))
        yield Parents(project_id, revision_id, other)


def row(parents: Parents, **overrides: object) -> Executable:
    """Give the insertion of a document under the current revision, valid but for the changes."""
    values = indicator_row(parents.project_id, parents.revision_id)
    return insert(RevisionIndicator).values(**{**values, **overrides})


# The constraint of the partitioned table a constraint of a partition comes from.
PARENT_CONSTRAINT = text(
    "WITH RECURSIVE up(parent, name) AS (SELECT conparentid, conname FROM pg_constraint "
    "WHERE conname = :name UNION SELECT c.conparentid, c.conname FROM pg_constraint AS c "
    "JOIN up ON c.oid = up.parent) SELECT name FROM up WHERE parent = 0 LIMIT 1"
)


def constraint_of(owner: Engine, error: IntegrityError) -> str:
    """Give the constraint of the table a refusal comes from, that of its partition named so."""
    cause = error.orig
    assert isinstance(cause, psycopg.Error)
    name = cause.diag.constraint_name or ""
    with owner.connect() as connection:
        return connection.scalar(PARENT_CONSTRAINT, {"name": name}) or name


# A value the parents hold: the other project, which does not hold the revision.
OTHER = "OTHER"

REFUSALS: list[tuple[dict[str, object], str]] = [
    ({"revision_id": uuid4()}, "fk_revision_indicator_project_id_revision"),
    ({"project_id": OTHER}, "fk_revision_indicator_project_id_revision"),
    ({"created_by": uuid4()}, "fk_revision_indicator_created_by_user_account"),
    ({"kind": "risks"}, "ck_revision_indicator_kind_known"),
    # The kinds of the portfolio are named whole (migration 0037): no prefix stands for them.
    ({"kind": "portfolio"}, "ck_revision_indicator_kind_known"),
    ({"scope": ""}, "ck_revision_indicator_scope_length"),
    ({"scope": "x" * 37}, "ck_revision_indicator_scope_length"),
    ({"scope": "  "}, "ck_revision_indicator_scope_not_blank"),
    ({"document": ["cpi", "spi"]}, "ck_revision_indicator_document_object"),
    ({"document": "cpi"}, "ck_revision_indicator_document_object"),
]


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(("overrides", "constraint"), REFUSALS)
def test_a_document_of_indicators_that_breaks_a_constraint_is_refused_by_the_base(
    parents: Parents, owner: Engine, overrides: dict[str, object], constraint: str
) -> None:
    named = {
        column: parents.other_project_id if value == OTHER else value
        for column, value in overrides.items()
    }
    with pytest.raises(IntegrityError) as refused, owner.begin() as connection:
        connection.execute(row(parents, **named))
    assert constraint_of(owner, refused.value) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_a_revision_keeps_one_document_by_kind_and_scope(parents: Parents, owner: Engine) -> None:
    # The same kind for another scope, or another kind for the same scope, is another document;
    # the same pair twice is refused, before the end of the transaction.
    with owner.connect() as connection:
        for written_once in (
            row(parents),
            row(parents, scope="unassigned"),
            row(parents, kind="remaining"),
        ):
            connection.execute(written_once)
        with pytest.raises(IntegrityError) as refused:
            connection.execute(row(parents))
        connection.rollback()
    assert constraint_of(owner, refused.value) == "uq_revision_indicator_project_id"


@pytest.mark.parametrize("who", ["owner", "service"])
def test_a_document_written_outside_the_marking_of_its_revision_is_refused_at_its_end(
    parents: Parents, owner: Engine, database: Database, who: str
) -> None:
    # Written while the revision is current, and the transaction ends with it current: no marking
    # wrote it, and its revision would have indicators while current (EP-10, "Tables et
    # migrations"). The owner is refused as the service is.
    with pytest.raises(DBAPIError, match=OUTSIDE):
        written(owner if who == "owner" else database, row(parents))
    with owner.connect() as connection:
        assert connection.scalars(RevisionIndicator.__table__.select()).all() == []


def written(writer: Engine | Database, *statements: Executable) -> None:
    """Run statements in one transaction, as the owner or as the service, and end it."""
    if isinstance(writer, Database):
        with writer.transaction() as session:
            for statement in statements:
                session.execute(statement)
        return
    with writer.begin() as connection:
        for statement in statements:
            connection.execute(statement)


def marking(parents: Parents, at: object) -> Executable:
    """Give the marking of the current revision at an instant, around the service."""
    return (
        update(Revision)
        .where(Revision.id == parents.revision_id)
        .values(status="marked", version_name="v1.0", marked_at=at)
    )


def test_a_document_computed_at_another_instant_than_the_marking_is_refused(
    parents: Parents, owner: Engine
) -> None:
    # The revision is marked in the transaction, but not at the instant the document says it was
    # computed at: the marking did not write it.
    with pytest.raises(DBAPIError, match=OUTSIDE):
        written(owner, row(parents), marking(parents, AT + timedelta(seconds=1)))


def test_a_document_written_by_the_transaction_that_marks_its_revision_is_kept(
    parents: Parents, owner: Engine
) -> None:
    # Written while the revision is current, computed at the instant the same transaction marks it
    # at: what the marking does (``store_indicators``, US-1670/L1).
    written(owner, row(parents), marking(parents, AT))
    with owner.connect() as connection:
        kept = connection.execute(
            RevisionIndicator.__table__.select().with_only_columns(
                RevisionIndicator.kind, RevisionIndicator.scope, RevisionIndicator.computed_at
            )
        ).all()
    assert [tuple(each) for each in kept] == [("estimate", "project", AT)]


# The kinds a marking keeps for the portfolio (EP-11, "Tables et migrations"; migration 0037).
PORTFOLIO_KINDS = (
    "portfolio_workload",
    "portfolio_cost_structure",
    "portfolio_risks",
    "portfolio_milestones",
    "portfolio_offer_curves",
)


@pytest.mark.parametrize("kind", PORTFOLIO_KINDS)
def test_a_document_of_the_portfolio_is_kept_by_the_marking_of_its_revision_alone(
    parents: Parents, owner: Engine, kind: str
) -> None:
    # The check of the kinds admits it (#3549), of the scope ``project``; the trigger is unchanged:
    # computed at another instant than the marking, it is refused as any other document.
    with pytest.raises(DBAPIError, match=OUTSIDE):
        written(owner, row(parents, kind=kind), marking(parents, AT + timedelta(seconds=1)))
    written(owner, row(parents, kind=kind), marking(parents, AT))
    with owner.connect() as connection:
        kept = connection.execute(
            RevisionIndicator.__table__.select().with_only_columns(
                RevisionIndicator.kind, RevisionIndicator.scope, RevisionIndicator.computed_at
            )
        ).all()
    assert [tuple(each) for each in kept] == [(kind, "project", AT)]


def test_the_kinds_the_interface_names_are_those_the_base_holds() -> None:
    # The kinds a reading asks ``stored_document`` for are those the check of the table accepts.
    assert get_args(IndicatorKind.__value__) == KINDS


@pytest.mark.requirement("WF-DAT-0050-A")
def test_a_stored_document_is_read_in_the_partition_of_its_project_alone(
    parents: Parents, owner: Engine, database: Database
) -> None:
    # The table is partitioned by project: the reading names the project of the revision, so that
    # the plan of its query probes the partition of that project and no other.
    written(owner, row(parents), marking(parents, AT))
    seen: list[tuple[str, dict[str, object]]] = []

    def capture(*call: Any) -> None:
        _, _, statement, parameters = call[:4]
        if "FROM revision_indicator" in statement:
            seen.append((statement, dict(parameters)))

    with database.transaction() as session:
        event.listen(session.get_bind(), "before_cursor_execute", capture)
        try:
            found = stored_document(session, parents.revision_id, "estimate", "project")
        finally:
            event.remove(session.get_bind(), "before_cursor_execute", capture)
    assert found is not None
    assert len(seen) == 1
    statement, parameters = seen[0]
    with Session(owner) as session:
        plan = session.connection().exec_driver_sql(f"EXPLAIN {statement}", parameters).all()
    named = re.compile(r"revision_indicator_p_[0-9a-f]{32}\b")
    probed = {name for (line,) in plan for name in named.findall(line)}
    held = f"revision_indicator_p_{parents.project_id.hex}"
    assert probed == {held}
