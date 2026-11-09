# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of an estimate and the rates it lacks (WF-DEV-0060, WF-DEV-0010).

``getEstimateIndicators`` and ``getMissingRates`` (US-1510), read by whoever may consult the
estimate (``estimate.read``): the revision named, else the current one, else the last one marked;
the scope of the indicators, the project, a subproject or the set out of any subproject. An amount
that a missing rate prevents from being computed is served in the envelope the contract reads
(``ComputableMoney``, ``Computable``), the categories and the year named.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.core.estimate.interface import (
    AmountByKey,
    EstimateIndicators,
    Figure,
    IndicatorsAsked,
    MissingRate,
    estimate_indicators,
    missing_rates,
)
from waterfall.core.estimate.shares import shown
from waterfall.platform.database import utc_now

router = APIRouter(tags=["estimate"])

CONSULT = "estimate.read"
INDICATORS = "/projects/{project_id}/estimate-indicators"


def _missing(missing: MissingRate) -> dict[str, Any]:
    return {
        "cost_category_id": str(missing.cost_category_id),
        "label": missing.label,
        "year": missing.year,
    }


def _computable(figure: Figure, *, share: bool = False) -> dict[str, Any]:
    """Give a figure in the envelope of the contract: its value, or its reason and what it names."""
    value = None
    if figure.value is not None:
        value = shown(figure.value) if share else format(figure.value, "f")
    envelope: dict[str, Any] = {
        "is_computable": figure.value is not None,
        "value": value,
        "reason": figure.reason,
    }
    if figure.missing:
        envelope["params"] = {"missing_rates": [_missing(each) for each in figure.missing]}
    return envelope


def _by_key(each: AmountByKey) -> dict[str, Any]:
    return {
        "key": each.key,
        "label": each.label,
        "amount": _computable(each.amount),
        "share": _computable(each.share, share=True),
    }


def indicators_body(found: EstimateIndicators) -> dict[str, Any]:
    """Give the indicators of an estimate as the contract writes them."""
    return {
        "context": {
            "revision_id": str(found.revision_id),
            "revision_status": "marked" if found.marked else "draft",
            "computed_at": found.computed_at,
            "scope": found.scope,
            "is_stored": False,
        },
        "total": _computable(found.total),
        "by_cost_type": [_by_key(each) for each in found.by_cost_type],
        "by_subproject": [_by_key(each) for each in found.by_subproject],
        "by_work_package": [_by_key(each) for each in found.by_work_package],
        "provisions_identified": format(found.provisions_identified, "f"),
        "delta_to_reference": (
            None if found.delta_to_reference is None else _computable(found.delta_to_reference)
        ),
        "delta_to_previous_revision": (
            None
            if found.delta_to_previous_revision is None
            else _computable(found.delta_to_previous_revision)
        ),
    }


@router.get(
    INDICATORS,
    operation_id="getEstimateIndicators",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_indicators(
    project_id: UUID,
    session: Transaction,
    revision_id: Annotated[UUID | None, Query()] = None,
    scope: Annotated[str, Query()] = "project",
) -> dict[str, Any]:
    """Give the total of an estimate, its ventilations and its differences, in one reading."""
    asked = IndicatorsAsked(revision_id, scope, utc_now())
    return indicators_body(estimate_indicators(session, project_id, asked))


@router.get(
    f"{INDICATORS}/missing-rates",
    operation_id="getMissingRates",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_missing_rates(
    project_id: UUID, session: Transaction, revision_id: Annotated[UUID | None, Query()] = None
) -> list[dict[str, Any]]:
    """Give the categories of labour an estimate employs without a rate for its year."""
    return [_missing(each) for each in missing_rates(session, project_id, revision_id)]
