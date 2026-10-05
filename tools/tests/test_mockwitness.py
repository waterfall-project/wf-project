# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the witness project said once, and of the hours of work of its calendars."""

from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import pairwise

import pytest

from wftools import mockwitness
from wftools.mockcalendar import ORIGIN, Calendar, Instant, applicable


def hours(*values: int) -> tuple[Decimal, ...]:
    return tuple(Decimal(value) for value in values)


STANDARD = Calendar("standard", hours(8, 8, 8, 8, 8, 0, 0))
FOUR_DAYS = Calendar("four", hours(10, 10, 10, 10, 0, 0, 0))


def at(day: int, worked: int | str = 0) -> Instant:
    """Return an instant of June 2026."""
    return Instant(date(2026, 6, day), Decimal(worked))


def test_today_is_the_instant_every_first_example_describes() -> None:
    assert datetime(2026, 6, 3, 14, 5, tzinfo=UTC) == mockwitness.TODAY
    days = [event.on for event in mockwitness.CHRONOLOGY]
    assert days == sorted(days)
    assert days[0] == date(2025, 9, 1)
    assert days[-1] == mockwitness.TODAY.date()
    # The project is created before its offer is opened (#287, C11).
    assert mockwitness.CREATED.on < mockwitness.OFFER_OPENED.on < mockwitness.OFFER_MARKED.on


def test_the_families_of_identifiers_lie_on_disjoint_ranges() -> None:
    by_family: dict[int, list[mockwitness.Family]] = {}
    for family in mockwitness.IDENTIFIERS:
        by_family.setdefault(family.generated, []).append(family)
    assert [len(families) for number, families in sorted(by_family.items()) if number] == [1] * 5
    written = sorted(by_family[0], key=lambda family: family.first)
    assert all(family.first <= family.last for family in written)
    assert all(before.last < after.first for before, after in pairwise(written))
    assert all(family.last < 1_000 for family in written)


def test_an_identifier_belongs_to_one_family() -> None:
    node = mockwitness.universe(521)
    assert node == "01926f3a-7c00-7000-8000-000000000521"
    assert [family.what for family in mockwitness.IDENTIFIERS if family.holds(node)] == [
        "nœuds de la structure"
    ]
    drawn = mockwitness.identifier(mockwitness.NODES, 4)
    assert drawn == "01926f3a-7c00-7000-8000-000100000004"
    assert [family.what for family in mockwitness.IDENTIFIERS if family.holds(drawn)] == [
        "nœuds engendrés"
    ]
    assert not any(family.holds("an identifier") for family in mockwitness.IDENTIFIERS)


def _core(task: mockwitness.Task) -> list[mockwitness.Task | mockwitness.Line]:
    return [task, *task.lines, *(each for child in task.children for each in _core(child))]


def test_the_core_has_one_identifier_a_node_and_its_lineage_apart() -> None:
    numbers = [each.number for root in mockwitness.CORE for each in _core(root)]
    assert len(numbers) == len(set(numbers)) == 18
    nodes = next(family for family in mockwitness.IDENTIFIERS if family.what.startswith("nœuds de"))
    lineages = next(family for family in mockwitness.IDENTIFIERS if family.first == 600)
    assert all(nodes.holds(mockwitness.universe(number)) for number in numbers)
    assert all(lineages.holds(mockwitness.universe(number + 100)) for number in numbers)


def test_the_witness_employs_three_active_roles_on_two_calendars() -> None:
    roles = {role["resource_role_id"]: role for role in mockwitness.fixture("resource_roles")}
    fitter = roles[mockwitness.CABLE_FITTER]
    assert (fitter["label"], fitter["is_active"]) == ("Monteur câbleur", True)
    assert fitter["cost_category_id"] == mockwitness.ELECTRICAL_ENGINEERING
    calendars = mockwitness.role_calendars()
    assert {role: calendar.calendar_id for role, calendar in calendars.items()} == {
        mockwitness.ENGINEER: mockwitness.STANDARD_WEEK,
        mockwitness.COMMISSIONING_TECHNICIAN: mockwitness.STANDARD_WEEK,
        mockwitness.CABLE_FITTER: mockwitness.FOUR_DAY_WEEK,
    }
    assert calendars[mockwitness.CABLE_FITTER].week == FOUR_DAYS.week
    assert mockwitness.default_calendar().week == STANDARD.week


@pytest.mark.parametrize(
    ("instant", "count"),
    [
        (Instant(ORIGIN), 0),
        (at(1), 8 * 5 * 21),
        (at(1, 3), 8 * 5 * 21 + 3),
        # Hours past those of the day count as its end; a Saturday, as the Friday before it.
        (at(1, 12), 8 * 5 * 21 + 8),
        (at(6, 4), 8 * 5 * 22),
        (Instant(date(2026, 1, 2), Decimal(8)), 0),
    ],
)
def test_an_instant_counts_its_hours_of_work_from_a_monday(instant: Instant, count: int) -> None:
    assert STANDARD.elapsed(instant) == count


def test_a_count_on_a_day_boundary_is_a_finish_or_a_start() -> None:
    friday_end = STANDARD.elapsed(at(5, 8))
    assert STANDARD.instant(friday_end, finish=True) == at(5, 8)
    assert STANDARD.instant(friday_end, finish=False) == at(8)
    # Before the Monday hours are counted from, a count falls in its own week.
    assert STANDARD.instant(Decimal(-16), finish=False) == Instant(date(2026, 1, 1))
    assert STANDARD.instant(Decimal(-8), finish=True) == Instant(date(2026, 1, 1), Decimal(8))


def test_a_duration_is_placed_hour_after_hour_on_its_calendar() -> None:
    # Five days of eight hours: a week of the standard calendar, four days of ten hours.
    forty = Decimal(40)
    assert STANDARD.finish_after(at(1), forty) == at(5, 8)
    assert FOUR_DAYS.finish_after(at(1), forty) == at(4, 10)
    assert FOUR_DAYS.finish_after(at(4, 6), Decimal(8)) == at(8, 4)
    assert FOUR_DAYS.start_at(at(5)) == at(8)
    assert FOUR_DAYS.start_before(at(8, 4), Decimal(8)) == at(4, 6)
    assert FOUR_DAYS.work_between(at(4, 6), at(8, 4)) == 8


def test_the_calendar_of_a_task_grants_each_day_the_fewest_hours_of_its_roles() -> None:
    # WF-PLA-0010: the standard week and the week of four days of ten hours leave four days of
    # eight hours; one calendar is itself, none the default.
    both = applicable([STANDARD, FOUR_DAYS, STANDARD], STANDARD)
    assert both.week == hours(8, 8, 8, 8, 0, 0, 0)
    assert applicable([FOUR_DAYS, FOUR_DAYS], STANDARD) is FOUR_DAYS
    assert applicable([], STANDARD) is STANDARD
