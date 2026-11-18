# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a marking keeps, closed by the review of US-1670/L2 (EP-10, "Les tests du back").

Three criteria the tests of ``test_indicators_marked_read`` and ``test_indicators_stored`` leave
open: the document kept of a revision marked without any actual cost carries the cost index as not
computable, as the computation gave it; the project that has no current revision reads, after an
import of actual costs, the indicators of the day changed and the documents kept of its last marked
revision whole; a revision marked that holds no document is refused its project indicators by name
as an offer's is (the decision of #3612). The project is the one of ``test_indicators_stored``.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import declare
from costs_support import load_import
from day_indicators_support import (
    Planned,
    completed,
    dated,
    indicators,
    indicators_answer,
    priced,
    subproject,
)
from fastapi.testclient import TestClient
from imports_trial import import_worker
from indicators_support import clock_setter
from nodes_support import refusal
from planning_support import DAY
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import delete, text
from sqlalchemy.orm import Session
from support import ContractClient
from test_indicators_stored import ONE_DAY, document, kept, marked_now

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.platform.database import utc_now
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from day_indicators_support import Priced
    from indicators_support import Clock
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.platform.storage import Bucket
    from waterfall.worker.runner import Worker

OFFER: tuple[int, str, dict[str, Any]] = (409, "STATE_FORBIDS_OPERATION", {})


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
    """Give a platform, its sessions, the mapping of the extractions declared, and a project."""
    made = make_scene(api, owner, database, realm)
    declare(database)
    return made


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> Clock:
    """Give the means to set the day the indicators are computed on."""
    return clock_setter(monkeypatch)


@pytest.fixture
def lot(api: ContractClient, stage: Scene) -> str:
    """Give a subproject of the project, which the line of the wiring bears."""
    return subproject(api, stage, "10001", "Lot 10001")


@pytest.fixture
def project(api: ContractClient, stage: Scene, lot: str) -> Priced:
    """Give a project In progress of budget 1 000, the studies, 400, completed on ``DAY``."""
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600", lot)])
    completed(found.tree, "Études", DAY)
    return found


def project_path(stage: Scene) -> str:
    """Give the address of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def named(revision_id: str) -> str:
    """Give the query that names a revision."""
    return f"?revision_id={revision_id}"


@pytest.mark.requirement("WF-IND-0010-A")
def test_a_revision_marked_without_actual_cost_keeps_the_cost_index_not_computable(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # « Un indice de coût sans coût réel est affiché non calculable. » (constaté par US-1660) Ici,
    # le document conservé porte l'enveloppe non calculable telle quelle : no line of actual cost,
    # earned value 400, the index has no value and says why; the document is read as kept.
    review = project.tree.revision["revision_id"]
    marked_now(stage, clock, project.tree.revision)
    expected = {
        "value": {"is_computable": False, "value": None, "reason": "no_actual_cost"},
        "zone": None,
    }
    held = document(stage.database, review, "project", PROJECT)
    assert held["actual_cost"] == "0.00"
    assert held["cost_index"] == expected
    found = indicators(api, stage, named(review))
    assert found["context"]["is_stored"] is True
    assert found["cost_index"] == expected


@pytest.mark.requirement("WF-IND-0010-A")
def test_an_import_of_actual_costs_changes_the_day_and_leaves_kept_those_of_the_last_marking(
    api: ContractClient, stage: Scene, worker: Worker, clock: Clock, project: Priced
) -> None:
    # « Sur un projet sans révision en cours, un import de coûts réels change les indicateurs au
    # jour courant et laisse inchangés ceux conservés de la dernière révision marquée. » The exit
    # that marks leaves the project completed with no current revision; every row kept of the
    # revision, whole, and the answer by name, are the same after an import applied; the indicators
    # of the day, without ``revision_id``, change.
    review = project.tree.revision["revision_id"]
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    counter = api.get(project_path(stage), headers=stage.manager.headers).json()["lock_version"]
    body = {
        "to_state": "completed",
        "confirmed": True,
        "lock_version": counter,
        "current_revision": {"action": "mark", "version_name": "Clôture", "description": "Fin"},
    }
    asked = api.post(f"{project_path(stage)}/exit", headers=stage.manager.headers, json=body)
    assert asked.status_code == 202, asked.text
    while worker.step():
        pass
    state = api.get(project_path(stage), headers=stage.manager.headers).json()
    assert (state["state"], state["current_revision_id"]) == ("completed", None)
    clock(utc_now().date() + 5 * ONE_DAY)
    rows_before = kept(stage.database, review)
    assert rows_before
    named_before = indicators(api, stage, named(review))
    day_before = indicators(api, stage)
    assert day_before["actual_cost"] == "500.00"
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-2", None, "250.00", DAY)])
    assert kept(stage.database, review) == rows_before
    assert indicators(api, stage, named(review)) == named_before
    assert named_before["actual_cost"] == "500.00"
    day_after = indicators(api, stage)
    assert day_after["actual_cost"] == "750.00"
    assert day_after["cost_index"] != day_before["cost_index"]


@pytest.mark.requirement("WF-DAT-0040-A")
def test_a_marked_revision_that_holds_no_document_is_refused_its_project_indicators_by_name(
    api: ContractClient, stage: Scene, clock: Clock, project: Priced
) -> None:
    # La décision de #3612 : a revision marked before the indicators were kept holds no row; named
    # on ``getProjectIndicators``, which has nothing to read it from and does not recompute it, it
    # is refused as an offer is, 409 ``STATE_FORBIDS_OPERATION`` without ``params``.
    review = project.tree.revision["revision_id"]
    marked_now(stage, clock, project.tree.revision)
    assert kept(stage.database, review)
    # The table refuses the deletion of a marked row (trigger): the owner lifts it for the test.
    with Session(stage.owner) as session, session.begin():
        session.execute(text("ALTER TABLE revision_indicator DISABLE TRIGGER USER"))
        session.execute(
            delete(RevisionIndicator).where(RevisionIndicator.revision_id == UUID(review))
        )
        session.execute(text("ALTER TABLE revision_indicator ENABLE TRIGGER USER"))
    assert not kept(stage.database, review)
    assert refusal(indicators_answer(api, stage, named(review))) == OFFER
