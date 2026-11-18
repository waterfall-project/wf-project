# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A differential opened and listed (``createCostStructure``, ``listCostStructures``; US-2550/L3).

The differential is born as the copy of the main structure of its revision, its planning start
date included, every node the main structure's by its lineage and read ``unchanged``; it is
refused on a marked revision and while a background task runs; the list gives every nature of
structure of the revision read, each with its commands; a revision whose only a differential bears
a task lists the skeleton available (#2541). Every answer is checked against the contract
(``ContractClient``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import (
    commands_of,
    listed,
    on,
    open_amendment,
    opened_amendment,
    revision_commands,
    started_marking,
    structures_path,
)
from estimate_support import Costing, costing
from nodes_support import Tree, mark, opened, put_facts, work_breakdown
from projects_support import PROJECTS, Scene, put_in_state
from projects_support import scene as make_scene
from risks_support import STUDY, Costed, costed, declared
from sqlalchemy import select, update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node, Task
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


def rows_of(project: Costed, structure_id: str) -> list[tuple[Any, ...]]:
    """Read the nodes of a structure by their lineage, without their identifiers."""
    with project.stage.database.transaction() as session:
        nodes = session.scalars(select(Node).where(Node.structure_id == UUID(structure_id))).all()
        return sorted((each.lineage_id, each.kind, each.rank, each.lock_version) for each in nodes)


def structures_counted(project: Costed) -> int:
    """Count the structures of the project costed."""
    with project.stage.database.transaction() as session:
        return len(
            session.scalars(
                select(CostStructure.id).where(CostStructure.project_id == project.project_id)
            ).all()
        )


# --- WF-REV-0100-A: the opening -------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_differential_is_born_the_copy_of_the_main_structure_planning_start_included(
    api: ContractClient, project: Costed
) -> None:
    # The planning start date of the main structure is changed first: the copy takes it, and the
    # nodes it holds, each under an identifier of its own and the lineage of the main node; the
    # attachment of a task to the work breakdown is the main structure's alone (WF-PLA-0170).
    day = date(2026, 3, 9)
    package, _ = work_breakdown(project.stage)
    put_facts(project.stage, str(project.tasks[STUDY]), work_package_id=package, order_item_id=None)
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure)
            .where(CostStructure.id == UUID(project.tree.structure_id))
            .values(planning_start_on=day)
        )
    answer = open_amendment(api, project, "Avenant « reprise des essais »")
    assert answer.status_code == 201, answer.text
    created = answer.json()
    assert created["kind"] == "amendment"
    assert created["label"] == "Avenant « reprise des essais »"
    assert created["planning_start_on"] == day.isoformat()
    assert (created["is_merged"], created["lock_version"]) == (False, 1)
    assert "risk_id" not in created
    assert rows_of(project, created["structure_id"]) == rows_of(project, project.tree.structure_id)
    with project.stage.database.transaction() as session:
        main = session.scalars(
            select(Node.id).where(Node.structure_id == UUID(project.tree.structure_id))
        ).all()
        copied = session.scalars(
            select(Node.id).where(Node.structure_id == UUID(created["structure_id"]))
        ).all()
        attached = session.scalars(
            select(Task.structure_id).where(Task.work_package_id == package)
        ).all()
    assert len(copied) == len(main) == 4
    assert not set(main) & set(copied)
    assert attached == [UUID(project.tree.structure_id)]


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_lines_of_a_differential_keep_the_figures_of_the_main_structures_as_they_are(
    api: ContractClient, project: Costed
) -> None:
    # Not the reference's again: the budgeted amount a line of the main structure holds is the
    # copy's, and so is what it holds of the remaining to commit before (EP-09).
    plans = next(each for each in project.tree.items() if each["task"] is None)
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == UUID(plans["node_id"]))
            .values(budgeted_amount=Decimal("550.00"), previous_quantity=Decimal(2))
        )
    structure_id = opened_amendment(api, project)

    def figures(id_: str) -> dict[UUID, tuple[Any, ...]]:
        with project.stage.database.transaction() as session:
            rows = session.execute(
                select(
                    Node.lineage_id,
                    EstimateLine.budgeted_amount,
                    EstimateLine.previous_quantity,
                    EstimateLine.reestimated_amount,
                    EstimateLine.base_amount,
                    EstimateLine.consumption_year,
                    EstimateLine.lock_version,
                )
                .join(Node, Node.id == EstimateLine.node_id)
                .where(Node.structure_id == UUID(id_))
            )
            return {row[0]: tuple(row[1:]) for row in rows}

    held = figures(project.tree.structure_id)
    assert figures(structure_id) == held
    assert (Decimal("550.00"), Decimal(2)) in {each[:2] for each in held.values()}


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_revision_of_another_project_is_not_found_before_it_is_judged(
    api: ContractClient, project: Costed
) -> None:
    mark(project.stage, project.tree.revision)
    path = f"{PROJECTS}/{project.project_id}/revisions/{UUID(int=7)}/structures"
    answer = api.post(
        path,
        headers=project.stage.manager.headers,
        json={"kind": "amendment", "label": "Avenant"},
    )
    assert answer.status_code == 404, answer.text


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_reading_of_a_differential_returns_its_marks_whatever_fields_names(
    api: ContractClient, project: Costed
) -> None:
    tree = on(project.tree, opened_amendment(api, project))
    read = tree.read("?fields=task.label")
    assert read.status_code == 200, read.text
    for each in read.json()["items"]:
        assert each["difference"] == "unchanged"
        assert each["changes"] == []
        assert {"node_id", "row_number", "level", "lock_version"} <= set(each)


