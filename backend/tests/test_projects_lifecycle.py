# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The cycle of life of a project (US-0980/L1; WF-CYC-0020 to WF-CYC-0130), by the service.

``getProjectNextState``, ``exitProject`` and ``listProjectStateTransitions`` on a project its
manager created (``projects_support``), every answer checked against the contract. The facts of
``next_state`` are tried without a base. In progress is reached through the designation of the
reference, which asks tasks and lines (EP-06, EP-07): the project is put there around the service,
by the owner of the tables, as the tests of the revisions put it in Pricing (the designation is
tried in ``test_reference_designation``, the exit that marks in ``test_exit_marking``).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from projects_support import MANAGING, PROJECTS, Scene, contribute, create, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.projects.interface import (
    ExitRequest,
    NextState,
    Viewer,
    advance,
    exit_project,
    next_state,
)
from waterfall.core.projects.tables import Project, ProjectStateTransition
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ConflictError
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

AT = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
ABANDONING: dict[str, Any] = {"action": "abandon"}
MARKING: dict[str, Any] = {"action": "mark", "version_name": "Clôture"}
NOT_FOUND = "NOT_FOUND"
CREATED, PRICING, IN_PROGRESS = "created", "pricing", "in_progress"
TERMINAL = ("completed", "lost", "abandoned")


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


