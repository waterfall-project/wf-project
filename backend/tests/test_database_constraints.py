# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database itself refuses what the rules of the tables forbid, before any service rule.

Every test writes around the data access of the module, with the table alone, to show that the
refusal is the database's (WF-DAT-0090).
"""

from datetime import UTC, datetime
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import delete, insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Executable
from support import raw_account

from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database
from waterfall.platform.installation import Installation


def constraint_of(error: IntegrityError) -> str:
    """Give the name of the constraint a refusal of the database comes from."""
    cause = error.orig
    assert isinstance(cause, psycopg.Error)
    return cause.diag.constraint_name or ""


def refusal(database: Database, statement: Executable) -> str:
    """Run a statement the database must refuse, and give the constraint that refused it."""
    with pytest.raises(IntegrityError) as raised, database.engine.begin() as connection:
        connection.execute(statement)
    return constraint_of(raised.value)


def write_account(**overrides: object) -> Executable:
    """Give the insertion of an account by hand, with the changes a test asks for."""
    return insert(UserAccount).values(**raw_account(**overrides))


def insert_account(database: Database, **overrides: object) -> dict[str, object]:
    """Insert an account around the data access, and give its columns."""
    columns = raw_account(**overrides)
    with database.engine.begin() as connection:
        connection.execute(insert(UserAccount).values(**columns))
    return columns


@pytest.mark.requirement("WF-DAT-0090-A")
def test_two_accounts_with_the_same_address_are_rejected_by_the_database(
    database: Database,
) -> None:
    insert_account(database, email="Claire.Martin@example.org")
    assert (
        refusal(database, write_account(email="claire.martin@EXAMPLE.org"))
        == "uq_user_account_email_lower"
    )


@pytest.mark.requirement("WF-DAT-0090-A")
def test_two_accounts_with_the_same_subject_of_the_identity_provider_are_rejected(
    database: Database,
) -> None:
    insert_account(database, idp_subject="the-subject", email="a@example.org")
    statement = write_account(idp_subject="the-subject", email="b@example.org")
    assert refusal(database, statement) == "uq_user_account_idp_subject"


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"state": "archived"}, "ck_user_account_state_known"),
        ({"origin": "elsewhere"}, "ck_user_account_origin_known"),
        (
            {"avatar": b"x", "avatar_media_type": "image/gif"},
            "ck_user_account_avatar_media_type_known",
        ),
        (
            {"avatar": b"x" * (8 * 1024 * 1024 + 1), "avatar_media_type": "image/png"},
            "ck_user_account_avatar_size",
        ),
        ({"avatar": b"x"}, "ck_user_account_avatar_with_its_media_type"),
        ({"avatar_media_type": "image/png"}, "ck_user_account_avatar_with_its_media_type"),
        ({"lock_version": -1}, "ck_user_account_lock_version_not_negative"),
        ({"last_name": ""}, "ck_user_account_last_name_length"),
        ({"first_name": "x" * 101}, "ck_user_account_first_name_length"),
        ({"email": ""}, "ck_user_account_email_not_empty"),
        ({"idp_subject": ""}, "ck_user_account_idp_subject_not_empty"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_an_account_that_breaks_a_check(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    assert refusal(database, write_account(**overrides)) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_an_avatar_of_exactly_the_bound_is_accepted(database: Database) -> None:
    columns = insert_account(
        database, avatar=b"x" * (8 * 1024 * 1024), avatar_media_type="image/jpeg"
    )
    with database.engine.connect() as connection:
        size = connection.execute(
            text("SELECT octet_length(avatar) FROM user_account WHERE id = :id"), columns
        ).scalar_one()
    assert size == 8 * 1024 * 1024


@pytest.mark.requirement("WF-DAT-0090-A")
def test_an_account_is_active_unless_written_otherwise(database: Database) -> None:
    columns = insert_account(database)
    with database.engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT state, lock_version, display_preferences FROM user_account WHERE id = :id"
            ),
            columns,
        ).one()
    assert tuple(row) == ("active", 0, {})


@pytest.mark.requirement("WF-DAT-0090-A")
def test_every_foreign_key_of_the_schema_refuses_by_default(database: Database) -> None:
    with database.engine.connect() as connection:
        actions = connection.execute(
            text("SELECT conname, confdeltype, confupdtype FROM pg_constraint WHERE contype = 'f'")
        ).all()
    assert len(actions) >= 2
    assert {(row.confdeltype, row.confupdtype) for row in actions} <= {("r", "a"), ("a", "a")}


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize("column", ["created_by", "updated_by"])
def test_an_author_that_is_not_an_account_is_refused(database: Database, column: str) -> None:
    statement = write_account(**{column: uuid4()})
    assert refusal(database, statement) == f"fk_user_account_{column}_user_account"


@pytest.mark.requirement("WF-DAT-0090-A")
def test_an_account_that_authored_another_cannot_be_deleted(database: Database) -> None:
    author = insert_account(database, email="author@example.org")
    insert_account(
        database, email="written@example.org", created_by=author["id"], updated_by=author["id"]
    )
    statement = delete(UserAccount).where(UserAccount.id == author["id"])
    assert refusal(database, statement) == "fk_user_account_created_by_user_account"


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_installation_holds_one_row_in_one_language_under_the_bound_of_the_avatar(
    database: Database,
) -> None:
    good = {
        "id": 1,
        "default_language": "fr",
        "avatar_max_bytes": 2_097_152,
        "external_backup_max_bytes": 1_000_000,
        "installed_at": datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
    }

    def row(**changes: object) -> Executable:
        return insert(Installation).values(**{**good, **changes})

    with database.engine.begin() as connection:
        connection.execute(row())
    assert refusal(database, row(id=2)) == "ck_installation_single_row"
    assert refusal(database, row()) == "pk_installation"
    with database.engine.begin() as connection:
        connection.execute(delete(Installation))
    assert refusal(database, row(default_language="de")) == (
        "ck_installation_default_language_known"
    )
    assert refusal(database, row(avatar_max_bytes=8 * 1024 * 1024 + 1)) == (
        "ck_installation_avatar_max_bytes_bound"
    )
    assert refusal(database, row(external_backup_max_bytes=2**53)) == (
        "ck_installation_external_backup_max_bytes_bound"
    )
    with database.engine.begin() as connection:
        connection.execute(row(default_language="en", avatar_max_bytes=8 * 1024 * 1024))
        stored = connection.execute(text("SELECT installed_at FROM installation")).scalar_one()
    assert stored == good["installed_at"]


def write_inscription(**overrides: object) -> Executable:
    """Give the insertion of an inscription of the journal by hand, with the changes asked for."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "occurred_at": datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
        "action": "access_role_create",
        "object_kind": "access_role",
        "object_id": uuid4(),
        "object_label": "Auditeur",
        "params": {},
        "correlation_id": "req-1",
    }
    return insert(AuditEntry).values(**{**columns, **overrides})


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"action": "access_role_rename"}, "ck_audit_entry_action_known"),
        ({"object_kind": "task"}, "ck_audit_entry_object_kind_known"),
        ({"actor_user_id": uuid4()}, "ck_audit_entry_actor_named"),
        ({"actor_display_name": "Claire Martin"}, "ck_audit_entry_actor_named"),
        ({"project_id": uuid4(), "project_code": "PRJ-001"}, "ck_audit_entry_project_named"),
        ({"project_code": "PRJ-001", "project_label": "Poste"}, "ck_audit_entry_project_named"),
        ({"object_label": None}, "ck_audit_entry_object_labeled"),
        ({"object_revision_label": "Référence"}, "ck_audit_entry_object_revision_named"),
        ({"params": ["user_id"]}, "ck_audit_entry_params_object"),
        ({"correlation_id": "two words"}, "ck_audit_entry_correlation_id_form"),
        ({"correlation_id": "x" * 65}, "ck_audit_entry_correlation_id_form"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_an_inscription_that_breaks_a_check(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    assert refusal(database, write_inscription(**overrides)) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_an_inscription_outlives_the_account_and_the_project_it_names(database: Database) -> None:
    named = {"actor_user_id": uuid4(), "actor_display_name": "Claire Martin", "project_id": uuid4()}
    statement = write_inscription(**named, project_code="PRJ-001", project_label="Poste")
    with database.engine.begin() as connection:
        connection.execute(statement)
        foreign_keys = connection.execute(
            text(
                "SELECT count(*) FROM pg_constraint WHERE conrelid = 'audit_entry'::regclass "
                "AND contype = 'f'"
            )
        ).scalar_one()
    assert foreign_keys == 0
