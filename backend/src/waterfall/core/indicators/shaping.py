# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of a project as the contract writes them (``ProjectIndicators``).

A document of the day carries no zone: the same document is answered, kept at a marking and cached
(EP-10, "Ce que le cadrage décide"), and its indices are classified at each reading on the
thresholds of that day (``classified``, WF-REF-0130, WF-REF-0170). The amounts are written to the
cent, as ``Money``; the ratios and the indices without their trailing zeros, as ``Decimal``.
"""

from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from waterfall.core.cost_settings.interface import plain_decimal
from waterfall.core.indicator_settings.interface import index_zone

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from waterfall.core.cost_settings.interface import IndexThresholds
    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.formulas import Computable, Index, Indicators
    from waterfall.core.indicators.interface.documents import Document


@dataclass(frozen=True, slots=True)
class Context:
    """The context of a computation (``CalculationContext``).

    ``revision_status`` is ``draft`` for the current revision, ``marked`` otherwise.
    """

    revision_id: UUID
    revision_status: str
    computed_at: datetime
    scope: CostScope
    is_stored: bool


def money(amount: Decimal) -> str:
    """Write an amount to the cent, as ``Money`` of the contract."""
    return format(amount, "f")


def instant(at: datetime) -> str:
    """Give an instant as the contract writes it, in universal time."""
    return at.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _computable(figure: Computable, *, in_cents: bool = False) -> dict[str, Any]:
    value = figure.value
    shown = None if value is None else (money(value) if in_cents else plain_decimal(value))
    return {"is_computable": value is not None, "value": shown, "reason": figure.reason}


def _index(index: Index) -> dict[str, Any]:
    return {"value": _computable(index.value), "zone": index.zone}


def context_document(context: Context) -> Document:
    """Write a context as the contract writes it (``CalculationContext``)."""
    return {
        "revision_id": str(context.revision_id),
        "revision_status": context.revision_status,
        "computed_at": instant(context.computed_at),
        "scope": str(context.scope),
        "is_stored": context.is_stored,
    }


def indicators_document(found: Indicators, context: Context) -> Document:
    """Write the indicators of a scope and their context as the contract writes them."""
    projections = found.projections
    observed = projections.variance_at_observed_rate
    return {
        "context": context_document(context),
        "reference_budget": money(found.reference_budget),
        "planned_value": money(found.planned_value),
        "earned_value": money(found.earned_value),
        "actual_cost": money(found.actual_cost),
        "remaining": money(found.remaining),
        "financial_progress": _computable(found.financial_progress),
        "budget_consumption": _computable(found.budget_consumption),
        "physical_progress": _computable(found.physical_progress),
        "cost_index": _index(found.cost_index),
        "schedule_index": _index(found.schedule_index),
        "cost_variance": money(found.cost_variance),
        "schedule_variance": money(found.schedule_variance),
        "projections": {
            "at_budget": money(projections.at_budget),
            "project_manager": money(projections.project_manager),
            "at_observed_rate": _computable(projections.at_observed_rate, in_cents=True),
            "variance_at_budget": money(projections.variance_at_budget),
            "variance_project_manager": money(projections.variance_project_manager),
            "variance_at_observed_rate": None if observed is None else money(observed),
        },
    }


def _zone(index: dict[str, Any], watch: Decimal, alert: Decimal) -> dict[str, Any]:
    value = index["value"]["value"]
    zone = None if value is None else index_zone(Decimal(value), watch, alert)
    return {**index, "zone": zone}


def classified(document: Document, thresholds: IndexThresholds) -> Document:
    """Give a document of indicators with the zone of each index on the thresholds given.

    Classified on the value shown (WF-REF-0170); none for an index that is not computed.
    """
    return {
        **document,
        "cost_index": _zone(document["cost_index"], thresholds.cost_watch, thresholds.cost_alert),
        "schedule_index": _zone(
            document["schedule_index"], thresholds.schedule_watch, thresholds.schedule_alert
        ),
    }