def path_of(stage: Scene, tail: str) -> str:
    """Give the path of an operation on the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/{tail}"


def project_path(stage: Scene) -> str:
    """Give the path of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def project_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the project of the stage, as its manager does."""
    response = api.get(f"{PROJECTS}/{stage.project['project_id']}", headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def missing(listed: dict[str, Any]) -> dict[str, list[str]]:
    """Give the conditions each command of an object lacks, by command."""
    return {each["command"]: each["missing_conditions"] for each in listed["available_commands"]}


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def leave(api: ContractClient, stage: Scene, to_state: str, **body: Any) -> Any:
    """Exit the project of the stage as its manager does, confirmed, at the counter it has."""
    sent = {
        "to_state": to_state,
        "confirmed": True,
        "lock_version": project_of(api, stage)["lock_version"],
        **body,
    }
    return api.post(path_of(stage, "exit"), headers=stage.manager.headers, json=sent)


def transitions(api: ContractClient, stage: Scene) -> list[dict[str, Any]]:
    """Read the transitions of the project of the stage, as its manager does."""
    response = api.get(path_of(stage, "state-transitions"), headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def next_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the next state of the project of the stage, as its manager does."""
    response = api.get(path_of(stage, "next-state"), headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    response = api.post(path_of(stage, "revisions"), headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


def pend_marking(api: ContractClient, stage: Scene) -> None:
    """Open the current revision and ask for its marking: a real task of the queue, pending."""
    revision = open_revision(api, stage)
    asked = api.post(
        path_of(stage, f"revisions/{revision['revision_id']}/mark"),
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text


def state_in_the_base(stage: Scene) -> tuple[str, int]:
    """Read the state and the counter of the project of the stage, as the base keeps them."""
    with stage.database.transaction() as session:
        project = session.get_one(Project, UUID(stage.project["project_id"]))
        return project.state, project.lock_version


def in_progress_around(stage: Scene) -> None:
    """Put the project in progress around the service, its transition written as the owner does."""
    put_in_state(stage.owner, stage.project["project_id"], IN_PROGRESS)
    with stage.owner.begin() as connection:
        connection.execute(
            insert(ProjectStateTransition).values(
                id=new_id(),
                project_id=UUID(stage.project["project_id"]),
                from_state=PRICING,
                to_state=IN_PROGRESS,
                occurred_at=AT,
                actor_user_id=stage.manager.user_id,
            )
        )


@pytest.mark.requirement("WF-CYC-0050-A")
@pytest.mark.requirement("WF-CYC-0020-A")
@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (
            (CREATED, False, False, False),
            NextState(CREATED, PRICING, "first_revision_created", ()),
        ),
        (
            (PRICING, True, False, False),
            NextState(
                PRICING,
                IN_PROGRESS,
                "reference_designated_and_code_set",
                ("project_code_set", "reference_revision_designated"),
            ),
        ),
        (
            (PRICING, True, False, True),
            NextState(
                PRICING,
                IN_PROGRESS,
                "reference_designated_and_code_set",
                ("reference_revision_designated",),
            ),
        ),
        (
            (PRICING, True, True, False),
            NextState(
                PRICING, IN_PROGRESS, "reference_designated_and_code_set", ("project_code_set",)
            ),
        ),
        (
            (PRICING, True, True, True),
            NextState(PRICING, IN_PROGRESS, "reference_designated_and_code_set", ()),
        ),
        *[((state, True, True, True), NextState(state)) for state in (IN_PROGRESS, *TERMINAL)],
    ],
)
def test_the_next_state_is_a_function_of_the_facts_alone(
    facts: tuple[str, bool, bool, bool], expected: NextState
) -> None:
    # « Pour un projet dans chacun des états Créé et Chiffrage, l'utilisateur consulte le prochain
    # état, son déclencheur et les conditions restantes » ; nothing after In progress: no fact.
    state, has_revision, has_reference, has_code = facts
    assert (
        next_state(state, has_revision=has_revision, has_reference=has_reference, has_code=has_code)
        == expected
    )


@pytest.mark.requirement("WF-CYC-0050-A")
@pytest.mark.requirement("WF-PRJ-0010-A")
def test_the_next_state_is_read_in_each_state_without_trying_an_action(
    api: ContractClient, stage: Scene
) -> None:
    # « l'utilisateur consulte le prochain état, son déclencheur et les conditions restantes » ;
    # « la condition manquante est nommée » : the code, then the reference.
    assert next_of(api, stage) == {
        "current_state": CREATED,
        "next_state": PRICING,
        "trigger": "first_revision_created",
        "missing_conditions": [],
    }
    open_revision(api, stage)
    assert next_of(api, stage) == {
        "current_state": PRICING,
        "next_state": IN_PROGRESS,
        "trigger": "reference_designated_and_code_set",
        "missing_conditions": ["project_code_set", "reference_revision_designated"],
    }
    coded = api.patch(
        project_path(stage),
        headers=stage.manager.headers,
        json={"code": "PRJ-080", "lock_version": project_of(api, stage)["lock_version"]},
    )
    assert coded.status_code == 200, coded.text
    assert next_of(api, stage)["missing_conditions"] == ["reference_revision_designated"]
    in_progress_around(stage)
    assert next_of(api, stage) == {
        "current_state": IN_PROGRESS,
        "next_state": None,
        "trigger": None,
        "missing_conditions": [],
    }


@pytest.mark.requirement("WF-CYC-0020-A")
@pytest.mark.requirement("WF-CYC-0130-A")
def test_the_first_revision_moves_the_project_to_pricing_in_its_own_transaction(
    api: ContractClient, stage: Scene
) -> None:
    # « Chacun de ces états est atteint dès que son fait déclencheur est réalisé, sans autre
    # action. » ; the transition is dated of the instant of the opening, its author the account
    # that opened the revision, and a second revision moves nothing.
    revision = open_revision(api, stage)
    project = project_of(api, stage)
    assert project["state"] == PRICING
    [first, second] = transitions(api, stage)
    assert (first["from_state"], first["to_state"], first["reason"]) == (None, CREATED, None)
    assert (second["from_state"], second["to_state"], second["reason"]) == (CREATED, PRICING, None)
    assert second["occurred_at"] == revision["audit"]["created_at"]
    assert second["actor"]["user_id"] == str(stage.manager.user_id)
    assert project["lock_version"] == stage.project["lock_version"] + 1, (
        "the opening moves the counter once, advance not again"
    )
    assert len(transitions(api, stage)) == 2


@pytest.mark.requirement("WF-CYC-0030-A")
def test_the_code_and_the_reference_move_the_project_to_in_progress_in_either_order(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    # « Un projet dont la référence est désignée avant le code projet passe à En cours à la saisie
    # du code ; un projet dont le code est saisi avant la désignation y passe à la désignation. »
    # The reference is put around the service here (``test_reference_designation`` designates it).
    revision = open_revision(api, stage)
    with stage.owner.begin() as connection:
        connection.execute(
            update(Revision)
            .where(Revision.id == UUID(revision["revision_id"]))
            .values(status="marked", version_name="v1", marked_at=AT)
        )
        connection.execute(
            update(Project)
            .where(Project.id == UUID(stage.project["project_id"]))
            .values(current_revision_id=None, reference_revision_id=UUID(revision["revision_id"]))
        )
    coded = api.patch(
        project_path(stage),
        headers=stage.manager.headers,
        json={"code": "PRJ-081", "lock_version": project_of(api, stage)["lock_version"]},
    )
    assert coded.status_code == 200, coded.text
    assert coded.json()["state"] == IN_PROGRESS
    last = transitions(api, stage)[-1]
    assert (last["from_state"], last["to_state"]) == (PRICING, IN_PROGRESS)
    assert last["occurred_at"] == coded.json()["audit"]["updated_at"]
    assert last["actor"]["user_id"] == str(stage.manager.user_id)
    # The other order: the code first, the designation (a call of the module) second.
    other = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "Autre", "code": "X"})
    assert other.status_code == 201, other.text
    other_id = UUID(other.json()["project_id"])
    put_in_state(stage.owner, str(other_id), PRICING)
    with database.transaction() as session:
        session.get_one(Project, other_id).reference_revision_id = UUID(revision["revision_id"])
        advance(session, other_id, "reference_designated_and_code_set", Act(None, AT))
        assert session.get_one(Project, other_id).state == IN_PROGRESS
    with database.transaction() as session:
        final = session.scalars(
            select(ProjectStateTransition).where(
                ProjectStateTransition.project_id == other_id,
                ProjectStateTransition.to_state == IN_PROGRESS,
            )
        ).one()
        assert (final.to_state, final.occurred_at, final.actor_user_id) == (IN_PROGRESS, AT, None)


