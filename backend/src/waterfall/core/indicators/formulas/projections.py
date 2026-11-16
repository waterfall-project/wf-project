# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The variances and the three projections at completion (WF-IND-0050, WF-IND-0070, WF-IND-0080).

Pure, on exact amounts; each amount is rounded once, to the cent.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.indicators.formulas.computable import (
    NO_ACTUAL_COST,
    NO_EARNED_VALUE,
    Computable,
)
from waterfall.core.indicators.formulas.rounding import NOUGHT, round_amount

if TYPE_CHECKING:
    from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Projections:
    """The three projections at completion, and their variance to the reference budget."""

    at_budget: Decimal
    project_manager: Decimal
    at_observed_rate: Computable
    variance_at_budget: Decimal
    variance_project_manager: Decimal
    variance_at_observed_rate: Decimal | None


def cost_variance(earned_value: Decimal, actual_cost: Decimal) -> Decimal:
    """Give the earned value minus the actual cost: negative when it cost more (WF-IND-0070)."""
    return round_amount(earned_value - actual_cost)


def schedule_variance(earned_value: Decimal, planned_value: Decimal) -> Decimal:
    """Give the earned value minus the planned value: negative when behind (WF-IND-0080)."""
    return round_amount(earned_value - planned_value)


def _exact_at_observed_rate(
    reference_budget: Decimal, earned_value: Decimal, actual_cost: Decimal
) -> Decimal | str:
    # The budget over the cost index, written budget * cost / value: nothing is rounded twice.
    # Give the exact projection, or the reason it is not computable.
    if actual_cost == NOUGHT:
        return NO_ACTUAL_COST
    if earned_value == NOUGHT:
        return NO_EARNED_VALUE
    return reference_budget * actual_cost / earned_value


def projections(
    reference_budget: Decimal,
    earned_value: Decimal,
    actual_cost: Decimal,
    remaining: Decimal,
) -> Projections:
    """Give the projections: at budget, by the project manager, at the observed rate (WF-IND-0050).

    At budget, the actual cost plus what is left of the budget after the earned value; by the
    project manager, the actual cost plus the remaining to commit; at the observed rate, the budget
    over the cost index. The last is not computable before an actual cost (``no_actual_cost``) or,
    with one, before an earned value (``no_earned_value``), its variance then none; the two others
    are always computed. Each variance is taken on the exact projection, rounded once.
    """
    at_budget = actual_cost + reference_budget - earned_value
    project_manager = actual_cost + remaining
    at_observed_rate = _exact_at_observed_rate(reference_budget, earned_value, actual_cost)
    if isinstance(at_observed_rate, str):
        observed = Computable.not_computable(at_observed_rate)
        variance_at_observed_rate = None
    else:
        observed = Computable.of(round_amount(at_observed_rate))
        variance_at_observed_rate = round_amount(at_observed_rate - reference_budget)
    return Projections(
        at_budget=round_amount(at_budget),
        project_manager=round_amount(project_manager),
        at_observed_rate=observed,
        variance_at_budget=round_amount(at_budget - reference_budget),
        variance_project_manager=round_amount(project_manager - reference_budget),
        variance_at_observed_rate=variance_at_observed_rate,
    )
