# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk declared and read through the service (``createRisk``, ``getRisk``; US-2570/L1).

The declaration on a fresh installation where the category of labour and the role alone were
entered, retaining the category of provision without asking for it, and its refusal once that
category is deactivated (WF-REF-0030); the risk, its own estimate, its provision line and its first
review written in the current revision, created when the project has none; the refusals of the
declaration, in the order of ``declare_risk``, then on each field designated. Every answer is
checked against the contract (``ContractClient``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from nodes_support import Tree, mark, opened
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from waterfall.core.access_roles.predefined import PROJECT_MANAGER
from waterfall.core.cost_settings.interface import (
    CostCategoryDraft,
    create_cost_category,
    set_cost_category_activation,
)
from waterfall.core.cost_settings.tables import CostCategory, CostType
from waterfall.core.projects.interface import (
    SubprojectWrite,
    Viewer,
    create_subproject,
    current_day,
)
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReview
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

LABEL = "Indisponibilité de la grue de levage"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform whose labour category and role alone were entered, and a project."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name, the provision's among them."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000, its two tasks in its main structure."""
    return costed(api, stage, costs)


def risks_path(stage: Scene) -> str:
    """Give the path of the risks of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}/risks"


def declare(api: ContractClient, stage: Scene, who: Any = None, **body: Any) -> Any:
    """Declare a risk at 20 %, as the manager does by default; give the answer."""
    sent = {"label": LABEL, "probability": "0.2", **body}
    return api.post(risks_path(stage), headers=(who or stage.manager).headers, json=sent)


def declared(api: ContractClient, stage: Scene, **body: Any) -> dict[str, Any]:
    """Declare a risk that must be declared; give the risk answered."""
    answer = declare(api, stage, **body)
    assert answer.status_code == 201, answer.text
    return answer.json()


def read(api: ContractClient, stage: Scene, risk_id: str, query: str = "") -> Any:
    """Read a risk, in the revision the query names; give the answer."""
    return api.get(f"{risks_path(stage)}/{risk_id}{query}", headers=stage.manager.headers)


def refused_with(answer: Any, condition: str) -> None:
    """Assert a declaration refused by 409, the condition named."""
    assert answer.status_code == 409, answer.text
    assert answer.json()["params"] == {"missing_condition": condition}


def fields_of(answer: Any) -> list[tuple[str, str]]:
    """Give the fields a 422 names, each with its code."""
    assert answer.status_code == 422, answer.text
    return [(each["pointer"], each["code"]) for each in answer.json()["fields"]]


def counted(stage: Scene) -> tuple[int, int, int]:
    """Count the risks, the evaluations and the structures of the project of the stage."""
    project_id = UUID(stage.project["project_id"])
    with stage.database.transaction() as session:
        risks = session.scalar(select(func.count()).where(Risk.project_id == project_id))
        evaluations = session.scalar(
            select(func.count()).where(RiskEvaluation.project_id == project_id)
        )
        structures = session.scalar(
            select(func.count()).where(CostStructure.project_id == project_id)
        )
    return risks or 0, evaluations or 0, structures or 0


def provision_categories(stage: Scene) -> list[UUID]:
    """Give the categories of the provision kind of the installation."""
    with stage.database.transaction() as session:
        return list(
            session.scalars(
                select(CostCategory.id)
                .join(CostType, CostType.id == CostCategory.cost_type_id)
                .where(CostType.kind == "provision")
            )
        )


def deactivate(stage: Scene, category_id: UUID) -> None:
    """Deactivate a category of the reference through its module, at the version read."""
    with stage.database.transaction() as session:
        held = session.scalar(
            select(CostCategory.lock_version).where(CostCategory.id == category_id)
        )
        assert held is not None
        act = Act(None, utc_now())
        set_cost_category_activation(
            session, category_id, is_active=False, lock_version=held, act=act
        )


# --- WF-REF-0030-A --------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REF-0030-A")
def test_a_risk_is_declared_on_a_fresh_installation_its_provision_category_retained_unasked(
    api: ContractClient, stage: Scene
) -> None:
    # The category of labour and the role alone were entered (``complete_reference``): the project
    # is created (the stage's), and the declaration succeeds without any category of provision
    # entered, the one the installation is delivered with retained without being asked for.
    (delivered,) = provision_categories(stage)
    tree = Tree(api, stage, opened(api, stage))
    tree.made("Études")
    risk = declared(api, stage)
    assert risk["provision_cost_category_id"] == str(delivered)
    assert risk["provision_cost_category_is_active"] is True
    assert risk["state"] == "identified"