@pytest.mark.requirement("WF-CYC-0020-A")
def test_no_operation_leads_to_pricing_or_in_progress_by_an_exit(
    api: ContractClient, stage: Scene
) -> None:
    # « Aucun écran ne propose de commande menant à Chiffrage ou En cours. » : an exit names a
    # terminal state alone, and the commands of the project are three exits, none of them leading
    # there.
    for state in (PRICING, IN_PROGRESS, CREATED):
        refused = leave(api, stage, state)
        assert refused.status_code == 422
    assert state_in_the_base(stage)[0] == CREATED
    commands = missing(project_of(api, stage))
    # What the project lists besides the commands that change it is its exits, and exactly three.
    changing = {
        "update",
        "update_win_probability",
        "update_work_breakdown",
        "manage_timelines",
        "manage_contributors",
        "create_revision",
    }
    assert set(commands) - changing == {"complete", "lose", "abandon"}


@pytest.mark.requirement("WF-CYC-0060-A")
@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (
            CREATED,
            {"complete": ["project_in_progress"], "lose": ["project_in_pricing"], "abandon": []},
        ),
        (PRICING, {"complete": ["project_in_progress"], "lose": [], "abandon": []}),
        (IN_PROGRESS, {"complete": [], "abandon": []}),
    ],
)
def test_the_commands_of_the_exits_follow_the_state(
    api: ContractClient, stage: Scene, state: str, expected: dict[str, list[str]]
) -> None:
    # « le menu des sorties ne permet que les sorties permises depuis cet état » ; « Terminer
    # depuis Chiffrage y est présentée indisponible, avec sa condition […] ; Déclarer perdu depuis
    # En cours n'y figure pas. » The state is put around the service.
    put_in_state(stage.owner, stage.project["project_id"], state)
    commands = missing(project_of(api, stage))
    assert {name: commands[name] for name in expected} == expected
    assert ("lose" in commands) == ("lose" in expected)


