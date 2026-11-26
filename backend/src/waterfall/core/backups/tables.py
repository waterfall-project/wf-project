# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tables of the backups, private to the module (§4.4.1, regime "platform").

A row of ``backup`` is a backup taken and stored: its archive lives in the bucket of the backups
under its key, and the row says what the verification of that archive found, and where and how its
latest copy out of the platform went (EP-13). The schedule of the backups is one row, written by
the migrations at its shipped values and then changed by an administrator (WF-ADM-0170); a
restoration keeps it, as it keeps the list it governs (#1743). A test of a restoration is one row
per test, its outcome as the ephemeral platform gave it back (WF-EXP-0060).
"""

from datetime import datetime, time
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import SHIPPED_ROW, Base, UtcDateTime
from waterfall.platform.tasks import BackgroundTask

# The outcomes of a verification and the origins of a backup, as the contract says them (`Backup`).
VERIFICATIONS = ("pending", "passed", "failed")
ORIGINS = ("manual", "scheduled")
# Why an external location refused a copy, as the contract says it (`ExternalBackupFailure`).
COPY_FAILURES = (
    "location_unreachable",
    "access_denied",
    "write_failed",
    "delete_failed",
    "storage_full",
    "timed_out",
)
# The frequencies of a schedule (`BackupSchedule.frequency`), and the key of its single row.
FREQUENCIES = ("daily", "weekly")
SINGLE_ROW = 1
# The bounds of a retention, on the platform and on a location (WF-ADM-0170).
RETENTIONS = (1, 365)
# The forms of a location's name and of a folder in it (`ExternalBackupLocationName`,
# `ExternalBackupPath`), and the longest folder.
LOCATION_FORM = "^[a-z0-9][a-z0-9_-]{0,62}$"
PATH_FORM = "^[A-Za-z0-9_][A-Za-z0-9_.-]*(/[A-Za-z0-9_][A-Za-z0-9_.-]*)*$"
PATH_LENGTH = 255
# The reason of a failed test of a restoration is a text, bounded like the other texts.
RESTORE_TEST_FAILURE_LENGTH = 1000


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _all_or_none(*columns: str) -> str:
    first, *others = columns
    return " AND ".join(f"({first} IS NULL) = ({other} IS NULL)" for other in others)


class Backup(Base):
    """A backup of the two databases: when, how large, verified or not, and where it is kept."""

    __tablename__ = "backup"
    __table_args__ = (
        CheckConstraint(_in("verification", VERIFICATIONS), name="verification_known"),
        CheckConstraint(_in("origin", ORIGINS), name="origin_known"),
        CheckConstraint("size_bytes >= 0", name="size_bytes_not_negative"),
        CheckConstraint(
            _all_or_none("last_copy_at", "last_copy_location", "last_copy_path"),
            name="last_copy_whole",
        ),
        CheckConstraint(_in("last_copy_failure", COPY_FAILURES), name="last_copy_failure_known"),
        CheckConstraint(
            "last_copy_failure IS NULL OR last_copy_at IS NOT NULL",
            name="last_copy_failure_of_a_copy",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    # The instant of the state it copies; the list reads the latest first.
    taken_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    verification: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)
    is_retained: Mapped[bool]
    # The key of its archive in the bucket of the backups.
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    # What produced it: the version of the application and the revision of the schema.
    application_version: Mapped[str] = mapped_column(Text)
    schema_revision: Mapped[str] = mapped_column(Text)
    # The task that took it: one backup per task, however many attempts it took.
    task_id: Mapped[UUID] = mapped_column(
        ForeignKey(BackgroundTask.id, ondelete="RESTRICT"), unique=True
    )
    # Its latest copy out of the platform (EP-13): when, to which location and folder, and why the
    # location refused it — null when the copy succeeded. All null while none was made.
    last_copy_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    last_copy_location: Mapped[str | None] = mapped_column(Text)
    last_copy_path: Mapped[str | None] = mapped_column(Text)
    last_copy_failure: Mapped[str | None] = mapped_column(Text)


# The schedule as the platform ships it: daily at 01:00 UTC, seven kept, no external copy
# (WF-ADM-0170, WF-EXP-0050), its counter at 1, as a created object's (`LockVersion`), and by the
# platform. Migration 0051 writes it.
SHIPPED_SCHEDULE: dict[str, object] = {
    "id": SINGLE_ROW,
    "is_enabled": True,
    "frequency": "daily",
    "at_time": time(1, 0),
    "weekday": None,
    "retained_count": 7,
    "lock_version": 1,
    "created_at": func.now(),
    "updated_at": func.now(),
    "timing_changed_at": func.now(),
}


class BackupSchedule(Base):
    """When the platform backs itself up, how many backups it keeps, and where it copies them.

    The external copy is all its columns or none of them: none, no copy is set. Its retention is
    at least the platform's (WF-EXP-0050).
    """

    __tablename__ = "backup_schedule"
    __table_args__ = (
        CheckConstraint(f"id = {SINGLE_ROW}", name="single_row"),
        CheckConstraint(_in("frequency", FREQUENCIES), name="frequency_known"),
        CheckConstraint("date_part('second', at_time) = 0", name="at_time_in_minutes"),
        CheckConstraint("weekday BETWEEN 1 AND 7", name="weekday_range"),
        CheckConstraint(
            "(frequency = 'weekly') = (weekday IS NOT NULL)", name="weekday_of_a_weekly"
        ),
        CheckConstraint(
            f"retained_count BETWEEN {RETENTIONS[0]} AND {RETENTIONS[1]}",
            name="retained_count_range",
        ),
        CheckConstraint(
            _all_or_none(
                "external_copy_is_enabled",
                "external_copy_location",
                "external_copy_path",
                "external_copy_retained_count",
            ),
            name="external_copy_whole",
        ),
        CheckConstraint(
            f"external_copy_location ~ '{LOCATION_FORM}'", name="external_copy_location_form"
        ),
        CheckConstraint(
            f"char_length(external_copy_path) <= {PATH_LENGTH} "
            f"AND external_copy_path ~ '{PATH_FORM}'",
            name="external_copy_path_form",
        ),
        CheckConstraint(
            f"external_copy_retained_count BETWEEN retained_count AND {RETENTIONS[1]}",
            name="external_copy_retained_count_range",
        ),
        CheckConstraint("lock_version >= 0", name="lock_version_not_negative"),
        {"info": {SHIPPED_ROW: SHIPPED_SCHEDULE}},
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    is_enabled: Mapped[bool]
    frequency: Mapped[str] = mapped_column(Text)
    # In universal time, to the minute.
    at_time: Mapped[time] = mapped_column(Time)
    # The day of a weekly backup, 1 Monday to 7 Sunday (ISO 8601); null for a daily one.
    weekday: Mapped[int | None] = mapped_column(SmallInteger)
    retained_count: Mapped[int] = mapped_column(SmallInteger)
    external_copy_is_enabled: Mapped[bool | None]
    external_copy_location: Mapped[str | None] = mapped_column(Text)
    external_copy_path: Mapped[str | None] = mapped_column(Text)
    external_copy_retained_count: Mapped[int | None] = mapped_column(SmallInteger)
    lock_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT")
    )
    # When the timing (enabled, frequency, time, weekday) last changed, which a writing of the
    # retention or of the copy alone leaves (``write_backup_schedule``): the base of what is owed.
    timing_changed_at: Mapped[datetime] = mapped_column(UtcDateTime)


class RestoreTest(Base):
    """A test of a restoration, as the ephemeral platform that ran it gave it back (WF-EXP-0060).

    The backup it restored is named by its identifier and its date, without a key: the rotation
    deletes a backup the test outlives, and a restoration, which restores the tests, writes back the
    backups it kept. The counts are those the test found — projects, marked revisions, cost lines,
    accounts of the identity provider —, null where it did not get to count.
    """

    __tablename__ = "restore_test"
    __table_args__ = (
        CheckConstraint("finished_at >= started_at", name="finished_after_started"),
        CheckConstraint(
            "projects >= 0 AND marked_revisions >= 0 AND cost_lines >= 0 "
            "AND identity_accounts >= 0",
            name="counts_not_negative",
        ),
        CheckConstraint(
            f"char_length(failure) BETWEEN 1 AND {RESTORE_TEST_FAILURE_LENGTH}",
            name="failure_length",
        ),
        CheckConstraint("succeeded = (failure IS NULL)", name="failure_of_a_failed_test"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    # The latest is read first.
    finished_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    backup_id: Mapped[UUID]
    backup_taken_at: Mapped[datetime] = mapped_column(UtcDateTime)
    succeeded: Mapped[bool]
    projects: Mapped[int | None] = mapped_column(Integer)
    marked_revisions: Mapped[int | None] = mapped_column(Integer)
    cost_lines: Mapped[int | None] = mapped_column(Integer)
    identity_accounts: Mapped[int | None] = mapped_column(Integer)
    failure: Mapped[str | None] = mapped_column(Text)
