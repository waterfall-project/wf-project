# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The exports: the task, the storage, the download of the result (US-1430/L2).

``requestExport`` deposits the task ``export``, the worker has the exporter of the kind write the
file under ``exports/<task_id>.<ext>``, and ``getBackgroundTaskResult`` streams it once, deleting it
at its last byte. The exporter of a test stands for the real ones (the MS Project schedule is
US-1430/L4); every answer is checked against the contract. The purge of the exports nobody
downloaded is US-1420/L2's.
"""

import asyncio
import contextlib
from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from projects_support import PROJECTS, Scene, contribute, create, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect
from support import ContractClient
from task_handlers import deposit

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.exports import disposition
from waterfall.core.exchanges.interface import ExportedFile, ExportOrder, exporters
from waterfall.core.planning.interface import MS_PROJECT_EXPORTER
from waterfall.core.revisions.commands import RevisionState, revision_commands
from waterfall.core.revisions.interface import mark_revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import NotFoundError
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import BackgroundTask, project_task_pending
from waterfall.worker.exchanges import ExportTask
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from starlette.types import ASGIApp, Message, Scope

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

TASKS = "/api/v1/tasks"
AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)
PLANNING = "ms_project_schedule"
PNG = "image/png"
CONTENT = b"\x89PNG\r\n\x1a\n" + b"x" * 100


class Trial:
    """The exporter of a test: it gives a file chosen, keeps the orders it received, may refuse.

    It overrides the stub of the planning under the kind ``ms_project_schedule``, the one exporter
    registered while the others (EP-07, EP-09, US-1440) are not.
    """

    def __init__(self) -> None:
        self.file = ExportedFile(CONTENT, PNG, "arbre.png")
        self.orders: list[ExportOrder] = []
        self.refusal: Exception | None = None

    def export(self, _session: object, order: ExportOrder) -> ExportedFile:
        """Give the file chosen, or refuse as chosen."""
        self.orders.append(order)
        if self.refusal is not None:
            raise self.refusal
        return self.file


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> Trial:
    """Stand for the exporter of the MS Project schedule, registered by the planning, by a trial."""
    exporter = Trial()
    monkeypatch.setattr(MS_PROJECT_EXPORTER, "export", exporter.export)
    return exporter


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give what the application reaches: the queue of the test, and a bucket to keep files in."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Give a client of the application that deposits its tasks and keeps its files for the test."""
    app = create_app(services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test that runs the exports, into the bucket of the test."""
    queue.prepare()
    return Worker(database, queue, {"export": ExportTask(backups_bucket)}, "worker", AT_ONCE)


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def opened(api: ContractClient, stage: Scene) -> tuple[str, str]:
    """Open the current revision of the project of the stage; give it and its main structure."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions"
    response = api.post(path, headers=stage.manager.headers, json={})
    assert response.status_code == 201, response.text
    revision_id = response.json()["revision_id"]
    listed = api.get(f"{path}/{revision_id}/structures", headers=stage.manager.headers).json()
    return revision_id, next(each["structure_id"] for each in listed if each["kind"] == "main")


def ask(api: ContractClient, stage: Scene, revision_id: str, **body: Any) -> Any:
    """Request an export of the project of the stage as its manager does; give the answer."""
    path = f"{PROJECTS}/{stage.project['project_id']}/exports"
    sent = {"kind": PLANNING, "revision_id": revision_id, **body}
    return api.post(path, headers=stage.manager.headers, json=sent)


def requested(api: ContractClient, stage: Scene, revision_id: str, **body: Any) -> str:
    """Request an export that must be accepted (202); give the identifier of its task."""
    answer = ask(api, stage, revision_id, **body)
    assert answer.status_code == 202, answer.text
    return answer.json()["task_id"]


def task_of(api: ContractClient, stage: Scene, task_id: str) -> dict[str, Any]:
    """Follow a task the manager asked for."""
    answer = api.get(f"{TASKS}/{task_id}", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def exported(api: ContractClient, stage: Scene, worker: Worker) -> tuple[str, dict[str, Any]]:
    """Request the export of a new revision and have the worker run it; give the task."""
    revision_id, _ = opened(api, stage)
    task_id = requested(api, stage, revision_id)
    assert worker.step()
    return task_id, task_of(api, stage, task_id)


def result(api: ContractClient, stage: Scene, task_id: str) -> Any:
    """Download the result of a task as the manager does."""
    return api.get(f"{TASKS}/{task_id}/result", headers=stage.manager.headers)


def stored(bucket: Bucket, key: str) -> int | None:
    """Give the size of the object of a key in the bucket of the test, if it is there."""
    return bucket.size(key)


async def pulled_then_dropped(app: ASGIApp, path: str, headers: dict[str, str]) -> int:
    """Read the first piece of an answer, then drop the connection; give the pieces received.

    The client stops reading as one whose network breaks does: the server fails to send the next
    piece, and its stream is closed where it stands.
    """
    received: list[bytes] = []
    scope: Scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(name.lower().encode(), value.encode()) for name, value in headers.items()],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        if message["type"] == "http.response.body" and message.get("body"):
            received.append(message["body"])
            raise ConnectionResetError

    with contextlib.suppress(ClientDisconnect):
        await app(scope, receive, send)
    return len(received)


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("trial")
def test_an_export_downloaded_to_the_end_is_no_longer_on_the_storage(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    task_id, done = exported(api, stage, worker)
    key = f"exports/{task_id}.png"
    assert done["status"] == "succeeded"
    assert done["result_url"] == f"{TASKS}/{task_id}/result"
    assert stored(backups_bucket, key) == len(CONTENT)
    answer = result(api, stage, task_id)
    assert answer.status_code == 200
    assert answer.content == CONTENT
    assert answer.headers["content-type"] == PNG
    assert answer.headers["content-disposition"] == 'attachment; filename="arbre.png"'
    assert answer.headers["content-length"] == str(len(CONTENT))
    assert stored(backups_bucket, key) is None
    assert task_of(api, stage, task_id)["result_url"] is None
    gone = result(api, stage, task_id)
    assert refusal(gone)[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("trial")
def test_an_interrupted_download_leaves_the_export_available_to_be_downloaded_again(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    task_id, _ = exported(api, stage, worker)
    key = f"exports/{task_id}.png"
    pieces = asyncio.run(
        pulled_then_dropped(api.client.app, f"{TASKS}/{task_id}/result", stage.manager.headers)
    )
    assert pieces == 1
    assert stored(backups_bucket, key) == len(CONTENT)
    assert task_of(api, stage, task_id)["result_url"] == f"{TASKS}/{task_id}/result"
    again = result(api, stage, task_id)
    assert (again.status_code, again.content) == (200, CONTENT)
    assert stored(backups_bucket, key) is None


@pytest.mark.requirement("WF-DAT-0120-A")
@pytest.mark.usefixtures("trial")
def test_an_export_whose_object_is_gone_is_a_result_that_does_not_exist(
    api: ContractClient, stage: Scene, worker: Worker, backups_bucket: Bucket
) -> None:
    task_id, _ = exported(api, stage, worker)
    backups_bucket.remove(f"exports/{task_id}.png")
    assert refusal(result(api, stage, task_id))[:2] == (404, "NOT_FOUND")
    assert task_of(api, stage, task_id)["result_url"] is None


@pytest.mark.requirement("WF-CYC-0110-A")
@pytest.mark.usefixtures("trial")
def test_the_export_of_a_marked_revision_succeeds_and_is_downloaded(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # « Ses exports aboutissent », a revision marked as one in progress.
    revision_id, _ = opened(api, stage)
    with (
        logging_context(correlation_id="marking"),
        Session(stage.owner) as session,
        session.begin(),
    ):
        mark_revision(session, UUID(revision_id), "v1.0", None, Act(None, utc_now()))
    task_id = requested(api, stage, revision_id)
    assert worker.step()
    assert task_of(api, stage, task_id)["status"] == "succeeded"
    answer = result(api, stage, task_id)
    assert (answer.status_code, answer.content) == (200, CONTENT)


@pytest.mark.requirement("WF-ARC-0090-A")
def test_the_result_of_a_task_that_has_not_succeeded_is_refused_by_the_condition_it_lacks(
    api: ContractClient, stage: Scene, worker: Worker, trial: Trial
) -> None:
    revision_id, _ = opened(api, stage)
    queued = requested(api, stage, revision_id)
    assert refusal(result(api, stage, queued)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "task_succeeded"},
    )
    trial.refusal = NotFoundError("NOT_FOUND")
    assert worker.step()
    failed = task_of(api, stage, queued)
    assert (failed["status"], failed["problem"]["code"], failed["result_url"]) == (
        "failed",
        "NOT_FOUND",
        None,
    )
    assert refusal(result(api, stage, queued)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "task_succeeded"},
    )


@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.usefixtures("trial")
def test_the_result_is_read_by_the_account_that_asked_for_it_and_for_an_export_alone(
    api: ContractClient, stage: Scene, worker: Worker, database: Database, queue: TaskQueue
) -> None:
    task_id, _ = exported(api, stage, worker)
    other = api.get(f"{TASKS}/{task_id}/result", headers=stage.participant.headers)
    assert refusal(other)[:2] == (404, "NOT_FOUND")
    unknown = api.get(f"{TASKS}/{UUID(int=1)}/result", headers=stage.manager.headers)
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    # A task that produces no file, as the reading of the accounts does, has no result to download.
    synchronised = deposit(database, queue, "identity_sync", stage.manager.user_id)
    assert refusal(result(api, stage, str(synchronised)))[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_task_keeps_where_the_file_lies_and_the_exporter_receives_what_was_asked(
    api: ContractClient, stage: Scene, worker: Worker, trial: Trial, database: Database
) -> None:
    revision_id, structure_id = opened(api, stage)
    trial.file = ExportedFile(CONTENT, PNG, "Planning été.png")
    task_id = requested(api, stage, revision_id, depth=2, review_date="2026-11-09")
    assert worker.step()
    with database.transaction() as session:
        row = session.get_one(BackgroundTask, UUID(task_id))
        kept = row.result
    assert kept == {
        "object_key": f"exports/{task_id}.png",
        "filename": "Planning été.png",
        "media_type": PNG,
    }
    assert trial.orders == [
        ExportOrder(
            project_id=UUID(stage.project["project_id"]),
            revision_id=UUID(revision_id),
            structure_id=UUID(structure_id),
            requested_by=stage.manager.user_id,
            depth=2,
            review_date=date(2026, 11, 9),
        )
    ]
    answer = result(api, stage, task_id)
    assert answer.headers["content-disposition"] == (
        "attachment; filename=\"Planning ete.png\"; filename*=UTF-8''Planning%20%C3%A9t%C3%A9.png"
    )


@pytest.mark.requirement("WF-DAT-0120-A")
def test_the_name_of_a_file_is_given_in_ascii_and_in_utf8_without_breaking_the_header() -> None:
    assert disposition("planning.xml") == 'attachment; filename="planning.xml"'
    assert disposition('a"b\\c.xml') == 'attachment; filename="a\'b_c.xml"'
    assert (
        disposition("été.png")
        == "attachment; filename=\"ete.png\"; filename*=UTF-8''%C3%A9t%C3%A9.png"
    )
    assert (
        disposition("日本.png")
        == "attachment; filename=\"export.png\"; filename*=UTF-8''%E6%97%A5%E6%9C%AC.png"
    )
    assert (
        disposition("日本")
        == "attachment; filename=\"export\"; filename*=UTF-8''%E6%97%A5%E6%9C%AC"
    )
    assert disposition(".png") == 'attachment; filename="export.png"'
    assert disposition('日本.a"b') == (
        "attachment; filename=\"export.a'b\"; filename*=UTF-8''%E6%97%A5%E6%9C%AC.a%22b"
    )
    injected = disposition("日本.a\nb\r\n")
    assert "\n" not in injected
    assert "\r" not in injected
    assert injected.startswith('attachment; filename="export.a_b__"')


@pytest.mark.requirement("WF-INTF-0050-A")
def test_an_export_is_accepted_for_the_revision_named_and_its_main_structure_by_default(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    revision_id, structure_id = opened(api, stage)
    answer = ask(api, stage, revision_id)
    assert answer.status_code == 202, answer.text
    body = answer.json()
    assert (body["kind"], body["status"], body["progress"], body["result_url"]) == (
        "export",
        "queued",
        0,
        None,
    )
    with database.transaction() as session:
        row = session.get_one(BackgroundTask, UUID(body["task_id"]))
        assert row.requested_by == stage.manager.user_id
        assert row.payload == {
            "project": stage.project["project_id"],
            "kind": PLANNING,
            "revision_id": revision_id,
            "structure_id": structure_id,
            "depth": None,
            "review_date": None,
        }
        # An export writes nothing: it makes no write of the project wait for it.
        assert not project_task_pending(session, UUID(stage.project["project_id"]))


@pytest.mark.requirement("WF-INTF-0050-A")
def test_an_export_refuses_an_unknown_revision_or_structure_and_a_body_without_revision(
    api: ContractClient, stage: Scene
) -> None:
    revision_id, _ = opened(api, stage)
    elsewhere = create(api, stage.outsider, label="Autre projet")["project_id"]
    path = f"{PROJECTS}/{elsewhere}/revisions"
    other = api.post(path, headers=stage.outsider.headers, json={}).json()["revision_id"]
    assert refusal(ask(api, stage, other))[:2] == (404, "NOT_FOUND")
    assert refusal(ask(api, stage, str(UUID(int=7))))[:2] == (404, "NOT_FOUND")
    assert refusal(ask(api, stage, revision_id, structure_id=str(UUID(int=7))))[:2] == (
        404,
        "NOT_FOUND",
    )
    missing = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/exports",
        headers=stage.manager.headers,
        json={"kind": PLANNING},
    )
    assert missing.status_code == 422
    assert missing.json()["fields"][0]["pointer"] == "/revision_id"
    hidden = api.post(
        f"{PROJECTS}/{UUID(int=9)}/exports",
        headers=stage.manager.headers,
        json={"kind": PLANNING, "revision_id": revision_id},
    )
    assert refusal(hidden)[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-PLA-0120-A")
def test_a_depth_below_the_first_level_is_refused_naming_the_bound(
    api: ContractClient, stage: Scene, database: Database
) -> None:
    revision_id, _ = opened(api, stage)
    answer = ask(api, stage, revision_id, kind="task_tree_image", depth=0)
    assert answer.status_code == 422
    assert answer.json()["fields"] == [
        {"pointer": "/depth", "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": 1}}
    ]
    with database.transaction() as session:
        assert session.scalars(select(BackgroundTask.id)).all() == []


@pytest.mark.requirement("WF-CYC-0110-A")
def test_the_command_of_the_kind_is_present_without_condition_or_absent_and_refuses_naming_it(
    api: ContractClient, stage: Scene, owner: Engine
) -> None:
    revision_id, _ = opened(api, stage)
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision_id}"

    def commands() -> dict[str, list[str]]:
        listed = api.get(path, headers=stage.manager.headers).json()["available_commands"]
        return {each["command"]: each["missing_conditions"] for each in listed}

    assert commands()["export_planning"] == []
    # The estimate and the remaining to commit are EP-07's and EP-09's: their commands are absent.
    for kind, permission in (("estimate", "estimate.read"), ("remaining", "remaining.read")):
        assert refusal(ask(api, stage, revision_id, kind=kind)) == (
            403,
            "PERMISSION_MISSING",
            {"missing_permission": permission},
        )
    # The exports remain on a project that ended, where no other command does.
    put_in_state(owner, stage.project["project_id"], "completed")
    assert commands() == {"export_planning": []}
    assert ask(api, stage, revision_id).status_code == 202


@pytest.mark.requirement("WF-CYC-0110-A")
def test_the_permission_of_the_kind_is_judged_by_its_command_not_by_the_route(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    # A contributor who holds ``estimate.read`` alone is not refused for ``planning.read``, which
    # the route no longer asks for: the command ``export_estimate`` is absent (EP-07's), and the
    # refusal names the permission of its kind.
    estimating = person(database, realm, "estimate.read", name="Léa")
    contribute(database, stage.project["project_id"], estimating, "contributor")
    revision_id, _ = opened(api, stage)
    path = f"{PROJECTS}/{stage.project['project_id']}/exports"
    answer = api.post(
        path, headers=estimating.headers, json={"kind": "estimate", "revision_id": revision_id}
    )
    assert refusal(answer) == (403, "PERMISSION_MISSING", {"missing_permission": "estimate.read"})


@pytest.mark.requirement("WF-CYC-0110-A")
def test_the_exports_are_listed_to_whoever_may_consult_the_planning_and_to_no_other() -> None:
    revision = RevisionState(
        marked=True, no_task_running=False, has_tasks_and_lines=False, reference_correctable=False
    )
    reading = revision_commands(("planning.read",), None, "in_progress", revision)
    assert reading == [("export_planning", ())]
    assert revision_commands((), None, "in_progress", revision) == []
    assert revision_commands(("planning.read",), None, "lost", revision) == [
        ("export_planning", ())
    ]


@pytest.mark.requirement("WF-INTF-0050-A")
def test_the_planning_registers_the_exporter_the_task_runs_for_its_kind() -> None:
    assert PLANNING in exporters()
    assert exporters()[PLANNING] is MS_PROJECT_EXPORTER