@pytest.mark.requirement("WF-CYC-0060-A")
@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.requirement("WF-CYC-0130-A")
@pytest.mark.parametrize(
    ("state", "to_state"),
    [
        (IN_PROGRESS, "completed"),
        (PRICING, "lost"),
        (CREATED, "abandoned"),
        (PRICING, "abandoned"),
        (IN_PROGRESS, "abandoned"),
    ],
)
def test_each_exit_the_state_permits_is_applied_with_its_reason(
    api: ContractClient, stage: Scene, state: str, to_state: str
) -> None:
    # « Terminé depuis En cours, Perdu depuis Chiffrage, Abandonné depuis tout état non
    # terminal » ; « Une sortie à Perdu confirmée avec un motif présente ce motif dans
    # l'historique ; une transition automatique n'en porte aucun. » ; the project, read-only, lists
    # no command and bears no current revision.
    put_in_state(stage.owner, stage.project["project_id"], state)
    answer = leave(api, stage, to_state, reason="Le client a changé d'avis")
    assert answer.status_code == 200, answer.text
    project = answer.json()
    assert (project["state"], project["current_revision_id"]) == (to_state, None)
    assert project["available_commands"] == []
    last = transitions(api, stage)[-1]
    assert (last["from_state"], last["to_state"], last["reason"]) == (
        state,
        to_state,
        "Le client a changé d'avis",
    )
    assert last["occurred_at"] == project["audit"]["updated_at"]
    assert last["actor"]["user_id"] == str(stage.manager.user_id)
    assert next_of(api, stage)["next_state"] is None


@pytest.mark.requirement("WF-CYC-0090-A")
def test_an_exit_confirmed_without_a_reason_is_applied(api: ContractClient, stage: Scene) -> None:
    # « une sortie confirmée sans motif est appliquée » : the transition bears no reason.
    assert leave(api, stage, "abandoned").status_code == 200
    assert transitions(api, stage)[-1]["reason"] is None
    assert len(transitions(api, stage)) == 2


@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.parametrize("sent", [{"confirmed": False}, {"confirmed": None}, {}])
def test_an_exit_not_confirmed_is_refused_and_writes_nothing(
    api: ContractClient, stage: Scene, sent: dict[str, Any]
) -> None:
    # « La confirmation nomme l'état visé […] » : the guard is a 400, before anything is read.
    body = {"to_state": "abandoned", "lock_version": 0, **sent}
    answer = api.post(path_of(stage, "exit"), headers=stage.manager.headers, json=body)
    assert refusal(answer) == (400, "CONFIRMATION_REQUIRED", {})
    assert state_in_the_base(stage) == (CREATED, stage.project["lock_version"])
    assert len(transitions(api, stage)) == 1


@pytest.mark.requirement("WF-CYC-0060-A")
@pytest.mark.requirement("WF-CYC-0080-A")
@pytest.mark.parametrize(
    ("state", "to_state", "condition"),
    [
        (CREATED, "completed", "project_in_progress"),
        (PRICING, "completed", "project_in_progress"),
        (CREATED, "lost", "project_in_pricing"),
        (IN_PROGRESS, "lost", "project_in_pricing"),
        *[(state, to, "project_not_terminal") for state in TERMINAL for to in TERMINAL],
    ],
)
def test_an_exit_the_state_does_not_permit_is_refused_naming_its_condition(
    api: ContractClient, stage: Scene, state: str, to_state: str, condition: str
) -> None:
    # « Toute tentative de transition depuis Terminé, Perdu ou Abandonné est refusée. » : the 409
    # names the first condition the command of the exit lacks, a terminal project's first.
    put_in_state(stage.owner, stage.project["project_id"], state)
    before = state_in_the_base(stage)
    answer = leave(api, stage, to_state)
    assert refusal(answer) == (409, "STATE_FORBIDS_OPERATION", {"missing_condition": condition})
    assert state_in_the_base(stage) == before


