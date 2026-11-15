# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The two paths that read a structure give the same tree (US-2220, "Deux chemins, un oracle").

A write reads the tree as objects of the session, which it changes (``read_tree``, ``read_links``);
``listNodes`` and ``compareRevisions`` read it as rows (``read_rows``, ``reading_of``). On each
revision of PRJ-001 of the loaded witness — two marked, one current —, every node of the main
structure is read whole by each path, its facet included, and the two readings are the same: the
views, the depth of the summaries, the totals of the lines. ``listNodes`` writes its body from
records rather than views (US-2220/L2): the records of the rows are the views of the objects made
records (``record_of``), which every other route writes its nodes from.
"""

from typing import TYPE_CHECKING

import pytest
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102
from test_witness_tasks import structure_of

from waterfall.core.planning.interface.facets import calendars_of
from waterfall.core.planning.filters import NodeFilters
from waterfall.core.planning.interface.nodes import list_nodes
from waterfall.core.planning.reading import list_records, reading_of
from waterfall.core.planning.tree import read_links, read_rows, read_tree
from waterfall.core.planning.views import (
    FacetRecord,
    NodeView,
    Reading,
    TaskRecord,
    record_of,
)
from waterfall.core.planning.writing import Place, facts_of

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import Amounts
    from waterfall.platform.database import Database

type Read = tuple[list[NodeView], int, Amounts]


def by_objects(session: Session, place: Place) -> Read:
    """Read a structure whole as a write reads it: its tree and its links as objects."""
    facts = facts_of(session, place, lock=False)
    tree = read_tree(session, place.project_id, place.structure_id)
    links = [
        link
        for link in read_links(session, place.project_id, place.structure_id)
        if {link.predecessor_id, link.successor_id} <= tree.tasks.keys()
    ]
    calendars = calendars_of(session, place.project_id, tree.tasks)
    structure = (place.project_id, facts.scheduled_at, facts.is_main)
    reading = Reading(session, structure, tree, links, calendars)
    reading.prefetch(tree.order)
    lines = [each for each in tree.order if each not in tree.tasks]
    views = [reading.node(each) for each in tree.order]
    return views, reading.summary_depth(), reading.totals(lines)


def by_rows(session: Session, place: Place) -> Read:
    """Read a structure whole as ``listNodes`` reads it: its tree and its links as rows."""
    facts = facts_of(session, place, lock=False)
    tree = read_rows(session, place.project_id, place.structure_id)
    reading = reading_of(session, place, tree, (facts.scheduled_at, facts.is_main))
    reading.prefetch(tree.order)
    lines = [each for each in tree.order if each not in tree.tasks]
    views = [reading.node(each) for each in tree.order]
    return views, reading.summary_depth(), reading.totals(lines)


@pytest.mark.parametrize("revision", [REVISION_100, REVISION_101, REVISION_102])
def test_the_rows_and_the_objects_of_a_structure_read_the_same_tree(
    witness: Database, revision: UUID
) -> None:
    with witness.transaction() as session:
        place = Place(PRJ_001, revision, structure_of(session, revision))
        objects = by_objects(session, place)
    with witness.transaction() as session:
        rows = by_rows(session, place)
    views, depth, totals = rows
    # The witness reads thousands of nodes, lines and tasks with their facets: nothing is compared
    # empty.
    assert len(views) > 5000
    assert {view.kind for view in views} == {"task", "estimate_line"}
    assert all(view.facet is not None for view in views if view.kind != "task")
    assert depth > 0
    assert totals.base > 0
    assert rows == objects


@pytest.mark.parametrize("revision", [REVISION_100, REVISION_101, REVISION_102])
def test_the_records_of_a_reading_are_the_views_of_the_objects_made_records(
    witness: Database, revision: UUID
) -> None:
    with witness.transaction() as session:
        place = Place(PRJ_001, revision, structure_of(session, revision))
        views, _, _ = by_objects(session, place)
    with witness.transaction() as session:
        facts = facts_of(session, place, lock=False)
        tree = read_rows(session, place.project_id, place.structure_id)
        reading = reading_of(session, place, tree, (facts.scheduled_at, facts.is_main))
        records = reading.records(tree.order)
    tasks = [each for each in records if isinstance(each, TaskRecord)]
    # What a record derives is compared on values that are there: summaries, milestones,
    # predecessors, links in conflict, lines with their facet.
    assert len(records) > 5000
    assert any(each.is_summary for each in tasks)
    assert any(each.predecessors for each in tasks)
    assert all(each.facet is not None for each in records if isinstance(each, FacetRecord))
    assert records == [record_of(view) for view in views]


@pytest.mark.parametrize("filters", [NodeFilters(), NodeFilters(kinds=("task",))])
def test_list_nodes_and_list_records_read_the_same_nodes(
    witness: Database, filters: NodeFilters
) -> None:
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        read = list_nodes(session, place, filters)
        records = list_records(session, place, filters)
    assert len(read.items) > 100
    assert tuple(record_of(view) for view in read.items) == records.items
    assert (read.task_count, read.summary_depth) == (records.task_count, records.summary_depth)
    assert (read.scheduled_at, read.totals) == (records.scheduled_at, records.totals)



def test_a_node_its_facet_does_not_read_names_no_field(witness: Database) -> None:
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        facts = facts_of(session, place, lock=False)
        tree = read_rows(session, place.project_id, place.structure_id)
        reading = reading_of(session, place, tree, (facts.scheduled_at, facts.is_main))
        line = next(each for each in tree.order if each not in tree.tasks)
        assert line not in reading._facets  # noqa: SLF001
        record = reading._facet_record(line, tree.nodes[line])  # noqa: SLF001
    assert isinstance(record, FacetRecord)
    assert record.computed_fields == ()
    assert record.editable_fields == ()
    assert record.facet is None
