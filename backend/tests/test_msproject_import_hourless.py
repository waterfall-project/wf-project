# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A planning of MS Project whose task falls on a calendar without an hour (US-3210b, #4799).

The import replays the engine without ``dated``: a task the file creates on a default calendar
without an hour, or a task matched whose roles no longer share a day, is refused by the report
(``TASK_WITHOUT_WORKING_HOURS``, ``ImportReport.refusals``), never by an internal error — at the
analysis, and at the application when the calendar loses its hours in between. The task is named
by its lineage and its label, as the report names its objects, and its roles as US-3330 names
them: a task created by its label, its lineage null, without a role; a task matched with the roles
of its labour lines. Every answer is checked against the contract.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Lines, add_role, costing
from fastapi.testclient import TestClient
from imports_trial import import_worker, path, read, run
from nodes_support import Tree, opened
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import select, update
from support import ContractClient
from test_msproject_import import analysed, by_label, imported, planning, task, tasks

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.resource_settings.tables import Calendar, ResourceRole
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from uuid import UUID

    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

pytestmark = pytest.mark.requirement("WF-PLA-0010-A")

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
WEEKDAYS = (8, 8, 8, 8, 8, 0, 0)
WEEKEND = (0, 0, 0, 0, 0, 8, 8)


@pytest.fixture
def services(
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
def api(contract: OpenAPI, services: Services) -> ContractClient:
    """Give a client of the service that deposits in the queue and the bucket of the test."""
    app = create_app(services)
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


def set_week(database: Database, hours: tuple[int, ...], calendar_id: UUID | None = None) -> None:
    """Write the hours of a calendar, the default by default, around the service's guard."""
    days = dict(zip(DAYS, (Decimal(each) for each in hours), strict=True))
    aimed = Calendar.is_default if calendar_id is None else Calendar.id == calendar_id
    with database.transaction() as session:
        session.execute(update(Calendar).where(aimed).values(**days))


def calendar_of_role(database: Database, role_id: UUID) -> UUID:
    """Read the calendar of a role."""
    with database.transaction() as session:
        return session.scalars(
            select(ResourceRole.calendar_id).where(ResourceRole.id == role_id)
        ).one()


def confirmed(api: ContractClient, stage: Scene, worker: Worker, import_id: str) -> dict[str, Any]:
    """Confirm the application of an import analysed, run it; give the import read after."""
    response = api.post(
        f"{path(stage, import_id)}/apply", headers=stage.manager.headers, json={"confirmed": True}
    )
    assert response.status_code == 202, response.text
    run(worker)
    return read(api, stage, import_id)


def test_a_task_the_file_creates_on_a_default_calendar_without_hours_is_refused_by_the_report(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # [US-3210b] #4799: the default calendar has no hour; the task the file creates is named by
    # its label, its lineage null — it has none yet —, and no role: the analysis reports the
    # refusal, where it ended in an internal error; nothing is compared beyond it.
    opened(api, stage)
    set_week(stage.database, (0,) * 7)
    found = analysed(api, stage, worker, planning(task(1, "Études")))
    assert found["report"]["refusals"] == [
        {
            "code": "TASK_WITHOUT_WORKING_HOURS",
            "params": {"resource_roles": [], "tasks": [{"lineage_id": None, "label": "Études"}]},
        }
    ]
    assert found["report"]["date_mismatches"] == []


def test_a_default_calendar_that_loses_its_hours_after_the_report_fails_the_application(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # [US-3210b] #4799: the report accepted, the default calendar loses its hours before the
    # confirmation; the application judges again, fails on the same refusal, and writes nothing.
    opened(api, stage)
    found = analysed(api, stage, worker, planning(task(1, "Études")))
    assert found["report"]["refusals"] == []
    set_week(stage.database, (0,) * 7)
    failed = confirmed(api, stage, worker, found["import_id"])
    assert failed["status"] == "failed"
    assert failed["task"]["problem"]["code"] == "TASK_WITHOUT_WORKING_HOURS"
    assert failed["task"]["problem"]["params"] == {
        "resource_roles": [],
        "tasks": [{"lineage_id": None, "label": "Études"}],
    }
    assert tasks(stage) == []


def test_a_task_matched_whose_roles_no_longer_share_a_day_is_named_with_them(
    api: ContractClient, stage: Scene, worker: Worker
) -> None:
    # [US-3210b] #4799: a task the structure holds, matched by its UID, keeps the lines of two
    # roles; the calendar of one passes to the weekend after the report: the application fails
    # naming the task by its lineage and its label, and both roles, as ``dated`` names them.
    costing(stage.database)
    revision = opened(api, stage)
    content = planning(task(1, "Câblage"))
    imported(api, stage, worker, content)
    node = by_label(stage)["Câblage"][0]
    first = add_role(stage.database, "AA", WEEKDAYS)
    second = add_role(stage.database, "BB", WEEKDAYS)
    lines = Lines(Tree(api, stage, revision))
    for role, label in ((first, "Premier"), (second, "Second")):
        line = {"quantity": "1", "resource_role_id": str(role), "hours": "10", "label": label}
        lines.made(str(node.id), **line)
    roles = [
        {"resource_role_id": str(first), "code": "AA", "label": "Rôle AA"},
        {"resource_role_id": str(second), "code": "BB", "label": "Rôle BB"},
    ]
    named = [{"lineage_id": str(node.lineage_id), "label": "Câblage"}]
    found = analysed(api, stage, worker, content)
    assert found["report"]["refusals"] == []
    set_week(stage.database, WEEKEND, calendar_of_role(stage.database, second))
    again = analysed(api, stage, worker, content)
    assert again["report"]["refusals"] == [
        {
            "code": "TASK_WITHOUT_WORKING_HOURS",
            "params": {"resource_roles": roles, "tasks": named},
        }
    ]
    failed = confirmed(api, stage, worker, found["import_id"])
    assert failed["status"] == "failed"
    problem = failed["task"]["problem"]
    assert problem["code"] == "TASK_WITHOUT_WORKING_HOURS"
    assert problem["params"] == {"resource_roles": roles, "tasks": named}
