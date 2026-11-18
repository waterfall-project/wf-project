# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The grids of the planning and of the estimate on a differential (US-2550/L3).

A differential is read and written by the operations of the main structure (``listNodes``,
``createNode``, ``updateTaskFacet``, ``updateEstimateLine``, ``setPredecessors``, ``moveNodes``,
``deleteNode``, ``previewPaste``, ``applyPaste``, ``undoLastChange``), each write an entry of the
history that can be undone (WF-IHM-0110): read as a diff with the main structure, which it leaves
as it was; the lines of a task completed are entered in it as the others (F-01, #1767), and so are
those of a project In progress, where the main structure is closed (WF-DEV-0050). Every answer is
checked against the contract (``ContractClient``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import commands_of, listed, on, opened_amendment
from estimate_support import Costing, Lines, costing
from history_support import delete, link, undone
from nodes_support import Tree, set_progress, signed_in
from paste_support import apply, counter, planned
from projects_support import PROJECTS, Person, Scene, put_in_state
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed, material

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

DAY = date(2026, 3, 2)


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


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def node_of(tree: Tree, label: str) -> dict[str, Any]:
    """Read a node of a structure by its label, a task's or a line's."""
    found = [
        each for each in tree.items() if (each["task"] or each["estimate_line"])["label"] == label
    ]
    assert len(found) == 1, label
    return found[0]


def marks(tree: Tree, query: str = "") -> dict[str, str | None]:
    """Read the mark of each node a structure returns, by its label."""
    return {
        (each["task"] or each["estimate_line"])["label"]: each.get("difference")
        for each in tree.items(query)
    }


def snapshot(tree: Tree) -> tuple[Any, int]:
    """Read a structure whole, and its counter: what a write elsewhere must leave as it was."""
    return tree.read().json(), counter(tree)


def total(tree: Tree) -> Decimal:
    """Read the re-estimated amount the totals of a structure give."""
    return Decimal(tree.read().json()["totals"]["reestimated_amount"])


# --- Reading a differential ----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_differential_is_read_as_a_diff_with_the_main_structure(
    api: ContractClient, project: Costed
) -> None:
    # Added, modified, removed, unchanged: matched by lineage; the node removed stays at its place,
    # read-only, and the totals do not count it; a summary is modified by its content.
    tree = on(project.tree, opened_amendment(api, project))
    lines = Lines(tree)
    tree.made("Essais")
    study = node_of(tree, STUDY)
    tree.changed(node_of(tree, MAKING), label="Réalisation et mise au point")
    answer = delete(tree, node_of(tree, "Fabrication"), project.stage.manager)
    assert answer.status_code == 200, answer.text
    lines.made(node_of(tree, "Essais"), **material(project.costs, "Banc d'essai", "50.00"))
    assert marks(tree) == {
        STUDY: "unchanged",
        "Plans": "unchanged",
        "Réalisation et mise au point": "modified",
        "Fabrication": "removed",
        "Essais": "added",
        "Banc d'essai": "added",
    }
    removed = node_of(tree, "Fabrication")
    assert removed["editable_fields"] == []
    assert removed["estimate_line"]["reestimated_amount"] == "400.00"
    assert node_of(tree, STUDY)["lineage_id"] == study["lineage_id"]
    # The line removed counts in no total: 600 and 50 remain.
    assert total(tree) == Decimal("650.00")
    assert tree.read().json()["totals"]["estimate_line_count"] == 2
    # The rows are numbered with the node removed in its place.
    assert [each["row_number"] for each in tree.items()] == [1, 2, 3, 4, 5, 6]


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_difference_filter_keeps_the_marks_it_names_and_their_ancestors(
    api: ContractClient, project: Costed
) -> None:
    tree = on(project.tree, opened_amendment(api, project))
    tree.made("Essais")
    delete(tree, node_of(tree, "Fabrication"), project.stage.manager)
    assert set(marks(tree, "?difference=added")) == {"Essais"}
    assert set(marks(tree, "?difference=removed")) == {MAKING, "Fabrication"}
    assert set(marks(tree, "?difference=added,removed")) == {MAKING, "Fabrication", "Essais"}
    assert marks(tree, "?difference=modified") == {MAKING: "modified"}
    # The main structure is read relative to nothing: the filter has no effect there.
    assert len(project.tree.items("?difference=added")) == 4
    refused = tree.read("?difference=unchanged")
    assert refused.status_code == 422, refused.text


# --- Writing in a differential -------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0100-A")
def test_every_write_of_the_grids_succeeds_in_a_differential_and_leaves_the_main_structure_alone(
    api: ContractClient, project: Costed
) -> None:
    stage = project.stage
    others = opened_amendment(api, project, "Autre avenant")
    main_before = snapshot(project.tree)
    other_before = snapshot(on(project.tree, others))
    tree = on(project.tree, opened_amendment(api, project))
    lines = Lines(tree)
    counted = counter(tree)
    # createNode, a task and a line under it.
    tests = tree.made("Essais")
    line = lines.made(tests, **material(project.costs, "Banc d'essai", "50.00"))["nodes"][0]
    assert counter(tree) == counted + 2
    # updateTaskFacet, updateEstimateLine.
    renamed = tree.changed(tests, label="Essais de recette")["nodes"][0]
    assert renamed["task"]["label"] == "Essais de recette"
    priced = lines.changed(line, quantity="3")["nodes"][0]
    assert priced["estimate_line"]["reestimated_amount"] == "150.00"
    # setPredecessors: the tests follow the study.
    study = node_of(tree, STUDY)
    answer = link(tree, node_of(tree, "Essais de recette"), stage.manager, study)
    assert answer.status_code == 200, answer.text
    # moveNodes: the line goes under the other task.
    sent = {
        "node_ids": [priced["node_id"]],
        "parent_id": node_of(tree, MAKING)["node_id"],
        "lock_version": counter(tree),
    }
    moved = api.post(f"{tree.path}/nodes/move", headers=stage.manager.headers, json=sent)
    assert moved.status_code == 200, moved.text
    assert node_of(tree, "Banc d'essai")["parent_id"] == node_of(tree, MAKING)["node_id"]
    # previewPaste, applyPaste: a label pasted.
    plan = planned(tree, node_of(tree, MAKING), "label", [["Réalisation du banc"]])
    pasted = apply(tree, plan)
    assert pasted.status_code == 200, pasted.text
    assert node_of(tree, "Réalisation du banc")["difference"] == "modified"
    # deleteNode.
    gone = delete(tree, node_of(tree, "Banc d'essai"), stage.manager)
    assert gone.status_code == 200, gone.text
    # The main structure and the other differential are as they were, their counters too.
    assert snapshot(project.tree) == main_before
    assert snapshot(on(project.tree, others)) == other_before
    structures = {each["structure_id"]: each for each in listed(api, project)}
    assert structures[others]["lock_version"] == 1
    assert structures[project.tree.structure_id]["lock_version"] == main_before[1]


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_write_in_a_differential_changes_neither_the_other_nor_the_main_structure(
    api: ContractClient, project: Costed
) -> None:
    first = on(project.tree, opened_amendment(api, project, "Avenant"))
    second = on(project.tree, opened_amendment(api, project, "Avenant"))
    main_before = snapshot(project.tree)
    Lines(first).changed(node_of(first, "Plans"), quantity="2")
    assert total(first) == Decimal("1600.00")
    # The other differential and the main structure read as before; only the counter of the first
    # moved, and every node of the second is still unchanged.
    assert total(second) == Decimal("1000.00")
    assert {each["difference"] for each in second.items()} == {"unchanged"}
    assert snapshot(project.tree) == main_before
    assert counter(first) == 2
    assert counter(second) == 1
    assert {each["difference"] for each in first.items()} == {"unchanged", "modified"}
    assert marks(first)["Plans"] == "modified"
    assert marks(first)[STUDY] == "modified"


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_write_in_a_differential_enters_the_history_that_can_be_undone(
    api: ContractClient, project: Costed, who: Person
) -> None:
    tree = on(project.tree, opened_amendment(api, project))
    main_before = snapshot(project.tree)
    task = node_of(tree, STUDY)
    written = tree.changed(task, who=who, label="Études détaillées")["nodes"][0]
    assert marks(tree)["Études détaillées"] == "modified"
    answer = undone(tree, who)
    assert answer["undone"]["kind"] == "cell"
    assert marks(tree) == dict.fromkeys(marks(tree), "unchanged")
    assert node_of(tree, STUDY)["lineage_id"] == written["lineage_id"]
    assert snapshot(project.tree) == main_before


# --- F-01: the lines of a task completed, and a project In progress ------------------------------


@pytest.mark.requirement("WF-DEV-0050-A")
def test_the_line_of_a_completed_task_is_entered_in_a_differential_and_refused_in_the_main_one(
    api: ContractClient, project: Costed
) -> None:
    # « Dans un différentiel, la modification de la quantité d'une ligne d'une tâche terminée
    # aboutit » (F-01, #1767): the refusal is the main structure's alone (``task_not_completed``).
    stage = project.stage
    set_progress(stage, str(project.tasks[STUDY]), "completed", DAY)
    amendment = on(project.tree, opened_amendment(api, project))
    plans = node_of(amendment, "Plans")
    changed = Lines(amendment).changed(plans, quantity="2")["nodes"][0]
    assert changed["estimate_line"]["quantity"] == "2"
    assert changed["estimate_line"]["reestimated_amount"] == "1200.00"
    main = node_of(project.tree, "Plans")
    refused = project.lines.change(main, quantity="2")
    assert refused.status_code == 409, refused.text
    assert refused.json()["params"] == {"missing_condition": "task_not_completed"}
    # A line is created under the task completed, and deleted, in the differential alone.
    made = Lines(amendment).made(
        node_of(amendment, STUDY), **material(project.costs, "Revue", "10")
    )
    assert made["nodes"][0]["estimate_line"]["reestimated_amount"] == "10.00"
    created = project.lines.create(
        str(project.tasks[STUDY]), **material(project.costs, "Revue", "10")
    )
    assert created.status_code == 409, created.text
    assert created.json()["params"] == {"missing_condition": "task_not_completed"}
    gone = delete(amendment, node_of(amendment, "Revue"), stage.manager)
    assert gone.status_code == 200, gone.text
    refused = delete(project.tree, main, stage.manager)
    assert refused.status_code == 409, refused.text
    assert node_of(project.tree, "Plans")["estimate_line"]["quantity"] == "1"


@pytest.mark.requirement("WF-DEV-0050-A")
def test_on_an_in_progress_project_the_estimate_of_a_differential_is_entered_and_its_writes_succeed(
    api: ContractClient, project: Costed
) -> None:
    # « Sur un projet En cours, la grille de devis de la structure principale ne propose aucune
    # saisie ; celle d'une structure différentielle les propose »: the command is unavailable on
    # the main structure, available on the differential, whose writes succeed.
    structure_id = opened_amendment(api, project)
    put_in_state(project.stage.owner, str(project.project_id), "in_progress")
    structures = {each["structure_id"]: each for each in listed(api, project)}
    main = commands_of(structures[project.tree.structure_id])
    assert main["edit_estimate"] == (False, ["project_before_in_progress"])
    assert commands_of(structures[structure_id])["edit_estimate"] == (True, [])
    assert "edit_remaining" not in commands_of(structures[structure_id])
    tree = on(project.tree, structure_id)
    lines = Lines(tree)
    changed = lines.changed(node_of(tree, "Fabrication"), quantity="2")["nodes"][0]
    assert changed["estimate_line"]["reestimated_amount"] == "800.00"
    made = lines.made(node_of(tree, MAKING), **material(project.costs, "Outillage", "25.00"))
    assert made["nodes"][0]["estimate_line"]["reestimated_amount"] == "25.00"
    assert marks(tree)["Outillage"] == "added"
    assert total(tree) == Decimal("1425.00")
    assert total(project.tree) == Decimal("1000.00")


def test_the_path_of_a_structure_of_another_revision_is_not_found(
    api: ContractClient, project: Costed
) -> None:
    structure_id = opened_amendment(api, project)
    path = (
        f"{PROJECTS}/{project.project_id}/revisions/{UUID(int=1)}/structures/{structure_id}/nodes"
    )
    answer = api.get(path, headers=project.stage.manager.headers)
    assert answer.status_code == 404, answer.text
