# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rows of a differential as the API numbers them (WF-REV-0080, WF-REV-0100).

A differential is read as the tree it holds, each node the main structure of its revision has and
it lacks returned in its place, read-only: ``row_number``, ``level`` and ``position`` count that
tree, the removed nodes included (``Node``), and the number of a predecessor is as well the row of
the whole structure (``Predecessor``). The tree the planning reads of a differential does not hold
the removed nodes, so that it numbers the nodes without them: this module is the one place that
gives the rows of the tree returned (``differential_rows``, of the estimate, which ``listNodes``
reads), and every operation that names a row of a differential takes them here:
``resolveRowNumber``, the numbers of the nodes a write gives back, those of the dependencies of
a computed value, the anchor of a paste. A structure that is no differential has none of its own:
``None``.
"""

from typing import TYPE_CHECKING, Any

from waterfall.core.estimate.interface import differential_rows
from waterfall.core.planning.interface import Place, describe_row, resolve_row_number
from waterfall.core.revisions.interface import aimed_structure, structure_facts
from waterfall.platform.errors import NOT_FOUND, NotFoundError

if TYPE_CHECKING:
    from collections.abc import Collection
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.comparing import Written
    from waterfall.core.estimate.interface import DifferentialRow
    from waterfall.core.planning.interface import RowResolution


def rows_of(session: Session, place: Place, written: Written) -> tuple[DifferentialRow, ...] | None:
    """Give the rows a structure is read as when it is a differential of the revision; else none.

    ``written`` how the reader writes a node whole, whose values the union compares. An unknown
    structure is not found (404).
    """
    facts = structure_facts(session, place.project_id, place.structure_id, lock=False)
    if not facts.is_differential or facts.revision_id != place.revision_id:
        return None
    return differential_rows(session, place, written)


def removed_in(rows: tuple[DifferentialRow, ...] | None) -> Collection[UUID]:
    """Give the nodes a differential removes, which its tree does not hold."""
    return () if rows is None else tuple(each.node_id for each in rows if each.removed)


def resolved(session: Session, place: Place, row_number: int, written: Written) -> RowResolution:
    """Give the node of a row of a structure (``resolveRowNumber``), in the numbering it is read in.

    A differential is numbered with the nodes it removes in their place: the row of one is that of
    the main structure's node, described there. Beyond its last row, not found (404).
    """
    rows = rows_of(session, place, written)
    if rows is None:
        return resolve_row_number(session, place, row_number)
    row = next((each for each in rows if each.row_number == row_number), None)
    if row is None:
        raise NotFoundError(NOT_FOUND)
    holder = place
    if row.removed:
        main_id = aimed_structure(session, place.project_id, place.revision_id, None)
        if main_id is None:
            raise NotFoundError(NOT_FOUND)
        holder = Place(place.project_id, place.revision_id, main_id)
    return describe_row(session, holder, row.node_id, row_number)


def renumbered(body: dict[str, Any], rows: tuple[DifferentialRow, ...]) -> dict[str, Any]:
    """Give the nodes a write returns (``nodes``, ``ancestors``) the rows the differential reads.

    Their ``row_number``, ``level`` and ``position``, and the ``predecessor_row_number`` of each of
    their links; a node the read no longer holds, deleted, keeps what the write gave it.
    """
    at = {str(each.node_id): each for each in rows}
    for node in [*body["nodes"], *body["ancestors"]]:
        row = at.get(node["node_id"])
        if row is not None:
            node["row_number"], node["level"], node["position"] = (
                row.row_number,
                row.level,
                row.position,
            )
        for link in node["predecessors"]:
            before = at.get(link["predecessor_node_id"])
            if before is not None:
                link["predecessor_row_number"] = before.row_number
    return body
