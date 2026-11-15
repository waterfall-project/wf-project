# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The series of the curves at the step of the month and the cash-out, without a database.

The tasks run on a calendar of eight hours from Monday to Friday. In 2026, February holds 20
working days, March and April 22 each: a task from 2 February to 30 April works 64 days, so 6 400
is spread 2 000, 2 200 and 2 200.
"""

from datetime import date
from decimal import Decimal

import pytest

from waterfall.core.estimate.interface import Month, Placement
from waterfall.core.indicators.series import (
    Point,
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
from waterfall.core.planning.interface import WorkInstant, weekly_calendar

EIGHT = Decimal(8)
ZERO = Decimal(0)
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
    assert cumulative_until({}, date(2026, 3, 16)) == []


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
    points = cumulative_until(events_by_month(pieces, until=as_of), as_of)
    assert points == [
        Point(date(2026, 1, 31), Decimal(0)),
        Point(date(2026, 2, 28), Decimal(1000)),
        Point(date(2026, 3, 16), Decimal("1500.50")),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_scope_with_lines_and_no_document_draws_the_actual_cost_at_zero() -> None:
    # « le coût réel d'une maille qui a des lignes et aucune pièce est tracé nul »
    points = cumulative_until({}, date(2026, 3, 16), from_month=FEBRUARY)
    assert points == [
        Point(date(2026, 1, 31), Decimal(0)),
        Point(date(2026, 2, 28), Decimal(0)),
        Point(date(2026, 3, 16), Decimal(0)),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_part_of_a_task_after_the_date_of_calculation_is_spread_on_the_hours_left() -> None:
    # « le reste à engager de chaque ligne étalé sur la part de la durée de sa tâche postérieure à
    # la date de calcul » : 12 days left in March from the 16th, and the 22 of April.
    shares = line_shares(line("3400"), as_of=date(2026, 3, 16))
    assert shares == {MARCH: Decimal(1200), APRIL: Decimal(2200)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_task_whose_end_is_past_is_carried_whole_to_the_month_of_the_date() -> None:
    # « porté entier au point du mois de la date de calcul quand la fin de la tâche est dépassée »
    shares = line_shares(line("750"), as_of=date(2026, 5, 11))
    assert shares == {MAY: Decimal(750)}


@pytest.mark.requirement("WF-IND-0100-A")
def test_the_projection_starts_at_the_actual_cost_and_reaches_it_plus_the_remaining() -> None:
    # « la projection part de ce point pour atteindre la projection du chef de projet » :
    # 1 500,50 spent, 3 400 left on a task in progress and 750 on one that is over.
    as_of = date(2026, 3, 16)
    over = SpreadLine(Decimal(750), task(date(2026, 2, 2), date(2026, 2, 27)))
    shares = spread_lines([line("3400"), over], as_of=as_of)
    points = cumulative_from(shares, as_of, Decimal("1500.50"))
    assert points == [
        Point(date(2026, 3, 16), Decimal("1500.50")),
        Point(date(2026, 3, 31), Decimal("3450.50")),
        Point(date(2026, 4, 30), Decimal("5650.50")),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_date_of_calculation_at_a_month_end_is_one_point_with_the_part_of_that_month() -> None:
    # The whole of an overdue task lands "au point du mois de la date de calcul": at the month-end
    # of the date, which here is the date itself.
    points = cumulative_from({MARCH: Decimal(100)}, date(2026, 3, 31), Decimal(50))
    assert points == [Point(date(2026, 3, 31), Decimal(150))]


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_projection_without_remaining_stays_at_the_actual_cost_to_month_end() -> None:
    assert cumulative_from({}, date(2026, 3, 16), Decimal(40)) == [
        Point(date(2026, 3, 16), Decimal(40)),
        Point(date(2026, 3, 31), Decimal(40)),
    ]


@pytest.mark.requirement("WF-IND-0110-A")
def test_a_terminated_task_makes_a_step_at_the_month_of_its_termination() -> None:
    # « Une tâche terminée produit une marche dans la valeur acquise au point du mois de sa date de
    # terminaison. »
    budgeted = [(date(2026, 3, 12), Decimal(2500)), (date(2026, 2, 9), Decimal(1000))]
    as_of = date(2026, 4, 15)
    points = cumulative_until(events_by_month(budgeted, until=as_of), as_of)
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
    earned = cumulative_until(events_by_month([(date(2026, 3, 2), Decimal("2800.25"))]), as_of)
    actual = cumulative_until(events_by_month([(date(2026, 2, 9), Decimal("1500.10"))]), as_of)
    assert earned[-1].day == actual[-1].day == as_of
    assert earned[-1].amount - actual[-1].amount == Decimal("1300.15")


@pytest.mark.requirement("WF-IND-0100-A")
def test_a_delay_of_sixty_days_translates_the_curve_by_two_months_here() -> None:
    # « la courbe du budget de référence décalée est la courbe non décalée translatée de 60 jours »
    plain = cumulative(spread_lines([line("6400")]))
    delayed = cumulative(spread_lines([line("6400", 60)], delayed=True))
    assert shifted({FEBRUARY: Decimal(2000)}, 60) == {APRIL: Decimal(2000)}
    assert days(delayed)[0] == date(2026, 3, 31)
    assert amounts(delayed) == amounts(plain)
    assert days(delayed) == [
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
        date(2026, 6, 30),
    ]


@pytest.mark.requirement("WF-IND-0100-A")
def test_no_delay_leaves_the_parts_where_they_are() -> None:
    shares = {FEBRUARY: Decimal(1), MARCH: Decimal(2)}
    assert shifted(shares, 0) == shares


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
    forecast = spread_lines([line("3400")], as_of=as_of, delayed=True)
    rows = cash_out_by_month(past, forecast)
    assert [row.month for row in rows] == [Month(2026, 1), FEBRUARY, MARCH, APRIL]
    assert [(row.past, row.forecast) for row in rows] == [
        (Decimal(400), Decimal(0)),
        (Decimal(0), Decimal(0)),
        (Decimal(600), Decimal(1200)),
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
