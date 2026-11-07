# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The immutability of a marked revision, held by the base (US-0970, WF-DAT-0020).

One table, one trigger: ``revision`` and ``cost_structure``, each guarded by a trigger of the
module of the revisions (migration 0020). The rows are written around the service, by the owner of
the tables, whom the triggers refuse as they refuse the service. A revision is opened through the
service, and marked by the transaction of the worker (``mark_revision``).
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.revisions.interface import mark_revision
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
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
        statement = text(f'TRUNCATE TABLE "{table}" CASCADE')  # noqa: S608
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
