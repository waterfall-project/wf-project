# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parts of the amount of a line by month, as it is consumed or paid out, without a database.

US-2050/L1 (WF-DEV-0100): the amount of a line over the hours worked of its task, a part the
difference of two roundings to the cent of the cumulated amount, shifted by the payment delay of
the line on request, and cut at the date of calculation of a remaining to commit. The tasks run on
a calendar of eight hours from Monday to Friday; in 2026, February holds 20 working days, March and
April 22 each.
"""

from datetime import date
from decimal import Decimal

import pytest

from waterfall.core.estimate.interface import (
    MONEY,
    Month,
    Placement,
    amount_parts,
    rounded_parts,
)
from waterfall.core.planning.interface import WorkInstant, weekly_calendar

EIGHT = Decimal(8)
ZERO = Decimal(0)
EIGHT_HOURS = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, ZERO, ZERO))
FEBRUARY, MARCH, APRIL = Month(2026, 2), Month(2026, 3), Month(2026, 4)
# The first of February to the last of April 2026: 64 days, 512 hours, 160 in February.
SPRING = Placement(
    EIGHT_HOURS, WorkInstant(date(2026, 2, 2)), WorkInstant(date(2026, 4, 30), EIGHT)
)
# Monday 2 March to Tuesday 31 March 2026: the 22 working days of March.
MARCH_ONLY = Placement(
    EIGHT_HOURS, WorkInstant(date(2026, 3, 2)), WorkInstant(date(2026, 3, 31), EIGHT)
)
# Monday 2 November to Thursday 31 December 2026, 352 hours: 168 in November, 184 in December.
AUTUMN = Placement(
    EIGHT_HOURS, WorkInstant(date(2026, 11, 2)), WorkInstant(date(2026, 12, 31), EIGHT)
)


@pytest.mark.requirement("WF-DEV-0100-A")
def test_without_a_delay_nor_a_date_the_parts_are_those_of_the_line_rounded_to_the_cent() -> None:
    # The spreading over the hours worked, a half away from nought: the parts the plan of workload
    # and the planned value of EP-07 round the same cumulated into.
    assert amount_parts(SPRING, Decimal(100)) == rounded_parts(SPRING, Decimal(100), MONEY)
    assert amount_parts(AUTUMN, Decimal(1200)) == {
        Month(2026, 11): Decimal("572.73"),
        Month(2026, 12): Decimal("627.27"),
    }


@pytest.mark.requirement("WF-DEV-0100-A")
def test_with_a_delay_of_30_days_the_amount_is_shifted_by_as_much() -> None:
    # « Avec un délai de paiement de trente jours, en mode décaissement, sa dépense est décalée
    # d'autant. » The cumulated at the end of a month is what the task had spent 30 days before: on
    # 31 December, on 1 December, 176 hours of 352, half; the whole at the end of January.
    parts = amount_parts(AUTUMN, Decimal(1200), delay_days=30)
    assert parts == {Month(2026, 12): Decimal("600.00"), Month(2027, 1): Decimal("600.00")}
    assert sum(parts.values()) == Decimal(1200)


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_delay_of_60_days_carries_the_line_two_months_after_its_task_and_no_earlier() -> None:
    # 60 days after 2 November is 1 January, after 31 December 1 March: January, February, March.
    # The last working day of the task, 31 December, 8 hours of 352, is paid in March, 27.27;
    # nothing is paid before January.
    parts = amount_parts(AUTUMN, Decimal(1200), delay_days=60)
    assert list(parts) == [Month(2027, 1), Month(2027, 2), Month(2027, 3)]
    assert parts[Month(2027, 3)] == Decimal("27.27")
    assert sum(parts.values()) == Decimal(1200)


@pytest.mark.requirement("WF-DEV-0100-A")
def test_on_a_remaining_the_amount_is_spread_over_the_part_of_the_task_after_the_day() -> None:
    # « le reste de chaque ligne sur la part de sa tâche postérieure à la date de calcul »:
    # calculated on Monday 16 November, the day belongs to the past, 80 hours of November follow
    # (17 to 30), 184 of December: 80 / 264 and 184 / 264 of 1 200.
    parts = amount_parts(AUTUMN, Decimal(1200), as_of=date(2026, 11, 16))
    assert parts == {Month(2026, 11): Decimal("363.64"), Month(2026, 12): Decimal("836.36")}
    # Calculated on the last day of November, only December is left, and no month precedes it.
    assert amount_parts(AUTUMN, Decimal(1200), as_of=date(2026, 11, 30)) == {
        Month(2026, 12): Decimal("1200.00")
    }


@pytest.mark.requirement("WF-DEV-0100-A")
def test_on_a_remaining_a_task_that_is_over_carries_the_whole_in_the_month_of_the_day() -> None:
    # « porté au mois de la date de calcul lorsque la fin de la tâche est dépassée » ; the day of
    # the finish itself belongs to the past too: the task ended at its eighth hour that day.
    assert amount_parts(AUTUMN, Decimal(1200), as_of=date(2027, 3, 10)) == {
        Month(2027, 3): Decimal("1200.00")
    }
    assert amount_parts(AUTUMN, Decimal(1200), as_of=date(2026, 12, 31)) == {
        Month(2026, 12): Decimal("1200.00")
    }


@pytest.mark.requirement("WF-DEV-0100-A")
def test_on_a_remaining_with_a_delay_the_part_to_come_is_shifted_and_the_past_not_listed() -> None:
    # Calculated on 16 November, the 80 hours to come of November and the 184 of December, shifted
    # by 30 days: 264 hours, at 30 days before 31 December (1 December) 88 hours of the 264 have
    # run, a third, 400; the rest in January.
    parts = amount_parts(AUTUMN, Decimal(1200), as_of=date(2026, 11, 16), delay_days=30)
    assert parts == {Month(2026, 12): Decimal("400.00"), Month(2027, 1): Decimal("800.00")}
    # A task over is paid out a delay after the day of the calculation.
    assert amount_parts(AUTUMN, Decimal(1200), as_of=date(2027, 3, 10), delay_days=30) == {
        Month(2027, 4): Decimal("1200.00")
    }


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_task_of_no_hour_carries_the_whole_at_its_end_shifted_by_the_delay() -> None:
    # A milestone, or a task over a weekend: no hour to spread by, the whole falls where it ends.
    milestone = Placement(
        EIGHT_HOURS, WorkInstant(date(2026, 3, 31)), WorkInstant(date(2026, 3, 31))
    )
    assert amount_parts(milestone, Decimal(500)) == {MARCH: Decimal("500.00")}
    assert amount_parts(milestone, Decimal(500), delay_days=1) == {APRIL: Decimal("500.00")}
    weekend = Placement(EIGHT_HOURS, WorkInstant(date(2026, 3, 28)), WorkInstant(date(2026, 3, 29)))
    assert amount_parts(weekend, Decimal(500)) == {MARCH: Decimal("500.00")}


@pytest.mark.requirement("WF-DEV-0100-A")
def test_an_amount_of_nought_has_no_month() -> None:
    assert amount_parts(SPRING, Decimal(0)) == {}
    assert amount_parts(SPRING, Decimal(0), as_of=date(2027, 1, 1), delay_days=10) == {}


@pytest.mark.requirement("WF-DEV-0100-A")
def test_the_parts_sum_to_the_amount_rounded_whatever_the_delay_and_the_day() -> None:
    # Each part the difference of two roundings of a cumulated that never falls: none is negative,
    # their sum is the amount, which holds the equalities of the totals of the projection.
    amount = Decimal("1000.01")
    for as_of in (None, date(2026, 3, 9), date(2026, 5, 20)):
        for delay in (0, 17, 45):
            parts = amount_parts(SPRING, amount, as_of=as_of, delay_days=delay)
            assert sum(parts.values()) == amount, (as_of, delay)
            assert all(part > 0 for part in parts.values()), (as_of, delay)
            assert list(parts) == sorted(parts), (as_of, delay)
