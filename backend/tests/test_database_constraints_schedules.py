# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The database refuses what the schedules, the tests of a restoration and a copy forbid (EP-13).

The constraints of migration 0037, one refusal each: the two schedules, a single row each that
migration 0038 writes at its shipped values; the tests of a restoration; the latest copy of a
backup out of the platform. Every row is written around the services of the modules, by the owner
of the tables, and the schedules written back at their shipped values after each test
(``database``).
"""

from datetime import UTC, datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from waterfall.core.backups.tables import (
    SHIPPED_SCHEDULE,
    Backup,
    BackupSchedule,
    RestoreTest,
)
from waterfall.core.users.tables import IdentitySyncSchedule
from waterfall.migrations.runner import upgrade
from waterfall.platform.database import SHIPPED_ROW, Base, Database
from waterfall.platform.tasks import BackgroundTask

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from sqlalchemy.sql import Executable

pytestmark = pytest.mark.requirement("WF-DAT-0090-A")

AT = datetime(2026, 11, 20, 1, 0, tzinfo=UTC)
COPY = {
    "external_copy_is_enabled": True,
    "external_copy_location": "secours-lyon",
    "external_copy_path": "waterfall/sauvegardes",
    "external_copy_retained_count": 30,
}
LAST_COPY = {
    "last_copy_at": AT,
    "last_copy_location": "secours-lyon",
    "last_copy_path": "waterfall/sauvegardes",
}
TABLES: tuple[type[Base], ...] = (BackupSchedule, IdentitySyncSchedule, RestoreTest)


def constraint_of(error: IntegrityError) -> str:
    """Give the constraint a refusal names."""
    cause = error.orig
    assert isinstance(cause, psycopg.Error)
    return cause.diag.constraint_name or ""


def refusal(owner: Engine, statement: Executable) -> str:
    """Run, as the owner, a statement the database must refuse; give the constraint that refused."""
    with pytest.raises(IntegrityError) as raised, owner.begin() as connection:
        connection.execute(statement)
    return constraint_of(raised.value)


def restore_test(**overrides: object) -> Executable:
    """Give the insertion of a test of a restoration that succeeded, with the changes asked for."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "started_at": AT,
        "finished_at": AT + timedelta(minutes=20),
        "backup_id": uuid4(),
        "backup_taken_at": AT - timedelta(days=1),
        "succeeded": True,
        "projects": 300,
        "marked_revisions": 180,
        "cost_lines": 12000,
        "identity_accounts": 450,
        "failure": None,
    }
    return insert(RestoreTest).values(**{**columns, **overrides})


def backup(task_id: object, **overrides: object) -> Executable:
    """Give the insertion of a verified backup of a task, with the changes asked for."""
    columns: dict[str, object] = {
        "id": uuid4(),
        "taken_at": AT,
        "size_bytes": 2048,
        "verification": "passed",
        "origin": "scheduled",
        "is_retained": False,
        "object_key": f"backup-{task_id}.tar",
        "application_version": "0.1.0",
        "schema_revision": "0037",
        "task_id": task_id,
    }
    return insert(Backup).values(**{**columns, **overrides})


def backup_task(owner: Engine) -> object:
    """Write a backup's task that succeeded; give its identifier."""
    task_id = uuid4()
    with owner.begin() as connection:
        connection.execute(
            insert(BackgroundTask).values(
                id=task_id,
                kind="backup",
                status="succeeded",
                progress=100,
                payload={},
                correlation_id="req-1",
                attempts=1,
                submitted_at=AT,
                started_at=AT,
                finished_at=AT,
            )
        )
    return task_id


