# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The current day, taken in the time zone of the installation (US-2200, #2527).

``current_day``, the one function of the core the service takes the day from, on the time zone the
process reads once (``TIME_ZONE``): near midnight in universal time, where the two days part; and
the reading itself, from the row the bootstrap writes, refused before it and kept after.
"""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import Engine, insert, update

from waterfall.core.projects.interface import current_day
from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import UnavailableError
from waterfall.platform.installation import (
    THE_ROW,
    TIME_ZONE,
    Installation,
    ProcessTimeZone,
    stored_in,
)

# Half past eleven in the evening, universal time, on the 13th of November 2026.
LATE = datetime(2026, 11, 13, 23, 30, tzinfo=UTC)
THIRTEENTH, FOURTEENTH = date(2026, 11, 13), date(2026, 11, 14)


@pytest.mark.requirement("WF-PLA-0130-A")
@pytest.mark.parametrize(
    ("zone", "at", "day"),
    [
        ("UTC", LATE, THIRTEENTH),
        ("Europe/Paris", LATE, FOURTEENTH),
        ("Europe/Paris", datetime(2026, 11, 13, 22, 59, 59, tzinfo=UTC), THIRTEENTH),
        ("America/New_York", datetime(2026, 11, 14, 3, 30, tzinfo=UTC), THIRTEENTH),
    ],
)
def test_the_current_day_is_that_of_the_time_zone_of_the_installation(
    zone: str, at: datetime, day: date
) -> None:
    # « Le passage à l'état démarré ou terminé demande une date, proposée au jour courant » : the
    # day of the installation, not of universal time — at 23:30 UTC, Paris is on the next day.
    TIME_ZONE.read_from(lambda: zone)
    assert current_day(at) == day


def test_the_time_zone_is_read_once_by_a_process() -> None:
    # The bootstrap fixes it, and nothing changes it afterwards: the process does not ask again.
    asked: list[str] = []

    def source() -> str:
        asked.append("asked")
        return "Europe/Paris"

    TIME_ZONE.read_from(source)
    assert [current_day(LATE), current_day(LATE)] == [FOURTEENTH, FOURTEENTH]
    assert asked == ["asked"]
    # A source named again is read again: a test, or a process that changes its database.
    TIME_ZONE.read_from(lambda: "UTC")
    assert current_day(LATE) == THIRTEENTH


def test_a_process_that_names_no_source_cannot_tell_the_day() -> None:
    with pytest.raises(RuntimeError, match="no source of the time zone"):
        ProcessTimeZone().zone()


def test_the_time_zone_is_read_from_the_row_of_the_installation_once_it_is_bootstrapped(
    owner: Engine, database: Database
) -> None:
    # Read where the entry point of the process says: refused as the other settings are while the
    # installation is not bootstrapped (503), the refusal not kept; read and kept once it is.
    TIME_ZONE.read_from(stored_in(database))
    with pytest.raises(UnavailableError):
        current_day(LATE)
    with owner.begin() as connection:
        connection.execute(
            insert(Installation).values(
                id=THE_ROW,
                default_language="fr",
                time_zone="Europe/Paris",
                avatar_max_bytes=1024,
                external_backup_max_bytes=1024,
                installed_at=utc_now(),
            )
        )
    assert current_day(LATE) == FOURTEENTH
    with owner.begin() as connection:
        connection.execute(update(Installation).values(time_zone="UTC"))
    assert current_day(LATE) == FOURTEENTH


@pytest.mark.requirement("WF-EXP-0020-A")
@pytest.mark.parametrize("name", ["Mars/X", "/etc/localtime", "../Europe/Paris", "Europe/../Paris"])
def test_a_time_zone_the_row_names_wrongly_is_unavailable_not_a_server_error(name: str) -> None:
    # A name the tz database does not know, or one malformed — an absolute path, a ``..`` that
    # ``ZoneInfo`` refuses by a ``ValueError`` (#3258) —, written in the row, is refused like an
    # installation not yet bootstrapped (503), and not kept: the next reading asks again.
    reading = ProcessTimeZone()
    reading.read_from(lambda: name)
    with pytest.raises(UnavailableError):
        reading.zone()
    reading.read_from(lambda: "Europe/Paris")
    assert reading.zone().key == "Europe/Paris"


@pytest.mark.requirement("WF-QUA-0040-A")
def test_a_command_reading_the_zone_from_its_database_leaves_the_source_of_before() -> None:
    # A command that opens a database to read the zone from it and disposes it must not leave its
    # source bound to it: the next reading would open, on the disposed engine, a connection no one
    # closes (the ``ResourceWarning`` of the reference tests).
    reading = ProcessTimeZone()
    reading.read_from(lambda: "Europe/Paris")
    with reading.reading_from(lambda: "UTC"):
        assert reading.zone().key == "UTC"
    assert reading.zone().key == "Europe/Paris"
    message = "the command failed"
    with pytest.raises(RuntimeError), reading.reading_from(lambda: "UTC"):
        raise RuntimeError(message)
    assert reading.zone().key == "Europe/Paris"
