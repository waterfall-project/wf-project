# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The project managers in the journal, the contributors stamped: migration 0056 (US-2980/L1).

The migration stamps the contributors already there, admits the three actions and the contributor
as an object, and lets the label of a contributor be forgotten with its account; its descent
refuses them again, and fails while the journal holds one.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from project_rows import insert_project
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import DBAPIError
from support import raw_account

from waterfall.core.users.tables import UserAccount
from waterfall.migrations.runner import downgrade, upgrade
from waterfall.platform.audit import AuditEntry

if TYPE_CHECKING:
    from sqlalchemy import Connection, Engine

MOMENT = datetime(2026, 11, 19, tzinfo=UTC)
CLOCK = text("SELECT clock_timestamp()")
VERSION = text("SELECT version_num FROM alembic_version")


def an_account(connection: Connection, *, anonymized: bool = False) -> UUID:
    """Write an account, named or anonymised, and give its identifier."""
    columns: dict[str, object] = (
        {
            "first_name": None,
            "last_name": None,
            "email": None,
            "state": "deactivated",
            "anonymized_at": MOMENT,
        }
        if anonymized
        else {"email": f"{uuid4().hex}@example.org"}
    )
    row = raw_account(**columns)
    connection.execute(insert(UserAccount).values(**row))
    return UUID(str(row["id"]))


def an_entry(connection: Connection, action: str, kind: str, object_id: UUID) -> UUID:
    """Inscribe a line of the journal, labelled, and give its identifier."""
    entry = uuid4()
    connection.execute(
        insert(AuditEntry).values(
            id=entry,
            occurred_at=MOMENT,
            action=action,
            object_kind=kind,
            object_id=object_id,
            object_label="Inès Roux",
            params={},
            correlation_id="managers",
        )
    )
    return entry


@pytest.mark.requirement("WF-DAT-0070-A")
def test_a_contributor_there_before_the_migration_is_dated_by_it_and_written_by_the_platform(
    empty_engine: Engine,
) -> None:
    # The columns of audit of a contributor (#3988): a line inscribed before them is dated by the
    # migration, its authors null — the platform —, no one knowing who wrote it.
    upgrade(empty_engine, "0055")
    project = uuid4()
    with empty_engine.begin() as connection:
        user = an_account(connection)
        connection.execute(insert_project(id=project))
        connection.execute(
            text(
                "INSERT INTO contributor (project_id, user_account_id, kind) "
                "VALUES (:project, :user, 'project_manager')"
            ),
            {"project": project, "user": user},
        )
    with empty_engine.connect() as connection:
        before = connection.scalar(CLOCK)
    upgrade(empty_engine, "0056")
    with empty_engine.connect() as connection:
        after = connection.scalar(CLOCK)
        row = (
            connection.execute(
                text(
                    "SELECT kind, created_at, created_by, updated_at, updated_by FROM contributor "
                    "WHERE project_id = :project AND user_account_id = :user"
                ),
                {"project": project, "user": user},
            )
            .mappings()
            .one()
        )
    assert before is not None
    assert after is not None
    assert row["kind"] == "project_manager"
    assert before <= row["created_at"] <= after
    assert row["updated_at"] == row["created_at"]
    assert (row["created_by"], row["updated_by"]) == (None, None)


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.parametrize(
    ("action", "kind", "refused"),
    [
        ("project_manager_add", "project", "action_known"),
        ("project_manager_remove", "project", "action_known"),
        ("project_manager_change", "project", "action_known"),
        ("project_exit", "contributor", "object_kind_known"),
    ],
)
def test_the_descent_fails_while_the_journal_holds_a_project_manager_or_a_contributor(
    empty_engine: Engine, action: str, kind: str, refused: str
) -> None:
    # The journal is never deleted nor rewritten: a descent that refused again what it holds would
    # make it lie; it fails, and the schema stays at 0056 with the line.
    upgrade(empty_engine, "0056")
    with empty_engine.begin() as connection:
        an_entry(connection, action, kind, an_account(connection))
    with pytest.raises(DBAPIError, match=refused):
        downgrade(empty_engine, "0055")
    with empty_engine.connect() as connection:
        assert connection.scalar(VERSION) == "0056"
        assert connection.scalar(select(func.count()).select_from(AuditEntry)) == 1
        columns = connection.scalars(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'contributor' AND column_name LIKE '%\\_by'"
            )
        )
        assert sorted(columns) == ["created_by", "updated_by"]


def forget(connection: Connection, entry: UUID) -> None:
    """Make null the label of a line of the journal, as the anonymisation of its account does."""
    connection.execute(update(AuditEntry).where(AuditEntry.id == entry).values(object_label=None))


def labels(engine: Engine) -> dict[str, str | None]:
    """Read the label of each line of the journal, by the nature of its object."""
    with engine.connect() as connection:
        rows = connection.execute(select(AuditEntry.object_kind, AuditEntry.object_label)).all()
    return {row.object_kind: row.object_label for row in rows}


@pytest.mark.requirement("WF-SEC-0030-A")
def test_after_the_descent_the_triggers_refuse_again_to_forget_the_label_of_a_contributor(
    empty_engine: Engine,
) -> None:
    # At 0056 the label of a contributor whose account is anonymised may be forgotten
    # (WF-ADM-0060, test_contributors); after the descent the triggers of 0011 forget the label of
    # an account alone. The checks of 0055 refuse a contributor before any trigger: they are
    # dropped here, so that the triggers alone answer, for an account and for a contributor.
    upgrade(empty_engine, "0056")
    downgrade(empty_engine, "0055")
    with empty_engine.begin() as connection:
        for name in ("object_kind_known", "object_labeled"):
            connection.execute(
                text(f"ALTER TABLE audit_entry DROP CONSTRAINT ck_audit_entry_{name}")
            )
        account = an_account(connection, anonymized=True)
        user = an_entry(connection, "user_anonymize", "user", account)
        contributor = an_entry(connection, "project_exit", "contributor", account)
    with empty_engine.begin() as connection:
        forget(connection, user)
    with pytest.raises(DBAPIError, match="refused"), empty_engine.begin() as connection:
        forget(connection, contributor)
    assert labels(empty_engine) == {"user": None, "contributor": "Inès Roux"}
