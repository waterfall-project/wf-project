# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The indicators of the remaining to commit of a project (WF-RAE-0020).

``getRemainingIndicators`` (US-1600), under ``remaining.read``: the revision named, else the
current one, else the last one marked. The server classifies the overrun of each subproject
(``zone``); the front deduces nothing from the margins.
"""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.evaluation import RequiresProject
from waterfall.core.estimate.interface import (
    AmountByKey,
    Figure,
    RemainingIndicators,
    remaining_indicators,
)
from waterfall.core.estimate.shares import shown
from waterfall.core.revisions.interface import read_revision_for
from waterfall.platform.database import utc_now

router = APIRouter(tags=["remaining"])

READ = "remaining.read"
# An amount ventilated is always valued: the remaining needs no rate that could be missing.
NOUGHT = Decimal("0.00")


def _money(amount: Decimal) -> str:
    return format(amount, "f")


def _share(figure: Figure) -> dict[str, Any]:
    """Give a share in the envelope of the contract: its value, or the reason it has none."""
    return {
        "is_computable": figure.value is not None,
        "value": None if figure.value is None else shown(figure.value),
        "reason": figure.reason,
    }


def _by_key(each: AmountByKey) -> dict[str, Any]:
    return {
        "key": each.key,
        "label": each.label,
        "amount": _money(NOUGHT if each.amount.value is None else each.amount.value),
        "share": _share(each.share),
    }


def indicators_body(found: RemainingIndicators) -> dict[str, Any]:
    """Give the indicators of the remaining to commit as the contract writes them."""
    context = found.context
    return {
        "context": {
            "revision_id": str(context.revision_id),
            "revision_status": context.revision_status,
            "computed_at": context.computed_at,
            "scope": context.scope,
            "is_stored": context.is_stored,
        },
        "total": _money(found.total),
        "by_cost_type": [_by_key(each) for each in found.by_cost_type],
        "by_subproject": [
            {
                "key": each.key,
                **({} if each.label is None else {"label": each.label}),
                "budget": _money(each.budget),
                "actual_cost": _money(each.actual_cost),
                "remaining": _money(each.remaining),
                "variance": _money(each.variance),
                "is_over_budget": each.is_over_budget,
                "zone": each.zone,
            }
            for each in found.by_subproject
        ],
        "coverage": {
            "reserve": _money(found.coverage.reserve),
            "remaining_provisions": _money(found.coverage.remaining_provisions),
            "occurred_cost": _money(found.coverage.occurred_cost),
            "occurred_reestimated": _money(found.coverage.occurred_reestimated),
            "coverage_variance": _money(found.coverage.coverage_variance),
        },
        "delta_to_reference": (
            None if found.delta_to_reference is None else _money(found.delta_to_reference)
        ),
        "delta_to_previous_revision": (
            None
            if found.delta_to_previous_revision is None
            else _money(found.delta_to_previous_revision)
        ),
    }


@router.get(
    "/projects/{project_id}/remaining-indicators",
    operation_id="getRemainingIndicators",
    dependencies=[Depends(RequiresProject(READ))],
    response_model=None,
)
def get_remaining_indicators(
    project_id: UUID, session: Transaction, revision_id: Annotated[UUID | None, Query()] = None
) -> dict[str, Any]:
    """Give the total of the remaining to commit, its ventilations and its margins at once."""
    read = read_revision_for(session, project_id, revision_id)
    return indicators_body(remaining_indicators(session, project_id, read.revision_id, utc_now()))
