# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric example of the indicators of the remaining to commit (US-1600), no database.

From its fixture under ``fixtures/remaining``: the margin on the reference budget and the difference
with the review before, as ``getRemainingIndicators`` computes them (``remaining.balancing``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.remaining.balancing import (
    UNASSIGNED,
    balances,
    delta_to_previous,
    delta_to_reference,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]


def _decimal(data: Example, name: str) -> Decimal:
    return Decimal(cast("str", data[name]))


@pytest.mark.requirement("WF-RAE-0020-A")
def test_a_project_of_budget_1000_cost_500_remaining_550_has_a_margin_of_minus_50_and_a_drop_of_50(
    example: Callable[[str], Example],
) -> None:
    # « Sur un projet de budget 1 000, de coût réel 500 et de reste à engager 550, la marge sur le
    # budget vaut - 50 ; un reste à engager passé de 600 à 550 depuis la revue précédente donne un
    # écart de - 50. »
    data = example("WF-RAE-0020-A#05bb86431330")
    budgets = {UNASSIGNED: _decimal(data, "budget")}
    actual_costs = {UNASSIGNED: _decimal(data, "actual_cost")}
    remainings = {UNASSIGNED: _decimal(data, "remaining")}
    assert delta_to_reference(budgets, actual_costs, remainings) == _decimal(
        data, "delta_to_reference"
    )
    assert delta_to_previous(
        _decimal(data, "remaining"), _decimal(data, "previous_remaining")
    ) == _decimal(data, "delta_to_previous_revision")
    # The only set is over its budget by the margin, and the project's margin is its margin.
    [only] = balances(budgets, actual_costs, remainings)
    assert (only.variance, only.is_over_budget) == (Decimal(-50), True)
