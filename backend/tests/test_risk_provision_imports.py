# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision line of a risk before the imports of an estimate and of a remaining (US-2580/L2).

A provision is its risk's (WF-RIS-0010): no import writes it. A line of the file that carries its
lineage is ignored and named in the report (``provision_lines``), and the line stays as it was; the
file of an estimate that no longer carries it keeps it, signalled (``kept``), never removed
(WF-INTF-0100); the file of a remaining to commit leaves it as every line it does not carry
(WF-INTF-0120). Through the service and its worker; every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_import_support import analysed_import, entry_of, row, workbook
from estimate_support import Costing, Lines, costing
from fastapi.testclient import TestClient
from imports_trial import apply, import_worker, read, run
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_import_support import analysed as remaining_analysed
from remaining_import_support import report as remaining_report
from remaining_import_support import workbook as remaining_workbook
from remaining_support import in_progress, line_named
from risks_support import RISK_LABEL, STUDY, Costed, Risks, costed, material
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.cost_settings.tables import CostCategory
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

PROVISION = f"Provision — {RISK_LABEL}"
OUTSIDE = "Hors sous-projet"


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
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def worker(database: Database, queue: TaskQueue, backups_bucket: Bucket) -> Worker:
    """Give a worker on the queue of the test, which runs the imports and the markings."""
    return import_worker(database, queue, backups_bucket)


def applied(api: ContractClient, stage: Scene, worker: Worker, import_id: str) -> None:
    """Confirm the application of an import analysed and run it; it is applied."""
    answer = apply(api, stage, import_id)
    assert answer.status_code == 202, answer.text
    run(worker)
    assert read(api, stage, import_id)["status"] == "applied"


def held(tree: Tree, label: str) -> tuple[str, str, str, str]:
    """Read what an import must leave of a line: its task, lineage, budgeted and re-estimated."""
    line = line_named(tree, label)
    facet = line["estimate_line"]
    budgeted, reestimated = facet["budgeted_amount"], facet["reestimated_amount"]
    return line["parent_id"], line["lineage_id"], budgeted, reestimated


# The two lines of material of the project costed, by the entry of their task, and their amounts.
MATERIAL = (("1 Étude", "Plans", 600), ("2 Réalisation", "Fabrication", 400))
IGNORED = [{"kind": "provision_lines", "count": 1, "labels": [PROVISION]}]


