# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the installation: its settings, one row (§4.4.1).

It is not a function of the business, so it lives in the platform. The row is written by the
bootstrap of a new installation (US-0420), never by a migration: the language and the date are
the installer's. Until the bootstrap writes it, the installation is not ready: what reads its
settings is refused as if its database did not answer, never served with values nobody chose.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from waterfall.platform.database import Base, UtcDateTime
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import get_logger

LANGUAGES = ("fr", "en")
AVATAR_MAX_BYTES = 8 * 1024 * 1024
EXTERNAL_BACKUP_MAX_BYTES = 2**53 - 1
THE_ROW = 1
COMPONENT_UNAVAILABLE = "COMPONENT_UNAVAILABLE"

logger = get_logger(__name__)


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


@dataclass(frozen=True, slots=True)
class Settings:
    """The settings of the installation that the API serves or applies."""

    default_language: str
    avatar_max_bytes: int
    external_backup_max_bytes: int


def read_settings(session: Session) -> Settings:
    """Read the settings of the installation; refused while it is not bootstrapped (503).

    Its row is the bootstrap's (US-0420): an installation without it is not ready to serve.
    """
    row = session.get(Installation, THE_ROW)
    if row is None:
        logger.warning("installation.not_bootstrapped")
        raise UnavailableError(COMPONENT_UNAVAILABLE, {"component": "database"})
    return Settings(row.default_language, row.avatar_max_bytes, row.external_backup_max_bytes)
