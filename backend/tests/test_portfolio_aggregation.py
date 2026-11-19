# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The pure arithmetic of the portfolio (US-2670/L2): what the examples miss, no database."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from waterfall.core.estimate.interface import Month
from waterfall.core.indicators.interface import Computable
from waterfall.core.portfolio.aggregation import (
    ALERT,
    NOMINAL,
    WATCH,
    ProjectFigures,
    Quarter,
    ZoneCount,
    aggregate,
    conversion_rate,
    count_by_key,
    load_ratio,
    load_zone,
    month_label,
    months_window,
    quarter_of,
    quarters_touched,
    ratio_of,
    reading_day,
    shares_of,
    sum_by_key,
    sum_by_month,
    total_of,
    weight_of,
    weighted_amount,
    weighted_hours,
    zone_distribution,
)

if TYPE_CHECKING:
    from waterfall.core.projects.interface import ProjectState

D = Decimal


@pytest.mark.requirement("WF-PRJ-0090-A")
@pytest.mark.parametrize(
    ("state", "weight"),
    [
        ("in_progress", D(1)),
        ("completed", D(1)),
        ("pricing", D("0.4")),
        ("created", D(0)),
        ("lost", D(0)),
        ("abandoned", D(0)),
    ],
)
def test_a_project_weighs_all_in_progress_or_completed_its_probability_in_pricing_and_nothing_else(
    state: ProjectState, weight: Decimal
) -> None:
    assert weight_of(state, D("0.4")) == weight


@pytest.mark.requirement("WF-PTF-0020-A")
def test_a_weighted_amount_is_rounded_to_the_cent_a_half_away_from_nought() -> None:
    assert weighted_amount(D("0.25"), D("0.1")) == D("0.03")
    assert weighted_amount(D("-0.25"), D("0.1")) == D("-0.03")


@pytest.mark.requirement("WF-PTF-0060-A")
def test_weighted_hours_are_rounded_to_the_hundredth_a_half_to_the_nearest_even() -> None:
    assert weighted_hours(D("0.25"), D("0.1")) == D("0.02")
    assert weighted_hours(D("0.35"), D("0.1")) == D("0.04")


@pytest.mark.requirement("WF-PTF-0020-A")
def test_the_sum_of_nothing_is_written_as_an_amount_and_keys_sum_in_the_order_they_appear() -> None:
    assert total_of([]) == D("0.00")
    assert str(total_of([])) == "0.00"
    assert list(sum_by_key([{"b": D("1.00")}, {"a": D("2.00"), "b": D("0.50")}]).items()) == [
        ("b", D("1.50")),
        ("a", D("2.00")),
    ]


@pytest.mark.requirement("WF-PTF-0090-A")
def test_the_risks_are_counted_by_cell_of_the_matrix_once_each_in_the_order_cells_appear() -> None:
    cells = [("high", "low"), ("low", "low"), ("high", "low")]
    assert list(count_by_key(cells).items()) == [(("high", "low"), 2), (("low", "low"), 1)]
    assert count_by_key([]) == {}


@pytest.mark.requirement("WF-PTF-0070-A")
def test_a_period_past_the_date_gives_the_quarters_to_come_each_read_on_the_date() -> None:
    # The contract bounds the quarters by the period alone: none is dropped, and a quarter that
    # is not over is read on the date of calculation, so the points repeat that reading.
    as_of = date(2026, 5, 20)
    quarters = quarters_touched(date(2026, 1, 1), date(2026, 12, 31))
    assert [each.label for each in quarters] == ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"]
    assert [reading_day(each, as_of) for each in quarters] == [
        date(2026, 3, 31),
        as_of,
        as_of,
        as_of,
    ]


@pytest.mark.requirement("WF-PTF-0100-A")
def test_the_sum_by_month_covers_the_window_and_leaves_out_the_months_outside_it() -> None:
    january, february, march = Month(2026, 1), Month(2026, 2), Month(2026, 3)
    sums = sum_by_month(
        [{january: D("1.50"), march: D("9.00")}, {january: D("0.50")}], [january, february]
    )
    assert sums == [D("2.00"), D("0.00")]
    assert str(sums[1]) == "0.00"


@pytest.mark.requirement("WF-PTF-0080-A")
def test_the_shares_of_a_distribution_sum_to_one_the_remainder_going_to_the_largest() -> None:
    shares = shares_of([D(1), D(1), D(1)])
    assert [each.value for each in shares] == [D("0.3334"), D("0.3333"), D("0.3333")]
    assert sum((each.value or D(0) for each in shares), D(0)) == D(1)


@pytest.mark.requirement("WF-PTF-0080-A")
def test_the_shares_of_a_distribution_of_nothing_are_not_computable_for_lack_of_a_total() -> None:
    assert [each.reason for each in shares_of([D(0), D(0)])] == ["no_total", "no_total"]


@pytest.mark.requirement("WF-PTF-0020-A")
def test_a_ratio_is_to_four_decimals_and_not_computable_without_a_denominator() -> None:
    assert ratio_of(D(2), D(3), "no_capacity").value == D("0.6667")
    assert ratio_of(D(2), D(0), "no_capacity") == Computable.not_computable("no_capacity")


