# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A revision marked by the exit of a project is a point of the time/time diagram (US-1710).

The diagram reads a marked revision when it kept the indicators of the project, which only a project
In progress does (US-1670/L1); the criterion names a marking after the passage In progress. The two
agree: the marking of an exit (``exitProject`` with the fate ``mark``, done In progress, run by the
worker) gives a point, the reference marked before In progress gives none.
"""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from indicators_support import clock_setter
from milestone_tracking_support import (
    DELIVERY,
    JUNE_30,
    START,
    STUDIES,
    TIME_TIME,
    Project,
    milestone,
    points,
)
from projects_support import PROJECTS
from projects_support import scene as make_scene
from support import ContractClient, nowhere

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.worker.marking import mark
from waterfall.worker.runner import Timing, Worker

if TYPE_CHECKING:
    from indicators_support import Clock
    from openapi_core import OpenAPI
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings

AT_ONCE = Timing(claim_after=0, block=0.01, redeposit_every=0)


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
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the diagram is computed on."""
    return clock_setter(monkeypatch)


@pytest.mark.requirement("WF-IND-0090-A")
def test_the_marking_of_an_exit_gives_a_point_and_the_reference_marked_before_none(
    api: ContractClient, stage: Scene, clock: Clock, database: Database, queue: TaskQueue
) -> None:
    # The project In progress, current revision still open: the exit that marks it (202, then the
    # worker marks, then exits) leaves one marked revision that kept the indicators — the point of
    # the exit — besides the reference, marked before In progress, which is no point.
    project = Project(api, stage, clock)
    project.track(STUDIES, TIME_TIME)
    project.track(DELIVERY, TIME_TIME)
    project.date(STUDIES, JUNE_30)
    clock(START)
    path = f"{PROJECTS}/{project.project_id}"
    read = api.get(path, headers=stage.manager.headers)
    assert read.status_code == 200, read.text
    sent = {
        "to_state": "abandoned",
        "confirmed": True,
        "current_revision": {"action": "mark", "version_name": "Clôture"},
        "lock_version": read.json()["lock_version"],
    }
    asked = api.post(f"{path}/exit", headers=stage.manager.headers, json=sent)
    assert asked.status_code == 202, asked.text
    queue.prepare()
    assert Worker(database, queue, {"revision_mark": mark}, "worker", AT_ONCE).step()
    body = project.diagram()
    # The reference, marked before, would make a third point; the exit makes one, then the day.
    found = milestone(body, STUDIES)
    assert [each[1] for each in points(found)] == ["2027-06-30", "2027-06-30"]
