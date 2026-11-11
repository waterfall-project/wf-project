# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a reading derives of a structure, and a structure read whole, private to the module.

``reading_of`` reads what a reading of a structure derives once for all its nodes — its links, its
calendars, its states —, which ``listNodes`` reads by (``nodes``). ``read_structure`` reads a
structure whole and what the filters of a reading retain of it, without the ancestors a reading
adds and whatever its kinds and its sort: what the comparison of two revisions reads of each
(``compareRevisions``, US-1530), which numbers and orders their union itself; the interface
re-exports it beside its files, whose list the socle of EP-06 laid.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from waterfall.core.planning.dating import constants_of
from waterfall.core.planning.filters import retained
from waterfall.core.planning.interface.facets import calendars_of
from waterfall.core.planning.tree import read_links, read_tree
from waterfall.core.planning.views import Reading
from waterfall.core.planning.writing import StructureTotals, facts_of

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.filters import NodeFilters
    from waterfall.core.planning.tree import Tree
    from waterfall.core.planning.views import NodeView
    from waterfall.core.planning.writing import Place


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
    session: Session, place: Place, tree: Tree, scheduled: tuple[datetime, bool]
) -> Reading:
    """Read what a reading of a structure derives: its links, its calendars, its states.

    The links are read after the tree, in their own statement: one whose ends a write committed
    in between is of a later state than the tree, and left out.
    """
    links = [
        link
        for link in read_links(session, place.project_id, place.structure_id)
        if {link.predecessor_id, link.successor_id} <= tree.tasks.keys()
    ]
    calendars = calendars_of(session, place.project_id, tree.tasks)
    return Reading(session, (place.project_id, *scheduled), tree, links, calendars)


def read_structure(session: Session, place: Place, filters: NodeFilters) -> StructureRead:
    """Read a structure whole, and what the filters retain of it; or refuse (404)."""
    facts = facts_of(session, place, lock=False)
    tree = read_tree(session, place.project_id, place.structure_id)
    reading = reading_of(session, place, tree, (facts.scheduled_at, facts.is_main))
    structure = (place.project_id, place.structure_id)
    asked = replace(filters, kinds=None, sort=None)
    found = retained(session, structure, reading, asked, constants_of(session))
    reading.prefetch(tree.order)
    return StructureRead(
        tuple(reading.node(each) for each in tree.order),
        found.kept,
        found.lines,
        found.task_count,
        reading.summary_depth(),
        facts.scheduled_at,
        StructureTotals(len(found.lines), reading.totals(found.lines)),
    )
