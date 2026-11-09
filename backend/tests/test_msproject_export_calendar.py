# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The week of a calendar written as periods of the clock, and an instant of work read on it.

Without a database: the day off, the day of twenty-four hours, the hours that are not whole, and
the opening that moves earlier so that a day does not pass midnight (US-1430/L4, WF-INTF-0050-A).
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from waterfall.core.planning.exporting import date_on_clock, hour_of_clock, period_of
from waterfall.core.planning.scheduling import WorkInstant


def at(text: str) -> datetime:
    """Give an instant of the wall clock, as MSPDI writes it."""
    return datetime.fromisoformat(text)


HOUR = timedelta(hours=1)
TUESDAY = date(2026, 11, 3)
SUNDAY = date(2026, 11, 8)
EIGHT = (Decimal(8),) * 5 + (Decimal(0),) * 2


@pytest.mark.requirement("WF-INTF-0050-A")
def test_a_day_off_has_no_period_and_a_day_of_eight_hours_opens_at_eight() -> None:
    assert period_of(Decimal(0)) is None
    assert period_of(Decimal(8)) == (8 * HOUR, 16 * HOUR)


@pytest.mark.requirement("WF-INTF-0050-A")
def test_hours_that_are_not_whole_give_a_period_to_the_minute() -> None:
    period = period_of(Decimal("10.5"))
    assert period == (8 * HOUR, timedelta(hours=18, minutes=30))
    assert period is not None
    assert hour_of_clock(period[1]) == time(18, 30)
    assert period_of(Decimal("7.75")) == (8 * HOUR, timedelta(hours=15, minutes=45))


@pytest.mark.requirement("WF-INTF-0050-A")
def test_a_day_of_twenty_four_hours_is_written_from_midnight_to_midnight() -> None:
    period = period_of(Decimal(24))
    assert period == (timedelta(0), 24 * HOUR)
    assert period is not None
    assert (hour_of_clock(period[0]), hour_of_clock(period[1])) == (time(0), time(0))
    # More than a day is a day.
    assert period_of(Decimal(30)) == period


@pytest.mark.requirement("WF-INTF-0050-A")
def test_the_opening_moves_earlier_for_a_day_that_would_pass_midnight() -> None:
    assert period_of(Decimal(20)) == (4 * HOUR, 24 * HOUR)
    assert period_of(Decimal(16)) == (8 * HOUR, 24 * HOUR)


@pytest.mark.requirement("WF-INTF-0050-A")
def test_an_instant_of_work_is_a_date_of_the_clock_after_the_opening_of_its_day() -> None:
    week = tuple(period_of(hours) for hours in EIGHT)
    assert date_on_clock(WorkInstant(TUESDAY, Decimal(3)), week) == at("2026-11-03T11:00:00")
    assert date_on_clock(WorkInstant(TUESDAY, Decimal("0.5")), week) == at("2026-11-03T08:30:00")
    # Past the end of the day, the end of the day.
    assert date_on_clock(WorkInstant(TUESDAY, Decimal(9)), week) == at("2026-11-03T16:00:00")
    # A day off: the opening hour.
    assert date_on_clock(WorkInstant(SUNDAY), week) == at("2026-11-08T08:00:00")


@pytest.mark.requirement("WF-INTF-0050-A")
def test_the_end_of_a_day_of_twenty_four_hours_is_the_midnight_that_follows() -> None:
    week = tuple(period_of(Decimal(24)) for _ in range(7))
    assert date_on_clock(WorkInstant(TUESDAY, Decimal(24)), week) == at("2026-11-04T00:00:00")
    assert date_on_clock(WorkInstant(TUESDAY, Decimal(6)), week) == at("2026-11-03T06:00:00")


@pytest.mark.requirement("WF-INTF-0050-A")
def test_the_opening_that_moved_earlier_is_the_origin_of_an_instant_of_that_day() -> None:
    week = tuple(period_of(Decimal(20)) for _ in range(7))
    assert date_on_clock(WorkInstant(TUESDAY, Decimal(2)), week) == at("2026-11-03T06:00:00")
