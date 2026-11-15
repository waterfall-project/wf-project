# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The two paths that read a structure give the same tree (US-2220, "Deux chemins, un oracle").

A write reads the tree as objects of the session, which it changes (``read_tree``, ``read_links``);
``listNodes`` and ``compareRevisions`` read it as rows (``read_rows``, ``reading_of``). On each
revision of PRJ-001 of the loaded witness — two marked, one current —, every node of the main
structure is read whole by each path, its facet included, and the two readings are the same: the
views, the depth of the summaries, the totals of the lines.
"""

from typing import TYPE_CHECKING

import pytest
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102
from test_witness_tasks import structure_of

from waterfall.core.planning.interface.facets import calendars_of
from waterfall.core.planning.reading import reading_of
from waterfall.core.planning.tree import read_links, read_rows, read_tree
from waterfall.core.planning.views import NodeView, Reading
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
