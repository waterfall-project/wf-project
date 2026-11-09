# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The immutability of a marked revision, held by the base (US-0970, WF-DAT-0020).

One table, one trigger: ``revision`` and ``cost_structure``, each guarded by a trigger of the
module of the revisions (migration 0020); ``node``, ``task`` and ``task_link``, by a trigger of the
module of the planning of the same form (migration 0022); what a review writes on a line of
estimate (migration 0027), by the guard of the estimate (migration 0025), whose other writes
``test_database_constraints_estimate.py`` tries. The rows are written around the service,
by the owner of the tables, whom the triggers refuse as they refuse the service. A revision is
opened through the service, and marked by the transaction of the worker (``mark_revision``).
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import give_a_line
from planning_support import insert_link, insert_task, main_structure, node_row, task_row
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from remaining_support import reviewed
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.interface import mark_revision
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import Base, utc_now
from waterfall.platform.identifiers import new_id
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Callable

    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.sql import Executable
    from support import ContractClient

    from waterfall.platform.database import Database

# What the guards say when they refuse (migration 0020).
ROW_REFUSED = "a row of a marked revision is never written"
REVISION_REFUSED = "a marked revision changes in its designation as reference alone"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def open_revision(api: ContractClient, stage: Scene) -> UUID:
    """Open the current revision of the project of the stage, as its manager does; give it."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return UUID(response.json()["revision_id"])


def mark(session: Session, revision_id: UUID) -> None:
    """Mark a revision by the transaction of the worker, in ``session``, which the caller ends."""
    with logging_context(correlation_id="marking"):
        mark_revision(session, revision_id, "v1.0", None, Act(None, utc_now()))


def marked_revision(api: ContractClient, stage: Scene) -> UUID:
    """Open a revision of the project of the stage, and mark it."""
    revision_id = open_revision(api, stage)
    with stage.database.transaction() as session:
        mark(session, revision_id)
    return revision_id


def structure_of(owner: Engine, revision_id: UUID) -> Any:
    """Read the main structure of a revision, every column."""
    with owner.connect() as connection:
        return connection.execute(
            select(CostStructure).where(CostStructure.revision_id == revision_id)
        ).one()


def second_structure(owner: Engine, revision_id: UUID) -> Executable:
    """Give the insertion of a structure into a revision beside its main one."""
    main = structure_of(owner, revision_id)
    identifier = new_id()
    row = {
        **main._asdict(),
        "id": identifier,
        "lineage_id": identifier,
        "label": "Seconde",
    }
    return insert(CostStructure).values(**row)


def changed_structure(_owner: Engine, revision_id: UUID) -> Executable:
    """Give the update of the label of the main structure of a revision."""
    return (
        update(CostStructure)
        .where(CostStructure.revision_id == revision_id)
        .values(label="Écrite pendant le marquage")
    )


def refused_by_owner(owner: Engine, statement: Executable, said: str) -> None:
    """Run a statement as the owner of the tables, and see it refused by the guard that says so."""
    with pytest.raises(IntegrityError, match=said), owner.begin() as connection:
        connection.execute(statement)


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_row_of_a_marked_revision_written_directly_in_the_base_is_refused(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # « Une mise à jour ou une suppression exécutée directement en base sur une tâche, une ligne de
    # devis ou une valeur de référentiel d'une révision marquée est rejetée par la base. » : here
    # ``cost_structure``, the revised table of this epic, written by its owner around the service;
    # an insertion as well. The rows stay as the marking left them.
    revision_id = marked_revision(api, stage)
    before = structure_of(owner, revision_id)
    refused_by_owner(
        owner,
        update(CostStructure)
        .where(CostStructure.revision_id == revision_id)
        .values(label="Changée"),
        ROW_REFUSED,
    )
    refused_by_owner(
        owner, delete(CostStructure).where(CostStructure.revision_id == revision_id), ROW_REFUSED
    )
    refused_by_owner(owner, second_structure(owner, revision_id), ROW_REFUSED)
    assert structure_of(owner, revision_id) == before


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_row_of_a_revision_in_progress_is_not_moved_into_a_marked_one(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # The update of ``revision_id`` is a write into the marked revision, which its owner is refused.
    marked = marked_revision(api, stage)
    in_progress = open_revision(api, stage)
    before = structure_of(owner, in_progress)
    refused_by_owner(
        owner,
        update(CostStructure)
        .where(CostStructure.revision_id == in_progress)
        .values(revision_id=marked),
        ROW_REFUSED,
    )
    assert structure_of(owner, in_progress) == before


@pytest.mark.requirement("WF-DAT-0020-A")
def test_the_owner_may_not_truncate_the_revisions_nor_their_structure_nor_a_partition_of_it(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # « … toute suppression, quel que soit le client » : TRUNCATE deletes without row, so the tables
    # refuse it by a statement trigger, on the parent of the partitions and on each partition.
    revision_id = marked_revision(api, stage)
    before = structure_of(owner, revision_id)
    partition = f"cost_structure_p_{str(stage.project['project_id']).replace('-', '')}"
    for table in ("revision", "cost_structure", partition):
        statement = text(f'TRUNCATE TABLE "{table}" CASCADE')
        with pytest.raises(DBAPIError, match="never truncated"), owner.begin() as connection:
            connection.execute(statement)
    assert structure_of(owner, revision_id) == before


@pytest.mark.requirement("WF-DAT-0020-A")
@pytest.mark.requirement("WF-REV-0090-A")
def test_a_marked_revision_never_becomes_current_again_nor_changes_but_its_designation(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # « … l'état d'une révision marquée ne redevient jamais « en cours ». » ; the update or the
    # deletion of a marked ``revision`` by its owner is refused, but its designation as reference,
    # which the designation writes with its counter and its audit (US-0980/L2).
    revision_id = marked_revision(api, stage)
    of_it = Revision.id == revision_id
    back = update(Revision).where(of_it).values(status="draft", version_name=None, marked_at=None)
    refused_by_owner(owner, back, REVISION_REFUSED)
    refused_by_owner(
        owner, update(Revision).where(of_it).values(version_name="v2"), REVISION_REFUSED
    )
    refused_by_owner(owner, delete(Revision).where(of_it), REVISION_REFUSED)
    with owner.begin() as connection:
        connection.execute(
            update(Revision)
            .where(of_it)
            .values(
                is_reference=True,
                lock_version=Revision.lock_version + 1,
                updated_at=utc_now(),
                updated_by=stage.manager.user_id,
            )
        )
    with owner.connect() as connection:
        status, name, reference = connection.execute(
            select(Revision.status, Revision.version_name, Revision.is_reference).where(of_it)
        ).one()
    assert (status, name, reference) == ("marked", "v1.0", True)


@pytest.mark.requirement("WF-DAT-0020-A")
@pytest.mark.parametrize(
    "write",
    [
        changed_structure,
        second_structure,
    ],
    ids=["update", "insert"],
)
def test_a_write_that_comes_during_the_marking_waits_for_it_and_is_refused(
    api: ContractClient,
    stage: Scene,
    owner: Engine,
    write: Callable[[Engine, UUID], Executable],
) -> None:
    # The marking locks the revision ``FOR UPDATE`` before it marks it (#2104): a writer of
    # ``cost_structure`` that comes meanwhile, the owner itself, waits for the marking, then reads
    # the revision marked and is refused; no row enters a marked revision.
    revision_id = open_revision(api, stage)
    before = structure_of(owner, revision_id)
    statement = write(owner, revision_id)

    def writing() -> None:
        with owner.begin() as connection:
            connection.execute(statement)

    with ThreadPoolExecutor(1) as others, Session(stage.database.engine) as marking:
        mark(marking, revision_id)
        written = others.submit(writing)
        wait_for_a_lock(stage.database)
        assert not written.done()
        marking.commit()
        with pytest.raises(IntegrityError, match=ROW_REFUSED):
            written.result(timeout=10)
    assert structure_of(owner, revision_id) == before


@pytest.mark.requirement("WF-DAT-0020-A")
def test_the_marking_waits_for_a_write_of_the_revision_begun_before_it(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # The other order (#2104): a write begun while the revision is current holds it under
    # ``FOR KEY SHARE``; the marking waits for it to end, and marks what it wrote.
    revision_id = open_revision(api, stage)

    def marking() -> None:
        with stage.database.transaction() as session:
            mark(session, revision_id)

    with ThreadPoolExecutor(1) as others, owner.connect() as writing:
        writing.execute(
            update(CostStructure)
            .where(CostStructure.revision_id == revision_id)
            .values(label="Écrite avant le marquage")
        )
        marked = others.submit(marking)
        wait_for_a_lock(stage.database)
        assert not marked.done()
        writing.commit()
        marked.result(timeout=10)
    assert structure_of(owner, revision_id).label == "Écrite avant le marquage"
    with stage.database.transaction() as session:
        assert session.scalar(select(Revision.status).where(Revision.id == revision_id)) == (
            "marked"
        )


# The revised tables of the planning (EP-06), guarded as the cost structures are (migration 0022).
PLANNED = (Node, Task, TaskLink)


@dataclass(frozen=True)
class Planned:
    """A revision with two tasks of its main structure, the first the predecessor of the second."""

    project_id: UUID
    revision_id: UUID
    structure_id: UUID
    first: UUID
    second: UUID


def planned_revision(api: ContractClient, stage: Scene, *, marked: bool = True) -> Planned:
    """Open a revision, give its main structure two linked tasks around the service; mark it."""
    revision_id = open_revision(api, stage)
    with stage.owner.begin() as connection:
        project_id, structure_id = main_structure(connection, revision_id)
        first = insert_task(connection, project_id, revision_id, structure_id)
        second = insert_task(connection, project_id, revision_id, structure_id, rank=2)
        connection.execute(insert_link(project_id, revision_id, structure_id, first, second))
    if marked:
        with stage.database.transaction() as session:
            mark(session, revision_id)
    return Planned(project_id, revision_id, structure_id, first, second)


def rows_of(owner: Engine, planned: Planned) -> list[tuple[object, ...]]:
    """Read every row of the planning of a project, every column, in a stable order."""
    with owner.connect() as connection:
        return [
            tuple(found)
            for table in (Base.metadata.tables[kept.__tablename__] for kept in PLANNED)
            for found in connection.execute(
                select(table)
                .where(table.c.project_id == planned.project_id)
                .order_by(*table.primary_key)
            )
        ]


def writes_of(table: type[Node | Task | TaskLink], planned: Planned) -> list[Executable]:
    """Give an update, a deletion and an insertion of a row of a table of the planning."""
    project_id, revision_id, structure_id = (
        planned.project_id,
        planned.revision_id,
        planned.structure_id,
    )
    if table is Node:
        mine = Node.id == planned.first
        added = node_row(project_id, revision_id, structure_id, rank=3)
        return [
            update(Node).where(mine).values(rank=9),
            delete(Node).where(mine),
            insert(Node).values(**added),
        ]
    if table is Task:
        facet = Task.node_id == planned.first
        return [
            update(Task).where(facet).values(label="Changée"),
            delete(Task).where(facet),
            insert(Task).values(**task_row(project_id, planned.first, structure_id)),
        ]
    link = TaskLink.predecessor_id == planned.first
    return [
        update(TaskLink).where(link).values(link_type="start_to_start"),
        delete(TaskLink).where(link),
        insert_link(project_id, revision_id, structure_id, planned.second, planned.first),
    ]


@pytest.mark.requirement("WF-DAT-0020-A")
@pytest.mark.parametrize("table", PLANNED, ids=["node", "task", "task_link"])
def test_a_task_or_a_link_of_a_marked_revision_written_directly_in_the_base_is_refused(
    api: ContractClient, stage: Scene, owner: Engine, table: type[Node | Task | TaskLink]
) -> None:
    # « Une mise à jour ou une suppression exécutée directement en base sur une tâche, une ligne de
    # devis ou une valeur de référentiel d'une révision marquée est rejetée par la base. » : a
    # node, its facet task and a link, written by the owner around the service; an insertion too.
    planned = planned_revision(api, stage)
    before = rows_of(owner, planned)
    for statement in writes_of(table, planned):
        refused_by_owner(owner, statement, ROW_REFUSED)
    assert rows_of(owner, planned) == before


def line_of(owner: Engine, node_id: UUID) -> tuple[object, ...]:
    """Read a line of estimate, every column."""
    with owner.connect() as connection:
        return tuple(
            connection.execute(select(EstimateLine).where(EstimateLine.node_id == node_id)).one()
        )


@pytest.mark.requirement("WF-DAT-0020-A")
def test_what_a_review_writes_on_a_line_of_a_marked_revision_written_directly_is_refused(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # « Une mise à jour ou une suppression exécutée directement en base sur une tâche, une ligne de
    # devis ou une valeur de référentiel d'une révision marquée est rejetée par la base. » : each of
    # the six columns EP-09 adds to a line (migration 0027) — its remaining to commit before the
    # review, the mark of its re-estimation, its reason —, written by the owner around the service,
    # is refused by the guard of the estimate (migration 0025), which they did not change.
    planned = planned_revision(api, stage, marked=False)
    with owner.begin() as connection:
        node_id = give_a_line(connection, planned.first)
    with stage.database.transaction() as session:
        mark(session, planned.revision_id)
    before = line_of(owner, node_id)
    for column, value in reviewed().items():
        written = (
            update(EstimateLine).where(EstimateLine.node_id == node_id).values({column: value})
        )
        refused_by_owner(owner, written, ROW_REFUSED)
    assert line_of(owner, node_id) == before


@pytest.mark.requirement("WF-DAT-0020-A")
def test_the_owner_may_not_truncate_the_tables_of_the_planning_nor_a_partition_of_them(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    planned = planned_revision(api, stage)
    before = rows_of(owner, planned)
    for table in ("node", "task", "task_link"):
        for truncated in (table, f"{table}_p_{planned.project_id.hex}"):
            statement = text(f'TRUNCATE TABLE "{truncated}" CASCADE')
            with pytest.raises(DBAPIError, match="never truncated"), owner.begin() as connection:
                connection.execute(statement)
    assert rows_of(owner, planned) == before


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_task_written_during_the_marking_waits_for_it_and_is_refused(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # The guard of the facet locks the revision through its node (#2104), as the others do.
    planned = planned_revision(api, stage, marked=False)
    before = rows_of(owner, planned)

    def writing() -> None:
        with owner.begin() as connection:
            connection.execute(
                update(Task).where(Task.node_id == planned.first).values(label="Pendant")
            )

    with ThreadPoolExecutor(1) as others, Session(stage.database.engine) as marking:
        mark(marking, planned.revision_id)
        written = others.submit(writing)
        wait_for_a_lock(stage.database)
        assert not written.done()
        marking.commit()
        with pytest.raises(IntegrityError, match=ROW_REFUSED):
            written.result(timeout=10)
    assert rows_of(owner, planned) == before


def refused_by_key(owner: Engine, statement: Executable, key: str) -> None:
    """Run a statement as the owner of the tables, and see it refused by the key named."""
    with pytest.raises(IntegrityError, match=key), owner.begin() as connection:
        connection.execute(statement)


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_row_of_a_current_revision_never_names_the_structure_or_a_node_of_a_marked_one(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    # The guards judge the revision a row names; the keys bind it to its structure, and the nodes
    # it names to that structure: a row written around the service with the revision in progress
    # and the structure, the parent, a task or the facet of a marked revision is refused, and the
    # marked revision gains nothing it could no longer lose.
    marked = planned_revision(api, stage)
    current = open_revision(api, stage)
    with owner.begin() as connection:
        project_id, structure_id = main_structure(connection, current)
        # After the two roots the copy of the marked revision brought (US-1380/L2).
        mine = insert_task(connection, project_id, current, structure_id, rank=3)
    before = rows_of(owner, marked)
    stray = node_row(project_id, current, marked.structure_id, rank=3)
    refused_by_key(owner, insert(Node).values(**stray), "fk_node_project_id_cost_structure")
    child = node_row(project_id, current, structure_id, rank=1, parent_id=marked.first)
    refused_by_key(owner, insert(Node).values(**child), "fk_node_project_id_node")
    refused_by_key(
        owner,
        insert_link(project_id, current, structure_id, marked.first, mine),
        "fk_task_link_predecessor_id_node",
    )
    refused_by_key(
        owner,
        insert_link(project_id, current, marked.structure_id, marked.second, marked.first),
        "fk_task_link_project_id_cost_structure",
    )
    refused_by_key(
        owner,
        update(Task).where(Task.node_id == mine).values(structure_id=marked.structure_id),
        "fk_task_node_id_node",
    )
    assert rows_of(owner, marked) == before