@pytest.mark.requirement("WF-REV-0100-A")
def test_every_node_of_a_differential_just_opened_is_the_main_ones_and_reads_unchanged(
    api: ContractClient, project: Costed
) -> None:
    # « à sa création, chacun de ses nœuds est celui de la structure principale » (NodeDifference):
    # the same tree, the same figures, the same totals, every node unchanged and nothing changing.
    structure_id = opened_amendment(api, project)
    main = project.tree.read().json()
    read = on(project.tree, structure_id).read()
    assert read.status_code == 200, read.text
    differential = read.json()
    assert len(differential["items"]) == len(main["items"]) == 4
    assert {each["difference"] for each in differential["items"]} == {"unchanged"}
    assert {tuple(each["changes"]) for each in differential["items"]} == {()}
    assert differential["totals"] == main["totals"]
    assert differential["meta"] == main["meta"]
    assert [each["lineage_id"] for each in differential["items"]] == [
        each["lineage_id"] for each in main["items"]
    ]
    assert [each["task"]["label"] for each in differential["items"] if each["task"]] == [
        each["task"]["label"] for each in main["items"] if each["task"]
    ]
    # The main structure is read relative to nothing: no mark.
    assert {each.get("difference") for each in main["items"]} == {None}


@pytest.mark.requirement("WF-REV-0100-A")
def test_two_differentials_each_have_their_own_counter_and_their_label_is_not_unique(
    api: ContractClient, project: Costed
) -> None:
    first = opened_amendment(api, project, "Avenant")
    second = opened_amendment(api, project, "Avenant")
    assert first != second
    amendments = [each for each in listed(api, project) if each["kind"] == "amendment"]
    assert sorted(each["structure_id"] for each in amendments) == sorted([first, second])
    assert {(each["label"], each["lock_version"]) for each in amendments} == {("Avenant", 1)}


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_main_structure_is_not_opened_and_the_own_estimate_of_a_risk_is_born_with_its_risk(
    api: ContractClient, project: Costed
) -> None:
    before = structures_counted(project)
    for kind in ("main", "risk"):
        answer = open_amendment(api, project, kind=kind)
        assert answer.status_code == 422, answer.text
        assert [each["pointer"] for each in answer.json()["fields"]] == ["/kind"]
    blank = open_amendment(api, project, " ")
    assert blank.status_code == 422, blank.text
    assert structures_counted(project) == before


