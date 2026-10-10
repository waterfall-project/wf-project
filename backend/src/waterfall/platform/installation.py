# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the installation: its settings, one row (§4.4.1).

It is not a function of the business, so it lives in the platform. The row is written by the
bootstrap of a new installation (US-0420), never by a migration: the language and the date are
the installer's.
"""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from waterfall.platform.database import Base, UtcDateTime

LANGUAGES = ("fr", "en")
AVATAR_MAX_BYTES = 8 * 1024 * 1024
EXTERNAL_BACKUP_MAX_BYTES = 2**53 - 1
THE_ROW = 1


class Installation(Base):
    """What was decided once, for the whole installation."""

    __tablename__ = "installation"
    __table_args__ = (
        CheckConstraint(f"id = {THE_ROW}", name="single_row"),
        CheckConstraint(
            f"default_language IN ({', '.join(repr(language) for language in LANGUAGES)})",
            name="default_language_known",
        ),
        CheckConstraint(
            f"avatar_max_bytes BETWEEN 1 AND {AVATAR_MAX_BYTES}", name="avatar_max_bytes_bound"
        ),
        CheckConstraint(
            f"external_backup_max_bytes BETWEEN 1 AND {EXTERNAL_BACKUP_MAX_BYTES}",
            name="external_backup_max_bytes_bound",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    default_language: Mapped[str] = mapped_column(Text)
    avatar_max_bytes: Mapped[int] = mapped_column(Integer)
    external_backup_max_bytes: Mapped[int] = mapped_column(BigInteger)
    installed_at: Mapped[datetime] = mapped_column(UtcDateTime)
