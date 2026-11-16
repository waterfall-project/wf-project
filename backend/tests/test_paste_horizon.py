# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The paste of a block beyond the horizon of fifteen years (WF-PLA-0150-A, #2606).

The refusal names the task the engine finds beyond the horizon: a row the paste creates, a row it
writes that is not the first, or a successor linked that it pushes, none of its rows.
"""

from typing import TYPE_CHECKING

import pytest
from history_support import counter
from nodes_support import Tree, opened, refusal, signed_in
from projects_support import scene as make_scene
from test_paste import apply, labels_of, planned

if TYPE_CHECKING:
    from projects_support import Person, Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_paste_that_creates_a_task_beyond_the_horizon_names_the_row_that_creates_it(
    tree: Tree, who: Person
) -> None:
    # #2606 : « Le déplacement d'une tâche qui porterait la fin du projet à quinze ans et un jour
    # de son début est refusé, et la tâche est nommée. » Le collage nomme la ligne créée qui porte
    # la tâche hors horizon (son nœud nul, son libellé), non la première ligne du plan.
    task = tree.made("Étude", who=who)
    before = counter(tree)
    block = [["Étude"], ["Courte", "", "", "2"], ["Interminable", "", "", "9000"], ["Finale"]]
    plan = planned(tree, task, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (4, 3, [])
    answer = apply(tree, plan, who)
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": None, "label": "Interminable"}},
    )
    assert labels_of(tree) == ["Étude"]
    assert counter(tree) == before


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_paste_beyond_the_horizon_names_the_existing_row_that_carries_it_not_the_first(
    tree: Tree, who: Person
) -> None:
    # #2606 : la tâche hors horizon est une ligne existante, qui n'est pas la première du bloc.
    first = tree.made("Première", who=who)
    second = tree.made("Seconde", who=who)
    plan = planned(tree, first, "duration", [["2"], ["9000"]], who)
    assert (plan["accepted"], plan["created"]) == (2, 0)
    answer = apply(tree, plan, who)
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": second["node_id"], "label": "Seconde"}},
    )
    assert tree.node(second["node_id"])["lock_version"] == 1


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_paste_that_pushes_a_linked_successor_beyond_the_horizon_names_that_successor(
    tree: Tree, who: Person
) -> None:
    # #2606 : « le déplacement [...] est refusé, et la tâche est nommée. » La tâche hors horizon est
    # un successeur lié, hors du bloc collé : le refus la nomme, non la première ligne du collage.
    first = tree.made("Amont", who=who, task={"duration": {"value": "2", "unit": "d"}})
    after = tree.made("Aval", who=who, task={"duration": {"value": "3000", "unit": "d"}})
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": first["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "0", "unit": "d"},
            }
        ],
        "lock_version": tree.node(after["node_id"])["lock_version"],
    }
    path = f"{tree.path}/nodes/{after['node_id']}/predecessors"
    assert tree.api.put(path, headers=who.headers, json=sent).status_code == 200
    before = counter(tree)
    plan = planned(tree, first, "duration", [["2500"]], who)
    assert (plan["accepted"], plan["created"]) == (1, 0)
    answer = apply(tree, plan, who)
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": after["node_id"], "label": "Aval"}},
    )
    assert counter(tree) == before
