# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The designation of the reference revision, by the service (US-0980/L2; WF-REV-0040, WF-CYC-0030).

``designateReferenceRevision`` on a project its manager created (``projects_support``), every
answer checked against the contract. A revision is marked by the transaction of the worker
(``mark_revision``); that it bears tasks and lines, which EP-06 and EP-07 answer, is put by a
fixture (``register_tasks_and_lines``).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from projects_support import MANAGING, PROJECTS, Scene, create, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.projects.tables import Project, ProjectStateTransition
from waterfall.core.revisions.interface import mark_revision, register_tasks_and_lines
from waterfall.core.revisions.tables import Revision
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import PROJECT, submit

if TYPE_CHECKING:
    from collections.abc import Iterator

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.queue import TaskQueue

EARLY = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
STATE_FORBIDS = "STATE_FORBIDS_OPERATION"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def lines() -> Iterator[None]:
    """Make every revision bear tasks and lines, as EP-06 and EP-07 will answer."""
    withdraw = register_tasks_and_lines(lambda _session, _revision: True)
    yield
    withdraw()


def project_path(stage: Scene) -> str:
    """Give the path of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def project_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the project of the stage, as its manager does."""
    response = api.get(project_path(stage), headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def open_revision(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    response = api.post(f"{project_path(stage)}/revisions", headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    return response.json()


def mark(stage: Scene, revision: dict[str, Any], name: str, at: datetime = EARLY) -> None:
    """Mark a revision by the transaction of the worker, at ``at``."""
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        mark_revision(session, UUID(revision["revision_id"]), name, None, Act(None, at))


def marked(api: ContractClient, stage: Scene, name: str, at: datetime = EARLY) -> dict[str, Any]:
    """Open the current revision, mark it under ``name`` at ``at``, and give it as it is read."""
    opened = open_revision(api, stage)
    mark(stage, opened, name, at)
    return read(api, stage, opened["revision_id"])


def read(api: ContractClient, stage: Scene, revision_id: str) -> dict[str, Any]:
    """Read a revision of the project of the stage, as its manager does."""
    path = f"{project_path(stage)}/revisions/{revision_id}"
    response = api.get(path, headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def missing(listed: dict[str, Any]) -> dict[str, list[str]]:
    """Give the conditions each command of an object lacks, by command."""
    return {each["command"]: each["missing_conditions"] for each in listed["available_commands"]}


def designate(
    api: ContractClient, stage: Scene, revision_id: str, *, headers: Any = None, **body: Any
) -> Any:
    """Designate a revision as its manager does, confirmed, at the counter the project has."""
    sent = {
        "revision_id": revision_id,
        "confirmed": True,
        "lock_version": project_of(api, stage)["lock_version"],
        **body,
    }
    return api.put(
        f"{project_path(stage)}/reference-revision",
        headers=stage.manager.headers if headers is None else headers,
        json=sent,
    )


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def references(stage: Scene) -> list[str | None]:
    """Give the names of the revisions of the project of the stage that are its reference."""
    with stage.database.transaction() as session:
        return list(
            session.scalars(
                select(Revision.version_name).where(
                    Revision.project_id == UUID(stage.project["project_id"]),
                    Revision.is_reference.is_(True),
                )
            )
        )


def project_row(stage: Scene) -> tuple[UUID | None, str, int]:
    """Read the reference, the state and the counter of the project, as the base keeps them."""
    with stage.database.transaction() as session:
        project = session.get_one(Project, UUID(stage.project["project_id"]))
        return project.reference_revision_id, project.state, project.lock_version


def journal(stage: Scene) -> list[AuditEntry]:
    """Read the designations of the journal."""
    with stage.database.transaction() as session:
        return list(
            session.scalars(select(AuditEntry).where(AuditEntry.action == "reference_designate"))
        )


def entered(api: ContractClient, stage: Scene, code: str) -> Any:
    """Enter the code of the project of the stage, as its manager does."""
    current = project_of(api, stage)["lock_version"]
    return api.patch(
        project_path(stage),
        headers=stage.manager.headers,
        json={"code": code, "lock_version": current},
    )


@pytest.mark.requirement("WF-CYC-0030-A")
def test_a_designation_without_tasks_and_lines_is_refused_naming_the_condition(
    api: ContractClient, stage: Scene
) -> None:
    # « La désignation d'une révision marquée sans tâche, ou sans ligne de devis, est refusée et la
    # condition manquante est nommée ; le projet n'a pas de référence. » None registers its tasks.
    revision = marked(api, stage, "v1.0")
    before = project_row(stage)
    answer = designate(api, stage, revision["revision_id"])
    assert refusal(answer) == (
        409,
        STATE_FORBIDS,
        {"missing_condition": "revision_has_tasks_and_lines"},
    )
    assert project_row(stage) == before
    assert before[0] is None
    assert references(stage) == []
    assert journal(stage) == []
    assert project_of(api, stage)["reference_revision_id"] is None


@pytest.mark.requirement("WF-CYC-0030-A")
@pytest.mark.usefixtures("lines")
def test_the_first_condition_the_command_lacks_is_told(
    api: ContractClient, stage: Scene, queue: TaskQueue
) -> None:
    # In the order of the command: a current revision lacks ``revision_marked``, a project
    # terminal ``project_not_terminal`` before anything, a task of the background its own.
    current = open_revision(api, stage)
    answer = designate(api, stage, current["revision_id"])
    assert refusal(answer)[2] == {"missing_condition": "revision_marked"}
    mark(stage, current, "v1.0")
    queue.prepare()
    with logging_context(correlation_id="around"), stage.database.transaction() as session:
        submit(session, queue, "revision_mark", None, {PROJECT: stage.project["project_id"]})
    busy = designate(api, stage, current["revision_id"])
    assert refusal(busy)[2] == {"missing_condition": "no_background_task_running"}
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    terminal = designate(api, stage, current["revision_id"])
    assert refusal(terminal) == (409, STATE_FORBIDS, {"missing_condition": "project_not_terminal"})
    assert references(stage) == []


@pytest.mark.requirement("WF-REV-0040-A")
@pytest.mark.requirement("WF-DAT-0020-A")
@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.usefixtures("lines")
def test_a_marked_revision_is_designated_the_reference_and_the_designation_is_inscribed(
    api: ContractClient, stage: Scene
) -> None:
    # « La désignation d'une révision marquée comme référence aboutit. » : the base admits that
    # alone to write a marked revision; the project names it, its counter moves, the journal
    # inscribes it under the revision, its author the manager.
    revision = marked(api, stage, "v1.0")
    assert missing(revision)["designate_reference"] == []
    before = project_row(stage)
    answer = designate(api, stage, revision["revision_id"])
    assert answer.status_code == 200, answer.text
    body = answer.json()
    assert body["reference_revision_id"] == revision["revision_id"]
    assert body["lock_version"] == before[2] + 1
    assert project_row(stage) == (UUID(revision["revision_id"]), "pricing", before[2] + 1)
    assert references(stage) == ["v1.0"]
    after = read(api, stage, revision["revision_id"])
    assert (after["is_reference"], after["status"], after["version_name"]) == (
        True,
        "marked",
        "v1.0",
    )
    [entry] = journal(stage)
    assert (entry.object_kind, entry.object_id, entry.object_label) == (
        "revision",
        UUID(revision["revision_id"]),
        "v1.0",
    )
    assert entry.actor_user_id == stage.manager.user_id


@pytest.mark.requirement("WF-CYC-0030-A")
@pytest.mark.requirement("WF-CYC-0020-A")
@pytest.mark.usefixtures("lines")
def test_the_designation_then_the_code_move_the_project_to_in_progress_at_the_code(
    api: ContractClient, stage: Scene
) -> None:
    # « Un projet dont la référence est désignée avant le code projet passe à En cours à la saisie
    # du code. » The transaction that realises the second fact writes the transition.
    revision = marked(api, stage, "v1.0")
    designated = designate(api, stage, revision["revision_id"])
    assert (designated.status_code, designated.json()["state"]) == (200, "pricing")
    coded = entered(api, stage, "PRJ-090")
    assert (coded.status_code, coded.json()["state"]) == (200, "in_progress"), coded.text
    last = transitions(api, stage)[-1]
    assert (last["from_state"], last["to_state"]) == ("pricing", "in_progress")
    assert last["occurred_at"] == coded.json()["audit"]["updated_at"]
    assert last["actor"]["user_id"] == str(stage.manager.user_id)


@pytest.mark.requirement("WF-CYC-0030-A")
@pytest.mark.requirement("WF-CYC-0020-A")
@pytest.mark.usefixtures("lines")
def test_the_code_then_the_designation_move_the_project_to_in_progress_at_the_designation(
    api: ContractClient, stage: Scene
) -> None:
    # « Un projet dont le code est saisi avant la désignation y passe à la désignation. »
    revision = marked(api, stage, "v1.0")
    assert entered(api, stage, "PRJ-091").json()["state"] == "pricing"
    designated = designate(api, stage, revision["revision_id"])
    assert designated.status_code == 200, designated.text
    assert designated.json()["state"] == "in_progress"
    last = transitions(api, stage)[-1]
    assert (last["from_state"], last["to_state"]) == ("pricing", "in_progress")
    assert last["occurred_at"] == designated.json()["audit"]["updated_at"]
    assert last["actor"]["user_id"] == str(stage.manager.user_id)
    assert [item["to_state"] for item in transitions(api, stage)].count("in_progress") == 1


def transitions(api: ContractClient, stage: Scene) -> list[dict[str, Any]]:
    """Read the transitions of the project of the stage, as its manager does."""
    response = api.get(f"{project_path(stage)}/state-transitions", headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.requirement("WF-REV-0040-A")
@pytest.mark.usefixtures("lines")
def test_a_revision_marked_since_the_designation_closes_the_correction(
    api: ContractClient, stage: Scene
) -> None:
    # « La désignation manuelle est proposée tant que le projet n'a ni coût réel ni révision
    # marquée depuis la dernière désignation, et refusée au-delà. » (J-01, #1797): the refusal is
    # ``STATE_FORBIDS_OPERATION``, ``reference_correctable``, and the list says it before.
    first = marked(api, stage, "v1.0")
    assert designate(api, stage, first["revision_id"]).status_code == 200
    second = marked(api, stage, "v2.0", utc_now() + timedelta(hours=1))
    assert missing(second)["designate_reference"] == ["reference_correctable"]
    answer = designate(api, stage, second["revision_id"])
    assert refusal(answer) == (409, STATE_FORBIDS, {"missing_condition": "reference_correctable"})
    assert references(stage) == ["v1.0"]


@pytest.mark.requirement("WF-REV-0040-A")
@pytest.mark.usefixtures("lines")
def test_a_reference_designated_by_mistake_is_corrected_and_stays_alone(
    api: ContractClient, stage: Scene
) -> None:
    # « Un projet dont les offres v2 puis v3 sont marquées, et dont v2 a été désignée par erreur,
    # accepte la désignation de v3 » (no actual cost): nothing was marked since the designation.
    first = marked(api, stage, "v2.0")
    second = marked(api, stage, "v3.0", EARLY + timedelta(days=1))
    assert designate(api, stage, first["revision_id"]).status_code == 200
    assert missing(read(api, stage, second["revision_id"]))["designate_reference"] == []
    corrected = designate(api, stage, second["revision_id"])
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["reference_revision_id"] == second["revision_id"]
    assert references(stage) == ["v3.0"]
    assert read(api, stage, first["revision_id"])["is_reference"] is False
    assert len(journal(stage)) == 2


@pytest.mark.requirement("WF-REV-0040-A")
@pytest.mark.usefixtures("lines")
def test_the_designation_is_refused_unconfirmed_unknown_or_at_a_stale_counter(
    api: ContractClient, stage: Scene
) -> None:
    revision = marked(api, stage, "v1.0")
    before = project_row(stage)
    unconfirmed = designate(api, stage, revision["revision_id"], confirmed=False)
    assert refusal(unconfirmed) == (400, "CONFIRMATION_REQUIRED", {})
    path = f"{project_path(stage)}/reference-revision"
    absent = api.put(
        path,
        headers=stage.manager.headers,
        json={"revision_id": revision["revision_id"], "lock_version": before[2]},
    )
    assert refusal(absent)[:2] == (400, "CONFIRMATION_REQUIRED")
    unknown = designate(api, stage, str(uuid4()))
    assert unknown.status_code == 404
    stale = designate(api, stage, revision["revision_id"], lock_version=before[2] + 1)
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": before[2]})
    assert project_row(stage) == before
    assert references(stage) == []


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.requirement("WF-PRJ-0060-A")
@pytest.mark.usefixtures("lines")
def test_the_designation_is_reserved_to_the_managers_holding_its_permission(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    revision = marked(api, stage, "v1.0")
    participant = designate(api, stage, revision["revision_id"], headers=stage.participant.headers)
    assert refusal(participant)[:2] == (403, "NOT_PROJECT_MANAGER")
    outsider = designate(api, stage, revision["revision_id"], headers=stage.outsider.headers)
    assert outsider.status_code == 404
    chief = person(
        stage.database,
        realm,
        *(each for each in MANAGING if each != "reference_designate"),
        name="Zoé",
    )
    own = create(api, chief, label="Sans désignation")
    path = f"{PROJECTS}/{own['project_id']}/reference-revision"
    sent = {"revision_id": str(uuid4()), "confirmed": True, "lock_version": 0}
    lacking = api.put(path, headers=chief.headers, json=sent)
    assert refusal(lacking)[:2] == (403, "PERMISSION_MISSING")
    assert references(stage) == []


@pytest.mark.requirement("WF-ARC-0070-A")
@pytest.mark.requirement("WF-CYC-0100-A")
@pytest.mark.usefixtures("lines")
@pytest.mark.parametrize("state", ["completed", "lost", "abandoned"])
def test_a_terminal_project_refuses_the_designation_before_any_other_condition(
    api: ContractClient, stage: Scene, state: str
) -> None:
    revision = marked(api, stage, "v1.0")
    put_in_state(stage.owner, stage.project["project_id"], state)
    answer = designate(api, stage, revision["revision_id"])
    assert refusal(answer) == (409, STATE_FORBIDS, {"missing_condition": "project_not_terminal"})
    assert references(stage) == []


@pytest.mark.requirement("WF-REV-0040-A")
@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.usefixtures("lines")
def test_two_designations_at_once_designate_once(api: ContractClient, stage: Scene) -> None:
    # « deux désignations concurrentes ne passent pas l'une sur l'autre, même quand aucune
    # révision n'a été marquée entre elles »: both read the counter, the second finds it moved.
    first = marked(api, stage, "v1.0")
    second = marked(api, stage, "v2.0", EARLY + timedelta(days=1))
    counter = project_of(api, stage)["lock_version"]
    path = f"{project_path(stage)}/reference-revision"
    bodies = [
        {"revision_id": each["revision_id"], "confirmed": True, "lock_version": counter}
        for each in (first, second)
    ]
    with ThreadPoolExecutor(2) as others, Session(stage.database.engine) as holding:
        holding.execute(
            select(Project.id)
            .where(Project.id == UUID(stage.project["project_id"]))
            .with_for_update()
        )
        asked = [
            others.submit(api.put, path, headers=stage.manager.headers, json=body)
            for body in bodies
        ]
        wait_for_a_lock(stage.database)
        holding.commit()
        answers = sorted(each.result(timeout=10).status_code for each in asked)
    assert answers == [200, 412]
    assert len(references(stage)) == 1
    assert len(journal(stage)) == 1
    assert project_row(stage)[2] == counter + 1


@pytest.mark.requirement("WF-CYC-0020-A")
@pytest.mark.usefixtures("lines")
def test_the_designation_of_a_project_already_in_progress_writes_no_transition(
    api: ContractClient, stage: Scene
) -> None:
    # A fact realised once moves the project once: the correction of the reference leaves it.
    first = marked(api, stage, "v1.0")
    second = marked(api, stage, "v2.0", EARLY + timedelta(days=1))
    assert entered(api, stage, "PRJ-092").status_code == 200
    assert designate(api, stage, first["revision_id"]).json()["state"] == "in_progress"
    again = designate(api, stage, second["revision_id"])
    assert (again.status_code, again.json()["state"]) == (200, "in_progress")
    with stage.database.transaction() as session:
        reached = session.scalars(
            select(ProjectStateTransition.to_state).where(
                ProjectStateTransition.project_id == UUID(stage.project["project_id"])
            )
        ).all()
    assert list(reached).count("in_progress") == 1
