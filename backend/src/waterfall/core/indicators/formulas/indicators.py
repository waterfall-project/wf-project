# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of one set from its five amounts, whole and pure (WF-IND-0040 to WF-IND-0080).

The five amounts of a set — reference budget, planned value, earned value, actual cost, remaining
to commit — in; the progress, the indices with their zone, the variances and the projections out,
each rounded once. The sets (project, subprojects, unassigned) are made of the callers' lines.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from waterfall.core.indicators.formulas.projections import (
    cost_variance,
    projections,
    schedule_variance,
)
from waterfall.core.indicators.formulas.ratios import (
    budget_consumption,
    cost_index,
    financial_progress,
    physical_progress,
    schedule_index,
    zone_of,
)
from waterfall.core.indicators.formulas.rounding import round_amount

if TYPE_CHECKING:
    from decimal import Decimal

    from waterfall.core.indicators.formulas.computable import Computable
    from waterfall.core.indicators.formulas.projections import Projections


@dataclass(frozen=True, slots=True)
class Amounts:
    """The five amounts of a set, as they were read, not yet rounded."""

    reference_budget: Decimal
    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    remaining: Decimal


@dataclass(frozen=True, slots=True)
class Thresholds:
    """The watch and alert thresholds of the two indices (``IndexThresholds`` of the reference)."""

    cost_watch: Decimal
    cost_alert: Decimal
    schedule_watch: Decimal
    schedule_alert: Decimal


@dataclass(frozen=True, slots=True)
class Index:
    """An index and its zone, none when the index is not computed."""

    value: Computable
    zone: str | None


@dataclass(frozen=True, slots=True)
class Indicators:
    """What a set shows: its amounts, progress, indices, variances and projections."""

    reference_budget: Decimal
    planned_value: Decimal
    earned_value: Decimal
    actual_cost: Decimal
    remaining: Decimal
    financial_progress: Computable
    budget_consumption: Computable
    physical_progress: Computable
    cost_index: Index
    schedule_index: Index
    cost_variance: Decimal
    schedule_variance: Decimal
    projections: Projections


def indicators_of(amounts: Amounts, thresholds: Thresholds | None) -> Indicators:
    """Compute the indicators of a set from its amounts, the zones on the thresholds given.

    Without thresholds, the zones are none: a document of the day, kept or cached, carries none, a
    reading classifying its indices on the thresholds of its own day (EP-10, "Ce que le cadrage
    décide").
    """
    budget, planned = amounts.reference_budget, amounts.planned_value
    earned, actual, remaining = amounts.earned_value, amounts.actual_cost, amounts.remaining
    cost = cost_index(earned, actual)
    schedule = schedule_index(earned, planned)
    cost_zone = schedule_zone = None
    if thresholds is not None:
        cost_zone = zone_of(cost, thresholds.cost_watch, thresholds.cost_alert)
        schedule_zone = zone_of(schedule, thresholds.schedule_watch, thresholds.schedule_alert)
    return Indicators(
        reference_budget=round_amount(budget),
        planned_value=round_amount(planned),
        earned_value=round_amount(earned),
        actual_cost=round_amount(actual),
        remaining=round_amount(remaining),
        financial_progress=financial_progress(actual, remaining),
        budget_consumption=budget_consumption(actual, budget),
        physical_progress=physical_progress(earned, budget),
        cost_index=Index(cost, cost_zone),
        schedule_index=Index(schedule, schedule_zone),
        cost_variance=cost_variance(earned, actual),
        schedule_variance=schedule_variance(earned, planned),
        projections=projections(budget, earned, actual, remaining),
    )
