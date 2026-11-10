# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spreading of a load or an amount by year and by month, without a database (US-1520/L1).

The tasks run on a calendar of eight hours from Monday to Friday unless a test says otherwise. In
2026, February holds 20 working days and March and April 22 each.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from waterfall.core.estimate.spreading import (
    Month,
    Placement,
    spread_by_month,
    spread_by_year,
)
from waterfall.core.planning.interface import Calendar, WorkInstant, weekly_calendar

EIGHT = Decimal(8)
ZERO = Decimal(0)
EIGHT_HOURS = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, ZERO, ZERO))
THREE_DAYS = weekly_calendar((EIGHT, EIGHT, EIGHT, ZERO, ZERO, ZERO, ZERO))


def task(start: date, finish: date, week: Calendar = EIGHT_HOURS) -> Placement:
    """Return a task from the first hour of its first day to the end of the work of its last."""
    return Placement(week, WorkInstant(start), WorkInstant(finish, EIGHT))


@pytest.mark.requirement("WF-DEV-0040-A")
def test_a_line_across_two_years_is_in_two_parts_in_the_ratio_of_the_hours_worked_in_each() -> None:
    # « Une ligne portée par une tâche à cheval sur deux années est chiffrée en deux parts, dont
    # le rapport est celui des heures travaillées dans chacune. »
    # 22 December 2025 to 9 January 2026: 8 working days in 2025, 7 in 2026.
    parts = spread_by_year(task(date(2025, 12, 22), date(2026, 1, 9)), Decimal(1500))
    assert parts == {2025: Decimal(800), 2026: Decimal(700)}


@pytest.mark.requirement("WF-DEV-0040-A")
def test_two_lines_of_a_task_on_different_calendars_are_spread_on_their_own() -> None:
    # « Deux lignes d’une même tâche, portées par des rôles aux calendriers différents, sont
    # réparties entre les années selon leur propre calendrier. »
    dates = (date(2025, 12, 22), date(2026, 1, 9))
    five_days = spread_by_year(task(*dates), Decimal(1500))
    three_days = spread_by_year(task(*dates, THREE_DAYS), Decimal(1500))
    # Monday to Wednesday: 6 days in 2025 (22, 23, 24, 29, 30, 31), 3 in 2026 (5, 6, 7).
    assert three_days == {2025: Decimal(1000), 2026: Decimal(500)}
    assert five_days != three_days


@pytest.mark.requirement("WF-DEV-0040-A")
def test_the_parts_of_a_line_add_up_to_its_total_even_when_the_ratio_does_not_divide_it() -> None:
    # « La somme des parts égale le montant total de la ligne avant inflation. »
    total = Decimal("100.01")
    for spread in (
        spread_by_year(task(date(2024, 5, 6), date(2027, 8, 20)), total),
        spread_by_month(task(date(2026, 1, 1), date(2026, 12, 31)), total),
    ):
        assert sum(spread.values()) == total
        assert len(spread) > 2


@pytest.mark.requirement("WF-DEV-0040-A")
def test_a_task_within_one_year_puts_the_whole_amount_on_it() -> None:
    # The year of consumption of a line is the one of the task that carries it.
    assert spread_by_year(task(date(2026, 3, 2), date(2026, 3, 13)), Decimal(90)) == {
        2026: Decimal(90)
    }


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_over_two_civil_months_is_on_both_in_the_ratio_of_their_hours_worked() -> None:
    # « La charge d’une ligne portée par une tâche qui couvre exactement deux mois civils
    # apparaît sur ces deux mois, au prorata des heures travaillées de la tâche dans chacun. »
    # February 2026: 20 working days, March: 22.
    parts = spread_by_month(task(date(2026, 2, 1), date(2026, 3, 31)), Decimal(420))
    assert parts == {Month(2026, 2): Decimal(200), Month(2026, 3): Decimal(220)}
    assert list(parts) == sorted(parts)


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_load_after_the_date_of_calculation_is_spread_on_the_months_left_only() -> None:
    # The load is spread on the part of the task after the date of calculation only.
    # 5 January to 13 March 2026; on 16 February, 10 working days remain in each of the two months.
    parts = spread_by_month(
        task(date(2026, 1, 5), date(2026, 3, 13)), Decimal(100), as_of=date(2026, 2, 16)
    )
    assert parts == {Month(2026, 2): Decimal(50), Month(2026, 3): Decimal(50)}


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_not_started_before_the_date_of_calculation_shows_nothing_on_the_months_past() -> (
    None
):
    # « Une tâche non démarrée dont la date de début est antérieure à la date de calcul ne
    # présente aucune charge sur les mois écoulés ; »
    parts = spread_by_month(
        task(date(2026, 1, 12), date(2026, 3, 27)), Decimal(70), as_of=date(2026, 3, 2)
    )
    assert parts == {Month(2026, 3): Decimal(70)}


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_over_before_the_date_of_calculation_is_carried_on_the_month_of_that_date() -> None:
    # The load is carried on the month of the date of calculation once the task is over.
    parts = spread_by_month(
        task(date(2026, 1, 5), date(2026, 1, 30)), Decimal(64), as_of=date(2026, 3, 10)
    )
    assert parts == {Month(2026, 3): Decimal(64)}


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_task_starting_after_the_date_of_calculation_is_spread_whole() -> None:
    # « sa charge est la même avant et après son démarrage. »
    dated = task(date(2026, 2, 2), date(2026, 3, 31))
    assert spread_by_month(dated, Decimal(420), as_of=date(2026, 1, 1)) == spread_by_month(
        dated, Decimal(420)
    )


