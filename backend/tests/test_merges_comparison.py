# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of the revision a merge marks with the marked one that precedes it (US-2560/L3).

``compareRevisions`` of a revision obtained by the merge of a differential: of the same year of
reference, it restitutes the tasks and the budgeted amounts of the differential as its report
presented them, and differs in re-estimated amounts by the lines added or removed, the started
tasks the merge completes and nothing else; of another year, it differs besides on each line whose
rate is projected, the tasks and the budgeted amounts staying those of the differential
(WF-REV-0080). Every answer is checked against the contract (``ContractClient``).
"""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import node_labelled, on, opened_amendment
from estimate_support import YEAR, Lines
from history_support import delete
from merges_support import (
    client,
    costed_project,
    merged,
    merging_worker,
    put_line,
    read_report,
    tasks_of,
)
from nodes_support import Tree, mark, opened, set_progress
from projects_support import PROJECTS, designate
from risks_support import MAKING, STUDY, Costed, material
from sqlalchemy import update

from waterfall.core.projects.tables import Project
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker

REQUIREMENT = "WF-REV-0080-A"
DAY = date(2026, 3, 2)
# An instant of the year after the one the first revision is priced at.
LATER = datetime(YEAR + 1, 1, 12, 10, tzinfo=UTC)


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    return client(contract, database, keycloak, realm_settings, queue)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the merges."""
    return merging_worker(database, queue)


