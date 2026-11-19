# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The merge of a differential applied, through the service and the worker (``mergeCostStructure``).

US-2560/L2. The confirmation of the report, handed to the worker as a task of the kind
``structure_merge``, one operation: what the report presented written into the main structure —
tasks and lines added under lineages new to it, values changed, tasks removed, the started ones
kept and completed —, the lines designated given their figures of reference, the revision marked
under the name confirmed and made the reference, the differential read merged. Every answer is
checked against the contract (``ContractClient``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import on, opened_amendment
from estimate_support import Lines
from history_support import delete, link
from merges_support import (
    asked,
    client,
    costed_project,
    lines_of,
    main_of,
    merged,
    merging_worker,
    project_of,
    read_report,
    revision_of,
    structure_row,
    tasks_of,
)
from nodes_support import put_facts, set_progress, work_breakdown
from risks_support import MAKING, STUDY, Costed, material
from sqlalchemy import update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.projects.interface import current_day
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

DAY = date(2026, 3, 2)


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


def node_of(tree: Any, label: str) -> dict[str, Any]:
    """Read a node of a structure by its label, a task's or a line's."""
    found = [
        each for each in tree.items() if (each["task"] or each["estimate_line"])["label"] == label
    ]
    assert len(found) == 1, label
    return found[0]


# --- What the merge writes ------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_merge_writes_what_the_report_presented_and_marks_the_revision(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Après fusion, la structure principale comporte les tâches ajoutées, les valeurs modifiées et
    # plus aucune des tâches retirées. »: a task and its line added under lineages new to the main
    # structure, a task renamed, a line whose quantity doubles, a task not started removed with
    # its line; « La fusion demande un nom de version, et la révision produite le porte. »;
    # « Après fusion, le projet ne comporte plus de révision en cours. »
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    manager = project.stage.manager
    lines = Lines(tree)
    tests = tree.made("Essais")
    lines.made(tests, **material(project.costs, "Banc d'essai", "50.00"))
    tree.changed(node_of(tree, STUDY), label="Étude détaillée")
    lines.changed(node_of(tree, "Plans"), quantity="2")
    assert delete(tree, node_of(tree, MAKING), manager).status_code == 200
    linked = link(tree, node_of(tree, "Essais"), manager, node_of(tree, "Étude détaillée"))
    assert linked.status_code == 200, linked.text
    before = tasks_of(project, project.structure_id)
    task = merged(
        api, project, worker, amendment, name="Avenant 1", description="Extension du poste"
    )
    assert (task["kind"], task["status"], task["problem"]) == ("structure_merge", "succeeded", None)
    after = tasks_of(project, project.structure_id)
    assert set(after) == {"Étude détaillée", "Essais"}
    # The task renamed keeps its node and its lineage; the task added has a lineage new to the
    # main structure, the one it has in the differential.
    assert after["Étude détaillée"][:2] == before[STUDY][:2]
    assert after["Essais"][1] not in {lineage for _, lineage, _ in before.values()}
    assert after["Essais"][1] == UUID(tests["lineage_id"])
    figures = lines_of(project, project.structure_id)
    assert set(figures) == {"Plans", "Banc d'essai"}
    assert figures["Plans"].reestimated_amount == Decimal("1200.00")
    assert figures["Banc d'essai"].reestimated_amount == Decimal("50.00")
    marked = revision_of(api, project, project.revision_id)
    assert (marked["status"], marked["version_name"], marked["description"]) == (
        "marked",
        "Avenant 1",
        "Extension du poste",
    )
    assert marked["is_reference"] is True
    read = project_of(api, project)
    assert read["current_revision_id"] is None
    assert read["reference_revision_id"] == str(project.revision_id)
    differential = structure_row(project, amendment)
    assert differential.is_merged is True


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_tasks_the_differential_does_not_touch_keep_their_identity_and_their_state(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Les tâches inchangées conservent leur identité et leur état. »: a started task the
    # differential does not touch keeps its node, its lineage, its state and its start, its
    # line its figures.
    set_progress(project.stage, str(project.tasks[MAKING]), "started", DAY)
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    before = tasks_of(project, project.structure_id)[MAKING]
    merged(api, project, worker, amendment)
    assert tasks_of(project, project.structure_id)[MAKING] == before
    making = lines_of(project, project.structure_id)["Fabrication"]
    assert (making.quantity, making.reestimated_amount) == (Decimal(1), Decimal("400.00"))


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_started_task_removed_is_kept_completed_and_its_lines_keep_their_budget(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Une tâche démarrée désignée comme retirée par un différentiel est conservée, son reste à
    # engager est nul, et le montant budgété de ses lignes est inchangé après la fusion : terminée,
    # elle l'acquiert. »: completed on the day of the merge, its start kept, its line at a
    # remaining of nought and its budget of 400 — the project had no reference, so the budget it
    # read from its re-estimated amount is now written. The task starts once the differential
    # copied it, around the service, which leaves the counters as they were.
    amendment = opened_amendment(api, project)
    set_progress(project.stage, str(project.tasks[MAKING]), "started", DAY)
    tree = on(project.tree, amendment)
    assert delete(tree, node_of(tree, MAKING), project.stage.manager).status_code == 200
    found = read_report(api, project, amendment)
    assert [each["label"] for each in found["completed_tasks"]] == [MAKING]
    task = merged(api, project, worker, amendment)
    assert task["status"] == "succeeded", task
    node, _, progress = tasks_of(project, project.structure_id)[MAKING]
    assert (node, progress) == (project.tasks[MAKING], "completed")
    facet = node_of(project.tree, MAKING)["task"]
    assert (facet["started_on"], facet["completed_on"]) == (
        DAY.isoformat(),
        current_day(utc_now()).isoformat(),
    )
    making = lines_of(project, project.structure_id)["Fabrication"]
    assert (making.reestimated_amount, making.budgeted_amount) == (
        Decimal("0.00"),
        Decimal("400.00"),
    )
    assert making.reestimated_at is not None


def put_line(project: Costed, label: str, **values: object) -> None:
    """Write columns of a line of the main structure around the service, as a review would."""
    with project.stage.owner.begin() as connection:
        connection.execute(update(EstimateLine).where(EstimateLine.label == label).values(**values))


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_line_the_differential_does_not_designate_keeps_its_budget_and_its_reestimate(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Une ligne réestimée à 140 pour un montant budgété de 100, non désignée par le différentiel,
    # porte toujours 100 et 140 après la fusion. » and « Une ligne ajoutée en revue périodique,
    # non désignée par le différentiel, garde un montant budgété nul. »: written around the
    # service as the review leaves them — the merge writes neither.
    lines = project.lines
    lines.made(node_of(project.tree, STUDY), **material(project.costs, "Revue", "30.00"))
    lines.changed(node_of(project.tree, "Fabrication"), unit_disbursement="140.00")
    put_line(project, "Fabrication", budgeted_amount=Decimal(100), reestimated_at=utc_now())
    put_line(project, "Revue", budgeted_amount=Decimal(0))
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    merged(api, project, worker, amendment)
    figures = lines_of(project, project.structure_id)
    assert (figures["Fabrication"].budgeted_amount, figures["Fabrication"].reestimated_amount) == (
        Decimal("100.00"),
        Decimal("140.00"),
    )
    assert (figures["Revue"].budgeted_amount, figures["Revue"].reestimated_amount) == (
        Decimal("0.00"),
        Decimal("30.00"),
    )


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_line_the_differential_designates_takes_its_figures_of_reference(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « une ligne désignée reçoit ses grandeurs de référence, et ses grandeurs courantes si sa
    # tâche n'est pas démarrée et qu'elle ne porte pas la marque d'une réestimation » (conception,
    # « La fusion et la survenance »): « Plans » of a task not started takes 2 as reference and
    # as current; « Fabrication », re-estimated, takes 3 as reference, its budget the
    # differential's, and keeps its current figure and its re-estimated amount.
    put_line(project, "Fabrication", reestimated_at=utc_now())
    amendment = opened_amendment(api, project)
    lines = Lines(on(project.tree, amendment))
    tree = on(project.tree, amendment)
    lines.changed(node_of(tree, "Plans"), quantity="2")
    lines.changed(node_of(tree, "Fabrication"), quantity="3")
    merged(api, project, worker, amendment)
    figures = lines_of(project, project.structure_id)
    plans, making = figures["Plans"], figures["Fabrication"]
    assert (plans.quantity, plans.reference_quantity) == (Decimal(2), Decimal(2))
    assert (plans.budgeted_amount, plans.reestimated_amount) == (
        Decimal("1200.00"),
        Decimal("1200.00"),
    )
    assert (making.quantity, making.reference_quantity) == (Decimal(1), Decimal(3))
    assert (making.budgeted_amount, making.reestimated_amount) == (
        Decimal("1200.00"),
        Decimal("400.00"),
    )


@pytest.mark.requirement("WF-PLA-0170-A")
def test_a_task_attached_to_an_order_item_keeps_its_attachment_after_the_merge(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Une tâche rattachée au poste 2 dont un différentiel allonge la durée porte toujours ce
    # rattachement après la fusion. »
    _, item = work_breakdown(project.stage)
    put_facts(project.stage, str(project.tasks[MAKING]), order_item_id=item)
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    tree.changed(node_of(tree, MAKING), duration={"value": "10", "unit": "d"})
    merged(api, project, worker, amendment)
    facet = node_of(project.tree, MAKING)["task"]
    assert facet["order_item_id"] == str(item)
    assert facet["duration"] == {"value": "10", "unit": "d"}
    assert main_of(project, project.revision_id) == project.structure_id


@pytest.mark.requirement("WF-PLA-0170-A")
def test_a_merge_confirmed_despite_an_order_item_out_of_its_package_fails_and_merges_nothing(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « la tâche de fond d'une fusion confirmée malgré lui finit en échec sans rien fusionner »:
    # ORDER_ITEM_OUTSIDE_WORK_PACKAGE, the two tasks named, the revision current, nothing merged.
    stage = project.stage
    package, item = work_breakdown(stage)
    study = str(project.tasks[STUDY])
    post = project.tree.made("Câblage", parent_id=study)
    put_facts(stage, study, work_package_id=package)
    put_facts(stage, post["node_id"], order_item_id=item)
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    held = structure_row(project, amendment).lock_version
    sent = {
        "node_ids": [node_of(tree, "Câblage")["node_id"]],
        "parent_id": node_of(tree, MAKING)["node_id"],
        "lock_version": held,
    }
    moved = api.post(f"{tree.path}/nodes/move", headers=stage.manager.headers, json=sent)
    assert moved.status_code == 200, moved.text
    before = tasks_of(project, project.structure_id)
    answer = asked(api, project, amendment)
    assert answer.status_code == 202, answer.text
    assert worker.step()
    task = api.get(f"/api/v1/tasks/{answer.json()['task_id']}", headers=stage.manager.headers)
    problem = task.json()["problem"]
    assert (task.json()["status"], problem["code"]) == ("failed", "ORDER_ITEM_OUTSIDE_WORK_PACKAGE")
    assert problem["params"] == {
        "work_package_task": {"node_id": study, "label": STUDY},
        "order_item_tasks": [{"node_id": post["node_id"], "label": "Câblage"}],
    }
    assert tasks_of(project, project.structure_id) == before
    assert revision_of(api, project, project.revision_id)["status"] == "draft"
    assert structure_row(project, amendment).is_merged is False
