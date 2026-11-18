# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The provision line of an identified risk, through the service (``updateRiskProvision``).

US-2580/L1. The category, the subproject and the task of the line changed in the current revision,
created when the project has none, abandoned with it, and refused in the order of
``update_provision`` (WF-RIS-0010, WF-RIS-0020); the line that follows its task when it is deleted
— the parent, the first task of the first level, the last task refused naming the risk — by the
grid and by the import of a planning; the provision ventilated under the nature of its category
and counted at the remaining to commit of its subproject, changed even from a started task whose
subproject received actual costs (WF-PRJ-0050). Every answer is checked against the contract
(``ContractClient``).
"""

import threading
import time
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import cost, load_import
from estimate_support import Costing, costing
from nodes_support import mark, refusal, set_progress
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from planning_support import insert_task
from risks_support import (
    MAKING,
    RISK_LABEL,
    STUDY,
    Costed,
    Risks,
    costed,
    differential,
    material_line,
)
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import DBAPIError

from waterfall.core.access_roles.predefined import PROJECT_MANAGER
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    CostTypeDraft,
    create_cost_category,
    create_cost_type,
    set_cost_category_activation,
)
from waterfall.core.cost_settings.tables import CostCategory
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import Risk, RiskEvaluation
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

CONDITION = "STATE_FORBIDS_OPERATION"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@pytest.fixture
def risks(api: ContractClient, project: Costed) -> Risks:
    """Give the risks of the project costed."""
    return Risks(api, project)


def provisions_total(project: Costed) -> Decimal:
    """Total the lines of the main structure of the revision, the provision lines included."""
    with project.stage.database.transaction() as session:
        held = session.scalar(
            select(func.sum(EstimateLine.reestimated_amount))
            .join(Node, Node.id == EstimateLine.node_id)
            .where(Node.structure_id == project.structure_id)
        )
    return held or Decimal(0)


def another_provision(stage: Scene, code: str = "ALE") -> UUID:
    """Give a category of the provision kind, under a nature other than the one installed."""
    act = Act(None, utc_now())
    with stage.database.transaction() as session:
        nature = create_cost_type(session, CostTypeDraft(code, "Aléas", "provision"), act)
        draft = CostCategoryDraft(
            f"{code}-001", "Aléas fournisseurs", "606003", nature.cost_type_id
        )
        return create_cost_category(session, draft, act).cost_category_id


def refused_by(answer: Any, condition: str) -> None:
    """Assert a refusal by 409, the condition named, and nothing else."""
    assert refusal(answer) == (409, CONDITION, {"missing_condition": condition})


# --- The task ------------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_risk_without_a_designated_task_bears_its_provision_on_the_first_task_and_moves_it(
    risks: Risks, project: Costed
) -> None:
    # « Un risque déclaré sans désignation de tâche porte sa provision sur la première tâche de
    # premier niveau ; la ligne peut être déplacée sur une autre tâche de la structure principale,
    # et le total du devis est inchangé. » 200 at 30 % : a provision of 60 under the study.
    risk = risks.declared()
    assert (risk["provision_amount"], risk["provision_task"]["label"]) == ("60.00", STUDY)
    total = provisions_total(project)
    assert total == Decimal("1060.00")
    moved = risks.provisioned(risk, provision_task_id=str(project.tasks[MAKING]))
    assert moved["provision_task"] == {"node_id": str(project.tasks[MAKING]), "label": MAKING}
    assert moved["provision_node_id"] == risk["provision_node_id"]
    assert moved["lock_version"] == risk["lock_version"] + 1
    assert provisions_total(project) == total
    line = project.tree.node(risk["provision_node_id"])
    assert (line["parent_id"], line["estimate_line"]["reestimated_amount"]) == (
        str(project.tasks[MAKING]),
        "60.00",
    )
    # A task sent as null gives it back to the first task of the first level; one omitted keeps it.
    kept = risks.provisioned(moved, provision_subproject_id=None)
    assert kept["provision_task"]["label"] == MAKING
    back = risks.provisioned(kept, provision_task_id=None)
    assert back["provision_task"]["label"] == STUDY
    assert provisions_total(project) == total


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_lineage_of_the_task_a_risk_designates_is_kept_and_none_for_the_default(
    risks: Risks, project: Costed
) -> None:
    # The lineage of the task designated is kept by the risk (WF-DAT-0030); none for the default.
    designated = risks.declared(provision_task_id=str(project.tasks[MAKING]))
    default = risks.declared()
    with project.stage.database.transaction() as session:
        lineages = dict(
            session.execute(
                select(RiskEvaluation.risk_id, RiskEvaluation.provision_task_lineage_id)
            ).all()
        )
    assert lineages[UUID(designated["risk_id"])] == project.tasks[MAKING]
    assert lineages[UUID(default["risk_id"])] is None
    risks.provisioned(designated, provision_task_id=None)
    with project.stage.database.transaction() as session:
        held = session.scalar(
            select(RiskEvaluation.provision_task_lineage_id).where(
                RiskEvaluation.risk_id == UUID(designated["risk_id"])
            )
        )
    assert held is None


# --- The category and the subproject --------------------------------------------------------------


def natures_of(risks: Risks) -> dict[str, str]:
    """Give the amount of each nature of the estimate, by its label."""
    found = risks.indicators()["by_cost_type"]
    return {each["label"]: each["amount"]["value"] for each in found}


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_estimate_is_ventilated_under_the_nature_of_the_category_the_risk_chose(
    risks: Risks, project: Costed
) -> None:
    # « …la ventilation du devis présente la provision sous la nature de la catégorie choisie ; avec
    # une seule, elle ne la demande pas. » A single category: retained, under the nature installed.
    stage = project.stage
    alone = risks.declared()
    delivered = alone["provision_cost_category_id"]
    assert natures_of(risks)["Provision pour risques"] == "60.00"
    # Two: the category is asked, and the provision follows the nature of the one chosen.
    second = another_provision(stage)
    asked = risks.declare()
    assert asked.status_code == 422
    assert [(each["pointer"], each["code"]) for each in asked.json()["fields"]] == [
        ("/provision_cost_category_id", "VALUE_REQUIRED")
    ]
    chosen = risks.declared("100.00", provision_cost_category_id=str(second))
    assert chosen["provision_cost_category_label"] == "Aléas fournisseurs"
    natures = natures_of(risks)
    assert (natures["Provision pour risques"], natures["Aléas"]) == ("60.00", "30.00")
    # Changed afterwards, the provision of the first moves to the nature of the second.
    changed = risks.provisioned(alone, provision_cost_category_id=str(second))
    assert changed["provision_cost_category_label"] == "Aléas fournisseurs"
    natures = natures_of(risks)
    assert natures.get("Provision pour risques", "0.00") == "0.00"
    assert natures["Aléas"] == "90.00"
    back = risks.provisioned(changed, provision_cost_category_id=delivered)
    assert back["provision_cost_category_id"] == delivered
    assert provisions_total(project) == Decimal("1090.00")


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_category_a_risk_keeps_is_accepted_deactivated_and_another_deactivated_refused(
    risks: Risks, project: Costed
) -> None:
    # Its category deactivated since is accepted as it is (INACTIVE_REFERENCE_OBJECT applies to a
    # value that changes it), a deactivated other refused on its field, nothing written.
    stage = project.stage
    risk = risks.declared()
    second = another_provision(stage)
    with stage.database.transaction() as session:
        held = session.scalar(select(CostCategory.lock_version).where(CostCategory.id == second))
        assert held is not None
        set_cost_category_activation(
            session, second, is_active=False, lock_version=held, act=Act(None, utc_now())
        )
    refused = risks.provision(risk, provision_cost_category_id=str(second))
    assert refused.status_code == 422, refused.text
    assert [(each["pointer"], each["code"]) for each in refused.json()["fields"]] == [
        ("/provision_cost_category_id", "INACTIVE_REFERENCE_OBJECT")
    ]
    assert risks.risk(risk)["lock_version"] == risk["lock_version"]
    kept = risks.provisioned(
        risk, provision_cost_category_id=risk["provision_cost_category_id"], provision_task_id=None
    )
    assert kept["provision_cost_category_id"] == risk["provision_cost_category_id"]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_risk_declared_on_a_subproject_bears_its_provision_in_its_remaining_to_commit(
    risks: Risks,
) -> None:
    # « Un risque déclaré sur le sous-projet S2 porte sa provision au reste à engager de S2 ; sans
    # sous-projet désigné, elle compte hors sous-projet. » 200 at 30 % : 60 under S2, then none.
    s2 = risks.subproject("S2")
    risk = risks.declared(provision_subproject_id=s2)
    assert risk["provision_subproject_label"] == "S2"
    by_key = {each["key"]: each["remaining"] for each in risks.remaining()["by_subproject"]}
    assert (by_key[s2], by_key["unassigned"]) == ("60.00", "1000.00")
    none = risks.provisioned(risk, provision_subproject_id=None)
    assert none["provision_subproject_id"] is None
    by_key = {each["key"]: each["remaining"] for each in risks.remaining()["by_subproject"]}
    assert by_key["unassigned"] == "1060.00"
    assert by_key.get(s2, "0.00") == "0.00"
    again = risks.provisioned(none, provision_subproject_id=s2)
    assert again["provision_subproject_label"] == "S2"
    assert risks.remaining()["total"] == "1060.00"


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_the_provision_of_a_started_task_passes_to_another_subproject_that_received_costs(
    risks: Risks, project: Costed
) -> None:
    # « …celui de la ligne de provision d'un risque identifié [aboutit] » même portée par une tâche
    # démarrée dont le sous-projet a reçu des coûts réels : the line of a started task is refused
    # its subproject (EP-09), the provision of a risk is not.
    stage = project.stage
    s1, s2 = risks.subproject("S1"), risks.subproject("S2")
    risk = risks.declared(provision_subproject_id=s1)
    set_progress(stage, str(project.tasks[STUDY]), "started", date(2026, 3, 2))
    load_import(stage, project.project_id, [cost("FA-1", "S1", "100.00")])
    moved = risks.provisioned(risk, provision_subproject_id=s2)
    assert moved["provision_subproject_label"] == "S2"
    line = project.tree.node(risk["provision_node_id"])["estimate_line"]
    assert line["subproject_id"] == s2
    free = risks.provisioned(moved, provision_subproject_id=None)
    assert free["provision_subproject_id"] is None


# --- The entry, its conditions, its abandonment -------------------------------------------------


def dismiss(project: Costed, risk: dict[str, Any]) -> None:
    """Dismiss a risk around the service: no provision line, as the reviews of US-2590 leave it."""
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskEvaluation)
            .where(RiskEvaluation.risk_id == UUID(risk["risk_id"]))
            .values(state="dismissed", provision_node_id=None)
        )
        connection.execute(delete(Node).where(Node.id == UUID(risk["provision_node_id"])))


def started_marking(api: ContractClient, project: Costed) -> None:
    """Ask for the marking of the revision, which the worker does not run: a task is pending."""
    stage = project.stage
    path = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
    held = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": held["lock_version"]},
    )
    assert asked.status_code == 202, asked.text


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_background_task_that_writes_is_judged_before_the_state_of_the_risk(
    api: ContractClient, risks: Risks, project: Costed
) -> None:
    # no_background_task_running comes before risk_identified, and before the 422 of a category
    # refused, as at the declaration (``createRisk``): nothing is written.
    risk = risks.declared()
    dismiss(project, risk)
    read = risks.risk(risk)
    started_marking(api, project)
    wrong = {"provision_cost_category_id": str(project.costs.labour)}
    refused_by(risks.provision(read, **wrong), "no_background_task_running")
    assert risks.risk(risk)["lock_version"] == read["lock_version"]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_provision_of_a_risk_that_is_not_identified_is_refused_whatever_is_sent(
    risks: Risks, project: Costed
) -> None:
    # « updateRiskProvision … risk_identified »: a category of labour, which would be a 422 of a
    # risk identified, is the 409 of a risk dismissed; the command says it unavailable beforehand.
    risk = risks.declared()
    dismiss(project, risk)
    read = risks.risk(risk)
    commands = {each["command"]: each for each in read["available_commands"]}
    assert commands["update_provision"]["missing_conditions"] == ["risk_identified"]
    wrong = {"provision_cost_category_id": str(project.costs.labour)}
    refused_by(risks.provision(read, **wrong), "risk_identified")
    refused_by(risks.provision(read, provision_task_id=None), "risk_identified")


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_provision_of_a_terminal_project_is_refused_before_everything(
    risks: Risks, project: Costed
) -> None:
    risk = risks.declared()
    put_in_state(project.stage.owner, str(project.project_id), "abandoned")
    refused_by(risks.provision(risk, provision_task_id=None), "project_not_terminal")
    stale = {**risk, "lock_version": 99}
    refused_by(risks.provision(stale, provision_task_id=None), "project_not_terminal")


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_stale_counter_an_unknown_risk_and_the_designations_are_refused_nothing_written(
    risks: Risks, project: Costed
) -> None:
    risk = risks.declared()
    line = next(each for each in project.tree.items() if each["kind"] == "estimate_line")
    stale = risks.provision(
        {**risk, "lock_version": risk["lock_version"] - 1}, provision_task_id=None
    )
    assert refusal(stale) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": risk["lock_version"]},
    )
    unknown = risks.provision({**risk, "risk_id": str(project.revision_id)}, provision_task_id=None)
    assert unknown.status_code == 404
    refused = risks.provision(
        risk,
        provision_cost_category_id=str(project.costs.labour),
        provision_subproject_id=str(project.revision_id),
        provision_task_id=line["node_id"],
    )
    assert refused.status_code == 422, refused.text
    assert [(each["pointer"], each["code"]) for each in refused.json()["fields"]] == [
        ("/provision_cost_category_id", "PROVISION_CATEGORY_REQUIRED"),
        ("/provision_subproject_id", "UNKNOWN_SUBPROJECT"),
        ("/provision_task_id", "UNKNOWN_TASK"),
    ]
    assert risks.risk(risk)["lock_version"] == risk["lock_version"]


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_provision_that_would_create_the_revision_is_refused_to_who_may_not_create_one(
    risks: Risks, project: Costed, database: Database, realm: TestRealm
) -> None:
    stage = project.stage
    risk = risks.declared()
    mark(stage, {"revision_id": str(project.revision_id)})
    entering = person(
        database,
        realm,
        *(each for each in PROJECT_MANAGER if each != "revisions.write"),
        name="Léa",
    )
    contribute(database, stage.project["project_id"], entering, "contributor")
    read = risks.risk(risk)
    commands = {each["command"] for each in read["available_commands"]}
    assert "update_provision" in commands
    refused_by(risks.provision(read, entering, provision_task_id=None), "may_create_revision")
    with stage.database.transaction() as session:
        drafts = session.scalar(
            select(func.count()).where(
                Revision.project_id == project.project_id, Revision.status == "draft"
            )
        )
    assert drafts == 0


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_provision_creates_the_revision_and_its_abandonment_brings_the_risk_back(
    api: ContractClient, risks: Risks, project: Costed
) -> None:
    # An entry of the revision, created by copy of the last marked one when the project has none,
    # that the abandonment of that revision reverts (WF-RIS-0020): the line is back under the study.
    stage = project.stage
    risk = risks.declared()
    mark(stage, {"revision_id": str(project.revision_id)})
    changed = risks.provisioned(risk, provision_task_id=str(project.tasks[MAKING]))
    assert changed["provision_task"]["label"] == MAKING
    assert changed["provision_task"]["node_id"] != str(project.tasks[MAKING])
    with stage.database.transaction() as session:
        current = session.scalars(
            select(Revision).where(
                Revision.project_id == project.project_id, Revision.status == "draft"
            )
        ).one()
    marked = risks.risk(risk, project.revision_id)
    assert marked["provision_task"]["label"] == STUDY
    path = f"{PROJECTS}/{project.project_id}/revisions/{current.id}"
    held = api.get(path, headers=stage.manager.headers).json()
    answer = api.delete(
        path, headers=stage.manager.headers, params={"lock_version": held["lock_version"]}
    )
    assert answer.status_code == 204, answer.text
    back = risks.risk(risk)
    assert back["provision_task"] == marked["provision_task"]
    assert back["lock_version"] > changed["lock_version"]


# --- The line follows its task --------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_deletion_of_the_task_bearing_a_provision_of_40_passes_it_to_the_parent_task(
    risks: Risks, project: Costed
) -> None:
    # « La suppression de la tâche qui porte une provision de 40 laisse le devis inchangé, la
    # provision étant passée sur la tâche parente. » 200 at 20 % is 40, under a subtask of the
    # study: the deletion of the subtask moves the line to the study, says so, and the total stays.
    tree = project.tree
    sub = tree.made("Sous-étude", parent_id=str(project.tasks[STUDY]))
    risk = risks.declared(probability="0.2", provision_task_id=sub["node_id"])
    assert risk["provision_task"]["label"] == "Sous-étude"
    total = provisions_total(project)
    answer = risks.delete(tree.node(sub["node_id"]))
    assert answer.status_code == 200, answer.text
    written = answer.json()
    assert [(each["node_id"], each["parent_id"]) for each in written["nodes"]] == [
        (risk["provision_node_id"], str(project.tasks[STUDY]))
    ]
    assert str(project.tasks[STUDY]) in {each["node_id"] for each in written["ancestors"]}
    assert provisions_total(project) == total
    read = risks.risk(risk)
    assert read["provision_task"] == {"node_id": str(project.tasks[STUDY]), "label": STUDY}
    assert (read["provision_amount"], read["lock_version"]) == ("40.00", risk["lock_version"] + 1)
    assert tree.node(risk["provision_node_id"])["lock_version"] > 1


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_deletion_of_a_first_level_task_passes_its_provision_to_the_first_one_left(
    risks: Risks, project: Costed
) -> None:
    # The first level has no parent: the line goes to the first task of the first level left, and
    # only the lines of the task deleted leave the estimate.
    risk = risks.declared()
    assert risk["provision_task"]["label"] == STUDY
    answer = risks.delete(project.tree.node(str(project.tasks[STUDY])))
    assert answer.status_code == 200, answer.text
    moved = answer.json()["nodes"]
    assert [(each["node_id"], each["parent_id"]) for each in moved] == [
        (risk["provision_node_id"], str(project.tasks[MAKING]))
    ]
    assert provisions_total(project) == Decimal("460.00")
    read = risks.risk(risk)
    assert read["provision_task"]["label"] == MAKING
    assert read["provision_amount"] == "60.00"


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_last_task_of_a_main_structure_that_bears_a_provision_is_not_deleted(
    risks: Risks, project: Costed
) -> None:
    # La suppression de la dernière tâche d'une structure principale qui porte une provision est
    # refusée en nommant le risque : the line would have no task to be placed under.
    risk = risks.declared()
    tree = project.tree
    deleted = risks.delete(tree.node(str(project.tasks[MAKING])))
    assert deleted.status_code == 200, deleted.text
    refused = risks.delete(tree.node(str(project.tasks[STUDY])))
    assert refusal(refused) == (
        409,
        CONDITION,
        {
            "missing_condition": "at_least_one_task",
            "risks": [{"risk_id": risk["risk_id"], "label": RISK_LABEL}],
        },
    )
    assert provisions_total(project) == Decimal("660.00")
    assert risks.risk(risk)["provision_task"]["label"] == STUDY


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_task_bearing_no_provision_is_deleted_as_before_and_gives_no_node(
    risks: Risks, project: Costed
) -> None:
    risks.declared()
    answer = risks.delete(project.tree.node(str(project.tasks[MAKING])))
    assert answer.status_code == 200, answer.text
    assert answer.json()["nodes"] == []
    assert provisions_total(project) == Decimal("660.00")


# --- The order of the locks, the counter judged under it ------------------------------------------


def concurrently(call: Callable[[], Any]) -> tuple[threading.Thread, list[Any]]:
    """Start a call in a thread; give the thread and the list its answer, or its failure, joins."""
    answers: list[Any] = []

    def run() -> None:
        try:
            answers.append(call())
        except BaseException as error:  # noqa: BLE001 - handed back to the test that joins
            answers.append(error)

    thread = threading.Thread(target=run)
    thread.start()
    return thread, answers


def waiting_for_a_lock(stage: Scene) -> None:
    """Wait until a transaction of the database waits for a lock another holds."""
    for _ in range(150):
        with stage.owner.connect() as connection:
            waiting = connection.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity"
                    " WHERE wait_event_type = 'Lock' AND datname = current_database()"
                )
            )
        if waiting:
            return
        time.sleep(0.1)
    pytest.fail("no transaction waits for a lock")


def lock_held(stage: Scene, structure_id: UUID) -> bool:
    """Tell whether another transaction holds the lock of a structure (``FOR UPDATE NOWAIT``)."""
    with stage.owner.connect() as connection:
        try:
            connection.execute(
                select(CostStructure.id)
                .where(CostStructure.id == structure_id)
                .with_for_update(nowait=True)
            )
        except DBAPIError:
            return True
        return False


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_write_of_the_own_estimate_takes_the_main_structure_before_the_risk(
    risks: Risks, project: Costed
) -> None:
    # The order of ``update_provision``: the main structure, then the risk. A write of the own
    # estimate that waits for the risk, held by another, holds the main structure already: were
    # it the other way round, it would hold the risk of ``updateRiskProvision`` on its structure
    # (an interlock, 40P01). The risk held here by the owner, the write stands still on it.
    risk = risks.declared()
    stage = project.stage
    with stage.owner.connect() as holder:
        holder.execute(select(Risk.id).where(Risk.id == UUID(risk["risk_id"])).with_for_update())
        thread, answers = concurrently(lambda: risks.costed_at(risk, "300.00"))
        waiting_for_a_lock(stage)
        assert lock_held(stage, project.structure_id)
        holder.rollback()
    thread.join(timeout=30)
    assert answers == [None]
    assert risks.risk(risk)["lock_version"] > risk["lock_version"]


def counted(project: Costed, table: type[Revision] | type[Node]) -> int:
    """Count the rows of a table of the project: what a provision refused must not have written."""
    with project.stage.database.transaction() as session:
        return session.scalar(
            select(func.count()).select_from(table).where(table.project_id == project.project_id)
        ) or 0


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_counter_of_a_provision_that_would_create_the_revision_is_judged_under_the_lock(
    risks: Risks, project: Costed
) -> None:
    # « updateRiskProvision … 412 »: the risk locked by another that advances its counter while
    # the entry waits, the counter it carries is stale when it gets the lock — it is refused,
    # the revision not created, instead of judged on the counter read before the lock.
    risk = risks.declared()
    stage = project.stage
    mark(stage, {"revision_id": str(project.revision_id)})
    with stage.owner.connect() as holder:
        holder.execute(select(Risk.id).where(Risk.id == UUID(risk["risk_id"])).with_for_update())
        thread, answers = concurrently(lambda: risks.provision(risk, provision_task_id=None))
        waiting_for_a_lock(stage)
        holder.execute(
            update(Risk)
            .where(Risk.id == UUID(risk["risk_id"]))
            .values(lock_version=Risk.lock_version + 1)
        )
        holder.commit()
    thread.join(timeout=30)
    assert len(answers) == 1
    assert refusal(answers[0]) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": risk["lock_version"] + 1},
    )
    assert counted(project, Revision) == 1


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_designation_refused_creates_no_revision_and_writes_nothing(
    risks: Risks, project: Costed
) -> None:
    # « … refusé sur son champ (422) … rien n'est écrit » — also when the entry would have created
    # the revision: it is not created, the risk and its line are as they were.
    risk = risks.declared()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    read = risks.risk(risk)
    revisions, nodes = counted(project, Revision), counted(project, Node)
    refused = risks.provision(read, provision_task_id=str(project.revision_id))
    assert refused.status_code == 422, refused.text
    assert [(each["pointer"], each["code"]) for each in refused.json()["fields"]] == [
        ("/provision_task_id", "UNKNOWN_TASK")
    ]
    assert (counted(project, Revision), counted(project, Node)) == (revisions, nodes)
    with project.stage.database.transaction() as session:
        drafts = session.scalar(
            select(func.count()).where(
                Revision.project_id == project.project_id, Revision.status == "draft"
            )
        )
    assert drafts == 0
    assert risks.risk(risk) == read


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_differential_with_a_provision_line_category_loses_its_last_task_as_any_other(
    risks: Risks, project: Costed
) -> None:
    # « … une structure principale qui porte une ligne de provision » alone is refused
    # (at_least_one_task): a differential holds lines of that category, and no provision of a risk.
    structure_id = differential(project)
    with project.stage.owner.begin() as connection:
        task = insert_task(
            connection, project.project_id, project.revision_id, structure_id, label="Avenant"
        )
        material_line(
            connection,
            (project.project_id, project.revision_id, structure_id, task),
            project.costs.provision,
            Decimal("50.00"),
        )
        held = connection.scalar(select(Node.lock_version).where(Node.id == task))
    path = (
        f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
        f"/structures/{structure_id}/nodes/{task}"
    )
    answer = risks.api.delete(path, headers=risks.headers, params={"lock_version": held})
    assert answer.status_code == 200, answer.text
    assert answer.json()["nodes"] == []


@pytest.mark.requirement("WF-RAE-0010-A")
def test_the_remaining_counts_the_provision_of_a_risk_under_a_completed_task(
    risks: Risks, project: Costed
) -> None:
    # « … plus les provisions des risques identifiés, quel que soit l'état de la tâche qui les
    # porte » : the task of the making completed, its 400 leave the remaining, the provision of 60
    # it bears stays in it.
    risks.declared(provision_task_id=str(project.tasks[MAKING]))
    assert risks.remaining()["total"] == "1060.00"
    set_progress(project.stage, str(project.tasks[MAKING]), "completed", date(2026, 6, 3))
    assert risks.remaining()["total"] == "660.00"
