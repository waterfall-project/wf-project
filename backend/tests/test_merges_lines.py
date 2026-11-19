# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the merge of a differential gives the lines and the links it designates (US-2560/L2).

``mergeCostStructure`` through the service and the worker: the figures a line designated keeps —
its current ones when it is re-estimated or its task started, its budget when the differential
names only what does not price it —, the links of the main structure removed or changed, a summary
left without a subordinate, the task the merge would leave without a working hour, and what the
marking the merge calls keeps of the revision. Every answer is checked against the contract
(``ContractClient``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from actual_costs_import_support import subproject
from amendments_support import node_labelled, on, opened_amendment
from estimate_support import Lines, add_role
from history_support import delete, link
from merges_support import (
    asked,
    client,
    costed_project,
    lines_of,
    links_of,
    merged,
    merging_worker,
    put_line,
    read_report,
    revision_of,
    structure_row,
    task_of,
    tasks_of,
)
from nodes_support import set_progress
from risks_support import MAKING, STUDY, Costed
from sqlalchemy import func, select, update

from waterfall.core.estimate.tables import (
    EstimateLine,
    RevisionCalendar,
    RevisionCategory,
    RevisionRole,
)
from waterfall.core.indicators.tables import RevisionIndicator
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from nodes_support import Tree
    from openapi_core import OpenAPI
    from projects_support import Person
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker

DAY = date(2026, 3, 2)
HOURLESS = "TASK_WITHOUT_WORKING_HOURS"
# The calendars of two roles that share no hour of the week: weekdays, the weekend.
WEEKDAYS = (8, 8, 8, 8, 8, 0, 0)
WEEKEND = (0, 0, 0, 0, 0, 8, 8)


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


def labour(role: object, hours: str = "10") -> dict[str, Any]:
    """Give a labour line of one person for some hours, as the service receives it."""
    return {"quantity": "1", "resource_role_id": str(role), "hours": hours}


def put_role(tree: Tree, label: str, role: UUID) -> None:
    """Give a line of a structure another role around the service, which its entry may refuse."""
    node = UUID(node_labelled(tree, label)["node_id"])
    with tree.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine).where(EstimateLine.node_id == node).values(resource_role_id=role)
        )


def predecessors(tree: Tree, node: dict[str, Any], who: Person, *sent: dict[str, Any]) -> Any:
    """Replace the predecessors of a task, each with its type and its lag; give the answer."""
    body = {"predecessors": list(sent), "lock_version": node["lock_version"]}
    return tree.api.put(
        f"{tree.path}/nodes/{node['node_id']}/predecessors", headers=who.headers, json=body
    )


