# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The import of a planning on the main structure and on the own estimate of a risk (US-2570/L2).

A planning of MS Project is imported on the main structure of a revision that carries the own
estimate of a risk, then the same file on the own estimate (``structure_id`` of ``openImport``):
each import leaves the other structure as it was, its tasks, its lines and its counter, the risk's
counter with the own estimate's (WF-INTF-0090). The own estimate is a differential of the main
structure since US-3070/L3: what the file adds to it is what it designates, and an import on the
main structure puts it out of date. Every answer is checked against the contract
(``ContractClient``).
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import on
from estimate_support import Costing, costing
from fastapi.testclient import TestClient
from imports_trial import deposited, import_worker, path, read, run
from paste_support import counter
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import Costed, Risks, costed
from sqlalchemy import select
from support import ContractClient
from test_msproject_import import KIND, planning, seven_hours_a_day, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.risks.tables import Risk
from waterfall.platform.keycloak_admin import KeycloakAdmin

if TYPE_CHECKING:
    from nodes_support import Tree
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
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


# The planning of the project, then the same one with a task more, which a reimport matches by
# their identifiers in the file: no task of the main structure is removed by it, the one that bears
# the provision of a risk neither (US-2580 settles the removal of that one).
FILE = planning(task(1, "Montage"), task(2, "Recette"))
LATER = planning(task(1, "Montage"), task(2, "Recette"), task(3, "Livraison"))


def content_of(tree: Tree) -> list[tuple[str, str]]:
    """Read what an import must leave as it was: the kind and the label of each node, in order."""
    return [
        (each["kind"], (each["task"] or each["estimate_line"])["label"]) for each in tree.items()
    ]


def risk_counter(project: Costed, risk: dict[str, Any]) -> int:
    """Read the counter of a risk, which its own estimate's follows (#1453)."""
    with project.stage.database.transaction() as session:
        held = session.scalar(select(Risk.lock_version).where(Risk.id == UUID(risk["risk_id"])))
    assert held is not None
    return held


def imported(
    api: ContractClient,
    project: Costed,
    worker: Worker,
    structure_id: str | None = None,
    file: bytes = FILE,
) -> dict[str, Any]:
    """Import a planning on a structure of the current revision, the main one unless named."""
    stage = project.stage
    sent: dict[str, Any] = {"kind": KIND, "upload_id": deposited(api, stage.manager, file)}
    if structure_id is not None:
        sent["structure_id"] = structure_id
    opening = api.post(path(stage), headers=stage.manager.headers, json=sent)
    assert opening.status_code == 202, opening.text
    run(worker)
    found = read(api, stage, opening.json()["import_id"])
    assert found["status"] == "analysed", found
    answer = api.post(
        f"{path(stage, found['import_id'])}/apply",
        headers=stage.manager.headers,
        json={"confirmed": True},
    )
    assert answer.status_code == 202, answer.text
    run(worker)
    done = read(api, stage, found["import_id"])
    assert done["status"] == "applied", done
    return done


def marks_of(tree: Tree) -> list[tuple[str, str]]:
    """Read the difference of each node of an own estimate to its base, by its label, in order."""
    return [
        ((each["task"] or each["estimate_line"])["label"], each["difference"])
        for each in tree.items()
    ]


def up_to_date(api: ContractClient, project: Costed, structure_id: str) -> bool | None:
    """Read whether a structure of the current revision is up to date, as the list gives it."""
    listed = api.get(
        f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/structures",
        headers=project.stage.manager.headers,
    ).json()
    return next(each for each in listed if each["structure_id"] == structure_id)["is_up_to_date"]


@pytest.mark.requirement("WF-INTF-0090-A")
@pytest.mark.story("US-3070")
def test_an_import_on_the_main_structure_leaves_what_the_own_estimate_designates_out_of_date(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « le même fichier appliqué sur la structure principale laisse inchangé ce que le devis propre
    # désigne, et le met en retard » (WF-INTF-0090): its nodes and their marks, its counter and the
    # risk's; the main structure takes the task of the file, which the own estimate does not.
    seven_hours_a_day(project.stage)
    imported(api, project, worker)
    risks = Risks(api, project)
    risk = risks.declared("0.5")
    risks.costed_at(risk, project.revision_id, "200.00")
    own = on(project.tree, risk["structure_id"])
    before = (marks_of(own), counter(own), risk_counter(project, risk))
    assert ("Grue", "added") in before[0]
    assert up_to_date(api, project, risk["structure_id"]) is True
    done = imported(api, project, worker, file=LATER)
    assert done["structure_id"] == project.tree.structure_id
    assert ("task", "Livraison") in content_of(project.tree)
    assert (marks_of(own), counter(own), risk_counter(project, risk)) == before
    assert up_to_date(api, project, risk["structure_id"]) is False


@pytest.mark.requirement("WF-INTF-0090-A")
@pytest.mark.story("US-3070")
def test_the_same_file_imported_on_the_own_estimate_of_a_risk_becomes_what_it_designates(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « l'import d'un planning ou d'un devis sur le devis propre (``structure_id``) s'y applique
    # comme sur un différentiel : ce que le fichier ajoute, change ou ne porte plus devient ce que
    # le devis propre désigne, et la structure principale est inchangée »: the tasks, the lines
    # and the counter of the main structure; the own estimate takes the task the file adds, marked
    # added, its counter advancing, the risk's with it.
    seven_hours_a_day(project.stage)
    imported(api, project, worker)
    risk = Risks(api, project).declared("0.5")
    main_before = (content_of(project.tree), counter(project.tree))
    held = risk_counter(project, risk)
    done = imported(api, project, worker, risk["structure_id"], LATER)
    assert done["structure_id"] == risk["structure_id"]
    own = on(project.tree, risk["structure_id"])
    marks = dict(marks_of(own))
    assert marks["Livraison"] == "added"
    assert (marks["Montage"], marks["Recette"]) == ("unchanged", "unchanged")
    assert (content_of(project.tree), counter(project.tree)) == main_before
    assert risk_counter(project, risk) > held
