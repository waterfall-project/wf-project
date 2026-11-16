# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The formulas of the indicators, pure (US-1660/L2): figures not computed, zones, rounding."""

from decimal import Decimal

import pytest

from waterfall.core.indicators.formulas import (
    NO_ACTUAL_COST,
    NO_ACTUAL_OR_REMAINING,
    NO_EARNED_VALUE,
    NO_PLANNED_VALUE,
    NO_REFERENCE_BUDGET,
    NOUGHT,
    Amounts,
    Computable,
    Thresholds,
    budget_consumption,
    cost_index,
    financial_progress,
    indicators_of,
    physical_progress,
    projections,
    round_amount,
    round_ratio,
    schedule_index,
)

THRESHOLDS = Thresholds(
    cost_watch=Decimal("0.9"),
    cost_alert=Decimal("0.8"),
    schedule_watch=Decimal("0.9"),
    schedule_alert=Decimal("0.8"),
)


def _d(text: str) -> Decimal:
    return Decimal(text)


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_computable_figure_has_a_value_and_no_reason_and_the_other_way_round() -> None:
    assert Computable.of(_d("0.5")) == Computable(value=_d("0.5"), reason=None)
    assert Computable.of(NOUGHT).is_computable
    missing = Computable.not_computable(NO_ACTUAL_COST)
    assert (missing.is_computable, missing.value, missing.reason) == (False, None, NO_ACTUAL_COST)


@pytest.mark.requirement("WF-IND-0040-A")
def test_a_subproject_without_actual_cost_nor_remaining_has_no_computable_financial_progress() -> (
    None
):
    assert financial_progress(NOUGHT, NOUGHT) == Computable.not_computable(NO_ACTUAL_OR_REMAINING)


@pytest.mark.requirement("WF-IND-0040-A")
def test_a_budget_consumption_over_a_nought_budget_is_not_computable() -> None:
    assert budget_consumption(_d("10"), NOUGHT) == Computable.not_computable(NO_REFERENCE_BUDGET)


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_nought_reference_budget_gives_a_physical_progress_that_is_not_computable() -> None:
    assert physical_progress(NOUGHT, NOUGHT) == Computable.not_computable(NO_REFERENCE_BUDGET)


@pytest.mark.requirement("WF-IND-0060-A")
def test_a_physical_progress_of_nothing_finished_is_computed_at_nought() -> None:
    assert physical_progress(NOUGHT, _d("1000")) == Computable.of(_d("0.0000"))


@pytest.mark.requirement("WF-IND-0070-A")
def test_a_cost_index_before_any_actual_cost_is_not_computable() -> None:
    assert cost_index(_d("400"), NOUGHT) == Computable.not_computable(NO_ACTUAL_COST)


@pytest.mark.requirement("WF-IND-0080-A")
def test_a_schedule_index_before_any_planned_value_is_not_computable() -> None:
    assert schedule_index(NOUGHT, NOUGHT) == Computable.not_computable(NO_PLANNED_VALUE)


@pytest.mark.requirement("WF-IND-0080-A")
def test_a_schedule_index_of_a_set_all_finished_on_its_planned_end_is_1() -> None:
    assert schedule_index(_d("1000"), _d("1000")) == Computable.of(_d("1.0000"))


@pytest.mark.requirement("WF-IND-0050-A")
def test_before_any_actual_cost_the_observed_rate_is_not_computable_and_the_others_are_shown() -> (
    None
):
    shown = projections(_d("1000"), NOUGHT, NOUGHT, _d("900"))
    assert shown.at_observed_rate == Computable.not_computable(NO_ACTUAL_COST)
    assert shown.variance_at_observed_rate is None
    assert shown.at_budget == _d("1000.00")
    assert shown.project_manager == _d("900.00")
    assert shown.variance_project_manager == _d("-100.00")


@pytest.mark.requirement("WF-IND-0050-A")
def test_with_an_actual_cost_and_no_earned_value_the_observed_rate_has_no_earned_value() -> None:
    shown = projections(_d("1000"), NOUGHT, _d("100"), _d("900"))
    assert shown.at_observed_rate == Computable.not_computable(NO_EARNED_VALUE)
    assert shown.variance_at_observed_rate is None


@pytest.mark.requirement("WF-IND-0050-A")
def test_the_observed_rate_is_rounded_once_from_the_exact_cost_index() -> None:
    # 1000 ÷ (100 ÷ 300) is 3000, where the index rounded to 0.3333 first would give 3000.30.
    shown = projections(_d("1000"), _d("100"), _d("300"), NOUGHT)
    assert shown.at_observed_rate == Computable.of(_d("3000.00"))


@pytest.mark.requirement("WF-IND-0070-A")
def test_an_index_changes_zone_when_it_crosses_a_threshold_and_back() -> None:
    def zone(index_of: str, thresholds: Thresholds) -> str | None:
        amounts = Amounts(_d("1000"), _d("1000"), _d(index_of), _d("100"), NOUGHT)
        return indicators_of(amounts, thresholds).cost_index.zone

    # An index of 0.85: watch at 0.9 and 0.8, nominal at 0.85 and 0.7, alert at 0.95 and 0.9.
    def thresholds(watch: str, alert: str) -> Thresholds:
        return Thresholds(_d(watch), _d(alert), _d(watch), _d(alert))

    assert zone("85", thresholds("0.9", "0.8")) == "watch"
    assert zone("85", thresholds("0.85", "0.7")) == "nominal"
    assert zone("85", thresholds("0.95", "0.9")) == "alert"
    assert zone("85", thresholds("0.9", "0.8")) == "watch"