@pytest.mark.requirement("WF-CYC-0080-A")
@pytest.mark.requirement("WF-CYC-0100-A")
@pytest.mark.requirement("WF-CYC-0110-A")
def test_a_terminal_project_refuses_every_write_and_gives_every_reading(
    api: ContractClient, stage: Scene
) -> None:
    # « Toute modification d'un projet terminal est refusée » ; « Toutes les vues de consultation
    # d'un projet clos s'affichent normalement » ; « Seules les modifications sont refusées. »
    assert leave(api, stage, "abandoned").status_code == 200
    terminal = {"missing_condition": "project_not_terminal"}
    project = project_of(api, stage)
    revision = api.post(path_of(stage, "revisions"), headers=stage.manager.headers, json={})
    assert refusal(revision) == (409, "STATE_FORBIDS_OPERATION", terminal)
    change = {"label": "Autre", "lock_version": project["lock_version"]}
    patch = api.patch(project_path(stage), headers=stage.manager.headers, json=change)
    assert refusal(patch) == (409, "STATE_FORBIDS_OPERATION", terminal)
    for tail in ("revisions", "state-transitions", "next-state", "contributors"):
        assert api.get(path_of(stage, tail), headers=stage.manager.headers).status_code == 200
    assert project["available_commands"] == []


@pytest.mark.requirement("WF-CYC-0090-A")
def test_an_exit_of_a_project_with_a_current_revision_asks_what_becomes_of_it(
    api: ContractClient, stage: Scene
) -> None:
    # « La sortie d'un projet qui porte une révision en cours demande de la marquer ou de
    # l'abandonner » : without its fate, 422 on /current_revision; nothing is written.
    revision = open_revision(api, stage)
    before = state_in_the_base(stage)
    for sent in ({}, {"current_revision": None}):
        answer = leave(api, stage, "abandoned", **sent)
        body = answer.json()
        assert (answer.status_code, body["code"]) == (422, "VALIDATION_FAILED")
        assert body["fields"] == [{"pointer": "/current_revision", "code": "VALUE_REQUIRED"}]
    assert state_in_the_base(stage) == before
    assert project_of(api, stage)["current_revision_id"] == revision["revision_id"]


