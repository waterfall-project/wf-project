# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The parts of a line by month, rounded so that they sum to its total, without a database.

US-2040/L2: the rule of ``docs/api/DECISIONS.md`` (US-2040/L1) — a part is the difference of two
roundings of the cumulated line, the last month closing on the whole line —, the hours a half to
the nearest even, the amounts a half away from nought. The tasks run on a calendar of eight hours
from Monday to Friday; in 2026, February holds 20 working days, March and April 22 each.
"""

from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest

from waterfall.core.estimate import parting
from waterfall.core.estimate.interface import (
    HOURS,
    MONEY,
    Month,
    Placement,
    PlannedLine,
    parts_of_cumulated,
    remaining_parts,
    rounded_parts,
    summed_parts,
    weighing,
)
from waterfall.core.estimate.spreading import MonthWeights, month_weights, planned_value
from waterfall.core.indicators.series import SpreadLine, spread_lines
from waterfall.core.planning.interface import WorkInstant, weekly_calendar

EIGHT = Decimal(8)
ZERO = Decimal(0)
EIGHT_HOURS = weekly_calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, ZERO, ZERO))
FEBRUARY, MARCH, APRIL = Month(2026, 2), Month(2026, 3), Month(2026, 4)
# From the first of February to the last of April 2026: 64 days, 512 hours, 160 in February.
SPRING = Placement(
    EIGHT_HOURS, WorkInstant(date(2026, 2, 2)), WorkInstant(date(2026, 4, 30), EIGHT)
)


def month_end(month: Month) -> date:
    """Give the last day of a month, December's included."""
    following = Month(month.year + month.month // 12, month.month % 12 + 1)
    return date(following.year, following.month, 1) - timedelta(days=1)


@pytest.mark.requirement("WF-DEV-0090-A")
def test_each_part_is_the_difference_of_two_rounded_cumulated_hours_a_half_to_the_even() -> None:
    # 100 hours: 31.25 in February, 34.375 in March and in April. Cumulated at the end of March,
    # 65.625 rounds to 65.62, a half to the even: March holds 34.37, April the rest of the line.
    parts = rounded_parts(SPRING, Decimal(100), HOURS)
    assert parts == {FEBRUARY: Decimal("31.25"), MARCH: Decimal("34.37"), APRIL: Decimal("34.38")}
    assert sum(parts.values()) == Decimal(100)
    assert list(parts) == [FEBRUARY, MARCH, APRIL]


@pytest.mark.requirement("WF-DEV-0090-A")
@pytest.mark.requirement("WF-DEV-0080-A")
def test_an_amount_rounds_its_cumulated_half_away_from_nought() -> None:
    # The same line as an amount: 65.625 rounds to 65.63, March holds 34.38. The amount lane is
    # that of the planned value (WF-DEV-0080), which rounds the same cumulated the same way.
    parts = rounded_parts(SPRING, Decimal(100), MONEY)
    assert parts == {FEBRUARY: Decimal("31.25"), MARCH: Decimal("34.38"), APRIL: Decimal("34.37")}


@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_parts_sum_to_the_line_rounded_and_none_is_negative() -> None:
    # A line of hours whose parts all fall between two hundredths: they still sum to the line.
    total = Decimal("100.013")
    parts = rounded_parts(SPRING, total, HOURS)
    assert sum(parts.values()) == HOURS.of(total) == Decimal("100.01")
    assert all(part > 0 for part in parts.values())


@pytest.mark.requirement("WF-DEV-0090-A")
def test_a_month_the_rounding_leaves_at_nought_is_not_loaded() -> None:
    # Half a hundredth on a task of a month: nought hours, a half to the even, so no month at all;
    # a cent as an amount, a half away from nought.
    march = Placement(EIGHT_HOURS, WorkInstant(date(2026, 3, 2)), WorkInstant(date(2026, 3, 31)))
    assert rounded_parts(march, Decimal("0.005"), HOURS) == {}
    assert rounded_parts(march, Decimal("0.005"), MONEY) == {MARCH: Decimal("0.01")}
    # A half between nought and a hundredth goes to nought, the even; one between a hundredth and
    # two goes to two (#3591).
    assert rounded_parts(march, Decimal("0.015"), HOURS) == {MARCH: Decimal("0.02")}


@pytest.mark.requirement("WF-DEV-0090-A")
def test_on_a_remaining_the_line_falls_after_the_date_of_calculation() -> None:
    # Calculated on the 1st of April, only April is left; past the finish, the whole line falls in
    # the month of the date of calculation.
    assert rounded_parts(SPRING, Decimal(64), HOURS, as_of=date(2026, 4, 1)) == {APRIL: Decimal(64)}
    assert rounded_parts(SPRING, Decimal(64), HOURS, as_of=date(2026, 6, 10)) == {
        Month(2026, 6): Decimal(64)
    }


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_parts_cumulate_to_the_planned_value_through_a_december_and_a_new_year() -> None:
    # 100.01 from Monday 16 November 2026 to Friday 8 January 2027: the end of December, the 31st,
    # is a month end like any other, and the year turns without a part lost.
    task = Placement(
        EIGHT_HOURS, WorkInstant(date(2026, 11, 16)), WorkInstant(date(2027, 1, 8), EIGHT)
    )
    parts = rounded_parts(task, Decimal("100.01"), MONEY)
    assert list(parts) == [Month(2026, 11), Month(2026, 12), Month(2027, 1)]
    line = [PlannedLine(Decimal("100.01"), task)]
    cumulated = Decimal(0)
    for month, part in parts.items():
        cumulated += part
        assert planned_value(line, month_end(month)) == cumulated, month
    assert month_end(Month(2026, 12)) == date(2026, 12, 31)


@pytest.mark.requirement("WF-DEV-0080-A")
def test_the_parts_of_an_amount_cumulate_to_its_planned_value_at_the_end_of_each_month() -> None:
    # The cumulated is rounded once from its exact value, as the planned value of the line is
    # (#3566). 0.05 from Monday 16 February to Friday 8 May 2026: 80, 176, 176 and 48 hours of 480.
    # At the end of April, nine tenths of it, 0.045 exactly, round to 0.05; summed from shares of
    # ten decimals, 0.0449999999, it would round to 0.04.
    task = Placement(
        EIGHT_HOURS, WorkInstant(date(2026, 2, 16)), WorkInstant(date(2026, 5, 8), EIGHT)
    )
    parts = rounded_parts(task, Decimal("0.05"), MONEY)
    assert parts == {FEBRUARY: Decimal("0.01"), MARCH: Decimal("0.02"), APRIL: Decimal("0.02")}
    line = [PlannedLine(Decimal("0.05"), task)]
    cumulated = Decimal(0)
    for month in (FEBRUARY, MARCH, APRIL, Month(2026, 5)):
        cumulated += parts.get(month, Decimal(0))
        last = month_end(month)
        assert planned_value(line, last) == cumulated, month


@pytest.mark.requirement("WF-DEV-0090-A")
def test_parts_summed_keep_the_months_in_order_and_leave_out_a_month_at_nought() -> None:
    summed = summed_parts(
        [
            {MARCH: Decimal("1.50"), FEBRUARY: Decimal(2)},
            {APRIL: Decimal(0), FEBRUARY: Decimal("0.25")},
        ]
    )
    assert summed == {FEBRUARY: Decimal("2.25"), MARCH: Decimal("1.50")}
    assert list(summed) == [FEBRUARY, MARCH]


MAY = Month(2026, 5)
CUMULATED = [
    (FEBRUARY, Fraction(10005, 1000)),
    (MARCH, Fraction(4004, 1000)),
    (APRIL, Fraction(4004, 1000)),
    (MAY, Fraction(20)),
]


@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_parts_of_a_cumulated_are_the_differences_of_its_roundings_in_the_order_given() -> None:
    # A cumulated that falls back (10.005, then 4.004) gives a negative part, which is kept; a
    # half goes away from nought as an amount (10.005 is 10.01) and to the even as hours (10.00);
    # a month that rounds as the one before holds no part (April);
    # the last month closes on the whole.
    assert parts_of_cumulated(CUMULATED, MONEY) == {
        FEBRUARY: Decimal("10.01"),
        MARCH: Decimal("-6.01"),
        MAY: Decimal("16.00"),
    }
    assert parts_of_cumulated(CUMULATED, HOURS) == {
        FEBRUARY: Decimal("10.00"),
        MARCH: Decimal("-6.00"),
        MAY: Decimal("16.00"),
    }


WINTER = Placement(
    EIGHT_HOURS, WorkInstant(date(2026, 1, 5)), WorkInstant(date(2026, 2, 27), EIGHT)
)


@pytest.mark.requirement("WF-DEV-0090-A")
@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_task_weighed_once_gives_each_of_its_lines_the_parts_it_has_alone() -> None:
    # The weights of the months depend on the task, not on the amount (#3802): the lines of a task
    # spread by one weighing, which weighs it once for a date of calculation, have the parts each
    # has alone, on the whole task and after a date of calculation; and the planned value of lines
    # of one task, each task counted once, is the sum of theirs.
    weighed: list[tuple[Placement, date | None]] = []
    kept = weighing()

    def weigh(placement: Placement, as_of: date | None) -> MonthWeights:
        weighed.append((placement, as_of))
        return kept(placement, as_of)

    amounts = (Decimal(100), Decimal("0.05"), Decimal("100.01"), Decimal(-7))
    after = date(2026, 2, 10)
    for placement in (SPRING, WINTER):
        for amount in amounts:
            alone = rounded_parts(placement, amount, MONEY)
            assert rounded_parts(placement, amount, MONEY, weigh=weigh) == alone
            alone = remaining_parts(placement, amount, HOURS, as_of=after)
            assert remaining_parts(placement, amount, HOURS, as_of=after, weigh=weigh) == alone
    assert len(weighed) == 2 * 2 * len(amounts)
    assert kept(SPRING, None) is kept(SPRING, None)
    assert kept(SPRING, after) is not kept(SPRING, None)
    lines = [PlannedLine(amount, SPRING) for amount in amounts]
    day = date(2026, 3, 17)
    assert planned_value(lines, day) == sum(
        (planned_value([line], day) for line in lines), Decimal(0)
    )


@pytest.mark.requirement("WF-DEV-0090-A")
def test_the_lines_of_a_sum_weigh_each_task_once_for_a_date_of_calculation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A detail of the realisation (#3802), which reprises no Vérif of its own: the weights of the
    # months are computed once by task and date, whatever the number of its lines.
    calls: list[tuple[Placement, date | None]] = []

    def counting(placement: Placement, *, as_of: date | None = None) -> MonthWeights:
        calls.append((placement, as_of))
        return month_weights(placement, as_of=as_of)

    monkeypatch.setattr(parting, "month_weights", counting)
    lines = [
        SpreadLine(Decimal(amount), placement)
        for placement in (SPRING, WINTER)
        for amount in (100, 7, 33, 250)
    ]
    for as_of in (None, date(2026, 2, 10)):
        # The part to come starts the day after the date of calculation.
        weighed_at = None if as_of is None else as_of + timedelta(days=1)
        calls.clear()
        spread_lines(lines, as_of=as_of)
        assert sorted(calls, key=lambda each: each[0].start.day) == [
            (WINTER, weighed_at),
            (SPRING, weighed_at),
        ]


def by_fraction(value: Decimal | Fraction, quantum: Decimal, *, half_up: bool) -> Decimal:
    """Round as fractions do: the rule of ``Rounding.of`` before it counted in integers (#3902)."""
    steps = Fraction(value) / Fraction(quantum)
    floor = steps.numerator // steps.denominator
    rest = steps - floor
    if rest != Fraction(1, 2):
        return Decimal(floor + int(rest > Fraction(1, 2))) * quantum
    # A half: away from nought — up for a positive value, down for a negative one —, or to the even.
    if half_up:
        return Decimal(floor + 1 if floor >= 0 else floor) * quantum
    return Decimal(floor if floor % 2 == 0 else floor + 1) * quantum


@pytest.mark.requirement("WF-DEV-0090-A")
def test_a_value_rounds_in_integers_as_its_exact_fraction_does() -> None:
    # A detail of the realisation (#3902), which reprises no Vérif of its own: the rounding counts
    # in integers, and rounds every value as the fraction did — a half away from nought for an
    # amount, to the even for hours, the other values to the nearest, of either sign.
    assert MONEY.of(Decimal("0.005")) == Decimal("0.01")
    assert MONEY.of(Decimal("-0.005")) == Decimal("-0.01")
    assert HOURS.of(Decimal("0.005")) == Decimal("0.00")
    assert HOURS.of(Decimal("0.015")) == Decimal("0.02")
    assert HOURS.of(Decimal("-0.015")) == Decimal("-0.02")
    assert MONEY.of(Fraction(2, 3)) == Decimal("0.67")
    assert MONEY.of(Fraction(-2, 3)) == Decimal("-0.67")
    cent = Decimal("0.01")
    values: list[Decimal | Fraction] = [
        Fraction(top, bottom) for top in range(-1201, 1202, 7) for bottom in (1, 3, 8, 200, 400)
    ]
    values += [Decimal(top) / 1000 for top in range(-2000, 2001, 5)]
    for value in values:
        assert MONEY.of(value) == by_fraction(value, cent, half_up=True), value
        assert HOURS.of(value) == by_fraction(value, cent, half_up=False), value