# --- The estimate (WF-INTF-0100) ------------------------------------------------------------------


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision, in pricing."""
    return costed(api, stage, costs)


def estimate_rows(project: Costed, risk: dict[str, Any] | None, amount: str) -> list[list[Any]]:
    """Give the rows the export writes of the two lines of material, and of the provision line.

    The provision line at the amount said, under the study; none without a risk.
    """
    stage, tree = project.stage, project.tree
    stuff = entry_of(stage.database, CostCategory, project.costs.material)
    rows = [
        row(
            entry,
            stuff,
            {
                "Désignation": label,
                "Quantité": 1,
                "Débours unitaire": float(figure),
                "Délai de paiement (j)": 0,
                "ID ligne": line_named(tree, label)["lineage_id"],
            },
        )
        for entry, label, figure in MATERIAL
    ]
    if risk is not None:
        provision = entry_of(stage.database, CostCategory, project.costs.provision)
        cells = {
            "Désignation": PROVISION,
            "Quantité": 1,
            "Débours unitaire": float(amount),
            "Délai de paiement (j)": 0,
            "ID ligne": line_named(tree, PROVISION)["lineage_id"],
        }
        rows.insert(1, row("1 Étude", provision, cells))
    return rows


def estimate_tasks(project: Costed) -> dict[str, str]:
    """Give the entries of « Tâches »: the two tasks, by their number and label, their lineage."""
    tree = project.tree
    return {
        f"{number} {label}": tree.node(str(project.tasks[label]))["lineage_id"]
        for number, label in ((1, STUDY), (2, "Réalisation"))
    }


def estimate_report(api: ContractClient, project: Costed, worker: Worker, rows: Any) -> Any:
    """Open the import of an estimate and run its analysis; give the import and its report."""
    content = workbook(rows, estimate_tasks(project))
    import_id = analysed_import(api, project.stage, worker, content)
    found = read(api, project.stage, import_id)
    assert found["status"] == "analysed", found
    return import_id, found["report"]


@pytest.mark.requirement("WF-INTF-0100-A")
def test_an_estimate_that_carries_a_provision_line_ignores_it_and_names_it(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # The provision line exported, its amount changed in the file: the import never modifies a
    # provision (`provision_lines`); the line read is neither unchanged nor written, and the line
    # of the risk keeps its task, its lineage, its budget and its amount after the application.
    risks = Risks(api, project)
    risk = risks.declared_costed()
    before = held(project.tree, PROVISION)
    import_id, found = estimate_report(api, project, worker, estimate_rows(project, risk, "999"))
    assert found["ignored"] == IGNORED
    assert (found["read_count"], found["unchanged_count"]) == (3, 2)
    assert (found["rejected"], found["differences"]) == ([], [])
    applied(api, project.stage, worker, import_id)
    assert held(project.tree, PROVISION) == before
    assert risks.risk(risk)["provision_amount"] == "60.00"


@pytest.mark.requirement("WF-INTF-0100-A")
def test_an_estimate_from_which_the_provision_line_was_removed_keeps_it_in_place(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « un devis importé d'où la ligne de provision a été retirée la laisse en place (`kept`,
    # `provision_lines`) » : the line the file no longer carries is kept and signalled, not
    # removed; the application leaves it where it was, at its amount.
    risks = Risks(api, project)
    risk = risks.declared_costed()
    before = held(project.tree, PROVISION)
    import_id, found = estimate_report(api, project, worker, estimate_rows(project, None, "0"))
    assert found["differences"] == [
        {
            "change": "kept",
            "target": "estimate_line",
            "lineage_id": before[1],
            "label": PROVISION,
            "fields": [],
        }
    ]
    assert (found["ignored"], found["unchanged_count"]) == ([], 2)
    applied(api, project.stage, worker, import_id)
    assert held(project.tree, PROVISION) == before
    assert before[0] == str(project.tasks[STUDY])
    assert risks.risk(risk)["provision_amount"] == "60.00"


# --- The remaining to commit (WF-INTF-0120) -----------------------------------------------------


def running(api: ContractClient, stage: Scene, costs: Costing) -> Risks:
    """Give the risks of a project In progress: the wiring, its supplies at 100, then the tests."""

    def build(tree: Tree, lines: Lines) -> None:
        wiring = tree.made("Câblage")
        lines.made(wiring, **material(costs, "Fournitures", "100"))
        tree.made("Essais")

    review = in_progress(api, stage, build)
    tree = review.tree
    tasks = {each["task"]["label"]: UUID(each["node_id"]) for each in tree.items("?kinds=task")}
    project = Costed(
        stage,
        costs,
        tree,
        review.lines,
        UUID(stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
        tasks,
    )
    return Risks(api, project)


@pytest.mark.requirement("WF-INTF-0120-A")
def test_a_remaining_that_carries_a_provision_line_ignores_it_and_leaves_every_line_as_it_was(
    api: ContractClient, stage: Scene, costs: Costing, worker: Worker
) -> None:
    # « … les montants budgétés et les lignées de toutes les lignes sont inchangés après l'import
    # » : the lines of provision of the file are ignored and signalled (`provision_lines`), those of
    # the revision unchanged; the supplies brought to 80 are re-estimated beside them.
    risks = running(api, stage, costs)
    tree = risks.project.tree
    risk = risks.declared_costed(provision_task_id=str(risks.project.tasks["Essais"]))
    before = {label: held(tree, label) for label in ("Fournitures", PROVISION)}
    stuff = entry_of(stage.database, CostCategory, costs.material)
    provision = entry_of(stage.database, CostCategory, costs.provision)
    rows = [
        ["1 Câblage", stuff, "Fournitures", None, 80, before["Fournitures"][1]],
        ["2 Essais", provision, PROVISION, None, 999, before[PROVISION][1]],
    ]
    entries = {
        f"{number} {label}": tree.node(str(risks.project.tasks[label]))["lineage_id"]
        for number, label in ((1, "Câblage"), (2, "Essais"))
    }
    import_id = remaining_analysed(api, stage, worker, remaining_workbook({OUTSIDE: rows}, entries))
    found = remaining_report(api, stage, import_id)
    assert found["ignored"] == IGNORED
    assert [(each["label"], each["fields"]) for each in found["differences"]] == [
        ("Fournitures", ["unit_disbursement"])
    ]
    assert (found["read_count"], found["unchanged_count"], found["rejected"]) == (2, 0, [])
    applied(api, stage, worker, import_id)
    assert held(tree, PROVISION) == before[PROVISION]
    supplies = held(tree, "Fournitures")
    assert supplies[:3] == before["Fournitures"][:3]
    assert supplies[3] == "80.00"
    assert risks.risk(risk)["provision_amount"] == "60.00"
