# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A failed import is followed in the logs, from the deposit of its file to the end of its task.

The identifier the user is given is the correlation of the task that failed (WF-OBS-0020): the
API and the worker write under it, and the records of the deposit, which was a request of its own,
name the deposit the import opened on, so that one search by that identifier finds them all. Every
record of the API and of the worker carries the correlation, the author, the severity and, when
there is one, the project.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from fastapi.testclient import TestClient
from imports_trial import (
    ROWS,
    TrialFormat,
    analysed,
    apply,
    import_worker,
    opened,
    read,
    run,
    stand_in,
)
from projects_support import Scene
from projects_support import scene as make_scene
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import Logs

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

# What a record names of the things a request and a task share: the lines that carry the same
# value of one of these belong to the same story.
LINKS = ("upload_id", "import_id", "task_id")
REQUIRED = ("correlation_id", "actor", "level")


@pytest.fixture
def import_services(
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
    backups_bucket: Bucket,
) -> Services:
    """Give the services of the API on the database, the queue and the bucket of the test."""
    administration = KeycloakAdmin(keycloak, realm_settings)
    return Services(database, keycloak, administration, queue, backups_bucket)


@pytest.fixture
def api(contract: OpenAPI, import_services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(import_services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def trial(monkeypatch: pytest.MonkeyPatch) -> TrialFormat:
    """Make the format of the remaining to commit act as the format of the tests, for the test."""
    return stand_in(monkeypatch, "remaining", TrialFormat())


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


def followed(records: list[dict[str, Any]], correlation_id: str) -> list[dict[str, Any]]:
    """Give the records of a correlation and, by what they name, those of the deposit it follows."""
    mine = [record for record in records if record["correlation_id"] == correlation_id]
    named = {str(record[key]) for record in mine for key in LINKS if key in record}
    return [
        record
        for record in records
        if record in mine or named & {str(record[key]) for key in LINKS if key in record}
    ]


def failed_import(api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat) -> str:
    """Open an import whose analysis breaks, run it; give the identifier its task failed under."""
    trial.analysis = "break"
    import_id = opened(api, stage, *ROWS)["import_id"]
    run(worker)
    found = read(api, stage, import_id)
    assert found["status"] == "failed"
    problem = found["task"]["problem"]
    assert problem["code"] == "INTERNAL_ERROR"
    identifier: str = problem["correlation_id"]
    return identifier


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_failed_import_is_followed_from_its_deposit_to_its_failure_by_one_identifier(
    api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat, logs: Logs
) -> None:
    # « Un import échoué peut être suivi du dépôt du fichier à l'échec de la tâche par un seul
    # identifiant, que le message présenté à l'utilisateur contient. »
    identifier = failed_import(api, stage, worker, trial)
    story = followed(logs.records, identifier)
    events = [(record["event"], record["correlation_id"] == identifier) for record in story]
    assert ("upload.deposited", False) in events
    assert ("import.opened", True) in events
    assert ("task.started", True) in events
    assert ("task.failed", True) in events
    assert events.index(("upload.deposited", False)) < events.index(("import.opened", True))
    assert events.index(("import.opened", True)) < events.index(("task.failed", True))
    # The one deposit of the story is the one the import opened on.
    (deposit,) = [record for record in story if record["event"] == "upload.deposited"]
    (opening,) = [record for record in story if record["event"] == "import.opened"]
    assert deposit["upload_id"] == opening["upload_id"]


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_failed_application_is_followed_from_its_request_to_its_failure(
    api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat, logs: Logs
) -> None:
    found = analysed(api, stage, worker)
    response = apply(api, stage, found["import_id"])
    assert response.status_code == 202
    trial.application = "break"
    run(worker)
    failed = read(api, stage, found["import_id"])
    identifier = failed["task"]["problem"]["correlation_id"]
    story = followed(logs.records, identifier)
    events = {record["event"] for record in story if record["correlation_id"] == identifier}
    assert {"import.apply_requested", "task.started", "task.failed"} <= events
    # The deposit was a request of its own, under another correlation: the import names it.
    assert "upload.deposited" in {record["event"] for record in story}
    assert {record["import_id"] for record in story if "import_id" in record} == {
        found["import_id"]
    }


@pytest.mark.story("US-2900")
@pytest.mark.requirement("WF-OBS-0020-A")
def test_every_record_of_the_api_and_the_worker_carries_its_correlation_its_author_and_its_level(
    api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat, logs: Logs
) -> None:
    failed_import(api, stage, worker, trial)
    records = logs.records
    assert {"request.completed", "task.failed", "task.started"} <= {r["event"] for r in records}
    assert [r for r in records if not all(key in r for key in REQUIRED)] == []
    assert all(r["actor"] for r in records)


@pytest.mark.story("US-2900")
@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_record_names_the_project_it_concerns_and_only_that_one(
    api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat, logs: Logs
) -> None:
    project = stage.project["project_id"]
    failed_import(api, stage, worker, trial)
    records = logs.records
    on_project = [r for r in records if r["event"] == "request.completed" and "project_id" in r]
    assert on_project
    assert {r["project_id"] for r in records if "project_id" in r} == {project}
    # The deposit of a file belongs to no project; the failure of the task, run by the worker, is
    # the project's.
    assert all("project_id" not in r for r in records if r["event"] == "upload.deposited")
    (failure,) = [r for r in records if r["event"] == "task.failed"]
    assert failure["project_id"] == project
    assert failure["actor"] == stage.manager.user_id.__str__()


@pytest.mark.story("US-2900")
def test_what_a_task_binds_to_its_records_does_not_outlive_it(
    api: ContractClient, stage: Scene, worker: Worker, trial: TrialFormat, logs: Logs
) -> None:
    failed_import(api, stage, worker, trial)
    logs.clear()
    worker.step()
    assert all("project_id" not in r and "import_id" not in r for r in logs.records)


BUNDLE = Path(__file__).resolve().parents[2] / "docs" / "api" / "waterfall.bundle.yaml"
# What the contract lets a request name a project by, outside the path /projects/{id}: a filter of
# the query of the journal of audit, which the middleware (PROJECT_PATH) does not read. Reported
# by the test, not decided: a new one must be looked at before it is added here.
PROJECT_OUTSIDE_THE_PATH = {("/audit-events", "get", "project_id", "query")}


@pytest.mark.story("US-2900")
def test_the_contract_designates_a_project_only_by_the_path_the_middleware_reads() -> None:
    contract: dict[str, Any] = yaml.safe_load(BUNDLE.read_text(encoding="utf-8"))

    def resolved(node: Any) -> Any:
        while "$ref" in node:
            target: Any = contract
            reference: str = node["$ref"]
            for key in reference[2:].split("/"):
                target = target[key]
            node = target
        return node

    found: set[tuple[str, str, str, str]] = set()
    paths: dict[str, dict[str, Any]] = contract["paths"]
    for path, item in paths.items():
        if path.startswith("/projects/{"):
            continue
        shared: list[Any] = item.get("parameters", [])
        for method, operation_node in item.items():
            operation: Any = operation_node
            if method == "parameters" or not isinstance(operation_node, dict):
                continue
            parameters: list[Any] = [*shared, *operation.get("parameters", [])]
            for parameter in parameters:
                named = resolved(parameter)
                if "project" in named["name"].lower():
                    found.add((path, method, named["name"], named["in"]))
    assert found == PROJECT_OUTSIDE_THE_PATH
