# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The history that can be undone: entries, undo, redo, conflicts.

Laid by US-1380/L1, the socle of EP-06; US-1450/L1 writes its tests here ("Les tests du back"). The
history reads no table of the planning: its tests pose the snapshots the planning would hand it, of
objects a ledger of the test holds and versions as the planning does — a write moves the version of
what it writes, a restoring too. The stacks are kept in the base of the tests, by revision, account
and session of sign-in, the ``sid`` of the token, which the API takes from it.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from project_rows import insert_revision, projects_with_partitions
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from realm import KEY, TestRealm
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session
from support import bearer, nowhere, raw_account, wait_for_a_lock

from waterfall.api.authentication import Caller, Services
from waterfall.core.history.interface import (
    PLAN_LIFETIME,
    REDO_HISTORY_NOT_EMPTY,
    UNDO_CONFLICT,
    UNDO_HISTORY_NOT_EMPTY,
    Depth,
    ObjectState,
    PlanToKeep,
    RecordedChange,
    Restoring,
    Snapshot,
    UndoneKind,
    UndoStack,
    depth,
    drop_plan,
    keep_plan,
    purge,
    read_plan,
    recording,
    redo,
    undo,
)
from waterfall.core.history.tables import PastePlan, UndoEntry
from waterfall.core.revisions.interface import mark_revision
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError, UnauthenticatedError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.settings import ServiceSettings

pytestmark = pytest.mark.requirement("WF-IHM-0110-A")

AT = datetime(2026, 11, 9, 8, tzinfo=UTC)
OFFICE = "sid-office"
HOME = "sid-home"


@dataclass
class Ledger:
    """The objects of the planning of a test, at their versions, as its snapshots give them."""

    stage: Stage
    objects: dict[UUID, ObjectState] = field(default_factory=dict[UUID, ObjectState])

    def read(self, object_ids: tuple[UUID, ...]) -> Snapshot:
        """Give the objects named as they are, those absent left out (the planning's snapshot)."""
        return tuple(self.objects[each] for each in object_ids if each in self.objects)

    def write(self, object_id: UUID, label: str | None) -> None:
        """Create or change an object at its next version, or delete it (``None``)."""
        current = self.objects.get(object_id)
        if label is None:
            del self.objects[object_id]
            return
        version = 0 if current is None else current.lock_version + 1
        rows: dict[str, Any] = {"task": {"label": label}, "links": [str(object_id)]}
        self.objects[object_id] = ObjectState(object_id, version, label, rows)

    def label(self, object_id: UUID) -> str | None:
        """Give the label of an object, ``None`` once deleted."""
        state = self.objects.get(object_id)
        return None if state is None else state.label


@dataclass(frozen=True)
class Stage:
    """A project with its current revision, and two accounts that write in it."""

    database: Database
    project: UUID
    revision: UUID
    claire: UUID
    lucas: UUID

    def stack(self, account: UUID | None = None, session_id: str = OFFICE) -> UndoStack:
        """Give the stack of an account — Claire's by default — in a session of sign-in."""
        return UndoStack(self.revision, account or self.claire, session_id)


@pytest.fixture
def stage(database: Database, owner: Engine) -> Iterator[Stage]:
    """Write a project, its current revision and two accounts, around the service."""
    with projects_with_partitions(owner) as (project,):
        revision, claire, lucas = uuid4(), uuid4(), uuid4()
        with database.engine.begin() as connection:
            for account in (claire, lucas):
                row = raw_account(id=account, email=f"{account}@example.org")
                connection.execute(insert(UserAccount).values(**row))
            connection.execute(insert_revision(project, id=revision))
        yield Stage(database, project, revision, claire, lucas)


def write(
    ledger: Ledger,
    stack: UndoStack,
    changes: dict[UUID, str | None],
    kind: UndoneKind = "cell",
    at: datetime = AT,
) -> None:
    """Write objects as the planning does, in one transaction framed by the history."""
    touched = tuple(changes)
    change = RecordedChange(ledger.stage.project, stack, kind, touched, at)
    with ledger.stage.database.transaction() as session, recording(session, change) as frame:
        frame.keep_before(ledger.read(touched))
        for object_id, label in changes.items():
            ledger.write(object_id, label)
        frame.keep_after(ledger.read(touched))


