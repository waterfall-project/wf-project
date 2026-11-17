# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (WF-REV-0080).

``compareRevisions`` (US-1530), read by whoever may consult the estimate (``estimate.read``): two
marked revisions of the project, the tree of the compared one with the mark of each node, its
totals and its meta, and the differences of the amounts by nature and by subproject. It reads the
parameters of ``listNodes``, judged as it judges them (``node_reading``), and ``difference``, the
marks it keeps; each node is written as ``listNodes`` writes it, ``fields`` choosing what of it,
``difference`` and ``changes`` always returned.

A comparison no filter restricts — ``difference`` and ``fields`` asked or not — reads the readings
kept of the two structures (EP-26, "La comparaison", US-2270), made and kept if they are not: the
union reads of each node of their documents what it unites and marks by (``UnitedNode``), its
identifiers left as texts, and each node returned is its node of the document, placed, renamed and
marked as the union says (``PlacedNode``); the totals and the meta are those of the document of the
compared structure. The body is the same, to the byte, as from the rows. A filtered one reads the
rows (#3168).
"""

from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from waterfall.api.authentication import Transaction
from waterfall.api.contract.models import NodeListMeta
from waterfall.api.evaluation import RequiresProject
from waterfall.api.nodes import (
    CENT,
    kept_body,
    node_body,
    node_reading,
    projected,
    read_body,
    totals_body,
)
from waterfall.api.queries import listed
from waterfall.core.estimate.interface import (
    AmountDelta,
    ComparedNode,
    Comparison,
    ComparisonAsked,
    LineAmounts,
    UnitedNode,
    compare_revisions,
    compare_united,
    compared_places,
    line_compared,
    task_compared,
)
from waterfall.core.planning.interface import NodeFilters

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from waterfall.core.estimate.interface import Compared, PlacedNode

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


def _identifier(ids: dict[str, UUID], text: str) -> UUID:
    """Read an identifier written in a document, once for all the lines that name it."""
    found = ids.get(text)
    if found is None:
        found = ids[text] = UUID(text)
    return found


def _united(item: dict[str, Any], ids: dict[str, UUID]) -> UnitedNode[str]:
    """Give what the union reads of a node of a document kept: as its rows give it, in texts.

    ``ids`` the identifiers of the categories and the subprojects already read, which many lines
    share.
    """
    task, line = item["task"], item["estimate_line"]
    compared: Compared = ()
    amounts = None
    if task is not None:
        compared = task_compared(
            (task["start"], task["finish"]), task["duration"], task["progress"]
        )
    elif line is not None:
        category, subproject = line["cost_category_id"], line["subproject_id"]
        compared = line_compared(
            line["budgeted_amount"],
            line["reestimated_amount"],
            line["payment_delay_days"],
            subproject,
            category,
        )
        amounts = LineAmounts(
            _identifier(ids, category),
            None if subproject is None else _identifier(ids, subproject),
            Decimal(line["budgeted_amount"]),
            Decimal(line["reestimated_amount"]),
        )
    return UnitedNode(
        item["node_id"],
        item["lineage_id"],
        item["kind"],
        item["parent_id"],
        tuple(each["predecessor_node_id"] for each in item["predecessors"]),
        compared,
        amounts,
    )


def _placed(
    item: dict[str, Any], placed: PlacedNode[str], fields: frozenset[str] | None
) -> dict[str, Any]:
    """Write a node of a document kept as the union returns it: placed, renamed, marked."""
    item["parent_id"] = placed.parent_id
    item["row_number"] = placed.row_number
    item["level"] = placed.level
    item["position"] = placed.position
    for each, renamed in zip(item["predecessors"], placed.predecessors, strict=False):
        if renamed is not None:
            each["predecessor_node_id"], each["predecessor_row_number"] = renamed
    if placed.removed:
        item["editable_fields"] = []
    written = item if fields is None else projected(item, fields)
    written["difference"] = placed.difference
    written["changes"] = list(placed.changes)
    return written


def kept_comparison(
    session: Session, project_id: UUID, asked: ComparisonAsked, fields: frozenset[str] | None
) -> dict[str, Any] | None:
    """Compare two marked revisions from the readings kept of their structures (US-2270).

    The body of ``compareRevisions`` no filter restricts; none when a structure has no reading
    kept, which a marked revision always has, made here if it is not. The revisions are judged
    first (404, then 409).
    """
    reads, places = compared_places(session, project_id, asked)
    base, compared = (kept_body(session, place) for place in places)
    if base is None or compared is None:
        return None
    ids: dict[str, UUID] = {}
    found = compare_united(
        session,
        project_id,
        reads,
        (
            [_united(each, ids) for each in base["items"]],
            [_united(each, ids) for each in compared["items"]],
        ),
        asked.differences,
    )
    nodes = {each["node_id"]: each for each in (*base["items"], *compared["items"])}
    return {
        "from_revision_id": str(asked.from_revision_id),
        "to_revision_id": str(asked.to_revision_id),
        "items": [_placed(nodes[each.node_id], each, fields) for each in found.items],
        "totals": compared["totals"],
        "meta": compared["meta"],
        "amount_deltas": [_delta(each) for each in found.amount_deltas],
    }


def comparison_body(found: Comparison, fields: frozenset[str] | None) -> dict[str, Any]:
    """Write a comparison read from the rows of the two structures (``RevisionComparison``)."""
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
) -> JSONResponse:
    """Compare two marked revisions of the project, read as ``listNodes`` reads a structure."""
    comparison, fields = asked
    if comparison.filters == NodeFilters():
        kept = kept_comparison(session, project_id, comparison, fields)
        if kept is not None:
            return read_body(kept)
    return read_body(comparison_body(compare_revisions(session, project_id, comparison), fields))
