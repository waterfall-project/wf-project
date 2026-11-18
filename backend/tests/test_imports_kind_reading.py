# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The imports of a project read by the kinds their caller consults (US-2660/L1, #2473).

The routes of the imports ask for the visibility of the project alone; the kind of an import is
judged by the exchanges with the import (``Format.reading``): ``listImports`` lists and counts the
kinds its caller consults, ``getImport`` and the commands of an import refuse one of another kind as
an unknown import (404), and an estimator who does not read the planning opens, reads and applies
the import of its estimate — which the reading of the planning, asked of every import before,
refused it. Through the service and its worker, each answer checked against the contract.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from estimate_import_support import as_exported, two_tasks, workbook
from estimate_support import costing
from fastapi.testclient import TestClient
from imports_trial import (
    ROWS,
    TrialFormat,
    analysed,
    apply,
    deposited,
    import_worker,
    open_import,
    path,
    read,
    refusal,
    run,
    stand_in,
    stored,
    trial_file,
    withdraw,
)
from nodes_support import Tree, opened
from projects_support import Person, Scene, contribute, person
from projects_support import scene as make_scene
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

# What an estimator holds: the estimate, read and written, and nothing of the planning.
ESTIMATING = ("estimate.read", "estimate.write")


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
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def kinds(monkeypatch: pytest.MonkeyPatch) -> dict[str, TrialFormat]:
    """Make the formats of the planning and of the remaining to commit the format of the tests.

    Each keeps the permissions of its kind, so that a caller reads the one and not the other.
    """
    planning = TrialFormat(reading="planning.read", permission="planning.write")
    return {
        "ms_project_schedule": stand_in(monkeypatch, "ms_project_schedule", planning),
        "remaining": stand_in(monkeypatch, "remaining", TrialFormat()),
    }


def opened_as(api: ContractClient, stage: Scene, who: Person, kind: str) -> str:
    """Deposit a trial file and open its import of ``kind`` as ``who`` does; give the import."""
    upload_id = deposited(api, who, trial_file(*ROWS))
    response = open_import(api, who, stage.project["project_id"], upload_id, kind=kind)
    assert response.status_code == 202, response.text
    return response.json()["import_id"]


def listed(api: ContractClient, stage: Scene, who: Person) -> dict[str, Any]:
    """List the imports of the project of the stage as ``who`` does; give the page."""
    response = api.get(path(stage), headers=who.headers)
    assert response.status_code == 200, response.text
    return response.json()


def planner(stage: Scene, realm: TestRealm) -> Person:
    """Write a contributor of the project who reads and writes the planning, not the remaining.

    It may create the revision an import of the planning creates, the project having none yet.
    """
    held = ("planning.read", "planning.write", "revisions.write")
    who = person(stage.database, realm, *held, name="Paul")
    contribute(stage.database, stage.project["project_id"], who, "contributor")
    return who