def restore(ledger: Ledger, restoring: Restoring) -> None:
    """Restore what an undoing or a redoing gives back, as the planning does: a write like any."""
    for state in restoring.restored:
        current = ledger.objects.get(state.object_id)
        version = (state.lock_version if current is None else current.lock_version) + 1
        ledger.objects[state.object_id] = replace(state, lock_version=version)
    for removed in restoring.removed:
        ledger.objects.pop(removed, None)
    touched = tuple(state.object_id for state in restoring.restored) + restoring.removed
    restoring.keep_present(ledger.read(touched))


def undone(ledger: Ledger, stack: UndoStack) -> Restoring:
    """Undo the last entry of a stack in a transaction of its own, restored by the ledger."""
    with (
        ledger.stage.database.transaction() as session,
        undo(session, stack, ledger.read) as restoring,
    ):
        restore(ledger, restoring)
    return restoring


def redone(ledger: Ledger, stack: UndoStack) -> Restoring:
    """Redo the last entry undone of a stack in a transaction of its own."""
    with (
        ledger.stage.database.transaction() as session,
        redo(session, stack, ledger.read) as restoring,
    ):
        restore(ledger, restoring)
    return restoring


def depth_of(stage: Stage, stack: UndoStack) -> Depth:
    """Read the depth of a stack."""
    with stage.database.transaction() as session:
        return depth(session, stack)


def refusal(error: pytest.ExceptionInfo[ConflictError]) -> tuple[str, dict[str, Any]]:
    """Give the code and the parameters of a refusal."""
    return error.value.code, dict(error.value.params)


def test_fifty_changes_are_undone_one_by_one_then_redone_in_order(stage: Stage) -> None:
    # « Cinquante modifications successives s'annulent une par une, puis se rétablissent dans
    # l'ordre. » By the module: fifty entries of the same task, each moving its version, so that
    # each undoing is judged on the version the undoing before it left.
    ledger, task, stack = Ledger(stage), uuid4(), stage.stack()
    write(ledger, stack, {task: "0"}, kind="node_create")
    for each in range(1, 50):
        write(ledger, stack, {task: str(each)})
    assert depth_of(stage, stack) == Depth(undoable=50, redoable=0)
    for each in reversed(range(1, 50)):
        restoring = undone(ledger, stack)
        assert (ledger.label(task), restoring.kind, restoring.node_ids) == (
            str(each - 1),
            "cell",
            (task,),
        )
        assert restoring.remaining_depth == each
    creation = undone(ledger, stack)
    assert (creation.kind, creation.removed, creation.remaining_depth) == (
        "node_create",
        (task,),
        0,
    )
    assert ledger.label(task) is None
    with pytest.raises(ConflictError) as empty:
        undone(ledger, stack)
    assert refusal(empty) == (
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": UNDO_HISTORY_NOT_EMPTY},
    )
    for each in range(50):
        restoring = redone(ledger, stack)
        assert (ledger.label(task), restoring.remaining_depth) == (str(each), 49 - each)
    with pytest.raises(ConflictError) as nothing:
        redone(ledger, stack)
    assert refusal(nothing) == (
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": REDO_HISTORY_NOT_EMPTY},
    )
    assert depth_of(stage, stack) == Depth(undoable=50, redoable=0)


def test_an_undo_of_a_change_another_contributor_took_up_is_refused_naming_it(
    stage: Stage,
) -> None:
    # « L'annulation d'une modification qu'un autre contributeur a depuis reprise est refusée en
    # nommant l'objet en conflit. » Judged on the version of each object the entry wrote: the
    # first one changed since is named, by its label of now; nothing is undone.
    ledger, task, other = Ledger(stage), uuid4(), uuid4()
    write(ledger, stage.stack(), {other: "Câblage", task: "Raccordement"})
    write(ledger, stage.stack(stage.lucas), {task: "Raccordement des borniers"})
    with pytest.raises(ConflictError) as conflict:
        undone(ledger, stage.stack())
    assert refusal(conflict) == (
        UNDO_CONFLICT,
        {
            "conflicting_object_id": str(task),
            "conflicting_object_label": "Raccordement des borniers",
        },
    )
    assert conflict.value.status == 409
    assert ledger.label(task) == "Raccordement des borniers"
    assert depth_of(stage, stage.stack()) == Depth(undoable=1, redoable=0)


