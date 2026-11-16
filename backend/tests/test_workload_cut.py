# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The day the plan of workload cuts a remaining to commit at: the end of the day of calculation.

#3615: the plan of workload cut the remaining at the start of the day of calculation, while the
curve of costs, the projection of spending and the fake back cut it at the end of that day, so
that the day of calculation was in the workload and not in the money. The tasks run on a calendar
of eight hours from Monday to Friday.

WF-DEV-0070-A, "half-way at the date of calculation": the first day is then over, as the remaining
is cut at the end of the day of calculation (#3615), so the months hold what remains to work after
it; "if they count as much" covers this case, and the tests below hold that cut.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from waterfall.core.estimate.interface import MONEY, Month, Placement, amount_parts
from waterfall.core.estimate.workloading import Load, spread_loads
from waterfall.core.planning.interface import WorkInstant, weekly_calendar

EIGHT, ZERO = Decimal(8), Decimal(0)
EIGHT_HOURS = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, ZERO, ZERO))
MARCH, APRIL = Month(2026, 3), Month(2026, 4)
# Monday 2 March to Wednesday 1 April 2026: 22 days of March, the first of April the last.
TO_APRIL = Placement(
    EIGHT_HOURS, WorkInstant(date(2026, 3, 2)), WorkInstant(date(2026, 4, 1), EIGHT)
)
TUESDAY_31_MARCH = date(2026, 3, 31)


def _spread(placement: Placement, as_of: date | None) -> dict[Month, Decimal]:
    role, task = uuid4(), uuid4()
    load = Load(role, task, Decimal(100), placement)
    return spread_loads([load], as_of)[role][task]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_remaining_to_commit_leaves_out_the_day_of_calculation() -> None:
    # « répartie sur la seule part de la durée de la tâche postérieure à la date de calcul » : on
    # Tuesday 31 March the day belongs to the past, what is to come is Wednesday 1 April alone,
    # in April. Cut at the start of the day, 8 hours of 16 stayed in March.
    assert _spread(TO_APRIL, TUESDAY_31_MARCH) == {APRIL: Decimal("100.00")}


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_workload_and_the_projection_of_spending_cut_a_remaining_at_the_same_day() -> None:
    # The same line as hours and as an amount, over the same task, on the same day: the same
    # months (#3615), the projection of spending cutting at the end of the day (WF-DEV-0100).
    hours = _spread(TO_APRIL, TUESDAY_31_MARCH)
    money = amount_parts(TO_APRIL, Decimal(100), as_of=TUESDAY_31_MARCH)
    assert list(hours) == list(money) == [APRIL]
    assert MONEY.of(hours[APRIL]) == money[APRIL]


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_over_by_the_end_of_the_day_of_calculation_falls_whole_on_its_month() -> None:
    # Placed from Monday 2 to Tuesday 31 March, the task ends on the day of calculation: the whole
    # falls on March, the month of the day, not on April, that of the next day.
    ended = Placement(EIGHT_HOURS, TO_APRIL.start, WorkInstant(TUESDAY_31_MARCH, EIGHT))
    assert _spread(ended, TUESDAY_31_MARCH) == {MARCH: Decimal("100.00")}


@pytest.mark.requirement("WF-DEV-0070-A")
def test_without_a_date_of_calculation_the_load_is_spread_over_the_whole_task() -> None:
    parts = _spread(TO_APRIL, None)
    assert list(parts) == [MARCH, APRIL]
    assert sum(parts.values()) == Decimal(100)
