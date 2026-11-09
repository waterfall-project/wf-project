# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The passage of a project to In progress, and its code (US-1540; WF-CYC-0030, WF-PRJ-0010).

A reference that bears tasks and lines written through the service (``nodes_support``,
``estimate_support``), designated and coded in both orders: ``advance`` of the projects moves the
project to In progress at the second fact. A participant writes a line and marks no revision
(WF-PRJ-0060). Every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, mark, opened
from projects_support import PROJECTS, Person, Scene
from projects_support import scene as make_scene

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

STATE_FORBIDS = "STATE_FORBIDS_OPERATION"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made, without a code."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def path_of(stage: Scene) -> str:
    """Give the path of the project of the stage."""
    return f"{PROJECTS}/{stage.project['project_id']}"


def project_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the project of the stage, as its manager does."""
    answer = api.get(path_of(stage), headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def next_of(api: ContractClient, stage: Scene) -> dict[str, Any]:
    """Read the next state of the project of the stage, as its manager does."""
    answer = api.get(f"{path_of(stage)}/next-state", headers=stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def designate(api: ContractClient, stage: Scene, revision: dict[str, Any]) -> Any:
    """Designate a marked revision the reference, as the manager does, confirmed."""
    sent = {
        "revision_id": revision["revision_id"],
        "confirmed": True,
        "lock_version": project_of(api, stage)["lock_version"],
    }
    return api.put(f"{path_of(stage)}/reference-revision", headers=stage.manager.headers, json=sent)


def enter_code(api: ContractClient, stage: Scene, code: str) -> Any:
    """Enter the code of the project of the stage, as its manager does."""
    sent = {"code": code, "lock_version": project_of(api, stage)["lock_version"]}
    return api.patch(path_of(stage), headers=stage.manager.headers, json=sent)


def estimated(tree: Tree, lines: Lines, costs: Costing, who: Person | None = None) -> None:
    """Write a task and, under it, a labour line of the role of the scene."""
    task = tree.made("Mise en service")
    line = {"quantity": "1", "resource_role_id": str(costs.role), "hours": "10"}
    lines.made(task, who, **line)


def refusal(answer: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = answer.json()
    return answer.status_code, body["code"], body.get("params", {})


@pytest.mark.requirement("WF-CYC-0020-A")
@pytest.mark.requirement("WF-CYC-0030-A")
def test_a_reference_with_tasks_and_lines_designated_then_the_code_moves_the_project_in_progress(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Chacun de ces états est atteint dès que son fait déclencheur est réalisé, sans autre
    # action. » ; « Un projet dont la référence est désignée avant le code projet passe à En cours
    # à la saisie du code. » The reference bears a task and a line the estimate wrote.
    estimated(tree, lines, costs)
    mark(stage, tree.revision)
    designated = designate(api, stage, tree.revision)
    assert (designated.status_code, designated.json()["state"]) == (200, "pricing")
    coded = enter_code(api, stage, "PRJ-1540")
    assert (coded.status_code, coded.json()["state"]) == (200, "in_progress"), coded.text
    assert project_of(api, stage)["state"] == "in_progress"
    assert next_of(api, stage)["next_state"] is None


@pytest.mark.requirement("WF-CYC-0020-A")
@pytest.mark.requirement("WF-CYC-0030-A")
def test_the_code_then_a_reference_with_tasks_and_lines_move_the_project_in_progress(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Un projet dont le code est saisi avant la désignation y passe à la désignation. »
    estimated(tree, lines, costs)
    mark(stage, tree.revision)
    coded = enter_code(api, stage, "PRJ-1541")
    assert (coded.status_code, coded.json()["state"]) == (200, "pricing"), coded.text
    designated = designate(api, stage, tree.revision)
    assert (designated.status_code, designated.json()["state"]) == (200, "in_progress")


@pytest.mark.requirement("WF-CYC-0030-A")
def test_a_marked_revision_with_tasks_and_no_line_is_not_designated_naming_the_lines(
    api: ContractClient, stage: Scene, tree: Tree
) -> None:
    # « La désignation d'une révision marquée sans tâche, ou sans ligne de devis, est refusée et la
    # condition manquante est nommée ; le projet n'a pas de référence. »
    tree.made("Mise en service")
    mark(stage, tree.revision)
    answer = designate(api, stage, tree.revision)
    assert refusal(answer) == (
        409,
        STATE_FORBIDS,
        {"missing_condition": "revision_has_tasks_and_lines"},
    )
    assert project_of(api, stage)["reference_revision_id"] is None
    assert enter_code(api, stage, "PRJ-1542").json()["state"] == "pricing"
    # The lines condition stays named: the marked revision bears none.
    assert next_of(api, stage)["missing_conditions"] == [
        "revision_has_tasks_and_lines",
        "reference_revision_designated",
    ]


@pytest.mark.requirement("WF-CYC-0050-A")
def test_the_next_state_names_the_lines_condition_until_a_marked_revision_bears_a_line(
    api: ContractClient, stage: Scene, costs: Costing
) -> None:
    # « Pour un projet dans chacun des états Créé et Chiffrage, l'utilisateur consulte le prochain
    # état, son déclencheur et les conditions restantes » : `revision_has_tasks_and_lines` tant
    # qu'aucune révision marquée ne porte de ligne.
    lines_condition = "revision_has_tasks_and_lines"
    assert next_of(api, stage)["current_state"] == "created"
    assert next_of(api, stage)["missing_conditions"] == [lines_condition]
    tree = Tree(api, stage, opened(api, stage))
    assert next_of(api, stage)["current_state"] == "pricing"
    assert next_of(api, stage)["missing_conditions"] == [
        "project_code_set",
        lines_condition,
        "reference_revision_designated",
    ]
    # A line of the current revision, not marked, changes nothing.
    estimated(tree, Lines(tree), costs)
    assert lines_condition in next_of(api, stage)["missing_conditions"]
    mark(stage, tree.revision)
    assert next_of(api, stage)["missing_conditions"] == [
        "project_code_set",
        "reference_revision_designated",
    ]


@pytest.mark.requirement("WF-PRJ-0010-A")
@pytest.mark.requirement("WF-CYC-0050-A")
def test_lines_are_written_without_a_code_and_the_reference_without_one_stays_in_pricing(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Un projet se crée et se chiffre sans code projet. » ; « Le projet ne passe pas à En cours
    # tant qu'il n'est pas renseigné, et la condition manquante est nommée. »
    assert project_of(api, stage)["code"] is None
    estimated(tree, lines, costs)
    mark(stage, tree.revision)
    designated = designate(api, stage, tree.revision)
    assert (designated.status_code, designated.json()["state"]) == (200, "pricing")
    assert next_of(api, stage) == {
        "current_state": "pricing",
        "next_state": "in_progress",
        "trigger": "reference_designated_and_code_set",
        "missing_conditions": ["project_code_set"],
    }


@pytest.mark.requirement("WF-PRJ-0060-A")
def test_a_participant_writes_a_line_and_marks_no_revision_where_a_project_manager_does(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # « Inscrit comme participant, il l'ouvre et saisit le devis, mais ne marque pas de révision
    # même s'il en porte la permission ; inscrit comme chef de projet, il la marque. »
    estimated(tree, lines, costs, stage.participant)
    path = f"{path_of(stage)}/revisions/{tree.revision['revision_id']}/mark"
    sent = {"version_name": "v1.0", "lock_version": tree.revision["lock_version"]}
    refused = api.post(path, headers=stage.participant.headers, json=sent)
    assert refusal(refused) == (
        403,
        "NOT_PROJECT_MANAGER",
        {"missing_condition": "is_project_manager"},
    )
    accepted = api.post(path, headers=stage.manager.headers, json=sent)
    assert accepted.status_code == 202, accepted.text
