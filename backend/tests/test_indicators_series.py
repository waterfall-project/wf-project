# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The series of the curves at the step of the month and the cash-out, without a database.

The tasks run on a calendar of eight hours from Monday to Friday. In 2026, February holds 20
working days, March and April 22 each: a task from 2 February to 30 April works 64 days, so 6 400
is spread 2 000, 2 200 and 2 200.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest

from waterfall.core.estimate.interface import MONEY, Month, Placement, rounded_parts
from waterfall.core.indicators.series import (
    Point,
    Spreader,
    SpreadLine,
    cash_out_by_month,
    cumulative,
    cumulative_from,
    cumulative_until,
    events_by_month,
    line_shares,
    month_before,
    month_end,
    month_ends,
    shifted,
    spread_lines,
)
from waterfall.core.indicators.series import shares as shares_module
from waterfall.core.indicators.series.shares import spread_delayed
from waterfall.core.planning.interface import WorkInstant, weekly_calendar

EIGHT = Decimal(8)
ZERO = Decimal(0)
WORKING_DAYS_A_WEEK = 5
WEEK = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, ZERO, ZERO))
FEBRUARY, MARCH, APRIL, MAY = (Month(2026, number) for number in range(2, 6))


def task(start: date, finish: date) -> Placement:
    """Return a task from the first hour of its first day to the end of the work of its last."""
    return Placement(WEEK, WorkInstant(start), WorkInstant(finish, EIGHT))


def line(amount: str, delay: int = 0) -> SpreadLine:
    """Return a line of the task from 2 February to 30 April."""
    return SpreadLine(Decimal(amount), task(date(2026, 2, 2), date(2026, 4, 30)), delay)


def amounts(points: list[Point]) -> list[Decimal]:
    """Return the amounts of the points."""
    return [point.amount for point in points]


def days(points: list[Point]) -> list[date]:
    """Return the days of the points."""
    return [point.day for point in points]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_month_ends_of_a_range_run_from_the_first_month_to_the_last() -> None:
    # « Les courbes se calculent et se présentent au pas du mois » (G-01), un point par fin de mois.
    assert month_ends(date(2027, 12, 15), date(2028, 3, 2)) == [
        date(2027, 12, 31),
        date(2028, 1, 31),
        date(2028, 2, 29),
        date(2028, 3, 31),
    ]
    assert month_end(date(2026, 2, 3)) == date(2026, 2, 28)
    assert month_before(Month(2026, 1)) == Month(2025, 12)


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_first_point_is_zero_at_the_end_of_the_month_that_precedes_the_first_amount() -> None:
    # « chaque point portant le cumul à la fin du mois, le premier à la fin du mois qui précède »
    points = cumulative(spread_lines([line("6400")]))
    assert days(points) == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]
    assert amounts(points) == [Decimal(0), Decimal(2000), Decimal(4200), Decimal(6400)]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_reference_budget_reaches_the_budget_at_the_month_of_the_last_task_and_stays() -> None:
    # « La courbe du budget de référence atteint le budget de référence à la date de fin de la
    # référence. » Two lines of a reference whose last task ends on 30 April.
    later = SpreadLine(Decimal(900), task(date(2026, 3, 2), date(2026, 3, 31)))
    shares = spread_lines([line("6400"), later])
    points = cumulative(shares, through=date(2026, 6, 15))
    assert points[3] == Point(date(2026, 4, 30), Decimal(7300))
    # Prolonged to the month of ``through``, the curve does not move after the end.
    assert amounts(points[3:]) == [Decimal(7300)] * 3
    assert days(points)[-1] == date(2026, 6, 30)


