# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The weight of a project in a sum, and what an offer weighs (WF-PTF-0020, WF-PRJ-0090).

Pure. A project in progress or completed counts for all of what it holds; an offer, for its win
probability — a ratio, ``0.4`` for 40 % —, which the raw pipeline and the risks never apply. The
weighted part is rounded once, as EP-10 rounds what it keeps: an amount to the cent, a half away
from nought; the hours to the hundredth, a half to the nearest even.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import HOURS, MONEY
from waterfall.core.portfolio.aggregation.sums import sum_by_key

if TYPE_CHECKING:
    from collections.abc import Iterable

    from waterfall.core.projects.interface import ProjectState

NOUGHT = Decimal(0)
ONE = Decimal(1)
WHOLE_STATES: frozenset[str] = frozenset({"in_progress", "completed"})
PRICING = "pricing"
ZERO_HOURS = Decimal("0.00")


def weight_of(state: ProjectState, win_probability: Decimal) -> Decimal:
    """Give the weight of a project: one in progress or completed, its probability in pricing.

    Another state — created, lost, abandoned — weighs nothing: no view counts it.
    """
    if state in WHOLE_STATES:
        return ONE
    if state == PRICING:
        return win_probability
    return NOUGHT


def weighted_amount(amount: Decimal, weight: Decimal) -> Decimal:
    """Give the part of an amount a weight keeps, to the cent, a half away from nought."""
    return MONEY.of(amount * weight)


def weighted_hours(hours: Decimal, weight: Decimal) -> Decimal:
    """Give the part of some hours a weight keeps, to the hundredth, a half to the nearest even."""
    return HOURS.of(hours * weight)


def included_hours(hours: Decimal, weight: Decimal, *, included: bool) -> Decimal:
    """Give the hours an offer adds to the workload: its weighted hours if included, else nought."""
    return weighted_hours(hours, weight) if included else ZERO_HOURS


@dataclass(frozen=True, slots=True)
class CostLine:
    """A line of the quote of an offer: its nature, its amount, whether it is a risk provision."""

    nature: str
    amount: Decimal
    provision: bool = False


def sum_by_nature(
    lines: Iterable[CostLine], weight: Decimal, *, with_provisions: bool
) -> dict[str, Decimal]:
    """Give the weighted amount of the lines of a quote by nature, in the order natures appear.

    The budget document holds no provision line: ``with_provisions`` false leaves them out, the
    remaining to commit keeps them (WF-PTF-0080). Each line is weighted and rounded once, then
    summed.
    """
    return sum_by_key(
        {each.nature: weighted_amount(each.amount, weight)}
        for each in lines
        if with_provisions or not each.provision
    )
