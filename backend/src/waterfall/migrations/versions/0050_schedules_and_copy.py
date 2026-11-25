# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The schedules, the external copy of a backup, the tests of a restoration (EP-13, US-2910).

``backup_schedule`` and ``identity_sync_schedule`` hold one row each — written at their shipped
values by ``0051``, a migration of data of its own —: when the platform backs itself up, how many
backups it keeps and where it copies them (WF-ADM-0170, WF-EXP-0050), and when it reads the
accounts of the identity provider (WF-ADM-0070). A location keeps at least as many copies as the
platform keeps backups. ``backup`` receives the latest copy of each out of the platform, and
``restore_test`` one row per test of a restoration (WF-EXP-0060).

The role of the service reads each schedule and changes it, but inserts or deletes none; inserts
and reads a test, which nothing changes; and receives on ``backup`` the change — its mark, the
outcome of its copy — and the deletion of the rotation (WF-ADM-0170), which ``0010`` left to EP-13.
The kinds of the tasks that copy a backup and test a restoration are ``0048``'s.

The new columns of ``backup`` are null, and its new constraints admit every row it holds: the table
holds a few hundred rows, which the checks read at once.
"""

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.schema import SchemaItem

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BACKUP = "backup"
FREQUENCIES = "frequency IN ('daily', 'weekly')"
COPY_FAILURES = (
    "location_unreachable",
    "access_denied",
    "write_failed",
    "delete_failed",
    "storage_full",
    "timed_out",
)
RESTORE_TEST_FAILURE_LENGTH = 1000
LOCATION_FORM = "^[a-z0-9][a-z0-9_-]{0,62}$"
PATH_FORM = "^[A-Za-z0-9_][A-Za-z0-9_.-]*(/[A-Za-z0-9_][A-Za-z0-9_.-]*)*$"
GRANT = """
DO $$
BEGIN
    EXECUTE format(
        'GRANT SELECT, UPDATE ON backup_schedule, identity_sync_schedule TO %I',
        current_database() || '_service'
    );
    EXECUTE format('GRANT SELECT, INSERT ON restore_test TO %I', current_database() || '_service');
    EXECUTE format('GRANT UPDATE, DELETE ON backup TO %I', current_database() || '_service');
END
$$
"""
REVOKE = """
DO $$
BEGIN
    EXECUTE format('REVOKE UPDATE, DELETE ON backup FROM %I', current_database() || '_service');
END
$$
"""


def _listed(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _all_or_none(*columns: str) -> str:
    first, *others = columns
    return " AND ".join(f"({first} IS NULL) = ({other} IS NULL)" for other in others)


def _schedule() -> list[SchemaItem]:
    """Give what both schedules hold: one row, a frequency, a time to the minute, a day, audit."""
    return [
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=False),
        sa.Column("at_time", sa.Time(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="single_row"),
        sa.CheckConstraint(FREQUENCIES, name="frequency_known"),
        sa.CheckConstraint("date_part('second', at_time) = 0", name="at_time_in_minutes"),
        sa.CheckConstraint("weekday BETWEEN 1 AND 7", name="weekday_range"),
        sa.CheckConstraint(
            "(frequency = 'weekly') = (weekday IS NOT NULL)", name="weekday_of_a_weekly"
        ),
    ]


def _audited() -> list[SchemaItem]:
    """Give the counter of the writes and the columns of audit of a row that changes."""
    return [
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
    ]


def upgrade() -> None:
    """Create the two schedules and the tests of a restoration; give a backup its latest copy."""
    copy = (
        "external_copy_is_enabled",
        "external_copy_location",
        "external_copy_path",
        "external_copy_retained_count",
    )
    op.create_table(
        "backup_schedule",
        *_schedule(),
        sa.Column("retained_count", sa.SmallInteger(), nullable=False),
        sa.Column("external_copy_is_enabled", sa.Boolean(), nullable=True),
        sa.Column("external_copy_location", sa.Text(), nullable=True),
        sa.Column("external_copy_path", sa.Text(), nullable=True),
        sa.Column("external_copy_retained_count", sa.SmallInteger(), nullable=True),
        *_audited(),
        sa.CheckConstraint("retained_count BETWEEN 1 AND 365", name="retained_count_range"),
        sa.CheckConstraint(_all_or_none(*copy), name="external_copy_whole"),
        sa.CheckConstraint(
            f"external_copy_location ~ '{LOCATION_FORM}'", name="external_copy_location_form"
        ),
        sa.CheckConstraint(
            f"char_length(external_copy_path) <= 255 AND external_copy_path ~ '{PATH_FORM}'",
            name="external_copy_path_form",
        ),
        sa.CheckConstraint(
            "external_copy_retained_count BETWEEN retained_count AND 365",
            name="external_copy_retained_count_range",
        ),
    )
    op.create_table("identity_sync_schedule", *_schedule(), *_audited())
    op.create_table(
        "restore_test",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("backup_id", sa.Uuid(), nullable=False),
        sa.Column("backup_taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("projects", sa.Integer(), nullable=True),
        sa.Column("marked_revisions", sa.Integer(), nullable=True),
        sa.Column("cost_lines", sa.Integer(), nullable=True),
        sa.Column("identity_accounts", sa.Integer(), nullable=True),
        sa.Column("failure", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("finished_at >= started_at", name="finished_after_started"),
        sa.CheckConstraint(
            "projects >= 0 AND marked_revisions >= 0 AND cost_lines >= 0 "
            "AND identity_accounts >= 0",
            name="counts_not_negative",
        ),
        sa.CheckConstraint(
            f"char_length(failure) BETWEEN 1 AND {RESTORE_TEST_FAILURE_LENGTH}",
            name="failure_length",
        ),
        sa.CheckConstraint("succeeded = (failure IS NULL)", name="failure_of_a_failed_test"),
    )
    op.create_index(None, "restore_test", ["finished_at"])
    _add_last_copy()
    op.execute(GRANT)


def _add_last_copy() -> None:
    op.add_column(BACKUP, sa.Column("last_copy_at", sa.DateTime(timezone=True), nullable=True))
    for name in ("last_copy_location", "last_copy_path", "last_copy_failure"):
        op.add_column(BACKUP, sa.Column(name, sa.Text(), nullable=True))
    op.create_check_constraint(
        op.f("ck_backup_last_copy_whole"),
        BACKUP,
        _all_or_none("last_copy_at", "last_copy_location", "last_copy_path"),
    )
    op.create_check_constraint(
        op.f("ck_backup_last_copy_failure_known"),
        BACKUP,
        _listed("last_copy_failure", COPY_FAILURES),
    )
    op.create_check_constraint(
        op.f("ck_backup_last_copy_failure_of_a_copy"),
        BACKUP,
        "last_copy_failure IS NULL OR last_copy_at IS NOT NULL",
    )


def downgrade() -> None:
    """Drop the schedules, the tests and the latest copies; take back the rights on ``backup``.

    The schedules set, the tests run and the outcome of each copy are lost.
    """
    op.execute(REVOKE)
    for name in ("last_copy_at", "last_copy_location", "last_copy_path", "last_copy_failure"):
        op.drop_column(BACKUP, name)
    op.drop_table("restore_test")
    op.drop_table("identity_sync_schedule")
    op.drop_table("backup_schedule")
