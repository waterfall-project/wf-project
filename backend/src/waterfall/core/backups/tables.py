# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the backups, private to the module (§4.4.1, regime "platform").

A row is a backup taken and stored: its archive lives in the bucket of the backups under its key,
and the row says what the verification of that archive found. No row is deleted in EP-03: the
rotation of the backups is EP-13's.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import Base, UtcDateTime
from waterfall.platform.tasks import BackgroundTask

# The outcomes of a verification and the origins of a backup, as the contract says them (`Backup`).
VERIFICATIONS = ("pending", "passed", "failed")
ORIGINS = ("manual", "scheduled")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class Backup(Base):
    """A backup of the two databases: when, how large, verified or not, and where it is kept."""

    __tablename__ = "backup"
    __table_args__ = (
        CheckConstraint(_in("verification", VERIFICATIONS), name="verification_known"),
        CheckConstraint(_in("origin", ORIGINS), name="origin_known"),
        CheckConstraint("size_bytes >= 0", name="size_bytes_not_negative"),
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
