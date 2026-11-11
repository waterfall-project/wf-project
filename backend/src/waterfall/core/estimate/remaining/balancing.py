# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The margins of the remaining to commit, private to the module: pure functions (US-1600).

The margin of the project, and of each subproject, is the budget of the reference minus the sum of
the actual cost and the remaining to commit, positive when some is left, negative beyond the budget
(WF-RAE-0020). A subproject without a reference has a budget of nought, the amount and not the
absence: its margin is then the opposite of what it has committed. The lines out of any subproject,
and the cost imputed to the project alone, form the ``unassigned`` set, always present, so that the
margins of the subprojects sum to that of the project; its key is the one of the interface of
``costs``, the only import of the module outside ``estimate``. Neither the base nor the clock is read: the
numeric examples run on it alone.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.costs.interface import UNASSIGNED
from waterfall.core.estimate.indicating import NO_TOTAL, AmountByKey, Figure
from waterfall.core.estimate.remaining.summing import NOUGHT
from waterfall.core.estimate.shares import distribution

if TYPE_CHECKING:
    from collections.abc import Mapping
    from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Balance:
    """The budget, the actual cost, the remaining and the margin of a subproject, by its key."""

    key: str
    budget: Decimal
    actual_cost: Decimal
    remaining: Decimal
    variance: Decimal
    is_over_budget: bool


def margin(budget: Decimal, actual_cost: Decimal, remaining: Decimal) -> Decimal:
    """Give the budget minus the sum of the actual cost and the remaining to commit."""
    return budget - (actual_cost + remaining)


def balances(
    budgets: Mapping[str, Decimal],
    actual_costs: Mapping[str, Decimal],
    remainings: Mapping[str, Decimal],
) -> tuple[Balance, ...]:
    """Give the balance of each key any of the three names, the subprojects by key, then the rest.

    ``unassigned`` is always given, last. A key a sum does not name has nought in it. A subproject
    with no line, no budget and no actual cost is named by none of them and does not appear.
    """
    keys = sorted({*budgets, *actual_costs, *remainings} - {UNASSIGNED})
    found: list[Balance] = []
    for key in [*keys, UNASSIGNED]:
        budget = budgets.get(key, NOUGHT)
        actual_cost = actual_costs.get(key, NOUGHT)
        remaining = remainings.get(key, NOUGHT)
        variance = margin(budget, actual_cost, remaining)
        found.append(Balance(key, budget, actual_cost, remaining, variance, variance < 0))
    return tuple(found)


def delta_to_reference(
    budgets: Mapping[str, Decimal] | None,
    actual_costs: Mapping[str, Decimal],
    remainings: Mapping[str, Decimal],
) -> Decimal | None:
    """Give the margin on the reference budget of the project; none without a reference."""
    if budgets is None:
        return None
    return margin(
        sum(budgets.values(), NOUGHT),
        sum(actual_costs.values(), NOUGHT),
        sum(remainings.values(), NOUGHT),
    )


def delta_to_previous(remaining: Decimal, previous: Decimal | None) -> Decimal | None:
    """Give the remaining to commit minus that of the review before; none without one."""
    return None if previous is None else remaining - previous


def distributed(
    amounts: Mapping[str, Decimal], labels: Mapping[str, str | None]
) -> tuple[AmountByKey, ...]:
    """Give each amount by its key, in the order of the keys, with its share of their total.

    The shares sum to one, the largest carrying the remainder of the roundings; on a total of nought
    none is computable (``no_total``).
    """
    keys = sorted(amounts)
    total = sum(amounts.values(), NOUGHT)
    if total == 0:
        shares = [Figure(None, NO_TOTAL) for _ in keys]
    else:
        shares = [Figure(each) for each in distribution([amounts[key] for key in keys])]
    return tuple(
        AmountByKey(key, labels.get(key), Figure(amounts[key]), share)
        for key, share in zip(keys, shares, strict=True)
    )