SCHEDULE_REFUSALS: list[tuple[type[Base], dict[str, Any], str]] = [
    (BackupSchedule, {"frequency": "monthly"}, "ck_backup_schedule_frequency_known"),
    (BackupSchedule, {"at_time": time(1, 0, 30)}, "ck_backup_schedule_at_time_in_minutes"),
    (BackupSchedule, {"frequency": "weekly", "weekday": 8}, "ck_backup_schedule_weekday_range"),
    (BackupSchedule, {"weekday": 3}, "ck_backup_schedule_weekday_of_a_weekly"),
    (BackupSchedule, {"frequency": "weekly"}, "ck_backup_schedule_weekday_of_a_weekly"),
    (BackupSchedule, {"retained_count": 0}, "ck_backup_schedule_retained_count_range"),
    (BackupSchedule, {"retained_count": 366}, "ck_backup_schedule_retained_count_range"),
    (
        BackupSchedule,
        COPY | {"external_copy_path": None},
        "ck_backup_schedule_external_copy_whole",
    ),
    (
        BackupSchedule,
        COPY | {"external_copy_location": "Secours Lyon"},
        "ck_backup_schedule_external_copy_location_form",
    ),
    (
        BackupSchedule,
        COPY | {"external_copy_path": "../sauvegardes"},
        "ck_backup_schedule_external_copy_path_form",
    ),
    (
        BackupSchedule,
        COPY | {"external_copy_path": "a" * 256},
        "ck_backup_schedule_external_copy_path_form",
    ),
    (
        BackupSchedule,
        COPY | {"external_copy_retained_count": 6},
        "ck_backup_schedule_external_copy_retained_count_range",
    ),
    (
        BackupSchedule,
        COPY | {"retained_count": 300, "external_copy_retained_count": 366},
        "ck_backup_schedule_external_copy_retained_count_range",
    ),
    (BackupSchedule, {"lock_version": -1}, "ck_backup_schedule_lock_version_not_negative"),
    (
        BackupSchedule,
        {"created_by": uuid4()},
        "fk_backup_schedule_created_by_user_account",
    ),
    (
        BackupSchedule,
        {"updated_by": uuid4()},
        "fk_backup_schedule_updated_by_user_account",
    ),
    (IdentitySyncSchedule, {"frequency": "hourly"}, "ck_identity_sync_schedule_frequency_known"),
    (
        IdentitySyncSchedule,
        {"at_time": time(1, 30, 1)},
        "ck_identity_sync_schedule_at_time_in_minutes",
    ),
    (
        IdentitySyncSchedule,
        {"frequency": "weekly", "weekday": 0},
        "ck_identity_sync_schedule_weekday_range",
    ),
    (IdentitySyncSchedule, {"weekday": 1}, "ck_identity_sync_schedule_weekday_of_a_weekly"),
    (
        IdentitySyncSchedule,
        {"lock_version": -1},
        "ck_identity_sync_schedule_lock_version_not_negative",
    ),
    (
        IdentitySyncSchedule,
        {"created_by": uuid4()},
        "fk_identity_sync_schedule_created_by_user_account",
    ),
    (
        IdentitySyncSchedule,
        {"updated_by": uuid4()},
        "fk_identity_sync_schedule_updated_by_user_account",
    ),
]
RESTORE_TEST_REFUSALS: list[tuple[dict[str, Any], str]] = [
    ({"finished_at": AT - timedelta(seconds=1)}, "ck_restore_test_finished_after_started"),
    ({"cost_lines": -1}, "ck_restore_test_counts_not_negative"),
    ({"succeeded": False, "failure": "lost"}, "ck_restore_test_failure_known"),
    ({"succeeded": False}, "ck_restore_test_failure_of_a_failed_test"),
    ({"failure": "counts_differ"}, "ck_restore_test_failure_of_a_failed_test"),
]
BACKUP_REFUSALS: list[tuple[dict[str, Any], str]] = [
    (LAST_COPY | {"last_copy_path": None}, "ck_backup_last_copy_whole"),
    ({"last_copy_location": "secours-lyon"}, "ck_backup_last_copy_whole"),
    (LAST_COPY | {"last_copy_failure": "lost"}, "ck_backup_last_copy_failure_known"),
    ({"last_copy_failure": "timed_out"}, "ck_backup_last_copy_failure_of_a_copy"),
]


@pytest.mark.parametrize(
    ("table", "overrides", "constraint"),
    SCHEDULE_REFUSALS,
    ids=[constraint for _, _, constraint in SCHEDULE_REFUSALS],
)
def test_the_database_refuses_a_schedule_that_breaks_a_rule(
    database: Database,
    owner: Engine,
    table: type[Base],
    overrides: dict[str, Any],
    constraint: str,
) -> None:
    del database
    assert refusal(owner, update(table).values(**overrides)) == constraint


