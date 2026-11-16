# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An entry of an inert column reads no tree as objects of the session (EP-26, US-2250/L2).

The criterion of US-2250/L2, its own — the story has no requirement of its own, its gain being read
in the report of WF-QUA-0060 (US-2300) —, on the witness, the main structure of the current
revision of PRJ-001 (#3540): an entry whose columns are all inert reads its structure as rows, the
node it writes alone as an object of the session; one that is not reads the tree whole as objects.
And what ``reshaped`` rests on, out of a write: the withdrawal of an element of the work breakdown
advances the counter of the nodes whose task it writes (#3562).
"""

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import event, select, update
from sqlalchemy.orm import InstrumentedAttribute, Session
from test_inert_writes import COLUMNS, INERT, counting, listened, read_of, unkept
from test_witness_projects import PRJ_001, REVISION_102

from waterfall.core.planning import writing
from waterfall.core.planning.interface import Writer, detach_work_breakdown_item
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from uuid import UUID

    from waterfall.platform.database import Database

# A column of the whole path, beside the inert ones: its entry reads the tree whole as objects.
WHOLE = "task.duration"


@pytest.mark.parametrize("field", [*sorted(INERT), WHOLE])
def test_an_inert_entry_reads_as_objects_only_the_node_it_writes(
    witness: Database, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    write, _ = COLUMNS[field]
    read = read_of(witness)
    rows = counting(monkeypatch, (writing,), "read_inert")
    loaded: list[UUID] = []

    def made(target: Node, _context: object) -> None:
        loaded.append(target.id)

    event.listen(Node, "load", made)
    try:
        with Session(witness.engine) as session:
            try:
                written = write(session, read, Writer(Act(None, read.listed.scheduled_at), None))
            finally:
                session.rollback()
    finally:
        event.remove(Node, "load", made)
    if field == WHOLE:
        assert rows.count == 0
        assert len(set(loaded)) == len(read.nodes)
    else:
        # Its structure as rows, once; the node it writes alone as an object (#3540).
        assert rows.count == 1
        assert loaded == [each.node_id for each in written.nodes]


@pytest.mark.parametrize("column", [Task.work_package_id, Task.order_item_id])
def test_the_withdrawal_of_an_element_advances_the_counter_of_the_nodes_it_writes(
    witness: Database, column: InstrumentedAttribute[UUID | None]
) -> None:
    read = read_of(witness)
    kind = "work_package" if column is Task.work_package_id else "order_item"
    with listened() as sent, Session(witness.engine) as session:
        try:
            of_current = select(Node.id).where(
                Node.project_id == PRJ_001, Node.revision_id == REVISION_102
            )
            elsewhere_ids = select(Node.id).where(
                Node.project_id == PRJ_001, Node.id.not_in(of_current)
            )
            outside = select(Node.id, Node.lock_version).where(Node.id.in_(elsewhere_ids))
            if column is Task.work_package_id:
                # The witness: a work package its tasks bear in each of its revisions.
                bearing = read.first(
                    lambda each: each.task is not None and bool(each.task.work_package_id)
                )
                assert bearing.task is not None
                item = bearing.task.work_package_id
            else:
                # No order item is borne: a leaf of the current revision is given one, and only
                # that revision can be written.
                item = min(
                    each.item_id
                    for each in work_breakdown_items(session, PRJ_001).values()
                    if each.kind == kind and not each.deleted
                )
                bearing = read.first(
                    lambda each: each.task is not None and not each.task.is_summary
                )
                session.execute(
                    update(Task)
                    .where(Task.project_id == PRJ_001, Task.node_id == bearing.node_id)
                    .values({column.key: item})
                    .execution_options(synchronize_session=False)
                )
            elsewhere = dict(session.execute(outside).all())
            borne = session.scalars(
                select(Task.node_id).where(
                    Task.project_id == PRJ_001, column == item, Task.node_id.in_(elsewhere_ids)
                )
            ).all()
            before = session.scalar(select(Node.lock_version).where(Node.id == bearing.node_id))
            assert item is not None
            sent.clear()
            detach_work_breakdown_item(session, PRJ_001, item)
            after = session.execute(
                select(Node.lock_version, column)
                .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
                .where(Node.id == bearing.node_id)
            ).one()
            counters = dict(session.execute(outside).all())
            kept = session.scalars(
                select(Task.node_id).where(
                    Task.project_id == PRJ_001, column == item, Task.node_id.in_(elsewhere_ids)
                )
            ).all()
        finally:
            session.rollback()
    # Withdrawn, and the counter of its node advanced (#3562).
    assert before is not None
    assert tuple(after) == (before + 1, None)
    # A node of another revision than the current one keeps its element and its counter; the
    # work package is borne by one in each of the others.
    assert counters == elsewhere
    assert kept == borne
    assert bool(borne) is (column is Task.work_package_id)
    # Its node passes the guard of ``reshaped``; its task, written by a statement, would be told
    # if a write of the tree ever called it.
    told = unkept(sent)
    assert told
    assert all(each.startswith("UPDATE task ") for each in told)
