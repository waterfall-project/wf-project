# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the amount of an estimate line (US-1490/L2), without a database.

A line consumed two years after the reference year at 3 % of inflation (WF-DEV-0020, WF-DEV-0030),
from its fixture under ``fixtures/pricing``, on the pure module ``pricing``.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.pricing import (
    Share,
    inflation_factor,
    labour_base_amount,
    projected_amount,
    round_to_cent,
    unrounded_labour_amount,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _line(
    example: Callable[[str], Example], key: str
) -> tuple[Example, Decimal, tuple[Share, ...]]:
    data = example(key)
    quantity, effort, rate = (
        Decimal(cast("str", data[name])) for name in ("quantity", "effort", "hourly_rate")
    )
    product = unrounded_labour_amount(quantity, effort, rate)
    share = Share(cast("int", data["consumption_year"]), product)
    return data, labour_base_amount(quantity, effort, rate), (share,)


@pytest.mark.requirement("WF-DEV-0020-A")
def test_labour_line_two_years_later_is_the_product_times_1_0609(
    example: Callable[[str], Example],
) -> None:
    # « ... pour une ligne consommée deux ans plus tard, avec un taux d'inflation de 3 %, il vaut
    # ce produit fois 1,0609 (WF-DEV-0030). »
    data, base, shares = _line(example, "WF-DEV-0020-A#4b83e45d65ae")
    projected = projected_amount(
        shares, cast("int", data["reference_year"]), Decimal(cast("str", data["inflation_rate"]))
    )
    assert base == Decimal(cast("str", data["base_amount"]))
    assert projected == round_to_cent(base * Decimal(cast("str", data["factor"])))
    assert projected == Decimal(cast("str", data["projected_amount"]))


@pytest.mark.requirement("WF-DEV-0030-A")
def test_two_years_at_three_percent_is_1_03_times_1_03(
    example: Callable[[str], Example],
) -> None:
    # « ... vaut 1,03 x 1,03 fois son montant de base. »
    data = example("WF-DEV-0030-A#e6c446928b5b")
    rate = Decimal(cast("str", data["inflation_rate"]))
    factor = inflation_factor(
        rate, cast("int", data["reference_year"]), cast("int", data["consumption_year"])
    )
    assert factor == (1 + rate) * (1 + rate) == Decimal(cast("str", data["factor"]))
