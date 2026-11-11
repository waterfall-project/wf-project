# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The amount of an estimate line and its projection, without a database (US-1490/L2).

The numeric examples of WF-DEV-0020, WF-DEV-0030 and WF-DAT-0100 on the pure module ``pricing``.
"""

from decimal import Decimal
from itertools import permutations, product

import pytest
import yaml
from support import CONTRACT

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


@pytest.mark.requirement("WF-DEV-0030-A")
def test_line_consumed_in_the_reference_year_is_its_base_amount() -> None:
    base = labour_base_amount(D(1), D(7), D("33.33"))
    assert projected_amount([Share(2026, D(7) * D("33.33"))], 2026, RATE) == base


def test_year_before_the_reference_year_is_not_deflated_pending_2545() -> None:
    """Fix the reading kept until #2545 settles it (to be decided), not a Vérif of the sentence.

    It cites no requirement, so as not to count as the coverage of WF-DEV-0030-A (#2548).
    """
    assert inflation_factor(RATE, 2026, 2025) == D(1)


@pytest.mark.requirement("WF-DEV-0030-A")
def test_provision_line_is_not_projected() -> None:
    shares = [Share(2028, D("1000.00"))]
    assert projected_amount(shares, 2026, RATE, provision=True) == D("1000.00")
    assert projected_amount(shares, 2026, RATE) == D("1060.90")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_reestimated_amount_sums_the_projected_shares_then_rounds_once() -> None:
    shares = [Share(2026, D("0.004")), Share(2027, D("0.004")), Share(2027, D("0.004"))]
    # 0.004 + 2 x 0.00412 = 0.01224, rounded once to 0.01; each projected share rounded apart is
    # 0.00, and their sum 0.00.
    assert projected_amount(shares, 2026, RATE) == D("0.01")
    apart = (round_to_cent(s.amount * inflation_factor(RATE, 2026, s.year)) for s in shares)
    assert sum_amounts(apart) == D("0.00")
    halves = [Share(2026, D("0.045")), Share(2026, D("0.045"))]
    assert projected_amount(halves, 2026, RATE) == D("0.09")
    assert sum_amounts(round_to_cent(share.amount) for share in halves) == D("0.10")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_rounding_is_half_away_from_zero_as_money_of_the_contract_says() -> None:
    # ``Money``: "rounded to the cent, to nearest, a half going away from zero" (#2618); the
    # projected rate of the contract's ``rate_update``, 73.50 x 1.03 = 75.705, gives 75.71.
    assert round_to_cent(D("0.125")) == D("0.13")
    assert round_to_cent(D("0.135")) == D("0.14")
    assert round_to_cent(D("-0.125")) == D("-0.13")
    assert round_to_cent(D("73.50") * D("1.03")) == D("75.71")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_sum_does_not_depend_on_the_order() -> None:
    amounts = [D("19.99"), D("0.01"), D("1234.56"), D("0.10"), D("7.07")]
    assert len({sum_amounts(order) for order in permutations(amounts)}) == 1
    assert sum_amounts(amounts) == D("1261.73")


def test_an_amount_not_to_the_cent_is_refused_by_the_sum() -> None:
    """A sum of amounts holds amounts already rounded: one that is not is an error, not rounded."""
    with pytest.raises(ValueError, match="not to the cent"):
        sum_amounts([D("1.00"), D("0.005")])
    assert sum_amounts([D("1.500"), D("2")]) == D("3.50")


@pytest.mark.requirement("WF-DAT-0100-A")
def test_ten_times_ten_cents_is_exactly_one() -> None:
    """Ten cents ten times are one exactly: decimal precision, where binary floats drift.

    The independence to the order is carried by the permutations test.
    """
    assert sum_amounts([D("0.10")] * 10) == D("1.00")


@pytest.mark.requirement("WF-DEV-0020-A")
def test_dependencies_of_the_amounts() -> None:
    assert dependencies_of(Amount.BASE, labour=True) == ("hourly_rate",)
    assert dependencies_of(Amount.BASE, labour=False) == ("unit_disbursement",)
    assert dependencies_of(Amount.BUDGETED, labour=True) == ("reference_revision", "inflation")
    assert dependencies_of(Amount.REESTIMATED, labour=False) == ("remaining_reviews", "inflation")


@pytest.mark.requirement("WF-DEV-0020-A")
def test_dependencies_of_a_provision_line_name_no_inflation() -> None:
    for amount in Amount:
        assert "inflation" not in dependencies_of(amount, labour=False, provision=True)


@pytest.mark.requirement("WF-IHM-0030-A")
def test_dependencies_of_a_provision_line_follow_the_risk() -> None:
    assert dependencies_of(Amount.BASE, labour=False, provision=True) == ("risk",)
    assert dependencies_of(Amount.REESTIMATED, labour=False, provision=True) == ("risk",)
    assert dependencies_of(Amount.BUDGETED, labour=False, provision=True) == ("reference_revision",)


@pytest.mark.requirement("WF-IHM-0030-A")
def test_every_dependency_named_is_one_of_the_contract() -> None:
    contract = yaml.safe_load(
        (CONTRACT.parent / "components" / "schemas" / "revisions.yaml").read_text(encoding="utf-8")
    )
    declared = contract["ComputedDependency"].get("enum")
    assert declared, "ComputedDependency declares no enumeration"
    for amount, labour, provision in product(Amount, (True, False), (True, False)):
        assert set(dependencies_of(amount, labour=labour, provision=provision)) <= set(declared)


@pytest.mark.requirement("WF-DAT-0100-A")
def test_an_empty_sum_is_zero_to_the_cent() -> None:
    assert str(sum_amounts([])) == "0.00"
