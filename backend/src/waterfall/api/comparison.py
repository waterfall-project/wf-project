# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (WF-REV-0080).

``compareRevisions`` (US-1530), read by whoever may consult the estimate (``estimate.read``): two
marked revisions of the project, the tree of the compared one with the mark of each node, its
totals and its meta, and the differences of the amounts by nature and by subproject. It reads the
parameters of ``listNodes``, judged as it judges them (``node_reading``), and ``difference``, the
marks it keeps; each node is written as ``listNodes`` writes it, ``fields`` choosing what of it,
``difference`` and ``changes`` always returned.
"""

from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import NodeListMeta
from waterfall.api.evaluation import RequiresProject
from waterfall.api.nodes import CENT, node_body, node_reading, totals_body
from waterfall.api.queries import listed
from waterfall.core.estimate.interface import (
    AmountDelta,
    ComparedNode,
    ComparisonAsked,
    compare_revisions,
)
from waterfall.core.planning.interface import NodeFilters

router = APIRouter(tags=["revisions"])

CONSULT = "estimate.read"


class DifferenceAsked(StrEnum):
    """A mark the filter ``difference`` keeps (``NodeDifferenceFilter``)."""

    added = "added"
    removed = "removed"
    modified = "modified"


def _compared(node: ComparedNode, fields: frozenset[str] | None) -> dict[str, Any]:
    """Write a node of the comparison: as ``listNodes`` does, with its mark always."""
    return {
        **node_body(node.view, fields),
        "difference": node.difference,
        "changes": list(node.changes),
    }


def _delta(each: AmountDelta) -> dict[str, Any]:
    return {
        "dimension": each.dimension,
        "key": each.key,
        "label": each.label,
        "budgeted_delta": format(each.budgeted.quantize(CENT), "f"),
        "reestimated_delta": format(each.reestimated.quantize(CENT), "f"),
    }


def comparison_reading(
    from_revision_id: Annotated[UUID, Query()],
    to_revision_id: Annotated[UUID, Query()],
    asked: Annotated[tuple[NodeFilters, frozenset[str] | None], Depends(node_reading)],
    difference: Annotated[str | None, Query()] = None,
) -> tuple[ComparisonAsked, frozenset[str] | None]:
    """Read what ``compareRevisions`` asks: its revisions, the reading of the tree, the marks."""
    filters, fields = asked
    marks = listed("difference", difference, DifferenceAsked)
    kept = None if marks is None else tuple(each.value for each in marks)
    return ComparisonAsked(from_revision_id, to_revision_id, filters, kept), fields


@router.get(
    "/projects/{project_id}/revisions/comparison",
    operation_id="compareRevisions",
    dependencies=[Depends(RequiresProject(CONSULT))],
    response_model=None,
)
def get_comparison(
    project_id: UUID,
    asked: Annotated[tuple[ComparisonAsked, frozenset[str] | None], Depends(comparison_reading)],
    session: Transaction,
) -> dict[str, Any]:
    """Compare two marked revisions of the project, read as ``listNodes`` reads a structure."""
    comparison, fields = asked
    found = compare_revisions(session, project_id, comparison)
    meta = NodeListMeta.model_validate(
        {"summary_depth": found.summary_depth, "scheduled_at": found.scheduled_at}
    )
    return {
        "from_revision_id": str(found.from_revision_id),
        "to_revision_id": str(found.to_revision_id),
        "items": [_compared(each, fields) for each in found.items],
        "totals": totals_body(found.task_count, found.totals),
        "meta": meta.model_dump(mode="json"),
        "amount_deltas": [_delta(each) for each in found.amount_deltas],
    }
