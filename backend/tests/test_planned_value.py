# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned value on given lines and dates, without a database (US-1520/L1).

The lines are those of the reference, given; their tasks run on a calendar of eight hours from
Monday to Friday. In 2026, March and April hold 22 working days each.
"""

from datetime import date
from decimal import Decimal

import pytest

from waterfall.core.estimate.spreading import Placement, PlannedLine, WorkWeek, planned_value
from waterfall.core.planning.interface import WorkInstant

EIGHT = Decimal(8)
ZERO = Decimal(0)
EIGHT_HOURS = WorkWeek((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, ZERO, ZERO))


def line(amount: int, start: date, finish: date) -> PlannedLine:
    """Return a line of a task from the first hour of its first day to the end of its last."""
    return PlannedLine(
        Decimal(amount), Placement(EIGHT_HOURS, WorkInstant(start), WorkInstant(finish, EIGHT))
    )


TWO_MONTHS = line(1000, date(2026, 3, 1), date(2026, 4, 30))


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_task_of_two_equal_months_counts_for_half_at_the_end_of_the_first() -> None:
    # « Une ligne portée par une tâche de deux mois comptant autant d’heures travaillées
    # contribue pour moitié à la fin du premier mois. »
    assert planned_value([TWO_MONTHS], date(2026, 3, 31)) == Decimal(500)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_grows_with_the_hours_worked_and_stops_at_the_amount() -> None:
    # The amount is spread over the task in proportion to the hours worked (body).
    week_one = date(2026, 3, 6)
    values = [
        planned_value([TWO_MONTHS], at) for at in (date(2026, 2, 28), week_one, date(2026, 4, 30))
    ]
    assert values == [Decimal(0), Decimal("113.64"), Decimal(1000)]
    assert planned_value([TWO_MONTHS], date(2030, 1, 1)) == Decimal(1000)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_line_of_a_milestone_counts_whole_on_its_date_and_not_before() -> None:
    # A line of a milestone is counted whole on the date of the milestone (body of the requirement).
    milestone = WorkInstant(date(2026, 3, 20))
    lines = [PlannedLine(Decimal(300), Placement(EIGHT_HOURS, milestone, milestone))]
    assert planned_value(lines, date(2026, 3, 19)) == Decimal(0)
    assert planned_value(lines, date(2026, 3, 20)) == Decimal(300)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_lines_add_up_and_the_sum_is_rounded_once_to_the_cent() -> None:
    # The planned value totals the budget exactly at the end (reason of the requirement).
    lines = [line(1, date(2026, 3, 2), date(2026, 3, 6))] * 3
    assert planned_value(lines, date(2026, 3, 4)) == Decimal("1.80")
    assert planned_value(
        [line(10, date(2026, 3, 2), date(2026, 3, 4))] * 3, date(2026, 3, 2)
    ) == Decimal(10)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_delaying_a_task_of_the_current_revision_leaves_the_planned_value_of_the_reference() -> (
    None
):
    # « Retarder une tâche dans la révision courante ne change pas la valeur planifiée. »
    # Here the reference is given to the function, so that the delay of the other revision cannot
    # reach it; the criterion closes fully with US-1520/L2, which chooses the lines, on
    # ``planned_value`` of the interface of ``estimate`` (the reference revision, not the current).
    reference = [line(400, date(2026, 3, 2), date(2026, 3, 13))]
    delayed = line(400, date(2026, 3, 30), date(2026, 4, 10))
    before = planned_value(reference, date(2026, 3, 13))
    assert planned_value([delayed], date(2026, 3, 13)) == Decimal(0)
    assert planned_value(reference, date(2026, 3, 13)) == before == Decimal(400)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_without_lines_the_planned_value_is_nil() -> None:
    assert planned_value([], date(2026, 3, 13)) == Decimal(0)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_sum_is_rounded_once_from_the_exact_total_not_from_a_quotient() -> None:
    # Just under a cent and a half, past the 28 digits of a quotient: rounded in two steps it would
    # reach 0.015 and then the even 0.02; rounded once it is 0.01.
    just_under = Decimal("0.014999999999999999999999999999999")
    day = WorkInstant(date(2026, 3, 2))
    lines = [PlannedLine(just_under, Placement(EIGHT_HOURS, day, day))]
    assert planned_value(lines, date(2026, 3, 2)) == Decimal("0.01")
    third = [line(1, date(2026, 3, 2), date(2026, 3, 4))] * 3
    assert planned_value(third, date(2026, 3, 2)) == Decimal(1)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_task_over_a_weekend_counts_whole_at_its_end_not_at_its_start() -> None:
    # The choice (the design is silent): no hour worked, the line counts whole at the end.
    weekend = PlannedLine(
        Decimal(80),
        Placement(EIGHT_HOURS, WorkInstant(date(2026, 3, 7)), WorkInstant(date(2026, 3, 9))),
    )
    assert planned_value([weekend], date(2026, 3, 7)) == Decimal(0)
    assert planned_value([weekend], date(2026, 3, 9)) == Decimal(80)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_keeps_the_two_decimals_of_the_cent() -> None:
    """The value serialises with its cents: ``80.00``, ``1.80`` and ``0.00``, not ``80``."""
    weekend = line(80, date(2026, 3, 7), date(2026, 3, 8))
    assert str(planned_value([weekend], date(2026, 3, 9))) == "80.00"
    assert str(planned_value([TWO_MONTHS], date(2026, 3, 31))) == "500.00"
    assert str(planned_value([], date(2026, 3, 13))) == "0.00"