@pytest.mark.parametrize("table", [BackupSchedule, IdentitySyncSchedule])
def test_a_schedule_holds_one_row_alone(
    database: Database, owner: Engine, table: type[Base]
) -> None:
    del database
    shipped: dict[str, object] = Base.metadata.tables[table.__tablename__].info[SHIPPED_ROW]
    second = {**shipped, "id": 2}
    assert refusal(owner, insert(table).values(**second)) == f"ck_{table.__tablename__}_single_row"


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    RESTORE_TEST_REFUSALS,
    ids=[constraint for _, constraint in RESTORE_TEST_REFUSALS],
)
def test_the_database_refuses_a_test_of_a_restoration_that_breaks_a_rule(
    database: Database, owner: Engine, overrides: dict[str, Any], constraint: str
) -> None:
    del database
    assert refusal(owner, restore_test(**overrides)) == constraint


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    BACKUP_REFUSALS,
    ids=[constraint for _, constraint in BACKUP_REFUSALS],
)
def test_the_database_refuses_a_latest_copy_of_a_backup_that_breaks_a_rule(
    database: Database, owner: Engine, overrides: dict[str, Any], constraint: str
) -> None:
    del database
    assert refusal(owner, backup(backup_task(owner), **overrides)) == constraint


def test_the_forms_the_constraints_admit_are_written(database: Database, owner: Engine) -> None:
    # A weekly schedule with a copy keeping as many as the platform, its folder at its longest; a
    # test that failed with its reason and without counts; a backup whose copy failed, and one
    # whose copy succeeded.
    del database
    weekly = {"frequency": "weekly", "weekday": 7, "retained_count": 30}
    longest = {"external_copy_path": "a" * 255}
    with owner.begin() as connection:
        connection.execute(update(BackupSchedule).values(COPY | weekly | longest))
        connection.execute(update(IdentitySyncSchedule).values(frequency="weekly", weekday=1))
        failed = {"succeeded": False, "failure": "platform_unstarted"}
        uncounted = {"projects": None, "marked_revisions": None, "cost_lines": None}
        connection.execute(restore_test(**failed, **uncounted, identity_accounts=None))
        connection.execute(
            backup(backup_task(owner), **LAST_COPY, last_copy_failure="storage_full")
        )
        connection.execute(backup(backup_task(owner), **LAST_COPY))
        copies = connection.execute(select(BackupSchedule.external_copy_retained_count)).scalar()
    assert copies == COPY["external_copy_retained_count"]


def test_the_migrations_write_each_schedule_at_its_shipped_values(empty_engine: Engine) -> None:
    # A database just migrated holds the rows the tests write back after each.
    upgrade(empty_engine)
    shipped = {name: value for name, value in SHIPPED_SCHEDULE.items() if not name.endswith("_at")}
    with empty_engine.connect() as connection:
        row = connection.execute(select(BackupSchedule)).mappings().one()
        reading = connection.execute(select(IdentitySyncSchedule)).mappings().one()
    assert {name: row[name] for name in shipped} == shipped
    assert row["external_copy_is_enabled"] is None
    assert (row["created_by"], row["updated_by"]) == (None, None)
    assert (reading["at_time"], reading["weekday"], reading["lock_version"]) == (
        time(1, 30),
        None,
        1,
    )


def test_every_named_constraint_of_the_schedules_and_of_the_copy_has_its_refusal_tried() -> None:
    named = {
        str(constraint.name)
        for table in TABLES
        for constraint in Base.metadata.tables[table.__tablename__].constraints
        if constraint.name is not None and not str(constraint.name).startswith("pk_")
    } | {
        str(constraint.name)
        for constraint in Base.metadata.tables[Backup.__tablename__].constraints
        if str(constraint.name).startswith("ck_backup_last_copy")
    }
    tried = {
        *(constraint for _, _, constraint in SCHEDULE_REFUSALS),
        *(constraint for _, constraint in RESTORE_TEST_REFUSALS),
        *(constraint for _, constraint in BACKUP_REFUSALS),
        "ck_backup_schedule_single_row",
        "ck_identity_sync_schedule_single_row",
    }
    assert named == tried
