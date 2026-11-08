# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The planned value on given lines and dates, without a database (US-1520/L1).

The lines are those of the reference, given; their tasks run on a calendar of eight hours from
Monday to Friday. In 2026, March and April hold 22 working days each.
"""

from datetime import date
from decimal import Decimal

import pytest

from waterfall.core.estimate.spreading import PlannedLine, Placement, WorkWeek, planned_value
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
def test_a_line_of_a_task_of_two_months_of_equal_hours_counts_for_half_at_the_end_of_the_first() -> None:
    # « Une ligne portée par une tâche de deux mois comptant autant d'heures travaillées
    # contribue pour moitié à la fin du premier mois. »
    assert planned_value([TWO_MONTHS], date(2026, 3, 31)) == Decimal(500)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_planned_value_grows_with_the_hours_worked_and_stops_at_the_amount() -> None:
    # « Étalé sur la durée de leur tâche au prorata des heures travaillées. »
    week_one = date(2026, 3, 6)
    values = [planned_value([TWO_MONTHS], at) for at in (date(2026, 2, 28), week_one, date(2026, 4, 30))]
    assert values == [Decimal(0), Decimal("113.64"), Decimal(1000)]
    assert planned_value([TWO_MONTHS], date(2030, 1, 1)) == Decimal(1000)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_line_of_a_milestone_counts_whole_on_its_date_and_not_before() -> None:
    # « Une ligne portée par un jalon est comptée entière à la date du jalon. »
    milestone = WorkInstant(date(2026, 3, 20))
    lines = [PlannedLine(Decimal(300), Placement(EIGHT_HOURS, milestone, milestone))]
    assert planned_value(lines, date(2026, 3, 19)) == Decimal(0)
    assert planned_value(lines, date(2026, 3, 20)) == Decimal(300)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_lines_add_up_and_the_sum_is_rounded_once_to_the_cent() -> None:
    # « Elle doit totaliser exactement le budget de référence en fin de projet. »
    lines = [line(1, date(2026, 3, 2), date(2026, 3, 6))] * 3
    assert planned_value(lines, date(2026, 3, 4)) == Decimal("1.80")
    assert planned_value([line(10, date(2026, 3, 2), date(2026, 3, 4))] * 3, date(2026, 3, 2)) == Decimal(10)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_delaying_a_task_of_the_current_revision_leaves_the_planned_value_of_the_reference() -> None:
    # « Retarder une tâche dans la révision courante ne change pas la valeur planifiée. »
    reference = [line(400, date(2026, 3, 2), date(2026, 3, 13))]
    delayed = line(400, date(2026, 3, 30), date(2026, 4, 10))
    before = planned_value(reference, date(2026, 3, 13))
    assert planned_value([delayed], date(2026, 3, 13)) == Decimal(0)
    assert planned_value(reference, date(2026, 3, 13)) == before == Decimal(400)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_without_lines_the_planned_value_is_nil() -> None:
    assert planned_value([], date(2026, 3, 13)) == Decimal(0)
