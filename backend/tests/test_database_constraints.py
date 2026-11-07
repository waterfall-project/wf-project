# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database itself refuses what the rules of the tables forbid, before any service rule.

Every test writes around the data access of the module, with the table alone, to show that the
refusal is the database's (WF-DAT-0090).
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import Engine, delete, insert, select, text
from sqlalchemy.exc import IntegrityError
from support import raw_account

from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.core.backups.tables import Backup
from waterfall.core.cost_settings.tables import (
    ActualCostMapping,
    ActualCostMappingLabel,
    CostCategory,
    CostType,
    HourlyRate,
    ReferenceSetting,
)
from waterfall.core.cost_settings.tables import (
    Audited as CostAudited,
)
from waterfall.core.resource_settings.tables import (
    DAYS,
    Calendar,
    DurationUnit,
    OrgNode,
    ResourceRole,
)
from waterfall.core.resource_settings.tables import (
    Audited as ResourceAudited,
)
from waterfall.core.users.tables import IdentitySyncReport, UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Base, Database
from waterfall.platform.installation import Installation
from waterfall.platform.tasks import BackgroundTask
from waterfall.platform.uploads import FileUpload

if TYPE_CHECKING:
    from sqlalchemy.sql import Executable

ANONYMIZED = datetime(2026, 10, 8, 9, 30, tzinfo=UTC)
# An anonymised account as the database holds it: deactivated, without its names nor its address.
FORGOTTEN: dict[str, object] = {
    "anonymized_at": ANONYMIZED,
    "state": "deactivated",
    "last_name": None,
    "first_name": None,
    "email": None,
}


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
@pytest.mark.parametrize(
    ("held", "written"),
    [
        ("Claire.Martin@example.org", "claire.martin@EXAMPLE.org"),
        # Every letter is lowered, not only the ASCII ones that the collation of the column knows.
        ("Élodie.Faure@example.org", "élodie.faure@example.org"),
    ],
)
def test_two_accounts_with_the_same_address_are_rejected_by_the_database(
    database: Database, held: str, written: str
) -> None:
    insert_account(database, email=held)
    assert refusal(database, write_account(email=written)) == "uq_user_account_email_lower"


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
        # The names and the address are null for an anonymised account, and for it alone; it
        # stays deactivated, without its avatar (WF-ADM-0060).
        ({"last_name": None}, "ck_user_account_identity_unless_anonymized"),
        ({"email": None}, "ck_user_account_identity_unless_anonymized"),
        (
            {"anonymized_at": ANONYMIZED, "state": "deactivated"},
            "ck_user_account_identity_unless_anonymized",
        ),
        ({**FORGOTTEN, "first_name": "Claire"}, "ck_user_account_identity_unless_anonymized"),
        ({**FORGOTTEN, "state": "active"}, "ck_user_account_anonymized_deactivated"),
        (
            {**FORGOTTEN, "avatar": b"x", "avatar_media_type": "image/png"},
            "ck_user_account_anonymized_deactivated",
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_an_account_that_breaks_a_check(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    assert refusal(database, write_account(**overrides)) == constraint


def test_two_anonymized_accounts_hold_no_address_and_are_both_accepted(database: Database) -> None:
    # The index of the addresses admits several null ones (#832).
    for _ in range(2):
        insert_account(database, **FORGOTTEN)
    with database.engine.connect() as connection:
        held = connection.execute(text("SELECT count(*) FROM user_account WHERE email IS NULL"))
        assert held.scalar_one() == 2


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
@pytest.mark.usefixtures("database")
def test_the_installation_holds_one_row_in_one_language_under_the_bound_of_the_avatar(
    owner: Engine,
) -> None:
    # The bootstrap writes the row, as the owner of the tables (#701).
    database = Database(owner)
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
        # The platform has no name.
        ({"actor_display_name": "Claire Martin"}, "ck_audit_entry_actor_named"),
        ({"project_id": uuid4(), "project_code": "PRJ-001"}, "ck_audit_entry_project_named"),
        ({"project_code": "PRJ-001", "project_label": "Poste"}, "ck_audit_entry_project_named"),
        # A code without a project (#2166).
        ({"project_code": "PRJ-001"}, "ck_audit_entry_project_named"),
        ({"object_label": None}, "ck_audit_entry_object_labeled"),
        # A revision keeps its label in every inscription but its abandonment's.
        (
            {"action": "revision_mark", "object_kind": "revision", "object_label": None},
            "ck_audit_entry_object_labeled",
        ),
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


@pytest.mark.requirement("WF-SEC-0030-A")
def test_an_anonymized_account_is_named_by_no_label_as_author_or_as_object(
    database: Database,
) -> None:
    # An account that lost its name to its anonymisation is still the author and the object, by
    # its identifier (WF-ADM-0060); any other object keeps its label.
    forgotten = uuid4()
    statement = write_inscription(
        actor_user_id=forgotten, object_kind="user", object_id=forgotten, object_label=None
    )
    with database.engine.begin() as connection:
        connection.execute(statement)
    assert refusal(database, write_inscription(object_label=None)) == (
        "ck_audit_entry_object_labeled"
    )


@pytest.mark.requirement("WF-SEC-0030-A")
def test_a_project_without_code_is_inscribed_by_its_identifier_and_its_label(
    database: Database,
) -> None:
    # A project is born without code (WF-PRJ-0010): its creation is inscribed all the same (#2166).
    project_id = uuid4()
    statement = write_inscription(
        action="project_create",
        object_kind="project",
        object_id=project_id,
        object_label="Poste",
        project_id=project_id,
        project_label="Poste",
    )
    with database.engine.begin() as connection:
        connection.execute(statement)
        named = connection.execute(
            select(AuditEntry.project_id, AuditEntry.project_code, AuditEntry.project_label)
        ).all()
    assert [tuple(row) for row in named] == [(project_id, None, "Poste")]


@pytest.mark.requirement("WF-SEC-0030-A")
def test_the_abandonment_of_a_revision_is_inscribed_without_its_label(database: Database) -> None:
    # The abandoned revision is deleted: its inscription names it by its identifier alone (#2161).
    statement = write_inscription(
        action="revision_abandon", object_kind="revision", object_label=None
    )
    with database.engine.begin() as connection:
        connection.execute(statement)
        labels = connection.execute(select(AuditEntry.object_label)).scalars().all()
    assert labels == [None]


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


def write_task(**overrides: object) -> Executable:
    """Give the insertion of a background task by hand, queued, with the changes asked for."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "kind": "identity_sync",
        "status": "queued",
        "progress": 0,
        "payload": {},
        "correlation_id": "req-1",
        "attempts": 0,
        "submitted_at": datetime(2026, 10, 11, 7, 0, tzinfo=UTC),
    }
    return insert(BackgroundTask).values(**{**columns, **overrides})


ENDED = datetime(2026, 10, 11, 7, 5, tzinfo=UTC)


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"kind": "directory_sync"}, "ck_background_task_kind_known"),
        ({"status": "cancelled"}, "ck_background_task_status_known"),
        ({"progress": 101}, "ck_background_task_progress_bound"),
        ({"progress": -1}, "ck_background_task_progress_bound"),
        ({"attempts": -1}, "ck_background_task_attempts_not_negative"),
        ({"payload": ["identity_sync"]}, "ck_background_task_payload_object"),
        ({"status": "failed", "finished_at": ENDED}, "ck_background_task_problem_of_a_failure"),
        ({"problem": {"code": "INTERNAL_ERROR"}}, "ck_background_task_problem_of_a_failure"),
        ({"status": "succeeded"}, "ck_background_task_finished_at_end"),
        ({"finished_at": ENDED}, "ck_background_task_finished_at_end"),
        ({"correlation_id": "two words"}, "ck_background_task_correlation_id_form"),
        ({"requested_by": uuid4()}, "fk_background_task_requested_by_user_account"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_task_that_breaks_a_rule(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    assert refusal(database, write_task(**overrides)) == constraint


def write_backup(of_task: object, **overrides: object) -> Executable:
    """Give the insertion of a backup by hand, verified, with the changes asked for."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "taken_at": ENDED,
        "size_bytes": 2048,
        "verification": "passed",
        "origin": "manual",
        "is_retained": False,
        "object_key": f"backup-{of_task}.tar",
        "application_version": "0.1.0",
        "schema_revision": "0010",
        "task_id": of_task,
    }
    return insert(Backup).values(**{**columns, **overrides})


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"verification": "skipped"}, "ck_backup_verification_known"),
        ({"origin": "imported"}, "ck_backup_origin_known"),
        ({"size_bytes": -1}, "ck_backup_size_bytes_not_negative"),
        ({"task_id": uuid4()}, "fk_backup_task_id_background_task"),
        ({"object_key": "taken.tar"}, "uq_backup_object_key"),
        ({}, "uq_backup_task_id"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_backup_that_breaks_a_rule(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    task_id, other = uuid4(), uuid4()
    with database.engine.begin() as connection:
        connection.execute(write_task(id=task_id, kind="backup"))
        connection.execute(write_task(id=other, kind="backup"))
        connection.execute(write_backup(other, object_key="taken.tar"))
        if not overrides:
            connection.execute(write_backup(task_id, object_key="first.tar"))
    assert refusal(database, write_backup(task_id, **overrides)) == constraint


def write_report(of_task: object, **overrides: object) -> Executable:
    """Give the insertion of the report of a reading of the accounts, with the changes asked for."""
    columns: dict[str, object] = {
        "task_id": of_task,
        "finished_at": ENDED,
        "created": 1,
        "updated": 0,
        "deactivated": 0,
        "skipped": [],
        "removed": [],
    }
    return insert(IdentitySyncReport).values(**{**columns, **overrides})


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"created": -1}, "ck_identity_sync_report_counts_not_negative"),
        ({"deactivated": -1}, "ck_identity_sync_report_counts_not_negative"),
        ({"restored": -1}, "ck_identity_sync_report_restored_not_negative"),
        ({"skipped": {"email": "a@b"}}, "ck_identity_sync_report_skipped_array"),
        ({"removed": "a@b"}, "ck_identity_sync_report_removed_array"),
        ({"task_id": uuid4()}, "fk_identity_sync_report_task_id_background_task"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_report_of_a_reading_that_breaks_a_rule(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    task_id = uuid4()
    with database.engine.begin() as connection:
        connection.execute(write_task(id=task_id, kind="identity_sync"))
    assert refusal(database, write_report(task_id, **overrides)) == constraint


def write_upload(by: object, **overrides: object) -> Executable:
    """Give the insertion of a deposit by parts, open, with the changes asked for."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "purpose": "external_backup",
        "filename": "copie.tar",
        "size_bytes": 1,
        "part_size_bytes": 5 * 1024**2,
        "part_count": 1,
        "object_key": f"uploads/{uuid4()}",
        "deposit": "opened",
        "uploaded_by": by,
        "created_at": ENDED,
        "expires_at": ENDED,
    }
    return insert(FileUpload).values(**{**columns, **overrides})


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"purpose": "avatar"}, "ck_file_upload_purpose_known"),
        ({"filename": ""}, "ck_file_upload_filename_length"),
        ({"filename": "x" * 256}, "ck_file_upload_filename_length"),
        ({"size_bytes": 0}, "ck_file_upload_size_bytes_positive"),
        ({"part_size_bytes": 5 * 1024**2 - 1}, "ck_file_upload_part_size_bound"),
        ({"part_size_bytes": 10 * 1024**2 + 1}, "ck_file_upload_part_size_bound"),
        ({"part_count": 0}, "ck_file_upload_part_count_bound"),
        ({"part_count": 10_001}, "ck_file_upload_part_count_bound"),
        ({"deposit": None}, "ck_file_upload_open_or_completed"),
        ({"completed_at": ENDED}, "ck_file_upload_open_or_completed"),
        ({"uploaded_by": uuid4()}, "fk_file_upload_uploaded_by_user_account"),
        ({"object_key": "uploads/taken"}, "uq_file_upload_object_key"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_a_deposit_that_breaks_a_rule(
    database: Database, overrides: dict[str, object], constraint: str
) -> None:
    account = raw_account()
    with database.engine.begin() as connection:
        connection.execute(insert(UserAccount).values(**account))
        connection.execute(write_upload(account["id"], object_key="uploads/taken"))
    assert refusal(database, write_upload(account["id"], **overrides)) == constraint


# The reference (§4.4.1, regime "reference"; EP-05): rows written around the service, each valid
# unless a test changes it, after the parents they name.
AT = datetime(2026, 11, 6, 9, 0, tzinfo=UTC)
NODE, NATURE, CATEGORY, CALENDAR, SELF = (uuid4() for _ in range(5))
WEEK = {**dict.fromkeys(DAYS[:5], Decimal(8)), **dict.fromkeys(DAYS[5:], Decimal(0))}
PARENTS: dict[type[Base], dict[str, object]] = {
    OrgNode: {"id": NODE, "code": "DT"},
    CostType: {"id": NATURE, "code": "MO", "kind": "labor"},
    CostCategory: {"id": CATEGORY, "code": "ING", "accounting_code": "641", "cost_type_id": NATURE},
    Calendar: {"id": CALENDAR, "label": "Standard", **WEEK, "is_default": True},
}
BOUNDS = {
    f"{axis}_bound_{rank}": Decimal(bound)
    for axis, bounds in (("probability", (".25", ".5", ".75")), ("severity", (".01", ".05", ".1")))
    for rank, bound in enumerate(bounds, 1)
}
VALID: dict[type[Base], dict[str, object]] = {
    ReferenceSetting: {
        "id": 1,
        "currency_code": "EUR",
        "company_name": "Delmas Automatismes",
        **BOUNDS,
        "risk_zones": ["nominal"] * 16,
        **dict.fromkeys(("cost_watch", "schedule_watch"), Decimal("0.9")),
        **dict.fromkeys(("cost_alert", "schedule_alert"), Decimal("0.8")),
        "max_weeks_between_reviews": 6,
    },
    DurationUnit: {
        "id": 1,
        "hours_per_day": Decimal(8),
        "hours_per_week": Decimal(40),
        "days_per_month": Decimal(20),
    },
    CostType: {"kind": "non_labor"},
    CostCategory: {"accounting_code": "604", "cost_type_id": NATURE},
    HourlyRate: {"cost_category_id": CATEGORY, "year": 2026, "amount": Decimal("85.00")},
    OrgNode: {"parent_id": NODE},
    Calendar: {**WEEK, "is_default": False},
    ResourceRole: {
        "org_node_id": NODE,
        "cost_category_id": CATEGORY,
        "calendar_id": CALENDAR,
        "monthly_hours": Decimal(140),
        "headcount": Decimal(2),
    },
    ActualCostMapping: {"id": 1},
    ActualCostMappingLabel: {"kind": "read", "column": "amount", "position": 0, "label": "Montant"},
}
# What a row already held — deactivated, which leaves it its code — takes from the one tried.
HELD: dict[type[Base], dict[str, object]] = {
    CostType: {"code": "TAKEN", "is_active": False},
    CostCategory: {"code": "TAKEN", "accounting_code": "TAKEN", "is_active": False},
    HourlyRate: {"year": 2025},
    OrgNode: {"code": "TAKEN", "is_active": False},
    Calendar: {"label": "Pris", "is_active": False},
    ResourceRole: {"code": "TAKEN", "is_active": False},
    ActualCostMappingLabel: {"label": "Pris", "folded": "pris", "column": "wbs_element"},
}


def reference_row(table: type[Base], **columns: object) -> Executable:
    """Give the insertion of a row of the reference: its own identifier, code and label, audited.

    Active unless said otherwise; a label of the mapping folded as its label is, lowered.
    """
    held = set(table.__table__.columns.keys())
    given: dict[str, object] = {"id": uuid4()}
    if "created_at" in held:
        given |= {"created_at": AT, "updated_at": AT}
    own = {"code": uuid4().hex[:20], "label": f"L {uuid4().hex}", "is_active": True}
    given |= {name: value for name, value in own.items() if name in held}
    given |= columns
    if "folded" in held:
        given.setdefault("folded", str(given["label"]).lower())
    return insert(table).values(**given)


# The tables of the reference that keep the audit columns; the labels of the mapping do not.
AUDITED = (
    ReferenceSetting,
    DurationUnit,
    CostType,
    CostCategory,
    HourlyRate,
    OrgNode,
    Calendar,
    ResourceRole,
    ActualCostMapping,
)
# What every audited table refuses besides its own rules: a negative counter, an author that is no
# account.


def audit_refusals() -> list[tuple[type[Base], dict[str, object], str]]:
    """Give, for each audited table, the three refusals the audit columns bring."""
    refused: list[tuple[type[Base], dict[str, object], str]] = []
    for table in AUDITED:
        name = table.__tablename__
        refused.append((table, {"lock_version": -1}, f"ck_{name}_lock_version_not_negative"))
        refused.append((table, {"created_by": uuid4()}, f"fk_{name}_created_by_user_account"))
        refused.append((table, {"updated_by": uuid4()}, f"fk_{name}_updated_by_user_account"))
    return refused


AUDIT_REFUSALS = audit_refusals()

REFUSALS: list[tuple[type[Base], dict[str, object], str]] = [
    (ReferenceSetting, {"id": 2}, "ck_reference_setting_single_row"),
    (ReferenceSetting, {"currency_code": "eur"}, "ck_reference_setting_currency_code_form"),
    (ReferenceSetting, {"currency_code": "EURO"}, "ck_reference_setting_currency_code_form"),
    (ReferenceSetting, {"company_name": ""}, "ck_reference_setting_company_name_length"),
    (ReferenceSetting, {"company_name": "x" * 201}, "ck_reference_setting_company_name_length"),
    (ReferenceSetting, {"company_name": " \t"}, "ck_reference_setting_company_name_not_blank"),
    (
        ReferenceSetting,
        {"probability_bound_2": Decimal(".25")},
        "ck_reference_setting_probability_bounds_increasing",
    ),
    (
        ReferenceSetting,
        {"severity_bound_3": Decimal(".05")},
        "ck_reference_setting_severity_bounds_increasing",
    ),
    (
        ReferenceSetting,
        {"risk_zones": ["watch"] * 15},
        "ck_reference_setting_risk_zones_sixteen",
    ),
    (
        ReferenceSetting,
        {"risk_zones": [["watch"] * 4] * 4},
        "ck_reference_setting_risk_zones_sixteen",
    ),
    (
        ReferenceSetting,
        {"risk_zones": ["watch"] * 15 + ["red"]},
        "ck_reference_setting_risk_zones_known",
    ),
    (
        ReferenceSetting,
        {"cost_watch": Decimal(1)},
        "ck_reference_setting_thresholds_between_zero_and_one",
    ),
    (
        ReferenceSetting,
        {"schedule_alert": Decimal(0)},
        "ck_reference_setting_thresholds_between_zero_and_one",
    ),
    (
        ReferenceSetting,
        {"cost_alert": Decimal("0.9")},
        "ck_reference_setting_alert_below_watch",
    ),
    (
        ReferenceSetting,
        {"max_weeks_between_reviews": 0},
        "ck_reference_setting_max_weeks_between_reviews_bound",
    ),
    (
        ReferenceSetting,
        {"max_weeks_between_reviews": 105},
        "ck_reference_setting_max_weeks_between_reviews_bound",
    ),
    (DurationUnit, {"id": 2}, "ck_duration_unit_single_row"),
    (DurationUnit, {"hours_per_day": Decimal(0)}, "ck_duration_unit_constants_positive"),
    (DurationUnit, {"days_per_month": Decimal(-20)}, "ck_duration_unit_constants_positive"),
    (CostType, {"code": "TAKEN"}, "uq_cost_type_code"),
    (CostType, {"code": ""}, "ck_cost_type_code_length"),
    (CostType, {"code": "x" * 21}, "ck_cost_type_code_length"),
    (CostType, {"code": "  "}, "ck_cost_type_code_not_blank"),
    (CostType, {"label": "x" * 201}, "ck_cost_type_label_length"),
    (CostType, {"label": " "}, "ck_cost_type_label_not_blank"),
    (CostType, {"kind": "subcontracting"}, "ck_cost_type_kind_known"),
    (CostCategory, {"code": "TAKEN"}, "uq_cost_category_code"),
    (CostCategory, {"accounting_code": "TAKEN"}, "uq_cost_category_accounting_code"),
    (CostCategory, {"code": ""}, "ck_cost_category_code_length"),
    (CostCategory, {"code": "x" * 21}, "ck_cost_category_code_length"),
    (CostCategory, {"code": "  "}, "ck_cost_category_code_not_blank"),
    (CostCategory, {"label": "x" * 201}, "ck_cost_category_label_length"),
    (CostCategory, {"label": " "}, "ck_cost_category_label_not_blank"),
    (CostCategory, {"accounting_code": ""}, "ck_cost_category_accounting_code_length"),
    (CostCategory, {"accounting_code": " "}, "ck_cost_category_accounting_code_not_blank"),
    (CostCategory, {"cost_type_id": uuid4()}, "fk_cost_category_cost_type_id_cost_type"),
    (HourlyRate, {"year": 2025}, "uq_hourly_rate_cost_category_id"),
    (HourlyRate, {"year": 1999}, "ck_hourly_rate_year_bound"),
    (HourlyRate, {"year": 2101}, "ck_hourly_rate_year_bound"),
    (HourlyRate, {"amount": Decimal("0.00")}, "ck_hourly_rate_amount_minimum"),
    (
        HourlyRate,
        {"cost_category_id": uuid4()},
        "fk_hourly_rate_cost_category_id_cost_category",
    ),
    (OrgNode, {"code": "TAKEN"}, "uq_org_node_code"),
    (OrgNode, {"label": ""}, "ck_org_node_label_length"),
    (OrgNode, {"code": ""}, "ck_org_node_code_length"),
    (OrgNode, {"code": "x" * 21}, "ck_org_node_code_length"),
    (OrgNode, {"code": "  "}, "ck_org_node_code_not_blank"),
    (OrgNode, {"label": " "}, "ck_org_node_label_not_blank"),
    (OrgNode, {"parent_id": uuid4()}, "fk_org_node_parent_id_org_node"),
    (OrgNode, {"id": SELF, "parent_id": SELF}, "ck_org_node_not_its_own_parent"),
    (Calendar, {"label": "Pris"}, "uq_calendar_label"),
    (Calendar, {"label": ""}, "ck_calendar_label_length"),
    (Calendar, {"label": "x" * 201}, "ck_calendar_label_length"),
    (Calendar, {"label": " "}, "ck_calendar_label_not_blank"),
    (Calendar, {"monday": Decimal("24.5")}, "ck_calendar_hours_of_a_day"),
    (Calendar, {"sunday": Decimal(-1)}, "ck_calendar_hours_of_a_day"),
    (Calendar, {"is_default": True, "is_active": False}, "ck_calendar_default_active"),
    (Calendar, {"is_default": True}, "uq_calendar_default"),
    (ResourceRole, {"code": "TAKEN"}, "uq_resource_role_code"),
    (ResourceRole, {"code": ""}, "ck_resource_role_code_length"),
    (ResourceRole, {"code": "x" * 21}, "ck_resource_role_code_length"),
    (ResourceRole, {"code": "  "}, "ck_resource_role_code_not_blank"),
    (ResourceRole, {"label": "x" * 201}, "ck_resource_role_label_length"),
    (ResourceRole, {"label": " "}, "ck_resource_role_label_not_blank"),
    (ResourceRole, {"org_node_id": uuid4()}, "fk_resource_role_org_node_id_org_node"),
    (
        ResourceRole,
        {"cost_category_id": uuid4()},
        "fk_resource_role_cost_category_id_cost_category",
    ),
    (ResourceRole, {"calendar_id": uuid4()}, "fk_resource_role_calendar_id_calendar"),
    (
        ResourceRole,
        {"monthly_hours": Decimal(-1)},
        "ck_resource_role_monthly_hours_not_negative",
    ),
    (ResourceRole, {"headcount": Decimal("-0.5")}, "ck_resource_role_headcount_not_negative"),
    (ActualCostMapping, {"id": 2}, "ck_actual_cost_mapping_single_row"),
    (ActualCostMappingLabel, {"folded": "pris"}, "uq_actual_cost_mapping_label_folded"),
    (
        ActualCostMappingLabel,
        {"kind": "ignored", "column": None},
        "ck_actual_cost_mapping_label_kind_known",
    ),
    (ActualCostMappingLabel, {"column": "vendor"}, "ck_actual_cost_mapping_label_column_known"),
    (
        ActualCostMappingLabel,
        {"column": None},
        "ck_actual_cost_mapping_label_column_of_a_label_read",
    ),
    (
        ActualCostMappingLabel,
        {"kind": "kept"},
        "ck_actual_cost_mapping_label_column_of_a_label_read",
    ),
    (
        ActualCostMappingLabel,
        {"label": "", "folded": "x"},
        "ck_actual_cost_mapping_label_label_length",
    ),
    (
        ActualCostMappingLabel,
        {"label": "  ", "folded": "y"},
        "ck_actual_cost_mapping_label_label_not_blank",
    ),
]


@pytest.mark.requirement("WF-DAT-0090-A")
@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    [*REFUSALS, *AUDIT_REFUSALS],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_the_database_refuses_an_object_of_the_reference_that_breaks_a_rule(
    database: Database,
    owner: Engine,
    table: type[Base],
    overrides: dict[str, object],
    constraint: str,
) -> None:
    # A code, a label, a folded label already held by a deactivated object is held all the same.
    # The row of the settings shared is inserted by the bootstrap, as the owner: the service has no
    # right to insert it.
    with database.engine.begin() as connection:
        for parent, columns in PARENTS.items():
            connection.execute(reference_row(parent, **columns))
        if table in HELD:
            connection.execute(reference_row(table, **{**VALID[table], **HELD[table]}))
    statement = reference_row(table, **{**VALID[table], **overrides})
    if table is ReferenceSetting:
        assert owner_refusal(owner, statement) == constraint
    else:
        assert refusal(database, statement) == constraint


@pytest.mark.requirement("WF-DAT-0090-A")
def test_an_account_is_attached_to_a_node_that_exists_or_to_none(database: Database) -> None:
    with database.engine.begin() as connection:
        connection.execute(reference_row(OrgNode, id=NODE, code="DT"))
        connection.execute(write_account(org_node_id=NODE))
    statement = write_account(email="other@example.org", org_node_id=uuid4())
    assert refusal(database, statement) == "fk_user_account_org_node_id_org_node"


@pytest.mark.requirement("WF-DAT-0090-A")
def test_every_named_constraint_of_the_reference_has_its_refusal_tried() -> None:
    # A constraint added to a table of the reference with no case above would stay untried.
    tables = [table.__tablename__ for table in (*AUDITED, ActualCostMappingLabel)]
    # The unique index that keeps one default calendar counts, as the constraints do.
    named = {
        str(constraint.name)
        for name in tables
        for constraint in Base.metadata.tables[name].constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    } | {
        str(index.name)
        for name in tables
        for index in Base.metadata.tables[name].indexes
        if index.unique
    }
    tried = {constraint for _, _, constraint in (*REFUSALS, *AUDIT_REFUSALS)}
    assert named == tried


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
def test_the_audit_columns_of_the_two_modules_of_the_reference_do_not_drift() -> None:
    # Each module declares its own ``Audited`` (a module imports no table of another, WF-ARC-0010):
    # the two copies stay the same columns, whatever a lot changes in one of them.
    assert audit_columns(CostType) == audit_columns(OrgNode)
    own = {CostType: CostAudited, OrgNode: ResourceAudited}
    assert all(issubclass(table, audited) for table, audited in own.items())
