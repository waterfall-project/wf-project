# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of two revisions of a project (WF-REV-0080).

``compareRevisions`` (US-1530; US-2320), read by whoever may consult one of the three grids
(``planning.read``, ``estimate.read`` or ``remaining.read``), which read it on the main structure:
the revision read, current or marked, compared with a marked base, the tree of the revision read
with the mark of each node and what its base carried of what differs, its totals and its meta, and
the differences of the amounts by nature and by subproject, and the totals of the base and their
difference (US-2340, US-2350). It reads the parameters of ``listNodes``, judged as it judges them
(``node_reading``), ``difference``, the marks it keeps, and ``include_differences``, the nodes in
difference a filter of progress leaves out; each node is written as ``listNodes`` writes it,
``fields`` choosing what of it, ``difference``, ``changes``, ``base`` and ``deltas`` always
returned, ``base`` and ``deltas`` reduced to the fields read as the node is: the core does not
know ``fields``, and judges a node on every value it carries.

A comparison no filter restricts — ``difference`` and ``fields`` asked or not — reads the reading
kept of the base (EP-26, "La comparaison", US-2270), made and kept if it is not, and that of the
revision read when it is marked, its columns when it is current (US-2220), nothing being kept of a
current one: the union reads of each node of their documents what it unites and marks by
(``UnitedNode``), its identifiers left as texts, and each node returned is its node of the
document, placed, renamed, marked and given its base as the union says (``PlacedNode``); the
totals and the meta are those of the document of the revision read. The body is the same, to the
byte, as from the rows. A filtered one reads the rows (#3168).
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
    nodes_body,
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
    CountedTotals,
    LineAmounts,
    UnitedNode,
    compare_revisions,
    compare_united,
    compared_places,
)
from waterfall.core.planning.interface import NodeFilters, list_records

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.interface import PlacedNode

router = APIRouter(tags=["revisions"])

# The permissions one at least of which a comparison asks for: those of the three grids, which
# read it; the first is judged when the caller holds none (US-2320, WF-REV-0080).
READERS = ("planning.read", "estimate.read", "remaining.read")


class DifferenceAsked(StrEnum):
    """A mark the filter ``difference`` keeps (``NodeDifferenceFilter``)."""

    added = "added"
    removed = "removed"
    modified = "modified"


def _base_body(
    base: Mapping[str, Any] | None, fields: frozenset[str] | None
) -> dict[str, Any] | None:
    """Write what the base carried of a node (``ComparedNodeBase``), reduced to the fields read.

    The values named as ``task.finish`` in the shape of a node, ``{"task": {"finish": …}}``; a
    facet ``fields`` names whole kept whole, one of which none is left omitted, as ``projected``
    reduces a node.
    """
    if base is None:
        return None
    written: dict[str, Any] = {}
    for name, value in base.items():
        facet, _, key = name.partition(".")
        if fields is not None and name not in fields and (not key or facet not in fields):
            continue
        if key:
            written.setdefault(facet, {})[key] = value
        else:
            written[name] = value
    return written


def _compared(node: ComparedNode, fields: frozenset[str] | None) -> dict[str, Any]:
    """Write a node of the comparison: as ``listNodes`` does, its mark, base and deltas always."""
    return {
        **node_body(node.view, fields),
        "difference": node.difference,
        "changes": list(node.changes),
        "base": _base_body(node.base, fields),
        "deltas": _base_body(node.deltas, fields),
    }


def _totals(counted: CountedTotals) -> dict[str, Any]:
    """Write totals counted by the comparison, or their difference (``NodeTotalsDelta``)."""
    return totals_body(counted.task_count, counted.totals)


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
    """Give what the union reads of a node of a document: as its rows give it, in texts.

    ``ids`` the identifiers of the categories and the subprojects already read, which many lines
    share.
    """
    line = item["estimate_line"]
    amounts = None
    if line is not None:
        subproject = line["subproject_id"]
        hours = line["hours"]
        amounts = LineAmounts(
            _identifier(ids, line["cost_category_id"]),
            None if subproject is None else _identifier(ids, subproject),
            Decimal(line["budgeted_amount"]),
            Decimal(line["reestimated_amount"]),
            Decimal(0) if hours is None else Decimal(hours),
            Decimal(line["base_amount"]),
        )
    return UnitedNode(
        item["node_id"],
        item["lineage_id"],
        item["kind"],
        item["parent_id"],
        tuple(each["predecessor_node_id"] for each in item["predecessors"]),
        item,
        amounts,
    )


def _placed(
    item: dict[str, Any], placed: PlacedNode[str], fields: frozenset[str] | None
) -> dict[str, Any]:
    """Write a node of a document as the union returns it: placed, renamed, marked, its base."""
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
    written["base"] = _base_body(placed.base, fields)
    written["deltas"] = _base_body(placed.deltas, fields)
    return written


def kept_comparison(
    session: Session, project_id: UUID, asked: ComparisonAsked, fields: frozenset[str] | None
) -> dict[str, Any] | None:
    """Compare a revision with a marked base from the reading kept of their structures (US-2270).

    The body of ``compareRevisions`` no filter restricts: the reading kept of the base, made here
    if it is not; that of the revision read, or its columns when it is current (US-2220), nothing
    kept of it. None when the base has no reading kept, which a marked revision always has. The
    revisions are judged first (404, then 409).
    """
    reads, (base_place, compared_place) = compared_places(session, project_id, asked)
    base = kept_body(session, base_place)
    if base is None:
        return None
    compared = kept_body(session, compared_place)
    if compared is None:
        compared = nodes_body(list_records(session, compared_place, NodeFilters()))
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
        "base_totals": _totals(found.base_totals),
        "totals_delta": _totals(found.totals_delta),
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
        "totals": _totals(found.totals),
        "base_totals": _totals(found.base_totals),
        "totals_delta": _totals(found.totals_delta),
        "meta": meta.model_dump(mode="json"),
        "amount_deltas": [_delta(each) for each in found.amount_deltas],
    }


def comparison_reading(
    from_revision_id: Annotated[UUID, Query()],
    to_revision_id: Annotated[UUID, Query()],
    asked: Annotated[tuple[NodeFilters, frozenset[str] | None], Depends(node_reading)],
    difference: Annotated[str | None, Query()] = None,
    *,
    include_differences: Annotated[bool, Query()] = False,
) -> tuple[ComparisonAsked, frozenset[str] | None]:
    """Read what ``compareRevisions`` asks: its revisions, the reading of the tree, the marks.

    ``include_differences`` the nodes in difference a filter of progress leaves out, retained.
    """
    filters, fields = asked
    marks = listed("difference", difference, DifferenceAsked)
    kept = None if marks is None else tuple(each.value for each in marks)
    found = ComparisonAsked(from_revision_id, to_revision_id, filters, kept, include_differences)
    return found, fields


@router.get(
    "/projects/{project_id}/revisions/comparison",
    operation_id="compareRevisions",
    dependencies=[Depends(RequiresProject(one_of=READERS))],
    response_model=None,
)
def get_comparison(
    project_id: UUID,
    asked: Annotated[tuple[ComparisonAsked, frozenset[str] | None], Depends(comparison_reading)],
    session: Transaction,
) -> JSONResponse:
    """Compare a revision of the project with a marked base, read as ``listNodes`` reads one."""
    comparison, fields = asked
    if comparison.filters == NodeFilters():
        kept = kept_comparison(session, project_id, comparison, fields)
        if kept is not None:
            return read_body(kept)
    found = compare_revisions(session, project_id, comparison, node_body)
    return read_body(comparison_body(found, fields))