@pytest.mark.requirement("WF-CYC-0090-A")
@pytest.mark.requirement("WF-SEC-0030-A")
def test_an_exit_that_abandons_the_current_revision_leaves_the_project_without_one(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    # « après la sortie, le projet n'a plus de révision en cours » : 200 and the project, the
    # abandonment and the exit in the journal under one correlation, the revision gone.
    revision = open_revision(api, stage)
    answer = leave(api, stage, "abandoned", current_revision=ABANDONING, reason="Plus de budget")
    assert answer.status_code == 200, answer.text
    assert (answer.json()["state"], answer.json()["current_revision_id"]) == ("abandoned", None)
    assert answer.json()["lock_version"] > stage.project["lock_version"]
    with database.transaction() as session:
        assert session.get(Revision, UUID(revision["revision_id"])) is None
        entries = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.action.in_(["revision_abandon", "project_exit"]))
            .order_by(AuditEntry.id)
        ).all()
        assert [entry.action for entry in entries] == ["revision_abandon", "project_exit"]
        assert len({entry.correlation_id for entry in entries}) == 1
        exit_entry = entries[1]
        assert (exit_entry.object_kind, exit_entry.object_id, exit_entry.object_label) == (
            "project",
            UUID(stage.project["project_id"]),
            stage.project["label"],
        )
        assert exit_entry.params == {"to_state": "abandoned", "reason": "Plus de budget"}
        assert exit_entry.actor_user_id == stage.manager.user_id
    auditor = person(database, realm, "audit_log.read", name="Ada")
    journal = api.get("/api/v1/audit-events?actions=project_exit", headers=auditor.headers)
    assert journal.status_code == 200
    assert [event["action"] for event in journal.json()["items"]] == ["project_exit"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_exit_at_a_stale_counter_is_refused_naming_the_counter(
    api: ContractClient, stage: Scene
) -> None:
    # The counter of the project read: refused, nothing written, even with a revision to abandon.
    open_revision(api, stage)
    current = project_of(api, stage)["lock_version"]
    for sent in ({}, {"current_revision": ABANDONING}):
        answer = leave(api, stage, "abandoned", lock_version=current - 1, **sent)
        assert refusal(answer) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": current})
    assert state_in_the_base(stage) == (PRICING, current)
    assert project_of(api, stage)["current_revision_id"] is not None


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_an_exit_is_reserved_to_the_managers_of_the_project(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    # Reserved to the project managers: a participant who is no manager, and a stranger, are
    # refused, naming what they lack; the reader, who may not even open it, is not found.
    body = {"to_state": "abandoned", "confirmed": True, "lock_version": 0}
    path = path_of(stage, "exit")
    participant = api.post(path, headers=stage.participant.headers, json=body)
    assert refusal(participant)[:2] == (403, "NOT_PROJECT_MANAGER")
    outsider = api.post(path, headers=stage.outsider.headers, json=body)
    assert outsider.status_code == 404
    contribute(database, stage.project["project_id"], stage.reader, "contributor")
    assert api.post(path, headers=stage.reader.headers, json=body).status_code == 403
    assert state_in_the_base(stage)[0] == CREATED


@pytest.mark.requirement("WF-CYC-0080-A")
def test_two_exits_at_once_exit_the_project_once(api: ContractClient, stage: Scene) -> None:
    # Under the lock of the project: the second exit waits for the first, reads the counter it
    # moved and is refused, not applied on top of it.
    body = {
        "to_state": "abandoned",
        "confirmed": True,
        "lock_version": project_of(api, stage)["lock_version"],
    }
    path = path_of(stage, "exit")
    with ThreadPoolExecutor(2) as others, Session(stage.database.engine) as holding:
        holding.execute(
            select(Project.id)
            .where(Project.id == UUID(stage.project["project_id"]))
            .with_for_update()
        )
        exits = [
            others.submit(api.post, path, headers=stage.manager.headers, json=body)
            for _ in range(2)
        ]
        wait_for_a_lock(stage.database)
        holding.commit()
        answers = sorted(each.result(timeout=10).status_code for each in exits)
    assert answers == [200, 412]
    assert [item["to_state"] for item in transitions(api, stage)] == [CREATED, "abandoned"]


@pytest.mark.requirement("WF-CYC-0080-A")
def test_two_exits_abandoning_the_same_revision_at_once_exit_the_project_once(
    api: ContractClient, stage: Scene
) -> None:
    # Both abandon the revision: the second waits for the lock of the revision, finds it deleted
    # and is told the counter moved (412), not that the revision is unknown (404).
    revision = open_revision(api, stage)
    body = {
        "to_state": "abandoned",
        "confirmed": True,
        "lock_version": project_of(api, stage)["lock_version"],
        "current_revision": ABANDONING,
    }
    path = path_of(stage, "exit")
    with ThreadPoolExecutor(2) as others, Session(stage.database.engine) as holding:
        holding.execute(
            select(Revision.id)
            .where(Revision.id == UUID(revision["revision_id"]))
            .with_for_update()
        )
        exits = [
            others.submit(api.post, path, headers=stage.manager.headers, json=body)
            for _ in range(2)
        ]
        wait_for_a_lock(stage.database)
        holding.commit()
        answers = sorted(each.result(timeout=10).status_code for each in exits)
    assert answers == [200, 412]
    with stage.database.transaction() as session:
        actions = session.scalars(
            select(AuditEntry.action).where(
                AuditEntry.action.in_(["revision_abandon", "project_exit"])
            )
        ).all()
        assert sorted(actions) == ["project_exit", "revision_abandon"]
    assert [item["to_state"] for item in transitions(api, stage)] == [CREATED, PRICING, "abandoned"]


@pytest.mark.requirement("WF-CYC-0060-A")
def test_the_first_condition_of_the_contract_is_told_before_the_revision_is_abandoned(
    api: ContractClient, stage: Scene
) -> None:
    # A Pricing project with a current revision and a marking of it pending, a real task of the
    # queue: the state (``project_in_progress``) is told, not the task of the revision, and
    # nothing is abandoned.
    pend_marking(api, stage)
    before = state_in_the_base(stage)
    answer = leave(api, stage, "completed", current_revision=ABANDONING)
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "project_in_progress"},
    )
    assert state_in_the_base(stage) == before
    assert project_of(api, stage)["current_revision_id"] is not None


@pytest.mark.requirement("WF-CYC-0060-A")
def test_a_marking_pending_in_the_queue_refuses_the_exit_that_would_abandon_the_revision(
    api: ContractClient, stage: Scene
) -> None:
    pend_marking(api, stage)
    before = state_in_the_base(stage)
    answer = leave(api, stage, "abandoned", current_revision=ABANDONING)
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_background_task_running"},
    )
    assert state_in_the_base(stage) == before