def test_an_undo_of_a_change_to_an_object_deleted_since_names_it_by_its_last_label(
    stage: Stage,
) -> None:
    ledger, task = Ledger(stage), uuid4()
    write(ledger, stage.stack(), {task: "Essais"})
    write(ledger, stage.stack(stage.lucas), {task: None}, kind="node_delete")
    with pytest.raises(ConflictError) as conflict:
        undone(ledger, stage.stack())
    assert refusal(conflict)[1] == {
        "conflicting_object_id": str(task),
        "conflicting_object_label": "Essais",
    }


def test_a_redo_of_an_undo_another_contributor_took_up_is_refused_naming_it(stage: Stage) -> None:
    ledger, task = Ledger(stage), uuid4()
    write(ledger, stage.stack(), {task: "Pose"})
    write(ledger, stage.stack(), {task: "Pose des chemins"})
    undone(ledger, stage.stack())
    write(ledger, stage.stack(stage.lucas), {task: "Pose des goulottes"})
    with pytest.raises(ConflictError) as conflict:
        redone(ledger, stage.stack())
    assert refusal(conflict) == (
        UNDO_CONFLICT,
        {"conflicting_object_id": str(task), "conflicting_object_label": "Pose des goulottes"},
    )
    assert depth_of(stage, stage.stack()) == Depth(undoable=1, redoable=1)


def test_the_undo_of_a_deletion_gives_back_the_rows_as_they_were(stage: Stage) -> None:
    # The planning restores what the history gives back: the rows of the task, its links and its
    # inscriptions, as its snapshot held them before the deletion (US-1450/L2 restores them).
    ledger, task = Ledger(stage), uuid4()
    write(ledger, stage.stack(), {task: "Recette"}, kind="node_create")
    before = ledger.objects[task]
    write(ledger, stage.stack(), {task: None}, kind="node_delete")
    restoring = undone(ledger, stage.stack())
    assert (restoring.kind, restoring.removed) == ("node_delete", ())
    assert restoring.restored == (before,)
    assert ledger.objects[task].rows == before.rows


def test_a_new_change_deletes_the_entries_undone_of_its_stack(stage: Stage) -> None:
    ledger, task = Ledger(stage), uuid4()
    for label in ("a", "b", "c"):
        write(ledger, stage.stack(), {task: label})
    undone(ledger, stage.stack())
    undone(ledger, stage.stack())
    assert depth_of(stage, stage.stack()) == Depth(undoable=1, redoable=2)
    write(ledger, stage.stack(), {task: "d"})
    assert depth_of(stage, stage.stack()) == Depth(undoable=2, redoable=0)
    with stage.database.transaction() as session:
        ranks = session.scalars(select(UndoEntry.rank).order_by(UndoEntry.rank)).all()
    assert ranks == [1, 2]
    assert undone(ledger, stage.stack()).remaining_depth == 1
    assert ledger.label(task) == "a"


def test_a_stack_is_by_revision_by_account_and_by_session_of_sign_in(stage: Stage) -> None:
    ledger = Ledger(stage)
    write(ledger, stage.stack(), {uuid4(): "bureau"})
    write(ledger, stage.stack(session_id=HOME), {uuid4(): "maison"})
    write(ledger, stage.stack(session_id=HOME), {uuid4(): "maison encore"})
    assert depth_of(stage, stage.stack()) == Depth(undoable=1, redoable=0)
    assert depth_of(stage, stage.stack(session_id=HOME)) == Depth(undoable=2, redoable=0)
    assert depth_of(stage, stage.stack(stage.lucas)) == Depth(undoable=0, redoable=0)
    elsewhere = UndoStack(uuid4(), stage.claire, OFFICE)
    assert depth_of(stage, elsewhere) == Depth(undoable=0, redoable=0)


