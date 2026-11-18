# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The two paths that read a structure give the same tree (US-2220, "Deux chemins, un oracle").

A write reads the tree as objects of the session, which it changes (``read_tree``, ``read_links``);
``listNodes`` and ``compareRevisions`` read it as rows (``read_rows``, ``reading_of``). On each
revision of PRJ-001 of the loaded witness — two marked, one current —, every node of the main
structure is read whole by each path, its facet included, and the two readings are the same: the
views, the depth of the summaries, the totals of the lines. ``listNodes`` writes its body from
records rather than views (US-2220/L2): the records of the rows are the views of the objects made
records (``record_of``), which every other route writes its nodes from. A reading of the tasks
alone reads none of the lines, but what they count under each task (US-2280): the whole reading of
the same filters is its oracle. Each path asks the physical progress of its summaries once, and
gives the same (US-1680).
"""

import itertools
from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, update
from test_witness_projects import PRJ_001, REVISION_100, REVISION_101, REVISION_102
from test_witness_tasks import structure_of

import waterfall.core.planning.reading as reading_module
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.indicators.interface import physical_progress as indicators_progress
from waterfall.core.planning.filters import NodeFilters
from waterfall.core.planning.interface import (
    PhysicalShare,
    SummariesAsked,
    register_physical_progress,
)
from waterfall.core.planning.interface.facets import (
    Amounts,
    LineSort,
    Tally,
    calendars_of,
    facets,
    register_facet,
)
from waterfall.core.planning.interface.nodes import list_nodes
from waterfall.core.planning.reading import (
    list_records,
    reading_of,
    retained_reading,
    tallies_of,
)
from waterfall.core.planning.tables import Node
from waterfall.core.planning.tree import read_links, read_rows, read_tree
from waterfall.core.planning.views import (
    FacetRecord,
    NodeRecord,
    NodeView,
    Reading,
    TaskRecord,
    TasksReading,
    record_of,
)
from waterfall.core.planning.writing import Place, facts_of

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from uuid import UUID

    from sqlalchemy import Subquery
    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface.facets import FacetHooks
    from waterfall.core.planning.tree import NodeRow, TaskRow
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
    structure = (place, facts.scheduled_at, facts.is_main)
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


def test_a_node_its_facet_does_not_read_names_no_field(
    witness: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A facet its hooks do not read — a line written around the service —: ``prefetch`` leaves it
    # out of the facets of the reading, which ``records`` then gives without a facet.

    def leave_out(_reading: Reading[NodeRow, TaskRow], _node_ids: Collection[UUID]) -> None:
        """Read no facet."""

    monkeypatch.setattr(Reading, "prefetch", leave_out)
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        facts = facts_of(session, place, lock=False)
        tree = read_rows(session, place.project_id, place.structure_id)
        reading = reading_of(session, place, tree, (facts.scheduled_at, facts.is_main))
        line = next(each for each in tree.order if each not in tree.tasks)
        (record,) = reading.records([line])
        # The node is among no facet read, ``records`` included (#3436): its record is then the
        # case of the facet missing, not one whose facet the test only left unread.
        assert reading.node(line).facet is None
    assert isinstance(record, FacetRecord)
    assert record.computed_fields == ()
    assert record.editable_fields == ()
    assert record.facet is None


# What a reading of the tasks alone is asked, each against the whole reading (US-2280): the tasks
# alone, filtered by a task, by their level, their summaries, sorted by a column of the line.
TASKS_ALONE = {
    "tasks": NodeFilters(kinds=("task",)),
    "searched, by state": NodeFilters(
        kinds=("task",), search="revue", progress=("not_started", "started")
    ),
    "two levels": NodeFilters(kinds=("task",), max_level=2),
    "summaries": NodeFilters(kinds=("task",), summaries_only=True),
    "sorted by a line": NodeFilters(kinds=("task",), sort=LineSort("base_amount", descending=True)),
}


@pytest.mark.parametrize("revision", [REVISION_100, REVISION_101, REVISION_102])
@pytest.mark.parametrize("name", list(TASKS_ALONE))
def test_the_tasks_read_alone_are_those_the_whole_reading_gives(
    witness: Database, revision: UUID, name: str
) -> None:
    # ``kinds=task`` reads the tasks and the tallies of their lines, none of these (US-2280): its
    # records, the count, the depth and the totals of the lines retained are those the whole
    # reading gives of the same filters, its lines left out.
    filters = TASKS_ALONE[name]
    with witness.transaction() as session:
        place = Place(PRJ_001, revision, structure_of(session, revision))
        alone_read, _, _ = retained_reading(session, place, filters)
        whole_read, _, _ = retained_reading(session, place, replace(filters, kinds=None))
        alone = list_records(session, place, filters)
        whole = list_records(session, place, replace(filters, kinds=None))
    assert isinstance(alone_read, TasksReading)
    assert not isinstance(whole_read, TasksReading)
    tasks = tuple(each for each in whole.items if isinstance(each, TaskRecord))
    assert tasks
    assert alone.items == tasks
    assert (alone.task_count, alone.summary_depth) == (whole.task_count, whole.summary_depth)
    assert (alone.scheduled_at, alone.totals) == (whole.scheduled_at, whole.totals)


def test_the_tasks_read_alone_are_numbered_and_summed_through_their_lines(
    witness: Database,
) -> None:
    # The numbers and the sums of the tasks read alone come from the tallies of their lines: on the
    # witness, tasks bear lines, and the next task is numbered past them (the places after the
    # lines of a summary: ``test_open_lines``).
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        records = list_records(session, place, NodeFilters(kinds=("task",))).items
    tasks = [each for each in records if isinstance(each, TaskRecord)]
    assert len(tasks) == len(records) > 100
    gaps = [after.row_number - before.row_number for before, after in itertools.pairwise(tasks)]
    assert max(gaps) > 1
    assert any(each.amounts.base > 0 for each in tasks)


def alone_as_whole(session: Session, place: Place, filters: NodeFilters) -> None:
    """Check the tasks read alone are those of the whole reading of the same filters."""
    alone = list_records(session, place, filters)
    whole = list_records(session, place, replace(filters, kinds=None))
    tasks = tuple(each for each in whole.items if isinstance(each, TaskRecord))
    assert tasks
    assert alone.items == tasks
    assert (alone.task_count, alone.summary_depth) == (whole.task_count, whole.summary_depth)
    assert (alone.scheduled_at, alone.totals) == (whole.scheduled_at, whole.totals)


@pytest.mark.parametrize(
    "filters",
    [
        NodeFilters(kinds=("task", "estimate_line")),
        NodeFilters(kinds=("task",), lines={"asked": True}),
    ],
    ids=["tasks and lines", "a filter of the line"],
)
def test_a_reading_that_asks_of_the_lines_is_read_whole(
    witness: Database, filters: NodeFilters
) -> None:
    # A reading that returns the lines, or filters them, is none of the tasks alone: it is read
    # whole, by the reading of the rows the whole reading takes; the one that returns the lines
    # answers besides what the whole reading answers.
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        read, _, _ = retained_reading(session, place, filters)
        whole, _, _ = retained_reading(session, place, replace(filters, kinds=None))
        assert not isinstance(read, TasksReading)
        assert type(read) is type(whole)
        if filters.lines is None:
            assert list_records(session, place, filters) == list_records(
                session, place, NodeFilters()
            )


def test_a_kind_of_node_without_hooks_is_read_whole(
    witness: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A kind no facet counts (``facets`` naming none): ``kinds=task`` reads the lines whole, and
    # answers what the tasks read alone answered.
    filters = NodeFilters(kinds=("task",))
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        before = list_records(session, place, filters)
        monkeypatch.setattr(reading_module, "facets", dict)
        read, _, _ = retained_reading(session, place, filters)
        after = list_records(session, place, filters)
    assert not isinstance(read, TasksReading)
    assert after == before


def test_a_summary_of_risk_lines_and_a_line_without_a_facet_count_as_the_whole_reading_counts(
    witness: Database,
) -> None:
    # A summary whose lines are all a risk's is held open by no own line (``own`` false), and a
    # line whose facet is missing — written around the service — counts in the number and adds
    # nought: the tasks read alone are those the whole reading gives, its oracle.
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        tree = read_rows(session, place.project_id, place.structure_id)
        borne = [each for each in tree.order if each in tree.tasks and tree.lines(each)]
        summary = next(each for each in tree.order if tree.is_summary(each))
        donor, other = borne[0], borne[1]
        assert summary not in (donor, other)
        bare = tree.lines(other)[0]
        moved = tree.lines(donor)
        # The witness has no summary bearing a line: the lines of a task pass under one, as a
        # risk's provisions.
        session.execute(
            update(Node).where(Node.id.in_(moved)).values(parent_id=summary, origin_risk_id=uuid4())
        )
        session.execute(delete(EstimateLine).where(EstimateLine.node_id == bare))
        session.flush()
        tallies = tallies_of(session, place)
        alone_as_whole(session, place, NodeFilters(kinds=("task",)))
    assert tallies[summary].own is False
    assert tallies[summary].count == len(moved)
    assert tallies[other].count == len(tree.lines(other))


def second_kind(task_id: UUID, calendar: UUID, *, own: bool, held_open: bool) -> FacetHooks:
    """Give the hooks of the lines with a tally of two nodes of a second kind under a task."""

    def tally(_s: Session, _p: UUID, _n: Subquery) -> dict[UUID, Tally]:
        """Count two nodes under the task: the sums of ``SECOND``, the flags said."""
        return {task_id: Tally(SECOND, 2, own, held_open, frozenset({calendar}), SECOND.budgeted)}

    return replace(facets()["estimate_line"], tally=tally)


SECOND = Amounts(Decimal(1), Decimal("2.00"), Decimal("3.00"), Decimal("4.00"))


@pytest.mark.parametrize("flags", [(False, False), (True, False), (False, True), (True, True)])
def test_the_tallies_of_several_kinds_under_a_task_are_added(
    witness: Database, flags: tuple[bool, bool]
) -> None:
    # Two kinds count under a task: the sums and the numbers add, a task is held open or own by
    # either kind, the calendars of both are named, their budgeted amounts out of a provision add
    # (US-1680); the other tasks are left as they were.
    calendar = uuid4()
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        real = tallies_of(session, place)
        task_id = next(iter(real))
        hooks = second_kind(task_id, calendar, own=flags[0], held_open=flags[1])
        withdraw = register_facet("second_kind", hooks)
        try:
            merged = tallies_of(session, place)
        finally:
            withdraw()
    first = real[task_id]
    assert merged[task_id] == Tally(
        first.amounts + SECOND,
        first.count + 2,
        first.own or flags[0],
        first.held_open or flags[1],
        first.calendars | {calendar},
        first.earnable + SECOND.budgeted,
    )
    assert {each: tally for each, tally in merged.items() if each != task_id} == {
        each: tally for each, tally in real.items() if each != task_id
    }


def test_the_nodes_the_planning_names_to_the_hook_of_a_tally_hold_three_columns(
    witness: Database,
) -> None:
    # The subquery the planning names to the hooks of a kind is a contract with the estimate
    # (``line_tallies``): the node, the task bearing it, whether a risk provides for it.
    seen: list[tuple[str, ...]] = []

    def watch(_s: Session, _p: UUID, nodes: Subquery) -> dict[UUID, Tally]:
        """Note the columns of the nodes named; count nothing."""
        seen.append(tuple(nodes.c.keys()))
        return {}

    hooks = replace(facets()["estimate_line"], tally=watch)
    with witness.transaction() as session:
        place = Place(PRJ_001, REVISION_102, structure_of(session, REVISION_102))
        withdraw = register_facet("watched_kind", hooks)
        try:
            tallies_of(session, place)
        finally:
            withdraw()
    assert seen == [("node_id", "task_id", "from_risk")]


def shares_of(items: Sequence[NodeView | NodeRecord]) -> dict[UUID, PhysicalShare | None]:
    """Give the physical progress of each summary among nodes read, as views or as records."""
    found: dict[UUID, PhysicalShare | None] = {}
    for each in items:
        if isinstance(each, NodeView):
            if each.task is not None and each.task.is_summary:
                found[each.node_id] = each.task.physical_progress
        elif isinstance(each, TaskRecord) and each.is_summary:
            found[each.node_id] = each.physical_progress
    return found


@pytest.mark.requirement("WF-IND-0060-A")
@pytest.mark.parametrize("revision", [REVISION_100, REVISION_102])
def test_every_path_asks_the_physical_progress_once_and_gives_the_same(
    witness: Database, revision: UUID
) -> None:
    # The physical progress of the summaries (US-1680) is asked once a reading — the objects of a
    # write, the rows, the tasks alone —, never once a task, for every summary it gives; the tasks
    # read alone hand on the tallies they read. Each path gives the summaries the same shares, the
    # indicators' answer to what the first reading asked, and computed: none is left null.
    asked: list[SummariesAsked] = []

    def watch(_session: Session, summaries: SummariesAsked) -> dict[UUID, PhysicalShare]:
        """Note what a reading asks; answer nothing."""
        asked.append(summaries)
        return {}

    withdraw = register_physical_progress(watch)
    try:
        with witness.transaction() as session:
            place = Place(PRJ_001, revision, structure_of(session, revision))
            objects, _, _ = by_objects(session, place)
            rows, _, _ = by_rows(session, place)
            whole = list_records(session, place, NodeFilters()).items
            alone = list_records(session, place, NodeFilters(kinds=("task",))).items
            answered = indicators_progress(session, asked[0])
    finally:
        withdraw()
    assert len(asked) == 4
    assert [each.tallies is None for each in asked] == [True, True, True, False]
    shares = shares_of(objects)
    assert set(shares) == asked[0].summaries == asked[3].summaries
    assert len(shares) > 10
    assert None not in shares.values()
    assert shares == answered == shares_of(rows) == shares_of(whole) == shares_of(alone)
    if revision == REVISION_102:
        assert any(each is not None and each.value for each in shares.values())
