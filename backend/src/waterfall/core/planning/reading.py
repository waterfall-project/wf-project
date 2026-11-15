# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a reading derives of a structure, and a structure read whole, private to the module.

``reading_of`` reads what a reading of a structure derives once for all its nodes — its links, its
calendars, its states — from the tree read as rows, which ``listNodes`` uses: a reading writes
nothing, and the objects of the session are left to the writes (US-2220). ``list_records`` reads
what ``list_nodes`` reads, each node a flat record rather than a view, from which the API writes
the body of ``listNodes``: the core does not know the form of a response (US-2220/L2).
``read_structure`` reads a structure whole and what the filters of a reading retain of it, without
the ancestors a reading adds and whatever its kinds and its sort: what the comparison of two
revisions reads of each (``compareRevisions``, US-1530), which numbers and orders their union
itself; the interface re-exports it beside its files, whose list the socle of EP-06 laid.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from waterfall.core.planning.dating import constants_of
from waterfall.core.planning.filters import retained
from waterfall.core.planning.interface.facets import calendars_of
from waterfall.core.planning.tree import read_link_rows, read_rows
from waterfall.core.planning.views import RowsReading
from waterfall.core.planning.writing import StructureTotals, facts_of

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.filters import NodeFilters, Retained
    from waterfall.core.planning.tree import NodeRow, TaskRow, Tree
    from waterfall.core.planning.views import NodeRecord, NodeView
    from waterfall.core.planning.writing import Place


@dataclass(frozen=True, slots=True)
class NodeRecords:
    """A reading of a structure as ``listNodes`` returns it, its nodes as records (US-2220).

    What ``list_nodes`` gives — its nodes, its tasks counted, its meta, its totals —, each node a
    flat record (``TaskRecord``, ``FacetRecord``) rather than a view: the API writes the body.
    """

    items: list[NodeRecord]
    task_count: int
    summary_depth: int
    scheduled_at: datetime
    totals: StructureTotals


@dataclass(frozen=True, slots=True)
class StructureRead:
    """A structure read whole, and what the filters of a reading retain of it.

    ``nodes`` every node, whole, in the order of the plan, numbered on the whole structure;
    ``kept`` the tasks the filters retain and ``lines`` the nodes of the other kinds; the meta,
    the count of the tasks and the totals as ``list_nodes`` gives them.
    """

    nodes: tuple[NodeView, ...]
    kept: frozenset[UUID]
    lines: frozenset[UUID]
    task_count: int
    summary_depth: int
    scheduled_at: datetime
    totals: StructureTotals


def reading_of(
    session: Session, place: Place, tree: Tree[NodeRow, TaskRow], scheduled: tuple[datetime, bool]
) -> RowsReading:
    """Read what a reading of a structure derives: its links, its calendars, its states.

    Of the tree read as rows (``read_rows``), its links and its facets too: a reading writes
    nothing. The links are read after the tree, in their own statement: one whose ends a write
    committed in between is of a later state than the tree, and left out.
    """
    links = [
        link
        for link in read_link_rows(session, place.project_id, place.structure_id)
        if {link.predecessor_id, link.successor_id} <= tree.tasks.keys()
    ]
    calendars = calendars_of(session, place.project_id, tree.tasks)
    structure = (place.project_id, *scheduled)
    return RowsReading(session, structure, tree, links, calendars)


def retained_reading(
    session: Session, place: Place, filters: NodeFilters
) -> tuple[RowsReading, Retained, datetime]:
    """Read a structure as rows, and what the filters retain of it; or refuse (404).

    The reading, what it retains, and the instant of the dates of the structure.
    """
    facts = facts_of(session, place, lock=False)
    tree = read_rows(session, place.project_id, place.structure_id)
    reading = reading_of(session, place, tree, (facts.scheduled_at, facts.is_main))
    structure = (place.project_id, place.structure_id)
    found = retained(session, structure, reading, filters, constants_of(session))
    return reading, found, facts.scheduled_at


def list_records(session: Session, place: Place, filters: NodeFilters) -> NodeRecords:
    """Read the nodes of a structure as ``list_nodes`` does, as records (``listNodes``, US-2220).

    The same nodes, numbers, meta and totals, each node a record rather than a view: the API
    writes the body from them.
    """
    reading, found, scheduled_at = retained_reading(session, place, filters)
    return NodeRecords(
        reading.records(found.order),
        found.task_count,
        reading.summary_depth(),
        scheduled_at,
        StructureTotals(len(found.lines), reading.totals(found.lines)),
    )


def read_structure(session: Session, place: Place, filters: NodeFilters) -> StructureRead:
    """Read a structure whole, and what the filters retain of it; or refuse (404)."""
    reading, found, scheduled_at = retained_reading(
        session, place, replace(filters, kinds=None, sort=None)
    )
    tree = reading.tree
    reading.prefetch(tree.order)
    return StructureRead(
        tuple(reading.node(each) for each in tree.order),
        found.kept,
        found.lines,
        found.task_count,
        reading.summary_depth(),
        scheduled_at,
        StructureTotals(len(found.lines), reading.totals(found.lines)),
    )