@pytest.mark.requirement("WF-IND-0070-A")
def test_an_index_that_is_not_computable_has_no_zone() -> None:
    shown = indicators_of(Amounts(_d("1000"), NOUGHT, _d("400"), NOUGHT, NOUGHT), THRESHOLDS)
    assert (shown.cost_index.value.reason, shown.cost_index.zone) == (NO_ACTUAL_COST, None)
    assert (shown.schedule_index.value.reason, shown.schedule_index.zone) == (
        NO_PLANNED_VALUE,
        None,
    )


def test_without_thresholds_the_indices_are_computed_and_left_unclassified() -> None:
    # A document of the day, kept or cached, carries no zone: a reading classifies it (US-1660/L3).
    shown = indicators_of(Amounts(_d("1000"), _d("500"), _d("400"), _d("500"), NOUGHT), None)
    assert (shown.cost_index.value.value, shown.cost_index.zone) == (_d("0.8000"), None)
    assert (shown.schedule_index.value.value, shown.schedule_index.zone) == (_d("0.8000"), None)


@pytest.mark.requirement("WF-REF-0170-A")
def test_the_zone_is_classed_on_the_index_rounded_to_four_decimals() -> None:
    # 0.89996 is shown 0.9000, nominal at a threshold of 0.9.
    amounts = Amounts(_d("1000"), _d("1000"), _d("89.996"), _d("100"), NOUGHT)
    shown = indicators_of(amounts, THRESHOLDS).cost_index
    assert (shown.value.value, shown.zone) == (_d("0.9000"), "nominal")


_SET = Amounts(_d("1000"), _d("500"), _d("400"), _d("500"), _d("550"))


@pytest.mark.requirement("WF-IND-0040-A")
def test_the_financial_progress_of_a_set_is_given_rounded_once() -> None:
    assert indicators_of(_SET, THRESHOLDS).financial_progress.value == _d("0.4762")


@pytest.mark.requirement("WF-IND-0060-A")
def test_the_physical_progress_of_a_set_is_given_rounded_once() -> None:
    assert indicators_of(_SET, THRESHOLDS).physical_progress.value == _d("0.4000")


@pytest.mark.requirement("WF-IND-0070-A")
def test_the_cost_index_and_variance_of_a_set_are_given_rounded_once() -> None:
    shown = indicators_of(_SET, THRESHOLDS)
    assert (shown.cost_index.value.value, shown.cost_index.zone) == (_d("0.8000"), "watch")
    assert shown.cost_variance == _d("-100.00")


@pytest.mark.requirement("WF-IND-0080-A")
def test_the_schedule_index_and_variance_of_a_set_are_given_rounded_once() -> None:
    shown = indicators_of(_SET, THRESHOLDS)
    assert shown.schedule_index.value.value == _d("0.8000")
    assert shown.schedule_variance == _d("-100.00")


@pytest.mark.requirement("WF-IND-0050-A")
def test_the_projection_at_the_observed_rate_of_a_set_is_given_rounded_once() -> None:
    assert indicators_of(_SET, THRESHOLDS).projections.at_observed_rate.value == _d("1250.00")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_a_variance_is_taken_on_the_exact_projection_and_rounded_once() -> None:
    # The projection 100.0051 is shown 100.01, where the variance to a budget of 100.004 is 0.00.
    shown = projections(_d("100.004"), NOUGHT, _d("10"), _d("90.0051"))
    assert shown.project_manager == _d("100.01")
    assert shown.variance_project_manager == _d("0.00")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_the_other_two_projections_and_their_variances_are_rounded_once_too() -> None:
    # At budget: 0.0011 + 100.004 - 0 = 100.0051, shown 100.01; the variance is 0.0011, shown 0.00.
    at_budget = projections(_d("100.004"), NOUGHT, _d("0.0011"), NOUGHT)
    assert at_budget.at_budget == _d("100.01")
    assert at_budget.variance_at_budget == _d("0.00")
    # At the observed rate: 100.004 * 1.00001 / 1 = 100.00500004, shown 100.01; variance 0.00.
    observed = projections(_d("100.004"), _d("1"), _d("1.00001"), NOUGHT)
    assert observed.at_observed_rate.value == _d("100.01")
    assert observed.variance_at_observed_rate == _d("0.00")


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_figure_with_both_a_value_and_a_reason_or_neither_is_refused() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        Computable(value=NOUGHT, reason=NO_ACTUAL_COST)
    with pytest.raises(ValueError, match="exactly one"):
        Computable()


@pytest.mark.requirement("WF-IND-0070-A")
def test_an_amount_rounds_half_away_from_zero_and_a_ratio_half_to_even() -> None:
    assert round_amount(_d("0.005")) == _d("0.01")
    assert round_amount(_d("-0.005")) == _d("-0.01")
    assert round_ratio(_d("0.00005")) == _d("0.0000")
    assert round_ratio(_d("0.00015")) == _d("0.0002")