@pytest.mark.requirement("WF-IND-0110-A")
def test_the_planned_value_is_prolonged_to_the_end_of_the_reference_at_the_budget() -> None:
    # « La courbe de valeur planifiée atteint le budget de référence à la fin de la référence. »
    points = cumulative(spread_lines([line("6400")]), through=date(2026, 5, 31))
    assert points[-1] == Point(date(2026, 5, 31), Decimal(6400))


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_series_without_a_part_has_no_point() -> None:
    # « une maille sans ligne dans la référence ni dans la révision calculée […] a des séries sans
    # point »
    assert cumulative({}) == []
    assert cumulative_until([], date(2026, 3, 16)) == []


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_actual_cost_stops_at_the_date_of_calculation_with_a_point_of_its_own() -> None:
    # « Celle du coût réel s’arrête à la date de calcul »
    pieces = [
        (date(2026, 2, 10), Decimal(1000)),
        (date(2026, 3, 5), Decimal("500.50")),
        (date(2026, 3, 20), Decimal(300)),
        (date(2026, 4, 2), Decimal(999)),
    ]
    as_of = date(2026, 3, 16)
    points = cumulative_until(pieces, as_of)
    assert points == [
        Point(date(2026, 1, 31), Decimal(0)),
        Point(date(2026, 2, 28), Decimal(1000)),
        Point(date(2026, 3, 16), Decimal("1500.50")),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_scope_with_lines_and_no_document_draws_the_actual_cost_at_zero() -> None:
    # « le coût réel d'une maille qui a des lignes et aucune pièce est tracé nul »
    points = cumulative_until([], date(2026, 3, 16), from_month=FEBRUARY)
    assert points == [
        Point(date(2026, 1, 31), Decimal(0)),
        Point(date(2026, 2, 28), Decimal(0)),
        Point(date(2026, 3, 16), Decimal(0)),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_part_of_a_task_after_the_date_of_calculation_is_spread_on_the_hours_left() -> None:
    # « le reste à engager de chaque ligne étalé sur la part de la durée de sa tâche postérieure à
    # la date de calcul » : the 16th is spent (its documents count in the actual cost), so 11 days
    # are left in March, from the 17th, and the 22 of April.
    shares = line_shares(line("3300"), as_of=date(2026, 3, 16))
    assert shares == {MARCH: Decimal(1100), APRIL: Decimal(2200)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_task_that_ends_on_the_date_of_calculation_is_carried_whole_to_its_month_end() -> None:
    # The part to come is what follows the end of the day: a task that ends on 31 March, the date
    # of calculation, has nothing after it and stays in March, not in April, the month of the next
    # day (#3556).
    last = SpreadLine(Decimal(900), task(date(2026, 3, 2), date(2026, 3, 31)))
    assert line_shares(last, as_of=date(2026, 3, 31)) == {MARCH: Decimal(900)}
    assert line_shares(last, as_of=date(2026, 3, 30)) == {MARCH: Decimal(900)}
    assert line_shares(last, as_of=date(2026, 3, 29)) == {MARCH: Decimal(900)}
    assert shifted(last, as_of=date(2026, 3, 31)) == {MARCH: Decimal(900)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_task_whose_end_is_past_is_carried_whole_to_the_month_of_the_date() -> None:
    # « porté entier au point du mois de la date de calcul quand la fin de la tâche est dépassée »
    shares = line_shares(line("750"), as_of=date(2026, 5, 11))
    assert shares == {MAY: Decimal(750)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_projection_starts_at_the_actual_cost_and_reaches_it_plus_the_remaining() -> None:
    # « la projection part de ce point pour atteindre la projection du chef de projet » :
    # 1 500,50 spent, 3 300 left on a task in progress and 750 on one that is over.
    as_of = date(2026, 3, 16)
    over = SpreadLine(Decimal(750), task(date(2026, 2, 2), date(2026, 2, 27)))
    shares = spread_lines([line("3300"), over], as_of=as_of)
    points = cumulative_from(shares, as_of, Decimal("1500.50"))
    assert points == [
        Point(date(2026, 3, 16), Decimal("1500.50")),
        Point(date(2026, 3, 31), Decimal("3350.50")),
        Point(date(2026, 4, 30), Decimal("5550.50")),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_date_of_calculation_at_a_month_end_is_one_point_with_the_part_of_that_month() -> None:
    # The whole of an overdue task lands "au point du mois de la date de calcul": at the month-end
    # of the date, which here is the date itself.
    points = cumulative_from({MARCH: Decimal(100)}, date(2026, 3, 31), Decimal(50))
    assert points == [Point(date(2026, 3, 31), Decimal(150))]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_projection_without_remaining_is_the_actual_cost_at_the_date_alone() -> None:
    # Nothing is left to spread: the projection is its starting point, as the contract's examples
    # draw a scope whose lines have nothing left (``cost_curve_subproject_unbudgeted``).
    assert cumulative_from({}, date(2026, 3, 16), Decimal(40)) == [
        Point(date(2026, 3, 16), Decimal(40)),
    ]


@pytest.mark.requirement("WF-IND-0110-A")
def test_a_terminated_task_makes_a_step_at_the_month_of_its_termination() -> None:
    # « Une tâche terminée produit une marche dans la valeur acquise au point du mois de sa date de
    # terminaison. »
    budgeted = [(date(2026, 3, 12), Decimal(2500)), (date(2026, 2, 9), Decimal(1000))]
    as_of = date(2026, 4, 15)
    points = cumulative_until(budgeted, as_of)
    assert points == [
        Point(date(2026, 1, 31), Decimal(0)),
        Point(date(2026, 2, 28), Decimal(1000)),
        Point(date(2026, 3, 31), Decimal(3500)),
        Point(date(2026, 4, 15), Decimal(3500)),
    ]


@pytest.mark.requirement("WF-IND-0110-A")
def test_at_the_date_of_calculation_the_gap_of_the_two_curves_is_the_cost_variance() -> None:
    # « À la date de calcul, l’écart vertical entre la courbe de valeur acquise et celle du coût
    # réel égale la différence des deux grandeurs. »
    as_of = date(2026, 3, 16)
    earned = cumulative_until([(date(2026, 3, 2), Decimal("2800.25"))], as_of)
    actual = cumulative_until([(date(2026, 2, 9), Decimal("1500.10"))], as_of)
    assert earned[-1].day == actual[-1].day == as_of
    assert earned[-1].amount - actual[-1].amount == Decimal("1300.15")


def spent_by(day: date) -> Decimal:
    """Return what the line of 6 400 has spent by the end of a day: 100 a working day of 64."""
    worked = sum(
        1
        for offset in range((min(day, date(2026, 4, 30)) - date(2026, 2, 2)).days + 1)
        if (date(2026, 2, 2) + timedelta(days=offset)).weekday() < WORKING_DAYS_A_WEEK
    )
    return Decimal(100 * worked) if day >= date(2026, 2, 2) else Decimal(0)


@pytest.mark.requirement("WF-IND-0100-A")
@pytest.mark.parametrize("delay", [31, 45, 60])
def test_a_delayed_curve_is_the_other_translated_by_the_delay_in_days(delay: int) -> None:
    # « la courbe du budget de référence décalée est la courbe non décalée translatée de 60 jours »:
    # at each month-end, the value of the other at that day less the delay, not a month moved.
    delayed = cumulative(spread_lines([line("6400", delay)], delayed=True))
    assert delayed[0].amount == Decimal(0)
    for point in delayed:
        assert point.amount == spent_by(point.day - timedelta(days=delay))
    assert delayed[-1].amount == Decimal(6400)
    assert len({point.day for point in delayed}) == len(delayed)


@pytest.mark.requirement("WF-IND-0100-A")
def test_two_months_of_a_task_do_not_fall_in_one_by_a_delay_of_31_days() -> None:
    # March and April, which a month-end plus 31 days both carry to May, stay two parts.
    delayed = line_shares(line("6400", 31), delayed=True)
    assert len([part for part in delayed.values() if part]) >= len(
        line_shares(line("6400")).values()
    )
    assert sum(delayed.values()) == Decimal(6400)


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_delay_translates_the_part_after_the_date_of_calculation() -> None:
    as_of = date(2026, 3, 16)
    delayed = spread_lines([line("6400", 45)], as_of=as_of, delayed=True)
    # The 6 400 left are spread from 17 March, the day after the date, and shifted by 45 days: the
    # first part falls on 1 May.
    assert sum(delayed.values()) == Decimal(6400)
    assert min(delayed) == MAY
    past = SpreadLine(Decimal(6400), task(date(2026, 2, 2), date(2026, 3, 13)), 45)
    assert spread_lines([past], as_of=as_of, delayed=True) == {Month(2026, 4): Decimal(6400)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_no_delay_leaves_the_parts_where_they_are() -> None:
    assert line_shares(line("6400", 0), delayed=True) == line_shares(line("6400"))


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_delay_is_the_one_of_each_line() -> None:
    lines = [line("6400", 0), line("3200", 30)]
    delayed = spread_lines(lines, delayed=True)
    # The 30 days of the second move February to March (28 February + 30), March to April and
    # April to May; the first stays.
    assert delayed == {
        FEBRUARY: Decimal(2000),
        MARCH: Decimal(2200) + Decimal(1000),
        APRIL: Decimal(2200) + Decimal(1100),
        MAY: Decimal(1100),
    }


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_sum_of_the_forecast_cash_out_equals_the_remaining_to_commit() -> None:
    # « La somme des décaissements à venir égale le reste à engager » : amounts that do not divide
    # to the cent, three lines with three delays.
    as_of = date(2026, 3, 16)
    lines = [line("3333.33", 0), line("1000.01", 30), line("777.77", 61)]
    remaining = sum((item.amount for item in lines), Decimal(0))
    forecast = spread_lines(lines, as_of=as_of, delayed=True)
    rows = cash_out_by_month({}, forecast)
    assert sum((row.forecast for row in rows), Decimal(0)) == remaining
    assert all(row.forecast == row.forecast.quantize(Decimal("0.01")) for row in rows)


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_month_of_the_date_of_calculation_carries_the_past_and_the_forecast() -> None:
    # « le mois de la date de calcul portant les deux, nul sinon »
    as_of = date(2026, 3, 16)
    past = events_by_month(
        [(date(2026, 1, 20), Decimal(400)), (date(2026, 3, 5), Decimal(600))], until=as_of
    )
    forecast = spread_lines([line("3300")], as_of=as_of, delayed=True)
    rows = cash_out_by_month(past, forecast)
    assert [row.month for row in rows] == [Month(2026, 1), FEBRUARY, MARCH, APRIL]
    assert [(row.past, row.forecast) for row in rows] == [
        (Decimal(400), Decimal(0)),
        (Decimal(0), Decimal(0)),
        (Decimal(600), Decimal(1100)),
        (Decimal(0), Decimal(2200)),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_actual_cost_is_not_shifted_in_the_cash_out() -> None:
    # « le coût réel n'est pas décalé » : the past keeps the month of the document whatever the
    # delay of the forecast.
    as_of = date(2026, 3, 16)
    past = events_by_month([(date(2026, 3, 5), Decimal(600))], until=as_of)
    rows = cash_out_by_month(past, spread_lines([line("3400", 60)], as_of=as_of, delayed=True))
    assert rows[0].month == MARCH
    assert rows[0].past == Decimal(600)
    assert rows[0].forecast == Decimal(0)


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_cash_out_without_amount_has_no_month() -> None:
    assert cash_out_by_month({}, {}) == []


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_negative_part_lowers_the_cumulative() -> None:
    shares = {FEBRUARY: Decimal("100.01"), MARCH: Decimal("-30.01"), APRIL: Decimal(0)}
    assert amounts(cumulative(shares)) == [
        Decimal(0),
        Decimal("100.01"),
        Decimal("70.00"),
        Decimal("70.00"),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_date_of_calculation_before_the_first_amount_draws_zero_to_that_date() -> None:
    events = [(date(2026, 3, 5), Decimal(100))]
    assert cumulative_until(events, date(2026, 2, 10)) == []
    points = cumulative_until(events, date(2026, 2, 10), from_month=FEBRUARY)
    assert days(points) == [date(2026, 1, 31), date(2026, 2, 10)]
    assert set(amounts(points)) == {Decimal(0)}
    # A ``from_month`` after the date of calculation is brought back to the month of the date.
    later = cumulative_until(events, date(2026, 2, 10), from_month=Month(2026, 4))
    assert days(later) == [date(2026, 1, 31), date(2026, 2, 10)]
    assert set(amounts(later)) == {Decimal(0)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_piece_after_the_date_of_calculation_is_not_counted_whatever_the_caller_does() -> None:
    as_of = date(2026, 3, 16)
    events = [
        (date(2026, 3, 16), Decimal(10)),
        (date(2026, 3, 17), Decimal(50)),
        (date(2026, 4, 2), Decimal(7)),
    ]
    points = cumulative_until(events, as_of)
    assert points[-1] == Point(as_of, Decimal("10.00"))
    assert all(point.day <= as_of for point in points)


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_delayed_task_without_an_hour_of_work_is_spent_whole_at_its_end_shifted() -> None:
    weekend = SpreadLine(Decimal(500), task(date(2026, 2, 7), date(2026, 2, 8)), 40)
    assert shifted(weekend) == {MARCH: Decimal(500)}
    assert shifted(weekend, as_of=date(2026, 2, 7)) == {MARCH: Decimal(500)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_delayed_task_whose_end_is_past_is_spent_whole_at_the_date_shifted() -> None:
    past = SpreadLine(Decimal(800), task(date(2026, 2, 2), date(2026, 2, 13)), 20)
    assert shifted(past, as_of=date(2026, 3, 16)) == {APRIL: Decimal(800)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_delay_at_the_end_of_a_month_drops_the_null_part_and_adds_no_month() -> None:
    # The date of calculation is the 31 March, the task goes on to 30 April (22 working days, 100
    # each of 2 200). The share starts on 1 April: a delay of 30 days puts the end of April at
    # 30 March, before it, so April holds a null part, dropped, and May holds the whole; a delay
    # of one day puts 21 days in April (to the 29th) and the last one in May, and no month beyond;
    # without a delay the whole stays in April (#3574).
    as_of = date(2026, 3, 31)
    assert shifted(line("2200", 30), as_of=as_of) == {MAY: Decimal(2200)}
    assert shifted(line("2200", 1), as_of=as_of) == {APRIL: Decimal(2100), MAY: Decimal(100)}
    assert shifted(line("2200", 0), as_of=as_of) == {APRIL: Decimal(2200)}


def across(amount: str, finish: date, delay: int = 0) -> SpreadLine:
    """Return a line of a task from Friday 27 February to a day of March."""
    return SpreadLine(Decimal(amount), task(date(2026, 2, 27), finish), delay)


@pytest.mark.requirement("WF-IND-0100-A")
@pytest.mark.parametrize(("delay", "first", "second"), [(0, FEBRUARY, MARCH), (30, MARCH, APRIL)])
def test_the_curve_sums_the_parts_of_each_line_rounded_as_the_estimate_rounds_them(
    delay: int, first: Month, second: Month
) -> None:
    # Propre à l'US : « la courbe de coûts passe, comme la projection de dépenses et le plan de
    # charge, par les parts arrondies communes de core/estimate » (US-1690/L4, #3564). A line of 1
    # over three working days, one in February and two in March: 0.33 and 0.67, the difference of
    # two roundings of its cumulated, those of ``rounded_parts``; two such lines put 0.66 in the
    # first month, the sum of their parts, not 0.67, the rounding of their sum. With a delay of 30
    # days, the same parts a month later, the cumulated rounded after the shift.
    third = across("1.00", date(2026, 3, 3), delay)
    assert line_shares(third, delayed=True) == {first: Decimal("0.33"), second: Decimal("0.67")}
    if not delay:
        assert line_shares(third) == rounded_parts(third.placement, third.amount, MONEY)
    points = cumulative(spread_lines([third, third], delayed=True))
    assert amounts(points) == [Decimal(0), Decimal("0.66"), Decimal("2.00")]


@pytest.mark.requirement("WF-IND-0100-A")
@pytest.mark.parametrize(("delay", "month"), [(0, FEBRUARY), (30, MARCH)])
def test_a_half_cent_of_a_part_goes_away_from_nought_as_money_does(
    delay: int, month: Month
) -> None:
    # 0.01 over two working days, 27 February and 2 March: half a cent in the first month, which
    # rounds to a cent, a half away from nought (``MONEY``, ``docs/api/DECISIONS.md``, US-2040/L1),
    # not to nought as the half to the even would; the second month then holds nothing.
    cent = across("0.01", date(2026, 3, 2), delay)
    assert line_shares(cent, delayed=True) == {month: Decimal("0.01")}


MILESTONE = SpreadLine(Decimal("1000.01"), task(date(2026, 3, 18), date(2026, 3, 18)))
TWO_WAYS = [
    pytest.param(line("6400.07"), None, id="ordinary-task"),
    pytest.param(line("6400.07"), date(2026, 3, 16), id="as-of-in-the-task"),
    pytest.param(line("6400.07"), date(2026, 6, 1), id="as-of-after-the-end"),
    pytest.param(line("6400.07"), date(2026, 4, 30), id="as-of-on-the-end"),
    pytest.param(MILESTONE, None, id="milestone"),
    pytest.param(MILESTONE, date(2026, 3, 10), id="milestone-after-as-of"),
    pytest.param(MILESTONE, date(2026, 3, 18), id="milestone-on-as-of"),
    pytest.param(MILESTONE, date(2026, 5, 4), id="milestone-before-as-of"),
]


@pytest.mark.requirement("WF-IND-0100-A")
@pytest.mark.parametrize(("spread", "as_of"), TWO_WAYS)
def test_the_path_of_a_delayed_line_with_no_delay_gives_the_parts_of_the_estimate(
    spread: SpreadLine, as_of: date | None
) -> None:
    # « la courbe du budget de référence décalée est la courbe non décalée translatée de 60
    # jours » : a delay of nought leaves the curve where it is, so the two ways of spreading — the
    # parts of the estimate, and the cumulated read at each month-end less the delay — agree.
    assert spread.payment_delay_days == 0
    assert spread_delayed(spread, as_of=as_of) == line_shares(spread, as_of=as_of)


def test_a_spreader_spreads_each_line_once_for_every_sum_and_sums_as_each_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A detail of the realisation (#3902), which reprises no Vérif of its own: the curves of a
    # computation share a spreader, each line spread once for a date of calculation — with and
    # without the delays for a line that has none, in every scope —, the sums those of each alone.
    spread: list[tuple[SpreadLine, date | None, bool]] = []
    original = shares_module.line_shares

    def counting(
        each: SpreadLine, *, as_of: date | None = None, delayed: bool = False, **rest: Any
    ) -> dict[Month, Decimal]:
        spread.append((each, as_of, delayed))
        return original(each, as_of=as_of, delayed=delayed, **rest)

    plain, delayed, other = line("6400.07"), line("3300", 45), line("1000.01")
    as_of = date(2026, 3, 16)
    every = [plain, delayed, other]
    asked = [(delay, day) for delay in (False, True) for day in (None, as_of)]
    alone = {
        each: (
            spread_lines(every, as_of=each[1], delayed=each[0]),
            spread_lines([plain], as_of=each[1], delayed=each[0]),
        )
        for each in asked
    }
    monkeypatch.setattr(shares_module, "line_shares", counting)
    spreader = Spreader()
    for delay, day in asked:
        whole, scope = alone[delay, day]
        assert spread_lines(every, as_of=day, delayed=delay, spreader=spreader) == whole
        # A scope of fewer lines is drawn from the same parts.
        assert spread_lines([plain], as_of=day, delayed=delay, spreader=spreader) == scope
    # Each line once by date, the line with a delay delayed and not: none spread again.
    assert len([each for each in spread if each[0] is plain]) == 2
    assert len([each for each in spread if each[0] is other]) == 2
    assert len([each for each in spread if each[0] is delayed]) == 2 * 2
    assert spreader.shares(plain, as_of=as_of) is spreader.shares(plain, as_of=as_of, delayed=True)
    assert len(spread) == 2 + 2 + 2 * 2
