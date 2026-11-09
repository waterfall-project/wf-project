# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The revised tables, partitioned by project (WF-DAT-0050; EP-04, "Tables et migrations").

One partition per project, by list on its identifier, created by the function of the owner in the
transaction that creates the project; the plan of a reading of a revision reads the partition of
its project alone. The rows are written around the service, by the owner; the volumes, six hundred
projects, are EP-13's.

The creation waits for no lock while it holds one (migration ``0026``; #2603, #2667): a reading or
a write of another project that holds one of the tables it locks does not wait for it in return,
and eight creations at once meet no deadlock. Where a state of the locks is awaited, ``pg_locks``
and ``pg_stat_activity`` are read until it comes, never a fixed pause.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from installed_reference import install
from planning_support import node_row
from project_rows import (
    drop_partitions,
    insert_project,
    insert_revision,
    insert_structure,
    partition_of,
    projects_with_partitions,
)
from projects_support import complete_reference
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from waterfall.api.restores import RESTORE_LOCK
from waterfall.bootstrap import INSTALL_LOCK
from waterfall.core.access_roles.administrators import ADMINISTRATORS_LOCK
from waterfall.core.cost_settings.records import NATURES_LOCK
from waterfall.core.history.stacks import STACK_LOCK
from waterfall.core.planning.tables import Node
from waterfall.core.projects.interface import ProjectDraft, Viewer, create_project
from waterfall.core.projects.tables import Project
from waterfall.core.resource_settings.interface.calendars import DEFAULT_LOCK
from waterfall.core.resource_settings.interface.org_nodes import TREE_LOCK
from waterfall.core.resource_settings.interface.readiness import REFERENCE_LOCK
from waterfall.core.revisions.interface import create_project_partitions
from waterfall.core.revisions.interface.revisions import PARTITIONS_LOCK
from waterfall.core.revisions.tables import CostStructure
from waterfall.platform.audit import FORGETTING_LOCK, Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context
from waterfall.witness.main import WITNESS_LOCK
from waterfall.worker.main import PURGE_LOCK, SCHEDULE_LOCK
from waterfall.worker.runner import RUN_LOCK

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Engine
    from sqlalchemy.engine import Connection

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-DAT-0050-A")


def scanned(plan: Any) -> set[str]:
    """Give the relations a plan of PostgreSQL reads, in its whole tree."""
    found: set[str] = {plan["Relation Name"]} if "Relation Name" in plan else set()
    for child in plan.get("Plans", []):
        found |= scanned(child)
    return found


def plan_of(connection: Connection, query: str, **values: UUID) -> set[str]:
    """Give the relations the plan of a query reads."""
    explained = connection.execute(text(f"EXPLAIN (FORMAT JSON) {query}"), values).scalar_one()
    return scanned(explained[0]["Plan"])


def partitions(connection: Connection) -> set[str]:
    """Name the partitions of the cost structures."""
    rows = connection.execute(
        text(
            "SELECT inhrelid::regclass::text FROM pg_inherits "
            "WHERE inhparent = 'cost_structure'::regclass"
        )
    )
    return set(rows.scalars())


def test_the_plan_of_a_reading_of_a_revision_reads_the_partition_of_its_project_alone(
    database: Database, owner: Engine
) -> None:
    # « Le plan d'exécution d'une lecture de révision ne parcourt que la partition du projet. » A
    # reading by the revision alone would read every partition: the plan says which it reads.
    del database
    with projects_with_partitions(owner, 3) as projects, owner.begin() as connection:
        revisions: dict[UUID, UUID] = {}
        for project_id in projects:
            revisions[project_id] = uuid4()
            connection.execute(insert_revision(project_id, id=revisions[project_id]))
            connection.execute(insert_structure(project_id, revisions[project_id]))
        connection.execute(text("ANALYZE cost_structure"))
        first = projects[0]
        reading = (
            "SELECT * FROM cost_structure WHERE project_id = :project AND revision_id = :revision"
        )
        assert plan_of(connection, reading, project=first, revision=revisions[first]) == {
            partition_of(first)
        }
        everywhere = "SELECT * FROM cost_structure WHERE revision_id = :revision"
        assert plan_of(connection, everywhere, revision=revisions[first]) == {
            partition_of(project_id) for project_id in projects
        }


def test_the_service_creates_the_partitions_of_a_project_in_the_transaction_that_creates_it(
    database: Database, owner: Engine
) -> None:
    # Through the interface of the revisions, as the creation of a project will: rolled back with
    # its transaction, written with it; a second time, refused.
    project_id = uuid4()
    with Session(database.engine) as session:
        session.execute(insert_project(id=project_id))
        create_project_partitions(session, project_id)
        assert partition_of(project_id) in partitions(session.connection())
        session.rollback()
    try:
        with database.engine.connect() as connection:
            assert partition_of(project_id) not in partitions(connection)
        with database.transaction() as session:
            session.execute(insert_project(id=project_id))
            create_project_partitions(session, project_id)
        with pytest.raises(DBAPIError) as twice, database.transaction() as session:
            create_project_partitions(session, project_id)
        assert getattr(twice.value.orig, "sqlstate", None) == "42P07"
    finally:
        with owner.begin() as connection:
            drop_partitions(connection, project_id)


def test_a_row_of_a_project_without_its_partitions_is_refused(
    database: Database, owner: Engine
) -> None:
    # Each project has its partition, or no revised row: none holds the rows of several projects.
    project_id = uuid4()
    with owner.begin() as connection:
        connection.execute(insert_project(id=project_id))
        revision_id = uuid4()
        connection.execute(insert_revision(project_id, id=revision_id))
    with pytest.raises(IntegrityError) as refused, database.engine.begin() as connection:
        connection.execute(insert_structure(project_id, revision_id))
    assert getattr(refused.value.orig, "sqlstate", None) == "23514"


# The tables the function creates partitions in: partitioned by list on ``project_id`` alone, as
# it reads them in the catalogue.
REVISED_TABLES = text(
    "SELECT parent.relname FROM pg_partitioned_table AS partitioned "
    "JOIN pg_class AS parent ON parent.oid = partitioned.partrelid "
    "JOIN pg_attribute AS key "
    "ON key.attrelid = partitioned.partrelid AND key.attnum = partitioned.partattrs[0] "
    "WHERE parent.relnamespace = 'public'::regnamespace AND NOT parent.relispartition "
    "AND partitioned.partstrat = 'l' AND partitioned.partnatts = 1 "
    "AND key.attname = 'project_id' ORDER BY parent.relname"
)
# The tables the function locks, by name: the revised, and those their keys bind, both ways.
LOCKED_TABLES = text(
    "SELECT relname FROM pg_class WHERE relname = ANY (:revised) "
    "AND relnamespace = 'public'::regnamespace "
    "UNION SELECT confrelid::regclass::text FROM pg_constraint "
    "WHERE contype = 'f' AND conparentid = 0 AND conrelid::regclass::text = ANY (:revised) "
    "UNION SELECT conrelid::regclass::text FROM pg_constraint "
    "WHERE contype = 'f' AND conparentid = 0 AND confrelid::regclass::text = ANY (:revised)"
)
# The keys of the advisory locks the transaction holds.
ADVISORY_KEYS = text(
    "SELECT (classid::bigint << 32) | objid::bigint FROM pg_locks "
    "WHERE locktype = 'advisory' AND pid = pg_backend_pid() AND granted"
)
# The creations asleep between two attempts at their locks — holding the advisory lock of the
# creations —, each with the tables of ``:locked`` it holds a lock on, granted.
ASLEEP = text(
    "SELECT ARRAY(SELECT held.relation::regclass::text FROM pg_locks AS held "
    "WHERE held.pid = activity.pid AND held.granted AND held.locktype = 'relation' "
    "AND held.relation::regclass::text = ANY (:locked)) "
    "FROM pg_stat_activity AS activity JOIN pg_locks AS creating ON creating.pid = activity.pid "
    "WHERE activity.datname = current_database() AND activity.wait_event = 'PgSleep' "
    "AND creating.locktype = 'advisory' AND creating.granted "
    "AND (creating.classid::bigint << 32) | creating.objid::bigint = :key"
)
NINE = [
    "cost_structure",
    "estimate_line",
    "node",
    "revision_calendar",
    "revision_category",
    "revision_rate",
    "revision_role",
    "task",
    "task_link",
]
ACT = Act(None, utc_now())


def asleep_holding_nothing(owner: Engine) -> None:
    """Wait, ten seconds at most, for a creation asleep that holds none of the tables it locks.

    A creation that kept its locks while it waits for another would never be seen so; one that
    gives them back is seen so at its first pause, or at the next if it was caught between two.
    """
    deadline = time.monotonic() + 10
    seen: list[list[str]] = []
    with owner.connect() as watching:
        revised = watching.scalars(REVISED_TABLES).all()
        locked = watching.scalars(LOCKED_TABLES, {"revised": revised}).all()
        assert len(locked) > len(revised)
        while time.monotonic() < deadline:
            seen = list(watching.scalars(ASLEEP, {"locked": locked, "key": PARTITIONS_LOCK}))
            if [] in seen:
                return
            watching.rollback()
            time.sleep(0.01)
    pytest.fail(f"no creation asleep without a lock on the tables it locks: {seen}")


def created_alone(database: Database, project_id: UUID) -> None:
    """Create the partitions of a project in a transaction of their own."""
    with database.transaction() as session:
        create_project_partitions(session, project_id)


def test_the_revised_tables_the_catalogue_partitions_by_project_are_the_nine_expected(
    owner: Engine,
) -> None:
    # What the function reads at each call: a table partitioned by another column, or by range,
    # would not be one; a table an epic adds enters by itself, and this list with it.
    with owner.connect() as connection:
        assert connection.scalars(REVISED_TABLES).all() == NINE


def test_the_creation_takes_the_advisory_lock_of_the_revisions_distinct_from_the_others(
    database: Database,
) -> None:
    # The key the function takes is the constant the revisions name, and no other lock of the
    # service shares it.
    with Session(database.engine) as session:
        create_project_partitions(session, uuid4())
        held = session.scalars(ADVISORY_KEYS).all()
        session.rollback()
    assert held == [PARTITIONS_LOCK]
    others = [
        INSTALL_LOCK,
        WITNESS_LOCK,
        REFERENCE_LOCK,
        NATURES_LOCK,
        RESTORE_LOCK,
        SCHEDULE_LOCK,
        PURGE_LOCK,
        RUN_LOCK,
        STACK_LOCK,
        TREE_LOCK,
        DEFAULT_LOCK,
        ADMINISTRATORS_LOCK,
        FORGETTING_LOCK,
    ]
    assert PARTITIONS_LOCK not in others


def test_the_creation_holds_no_access_exclusive_lock_on_a_relation_that_existed_before_it(
    database: Database,
) -> None:
    # ``PARTITION OF`` locked each parent ``ACCESS EXCLUSIVE``, which every reading waits for: the
    # attachment leaves that lock to the partitions it creates, their indexes and their toast.
    exclusive = text(
        "SELECT relation FROM pg_locks WHERE pid = pg_backend_pid() AND locktype = 'relation' "
        "AND mode = 'AccessExclusiveLock'"
    )
    with Session(database.engine) as session:
        before = set(session.scalars(text("SELECT oid FROM pg_class")))
        create_project_partitions(session, uuid4())
        held = set(session.scalars(exclusive))
        session.rollback()
    assert held
    assert held & before == set()


def test_a_reading_that_holds_the_nodes_then_reads_the_structures_does_not_meet_a_creation(
    database: Database,
) -> None:
    # #2603, step by step: a reading holds ``node``; a creation ends meanwhile, neither waiting
    # more than two seconds for a lock; the reading reads ``cost_structure`` after.
    timeout = text("SET LOCAL lock_timeout = '2s'")
    project_id = uuid4()
    with database.engine.connect() as reading, reading.begin():
        reading.execute(timeout)
        reading.execute(select(Node.id).limit(1)).all()
        with database.transaction() as creating:
            creating.execute(timeout)
            create_project_partitions(creating, project_id)
        reading.execute(select(CostStructure.id).limit(1)).all()
    with database.engine.connect() as connection:
        assert partition_of(project_id) in partitions(connection)


def test_a_creation_holds_nothing_while_a_write_holds_the_nodes_which_writes_the_structures(
    database: Database, owner: Engine
) -> None:
    # #2667: a write of a node of another project is open; the creation, which cannot take
    # ``node``, holds none of its tables between two attempts, and the write writes
    # ``cost_structure`` without waiting more than two seconds. Once it commits, the creation ends.
    project_id = uuid4()
    with projects_with_partitions(owner) as (other,):
        revision_id, structure_id = uuid4(), uuid4()
        with owner.begin() as connection:
            connection.execute(insert_revision(other, id=revision_id))
            connection.execute(insert_structure(other, revision_id, id=structure_id))
        with ThreadPoolExecutor(1) as pool:
            with database.engine.connect() as writing, writing.begin():
                writing.execute(text("SET LOCAL lock_timeout = '2s'"))
                writing.execute(insert(Node).values(**node_row(other, revision_id, structure_id)))
                creation = pool.submit(created_alone, database, project_id)
                asleep_holding_nothing(owner)
                writing.execute(
                    update(CostStructure)
                    .where(CostStructure.project_id == other, CostStructure.id == structure_id)
                    .values(label="Révisée")
                )
            creation.result(timeout=15)
        with database.engine.connect() as connection:
            assert partition_of(project_id) in partitions(connection)


def test_a_creation_that_finds_a_lock_held_ten_seconds_long_gives_up_holding_nothing(
    database: Database,
) -> None:
    # The attempts are bounded: past about ten seconds, ``lock_not_available`` (``55P03``), which
    # the service answers by a 500 it logs; the creation leaves no partition, and the write that
    # held the lock goes on.
    project_id = uuid4()
    with database.engine.connect() as writing, writing.begin():
        writing.execute(text("LOCK TABLE ONLY node IN ROW EXCLUSIVE MODE"))
        started = time.monotonic()
        with pytest.raises(DBAPIError) as refused:
            created_alone(database, project_id)
        waited = time.monotonic() - started
        writing.execute(select(Node.id).limit(1)).all()
    assert getattr(refused.value.orig, "sqlstate", None) == "55P03"
    assert 9 < waited < 15
    with database.engine.connect() as connection:
        assert partition_of(project_id) not in partitions(connection)


def test_eight_creations_of_a_project_at_once_meet_no_deadlock(
    database: Database, owner: Engine
) -> None:
    # As the service creates a project, its default work package and order item written after
    # the partitions: none of the eight fails, by a deadlock (``DeadlockDetected``) or otherwise.
    install(owner)
    complete_reference(database)
    start = Barrier(8)

    def create(rank: int) -> UUID:
        viewer = Viewer(uuid4(), ("all_projects_read",))
        start.wait(timeout=10)
        with logging_context(correlation_id=f"creation-{rank}"), database.transaction() as session:
            return create_project(session, ProjectDraft(f"Course {rank}"), ACT, viewer).project_id

    with ThreadPoolExecutor(8) as pool:
        created = list(pool.map(create, range(8), timeout=60))
    with database.engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(Project)) == 8
        assert {partition_of(project_id) for project_id in created} <= partitions(connection)
    assert len(set(created)) == 8
