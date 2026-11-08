# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The marking of a revision by the worker (US-0970, WF-REV-0020), through the service.

``markRevision`` on a project its manager created (``projects_support``), every answer checked
against the contract: the request judges and deposits the task in the queue of the test, and a
worker of the test runs it by the handler of the platform (``waterfall.worker.marking``). A task
the request would refuse is written around it, by ``submit``, to prove that the worker judges
again.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from projects_support import PROJECTS, READING, Scene, person
from projects_support import scene as make_scene
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from support import ContractClient, nowhere, wait_for_a_lock

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.projects.tables import Project
from waterfall.core.revisions.interface import register_indicators
from waterfall.core.revisions.tables import Revision
from waterfall.core.users.interface import anonymize_account
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act, AuditEntry
from waterfall.platform.database import utc_now
from waterfall.platform.errors import UnprocessableError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import load_worker_settings
from waterfall.platform.tasks import BackgroundTask, Task, submit
from waterfall.worker.main import handlers
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

TASKS = "/api/v1/tasks"
EVENTS = "/api/v1/audit-events"
# The correlation of the tasks this file writes around the request.
AROUND = "around-the-request"
# Every entry pending is taken at once.
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
# Why a computation of the indicators refuses, as EP-10 will: a category without its rate.
HOURLY_RATE_MISSING = "HOURLY_RATE_MISSING"
MISSING_RATES = {
    "missing_rates": [{"cost_category_id": "01926f3a-7c00-7000-8000-000000000201", "year": 2026}]
}


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    _, bucket = nowhere()
    app = create_app(Services(database, keycloak, administration, queue, bucket))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the markings, by the platform's handler."""
    queue.prepare()
    return Worker(database, queue, {"revision_mark": mark}, "worker", AT_ONCE)


