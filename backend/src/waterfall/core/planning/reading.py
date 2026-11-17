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

A reading of the tasks alone — ``kinds=task``, no filter of the line — reads none of the nodes the
tasks bear (``tasks_reading``, US-2280): the tasks, and what the hooks of each kind count under each
task in one statement grouped by task (``FacetHooks.tally``), from which their numbers, their sums,
their calendars and the summaries an own line holds open are derived, the same as a whole reading
derives them (EP-26, "L'agrégat d'abord"); the tallies are read by ``tallying`` (US-1680), which
the physical progress of the summaries reads too, and the reading hands them on to it.
"""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from waterfall.core.planning.calendars import applicable_calendars
from waterfall.core.planning.dating import constants_of
from waterfall.core.planning.filters import retained
from waterfall.core.planning.interface.facets import calendars_of, facets
from waterfall.core.planning.tables import NODE_KINDS
from waterfall.core.planning.tallying import tallies_of
from waterfall.core.planning.tree import (
    TASK,
    completed_below,
    numbered,
    read_link_rows,
    read_rows,
    read_task_rows,
)
from waterfall.core.planning.views import RowsReading, TasksReading
from waterfall.core.planning.writing import StructureTotals, facts_of

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.filters import NodeFilters, Retained
    from waterfall.core.planning.tree import LinkRow, NodeRow, TaskRow, Tree
    from waterfall.core.planning.views import NodeRecord, NodeView, Reading
    from waterfall.core.planning.writing import Place


@dataclass(frozen=True, slots=True)
class NodeRecords:
    """A reading of a structure as ``listNodes`` returns it, its nodes as records (US-2220).

    What ``list_nodes`` gives — its nodes, its tasks counted, its meta, its totals —, each node a
    flat record (``TaskRecord``, ``FacetRecord``) rather than a view: the API writes the body.
    """

    items: tuple[NodeRecord, ...]
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
    links = _links(session, place, tree)
    calendars = calendars_of(session, place.project_id, tree.tasks)
    structure = (place, *scheduled)
    return RowsReading(session, structure, tree, links, calendars)


def _links(session: Session, place: Place, tree: Tree[NodeRow, TaskRow]) -> list[LinkRow]:
    """Read the links of a structure after its tree, those between tasks of the tree alone.

    In their own statement: one whose ends a write committed in between is of a later state than
    the tree, and left out.
    """
    return [
        link
        for link in read_link_rows(session, place.project_id, place.structure_id)
        if {link.predecessor_id, link.successor_id} <= tree.tasks.keys()
    ]


def _tasks_alone(filters: NodeFilters) -> bool:
    """Tell whether a reading returns tasks alone and asks nothing of their lines (US-2280).

    And whether every other kind of node counts under each task by the hooks of its facet: a kind
    without hooks is read whole.
    """
    return (
        filters.kinds is not None
        and all(kind == TASK for kind in filters.kinds)
        and filters.lines is None
        and all(kind in facets() for kind in NODE_KINDS if kind != TASK)
    )


def tasks_reading(session: Session, place: Place, scheduled: tuple[datetime, bool]) -> TasksReading:
    """Read the tasks of a structure alone, and what their lines count, none of these read.

    The tree of the tasks numbered from how many nodes each bears; the summaries completed below
    held open as their tallies tell (``Tree.held``); the calendar of each task from those its
    tallies name (WF-PLA-0010).
    """
    tree = read_task_rows(session, place.project_id, place.structure_id)
    # The session of a reading is not frozen (a ``READ COMMITTED`` transaction): the tree, the
    # tallies, the calendars (``applicable_calendars``) and the links are read by their own
    # statements, each of the state of its own instant. A line a write committed in between shifts
    # the numbers of the rows after it by one, or leaves a link out, until the next reading;
    # ``frozen_reading`` (#2679) would remove it, a change of the session this reading does not
    # make. The whole reading numbers from its tree alone, and has the gap of the links only.
    tallies = tallies_of(session, place)
    numbered(tree, {task_id: tally.count for task_id, tally in tallies.items()})
    tree.held = frozenset(
        each
        for each in completed_below(tree)
        if (tally := tallies.get(each)) is not None and tally.held_open
    )
    none: frozenset[UUID] = frozenset()
    named = {
        task_id: tallies[task_id].calendars if task_id in tallies else none
        for task_id in tree.tasks
    }
    calendars = applicable_calendars(session, named)
    structure = (place, *scheduled)
    read = (tree, _links(session, place, tree), tallies)
    return TasksReading(session, structure, read, calendars)


def structure_totals(reading: Reading[NodeRow, TaskRow], found: Retained) -> StructureTotals:
    """Give the totals of the lines a reading retains, whatever the kinds it returns.

    Those the tasks retained bear, from their tallies, for a reading of the tasks alone.
    """
    if isinstance(reading, TasksReading):
        return StructureTotals(*reading.borne(found.kept))
    return StructureTotals(len(found.lines), reading.totals(found.lines))


def retained_reading(
    session: Session, place: Place, filters: NodeFilters
) -> tuple[RowsReading, Retained, datetime]:
    """Read a structure as rows, and what the filters retain of it; or refuse (404).

    The reading, what it retains, and the instant of the dates of the structure. A reading of the
    tasks alone reads none of the nodes they bear (``tasks_reading``, US-2280).
    """
    facts = facts_of(session, place, lock=False)
    scheduled = (facts.scheduled_at, facts.is_main)
    reading: RowsReading
    if _tasks_alone(filters):
        reading = tasks_reading(session, place, scheduled)
    else:
        tree = read_rows(session, place.project_id, place.structure_id)
        reading = reading_of(session, place, tree, scheduled)
    structure = (place.project_id, place.structure_id)
    found = retained(session, structure, reading, filters, constants_of(session))
    return reading, found, facts.scheduled_at


def list_records(
    session: Session, place: Place, filters: NodeFilters, *, progress: bool = True
) -> NodeRecords:
    """Read the nodes of a structure as ``list_nodes`` does, as records (``listNodes``, US-2220).

    The same nodes, numbers, meta and totals, each node a record rather than a view: the API
    writes the body from them. ``progress`` is whether the summaries are given their physical
    progress: a projection that names none leaves it out (a bound on it asks it all the same).
    """
    reading, found, scheduled_at = retained_reading(session, place, filters)
    return NodeRecords(
        tuple(reading.records(found.order, progress=progress)),
        found.task_count,
        reading.summary_depth(),
        scheduled_at,
        structure_totals(reading, found),
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
        structure_totals(reading, found),
    )