@pytest.mark.usefixtures("kinds")
def test_the_list_of_the_imports_gives_and_counts_the_kinds_its_caller_reads_alone(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # US-2660/L1 (#2473): the route asks for the visibility of the project; the kind is judged by
    # the exchanges. A planner lists the import of the planning and not that of the remaining.
    remaining = opened_as(api, stage, stage.manager, "remaining")
    schedule = opened_as(api, stage, stage.manager, "ms_project_schedule")
    whole = listed(api, stage, stage.manager)
    assert [each["import_id"] for each in whole["items"]] == [schedule, remaining]
    assert whole["meta"]["total"] == 2
    seen = listed(api, stage, planner(stage, realm))
    assert [each["import_id"] for each in seen["items"]] == [schedule]
    assert seen["meta"] == {"limit": 50, "offset": 0, "total": 1}
    # Reading nothing of the exchanges, a contributor lists none, the project still visible.
    idle = person(stage.database, realm, "project_settings.read", name="Ilse")
    contribute(stage.database, stage.project["project_id"], idle, "contributor")
    assert listed(api, stage, idle) == {
        "items": [],
        "meta": {"limit": 50, "offset": 0, "total": 0},
    }
    # The project its caller may not consult stays unknown, whatever the kind.
    assert refusal(api.get(path(stage), headers=stage.outsider.headers))[:2] == (404, "NOT_FOUND")


@pytest.mark.requirement("WF-ADM-0110-A")
@pytest.mark.usefixtures("kinds")
def test_an_import_of_a_kind_its_caller_does_not_read_is_answered_as_an_unknown_import(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # « Une adresse d'objet inexistant et une adresse d'objet non consultable mènent au même
    # écran. » US-2660/L1 (#2473): the import of the remaining, to a planner, is an unknown import,
    # to read as to act on; the import is left as it is.
    import_id = opened_as(api, stage, stage.manager, "remaining")
    who = planner(stage, realm)
    hidden = api.get(path(stage, import_id), headers=who.headers)
    unknown = api.get(path(stage, str(uuid4())), headers=who.headers)
    assert refusal(hidden) == refusal(unknown) == (404, "NOT_FOUND", {})
    # The same body but its correlation, which every answer has its own of.
    assert set(hidden.json()) == set(unknown.json()) == {"code", "status", "correlation_id"}
    applying = api.post(
        f"{path(stage, import_id)}/apply", headers=who.headers, json={"confirmed": True}
    )
    assert refusal(applying)[:2] == (404, "NOT_FOUND")
    rule = api.put(
        f"{path(stage, import_id)}/duration-rule",
        headers=who.headers,
        json={"duration_rule": "keep_dates"},
    )
    assert refusal(rule)[:2] == (404, "NOT_FOUND")
    assert refusal(api.delete(path(stage, import_id), headers=who.headers))[:2] == (
        404,
        "NOT_FOUND",
    )
    assert stored(stage.database, import_id).status == "analysing"
    # Its own kind it reads, as the manager reads both.
    schedule = opened_as(api, stage, who, "ms_project_schedule")
    assert api.get(path(stage, schedule), headers=who.headers).status_code == 200
    assert read(api, stage, import_id)["import_id"] == import_id


@pytest.mark.requirement("WF-ARC-0100-A")
@pytest.mark.usefixtures("kinds")
def test_an_import_whose_requester_no_longer_reads_its_kind_is_refused_its_file_deleted(
    api: ContractClient,
    stage: Scene,
    worker: Worker,
    database: Database,
    backups_bucket: Bucket,
) -> None:
    # « Un import confirmé par un utilisateur dont la permission est retirée avant l'exécution
    # n'est pas appliqué, le refus nomme la condition manquante et son fichier n'est plus sur le
    # stockage objet. » US-2660/L1 (#2473): the reading of the kind, judged with the import, is
    # one of these permissions; the import is unknown to its requester, and refused.
    import_id = analysed(api, stage, worker)["import_id"]
    key = stored(database, import_id).object_key
    withdraw(database, stage.manager, "remaining.read")
    assert refusal(apply(api, stage, import_id))[:2] == (404, "NOT_FOUND")
    row = stored(database, import_id)
    assert (row.status, row.expires_at) == ("refused", None)
    assert backups_bucket.size(key) is None
    found = api.get(path(stage, import_id), headers=stage.participant.headers).json()
    assert found["status"] == "refused"


@pytest.mark.usefixtures("kinds")
def test_an_opening_of_a_kind_its_caller_does_not_read_is_refused_as_unknown(
    api: ContractClient, stage: Scene, realm: TestRealm
) -> None:
    # US-2660/L1 (#2473): the reading of the kind comes before its writing, as on a route that
    # writes a function (404, then 403): a planner opens no import of the remaining.
    who = planner(stage, realm)
    upload_id = deposited(api, who, trial_file(*ROWS))
    response = open_import(api, who, stage.project["project_id"], upload_id, kind="remaining")
    assert refusal(response)[:2] == (404, "NOT_FOUND")
    assert listed(api, stage, stage.manager)["items"] == []


def test_an_estimator_who_does_not_read_the_planning_opens_reads_and_applies_its_estimate(
    api: ContractClient, stage: Scene, worker: Worker, realm: TestRealm
) -> None:
    # US-2660/L1 (#2473): the import of an estimate asks for the estimate alone. The estimator,
    # contributor of the project, holds neither the reading of the planning nor its writing.
    held = two_tasks(Tree(api, stage, opened(api, stage)), costing(stage.database), stage)
    estimator = person(stage.database, realm, *ESTIMATING, name="Élise")
    contribute(stage.database, stage.project["project_id"], estimator, "contributor")
    content = workbook(as_exported(held, {"Heures": 12}), held["tasks"])
    upload_id = deposited(api, estimator, content)
    opening = open_import(api, estimator, stage.project["project_id"], upload_id, kind="estimate")
    assert opening.status_code == 202, opening.text
    import_id = opening.json()["import_id"]
    run(worker)
    found = api.get(path(stage, import_id), headers=estimator.headers)
    assert found.status_code == 200, found.text
    assert found.json()["status"] == "analysed"
    offered = found.json()["available_commands"]
    assert {each["command"]: each["is_available"] for each in offered} == {
        "apply": True,
        "abandon": True,
    }
    assert [each["import_id"] for each in listed(api, stage, estimator)["items"]] == [import_id]
    applying = api.post(
        f"{path(stage, import_id)}/apply", headers=estimator.headers, json={"confirmed": True}
    )
    assert applying.status_code == 202, applying.text
    run(worker)
    assert api.get(path(stage, import_id), headers=estimator.headers).json()["status"] == "applied"
    # What it wrote is the estimate the workbook carries: the labour line now at twelve hours.
    labour = held["labour"]["lineage_id"]
    lines = {
        item["lineage_id"]: item["estimate_line"]
        for item in held["tree"].items()
        if item["kind"] == "estimate_line"
    }
    assert Decimal(lines[labour]["hours"]) == Decimal(12)
