# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The paste of a block beyond the horizon of fifteen years (WF-PLA-0150-A, #2606).

The refusal names the task the engine finds beyond the horizon: a row the paste creates, a row it
writes that is not the first, or a successor linked that it pushes, none of its rows. A task of the
paste is named with its row in the block, counted from zero, so that two tasks created with one
label are told apart (#3624); a successor pushed, none of its rows, without one.
"""

from typing import TYPE_CHECKING

import paste_support
import pytest
from estimate_support import Lines, costing
from history_support import counter
from nodes_support import Tree, refusal
from paste_support import apply, planned

from waterfall.core.planning.writing import Write

if TYPE_CHECKING:
    from projects_support import Person

stage, tree, who = paste_support.stage, paste_support.tree, paste_support.who


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
        {"task": {"node_id": None, "label": "Interminable", "row": 2}},
    )
    assert tree.labels() == ["Étude"]
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
        {"task": {"node_id": second["node_id"], "label": "Seconde", "row": 1}},
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


@pytest.mark.requirement("WF-PLA-0150-A")
def test_two_tasks_created_with_one_label_are_told_apart_by_their_row_in_the_refusal(
    tree: Tree, who: Person
) -> None:
    # #3624 : « Le déplacement d'une tâche qui porterait la fin du projet à quinze ans et un jour
    # de son début est refusé, et la tâche est nommée. » Deux lignes créées portent le même
    # libellé, leur nœud nul : le refus nomme celle qui dépasse par son rang dans le bloc.
    task = tree.made("Étude", who=who)
    before = counter(tree)
    block = [["Étude"], ["Essai", "", "", "9000"], ["Essai", "", "", "2"]]
    plan = planned(tree, task, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (3, 2, [])
    answer = apply(tree, plan, who)
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": None, "label": "Essai", "row": 1}},
    )
    assert tree.labels() == ["Étude"]
    assert counter(tree) == before


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_write_that_names_one_task_and_several_is_refused_before_it_replays() -> None:
    # #3624 : `among` donné, `blamed` est nul ; les deux ensemble ne se taisent pas.
    write = object.__new__(Write)
    with pytest.raises(ValueError, match="one task or several"):
        write.redate((None, "Étude"), among={})


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_task_named_by_two_rows_of_a_paste_is_named_by_the_first_of_them(
    tree: Tree, who: Person
) -> None:
    # #3624 : « le refus nomme celle qui dépasse par son rang dans le bloc » — la première ligne du
    # bloc qui nomme la tâche, y compris une ligne de devis qu'elle porte : ici la tâche (rang 0)
    # puis sa ligne (rang 1) la nomment, et le refus garde le rang 0.
    task = tree.made("Étude", who=who)
    material = costing(tree.stage.database).material
    sent = {"quantity": "1", "cost_category_id": str(material), "unit_disbursement": "350.00"}
    Lines(tree).made(task, who, label="Câble", **sent)
    block = [["Étude", "", "", "9000"], ["Câble 5 m"]]
    plan = planned(tree, task, "label", block, who)
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (2, 0, [])
    answer = apply(tree, plan, who)
    assert refusal(answer) == (
        422,
        "PROJECT_HORIZON_EXCEEDED",
        {"task": {"node_id": task["node_id"], "label": "Étude", "row": 0}},
    )