def revisions_of(stage: Scene) -> str:
    """Give the path of the revisions of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/revisions"


def open_revision(api: ContractClient, stage: Scene, **body: Any) -> dict[str, Any]:
    """Open the current revision of the project of the stage, as its manager does."""
    response = api.post(revisions_of(stage), headers=stage.manager.headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def read(api: ContractClient, stage: Scene, revision_id: str, headers: dict[str, str]) -> Any:
    """Read a revision of the project of the stage, as the session ``headers`` does."""
    response = api.get(f"{revisions_of(stage)}/{revision_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def ask_marking(
    api: ContractClient,
    stage: Scene,
    revision: dict[str, Any],
    headers: dict[str, str] | None = None,
    **body: Any,
) -> Any:
    """Ask for the marking of a revision at the counter read, as the manager does by default."""
    sent = {"version_name": "v1.0", "lock_version": revision["lock_version"], **body}
    return api.post(
        f"{revisions_of(stage)}/{revision['revision_id']}/mark",
        headers=stage.manager.headers if headers is None else headers,
        json=sent,
    )


def marked(
    api: ContractClient, stage: Scene, worker: Worker, revision: dict[str, Any], name: str
) -> dict[str, Any]:
    """Mark a revision under ``name`` through the service and the worker; give it read again."""
    asked = ask_marking(api, stage, revision, version_name=name)
    assert asked.status_code == 202, asked.text
    assert worker.step()
    return read(api, stage, revision["revision_id"], stage.manager.headers)


def task_of(api: ContractClient, stage: Scene, task_id: str) -> Any:
    """Follow a task the manager asked for (``getBackgroundTask``)."""
    response = api.get(f"{TASKS}/{task_id}", headers=stage.manager.headers)
    assert response.status_code == 200, response.text
    return response.json()


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def missing(listed: dict[str, Any]) -> dict[str, list[str]]:
    """Give the conditions each command of an object lacks, by command."""
    return {each["command"]: each["missing_conditions"] for each in listed["available_commands"]}


def current_of(database: Database, stage: Scene) -> UUID | None:
    """Read the current revision the project of the stage names."""
    with database.transaction() as session:
        return session.scalar(
            select(Project.current_revision_id).where(
                Project.id == UUID(stage.project["project_id"])
            )
        )


def markings(database: Database) -> list[AuditEntry]:
    """Read the inscriptions of the markings in the journal."""
    with database.transaction() as session:
        return list(session.scalars(select(AuditEntry).where(AuditEntry.action == "revision_mark")))


def around(
    database: Database,
    queue: TaskQueue,
    stage: Scene,
    revision: dict[str, Any],
    name: str,
    **described: str | None,
) -> UUID:
    """Write a task of marking around the request, which judges nothing: the worker must.

    The payload carries a ``description`` only if ``described`` gives one.
    """
    payload = {
        "project_id": stage.project["project_id"],
        "revision_id": revision["revision_id"],
        "version_name": name,
        **described,
    }
    with logging_context(correlation_id=AROUND), database.transaction() as session:
        return submit(session, queue, "revision_mark", stage.manager.user_id, payload)


@pytest.mark.requirement("WF-PRJ-0060-A")
@pytest.mark.requirement("WF-REV-0090-A")
def test_the_manager_marks_the_current_revision_in_a_task_the_worker_runs(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « … inscrit comme chef de projet, il la marque. » ; « Le nom de version et la description
    # sont ceux saisis au marquage » : 202 with its task, queued, which the worker runs; the
    # revision marked at the counter read, the project left without a current one, the marking
    # inscribed in the journal by its requester under the correlation of the request.
    revision = open_revision(api, stage)
    asked = ask_marking(api, stage, revision, version_name="Offre v1.0", description="Remise")
    assert asked.status_code == 202, asked.text
    queued = asked.json()
    assert (queued["kind"], queued["status"], queued["progress"], queued["problem"]) == (
        "revision_mark",
        "queued",
        0,
        None,
    )
    assert task_of(api, stage, queued["task_id"]) == queued
    assert worker.step()
    ended = task_of(api, stage, queued["task_id"])
    assert (ended["status"], ended["progress"], ended["problem"], ended["result_url"]) == (
        "succeeded",
        100,
        None,
        None,
    )
    after = read(api, stage, revision["revision_id"], stage.manager.headers)
    assert (after["status"], after["version_name"], after["description"]) == (
        "marked",
        "Offre v1.0",
        "Remise",
    )
    assert after["marked_at"] is not None
    assert after["lock_version"] == revision["lock_version"] + 1
    assert after["audit"]["updated_by"]["user_id"] == str(stage.manager.user_id)
    assert current_of(database, stage) is None
    [inscribed] = markings(database)
    with database.transaction() as session:
        correlation = session.scalar(
            select(BackgroundTask.correlation_id).where(
                BackgroundTask.id == UUID(queued["task_id"])
            )
        )
    assert (inscribed.actor_user_id, inscribed.object_id, inscribed.object_label) == (
        stage.manager.user_id,
        UUID(revision["revision_id"]),
        "Offre v1.0",
    )
    assert inscribed.correlation_id == correlation


@pytest.mark.requirement("WF-REV-0090-A")
@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        pytest.param({}, "A", id="absent-is-kept"),
        pytest.param({"description": "B"}, "B", id="present-replaces"),
        pytest.param({"description": None}, None, id="null-clears"),
    ],
)
def test_the_description_of_the_marking_follows_the_rule_of_the_update_of_a_project(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    sent: dict[str, Any],
    expected: str | None,
) -> None:
    # « Le nom de version et la description sont ceux saisis au marquage » (#2171, option A): a
    # description absent from the body keeps the one given at the opening, a given one replaces it,
    # a null one clears it, as ``updateProject`` does for ``client``.
    revision = open_revision(api, stage, description="A")
    assert revision["description"] == "A"
    asked = ask_marking(api, stage, revision, **sent)
    assert asked.status_code == 202, asked.text
    assert worker.step()
    after = read(api, stage, revision["revision_id"], stage.manager.headers)
    assert after["status"] == "marked"
    assert after["description"] == expected


@pytest.mark.requirement("WF-REV-0090-A")
def test_a_task_of_marking_queued_without_a_description_keeps_the_one_of_the_opening(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, queue: TaskQueue
) -> None:
    # ``run_marking`` on a payload without the key ``description`` (a task already in the queue):
    # the description given at the opening is kept; a payload with a null one clears it.
    kept = open_revision(api, stage, description="A")
    task_id = around(database, queue, stage, kept, "v1.0")
    assert worker.step()
    assert task_of(api, stage, str(task_id))["status"] == "succeeded"
    assert read(api, stage, kept["revision_id"], stage.manager.headers)["description"] == "A"
    cleared = open_revision(api, stage, description="C")
    task_id = around(database, queue, stage, cleared, "v2.0", description=None)
    assert worker.step()
    assert task_of(api, stage, str(task_id))["status"] == "succeeded"
    assert read(api, stage, cleared["revision_id"], stage.manager.headers)["description"] is None


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_participant_does_not_mark_even_holding_the_permission(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    # « Inscrit comme participant, il l'ouvre (…) mais ne marque pas de révision même s'il en
    # porte la permission » : 403 ``NOT_PROJECT_MANAGER``, nothing queued.
    revision = open_revision(api, stage)
    refused = ask_marking(api, stage, revision, headers=stage.participant.headers)
    assert refusal(refused) == (
        403,
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )
    with database.transaction() as session:
        assert session.scalars(select(BackgroundTask.id)).all() == []


@pytest.mark.requirement("WF-REV-0020-A")
@pytest.mark.parametrize(
    "name",
    [{"version_name": ""}, {"version_name": " \t  "}, {}],
    ids=["empty", "blank", "absent"],
)
def test_a_marking_without_a_name_of_version_is_refused(
    api: ContractClient, stage: Scene, database: Database, name: dict[str, str]
) -> None:
    # « Le marquage est refusé tant que le nom de version n'est pas renseigné. » : 422,
    # ``VALUE_REQUIRED`` on ``/version_name``; nothing is queued.
    revision = open_revision(api, stage)
    body = {"lock_version": revision["lock_version"], **name}
    refused = api.post(
        f"{revisions_of(stage)}/{revision['revision_id']}/mark",
        headers=stage.manager.headers,
        json=body,
    )
    assert refused.status_code == 422
    assert refused.json()["fields"] == [{"pointer": "/version_name", "code": "VALUE_REQUIRED"}]
    with database.transaction() as session:
        assert session.scalars(select(BackgroundTask.id)).all() == []


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_name_of_version_a_marked_revision_bears_is_refused_by_the_request_and_the_worker(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, queue: TaskQueue
) -> None:
    # « Le marquage d'une révision sous un nom de version déjà employé dans le projet est
    # refusé. » : 409 ``ALREADY_EXISTS`` on ``/version_name``, the revision that bears it named;
    # a task the request did not judge fails with the same refusal, the revision still current.
    offer = marked(api, stage, worker, open_revision(api, stage), "v1.0")
    current = open_revision(api, stage)
    refused = ask_marking(api, stage, current, version_name="v1.0")
    assert refused.status_code == 409
    assert refused.json()["code"] == "ALREADY_EXISTS"
    assert refused.json()["fields"] == [
        {
            "pointer": "/version_name",
            "code": "ALREADY_EXISTS",
            "params": {"conflicting_object_id": offer["revision_id"]},
        }
    ]
    task_id = around(database, queue, stage, current, "v1.0", description=None)
    assert worker.step()
    failed = task_of(api, stage, str(task_id))
    assert failed["status"] == "failed"
    assert failed["problem"]["fields"] == refused.json()["fields"]
    assert read(api, stage, current["revision_id"], stage.manager.headers)["status"] == "draft"
    assert current_of(database, stage) == UUID(current["revision_id"])
    assert len(markings(database)) == 1


@pytest.mark.requirement("WF-REV-0020-A")
def test_a_marked_revision_is_not_marked_again_by_the_request_nor_by_the_worker(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, queue: TaskQueue
) -> None:
    # « Toute tentative de modification d'une révision marquée est refusée, quel que soit le point
    # d'entrée. » : 409 ``revision_draft``, which its command says beforehand; a task the request
    # did not judge fails so, nothing written.
    offer = marked(api, stage, worker, open_revision(api, stage), "v1.0")
    assert missing(offer)["mark"] == ["revision_draft"]
    refused = ask_marking(api, stage, offer, version_name="v2.0")
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )
    task_id = around(database, queue, stage, offer, "v2.0")
    assert worker.step()
    assert task_of(api, stage, str(task_id))["problem"] == {
        "code": "STATE_FORBIDS_OPERATION",
        "status": 409,
        "params": {"missing_condition": "revision_draft"},
        "correlation_id": AROUND,
    }
    assert read(api, stage, offer["revision_id"], stage.manager.headers) == offer


def test_a_marking_at_a_stale_counter_or_of_an_unknown_revision_is_refused(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, queue: TaskQueue
) -> None:
    # The refusals of the contract that reprise no Vérif: a counter that is no longer the
    # revision's (412), a revision the project does not have (404); a task whose revision was
    # abandoned since fails with 404.
    revision = open_revision(api, stage)
    stale = ask_marking(api, stage, revision, lock_version=revision["lock_version"] + 1)
    assert refusal(stale) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": revision["lock_version"]},
    )
    unknown = ask_marking(api, stage, {**revision, "revision_id": stage.project["project_id"]})
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    path = f"{revisions_of(stage)}/{revision['revision_id']}"
    gone = api.delete(
        f"{path}?lock_version={revision['lock_version']}", headers=stage.manager.headers
    )
    assert gone.status_code == 204
    task_id = around(database, queue, stage, revision, "v1.0")
    assert worker.step()
    assert task_of(api, stage, str(task_id))["problem"] == {
        "code": "NOT_FOUND",
        "status": 404,
        "correlation_id": AROUND,
    }


def test_while_the_marking_is_pending_the_writes_of_the_revision_name_the_task(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # A criterion of the story's own, which reprises no Vérif: while the task is queued, each
    # command of the revision lacks ``no_background_task_running``, and the abandonment and a
    # second marking are refused by it; once the task has ended, they no longer lack it.
    revision = open_revision(api, stage)
    assert ask_marking(api, stage, revision).status_code == 202
    during = read(api, stage, revision["revision_id"], stage.manager.headers)
    running = ["no_background_task_running"]
    assert missing(during) == {
        "edit_planning": running,
        "generate_skeleton": running,
        "edit_estimate": running,
        "edit_remaining": running,
        "mark": running,
        "designate_reference": ["revision_marked", "revision_has_tasks_and_lines", *running],
        "abandon": running,
        # An export reads: it lacks no condition during a marking either (WF-CYC-0110).
        "export_planning": [],
        "export_task_tree_image": [],
    }
    again = ask_marking(api, stage, during, version_name="v2.0")
    assert refusal(again) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_background_task_running"},
    )
    path = f"{revisions_of(stage)}/{revision['revision_id']}"
    abandoned = api.delete(
        f"{path}?lock_version={during['lock_version']}", headers=stage.manager.headers
    )
    assert refusal(abandoned)[2] == {"missing_condition": "no_background_task_running"}
    assert worker.step()
    after = read(api, stage, revision["revision_id"], stage.manager.headers)
    assert missing(after)["mark"] == ["revision_draft"]


@pytest.mark.requirement("WF-DAT-0040-A")
@pytest.mark.requirement("WF-IHM-0080-A")
def test_a_marking_whose_computation_fails_writes_nothing_says_why_and_is_asked_again(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # « Le marquage d'une révision échoue entièrement si le calcul de ses indicateurs échoue. » ;
    # « L'échec d'un traitement de fond est signalé avec son motif, et le même traitement peut
    # être relancé. » : a computation that writes, then raises, fails the task with its code and
    # its parameters, the revision current and unwritten; a new ``markRevision`` marks it.
    revision = open_revision(api, stage)

    def missing_rates(session: Session, revision_id: UUID) -> None:
        session.execute(
            update(Revision).where(Revision.id == revision_id).values(description="computed")
        )
        raise UnprocessableError(HOURLY_RATE_MISSING, MISSING_RATES)

    with ExitStack() as registered:
        registered.callback(register_indicators(missing_rates))
        first = ask_marking(api, stage, revision).json()
        assert worker.step()
    failed = task_of(api, stage, first["task_id"])
    assert (failed["status"], failed["problem"]["code"], failed["problem"]["params"]) == (
        "failed",
        "HOURLY_RATE_MISSING",
        MISSING_RATES,
    )
    assert failed["finished_at"] is not None
    still = read(api, stage, revision["revision_id"], stage.manager.headers)
    assert (still["status"], still["description"], still["lock_version"]) == (
        "draft",
        None,
        revision["lock_version"],
    )
    assert missing(still)["mark"] == []
    assert current_of(database, stage) == UUID(revision["revision_id"])
    assert markings(database) == []
    relaunched = ask_marking(api, stage, still)
    assert relaunched.status_code == 202
    assert relaunched.json()["task_id"] != first["task_id"]
    assert worker.step()
    assert task_of(api, stage, relaunched.json()["task_id"])["status"] == "succeeded"
    assert read(api, stage, revision["revision_id"], stage.manager.headers)["status"] == "marked"


@pytest.mark.requirement("WF-ARC-0090-A")
def test_a_worker_stopped_during_the_marking_leaves_the_database_unchanged(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, queue: TaskQueue
) -> None:
    # « Une tâche interrompue est reprise ou échoue sans laisser d'état intermédiaire. » : the
    # marking done, the worker stopped before its end, as ``SIGTERM`` stops it; nothing of it is
    # kept, and the worker started again marks the revision.
    revision = open_revision(api, stage)
    task_id = ask_marking(api, stage, revision).json()["task_id"]

    def stopped(session: Session, task: Task) -> None:
        mark(session, task)
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        Worker(database, queue, {"revision_mark": stopped}, "stopped", AT_ONCE).step()
    assert read(api, stage, revision["revision_id"], stage.manager.headers)["status"] == "draft"
    assert current_of(database, stage) == UUID(revision["revision_id"])
    assert markings(database) == []
    assert task_of(api, stage, task_id)["status"] == "running"
    assert worker.step()
    assert task_of(api, stage, task_id)["status"] == "succeeded"
    assert read(api, stage, revision["revision_id"], stage.manager.headers)["status"] == "marked"
    assert len(markings(database)) == 1


@pytest.mark.requirement("WF-ADM-0060-A")
def test_a_revision_marked_by_an_account_since_deactivated_then_anonymized_names_its_author(
    api: ContractClient, stage: Scene, worker: Worker, owner: Engine, database: Database
) -> None:
    # « Une révision marquée par un compte depuis désactivé affiche toujours son auteur. » ;
    # « (…) les révisions qu'il a marquées affichent le libellé neutre comme auteur » : the author
    # named once deactivated, then without a name once anonymized, which the front shows by the
    # neutral label.
    revision = marked(api, stage, worker, open_revision(api, stage), "v1.0")
    reader = stage.reader.headers
    named = read(api, stage, revision["revision_id"], reader)["audit"]["updated_by"]
    with owner.begin() as connection:
        connection.execute(
            update(UserAccount)
            .where(UserAccount.id == stage.manager.user_id)
            .values(state="deactivated")
        )
    deactivated = read(api, stage, revision["revision_id"], reader)["audit"]["updated_by"]
    assert deactivated == named
    assert deactivated["user_id"] == str(stage.manager.user_id)
    assert deactivated["display_name"]
    with database.transaction() as session:
        version = session.scalar(
            select(UserAccount.lock_version).where(UserAccount.id == stage.manager.user_id)
        )
        assert version is not None
    with logging_context(correlation_id="anonymize"), database.transaction() as session:
        anonymize_account(session, stage.manager.user_id, version, Act(None, utc_now()))
    anonymized = read(api, stage, revision["revision_id"], reader)["audit"]["updated_by"]
    assert (anonymized["kind"], anonymized["user_id"], anonymized["display_name"]) == (
        "user",
        str(stage.manager.user_id),
        None,
    )


def test_the_marking_locks_the_revision_then_the_project_never_the_reverse(
    api: ContractClient, stage: Scene, worker: Worker, database: Database
) -> None:
    # The order of the locks (EP-04, "Modules"; #2179), which reprises no Vérif: while another
    # transaction holds the project, the marking waits for it holding the revision already — taken
    # first, and never after the project, which would let two writers wait for each other.
    revision = open_revision(api, stage)
    assert ask_marking(api, stage, revision).status_code == 202
    project_id = UUID(stage.project["project_id"])
    with ThreadPoolExecutor(1) as others, Session(database.engine) as holding:
        holding.execute(select(Project.id).where(Project.id == project_id).with_for_update())
        marking = others.submit(worker.step)
        wait_for_a_lock(database)
        with database.engine.connect() as probing, pytest.raises(OperationalError, match="lock"):
            probing.execute(
                text("SELECT 1 FROM revision WHERE id = :id FOR UPDATE NOWAIT"),
                {"id": UUID(revision["revision_id"])},
            )
        assert not marking.done()
        holding.commit()
        assert marking.result(timeout=10)
    assert current_of(database, stage) is None


def test_the_abandonment_locks_the_revision_then_the_project_never_the_reverse(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    # The same order for the abandonment, the other writer that locks the revision (#2179).
    revision = open_revision(api, stage)
    project_id = UUID(stage.project["project_id"])
    path = f"{revisions_of(stage)}/{revision['revision_id']}"
    with ThreadPoolExecutor(1) as others, Session(database.engine) as holding:
        holding.execute(select(Project.id).where(Project.id == project_id).with_for_update())
        abandoning = others.submit(
            api.delete,
            f"{path}?lock_version={revision['lock_version']}",
            headers=stage.manager.headers,
        )
        wait_for_a_lock(database)
        with database.engine.connect() as probing, pytest.raises(OperationalError, match="lock"):
            probing.execute(
                text("SELECT 1 FROM revision WHERE id = :id FOR UPDATE NOWAIT"),
                {"id": UUID(revision["revision_id"])},
            )
        holding.commit()
        assert abandoning.result(timeout=10).status_code == 204


@pytest.mark.usefixtures("platform_environment")
def test_the_worker_of_the_platform_runs_the_markings() -> None:
    # The handler registered for the kind ``revision_mark`` is the marking's (``handlers``).
    assert handlers(load_worker_settings())["revision_mark"] is mark


def test_a_marking_is_followed_by_its_requester_alone(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # A detail of EP-03 the marking keeps, which reprises no Vérif here: a task exists for its
    # requester alone (``getBackgroundTask``, 404 for another), who lists it.
    revision = open_revision(api, stage)
    task_id = ask_marking(api, stage, revision).json()["task_id"]
    other = person(stage.database, realm, *READING)
    assert api.get(f"{TASKS}/{task_id}", headers=other.headers).status_code == 404
    listed = api.get(TASKS, headers=stage.manager.headers).json()
    assert [item["task_id"] for item in listed["items"]] == [task_id]
