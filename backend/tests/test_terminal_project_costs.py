# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A terminal project: its remaining and its actual costs read, never written (US-1620/L1).

The reading of the actual costs and of the log of their imports answers on a project completed,
lost or abandoned; the re-estimate of a line, the gesture of the Kanban, the exclusion of a line of
cost and the opening of an import of the actual costs or of the remaining to commit are refused
(409 ``project_not_terminal``) and write nothing. The reading of the indicators of the remaining to
commit and of the startable tasks, and the export of the remaining, are those of the stories that
serve them (US-1600, US-1590, US-1630). Every answer is checked against the contract.
"""

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import extraction, line, opening
from costs_support import cost, load_import
from estimate_support import Costing, Lines, costing
from fastapi.testclient import TestClient
from imports_trial import deposited, open_import
from nodes_support import Tree, refusal
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, review_marked, task_named
from sqlalchemy import func, select
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.costs.tables import CostLine
from waterfall.core.exchanges.tables import ImportReport
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

STATE = "STATE_FORBIDS_OPERATION"
TERMINAL = ["completed", "lost", "abandoned"]
BASIS = "reestimated_amount_basis"


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


@pytest.fixture
def review(api: ContractClient, stage: Scene) -> Review:
    """Give the project In progress, a task and its line, and two lines of cost loaded."""
    costs: Costing = costing(stage.database)

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        lines.made(
            wiring,
            label="Fournitures",
            quantity="1",
            cost_category_id=str(costs.material),
            unit_disbursement="100",
        )

    held = in_progress(api, stage, build)
    load_import(
        stage,
        UUID(stage.project["project_id"]),
        [cost("FA-1", None, "100.00", "10"), cost("FA-2", None, "40.00")],
    )
    return held


def lines_of_cost(stage: Scene) -> list[tuple[str, bool]]:
    """Read the lines of cost as the base holds them: the document, and whether it is tracked."""
    with stage.database.transaction() as session:
        rows = session.execute(
            select(CostLine.document_number, CostLine.is_in_tracked_scope).order_by(
                CostLine.document_number
            )
        )
        return [(number, tracked) for number, tracked in rows]


def imports_opened(stage: Scene) -> int:
    """Count the imports of the exchanges the platform holds."""
    with stage.database.transaction() as session:
        return session.scalar(select(func.count()).select_from(ImportReport)) or 0


def not_terminal(answer: Any) -> None:
    """Check that an answer is the refusal of an operation on a terminal project."""
    assert refusal(answer) == (409, STATE, {"missing_condition": "project_not_terminal"}), (
        answer.text
    )


@pytest.mark.requirement("WF-CYC-0110-A")
@pytest.mark.usefixtures("review")
@pytest.mark.parametrize("state", TERMINAL)
def test_the_actual_costs_and_their_log_are_read_on_a_terminal_project(
    api: ContractClient, stage: Scene, state: str
) -> None:
    # « Toutes les vues de consultation d'un projet clos s'affichent normalement » : the list of the
    # actual costs and the log of their imports, as they were before the project left its cycle.
    base = f"{PROJECTS}/{stage.project['project_id']}"
    before = api.get(f"{base}/actual-costs", headers=stage.manager.headers).json()
    put_in_state(stage.owner, stage.project["project_id"], state)
    listed = api.get(f"{base}/actual-costs", headers=stage.manager.headers)
    assert listed.status_code == 200, listed.text
    assert listed.json() == before
    assert listed.json()["totals"]["overall"] == "140.00"
    log = api.get(f"{base}/cost-imports", headers=stage.manager.headers)
    assert log.status_code == 200, log.text
    assert log.json()["meta"]["total"] == 1
    reader = api.get(f"{base}/actual-costs", headers=stage.reader.headers)
    assert reader.status_code == 200, reader.text


@pytest.mark.requirement("WF-CYC-0100-A")
@pytest.mark.parametrize("state", TERMINAL)
def test_the_reestimate_and_the_gesture_of_the_kanban_are_refused_on_a_terminal_project(
    api: ContractClient, stage: Scene, review: Review, state: str
) -> None:
    # « Toute modification d'un projet terminal est refusée » : the re-estimate of a line and the
    # gesture of a card, nothing written.
    tree = review.tree
    task, row = task_named(tree, "Câblage"), line_named(tree, "Fournitures")
    # A project leaves its cycle with its current revision marked: the state alone would be one no
    # exit leaves behind, and a draft revision is judged first.
    review_marked(stage, tree.revision, "v2.0")
    put_in_state(stage.owner, stage.project["project_id"], state)
    headers = stage.manager.headers
    reestimated = api.put(
        f"{tree.path}/nodes/{row['node_id']}/remaining",
        headers=headers,
        json={"lock_version": row["lock_version"], BASIS: {"unit_disbursement": "150"}},
    )
    not_terminal(reestimated)
    gesture = api.put(
        f"{tree.path}/nodes/{task['node_id']}/progress",
        headers=headers,
        json={
            "progress": "started",
            "occurred_on": date(2026, 6, 3).isoformat(),
            "lock_version": task["lock_version"],
        },
    )
    not_terminal(gesture)
    assert line_named(tree, "Fournitures")["estimate_line"]["unit_disbursement"] == "100.00"
    assert task_named(tree, "Câblage")["task"]["progress"] == "not_started"


@pytest.mark.requirement("WF-CYC-0100-A")
@pytest.mark.usefixtures("review")
@pytest.mark.parametrize("state", TERMINAL)
def test_the_opening_of_an_import_of_costs_or_of_remaining_is_refused_on_a_terminal_project(
    api: ContractClient, stage: Scene, state: str
) -> None:
    put_in_state(stage.owner, stage.project["project_id"], state)
    before = imports_opened(stage)
    not_terminal(opening(api, stage, extraction([line()])))
    upload = deposited(api, stage.manager, b"no workbook")
    not_terminal(open_import(api, stage.manager, stage.project["project_id"], upload))
    assert imports_opened(stage) == before
