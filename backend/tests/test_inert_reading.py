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
from sqlalchemy import event, select
from sqlalchemy.orm import Session
from test_inert_writes import COLUMNS, INERT, counting, listened, read_of, unkept
from test_witness_projects import PRJ_001

from waterfall.core.planning import writing
from waterfall.core.planning.interface import Writer, detach_work_breakdown_item
from waterfall.core.planning.tables import Node, Task
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


def test_the_withdrawal_of_an_element_advances_the_counter_of_the_nodes_it_writes(
    witness: Database,
) -> None:
    read = read_of(witness)
    package = read.first(lambda each: each.task is not None and bool(each.task.work_package_id))
    item = None if package.task is None else package.task.work_package_id
    assert item is not None
    with listened() as sent, Session(witness.engine) as session:
        try:
            detach_work_breakdown_item(session, PRJ_001, item)
            after = session.execute(
                select(Node.lock_version, Task.work_package_id)
                .join(Task, (Task.project_id == Node.project_id) & (Task.node_id == Node.id))
                .where(Node.id == package.node_id)
            ).one()
        finally:
            session.rollback()
    # Withdrawn, and the counter of its node advanced (#3562).
    assert tuple(after) == (package.lock_version + 1, None)
    # Its node passes the guard of ``reshaped``; its task, written by a statement, would be told
    # if a write of the tree ever called it.
    told = unkept(sent)
    assert told
    assert all(each.startswith("UPDATE task ") for each in told)