@pytest.fixture
def project(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed_project(api, owner, database, realm)


def labour(project: Costed, label: str, hours: str = "10") -> dict[str, Any]:
    """Give a labour line of one engineer for some hours, as the service receives it."""
    return {
        "label": label,
        "quantity": "1",
        "resource_role_id": str(project.costs.role),
        "hours": hours,
    }


def compared(api: ContractClient, project: Costed, base: object, revision: object) -> Any:
    """Compare a revision with another of the project, as the manager does; give the comparison."""
    path = (
        f"{PROJECTS}/{project.project_id}/revisions/comparison"
        f"?from_revision_id={base}&to_revision_id={revision}"
    )
    answer = api.get(path, headers=project.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def label_of(item: dict[str, Any]) -> str:
    """Give the label of a node returned: its task's, or its line's."""
    facet = item.get("task") or item.get("estimate_line")
    assert facet is not None
    return facet["label"]


def marks(found: dict[str, Any]) -> dict[str, tuple[str, list[str]]]:
    """Give what each node returned bears: its mark and what changes of it."""
    return {label_of(each): (each["difference"], each["changes"]) for each in found["items"]}


def deltas(found: dict[str, Any]) -> dict[tuple[str, str | None], tuple[Decimal, Decimal]]:
    """Give the differences of amounts by dimension and label."""
    return {
        (each["dimension"], each["label"]): (
            Decimal(each["budgeted_delta"]),
            Decimal(each["reestimated_delta"]),
        )
        for each in found["amount_deltas"]
    }


def node_of(tree: Tree, label: str) -> dict[str, Any]:
    """Read a node of a structure by its label, a task's or a line's."""
    found = [
        each for each in tree.items() if (each["task"] or each["estimate_line"])["label"] == label
    ]
    assert len(found) == 1, label
    return found[0]


def following(api: ContractClient, project: Costed) -> Costed:
    """Open the next revision of the project; give the project costed as it stands in it."""
    revision = opened(api, project.stage)
    tree = Tree(api, project.stage, revision)
    tasks = {label: node for label, (node, _, _) in tasks_of(project, tree.structure_id).items()}
    return replace(
        project,
        tree=tree,
        lines=Lines(tree),
        revision_id=UUID(revision["revision_id"]),
        structure_id=UUID(tree.structure_id),
        tasks=tasks,
    )


@pytest.mark.requirement(REQUIREMENT)
def test_the_revision_a_merge_marks_differs_from_the_former_by_the_differential_alone(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « La comparaison d'une révision obtenue par fusion d'un différentiel avec la révision marquée
    # qui la précède, de même année de référence, lorsqu'aucune autre modification n'a été faite
    # entre les deux, restitue exactement les tâches et les montants budgétés de ce différentiel. »
    # and « Les montants réestimés n'y diffèrent que par les lignes que le différentiel ajoute ou
    # retire, par celles des tâches démarrées qu'il termine et par celles dont il change l'année de
    # consommation ; une ligne existante dont le différentiel ne modifie que le montant budgété ne
    # présente aucun écart de montant réestimé. »: the differential adds Essais and its line of
    # 50, renames Étude, takes the reference quantity of Plans — reviewed — from 1 to 2, a budget
    # of 1 200 for 600, and removes Réalisation, started, which the merge completes: its line of
    # 400 goes to a remaining of nought, its budget kept.
    put_line(project, "Plans", reestimated_at=utc_now())
    first = {"revision_id": str(project.revision_id)}
    mark(project.stage, first)
    designate(api, project.stage, first)
    second = following(api, project)
    amendment = opened_amendment(api, second)
    tree = on(second.tree, amendment)
    Lines(tree).made(tree.made("Essais"), **material(second.costs, "Banc d'essai", "50.00"))
    tree.changed(node_labelled(tree, STUDY), label="Étude détaillée")
    Lines(tree).changed(node_labelled(tree, "Plans"), quantity="2")
    set_progress(second.stage, str(second.tasks[MAKING]), "started", DAY)
    assert delete(tree, node_labelled(tree, MAKING), second.stage.manager).status_code == 200
    report = read_report(api, second, amendment)
    assert report["completed_tasks"][0]["label"] == MAKING
    assert merged(api, second, worker, amendment, second.revision_id)["status"] == "succeeded"
    found = compared(api, second, project.revision_id, second.revision_id)
    presented = {(each["target"], each["change"]): each["label"] for each in report["differences"]}
    assert presented[("task", "added")] == "Essais"
    assert presented[("estimate_line", "added")] == "Banc d'essai"
    changes = marks(found)
    assert changes["Essais"][0] == "added"
    assert changes["Banc d'essai"][0] == "added"
    assert changes["Étude détaillée"][0] == "modified"
    assert changes[MAKING][0] == "modified"
    assert changes["Plans"] == ("modified", ["budgeted_amount"])
    assert changes["Fabrication"] == ("modified", ["reestimated_amount", "other"])
    assert changes["Plans"][1] != changes["Fabrication"][1]
    amounts = deltas(found)
    material_delta = next(value for (_, label), value in amounts.items() if label == "Matériel")
    # Budgeted: 50 of the line added, 600 of the line of Plans; the line of the started task keeps
    # its budget. Re-estimated: 50 of the line added, and the 400 of the started task given back.
    assert material_delta == (Decimal("650.00"), Decimal("-350.00"))


@pytest.mark.requirement(REQUIREMENT)
def test_between_two_years_of_reference_the_merge_differs_by_the_rate_of_each_line_besides(
    api: ContractClient,
    project: Costed,
    worker: Worker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Entre deux révisions d'années de référence différentes, les montants réestimés diffèrent en
    # outre sur chaque ligne dont le taux a été mis à jour ou projeté jusqu'à la nouvelle année de
    # référence (WF-REV-0060) ; […] les tâches et les montants budgétés restent ceux du
    # différentiel. » (spécification 1.0.7, #3366): the first revision marked and designated, the
    # next opened the year after at an inflation of 3 %, its differential adds a task and a line
    # of labour and nothing else, and is merged; the line of labour of Étude, which the
    # differential does not name, differs by its re-estimated amount alone, the task and the line
    # added are the differential's. The line of a disbursement is the object of #3983.
    first = {"revision_id": str(project.revision_id)}
    project.lines.made(node_of(project.tree, STUDY), **labour(project, "Ingénierie"))
    mark(project.stage, first)
    designate(api, project.stage, first)
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(Project)
            .where(Project.id == project.project_id)
            .values(inflation_rate=Decimal("0.03"))
        )
    monkeypatch.setattr("waterfall.api.revisions.utc_now", lambda: LATER)
    second = following(api, project)
    before = node_of(project.tree, "Ingénierie")["estimate_line"]
    amendment = opened_amendment(api, second)
    tree = on(second.tree, amendment)
    Lines(tree).made(tree.made("Recette"), **labour(second, "Recette — Ingénieur", "5"))
    assert merged(api, second, worker, amendment, second.revision_id)["status"] == "succeeded"
    found = compared(api, second, project.revision_id, second.revision_id)
    after = node_of(second.tree, "Ingénierie")["estimate_line"]
    assert Decimal(after["budgeted_amount"]) == Decimal(before["budgeted_amount"])
    moved = Decimal(after["reestimated_amount"]) - Decimal(before["reestimated_amount"])
    assert moved > 0
    changes = marks(found)
    assert changes["Recette"][0] == "added"
    assert changes["Recette — Ingénieur"][0] == "added"
    assert changes["Ingénierie"][0] == "modified"
    assert "reestimated_amount" in changes["Ingénierie"][1]
    assert "budgeted_amount" not in changes["Ingénierie"][1]
    added = node_of(second.tree, "Recette — Ingénieur")["estimate_line"]
    amount = Decimal(added["reestimated_amount"])
    assert amount > 0
    labour_delta = deltas(found)[("cost_type", "Main-d'œuvre")]
    assert labour_delta == (amount, amount + moved)
