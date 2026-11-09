# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The command ``import_planning`` of a project and the refusal of ``openImport`` say the same.

Against the service: the project lists the import of a planning to whoever holds ``planning.write``,
names ``may_create_revision`` without a current revision to whoever cannot create one, and the
opening of the import refuses by that very condition (US-1430/L4, WF-INTF-0090). Every answer is
checked against the contract.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from imports_trial import deposited, open_import, refusal
from nodes_support import opened
from projects_support import PROJECTS, contribute, person
from projects_support import scene as make_scene
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket

CORPUS = Path(__file__).resolve().parents[2] / "fixtures" / "msproject"
KIND = "ms_project_schedule"
COMMAND = "import_planning"


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
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def commands(body: dict[str, Any]) -> dict[str, list[str]]:
    """Give the conditions each command a project lists lacks, by command."""
    return {each["command"]: each["missing_conditions"] for each in body["available_commands"]}


@pytest.mark.requirement("WF-INTF-0090")
def test_the_project_lists_the_import_of_a_planning_to_whoever_holds_the_planning_permission(
    api: ContractClient, stage: Scene
) -> None:
    path = f"{PROJECTS}/{stage.project['project_id']}"
    listed = api.get(path, headers=stage.manager.headers).json()
    names = [each["command"] for each in listed["available_commands"]]
    assert names[names.index("generate_skeleton") + 1] == COMMAND
    assert commands(listed)[COMMAND] == []
    # Absent from whoever lacks the permission, still listed once a revision is in progress.
    assert COMMAND not in commands(api.get(path, headers=stage.reader.headers).json())
    opened(api, stage)
    assert commands(api.get(path, headers=stage.manager.headers).json())[COMMAND] == []


@pytest.mark.requirement("WF-INTF-0090")
def test_the_command_names_may_create_revision_and_the_opening_refuses_by_the_same_condition(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    project_id = stage.project["project_id"]
    path = f"{PROJECTS}/{project_id}"
    lacking = person(database, realm, "planning.read", "planning.write", "project_settings.read")
    contribute(database, project_id, lacking, "contributor")
    seen = api.get(path, headers=lacking.headers).json()
    assert commands(seen)[COMMAND] == ["may_create_revision"]
    content = (CORPUS / "01-links-and-lags-days.xml").read_bytes()
    response = open_import(api, lacking, project_id, deposited(api, lacking, content), kind=KIND)
    assert refusal(response) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "may_create_revision"},
    )