# --- The figures of a line designated -------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_line_reestimated_or_of_a_started_task_keeps_its_current_figures_whatever_its_role(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « a designated line of a task not started, which nobody has re-estimated since the reference,
    # also takes these quantities as its current quantities; the current quantities and the
    # re-estimated amount of all other lines are kept » (mergeCostStructure): « Calculs »,
    # re-estimated, and « Montage », of a started task, take another role and 20 hours as their
    # reference, the differential's budget, and keep their 10 hours and their re-estimated amount
    # — the two roles of one category, at one rate.
    welder = add_role(project.stage.database, "SOUD", WEEKDAYS)
    project.lines.made(
        node_labelled(project.tree, STUDY), label="Calculs", **labour(project.costs.role)
    )
    project.lines.made(
        node_labelled(project.tree, MAKING), label="Montage", **labour(project.costs.role)
    )
    put_line(project, "Calculs", reestimated_at=utc_now())
    set_progress(project.stage, str(project.tasks[MAKING]), "started", DAY)
    before = lines_of(project, project.structure_id)
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    for label in ("Calculs", "Montage"):
        Lines(tree).changed(node_labelled(tree, label), resource_role_id=str(welder), hours="20")
    sent = lines_of(project, amendment)
    assert merged(api, project, worker, amendment)["status"] == "succeeded"
    after = lines_of(project, project.structure_id)
    for label in ("Calculs", "Montage"):
        line = after[label]
        assert (line.resource_role_id, line.reference_hours) == (welder, Decimal(20))
        assert (line.quantity, line.hours) == (Decimal(1), Decimal(10))
        assert line.reestimated_amount == before[label].reestimated_amount
        assert line.budgeted_amount == sent[label].reestimated_amount != line.reestimated_amount


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_line_designated_by_its_label_subproject_or_delay_alone_keeps_its_budget(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « le budgété ne change que si grandeurs, catégorie ou rôle changent » (merged.py): « Plans »,
    # at a budget of 500 its re-estimate of 600 does not give, renamed, moved to a subproject and
    # paid later by the differential, takes the three and keeps its budget and its figures.
    lot = subproject(api, project.stage)
    put_line(project, "Plans", budgeted_amount=Decimal(500))
    before = lines_of(project, project.structure_id)["Plans"]
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    Lines(tree).changed(
        node_labelled(tree, "Plans"),
        label="Plans révisés",
        subproject_id=lot,
        payment_delay_days=30,
    )
    [designated] = [
        each
        for each in read_report(api, project, amendment)["differences"]
        if each["target"] == "estimate_line"
    ]
    assert designated["fields"] == ["label", "subproject", "payment_delay_days"]
    merged(api, project, worker, amendment)
    plans = lines_of(project, project.structure_id)["Plans révisés"]
    assert (plans.subproject_id, plans.payment_delay_days) == (UUID(lot), 30)
    assert plans.budgeted_amount == Decimal(500)
    assert (plans.quantity, plans.unit_disbursement, plans.reference_quantity) == (
        before.quantity,
        before.unit_disbursement,
        before.reference_quantity,
    )


# --- The links and the summaries ------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_link_of_the_main_structure_the_differential_removes_or_changes_is_so_merged(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Après fusion, la structure principale comporte […] les valeurs modifiées » for the links:
    # Réalisation after Étude, which the differential removes, and Recette after Réalisation, whose
    # lag it brings to two days.
    manager = project.stage.manager
    main = project.tree
    main.made("Recette")
    assert (
        link(main, node_labelled(main, MAKING), manager, node_labelled(main, STUDY)).status_code
        == 200
    )
    assert (
        link(main, node_labelled(main, "Recette"), manager, node_labelled(main, MAKING)).status_code
        == 200
    )
    amendment = opened_amendment(api, project)
    tree = on(main, amendment)
    assert link(tree, node_labelled(tree, MAKING), manager).status_code == 200
    lagged = {
        "predecessor_node_id": node_labelled(tree, MAKING)["node_id"],
        "link_type": "finish_to_start",
        "lag": {"value": "2", "unit": "d"},
    }
    answer = predecessors(tree, node_labelled(tree, "Recette"), manager, lagged)
    assert answer.status_code == 200, answer.text
    merged(api, project, worker, amendment)
    assert links_of(project, project.structure_id) == {
        (MAKING, "Recette", "finish_to_start", Decimal(2), "d")
    }


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_summary_the_merge_leaves_without_a_subordinate_becomes_a_leaf(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « a summary the merge leaves without a subordinate becomes a leaf in the state they gave
    # it » (merging_writing): Étude, a summary of Sous-étude, which the differential removes, is
    # a leaf of the main structure after the merge, under its node, not started.
    main = project.tree
    main.made("Sous-étude", parent_id=str(project.tasks[STUDY]))
    assert node_labelled(main, STUDY)["task"]["is_summary"] is True
    amendment = opened_amendment(api, project)
    tree = on(main, amendment)
    assert delete(tree, node_labelled(tree, "Sous-étude"), project.stage.manager).status_code == 200
    merged(api, project, worker, amendment)
    study = node_labelled(main, STUDY)
    assert (study["node_id"], study["task"]["is_summary"]) == (str(project.tasks[STUDY]), False)
    assert study["task"]["progress"] == "not_started"
    assert set(tasks_of(project, project.structure_id)) == {STUDY, MAKING}


# --- What refuses the merge -----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_merge_that_would_leave_a_task_without_a_working_hour_is_refused_naming_it(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « le moteur de dates rejoué une fois juge […] la tâche sans heure » (conception) and « A merge
    # that would give a task of the main structure a labour line whose role would leave it without
    # any worked hour in the week fails without merging anything […] TASK_WITHOUT_WORKING_HOURS,
    # its params naming the roles and tasks concerned » (mergeCostStructure): Montage, a line of
    # Réalisation the differential designates, takes the weekend role around the service, beside
    # a welder on weekdays; Essais, a task it adds, bears both. Réalisation is named by its node,
    # Essais by its lineage, as the update names a task it adds; the confirmation fails with the
    # first, nothing merged.
    stage = project.stage
    welder = add_role(stage.database, "SOUD", WEEKDAYS)
    fitter = add_role(stage.database, "MONT", WEEKEND)
    making = node_labelled(project.tree, MAKING)
    project.lines.made(making, label="Soudure", **labour(welder, "4"))
    project.lines.made(making, label="Montage", **labour(welder, "4"))
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    tests = tree.made("Essais")
    Lines(tree).made(tests, label="Contrôle", **labour(welder, "4"))
    Lines(tree).made(tests, label="Contrôle week-end", **labour(welder, "4"))
    for label in ("Montage", "Contrôle week-end"):
        put_role(tree, label, fitter)
    refusals = read_report(api, project, amendment)["refusals"]
    assert [each["code"] for each in refusals] == [HOURLESS, HOURLESS]
    assert [each["params"]["tasks"] for each in refusals] == [
        [{"project_id": str(project.project_id), "node_id": making["node_id"], "label": MAKING}],
        [{"lineage_id": tests["lineage_id"], "label": "Essais"}],
    ]
    for each in refusals:
        roles = {
            role["resource_role_id"]: role["code"] for role in each["params"]["resource_roles"]
        }
        assert roles == {str(welder): "SOUD", str(fitter): "MONT"}
    before = tasks_of(project, project.structure_id)
    answer = asked(api, project, amendment)
    assert worker.step()
    task = task_of(api, project, answer)
    assert (task["status"], task["problem"]["code"]) == ("failed", HOURLESS)
    assert task["problem"]["params"] == refusals[0]["params"]
    assert tasks_of(project, project.structure_id) == before
    assert revision_of(api, project, project.revision_id)["status"] == "draft"
    assert structure_row(project, amendment).is_merged is False


# --- What the marking keeps -----------------------------------------------------------------------


def kept_of(project: Costed) -> tuple[int, int]:
    """Count the images of the reference and the documents of indicators the revision keeps."""
    with project.stage.database.transaction() as session:
        images = sum(
            session.scalar(
                select(func.count())
                .select_from(table)
                .where(table.revision_id == project.revision_id)
            )
            or 0
            for table in (RevisionCategory, RevisionRole, RevisionCalendar)
        )
        indicators = session.scalar(
            select(func.count())
            .select_from(RevisionIndicator)
            .where(RevisionIndicator.revision_id == project.revision_id)
        )
    return images, indicators or 0


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_merge_keeps_what_a_marking_keeps_of_the_revision(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « la fusion fait tout ce que fait un marquage — les images du référentiel, la conservation
    # des indicateurs et des courbes (register_marking, register_indicators, EP-10) […] »: the
    # revision the merge marks keeps the images of its categories, its roles and its calendars,
    # and its documents of indicators, which its draft had none of.
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    assert kept_of(project) == (0, 0)
    merged(api, project, worker, amendment)
    images, indicators = kept_of(project)
    assert images > 0
    assert indicators > 0
