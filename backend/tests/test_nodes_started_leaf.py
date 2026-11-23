# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A leaf started or completed that receives a subtask keeps its state (US-3310, #3336).

``createNode``, ``moveNodes``, ``applyPaste`` and ``deleteNode`` on the main structure of a
revision a project's manager opened, every answer checked against the contract, the structure read
back by ``listNodes``: the leaf P, started on the 1st of March 2026, given a subtask not started by
each entry, is a summary started at that date, overdue as a started task is; it is not deleted;
deprived of its subtask — deleted or outdented —, it is a leaf started at that date again. A leaf
completed that receives a subtask not completed is a summary started at its date, completed again
once the subtask is. The start of a summary is the earliest of its own and of its subordinates';
a summary never started is read as before. The states are written around the service, as
``set_progress`` does (US-1410). The import of MS Project is in ``test_msproject_import.py``, the
Kanban in ``test_startable_tasks.py``.
"""

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Lines, costing
from history_support import counter
from nodes_support import Tree, opened, put_facts, refusal, set_progress
from paste_support import applied, planned
from projects_support import scene as make_scene
from risks_support import material
from sqlalchemy import func, select

from waterfall.core.planning.tables import Node

if TYPE_CHECKING:
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MARCH_FIRST = date(2026, 3, 1)
MARCH_FIFTH = date(2026, 3, 5)
MARCH_TENTH = date(2026, 3, 10)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def started_leaf(tree: Tree, label: str = "Câblage", on: date = MARCH_FIRST) -> dict[str, Any]:
    """Create a leaf and start it on the day said, around the service; give it as read."""
    leaf = tree.made(label)
    set_progress(tree.stage, leaf["node_id"], "started", on)
    return tree.node(leaf["node_id"])


def state(tree: Tree, node: dict[str, Any]) -> tuple[str, str | None, str | None]:
    """Read the state of a task and its two dates, as ``listNodes`` gives them."""
    task = tree.node(node["node_id"])["task"]
    return task["progress"], task["started_on"], task["completed_on"]


def move(tree: Tree, nodes: list[dict[str, Any]], parent: dict[str, Any] | None) -> None:
    """Move nodes under a parent at the counter of the structure read; it must be accepted."""
    sent = {
        "node_ids": [node["node_id"] for node in nodes],
        "parent_id": None if parent is None else parent["node_id"],
        "lock_version": counter(tree),
    }
    headers = tree.stage.manager.headers
    answer = tree.api.post(f"{tree.path}/nodes/move", headers=headers, json=sent)
    assert answer.status_code == 200, answer.text


def delete(tree: Tree, node: dict[str, Any]) -> Any:
    """Delete a node at the counter read, as the manager does; give the answer."""
    path = f"{tree.path}/nodes/{node['node_id']}?lock_version={node['lock_version']}"
    return tree.api.delete(path, headers=tree.stage.manager.headers)


def nodes_held(stage: Scene) -> int:
    """Count the nodes of the project, of every kind."""
    with stage.database.transaction() as session:
        found = session.scalar(
            select(func.count())
            .select_from(Node)
            .where(Node.project_id == UUID(stage.project["project_id"]))
        )
    return found or 0


STARTED_ON_MARCH_FIRST = ("started", MARCH_FIRST.isoformat(), None)


# --- A leaf started that receives a subtask ------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_leaf_started_given_a_subtask_by_a_creation_is_a_summary_started_at_its_date(
    tree: Tree,
) -> None:
    # « Une feuille démarrée qui reçoit une sous-tâche non démarrée est une récapitulative
    # démarrée, à sa date de démarrage » : par ``createNode`` sous P, la récapitulative P est
    # démarrée au 1er mars 2026, et sa fin dépassée est jugée sur elle (WF-RAE-0040).
    parent = started_leaf(tree)
    created = tree.create("Pose", parent_id=parent["node_id"])
    assert created.status_code == 201, created.text
    read = tree.node(parent["node_id"])["task"]
    assert read["is_summary"] is True
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST
    # The plan starts on the 2nd of November 2026, a day before the date of calculation: P, started,
    # finishes before it.
    assert read["finish_overdue"] is True
    assert [item["node_id"] for item in tree.items("?finish_overdue=true")] == [parent["node_id"]]


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_leaf_started_given_a_subtask_by_an_indentation_is_a_summary_started_at_its_date(
    tree: Tree,
) -> None:
    # « Une feuille démarrée qui reçoit une sous-tâche non démarrée est une récapitulative
    # démarrée, à sa date de démarrage » : par ``moveNodes`` vers P, l'indentation de la tâche qui
    # la suit.
    parent = started_leaf(tree)
    following = tree.made("Pose")
    move(tree, [following], parent)
    assert tree.node(following["node_id"])["parent_id"] == parent["node_id"]
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST


@pytest.mark.story("US-3310")
def test_a_summary_born_of_a_leaf_started_receives_a_subtask_by_a_paste_not_refused(
    tree: Tree,
) -> None:
    # La règle vaut quelle que soit l'entrée : le collage (``applyPaste``) d'une ligne après la
    # dernière sous-tâche de P en crée une sœur sous P, sans refus, et P reste démarrée à sa date.
    parent = started_leaf(tree)
    first = tree.made("Pose", parent_id=parent["node_id"])
    plan = planned(tree, first, "label", [["Pose"], ["Raccordement"]])
    assert (plan["accepted"], plan["rejected"]) == (2, [])
    assert applied(tree, plan)["rejected"] == []
    below = [item for item in tree.items() if item["parent_id"] == parent["node_id"]]
    assert [item["task"]["label"] for item in below] == ["Pose", "Raccordement"]
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST


# --- Deprived of its subtask ---------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_born_of_a_leaf_started_deprived_of_its_subtask_deleted_is_a_leaf_started_again(
    tree: Tree,
) -> None:
    # « La suppression de la seule subordonnée d'une récapitulative de dix jours laisse une tâche
    # feuille […] » et « privée de cette sous-tâche, elle redevient une feuille démarrée à cette
    # date » : P reçoit C, non démarrée, puis la perd par sa suppression ; P est une feuille
    # démarrée le 1er mars 2026, non une feuille non démarrée, et reçoit de nouveau une sous-tâche.
    parent = started_leaf(tree)
    child = tree.made("Pose", parent_id=parent["node_id"])
    assert delete(tree, child).status_code == 200
    read = tree.node(parent["node_id"])["task"]
    assert read["is_summary"] is False
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST
    tree.made("Pose", parent_id=parent["node_id"])
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_summary_born_of_a_leaf_started_deprived_of_its_subtask_outdented_is_a_leaf_started_again(
    tree: Tree,
) -> None:
    # « privée de cette sous-tâche, elle redevient une feuille démarrée à cette date » : C quitte P
    # par sa désindentation (``moveNodes`` au premier niveau).
    parent = started_leaf(tree)
    child = tree.made("Pose", parent_id=parent["node_id"])
    move(tree, [child], None)
    assert tree.node(parent["node_id"])["task"]["is_summary"] is False
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST
    assert state(tree, child) == ("not_started", None, None)


# --- Not deleted ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0070-A")
def test_a_summary_born_of_a_leaf_started_is_not_deleted_nor_its_subtask_nor_its_lines(
    tree: Tree, stage: Scene
) -> None:
    # « La suppression d'une tâche démarrée est refusée » : P, feuille démarrée qui porte une
    # ligne, reçoit une sous-tâche non démarrée ; ``deleteNode(P)`` est refusé (409,
    # ``task_not_started``), et ni P, ni sa sous-tâche, ni sa ligne ne sont supprimées.
    costs = costing(stage.database)
    parent = started_leaf(tree)
    Lines(tree).made(parent, **material(costs, "Fixations", "50"))
    tree.made("Pose", parent_id=parent["node_id"])
    held = nodes_held(stage)
    answer = delete(tree, tree.node(parent["node_id"]))
    assert refusal(answer) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "task_not_started"},
    )
    assert nodes_held(stage) == held
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST


# --- A leaf completed that receives a subtask ----------------------------------------------------


@pytest.mark.requirement("WF-PLA-0040-A")
def test_a_leaf_completed_given_a_subtask_not_completed_is_a_summary_started_at_its_date(
    tree: Tree, stage: Scene
) -> None:
    # « Une feuille terminée qui reçoit une sous-tâche non terminée est une récapitulative
    # démarrée, à sa date de démarrage. » La terminaison, périmée, est effacée (#2769) ; la date de
    # démarrage est gardée, et P redevient terminée quand sa sous-tâche l'est, sans ligne propre
    # qui garde un reste à engager.
    parent = tree.made("Câblage")
    put_facts(
        stage,
        parent["node_id"],
        progress="completed",
        started_on=MARCH_FIRST,
        completed_on=MARCH_FIFTH,
    )
    child = tree.made("Pose", parent_id=parent["node_id"])
    assert state(tree, parent) == STARTED_ON_MARCH_FIRST
    set_progress(stage, child["node_id"], "completed", MARCH_TENTH)
    assert state(tree, parent) == ("completed", MARCH_FIRST.isoformat(), MARCH_TENTH.isoformat())


# --- The start of a summary, and a summary never started -----------------------------------------


@pytest.mark.story("US-3310")
@pytest.mark.parametrize(
    ("own", "below", "first"),
    [(MARCH_FIRST, MARCH_TENTH, MARCH_FIRST), (MARCH_TENTH, MARCH_FIRST, MARCH_FIRST)],
)
def test_the_start_of_a_summary_is_the_earliest_of_its_own_and_of_its_subordinates(
    tree: Tree, stage: Scene, own: date, below: date, first: date
) -> None:
    # La date de démarrage d'une récapitulative est la plus ancienne entre celle qu'elle portait
    # comme feuille et celles de ses subordonnées.
    parent = started_leaf(tree, on=own)
    child = tree.made("Pose", parent_id=parent["node_id"])
    set_progress(stage, child["node_id"], "started", below)
    assert state(tree, parent) == ("started", first.isoformat(), None)


@pytest.mark.story("US-3310")
def test_a_summary_never_a_leaf_started_is_read_as_before(tree: Tree, stage: Scene) -> None:
    # Une récapitulative qui n'a jamais été une feuille démarrée se lit comme aujourd'hui : non
    # démarrée tant qu'aucune subordonnée ne l'est, puis démarrée à la date de la première ; privée
    # de sa seule subordonnée non démarrée, elle est une feuille non démarrée.
    parent = tree.made("Études")
    first = tree.made("Avant-projet", parent_id=parent["node_id"])
    second = tree.made("Détail", parent_id=parent["node_id"])
    assert state(tree, parent) == ("not_started", None, None)
    set_progress(stage, second["node_id"], "started", MARCH_TENTH)
    assert state(tree, parent) == ("started", MARCH_TENTH.isoformat(), None)
    other = tree.made("Revue")
    lone = tree.made("Relecture", parent_id=other["node_id"])
    assert delete(tree, tree.node(lone["node_id"])).status_code == 200
    assert state(tree, other) == ("not_started", None, None)
    assert state(tree, first) == ("not_started", None, None)