@pytest.mark.requirement("WF-DEV-0070-A")
def test_the_remaining_hours_of_a_weekend_left_are_carried_on_the_month_of_the_date() -> None:
    # The part after the date works no hour: the load stays where the date is.
    dated = Placement(EIGHT_HOURS, WorkInstant(date(2026, 3, 2)), WorkInstant(date(2026, 4, 5)))
    parts = spread_by_month(dated, Decimal(10), as_of=date(2026, 4, 4))
    assert parts == {Month(2026, 4): Decimal(10)}


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_milestone_is_spread_whole_on_the_month_of_its_date() -> None:
    # A line of a milestone is counted whole on the date of the milestone.
    day = WorkInstant(date(2026, 3, 31))
    assert spread_by_month(Placement(EIGHT_HOURS, day, day), Decimal(5)) == {
        Month(2026, 3): Decimal(5)
    }


@pytest.mark.requirement("WF-DEV-0040-A")
def test_the_hours_of_a_long_task_are_counted_by_weeks_whatever_its_length() -> None:
    # No loop on the days: 5 000 years of full weeks cost as little as one.
    monday = date(1001, 1, 1) - timedelta(days=date(1001, 1, 1).weekday())
    weeks = 260_000
    first = WorkInstant(monday)
    last = WorkInstant(monday + timedelta(days=7 * weeks - 1), EIGHT)
    assert EIGHT_HOURS.worked(last) - EIGHT_HOURS.worked(first) == 40 * weeks
    spread = spread_by_year(Placement(EIGHT_HOURS, first, last), Decimal(1000))
    assert sum(spread.values()) == 1000
    assert len(spread) == last.day.year - first.day.year + 1


@pytest.mark.requirement("WF-DEV-0040-A")
def test_an_instant_past_the_hours_of_its_day_counts_the_whole_day() -> None:
    saturday = WorkInstant(date(2026, 3, 7), Decimal(5))
    monday = WorkInstant(date(2026, 3, 2))
    assert EIGHT_HOURS.worked(saturday) - EIGHT_HOURS.worked(monday) == 40
    assert EIGHT_HOURS.weekly == 40


@pytest.mark.requirement("WF-DEV-0040-A")
def test_a_week_of_six_days_or_of_a_day_over_twenty_four_hours_is_refused() -> None:
    with pytest.raises(ValueError, match="7 days"):
        weekly_calendar((EIGHT,) * 6)
    with pytest.raises(ValueError, match="24 hours"):
        weekly_calendar((Decimal(25), ZERO, ZERO, ZERO, ZERO, ZERO, ZERO))


@pytest.mark.requirement("WF-DEV-0040-A")
def test_a_task_finishing_before_it_starts_is_refused() -> None:
    with pytest.raises(ValueError, match="before it starts"):
        Placement(EIGHT_HOURS, WorkInstant(date(2026, 3, 3)), WorkInstant(date(2026, 3, 2)))


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_task_working_no_hour_is_carried_on_the_month_of_its_end() -> None:
    # The choice, the same as ``planned_value``: a task over a weekend that works no hour counts
    # whole where it ends.
    dated = Placement(EIGHT_HOURS, WorkInstant(date(2026, 1, 31)), WorkInstant(date(2026, 2, 2)))
    assert spread_by_month(dated, Decimal(10)) == {Month(2026, 2): Decimal(10)}