@pytest.mark.requirement("WF-RIS-0010-A")
@pytest.mark.requirement("WF-REF-0030-A")
def test_once_the_last_active_provision_category_is_deactivated_a_declaration_is_refused(
    api: ContractClient, stage: Scene
) -> None:
    tree = Tree(api, stage, opened(api, stage))
    tree.made("Études")
    (delivered,) = provision_categories(stage)
    deactivate(stage, delivered)
    before = counted(stage)
    refused_with(declare(api, stage), "active_provision_category")
    assert counted(stage) == before


# --- The declaration ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_risk_declared_has_its_own_estimate_its_provision_line_and_a_first_review(
    api: ContractClient, project: Costed
) -> None:
    # Its own estimate, empty, a structure of the kind risk the list of the structures gives with
    # its risk (#1369); its provision line under the first task of the first level, of nought, its
    # severity and its provision computed, never entered; a first review dated of the day.
    stage = project.stage
    risk = declared(api, stage, description="La grue est louée.", mitigation_notes=None)
    risk_id = UUID(risk["risk_id"])
    assert (risk["label"], risk["description"], risk["mitigation_notes"]) == (
        LABEL,
        "La grue est louée.",
        None,
    )
    assert (risk["probability"], risk["severity"], risk["provision_amount"]) == (
        "0.2",
        "0.00",
        "0.00",
    )
    assert risk["provision_task"] == {"node_id": str(project.tasks[STUDY]), "label": STUDY}
    assert risk["provision_subproject_id"] is None
    assert risk["last_review_on"] == current_day(utc_now()).isoformat()
    assert risk["lock_version"] == 1
    assert [each["field"] for each in risk["computed_fields"]] == ["severity", "provision_amount"]
    assert all(each["is_available"] for each in risk["available_commands"])
    path = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/structures"
    listed = api.get(path, headers=stage.manager.headers).json()
    own = [each for each in listed if each["kind"] == "risk"]
    assert own == [
        {
            **own[0],
            "structure_id": risk["structure_id"],
            "label": LABEL,
            "risk_id": risk["risk_id"],
            "is_merged": False,
        }
    ]
    line = project.tree.node(risk["provision_node_id"])
    assert line["parent_id"] == str(project.tasks[STUDY])
    assert line["estimate_line"]["reestimated_amount"] == "0.00"
    assert line["estimate_line"]["label"] == f"Provision — {LABEL}"
    with stage.database.transaction() as session:
        evaluation = session.scalars(
            select(RiskEvaluation).where(RiskEvaluation.risk_id == risk_id)
        ).one()
        reviews = session.scalars(select(RiskReview).where(RiskReview.risk_id == risk_id)).all()
    assert (evaluation.revision_id, evaluation.state, evaluation.probability) == (
        project.revision_id,
        "identified",
        Decimal("0.2"),
    )
    assert evaluation.provision_task_lineage_id is None
    assert [(each.revision_id, each.state, each.severity) for each in reviews] == [
        (project.revision_id, "identified", Decimal("0.00"))
    ]


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_risk_declared_on_a_task_and_a_subproject_bears_its_provision_there(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    with stage.database.transaction() as session:
        subproject = create_subproject(
            session,
            UUID(stage.project["project_id"]),
            SubprojectWrite("S2", "Lot 2"),
            Act(stage.manager.user_id, utc_now()),
            Viewer(stage.manager.user_id, PROJECT_MANAGER),
        ).subproject_id
    task = project.tasks[MAKING]
    risk = declared(
        api, stage, provision_task_id=str(task), provision_subproject_id=str(subproject)
    )
    assert risk["provision_task"] == {"node_id": str(task), "label": MAKING}
    assert (risk["provision_subproject_id"], risk["provision_subproject_label"]) == (
        str(subproject),
        "Lot 2",
    )
    line = project.tree.node(risk["provision_node_id"])
    assert (line["parent_id"], line["estimate_line"]["subproject_id"]) == (
        str(task),
        str(subproject),
    )
    with stage.database.transaction() as session:
        lineage = session.scalar(
            select(RiskEvaluation.provision_task_lineage_id).where(
                RiskEvaluation.risk_id == UUID(risk["risk_id"])
            )
        )
    assert lineage == task


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_risk_declared_without_a_current_revision_creates_it_by_copy_of_the_last_marked(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    mark(stage, {"revision_id": str(project.revision_id)})
    risk = declared(api, stage)
    with stage.database.transaction() as session:
        current = session.scalars(
            select(Revision).where(
                Revision.project_id == project.project_id, Revision.status == "draft"
            )
        ).one()
        held = session.scalar(
            select(RiskEvaluation.revision_id).where(
                RiskEvaluation.risk_id == UUID(risk["risk_id"])
            )
        )
    assert current.source_revision_id == project.revision_id
    assert held == current.id
    # The provision line is under the copy of the study, in the revision created.
    assert risk["provision_task"]["label"] == STUDY
    assert risk["provision_task"]["node_id"] != str(project.tasks[STUDY])


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_declaration_that_would_create_the_revision_is_refused_to_who_may_not_create_one(
    api: ContractClient, project: Costed, database: Database, realm: TestRealm
) -> None:
    stage = project.stage
    mark(stage, {"revision_id": str(project.revision_id)})
    entering = person(
        database,
        realm,
        *(each for each in PROJECT_MANAGER if each != "revisions.write"),
        name="Léa",
    )
    contribute(database, stage.project["project_id"], entering, "contributor")
    before = counted(stage)
    refused_with(declare(api, stage, entering), "may_create_revision")
    assert counted(stage) == before


@pytest.mark.requirement("WF-RIS-0010-A")
@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_declaration_on_a_main_structure_without_a_task_is_refused(
    api: ContractClient, stage: Scene
) -> None:
    revision = opened(api, stage)
    refused_with(declare(api, stage), "at_least_one_task")
    # « …aboutissent dès qu'une tâche existe. »
    Tree(api, stage, revision).made("Étude")
    assert declare(api, stage).status_code == 201


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_409_of_a_declaration_comes_before_the_designations_of_the_provision_alone(
    api: ContractClient, stage: Scene
) -> None:
    # #3979: on a main structure without a task, a designation that would be refused (422) and a
    # probability out of its bounds, judged with them, are not judged: 409. The label and the shape
    # of the probability, which the schema of the request judges, are refused (422) before it.
    opened(api, stage)
    designated = declare(api, stage, provision_cost_category_id=str(UUID(int=1)), probability="2")
    refused_with(designated, "at_least_one_task")
    assert fields_of(declare(api, stage, label="")) == [("/label", "VALUE_REQUIRED")]
    shape = fields_of(declare(api, stage, probability="beaucoup"))
    assert shape == [("/probability", "VALIDATION_FAILED")]


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_declaration_on_a_terminal_project_is_refused(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    put_in_state(stage.owner, stage.project["project_id"], "abandoned")
    refused_with(declare(api, stage), "project_not_terminal")


@pytest.mark.requirement("WF-RIS-0030-A")
def test_the_designations_of_a_declaration_are_refused_each_on_its_field(
    api: ContractClient, project: Costed
) -> None:
    # A category of labour, a subproject the project does not have, a node that is a line and a
    # probability above 1: each named, nothing written.
    stage = project.stage
    line = next(each for each in project.tree.items() if each["kind"] == "estimate_line")
    before = counted(stage)
    answer = declare(
        api,
        stage,
        probability="1.2",
        provision_cost_category_id=str(project.costs.labour),
        provision_subproject_id=str(project.revision_id),
        provision_task_id=line["node_id"],
    )
    assert fields_of(answer) == [
        ("/probability", "VALUE_OUT_OF_RANGE"),
        ("/provision_cost_category_id", "PROVISION_CATEGORY_REQUIRED"),
        ("/provision_subproject_id", "UNKNOWN_SUBPROJECT"),
        ("/provision_task_id", "UNKNOWN_TASK"),
    ]
    assert answer.json()["fields"][0]["params"] == {"maximum": "1"}
    unknown = declare(api, stage, provision_cost_category_id=str(project.revision_id))
    assert fields_of(unknown) == [("/provision_cost_category_id", "UNKNOWN_COST_CATEGORY")]
    assert counted(stage) == before


@pytest.mark.requirement("WF-RIS-0010-A")
@pytest.mark.requirement("WF-RIS-0030-A")
def test_with_two_active_provision_categories_the_category_is_asked_and_a_deactivated_refused(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    (delivered,) = provision_categories(stage)
    with stage.database.transaction() as session:
        nature = session.scalar(
            select(CostCategory.cost_type_id).where(CostCategory.id == delivered)
        )
        assert nature is not None
        draft = CostCategoryDraft("PRV-002", "Provisions pour aléas fournisseurs", "151002", nature)
        second = create_cost_category(session, draft, Act(None, utc_now())).cost_category_id
    assert fields_of(declare(api, stage)) == [("/provision_cost_category_id", "VALUE_REQUIRED")]
    deactivate(stage, delivered)
    refused = declare(api, stage, provision_cost_category_id=str(delivered))
    assert fields_of(refused) == [("/provision_cost_category_id", "INACTIVE_REFERENCE_OBJECT")]
    risk = declared(api, stage, provision_cost_category_id=str(second))
    assert risk["provision_cost_category_label"] == "Provisions pour aléas fournisseurs"


# --- The reading ----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0030-A")
def test_a_risk_unknown_or_of_a_revision_that_does_not_hold_it_is_not_found(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    risk = declared(api, stage)
    assert read(api, stage, str(project.revision_id)).status_code == 404
    assert (
        read(api, stage, risk["risk_id"], f"?revision_id={stage.project['project_id']}").status_code
        == 404
    )
    assert (
        read(api, stage, risk["risk_id"], f"?revision_id={project.revision_id}").status_code == 200
    )


# --- The commands that announce the declaration ---------------------------------------------------


def lacking(api: ContractClient, path: str, who: Any, command: str) -> list[str] | None:
    """Read what a command lacks on the object at ``path``; none if it is not listed."""
    answer = api.get(path, headers=who.headers)
    assert answer.status_code == 200, answer.text
    for each in answer.json()["available_commands"]:
        if each["command"] == command:
            return each["missing_conditions"]
    return None


def started_marking(api: ContractClient, stage: Scene, revision_id: object) -> None:
    """Ask for the marking of a revision, which the worker does not run: a task is pending."""
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision_id}"
    held = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": held["lock_version"]},
    )
    assert asked.status_code == 202, asked.text


def judged_alike(
    api: ContractClient, stage: Scene, path: str, expected: list[str], who: Any = None
) -> None:
    """Assert ``declare_risk`` at ``path`` lacks ``expected``, ``createRisk`` names its first."""
    who = who or stage.manager
    assert lacking(api, path, who, "declare_risk") == expected
    refused_with(declare(api, stage, who), expected[0])


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_entry_of_the_risks_is_the_projects_until_a_revision_is_current_then_the_revisions(
    api: ContractClient, project: Costed
) -> None:
    # « …`createRisk` est une saisie de la révision en cours, sous `edit_risks`, que la commande
    # `declare_risk` annonce » : la révision en cours les liste, après le reste à engager ; le
    # projet les porte tant qu'il n'en a pas ; une révision marquée n'en liste aucune.
    stage = project.stage
    base = f"{PROJECTS}/{stage.project['project_id']}"
    revision = f"{base}/revisions/{project.revision_id}"
    listed = api.get(revision, headers=stage.manager.headers).json()["available_commands"]
    commands = [each["command"] for each in listed]
    after = commands.index("edit_remaining") + 1
    assert commands[after : after + 2] == ["edit_risks", "declare_risk"]
    assert lacking(api, revision, stage.manager, "edit_risks") == []
    assert lacking(api, revision, stage.manager, "declare_risk") == []
    assert lacking(api, base, stage.manager, "edit_risks") is None
    assert lacking(api, base, stage.manager, "declare_risk") is None
    mark(stage, {"revision_id": str(project.revision_id)})
    assert lacking(api, base, stage.manager, "edit_risks") == []
    assert lacking(api, base, stage.manager, "declare_risk") == []
    assert lacking(api, revision, stage.manager, "edit_risks") is None
    assert lacking(api, revision, stage.manager, "declare_risk") is None


@pytest.mark.requirement("WF-RIS-0020-A")
def test_declare_risk_lacks_what_create_risk_refuses_in_the_same_order_on_a_revision(
    api: ContractClient, stage: Scene
) -> None:
    # An empty revision, then the last category of provision deactivated, then its marking
    # pending: « no_background_task_running, at_least_one_task, active_provision_category ».
    revision = opened(api, stage)
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}"
    judged_alike(api, stage, path, ["at_least_one_task"])
    (delivered,) = provision_categories(stage)
    deactivate(stage, delivered)
    judged_alike(api, stage, path, ["at_least_one_task", "active_provision_category"])
    started_marking(api, stage, revision["revision_id"])
    expected = ["no_background_task_running", "at_least_one_task", "active_provision_category"]
    judged_alike(api, stage, path, expected)
    assert lacking(api, path, stage.manager, "edit_risks") == ["no_background_task_running"]


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_declaration_during_a_marking_is_refused_before_the_category_of_provision(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{project.revision_id}"
    started_marking(api, stage, project.revision_id)
    before = counted(stage)
    judged_alike(api, stage, path, ["no_background_task_running"])
    (delivered,) = provision_categories(stage)
    deactivate(stage, delivered)
    judged_alike(api, stage, path, ["no_background_task_running", "active_provision_category"])
    assert counted(stage) == before


@pytest.mark.requirement("WF-RIS-0020-A")
def test_declare_risk_lacks_what_create_risk_refuses_in_the_same_order_on_the_project(
    api: ContractClient, stage: Scene, database: Database, realm: TestRealm
) -> None:
    # The project has no revision, so the declaration would open one, a copy of nothing: no task. A
    # caller who may not create a revision is told so last, as the 409 does.
    base = f"{PROJECTS}/{stage.project['project_id']}"
    judged_alike(api, stage, base, ["at_least_one_task"])
    (delivered,) = provision_categories(stage)
    deactivate(stage, delivered)
    judged_alike(api, stage, base, ["at_least_one_task", "active_provision_category"])
    entering = person(
        database,
        realm,
        *(each for each in PROJECT_MANAGER if each != "revisions.write"),
        name="Léa",
    )
    contribute(database, stage.project["project_id"], entering, "contributor")
    expected = ["at_least_one_task", "active_provision_category", "may_create_revision"]
    judged_alike(api, stage, base, expected, entering)
    assert lacking(api, base, entering, "edit_risks") == ["may_create_revision"]


@pytest.mark.requirement("WF-RIS-0020-A")
def test_declare_risk_of_the_project_judges_the_last_marked_revision_it_would_copy(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    base = f"{PROJECTS}/{stage.project['project_id']}"
    mark(stage, {"revision_id": str(project.revision_id)})
    assert lacking(api, base, stage.manager, "declare_risk") == []
    (delivered,) = provision_categories(stage)
    deactivate(stage, delivered)
    judged_alike(api, stage, base, ["active_provision_category"])


def task_outside_the_main_structure(stage: Scene, revision_id: object) -> None:
    """Leave the main structure of a revision without a task, the tasks in an amendment.

    The structure that bore them is turned into an amendment and a main one, empty, takes its
    place: what a differential structure bearing a task beside an empty main one looks like.
    """
    with Session(stage.owner) as session, session.begin():
        held = session.execute(
            select(CostStructure).where(
                CostStructure.revision_id == UUID(str(revision_id)), CostStructure.kind == "main"
            )
        ).scalar_one()
        columns = {each.key: getattr(held, each.key) for each in CostStructure.__table__.columns}
        session.execute(
            update(CostStructure)
            .where(CostStructure.project_id == held.project_id, CostStructure.id == held.id)
            .values(kind="amendment", label="Avenant", main_lock_version=held.lock_version)
        )
        session.add(CostStructure(**{**columns, "id": new_id(), "lineage_id": new_id()}))


@pytest.mark.requirement("WF-RIS-0020-A")
def test_declare_risk_of_a_revision_asks_a_task_of_its_main_structure_alone(
    api: ContractClient, project: Costed
) -> None:
    # A task kept by another structure of the revision does not make the declaration possible:
    # the list says what `createRisk` refuses (409 `at_least_one_task`).
    stage = project.stage
    task_outside_the_main_structure(stage, project.revision_id)
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{project.revision_id}"
    judged_alike(api, stage, path, ["at_least_one_task"])


@pytest.mark.requirement("WF-RIS-0020-A")
def test_declare_risk_of_the_project_asks_a_task_of_the_main_structure_it_would_copy(
    api: ContractClient, project: Costed
) -> None:
    # The same on the project without a current revision, which would copy the last marked one.
    stage = project.stage
    task_outside_the_main_structure(stage, project.revision_id)
    mark(stage, {"revision_id": str(project.revision_id)})
    base = f"{PROJECTS}/{stage.project['project_id']}"
    judged_alike(api, stage, base, ["at_least_one_task"])
