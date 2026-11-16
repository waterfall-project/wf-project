# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An entry of an inert column reads no tree as objects of the session (EP-26, US-2250/L2).

The criterion of US-2250/L2, its own — the story has no requirement of its own, its gain being read
in the report of WF-QUA-0060 (US-2300) —, on the witness, the main structure of the current
revision of PRJ-001 (#3540): an entry whose columns are all inert reads its structure as rows, the
node it writes alone as an object of the session; one that is not reads the tree whole as objects.
And what ``reshaped`` rests on, out of a write: the withdrawal of an element of the work breakdown
advances the counter of the nodes whose task it writes (#3562), and, through ``setWorkBreakdown``,
waits for the lock of every structure of the current revision before it locks the element, as a
write of the tree takes them (US-2250/L3, #3600).

The tests through ``setWorkBreakdown`` prove the Vérif of WF-PLA-0170 they cite — the deletion of
an order item a task of the current revision bears succeeds, and the task bears it no more —, under
the locks a concurrent write holds; the others, on the witness, prove a detail of realisation, the
counters, and cite none.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from nodes_support import Tree, opened, work_breakdown
from planning_support import insert_task
from project_rows import delete_structure, lifted_kind_check, structure_row
from projects_support import scene as make_scene
from sqlalchemy import event, func, insert, select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import InstrumentedAttribute, Session
from test_estimate_lines import blocked_by
from test_inert_writes import (
    COLUMNS,
    INERT,
    Read,
    Statement,
    counting,
    listened,
    read_of,
    unkept,
)
from test_witness_projects import PRJ_001, REVISION_102
from test_work_breakdown_attachments import attachment, without_item

from waterfall.core.planning import writing
from waterfall.core.planning.interface import Writer, detach_work_breakdown_item
from waterfall.core.planning.tables import Node, Task
from waterfall.core.projects.interface import work_breakdown_items
from waterfall.core.projects.tables import OrderItem
from waterfall.core.revisions.interface import structure_facts
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import Act

if TYPE_CHECKING:
    from collections.abc import Sequence

    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

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


def _counter(stage: Scene, structure_id: UUID) -> int | None:
    with stage.database.transaction() as session:
        return session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == structure_id)
        )


def _item_free(stage: Scene, item: UUID) -> bool:
    """Tell whether an order item can be locked at once by another transaction (``NOWAIT``)."""
    with stage.owner.begin() as trying:
        try:
            trying.execute(
                select(OrderItem.id).where(OrderItem.id == item).with_for_update(nowait=True)
            )
        except OperationalError:
            return False
    return True


@pytest.mark.requirement("WF-PLA-0170-A")
def test_the_withdrawal_of_an_element_waits_for_the_lock_of_its_structure_then_counts_it(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # US-2250, its own: the withdrawal of an element of the work breakdown advances the counter of
    # the structure under its lock (#3600). It waits for that lock before it writes or locks the
    # element: a write of the tree holds its structure, then shares the element it attaches a task
    # to, and the two would wait for each other the other way round.
    stage = make_scene(api, owner, database, realm)
    tree = Tree(api, stage, opened(api, stage))
    _, item = work_breakdown(stage)
    task = tree.made("Câblage", task={"order_item_id": str(item)})
    structure_id = UUID(tree.structure_id)
    before = _counter(stage, structure_id)
    assert before is not None
    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        connection.execute(
            select(CostStructure.id).where(CostStructure.id == structure_id).with_for_update()
        )
        holder = connection.scalar(select(func.pg_backend_pid()))
        waiting = pool.submit(without_item, api, stage, str(item))
        assert blocked_by(stage, holder, waiting)
        assert _item_free(stage, item)
        assert not waiting.done()
    waiting.result(timeout=30)
    assert _counter(stage, structure_id) == before + 1
    assert attachment(tree.node(task["node_id"])) == (None, None, None)


@pytest.mark.requirement("WF-PLA-0170-A")
def test_the_withdrawal_of_an_element_holds_a_structure_its_tasks_did_not_bear_it_in(
    api: ContractClient, owner: Engine, database: Database, realm: TestRealm
) -> None:
    # US-2250, its own (#3600): every structure of the current revision is held before the element,
    # not only those whose tasks bore it when read. A second structure, which bears nothing, is held
    # by a write of the tree: the withdrawal waits for it before it locks the element; the write
    # attaches a task to the element meanwhile, then ends. The withdrawal succeeds, writes that
    # task too, and advances the counter of that structure. Read before the lock, the second
    # structure was left out: the withdrawal ended without waiting, and wrote its task uncounted.
    stage = make_scene(api, owner, database, realm)
    tree = Tree(api, stage, opened(api, stage))
    _, item = work_breakdown(stage)
    task = tree.made("Câblage", task={"order_item_id": str(item)})
    project_id, revision_id = UUID(stage.project["project_id"]), UUID(tree.revision["revision_id"])
    # No differential is written before EP-08, and the kind of a structure is checked: lifted for
    # this test alone, and restored.
    row = structure_row(project_id, revision_id, kind="differential", label="Alpha")
    second = row["id"]
    assert isinstance(second, UUID)
    with lifted_kind_check(owner):
        try:
            with owner.begin() as connection:
                connection.execute(insert(CostStructure).values(**row))
            before = _counter(stage, second)
            assert before is not None
            with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
                connection.execute(
                    select(CostStructure.id).where(CostStructure.id == second).with_for_update()
                )
                holder = connection.scalar(select(func.pg_backend_pid()))
                waiting = pool.submit(without_item, api, stage, str(item))
                assert blocked_by(stage, holder, waiting)
                attached = insert_task(
                    connection, project_id, revision_id, second, order_item_id=item
                )
            waiting.result(timeout=30)
            assert _counter(stage, second) == before + 1
            with stage.database.transaction() as session:
                left = session.scalar(select(Task.order_item_id).where(Task.node_id == attached))
            assert left is None
            assert attachment(tree.node(task["node_id"])) == (None, None, None)
        finally:
            delete_structure(owner, second)


def _structure_counter(session: Session, read: Read) -> int:
    place = read.place
    return structure_facts(session, place.project_id, place.structure_id, lock=False).lock_version


# The lock of a structure (``structure_facts``) and the advance of its counter
# (``structure_counted``), as SQLAlchemy writes them.
_STRUCTURE_LOCKED = re.compile(r"^SELECT\b.*\bFROM cost_structure\b.*\bFOR UPDATE\b", re.DOTALL)
_STRUCTURE_COUNTED = re.compile(
    r"^UPDATE cost_structure SET lock_version\s*=\s*\(?\s*cost_structure\.lock_version\s*\+"
)


def withdrawn_unkept(statements: Sequence[Statement]) -> list[str]:
    """Give the statements of a withdrawal of an element that break what ``reshaped`` rests on.

    The withdrawal writes the tasks it detaches by statements, out of any write of the tree: they
    keep what ``reshaped`` rests on when the lock of their structure is taken before them and its
    counter advanced after them — no write of the tree reads them halfway, and the front knows its
    reading stale (#3600) —, a node written advancing its own counter (``unkept``).
    """
    texts = [each.text for each in statements]
    locked = [index for index, text in enumerate(texts) if _STRUCTURE_LOCKED.search(text)]
    counted = [index for index, text in enumerate(texts) if _STRUCTURE_COUNTED.search(text)]
    told: list[str] = []
    for index, each in enumerate(statements):
        if each.flushed or not each.text.startswith(("UPDATE node ", "UPDATE task ")):
            continue
        under = any(at < index for at in locked) and any(at > index for at in counted)
        if not under or (each.text.startswith("UPDATE node ") and unkept((each,))):
            told.append(each.text)
    return told


def test_the_withdrawal_of_an_element_writes_its_tasks_under_the_counted_lock_of_its_structure(
    witness: Database,
) -> None:
    # US-2250, its own: the withdrawal of an element of the work breakdown advances the counter of
    # the structure under its lock (#3600). The witness: a work package its tasks bear.
    read = read_of(witness)
    bearing = read.first(lambda each: each.task is not None and bool(each.task.work_package_id))
    assert bearing.task is not None
    item = bearing.task.work_package_id
    assert item is not None
    with listened() as sent, Session(witness.engine) as session:
        try:
            before = _structure_counter(session, read)
            sent.clear()
            detach_work_breakdown_item(session, PRJ_001, item)
            statements = tuple(sent)
            after = _structure_counter(session, read)
        finally:
            session.rollback()
    assert after == before + 1
    assert any(each.text.startswith("UPDATE task ") for each in statements)
    assert withdrawn_unkept(statements) == []


def test_the_statements_of_a_withdrawal_out_of_the_lock_of_its_structure_are_told() -> None:
    lock = "SELECT cost_structure.id \nFROM cost_structure \nWHERE cost_structure.id = 1 FOR UPDATE"
    count = (
        "UPDATE cost_structure SET lock_version=(cost_structure.lock_version + %(lv_1)s::INTEGER) "
        "WHERE true RETURNING cost_structure.lock_version"
    )
    node = "UPDATE node SET lock_version=(node.lock_version + %(lv_1)s::INTEGER) WHERE true"
    task = "UPDATE task SET order_item_id=%(order_item_id)s::UUID WHERE task.node_id IN (1)"

    def told(*texts: str) -> list[str]:
        return withdrawn_unkept(tuple(Statement(text, flushed=False) for text in texts))

    assert told(lock, node, task, count) == []
    # Not locked, not counted, or counted before it wrote: told.
    assert told(node, task, count) == [node, task]
    assert told(lock, node, task) == [node, task]
    assert told(lock, count, task) == [task]
    # Under the lock, a node written without its counter is told still.
    forgetting = "UPDATE node SET rank=node.rank + %(rank_1)s WHERE node.id IN (1)"
    assert told(lock, forgetting, task, count) == [forgetting]
