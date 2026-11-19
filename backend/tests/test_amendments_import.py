# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of the workbook of an estimate on a differential (US-2550/L4; WF-INTF-0100).

On a project In progress, the import of an estimate on the main structure is refused and names the
condition; on a differential, which the request names (``structure_id``), it is analysed then
applied, and only the structure aimed at is written: the main structure and the other differential
are left as they were. Through the service and its worker, each answer checked against the contract.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from amendments_support import listed, on, opened_amendment, structures_path
from estimate_import_support import STATE, entry_of, opening, row, workbook
from estimate_support import Costing, costing
from fastapi.testclient import TestClient
from imports_trial import apply, deposited, import_worker, read, refusal, run
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.tables import CostCategory
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
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


def exported(project: Costed, tree: Any, changes: dict[str, Any]) -> bytes:
    """Write the workbook the export writes of a structure, the line « Plans » changed."""
    items = tree.items()
    lineages = {each["task"]["label"]: each["lineage_id"] for each in items if each["task"]}
    category = entry_of(project.stage.database, CostCategory, project.costs.material)
    lines = {each["estimate_line"]["label"]: each for each in items if each["estimate_line"]}
    rows: list[list[Any]] = []
    for task, label, amount in ((STUDY, "Plans", 600), (MAKING, "Fabrication", 400)):
        rows.append(
            row(
                f"{1 + (task == MAKING)} {task}",
                category,
                {
                    "Désignation": label,
                    "Quantité": 1,
                    "Débours unitaire": amount,
                    "Délai de paiement (j)": 0,
                    "ID ligne": lines[label]["lineage_id"],
                    **(changes if label == "Plans" else {}),
                },
            )
        )
    tasks = {f"{1 + (task == MAKING)} {task}": lineages[task] for task in (STUDY, MAKING)}
    return workbook(rows, tasks)


def amounts(tree: Any) -> dict[str, Decimal]:
    """Read the re-estimated amount of each line of a structure, by its label."""
    return {
        each["estimate_line"]["label"]: Decimal(each["estimate_line"]["reestimated_amount"])
        for each in tree.items()
        if each["estimate_line"]
    }


@pytest.mark.requirement("WF-INTF-0100-A")
def test_on_an_in_progress_project_the_import_of_an_estimate_is_refused_on_the_main_structure(
    api: ContractClient, project: Costed
) -> None:
    # « Sur un projet En cours, l'import d'un devis sur la structure principale est refusé et nomme
    # la condition » : the refusal is EP-07's, kept here with the differential beside it.
    opened_amendment(api, project)
    put_in_state(project.stage.owner, str(project.project_id), "in_progress")
    answer = opening(api, project.stage, exported(project, project.tree, {}))
    assert refusal(answer) == (409, STATE, {"missing_condition": "project_before_in_progress"})


@pytest.mark.requirement("WF-INTF-0100-A")
def test_on_an_in_progress_project_the_import_of_an_estimate_on_a_differential_is_applied(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « sur une structure différentielle, il aboutit » : opened with ``structure_id``, analysed,
    # then applied; only that structure is written, the main one and the other differential are as
    # they were.
    stage = project.stage
    aimed, other = (opened_amendment(api, project, label) for label in ("Avenant 1", "Avenant 2"))
    amendment = on(project.tree, aimed)
    put_in_state(stage.owner, str(project.project_id), "in_progress")
    before = (project.tree.read().json(), on(project.tree, other).read().json())
    assert amounts(amendment)["Plans"] == Decimal("600.00")
    content = exported(project, amendment, {"Débours unitaire": 750})
    upload_id = deposited(api, stage.manager, content)
    opened = api.post(
        f"{PROJECTS}/{project.project_id}/imports",
        headers=stage.manager.headers,
        json={"kind": "estimate", "upload_id": upload_id, "structure_id": aimed},
    )
    assert opened.status_code == 202, opened.text
    import_id = opened.json()["import_id"]
    assert opened.json()["structure_id"] == aimed
    run(worker)
    found = read(api, stage, import_id)
    assert found["status"] == "analysed", found
    answer = apply(api, stage, import_id)
    assert answer.status_code == 202, answer.text
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"
    assert amounts(amendment)["Plans"] == Decimal("750.00")
    assert amounts(amendment)["Fabrication"] == Decimal("400.00")
    assert (project.tree.read().json(), on(project.tree, other).read().json()) == before
    marks = {
        (each["task"] or each["estimate_line"])["label"]: each["difference"]
        for each in amendment.items()
    }
    assert marks["Plans"] == "modified"
    assert marks["Fabrication"] == "unchanged"


@pytest.mark.requirement("WF-INTF-0100-A")
def test_an_import_aimed_at_a_structure_the_revision_does_not_hold_is_not_found(
    api: ContractClient, project: Costed
) -> None:
    upload_id = deposited(api, project.stage.manager, exported(project, project.tree, {}))
    answer = api.post(
        f"{PROJECTS}/{project.project_id}/imports",
        headers=project.stage.manager.headers,
        json={
            "kind": "estimate",
            "upload_id": upload_id,
            "structure_id": "01926f3a-7c00-7000-8000-0000000000ff",
        },
    )
    assert answer.status_code == 404, answer.text


@pytest.mark.requirement("WF-INTF-0100-A")
def test_an_import_analysed_on_a_differential_abandoned_since_is_not_applied(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # The import is kept by the structure it aims at, which no key binds: abandoned since its
    # analysis, the structure is unknown at the application, refused with 404 as at the opening
    # (I-03, #1789), not a failure; the import ends refused and nothing is written.
    stage = project.stage
    aimed = opened_amendment(api, project)
    amendment = on(project.tree, aimed)
    content = exported(project, amendment, {"Débours unitaire": 750})
    upload_id = deposited(api, stage.manager, content)
    opened = api.post(
        f"{PROJECTS}/{project.project_id}/imports",
        headers=stage.manager.headers,
        json={"kind": "estimate", "upload_id": upload_id, "structure_id": aimed},
    )
    assert opened.status_code == 202, opened.text
    import_id = opened.json()["import_id"]
    run(worker)
    assert read(api, stage, import_id)["status"] == "analysed"
    held = next(each for each in listed(api, project) if each["structure_id"] == aimed)
    gone = api.delete(
        f"{structures_path(project)}/{aimed}?lock_version={held['lock_version']}",
        headers=stage.manager.headers,
    )
    assert gone.status_code == 204, gone.text
    before = project.tree.read().json()
    answer = apply(api, stage, import_id)
    assert answer.status_code == 404, answer.text
    assert read(api, stage, import_id)["status"] == "refused"
    run(worker)
    assert read(api, stage, import_id)["status"] == "refused"
    assert project.tree.read().json() == before
