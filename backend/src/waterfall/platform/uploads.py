# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The files deposited on the object storage, in transit (WF-DAT-0120): by parts, for now (#350).

A backup copied out of a platform is deposited by parts, each under the bound of a request the
front carries, which the object storage assembles: a deposit opens — the server says in how many
parts, of which size, the file is cut, and opens a deposit in parts on the storage —, receives its
parts in any order, each written to the storage before the answer, and is completed, the parts
assembled into one object. The row says what was opened, by whom, and until when; the parts
received are those the storage says it holds. A deposit lives twenty-four hours: expired, or
completed, it receives nothing more. The requester is an account, whose module declares the key.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Integer, Text, insert, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from waterfall.platform.database import Base, UtcDateTime

# The uses of a deposit, as the contract says them (``FileUploadPurpose``).
PURPOSES = ("import", "external_backup")
EXTERNAL_BACKUP = "external_backup"
# How long a deposit lives, opened or completed (``ChunkedUpload.expires_at``).
LIFETIME = timedelta(hours=24)
# The bounds of a part: the storage assembles no part smaller than 5 MiB, but the last; 10 MiB is
# the bound of the body of a request the front carries; a deposit has 10 000 parts at most.
SMALLEST_PART = 5 * 1024**2
LARGEST_PART = 10 * 1024**2
MOST_PARTS = 10_000


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class FileUpload(Base):
    """A file deposited on the object storage: what for, its name, its size, and its parts."""

    __tablename__ = "file_upload"
    __table_args__ = (
        CheckConstraint(_in("purpose", PURPOSES), name="purpose_known"),
        CheckConstraint("char_length(filename) BETWEEN 1 AND 255", name="filename_length"),
        CheckConstraint("size_bytes >= 1", name="size_bytes_positive"),
        CheckConstraint(
            f"part_size_bytes BETWEEN {SMALLEST_PART} AND {LARGEST_PART}", name="part_size_bound"
        ),
        CheckConstraint(f"part_count BETWEEN 1 AND {MOST_PARTS}", name="part_count_bound"),
        CheckConstraint("(deposit IS NULL) = (completed_at IS NOT NULL)", name="open_or_completed"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    purpose: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    part_size_bytes: Mapped[int] = mapped_column(Integer)
    part_count: Mapped[int] = mapped_column(Integer)
    # The key of the object on the storage, and the identifier of its deposit in parts while open.
    object_key: Mapped[str] = mapped_column(Text, unique=True)
    deposit: Mapped[str | None] = mapped_column(Text)
    # The date the manifest of a backup deposited says, read once it is completed: a deposit whose
    # date does not read is not completed.
    backup_taken_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    uploaded_by: Mapped[UUID] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


@dataclass(frozen=True, slots=True)
class Cut:
    """How a file is cut: the size of each part but the last, and how many parts."""

    part_size_bytes: int
    part_count: int

    def expected(self, number: int, size_bytes: int) -> int:
        """Give the size of a part: the size of a part, or for the last what is left."""
        if number < self.part_count:
            return self.part_size_bytes
        return size_bytes - self.part_size_bytes * (self.part_count - 1)


def cut(size_bytes: int) -> Cut | None:
    """Cut a file into the fewest parts the bounds let; ``None`` if 10 000 parts cannot hold it."""
    part = max(SMALLEST_PART, -(-size_bytes // MOST_PARTS))
    if part > LARGEST_PART:
        return None
    return Cut(part, -(-size_bytes // part))


@dataclass(frozen=True, slots=True)
class Opened:
    """A deposit to record: its use, its file, how it is cut, where it goes, and who opens it."""

    purpose: str
    filename: str
    size_bytes: int
    cut: Cut
    object_key: str
    deposit: str
    uploaded_by: UUID


def object_key_of(upload_id: UUID) -> str:
    """Give the key of the object of a deposit on the storage."""
    return f"uploads/{upload_id}"


def record_upload(session: Session, upload_id: UUID, opened: Opened, at: datetime) -> FileUpload:
    """Record a deposit opened at ``at``, living ``LIFETIME``."""
    session.execute(
        insert(FileUpload).values(
            id=upload_id,
            purpose=opened.purpose,
            filename=opened.filename,
            size_bytes=opened.size_bytes,
            part_size_bytes=opened.cut.part_size_bytes,
            part_count=opened.cut.part_count,
            object_key=opened.object_key,
            deposit=opened.deposit,
            uploaded_by=opened.uploaded_by,
            created_at=at,
            expires_at=at + LIFETIME,
        )
    )
    return session.get_one(FileUpload, upload_id)


def open_upload(session: Session, upload_id: UUID, at: datetime) -> FileUpload | None:
    """Give a deposit that may still receive parts at ``at``: open, not expired."""
    row = session.get(FileUpload, upload_id)
    if row is None or row.deposit is None or row.expires_at <= at:
        return None
    return row


def completed_upload(session: Session, upload_id: UUID, at: datetime) -> FileUpload | None:
    """Give a deposit completed and not expired at ``at``, the file it holds whole."""
    row = session.get(FileUpload, upload_id)
    if row is None or row.completed_at is None or row.expires_at <= at:
        return None
    return row


def complete_upload(
    session: Session, upload_id: UUID, at: datetime, backup_taken_at: datetime
) -> FileUpload | None:
    """Say a deposit completed at ``at``, with the date its backup says; ``None`` if not open.

    The row is locked, then read under the lock: of two completions at once, the second finds it
    completed.
    """
    row = session.scalars(
        select(FileUpload).where(FileUpload.id == upload_id).with_for_update()
    ).one_or_none()
    if row is None or row.deposit is None:
        return None
    session.execute(
        update(FileUpload)
        .where(FileUpload.id == upload_id)
        .values(deposit=None, completed_at=at, backup_taken_at=backup_taken_at)
    )
    return session.get_one(FileUpload, upload_id, populate_existing=True)
