# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision line of a risk when an import no longer carries its task (US-2580/L1, L2).

A provision is the risk's, never the task's (WF-PLA-0070, WF-RIS-0010): the import of a planning
that drops the task that bears it does not take the line with it. The report presents the line as
updated, its parent (``parent``), the application passes it to the parent of the task removed or to
the first task of the first level left, the counter of its risk advancing with it; a file that
leaves no task at all is refused whole, the risks named (``PROVISION_WITHOUT_TASK``, #4011). Against
the service, with the worker of the imports; every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Lines, costing
from fastapi.testclient import TestClient
from imports_trial import import_worker, path, read, refusal, run
from nodes_support import Tree, opened
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import Costed, Risks
from sqlalchemy import select, update
from support import ContractClient
from test_msproject_import import analysed, applied, opening, planning, task

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.exchanges.tables import ImportReport
from waterfall.core.planning.tables import Node
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

STUDY, SUB, MAKING = "Étude", "Sous-étude", "Réalisation"


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
    return ContractClient(
        TestClient(create_app(import_services), raise_server_exceptions=False), contract
    )


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform whose reference is complete, its sessions, and a project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports."""
    return import_worker(database, queue, backups_bucket)


@pytest.fixture
def risks(api: ContractClient, stage: Scene, worker: Worker) -> Risks:
    """Give the risks of a project whose current revision a planning of three tasks fills.

    The study, the subtask of the study and the making, each told by its ``UID`` to the file that
    comes after (WF-INTF-0040).
    """
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    first = analysed(
        api, stage, worker, planning(task(1, STUDY), task(2, SUB, level=2), task(3, MAKING))
    )
    applied(api, stage, worker, first)
    labels = {each["task"]["label"]: UUID(each["node_id"]) for each in tree.items("?kinds=task")}
    project = Costed(
        stage,
        costing(stage.database),
        tree,
        Lines(tree),
        UUID(stage.project["project_id"]),
        UUID(revision["revision_id"]),
        UUID(tree.structure_id),
        labels,
    )
    return Risks(api, project)


def line_parent(risks: Risks, line_id: str) -> UUID | None:
    """Read the task that bears a line, as the tree holds it."""
    with risks.stage.database.transaction() as session:
        return session.scalar(select(Node.parent_id).where(Node.id == UUID(line_id)))


def difference_of(report: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any]:
    """Give the difference of the report that names the provision line of a risk."""
    named = [each for each in report["differences"] if each["target"] == "estimate_line"]
    assert [each["lineage_id"] for each in named] == [risk["provision_node_id"]]
    return named[0]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_an_import_that_drops_the_task_of_a_provision_passes_the_line_to_the_parent_task(
    api: ContractClient, risks: Risks, stage: Scene, worker: Worker
) -> None:
    # « La suppression de la tâche qui porte une provision […] laisse le devis inchangé, la
    # provision étant passée sur la tâche parente. » — the same, at the compte rendu, for the import
    # of a planning (EP-08, US-2580): the line is not removed with its task, the report says it.
    project = risks.project
    risk = risks.declared_costed(provision_task_id=str(project.tasks[SUB]))
    assert risk["provision_task"]["label"] == SUB
    found = analysed(api, stage, worker, planning(task(1, STUDY), task(3, MAKING)))
    report = found["report"]
    removed = [each["label"] for each in report["differences"] if each["change"] == "removed"]
    assert removed == [SUB]
    difference = difference_of(report, risk)
    assert (difference["change"], difference["fields"]) == ("updated", ["parent"])
    assert difference["label"] == f"Provision — {risk['label']}"
    assert line_parent(risks, risk["provision_node_id"]) == project.tasks[SUB]
    applied(api, stage, worker, found)
    assert line_parent(risks, risk["provision_node_id"]) == project.tasks[STUDY]
    read = risks.risk(risk)
    assert read["provision_task"] == {"node_id": str(project.tasks[STUDY]), "label": STUDY}
    assert (read["provision_amount"], read["lock_version"]) == ("60.00", risk["lock_version"] + 1)
    assert read["provision_node_id"] == risk["provision_node_id"]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_an_import_that_drops_a_first_level_task_passes_its_line_to_the_first_one_left(
    api: ContractClient, risks: Risks, stage: Scene, worker: Worker
) -> None:
    project = risks.project
    risk = risks.declared_costed(provision_task_id=str(project.tasks[MAKING]))
    found = analysed(api, stage, worker, planning(task(1, STUDY), task(2, SUB, level=2)))
    difference_of(found["report"], risk)
    applied(api, stage, worker, found)
    read = risks.risk(risk)
    assert read["provision_task"] == {"node_id": str(project.tasks[STUDY]), "label": STUDY}
    assert read["provision_amount"] == "60.00"
    assert line_parent(risks, risk["provision_node_id"]) == project.tasks[STUDY]


# --- A file that would leave the provision without a task (#4011) ---------------------------------

# A planning whose only task is rejected — its label empty, the task it would create not created:
# the main structure it leaves holds no task.
NO_TASK_LEFT = planning(task(9, ""))


def applying(api: ContractClient, stage: Scene, found: dict[str, Any]) -> Any:
    """Confirm the application of an import analysed; give the answer."""
    return api.post(
        f"{path(stage, found['import_id'])}/apply",
        headers=stage.manager.headers,
        json={"confirmed": True},
    )


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_planning_that_leaves_no_task_under_a_provision_is_refused_by_its_report(
    api: ContractClient, risks: Risks, stage: Scene, worker: Worker
) -> None:
    # « la suppression de la dernière tâche d'une structure principale qui porte une provision est
    # refusée en nommant le risque » — the same, at the report, for the import of a planning: the
    # whole file is refused (``PROVISION_WITHOUT_TASK``, ``params.risks``), and nothing applies.
    risk = risks.declared_costed()
    found = analysed(api, stage, worker, NO_TASK_LEFT)
    report = found["report"]
    assert report["refusals"] == [
        {
            "code": "PROVISION_WITHOUT_TASK",
            "params": {"risks": [{"risk_id": risk["risk_id"], "label": risk["label"]}]},
        }
    ]
    assert [each["code"] for each in report["rejected"]] == ["VALUE_REQUIRED"]
    refused = applying(api, stage, found)
    assert refusal(refused)[2] == {"missing_condition": "import_file_accepted"}
    assert line_parent(risks, risk["provision_node_id"]) == risks.project.tasks[STUDY]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_provision_declared_after_the_report_fails_the_application_by_the_same_reason(
    api: ContractClient, risks: Risks, stage: Scene, worker: Worker
) -> None:
    # The report accepted before any provision, a risk declared before the application: it judges
    # again under the lock, fails by the same reason, and leaves the structure as it was. The
    # provision line written since refuses the import from US-3210 on: the rule is tried on a report
    # without the counter of its structure, analysed before it was kept, applied without comparison.
    found = analysed(api, stage, worker, NO_TASK_LEFT)
    assert found["report"]["refusals"] == []
    with stage.owner.begin() as connection:
        connection.execute(
            update(ImportReport)
            .where(ImportReport.id == UUID(found["import_id"]))
            .values(structure_lock_version=None)
        )
    risk = risks.declared_costed()
    before = risks.project.tree.items()
    answer = applying(api, stage, found)
    assert answer.status_code == 202, answer.text
    run(worker)
    failed = read(api, stage, found["import_id"])
    assert failed["status"] == "failed"
    problem = failed["task"]["problem"]
    assert (problem["code"], problem["params"]) == (
        "PROVISION_WITHOUT_TASK",
        {"risks": [{"risk_id": risk["risk_id"], "label": risk["label"]}]},
    )
    assert risks.project.tree.items() == before


@pytest.mark.requirement("WF-ARC-0100-A")
def test_a_provision_declared_after_the_report_refuses_the_import_with_its_counter_kept(
    api: ContractClient, risks: Risks, stage: Scene, worker: Worker
) -> None:
    # The twin of the test above, the counter of the report kept: « Entre l'analyse et la
    # confirmation, aucune donnée du projet n'a changé. » The provision line written since refuses
    # the application (409 ``import_structure_unchanged``): the import is refused, nothing written.
    found = analysed(api, stage, worker, NO_TASK_LEFT)
    assert found["report"]["refusals"] == []
    risks.declared_costed()
    before = risks.project.tree.items()
    answer = applying(api, stage, found)
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "import_structure_unchanged"},
    )
    assert read(api, stage, found["import_id"])["status"] == "refused"
    assert risks.project.tree.items() == before


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_stranded_provision_line_without_a_risk_is_an_anomaly_not_an_empty_refusal(
    api: ContractClient,
    risks: Risks,
    stage: Scene,
    worker: Worker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A provision line always has its risk: a refusal that would name none is a defect to raise,
    # never a ``PROVISION_WITHOUT_TASK`` without ``params.risks``.
    risks.declared_costed()

    def nobody(*_args: object) -> list[object]:
        return []

    monkeypatch.setattr("waterfall.core.planning.importing.owners_named", nobody)
    response = opening(api, stage, NO_TASK_LEFT)
    assert response.status_code == 202, response.text
    run(worker)
    found = read(api, stage, response.json()["import_id"])
    assert found["status"] == "failed", found
    assert found.get("report") is None
