# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and of the remaining to commit as the contract writes them.

``estimate_document`` (``EstimateIndicators``, EP-07) and ``remaining_document``
(``RemainingIndicators``, EP-09) write what the estimate computes: the API answers them for the
current revision, and a marking keeps them for the revision it marks (EP-10, "La conservation au
marquage"), so that the two never part. An amount is written to the cent, as ``Money``; a share
without its trailing zeros, as ``Decimal``; an instant in universal time. A document is computed
``is_stored`` false: the marking says what it keeps (``storing``).

Moved here from the routes of EP-07 and EP-09 by US-1670/L1, which keeps them.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

from waterfall.core.estimate.interface import shown
from waterfall.core.indicators.shaping import instant

if TYPE_CHECKING:
    from waterfall.core.estimate.interface import (
        AmountByKey,
        CalculationContext,
        Coverage,
        EstimateIndicators,
        Figure,
        MissingRate,
        RemainingIndicators,
        SubprojectBalance,
    )
    from waterfall.core.indicators.interface.documents import Document

# An amount ventilated of the remaining is always valued: the remaining needs no rate that could be
# missing.
NOUGHT = Decimal("0.00")


def _money(amount: Decimal) -> str:
    return format(amount, "f")


def missing_rate_document(missing: MissingRate) -> dict[str, Any]:
    """Give a category without a rate for its year as the contract writes it (``MissingRate``)."""
    return {
        "cost_category_id": str(missing.cost_category_id),
        "label": missing.label,
        "year": missing.year,
    }


def _computable(figure: Figure, *, share: bool = False) -> dict[str, Any]:
    """Give a figure in the envelope of the contract: its value, or its reason and what it names."""
    value = None
    if figure.value is not None:
        value = shown(figure.value) if share else _money(figure.value)
    envelope: dict[str, Any] = {
        "is_computable": figure.value is not None,
        "value": value,
        "reason": figure.reason,
    }
    if figure.missing:
        envelope["params"] = {
            "missing_rates": [missing_rate_document(each) for each in figure.missing]
        }
    return envelope


def _estimate_by_key(each: AmountByKey) -> dict[str, Any]:
    return {
        "key": each.key,
        "label": each.label,
        "amount": _computable(each.amount),
        "share": _computable(each.share, share=True),
    }


def estimate_document(found: EstimateIndicators) -> Document:
    """Write the indicators of an estimate as the contract writes them, computed."""
    return {
        "context": {
            "revision_id": str(found.revision_id),
            "revision_status": "marked" if found.marked else "draft",
            "computed_at": instant(found.computed_at),
            "scope": found.scope,
            "is_stored": False,
        },
        "total": _computable(found.total),
        "by_cost_type": [_estimate_by_key(each) for each in found.by_cost_type],
        "by_subproject": [_estimate_by_key(each) for each in found.by_subproject],
        "by_work_package": [_estimate_by_key(each) for each in found.by_work_package],
        "provisions_identified": _money(found.provisions_identified),
        "delta_to_reference": (
            None if found.delta_to_reference is None else _computable(found.delta_to_reference)
        ),
        "delta_to_previous_revision": (
            None
            if found.delta_to_previous_revision is None
            else _computable(found.delta_to_previous_revision)
        ),
    }


def _share(figure: Figure) -> dict[str, Any]:
    """Give a share in the envelope of the contract: its value, or the reason it has none."""
    return {
        "is_computable": figure.value is not None,
        "value": None if figure.value is None else shown(figure.value),
        "reason": figure.reason,
    }


def _remaining_by_key(each: AmountByKey) -> dict[str, Any]:
    return {
        "key": each.key,
        "label": each.label,
        "amount": _money(NOUGHT if each.amount.value is None else each.amount.value),
        "share": _share(each.share),
    }


def _balance(each: SubprojectBalance) -> dict[str, Any]:
    return {
        "key": each.key,
        **({} if each.label is None else {"label": each.label}),
        "budget": _money(each.budget),
        "actual_cost": _money(each.actual_cost),
        "remaining": _money(each.remaining),
        "variance": _money(each.variance),
        "is_over_budget": each.is_over_budget,
        "zone": each.zone,
    }


def _context(context: CalculationContext) -> dict[str, Any]:
    return {
        "revision_id": str(context.revision_id),
        "revision_status": context.revision_status,
        "computed_at": instant(context.computed_at),
        "scope": str(context.scope),
        "is_stored": context.is_stored,
    }


def _coverage(coverage: Coverage) -> dict[str, Any]:
    """Write the coverage of the risks as the contract writes it (``RiskCoverageTotals``)."""
    return {
        "reserve": _money(coverage.reserve),
        "remaining_provisions": _money(coverage.remaining_provisions),
        "occurred_cost": _money(coverage.occurred_cost),
        "occurred_reestimated": _money(coverage.occurred_reestimated),
        "coverage_variance": _money(coverage.coverage_variance),
    }


def risk_coverage_document(context: CalculationContext, coverage: Coverage) -> Document:
    """Write the coverage of the risks of a revision as the contract writes it (``RiskCoverage``).

    The totals the remaining to commit gives for its ``coverage``, under their context: the two
    never part (WF-RAE-0020).
    """
    return {"context": _context(context), **_coverage(coverage)}


def remaining_document(found: RemainingIndicators) -> Document:
    """Write the indicators of the remaining to commit as the contract writes them."""
    return {
        "context": _context(found.context),
        "total": _money(found.total),
        "by_cost_type": [_remaining_by_key(each) for each in found.by_cost_type],
        "by_subproject": [_balance(each) for each in found.by_subproject],
        "coverage": _coverage(found.coverage),
        "delta_to_reference": (
            None if found.delta_to_reference is None else _money(found.delta_to_reference)
        ),
        "delta_to_previous_revision": (
            None
            if found.delta_to_previous_revision is None
            else _money(found.delta_to_previous_revision)
        ),
    }