def test_a_write_or_a_restoring_that_hands_no_snapshot_keeps_nothing(stage: Stage) -> None:
    ledger, task = Ledger(stage), uuid4()
    change = RecordedChange(stage.project, stage.stack(), "cell", (task,), AT)
    with (
        pytest.raises(RuntimeError, match="snapshots"),
        stage.database.transaction() as session,
        recording(session, change) as frame,
    ):
        frame.keep_before(ledger.read((task,)))
    write(ledger, stage.stack(), {task: "Montage"})
    with (
        pytest.raises(RuntimeError, match="objects"),
        stage.database.transaction() as session,
        undo(session, stage.stack(), ledger.read),
    ):
        pass
    assert depth_of(stage, stage.stack()) == Depth(undoable=1, redoable=0)


def test_two_undoings_of_one_stack_at_once_undo_two_entries_one_after_the_other(
    stage: Stage,
) -> None:
    # Two undoings sent together, the second waits for the stack the first holds, then undoes the
    # entry under it, judged on the version the first left: never the same entry twice.
    ledger, task = Ledger(stage), uuid4()
    write(ledger, stage.stack(), {task: "un"})
    write(ledger, stage.stack(), {task: "deux"})
    write(ledger, stage.stack(), {task: "trois"})
    holding, release = threading.Event(), threading.Event()

    def first() -> Restoring:
        with stage.database.transaction() as session:
            with undo(session, stage.stack(), ledger.read) as restoring:
                holding.set()
                assert release.wait(10)
                restore(ledger, restoring)
            return restoring

    with ThreadPoolExecutor(max_workers=2) as pool:
        held = pool.submit(first)
        assert holding.wait(10)
        waiting = pool.submit(undone, ledger, stage.stack())
        wait_for_a_lock(stage.database)
        release.set()
        results = [held.result(timeout=10), waiting.result(timeout=10)]
    assert [each.remaining_depth for each in results] == [2, 1]
    assert ledger.label(task) == "un"
    assert depth_of(stage, stage.stack()) == Depth(undoable=1, redoable=2)


def test_the_purge_removes_the_entries_of_the_sessions_over_and_the_plans_expired(
    stage: Stage,
) -> None:
    ledger = Ledger(stage)
    write(ledger, stage.stack(), {uuid4(): "ancienne"}, at=AT - timedelta(hours=13))
    write(ledger, stage.stack(session_id=HOME), {uuid4(): "récente"}, at=AT)
    with stage.database.transaction() as session:
        expired = keep_plan(session, plan(stage), AT - PLAN_LIFETIME)
        alive = keep_plan(session, plan(stage), AT - timedelta(minutes=30))
    with stage.database.transaction() as session:
        purge(session, AT - timedelta(hours=12), AT)
    assert depth_of(stage, stage.stack()) == Depth(undoable=0, redoable=0)
    assert depth_of(stage, stage.stack(session_id=HOME)) == Depth(undoable=1, redoable=0)
    with stage.database.transaction() as session:
        plans = set(session.scalars(select(PastePlan.id)))
    assert expired.plan_id not in plans
    assert plans == {alive.plan_id}


def plan(stage: Stage, account: UUID | None = None) -> PlanToKeep:
    """Give the plan of a paste of an account — Claire's by default — on a structure."""
    return PlanToKeep(
        project_id=stage.project,
        revision_id=stage.revision,
        structure_id=STRUCTURE,
        user_account_id=account or stage.claire,
        target_node_id=uuid4(),
        target_column="label",
        rows=[{"label": "Câblage"}, {"label": "Essais"}],
        structure_lock_version=4,
    )


# The structure a plan of the tests targets: the plan names it without a key.
STRUCTURE = uuid4()


def test_a_plan_is_read_by_its_account_on_its_structure_for_an_hour_then_dropped(
    stage: Stage,
) -> None:
    with stage.database.transaction() as session:
        kept = keep_plan(session, plan(stage), AT)
    assert kept.expires_at == AT + timedelta(hours=1)
    with stage.database.transaction() as session:
        read = read_plan(session, kept.plan_id, STRUCTURE, stage.claire, AT + timedelta(minutes=59))
        assert read == kept
        assert read_plan(session, kept.plan_id, STRUCTURE, stage.lucas, AT) is None
        assert read_plan(session, kept.plan_id, uuid4(), stage.claire, AT) is None
        assert read_plan(session, kept.plan_id, STRUCTURE, stage.claire, kept.expires_at) is None
        drop_plan(session, kept.plan_id)
    with stage.database.transaction() as session:
        assert read_plan(session, kept.plan_id, STRUCTURE, stage.claire, AT) is None


