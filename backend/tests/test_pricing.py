# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The amount of an estimate line and its projection, without a database (US-1490/L2).

The numeric examples of WF-DEV-0020, WF-DEV-0030 and WF-DAT-0100 on the pure module ``pricing``.
"""

from decimal import Decimal
from itertools import permutations

import pytest

from waterfall.core.estimate.pricing import (
    Amount,
    Share,
    dependencies_of,
    disbursement_base_amount,
    inflation_factor,
    labour_base_amount,
    projected_amount,
    round_to_cent,
    sum_amounts,
)

D = Decimal
RATE = D("0.03")


@pytest.mark.requirement("WF-DEV-0020-A")
def test_labour_base_amount_is_quantity_times_effort_times_rate() -> None:
    assert labour_base_amount(D(2), D(80), D("55.50")) == D("8880.00")


@pytest.mark.requirement("WF-DEV-0020-A")
def test_disbursement_base_amount_is_quantity_times_disbursement() -> None:
    assert disbursement_base_amount(D(3), D("12.345")) == D("37.04")


@pytest.mark.requirement("WF-DEV-0020-A")
def test_labour_line_two_years_later_is_the_product_times_1_0609() -> None:
    base = labour_base_amount(D(1), D(100), D(50))
    shares = [Share(2028, D(1) * D(100) * D(50))]
    assert projected_amount(shares, 2026, RATE) == round_to_cent(base * D("1.0609"))
    assert projected_amount(shares, 2026, RATE) == D("5304.50")


@pytest.mark.requirement("WF-DEV-0030-A")
def test_two_years_at_three_percent_is_1_03_times_1_03() -> None:
    assert inflation_factor(RATE, 2026, 2028) == D("1.03") * D("1.03") == D("1.0609")


@pytest.mark.requirement("WF-DEV-0030-A")
def test_line_consumed_in_the_reference_year_is_its_base_amount() -> None:
    base = labour_base_amount(D(1), D(7), D("33.33"))
    assert projected_amount([Share(2026, D(7) * D("33.33"))], 2026, RATE) == base


@pytest.mark.requirement("WF-DEV-0030-A")
def test_year_before_the_reference_year_is_not_deflated() -> None:
    assert inflation_factor(RATE, 2026, 2025) == D(1)


@pytest.mark.requirement("WF-DEV-0030-A")
def test_provision_line_is_not_projected() -> None:
    shares = [Share(2028, D("1000.00"))]
    assert projected_amount(shares, 2026, RATE, provision=True) == D("1000.00")
    assert projected_amount(shares, 2026, RATE) == D("1060.90")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_reestimated_amount_sums_the_projected_shares_then_rounds_once() -> None:
    shares = [Share(2026, D("0.05")), Share(2027, D("0.05"))]
    # 0.05 + 0.0515 = 0.1015, rounded once to 0.10; the two shares apart would give 0.05 + 0.05.
    assert projected_amount(shares, 2026, RATE) == D("0.10")
    halves = [Share(2026, D("0.045")), Share(2026, D("0.045"))]
    assert projected_amount(halves, 2026, RATE) == D("0.09")
    assert sum_amounts(round_to_cent(share.amount) for share in halves) == D("0.08")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_rounding_is_half_to_even() -> None:
    assert round_to_cent(D("0.125")) == D("0.12")
    assert round_to_cent(D("0.135")) == D("0.14")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_sum_does_not_depend_on_the_order() -> None:
    amounts = [D("19.99"), D("0.01"), D("1234.56"), D("0.10"), D("7.07")]
    assert len({sum_amounts(order) for order in permutations(amounts)}) == 1
    assert sum_amounts(amounts) == D("1261.73")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_ten_times_ten_cents_is_exactly_one() -> None:
    assert sum_amounts([D("0.10")] * 10) == D("1.00")


@pytest.mark.requirement("WF-DEV-0020-A")
def test_dependencies_of_the_amounts() -> None:
    assert dependencies_of(Amount.BASE, labour=True) == ("hourly_rate",)
    assert dependencies_of(Amount.BASE, labour=False) == ("unit_disbursement",)
    assert dependencies_of(Amount.BUDGETED, labour=True) == ("reference_revision", "inflation")
    assert dependencies_of(Amount.REESTIMATED, labour=False) == ("remaining_reviews", "inflation")


@pytest.mark.requirement("WF-DEV-0030-A")
def test_dependencies_of_a_provision_line_name_no_inflation() -> None:
    assert dependencies_of(Amount.REESTIMATED, labour=False, provision=True) == (
        "remaining_reviews",
    )
