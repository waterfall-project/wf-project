# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The table of the installation: its settings, one row (§4.4.1).

It is not a function of the business, so it lives in the platform. The row is written by the
bootstrap of a new installation (US-0420), never by a migration: the language, the time zone and
the date are the installer's. Until the bootstrap writes it, the installation is not ready: what
reads its settings is refused as if its database did not answer, never served with values nobody
chose.

The time zone is fixed by the bootstrap and never changes afterwards (US-2200): a process reads it
once, the first time it needs the current day, from the database its entry point names
(``TIME_ZONE``).
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import BigInteger, CheckConstraint, Integer, SmallInteger, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from waterfall.platform.database import Base, Database, UtcDateTime
from waterfall.platform.errors import UnavailableError
from waterfall.platform.logs import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

LANGUAGES = ("fr", "en")
# The language that follows the browser, then the installation: the realm's own by default.
FOLLOWED = "default"
# The time zone an installation is delivered with, and that of one bootstrapped before it was kept.
DELIVERED_TIME_ZONE = "UTC"
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
        # A name of the IANA database, checked by the bootstrap: the database does not know them.
        CheckConstraint("time_zone <> ''", name="time_zone_not_empty"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    default_language: Mapped[str] = mapped_column(Text)
    time_zone: Mapped[str] = mapped_column(Text)
    avatar_max_bytes: Mapped[int] = mapped_column(Integer)
    external_backup_max_bytes: Mapped[int] = mapped_column(BigInteger)
    installed_at: Mapped[datetime] = mapped_column(UtcDateTime)


@dataclass(frozen=True, slots=True)
class Settings:
    """The settings of the installation that the API serves or applies."""

    default_language: str
    time_zone: str
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
    return Settings(
        row.default_language, row.time_zone, row.avatar_max_bytes, row.external_backup_max_bytes
    )


def set_avatar_max_bytes(session: Session, avatar_max_bytes: int) -> bool:
    """Bound the avatars of a bootstrapped installation; tell whether the bound changed.

    An operating parameter (§4.4.1): the bootstrap writes it from its settings, the witness its
    own (#3965). An installation not bootstrapped has no bound to change.
    """
    row = session.get(Installation, THE_ROW, with_for_update=True)
    if row is None or row.avatar_max_bytes == avatar_max_bytes:
        return False
    row.avatar_max_bytes = avatar_max_bytes
    return True


def stored_in(database: Database) -> Callable[[], str]:
    """Give the reading of the time zone the installation of ``database`` keeps, in a transaction.

    Refused while the installation is not bootstrapped (503), as its other settings are.
    """

    def stored() -> str:
        with database.transaction() as session:
            return read_settings(session).time_zone

    return stored


class ProcessTimeZone:
    """The time zone of the installation, as a process reads it: kept, and read again (US-2200).

    The bootstrap fixes it, but a restoration replaces the database without restarting the API,
    the worker or the witness: a backup of an installation in another time zone would leave them
    with the zone they had read. So a process keeps the zone for ``KEPT`` seconds, then reads it
    again (#4695): the restoration that gives another one is seen within that time, whichever
    process saw it or not. It reads it where its entry point says (``read_from``), the first time
    it is asked, and not before: the API starts before an installation is bootstrapped. A first
    reading refused is not kept, and the next asks again; a later one that is refused leaves the
    zone known, which is asked again the next time. A process whose entry point names no source
    cannot tell the day.
    """

    KEPT = 60.0

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        """Know no source yet; ``clock`` gives the seconds the zone is kept by."""
        self._clock = clock
        self._source: Callable[[], str] | None = None
        self._zone: ZoneInfo | None = None
        self._read_at = 0.0

    def read_from(self, source: Callable[[], str]) -> None:
        """Read the time zone from ``source`` from now on, forgetting the one read before."""
        self._source = source
        self._zone = None

    def zone(self) -> ZoneInfo:
        """Give the time zone of the installation, read the first time it is asked, then again."""
        if self._zone is None or self._clock() - self._read_at >= self.KEPT:
            self._zone = self._read()
            self._read_at = self._clock()
        return self._zone

    def _read(self) -> ZoneInfo:
        if self._source is None:
            message = "the process names no source of the time zone of the installation"
            raise RuntimeError(message)
        try:
            name = self._source()
        except UnavailableError:
            if self._zone is None:
                raise
            # A zone already known stays while the database does not answer, for another term.
            logger.warning("installation.time_zone_unread")
            return self._zone
        # A name unknown, or malformed — an absolute path, ``..`` —, which only a database
        # changed by hand holds: the bootstrap refuses both (#3258).
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError, ValueError:
            logger.warning("installation.time_zone_unknown")
            raise UnavailableError(COMPONENT_UNAVAILABLE, {"component": "database"}) from None


# The time zone of the installation of this process, which ``current_day`` reads.
TIME_ZONE = ProcessTimeZone()