@pytest.fixture
def scene(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def opened(api: ContractClient, scene: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the scene, as its manager does."""
    path = f"{PROJECTS}/{scene.project['project_id']}/revisions"
    response = api.post(path, headers=scene.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


def kept_in(scene: Scene, revision: dict[str, Any]) -> tuple[int, int]:
    """Keep two entries of two sessions and a plan in a revision; count what it holds then."""
    project, revision_id = UUID(scene.project["project_id"]), UUID(revision["revision_id"])
    stage = Stage(
        scene.database, project, revision_id, scene.manager.user_id, scene.manager.user_id
    )
    ledger = Ledger(stage)
    write(ledger, stage.stack(), {uuid4(): "Câblage"})
    write(ledger, stage.stack(session_id=HOME), {uuid4(): "Essais"})
    with scene.database.transaction() as session:
        keep_plan(session, replace(plan(stage), project_id=project), AT)
    return held_by(scene, revision_id)


def held_by(scene: Scene, revision_id: UUID) -> tuple[int, int]:
    """Count the entries and the plans of a revision."""
    with scene.database.transaction() as session:
        entries = session.scalar(
            select(func.count()).select_from(UndoEntry).where(UndoEntry.revision_id == revision_id)
        )
        plans = session.scalar(
            select(func.count()).select_from(PastePlan).where(PastePlan.revision_id == revision_id)
        )
    return entries or 0, plans or 0


def test_the_marking_and_the_abandonment_empty_the_history_of_the_revision(
    api: ContractClient, scene: Scene
) -> None:
    # « Aucune commande n'annule un marquage » : the marking and the abandonment delete the stacks
    # of every account and session, and the plans, of their revision, before it is written.
    marked = opened(api, scene)
    assert kept_in(scene, marked) == (2, 1)
    with (
        logging_context(correlation_id="marking"),
        Session(scene.owner) as session,
        session.begin(),
    ):
        mark_revision(session, UUID(marked["revision_id"]), "v1.0", None, Act(None, utc_now()))
    assert held_by(scene, UUID(marked["revision_id"])) == (0, 0)
    abandoned = opened(api, scene)
    assert kept_in(scene, abandoned) == (2, 1)
    path = f"{PROJECTS}/{scene.project['project_id']}/revisions/{abandoned['revision_id']}"
    response = api.delete(
        f"{path}?lock_version={abandoned['lock_version']}", headers=scene.manager.headers
    )
    assert response.status_code == 204, response.text
    assert held_by(scene, UUID(abandoned["revision_id"])) == (0, 0)


def test_the_session_of_sign_in_of_a_token_is_its_sid(keycloak: Keycloak, realm: TestRealm) -> None:
    # The stacks are kept by the session of sign-in, which the refreshes of the token keep.
    assert keycloak.validate(realm.token("kc-claire", KEY, claims={"sid": OFFICE})).session_id == (
        OFFICE
    )
    assert keycloak.validate(realm.token("kc-claire", KEY)).session_id is None
    for sid in ("", 42):
        with pytest.raises(UnauthenticatedError) as refused:
            keycloak.validate(realm.token("kc-claire", KEY, claims={"sid": sid}))
        assert refused.value.code == "SESSION_REQUIRED"


@pytest.fixture
def session_echo(
    database: Database, keycloak: Keycloak, realm_settings: ServiceSettings
) -> Iterator[TestClient]:
    """Serve a route that says the account and the session of its caller."""
    app = FastAPI()
    app.state.services = Services(
        database, keycloak, KeycloakAdmin(keycloak, realm_settings), *nowhere()
    )

    @app.get("/caller")
    def who(caller: Caller) -> dict[str, str | None]:
        return {"user_id": str(caller.user_id), "session_id": caller.session_id}

    with TestClient(app) as client:
        yield client


def test_the_caller_carries_the_session_of_sign_in_of_its_token(
    database: Database, realm: TestRealm, session_echo: TestClient
) -> None:
    row = raw_account(idp_subject="kc-claire")
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    for sid in (OFFICE, HOME):
        token = realm.token("kc-claire", KEY, claims={"sid": sid})
        answer = session_echo.get("/caller", headers=bearer(token)).json()
        assert answer == {"user_id": str(row["id"]), "session_id": sid}
