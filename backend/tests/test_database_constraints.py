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
from sqlalchemy import Engine, delete, insert, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Executable
from support import raw_account

from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
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
def test_an_account_that_authored_another_cannot_be_deleted(
    database: Database, owner: Engine
) -> None:
    author = insert_account(database, email="author@example.org")
    insert_account(
        database, email="written@example.org", created_by=author["id"], updated_by=author["id"]
    )
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(delete(UserAccount).where(UserAccount.id == author["id"]))
    assert constraint_of(raised.value) == "fk_user_account_created_by_user_account"


@pytest.mark.requirement("WF-DAT-0090-A")
def test_the_installation_holds_one_row_in_one_language_under_the_bound_of_the_avatar(
    database: Database, owner: Engine
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
    with owner.begin() as connection:
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


def write_permission(**overrides: object) -> Executable:
    """Give the insertion of a permission by hand, as only a migration writes one."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "code": "reports.read",
        "kind": "function_read",
        "fbs_code": "FBS-5.1",
        "position": 1000,
    }
    return insert(Permission).values(**{**columns, **overrides})


def owner_refusal(owner: Engine, statement: Executable) -> str:
    """Run as the owner a statement the database must refuse, and give the refusing constraint."""
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(statement)
    return constraint_of(raised.value)


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"kind": "function_manage"}, "ck_permission_kind_known"),
        ({"fbs_code": None}, "ck_permission_fbs_code_of_a_function"),
        ({"kind": "irreversible"}, "ck_permission_fbs_code_of_a_function"),
        ({"fbs_code": "FBS-5"}, "ck_permission_fbs_code_form"),
        ({"position": -1}, "ck_permission_position_not_negative"),
        ({"code": "users.read"}, "uq_permission_code"),
        ({"position": 0}, "uq_permission_position"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_permission_that_breaks_a_rule_of_the_catalogue(
    owner: Engine, overrides: dict[str, object], constraint: str
) -> None:
    assert owner_refusal(owner, write_permission(**overrides)) == constraint


def write_role(**overrides: object) -> Executable:
    """Give the insertion of a role by hand, with the changes a test asks for."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "label": "Chiffreur",
        "is_predefined": False,
        "created_at": datetime(2026, 10, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 10, 1, tzinfo=UTC),
    }
    return insert(AccessRole).values(**{**columns, **overrides})


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"label": ""}, "ck_access_role_label_length"),
        ({"label": "x" * 101}, "ck_access_role_label_length"),
        ({"lock_version": -1}, "ck_access_role_lock_version_not_negative"),
        ({"created_by": uuid4()}, "fk_access_role_created_by_user_account"),
        ({"updated_by": uuid4()}, "fk_access_role_updated_by_user_account"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_role_that_breaks_a_check(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    assert refusal(database, write_role(**overrides)) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_a_role_grants_and_an_account_holds_only_what_exists_and_once(
    database: Database, owner: Engine
) -> None:
    account = insert_account(database)["id"]
    role_id = uuid4()
    with database.engine.begin() as connection:
        connection.execute(write_role(id=role_id))
        permission = connection.execute(
            text("SELECT id FROM permission WHERE code = 'users.read'")
        ).scalar_one()
        connection.execute(
            insert(AccessRolePermission).values(access_role_id=role_id, permission_id=permission)
        )
        connection.execute(
            insert(UserAccessRole).values(user_account_id=account, access_role_id=role_id)
        )
    grant = insert(AccessRolePermission)
    hold = insert(UserAccessRole)
    assert refusal(database, grant.values(access_role_id=role_id, permission_id=uuid4())) == (
        "fk_access_role_permission_permission_id_permission"
    )
    assert refusal(database, grant.values(access_role_id=uuid4(), permission_id=permission)) == (
        "fk_access_role_permission_access_role_id_access_role"
    )
    assert refusal(database, grant.values(access_role_id=role_id, permission_id=permission)) == (
        "pk_access_role_permission"
    )
    assert refusal(database, hold.values(user_account_id=uuid4(), access_role_id=role_id)) == (
        "fk_user_access_role_user_account_id_user_account"
    )
    assert refusal(database, hold.values(user_account_id=account, access_role_id=uuid4())) == (
        "fk_user_access_role_access_role_id_access_role"
    )
    assert refusal(database, hold.values(user_account_id=account, access_role_id=role_id)) == (
        "pk_user_access_role"
    )
    # What a role grants, and a role that is held, cannot disappear under it.
    assert owner_refusal(owner, delete(Permission).where(Permission.id == permission)) == (
        "fk_access_role_permission_permission_id_permission"
    )
    assert owner_refusal(owner, delete(AccessRole).where(AccessRole.id == role_id)) in {
        "fk_access_role_permission_access_role_id_access_role",
        "fk_user_access_role_access_role_id_access_role",
    }
