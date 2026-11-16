# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The progress and the indices: ratios of two amounts, each not computable when it divides by none.

Pure, on exact amounts; each ratio is rounded once, to four decimals (WF-IND-0040 to WF-IND-0080).
"""

from typing import TYPE_CHECKING

from waterfall.core.indicator_settings.interface import index_zone
from waterfall.core.indicators.formulas.computable import (
    NO_ACTUAL_COST,
    NO_ACTUAL_OR_REMAINING,
    NO_PLANNED_VALUE,
    NO_REFERENCE_BUDGET,
    Computable,
)
from waterfall.core.indicators.formulas.rounding import NOUGHT, round_ratio

if TYPE_CHECKING:
    from decimal import Decimal


def _ratio(numerator: Decimal, denominator: Decimal, reason: str) -> Computable:
    if denominator == NOUGHT:
        return Computable.not_computable(reason)
    return Computable.of(round_ratio(numerator / denominator))


def financial_progress(actual_cost: Decimal, remaining: Decimal) -> Computable:
    """Give the actual cost over the final spending, actual cost plus remaining (WF-IND-0040)."""
    return _ratio(actual_cost, actual_cost + remaining, NO_ACTUAL_OR_REMAINING)


def budget_consumption(actual_cost: Decimal, reference_budget: Decimal) -> Computable:
    """Give the actual cost over the reference budget (WF-IND-0040)."""
    return _ratio(actual_cost, reference_budget, NO_REFERENCE_BUDGET)


def physical_progress(earned_value: Decimal, reference_budget: Decimal) -> Computable:
    """Give the earned value over the reference budget (WF-IND-0060)."""
    return _ratio(earned_value, reference_budget, NO_REFERENCE_BUDGET)


def cost_index(earned_value: Decimal, actual_cost: Decimal) -> Computable:
    """Give the earned value over the actual cost (WF-IND-0070)."""
    return _ratio(earned_value, actual_cost, NO_ACTUAL_COST)


def schedule_index(earned_value: Decimal, planned_value: Decimal) -> Computable:
    """Give the earned value over the planned value (WF-IND-0080)."""
    return _ratio(earned_value, planned_value, NO_PLANNED_VALUE)


def zone_of(index: Computable, watch: Decimal, alert: Decimal) -> str | None:
    """Give the zone of an index on the thresholds read now, none when it is not computed.

    The zone is classed on the value shown, rounded (WF-REF-0170).
    """
    if index.value is None:
        return None
    return index_zone(index.value, watch, alert)
