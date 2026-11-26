# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A creation of a project takes a set of partitions the worker made in advance (US-2830/L4).

The creation of a project made its partitions itself, which locks the tables their keys bind: a
marking held it until it committed, or refused it (#4735). WF-ARC-0090-A — « Le marquage d'une
révision de dix mille objets n'immobilise aucune requête au-delà de la création de la tâche » —
is held of every request, the creation of a project included (decision of 2026-11-23): the
creation takes a set of the reserve with no DDL while a worker holds a marking, or an application
of an import, open; the worker fills the reserve once the marking is committed; with the reserve
empty, the creation makes its partitions as before, and waits; two creations take two sets.

The worker holds its task open by a handler that does the work of the platform's, then waits
before it returns, its transaction not committed.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Final, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from imports_trial import TrialFormat, analysed, apply, import_worker, stand_in, stored
from merges_support import AT_ONCE
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from psycopg.errors import LockNotAvailable
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.interface import (
    count_projects,
    fill_partition_reserve,
    partition_reserve_short,
    take_partitions,
)
from waterfall.core.projects.tables import PartitionReserve
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import BackgroundTask, RetriedError, Task, TaskHandler
from waterfall.worker import partition_reserve
from waterfall.worker.exchanges import ImportTasks
from waterfall.worker.marking import mark
from waterfall.worker.partition_reserve import ReserveTask
from waterfall.worker.runner import Worker
from waterfall.worker.schedule import Planned, deposit_due, reserve_short

if TYPE_CHECKING:
    from collections.abc import Mapping

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

SIZE = 3
# What the filling asks of the database, as a refusal names it.
STATEMENT = "SELECT reserve_project_partitions()"
FILLING: Final = "partition_reserve"
# The tables partitioned by the identifier of a project, as the functions of the partitions read
# them (migrations 0026 and 0055).
PARENTS = text(
    "SELECT count(*) FROM pg_partitioned_table AS partitioned "
    "JOIN pg_class AS parent ON parent.oid = partitioned.partrelid "
    "JOIN pg_attribute AS key "
    "ON key.attrelid = partitioned.partrelid AND key.attnum = partitioned.partattrs[0] "
    "WHERE parent.relnamespace = 'public'::regnamespace AND NOT parent.relispartition "
    "AND key.attname = 'project_id'"
)
# The partitions of a project, attached, by the suffix of their names.
PARTITIONS = text(
    "SELECT count(*) FROM pg_inherits JOIN pg_class AS child ON child.oid = inhrelid "
    "WHERE child.relname LIKE '%\\_p\\_' || :suffix"
)


@pytest.fixture
def services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API on the database, the queue and the bucket of the test."""
    return Services(
        database, keycloak, KeycloakAdmin(keycloak, realm_settings), queue, backups_bucket
    )


@pytest.fixture
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests, for the test."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


class Held:
    """A handler that does the work of another, then waits, its transaction open, until released."""

    def __init__(self, handler: TaskHandler) -> None:
        self.handler = handler
        self.done = threading.Event()
        self.released = threading.Event()

    def __call__(self, session: Session, task: Task) -> Mapping[str, Any] | None:
        """Do the work, written but not committed, and wait to be released."""
        result = self.handler(session, task)
        session.flush()
        self.done.set()
        assert self.released.wait(timeout=30)
        return result


def filled(database: Database, size: int = SIZE) -> list[UUID]:
    """Fill the reserve as the task of the worker does; give its sets in the order of the taking."""
    with database.transaction() as session:
        fill_partition_reserve(session, size)
    return reserved(database)


def reserved(database: Database) -> list[UUID]:
    """Give the sets of the reserve, in the order they are taken."""
    with database.transaction() as session:
        ordered = select(PartitionReserve.id).order_by(
            PartitionReserve.reserved_at, PartitionReserve.id
        )
        return list(session.scalars(ordered))


def whole(owner: Engine, project_id: UUID) -> bool:
    """Tell whether a project has its partition in every table partitioned by its identifier."""
    with owner.connect() as connection:
        parents = connection.scalar(PARENTS)
        held = connection.scalar(PARTITIONS, {"suffix": project_id.hex})
    return bool(parents) and held == parents


def fillings(database: Database) -> list[tuple[str, UUID | None]]:
    """Give the tasks of the filling: their state and their requester."""
    with database.transaction() as session:
        rows = session.execute(
            select(BackgroundTask.status, BackgroundTask.requested_by).where(
                BackgroundTask.kind == FILLING
            )
        )
        return [(status, requester) for status, requester in rows]


def created(api: ContractClient, stage: Scene, label: str = "Extension") -> Any:
    """Ask for the creation of a project, as the manager of the stage does; give the answer."""
    return api.post(PROJECTS, headers=stage.manager.headers, json={"label": label})


def marking_held(api: ContractClient, stage: Scene) -> None:
    """Open the current revision of the project of the stage and ask for its marking."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    revision = api.post(path, headers=stage.manager.headers, json={}).json()
    sent = {"version_name": "v1.0", "lock_version": revision["lock_version"]}
    marking = f"{path}/{revision['revision_id']}/mark"
    asked = api.post(marking, headers=stage.manager.headers, json=sent)
    assert asked.status_code == 202, asked.text


def a_task() -> Task:
    """Give a task of the filling as the worker hands it to its handler."""
    return Task(uuid4(), FILLING, {}, None, "reserve", 1)


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_project_is_created_while_the_worker_holds_a_marking_open(
    api: ContractClient, stage: Scene, database: Database, queue: TaskQueue
) -> None:
    # « Le marquage d'une révision de dix mille objets n'immobilise aucune requête au-delà de la
    # création de la tâche », the creation of a project included (#4735): the worker has marked,
    # its transaction is open, and a project is created at once — the first set of the reserve,
    # under its identifier — with a filling asked of the worker, for the platform.
    sets = filled(database)
    marking_held(api, stage)
    held = Held(mark)
    queue.prepare()
    worker = Worker(database, queue, {"revision_mark": held}, "worker", AT_ONCE)
    with ThreadPoolExecutor(1) as others:
        marking = others.submit(worker.step)
        assert held.done.wait(timeout=30)
        try:
            answer = created(api, stage)
            assert answer.status_code == 201, answer.text
            assert not marking.done()
        finally:
            held.released.set()
        assert marking.result(timeout=30)
    assert UUID(answer.json()["project_id"]) == sets[0]
    assert reserved(database) == sets[1:]
    assert whole(stage.owner, sets[0])
    assert fillings(database) == [("queued", None)]


@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.usefixtures("trial")
def test_a_project_is_created_while_the_worker_holds_the_application_of_an_import_open(
    api: ContractClient,
    stage: Scene,
    database: Database,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> None:
    # The same while an import is applied: the worker has written the tasks of the file in the
    # project, nodes and tasks the keys of a partition bind, and its transaction is open.
    found = analysed(api, stage, import_worker(database, queue, backups_bucket))
    assert apply(api, stage, found["import_id"]).status_code == 202
    sets = filled(database)
    held = Held(ImportTasks(backups_bucket).apply)
    worker = Worker(database, queue, {"import_apply": held}, "worker", AT_ONCE)
    with ThreadPoolExecutor(1) as others:
        applying = others.submit(worker.step)
        assert held.done.wait(timeout=30)
        try:
            answer = created(api, stage)
            assert answer.status_code == 201, answer.text
            assert not applying.done()
        finally:
            held.released.set()
        assert applying.result(timeout=30)
    assert UUID(answer.json()["project_id"]) == sets[0]
    assert stored(database, found["import_id"]).status == "applied"


@pytest.mark.requirement("WF-ARC-0090-A")
def test_the_reserve_is_filled_once_the_marking_is_committed(
    api: ContractClient, stage: Scene, database: Database, queue: TaskQueue
) -> None:
    # It is the worker that waits for the marking, never a request: the filling makes no set while
    # the marking is open, and makes them all once it is committed.
    marking_held(api, stage)
    held = Held(mark)
    queue.prepare()
    worker = Worker(database, queue, {"revision_mark": held}, "worker", AT_ONCE)

    def filling() -> Mapping[str, Any]:
        with database.transaction() as session:
            return ReserveTask(SIZE)(session, a_task())

    with ThreadPoolExecutor(2) as others:
        marking = others.submit(worker.step)
        assert held.done.wait(timeout=30)
        try:
            made = others.submit(filling)
            time.sleep(1)
            assert not made.done()
            assert reserved(database) == []
        finally:
            held.released.set()
        assert marking.result(timeout=30)
        assert made.result(timeout=30) == {"made": SIZE}
    sets = reserved(database)
    assert len(sets) == SIZE
    assert all(whole(stage.owner, each) for each in sets)


@pytest.mark.requirement("WF-ARC-0090-A")
def test_with_the_reserve_empty_the_creation_makes_its_partitions_and_waits_for_the_marking(
    api: ContractClient, stage: Scene, database: Database, queue: TaskQueue
) -> None:
    # The limit the documentation of operation states: the reserve empty, the creation makes its
    # partitions itself, as before — it waits for a marking that runs, and is created once it is
    # committed —, and asks no filling of the worker, the schedule doing it.
    marking_held(api, stage)
    held = Held(mark)
    queue.prepare()
    worker = Worker(database, queue, {"revision_mark": held}, "worker", AT_ONCE)
    with ThreadPoolExecutor(2) as others:
        marking = others.submit(worker.step)
        assert held.done.wait(timeout=30)
        try:
            creation = others.submit(created, api, stage)
            time.sleep(1)
            assert not creation.done()
        finally:
            held.released.set()
        assert marking.result(timeout=30)
        answer = creation.result(timeout=30)
    assert answer.status_code == 201, answer.text
    assert whole(stage.owner, UUID(answer.json()["project_id"]))
    assert reserved(database) == []
    assert fillings(database) == []


@pytest.mark.requirement("WF-ARC-0090-A")
def test_two_creations_together_take_two_sets_each_whole(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    # Two creations at once: the first holds its set until it commits, and the second takes
    # another, without waiting for it. Each project has all its partitions. Before, a set in
    # reserve is no project: the count of a backup's manifest does not see it.
    first, second = filled(database, 2)
    with database.transaction() as session:
        assert count_projects(session) == 1
    with database.transaction() as holding:
        assert take_partitions(holding) == first
        answer = created(api, stage)
        assert answer.status_code == 201, answer.text
        assert UUID(answer.json()["project_id"]) == second
    assert reserved(database) == []
    assert whole(stage.owner, first)
    assert whole(stage.owner, second)


@pytest.mark.story("US-2830")
def test_a_set_that_lacks_a_partition_is_never_taken(database: Database, owner: Engine) -> None:
    # Propre à l'US (notes de réalisation) : a set is taken whole or not at all — a table a later
    # migration partitions without making the partition of the sets in reserve makes no project
    # that lacks it: the creation makes its own partitions.
    (lacking,) = filled(database, 1)
    with owner.begin() as connection:
        connection.execute(text(f'DROP TABLE "revision_rate_p_{lacking.hex}"'))
    with database.transaction() as session:
        assert take_partitions(session) is None
    assert reserved(database) == [lacking]


@pytest.mark.story("US-2830")
def test_the_filling_makes_what_the_reserve_lacks_and_is_due_while_it_is_short(
    database: Database, queue: TaskQueue
) -> None:
    # Propre à l'US : the size of the reserve is an operating parameter, three sets; the filling
    # makes what the reserve lacks, nothing once it is full, and the schedule deposits it, for the
    # platform, only while the reserve holds fewer.
    plan = (Planned(FILLING, reserve_short(SIZE)),)
    with logging_context(correlation_id="schedule"):
        assert deposit_due(database, queue, plan) == [FILLING]
    with database.transaction() as session:
        assert ReserveTask(SIZE)(session, a_task()) == {"made": SIZE}
        assert ReserveTask(SIZE)(session, a_task()) == {"made": 0}
        assert not partition_reserve_short(session, SIZE)
        assert partition_reserve_short(session, SIZE + 1)
    with database.transaction() as session:
        session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.kind == FILLING)
            .values(status="succeeded", progress=100, finished_at=BackgroundTask.submitted_at)
        )
    with logging_context(correlation_id="schedule"):
        assert deposit_due(database, queue, plan) == []
    assert fillings(database) == [("succeeded", None)]


@pytest.mark.story("US-2830")
def test_a_filling_that_finds_the_locks_held_is_taken_again_and_no_other_error_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Propre à l'US : the creation of partitions gives up after ten seconds of locks held by a
    # marking (lock_not_available): the filling is then left to run again (RetriedError), the
    # sets it made undone; any other error of the database stays the error it is.
    def refused(cause: Exception) -> None:
        def fill(_session: Session, _size: int) -> int:
            raise OperationalError(STATEMENT, {}, cause)

        monkeypatch.setattr(partition_reserve.projects_interface, "fill_partition_reserve", fill)

    unused = cast("Session", None)
    refused(LockNotAvailable("could not obtain lock"))
    with pytest.raises(RetriedError) as stalled:
        ReserveTask(SIZE)(unused, a_task())
    assert isinstance(stalled.value.cause, OperationalError)
    refused(RuntimeError("other"))
    with pytest.raises(OperationalError):
        ReserveTask(SIZE)(unused, a_task())