@pytest.mark.requirement("WF-CYC-0060-A")
def test_the_exit_reads_the_tasks_under_the_lock_not_as_its_caller_read_them(
    api: ContractClient, stage: Scene
) -> None:
    # The caller read no task running, and a marking was deposited before the lock was taken: the
    # exit judges the task it finds under the lock (#2220).
    pend_marking(api, stage)
    request = ExitRequest(
        "abandoned", None, project_of(api, stage)["lock_version"], tasks_under_lock=True
    )
    assert request.no_task_running
    with pytest.raises(ConflictError) as refused, stage.database.transaction() as session:
        exit_project(
            session,
            UUID(stage.project["project_id"]),
            request,
            Act(stage.manager.user_id, utc_now()),
            Viewer(stage.manager.user_id, ()),
        )
    assert (refused.value.code, dict(refused.value.params)) == (
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_background_task_running"},
    )


@pytest.mark.requirement("WF-ADM-0100-A")
def test_an_exit_abandoning_the_revision_asks_for_the_permission_to_abandon_one(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # The exit deletes the revision: it asks for ``revision_abandon`` as ``abandonRevision`` does.
    database = stage.database
    chief = person(
        database, realm, *(each for each in MANAGING if each != "revision_abandon"), name="Zoé"
    )
    project = create(api, chief, label="Sans abandon")
    path = f"{PROJECTS}/{project['project_id']}"
    assert api.post(f"{path}/revisions", headers=chief.headers, json={}).status_code == 201
    body = {
        "to_state": "abandoned",
        "confirmed": True,
        "lock_version": api.get(path, headers=chief.headers).json()["lock_version"],
        "current_revision": ABANDONING,
    }
    answer = api.post(f"{path}/exit", headers=chief.headers, json=body)
    assert answer.status_code == 403, answer.text
    assert answer.json()["code"] == "PERMISSION_MISSING"
    assert api.get(path, headers=chief.headers).json()["state"] == PRICING


@pytest.mark.requirement("WF-CYC-0090-A")
def test_an_exit_whose_revision_is_not_found_without_the_counter_moving_stays_a_404(
    api: ContractClient, stage: Scene
) -> None:
    # A current revision that is no revision of the project (the base only demands that it exist)
    # is a 404, not the 412 of an exit that lost the race: the counter of the project is the one
    # read, nothing moved it.
    other = create(api, stage.manager, label="Autre projet")
    foreign = api.post(
        f"{PROJECTS}/{other['project_id']}/revisions", headers=stage.manager.headers, json={}
    ).json()
    put_in_state(
        stage.owner,
        stage.project["project_id"],
        PRICING,
        current_revision_id=UUID(foreign["revision_id"]),
    )
    before = state_in_the_base(stage)
    for fate in (ABANDONING, MARKING):
        answer = leave(api, stage, "abandoned", current_revision=fate)
        assert refusal(answer)[:2] == (404, "NOT_FOUND")
    assert state_in_the_base(stage) == before


@pytest.mark.requirement("WF-ADM-0100-A")
def test_an_exit_abandoning_asks_for_the_permission_even_without_a_current_revision(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # Choice of the route, fixed here: the fate ``abandon`` is judged on the permission to abandon
    # a revision whether the project bears one or not.
    chief = person(
        stage.database,
        realm,
        *(each for each in MANAGING if each != "revision_abandon"),
        name="Zoé",
    )
    project = create(api, chief, label="Sans révision")
    path = f"{PROJECTS}/{project['project_id']}"
    body = {
        "to_state": "abandoned",
        "confirmed": True,
        "lock_version": api.get(path, headers=chief.headers).json()["lock_version"],
        "current_revision": ABANDONING,
    }
    answer = api.post(f"{path}/exit", headers=chief.headers, json=body)
    assert (answer.status_code, answer.json()["code"]) == (403, "PERMISSION_MISSING")
    assert api.get(path, headers=chief.headers).json()["state"] == CREATED