@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_indices_of_no_project_are_not_computable_and_the_variances_nought() -> None:
    result = aggregate([])
    assert result.cost_index.reason == "no_actual_cost"
    assert result.schedule_index.reason == "no_planned_value"
    assert result.projections.at_observed_rate.is_computable is False
    assert (result.cost_variance, result.schedule_variance) == (D(0), D(0))


@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_variances_and_the_schedule_index_are_those_of_the_sums() -> None:
    first = ProjectFigures(D(1000), D(400), D(500), D(500), D(550))
    second = ProjectFigures(D(1000), D(500), D(500), D(400), D(450))
    result = aggregate([first, second])
    assert result.cost_variance == D("-100.00")
    assert result.schedule_variance == D("0.00")
    assert result.schedule_index.value == D("1.0000")
    assert result.projections.project_manager == D("2000.00")


@pytest.mark.requirement("WF-PTF-0050-A")
def test_the_conversion_rate_without_an_offer_out_of_pricing_is_not_computable() -> None:
    assert conversion_rate([]).reason == "no_offer_out_of_pricing"
    assert conversion_rate(["abandoned"]).reason == "no_offer_out_of_pricing"
    assert conversion_rate(["lost"]).value == D("0.0000")


@pytest.mark.requirement("WF-PTF-0070-A")
def test_the_distribution_by_zone_counts_a_project_once_and_skips_an_index_not_computed() -> None:
    indices = [
        Computable.of(D("0.95")),
        Computable.of(D("0.85")),
        Computable.of(D("0.5")),
        Computable.of(D("0.9")),
        Computable.not_computable("no_actual_cost"),
    ]
    assert zone_distribution(indices, D("0.9"), D("0.8")) == (
        ZoneCount(NOMINAL, 2),
        ZoneCount(WATCH, 1),
        ZoneCount(ALERT, 1),
    )


@pytest.mark.requirement("WF-PTF-0060-A")
@pytest.mark.parametrize(
    ("hours", "capacity", "zone"),
    [
        (D("100.01"), D(100), ALERT),
        (D(100), D(100), NOMINAL),
        (D("50.00"), D(100), NOMINAL),
        (D("49.99"), D(100), WATCH),
        (D(0), D(100), WATCH),
        (D("0.01"), D(0), ALERT),
        (D(0), D(0), WATCH),
    ],
)
def test_a_month_of_load_is_in_alert_beyond_the_capacity_and_in_watch_under_the_threshold(
    hours: Decimal, capacity: Decimal, zone: str
) -> None:
    assert load_zone(hours, capacity, D("0.5")) == zone


@pytest.mark.requirement("WF-PTF-0060-A")
def test_the_load_ratio_of_a_role_without_capacity_is_not_computable() -> None:
    assert load_ratio(D(10), D(0)).reason == "no_capacity"
    assert load_ratio(D(0), D(100)).value == D("0.0000")


@pytest.mark.requirement("WF-PTF-0100-A")
def test_the_months_of_the_curve_run_twelve_before_the_date_and_six_from_its_month() -> None:
    months = months_window(date(2026, 6, 15), before=12, horizon=6)
    assert [month_label(each) for each in (months[0], months[-1])] == ["2025-06", "2026-11"]
    assert len(months) == 18
    december = months_window(date(2025, 12, 31), before=12, horizon=1)
    assert (month_label(december[0]), month_label(december[-1])) == ("2024-12", "2025-12")


@pytest.mark.requirement("WF-PTF-0060-A")
def test_the_months_of_the_workload_run_from_the_month_of_the_date_across_a_year_end() -> None:
    months = months_window(date(2026, 11, 3), horizon=4)
    assert [month_label(each) for each in months] == ["2026-11", "2026-12", "2027-01", "2027-02"]


@pytest.mark.requirement("WF-PTF-0070-A")
def test_a_period_touches_the_quarters_from_its_first_to_its_last_day_across_a_year_end() -> None:
    quarters = quarters_touched(date(2025, 11, 20), date(2026, 4, 1))
    assert [each.label for each in quarters] == ["2025-Q4", "2026-Q1", "2026-Q2"]
    assert quarters_touched(date(2026, 5, 5), date(2026, 5, 5)) == [Quarter(2026, 2)]
    assert quarter_of(date(2026, 12, 31)) == Quarter(2026, 4)


@pytest.mark.requirement("WF-PTF-0070-A")
def test_a_quarter_is_read_on_its_last_day_and_the_one_holding_the_date_on_that_date() -> None:
    assert Quarter(2026, 1).last_day == date(2026, 3, 31)
    assert Quarter(2024, 1).last_day == date(2024, 3, 31)
    assert Quarter(2026, 4).last_day == date(2026, 12, 31)
    assert reading_day(Quarter(2026, 1), date(2026, 5, 20)) == date(2026, 3, 31)
    assert reading_day(Quarter(2026, 2), date(2026, 5, 20)) == date(2026, 5, 20)
