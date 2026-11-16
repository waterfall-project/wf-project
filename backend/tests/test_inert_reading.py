# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What ``reshaped`` rests on, out of a write of the tree (EP-26, US-2250/L2).

The story has no requirement of its own, its gain being read in the report of WF-QUA-0060
(US-2300); on the witness, the main structure of the current revision of PRJ-001: the withdrawal of
an element of the work breakdown advances the counter of the nodes whose task it writes (#3562).
"""

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_inert_writes import listened, read_of, unkept
from test_witness_projects import PRJ_001

from waterfall.core.planning.interface import detach_work_breakdown_item
from waterfall.core.planning.tables import Node, Task

if TYPE_CHECKING:
    from waterfall.platform.database import Database


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