# --- The refusals ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_opening_is_refused_on_a_marked_revision_and_creates_nothing(
    api: ContractClient, project: Costed
) -> None:
    mark(project.stage, project.tree.revision)
    before = structures_counted(project)
    answer = open_amendment(api, project)
    assert answer.status_code == 409, answer.text
    assert answer.json()["code"] == "STATE_FORBIDS_OPERATION"
    assert answer.json()["params"] == {"missing_condition": "revision_draft"}
    assert structures_counted(project) == before
    commands = revision_commands(api, project)
    assert commands["create_structure"] == (False, ["revision_draft"])


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_opening_is_refused_while_a_background_task_runs_and_the_command_says_it_in_advance(
    api: ContractClient, project: Costed
) -> None:
    assert revision_commands(api, project)["create_structure"] == (True, [])
    started_marking(api, project)
    before = structures_counted(project)
    answer = open_amendment(api, project)
    assert answer.status_code == 409, answer.text
    assert answer.json()["params"] == {"missing_condition": "no_background_task_running"}
    assert structures_counted(project) == before
    commands = revision_commands(api, project)
    assert commands["create_structure"] == (False, ["no_background_task_running"])


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_command_to_open_a_differential_follows_the_permission_to_manage_the_revisions(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    commands = list(revision_commands(api, project))
    after = commands.index("declare_risk") + 1
    assert commands[after] == "create_structure"
    # A reader of the project who may not write its revisions is shown no such command, and the
    # opening is refused as an entry of a contributor is.
    assert "create_structure" not in revision_commands(api, project, stage.reader)
    answer = api.post(
        structures_path(project),
        headers=stage.reader.headers,
        json={"kind": "amendment", "label": "Avenant"},
    )
    assert answer.status_code in (403, 404), answer.text


# --- listCostStructures ---------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_list_gives_the_main_structure_the_differentials_and_the_own_estimates_of_the_risks(
    api: ContractClient, project: Costed
) -> None:
    # Every nature of the revision read, each with its nature, whether it is merged and its
    # commands (#1369); the own estimate of a risk with its risk.
    risk = declared(project)
    first = opened_amendment(api, project, "Avenant 1")
    second = opened_amendment(api, project, "Avenant 2")
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.id == UUID(first)).values(is_merged=True)
        )
    structures = listed(api, project)
    assert [each["kind"] for each in structures] == ["main", "amendment", "amendment", "risk"]
    by_id = {each["structure_id"]: each for each in structures}
    assert by_id[project.tree.structure_id]["kind"] == "main"
    assert by_id[first]["is_merged"] is True
    assert by_id[second]["is_merged"] is False
    own = by_id[str(risk.structure_id)]
    assert own["kind"] == "risk"
    assert own["risk_id"] == str(risk.risk_id)
    assert all("risk_id" not in each for each in structures if each["kind"] != "risk")
    for each in structures:
        assert set(commands_of(each)) >= {"edit_planning", "edit_estimate"}
    # The remaining to commit is the main structure's alone.
    assert "edit_remaining" in commands_of(by_id[project.tree.structure_id])
    assert all(
        "edit_remaining" not in commands_of(each) for each in structures if each["kind"] != "main"
    )


@pytest.mark.requirement("WF-DEV-0050-A")
def test_on_an_in_progress_project_the_main_estimate_is_closed_and_a_differentials_is_open(
    api: ContractClient, project: Costed
) -> None:
    # « Sur un projet En cours, la grille de devis de la structure principale ne propose aucune
    # saisie ; celle d'une structure différentielle les propose. »
    structure_id = opened_amendment(api, project)
    put_in_state(project.stage.owner, str(project.project_id), "in_progress")
    by_id = {each["structure_id"]: each for each in listed(api, project)}
    main = commands_of(by_id[project.tree.structure_id])
    differential = commands_of(by_id[structure_id])
    assert main["edit_estimate"] == (False, ["project_before_in_progress"])
    assert differential["edit_estimate"] == (True, [])
    assert differential["edit_planning"] == (True, [])


# --- #2541: the skeleton -------------------------------------------------------------------------


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_a_revision_whose_only_a_differential_bears_a_task_lists_the_skeleton_available(
    api: ContractClient, stage: Scene
) -> None:
    # « main_structure_without_tasks » judges the main structure alone (#2541): the differential,
    # opened on a main structure without a task, bears the only one.
    revision = opened(api, stage)
    base = f"{PROJECTS}/{stage.project['project_id']}/revisions/{revision['revision_id']}"
    answer = api.get(base, headers=stage.manager.headers)
    assert commands_of(answer.json())["generate_skeleton"] == (True, [])
    tree = Tree(api, stage, revision)
    created = api.post(
        f"{base}/structures",
        headers=stage.manager.headers,
        json={"kind": "amendment", "label": "Avenant"},
    )
    assert created.status_code == 201, created.text
    pointed = on(tree, created.json()["structure_id"])
    assert pointed.create("Essais").status_code == 201
    answer = api.get(base, headers=stage.manager.headers)
    assert commands_of(answer.json())["generate_skeleton"] == (True, [])
    tree.made("Études")
    answer = api.get(base, headers=stage.manager.headers)
    assert commands_of(answer.json())["generate_skeleton"] == (
        False,
        ["main_structure_without_tasks"],
    )


@pytest.mark.requirement("WF-PRJ-0030-A")
def test_a_project_without_a_current_revision_judges_the_skeleton_on_the_main_structure_alone(
    api: ContractClient, stage: Scene
) -> None:
    # The revision its opening would create is a copy of the last marked one, which only a
    # differential bears a task in: the skeleton is listed available on the project (#2541).
    revision = opened(api, stage)
    tree = Tree(api, stage, revision)
    base = f"{PROJECTS}/{stage.project['project_id']}"
    created = api.post(
        f"{base}/revisions/{revision['revision_id']}/structures",
        headers=stage.manager.headers,
        json={"kind": "amendment", "label": "Avenant"},
    )
    assert on(tree, created.json()["structure_id"]).create("Essais").status_code == 201
    mark(stage, revision)
    held = commands_of(api.get(base, headers=stage.manager.headers).json())
    assert held["generate_skeleton"] == (True, [])
