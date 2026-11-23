# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The ratios of sums: the indices and the projections of the portfolio, the shares (WF-PTF-0020).

Pure. A portfolio index is the ratio of the sums of the projects, never the mean of their indices:
the formulas are those of the indicators (EP-10), applied to the sums, none written again. Shares
are rounded as the contract rounds a share (README, "A share…"), those of a distribution so that
they sum to one.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.estimate.interface import distribution, share_of
from waterfall.core.indicators.interface import (
    Computable,
    Projections,
    cost_index,
    cost_variance,
    projections,
    schedule_index,
    schedule_variance,
)
from waterfall.core.portfolio.aggregation.sums import total_of

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

NOUGHT = Decimal(0)
NO_TOTAL = "no_total"


@dataclass(frozen=True, slots=True)
class ProjectFigures:
    """What a project in progress gives to the sums of the indices: its rounded amounts."""

    reference_budget: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    planned_value: Decimal
    remaining: Decimal


@dataclass(frozen=True, slots=True)
class Aggregate:
    """The indices and the projections of the sums of the projects."""

    reference_budget: Decimal
    cost_index: Computable
    schedule_index: Computable
    cost_variance: Decimal
    schedule_variance: Decimal
    projections: Projections


def aggregate(figures: Iterable[ProjectFigures]) -> Aggregate:
    """Give the indices of the sums of the figures of the projects, and their projections.

    Each index is the ratio of two sums, to four decimals, not computable when the sum it divides
    by is nought (WF-PTF-0020); the variances are the variances of the sums, the sums of the
    projections at budget and of the project manager the projections of the sums, and the one at
    the observed rate the aggregated budget over the aggregated cost index, so that two projects
    of budget 1 000, of earned value 400 and 500 and of actual cost 500 and 500 give 2 222 and not
    2 250 (WF-PTF-0070).
    """
    held = list(figures)
    budget = total_of(each.reference_budget for each in held)
    earned = total_of(each.earned_value for each in held)
    actual = total_of(each.actual_cost for each in held)
    planned = total_of(each.planned_value for each in held)
    remaining = total_of(each.remaining for each in held)
    return Aggregate(
        reference_budget=budget,
        cost_index=cost_index(earned, actual),
        schedule_index=schedule_index(earned, planned),
        cost_variance=cost_variance(earned, actual),
        schedule_variance=schedule_variance(earned, planned),
        projections=projections(budget, earned, actual, remaining),
    )


def ratio_of(numerator: Decimal, denominator: Decimal, reason: str) -> Computable:
    """Give a ratio to four decimals, or the reason it is not computable when it divides by none."""
    if denominator == NOUGHT:
        return Computable.not_computable(reason)
    return Computable.of(share_of(numerator, denominator))


def shares_of(amounts: Sequence[Decimal]) -> list[Computable]:
    """Give the share of each amount in their total, the shares summing to one exactly.

    The remainder of the roundings is carried by the largest amount, the first on a tie, as the
    distribution of a project does (WF-DEV-0060); a total of nought gives no share, ``no_total``.
    """
    if sum(amounts, NOUGHT) == NOUGHT:
        return [Computable.not_computable(NO_TOTAL) for _ in amounts]
    return [Computable.of(share) for share in distribution(amounts)]
