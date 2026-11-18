# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The rows of a differential, the nodes it removes counted in its place (US-2550/L3).

A node a differential removes is read in its place, read-only: ``row_number`` counts the tree
returned, the removed nodes included (WF-REV-0080, C-361). Every operation that names a row takes
that numbering, not the tree the differential holds alone: ``resolveRowNumber``, the numbers of the
nodes a write gives back, the number of a predecessor, and the anchor of a paste (``previewPaste``;
#1278, #1361). Every answer is checked against the contract (``ContractClient``).
"""

from typing import TYPE_CHECKING, Any

import pytest
from amendments_support import on, opened_amendment
from estimate_support import Costing, Lines, costing
from history_support import counter, delete, link
from paste_support import apply, planned, preview
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import MAKING, STUDY, Costed, costed, material

if TYPE_CHECKING:
    from nodes_support import Tree
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

# The rows of the differential once "Fabrication", the line of the making, is deleted from it:
# the node is read in its place, at the row 4.
REMOVED_ROW = 4


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


def node_of(tree: Tree, label: str) -> dict[str, Any]:
    """Read a node of a structure by its label, a task's or a line's."""
    found = [
        each for each in tree.items() if (each["task"] or each["estimate_line"])["label"] == label
    ]
    assert len(found) == 1, label
    return found[0]


def removing(api: ContractClient, project: Costed) -> Tree:
    """Open a differential, delete a line of the main structure in it, add a task and its line.

    Read, it numbers: the study 1, its line 2, the making 3, the line removed 4, the task added 5
    and its line 6; the tree it holds numbers the last two 4 and 5.
    """
    tree = on(project.tree, opened_amendment(api, project))
    tests = tree.made("Essais")
    Lines(tree).made(tests, **material(project.costs, "Banc d'essai", "50.00"))
    gone = delete(tree, node_of(tree, "Fabrication"), project.stage.manager)
    assert gone.status_code == 200, gone.text
    assert [each["row_number"] for each in tree.items()] == [1, 2, 3, 4, 5, 6]
    assert node_of(tree, "Fabrication")["difference"] == "removed"
    return tree


def row(tree: Tree, number: int) -> Any:
    """Ask for the node of a row of a structure."""
    return tree.api.get(f"{tree.path}/rows/{number}", headers=tree.stage.manager.headers)


# --- resolveRowNumber ----------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0080-A")
@pytest.mark.parametrize("number", [5, 6])
def test_the_row_of_a_differential_resolves_to_the_node_the_list_numbers_so(
    api: ContractClient, project: Costed, number: int
) -> None:
    # A removed node occupies its row (4): the rows after it are those of the tree returned, not
    # those of the tree the differential holds, one fewer.
    tree = removing(api, project)
    read = tree.items()[number - 1]
    answer = row(tree, number)
    assert answer.status_code == 200, answer.text
    found = answer.json()
    assert (found["node_id"], found["row_number"], found["kind"]) == (
        read["node_id"],
        number,
        read["kind"],
    )
    assert found["label"] == (read["task"] or read["estimate_line"])["label"]


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_row_of_a_removed_node_resolves_to_it_and_one_past_the_last_is_not_found(
    api: ContractClient, project: Costed
) -> None:
    tree = removing(api, project)
    removed = node_of(tree, "Fabrication")
    found = row(tree, REMOVED_ROW)
    assert found.status_code == 200, found.text
    assert (found.json()["node_id"], found.json()["row_number"]) == (
        removed["node_id"],
        REMOVED_ROW,
    )
    assert row(tree, 7).status_code == 404


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_rows_of_the_main_structure_are_resolved_as_they_were(
    api: ContractClient, project: Costed
) -> None:
    removing(api, project)
    for number, each in enumerate(project.tree.items(), start=1):
        found = row(project.tree, number)
        assert found.status_code == 200, found.text
        assert found.json()["node_id"] == each["node_id"]
    assert row(project.tree, 5).status_code == 404


# --- The numbers of a write ----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_row_number_a_write_gives_back_is_the_one_the_read_that_follows_gives(
    api: ContractClient, project: Costed
) -> None:
    tree = removing(api, project)
    # createNode, updateTaskFacet: the node created follows the six rows, the one changed is the
    # task added, behind the removed row.
    created = tree.made("Recette")
    tests = node_of(tree, "Essais")
    changed = tree.changed(tests, label="Essais de recette")["nodes"][0]
    for written in (created, changed):
        read = tree.node(written["node_id"])
        assert (written["row_number"], written["level"], written["position"]) == (
            read["row_number"],
            read["level"],
            read["position"],
        )
    assert changed["row_number"] == 5
    assert created["row_number"] == 7


@pytest.mark.requirement("WF-PLA-0080-A")
def test_the_row_number_of_a_predecessor_counts_the_removed_nodes_in_a_write_and_in_the_read(
    api: ContractClient, project: Costed
) -> None:
    # The task added is the row 5 of the tree returned: the predecessor the task created names is
    # numbered so by the answer that enters it, and by the reading that follows.
    tree = removing(api, project)
    later = tree.made("Recette")
    answer = link(tree, later, project.stage.manager, node_of(tree, "Essais"))
    assert answer.status_code == 200, answer.text
    [written] = answer.json()["nodes"]
    [given] = written["predecessors"]
    assert given["predecessor_row_number"] == 5
    [read] = tree.node(later["node_id"])["predecessors"]
    assert read["predecessor_row_number"] == 5
    assert written["row_number"] == tree.node(later["node_id"])["row_number"] == 7


# --- previewPaste, applyPaste --------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_paste_aimed_at_a_removed_node_is_refused_whole_at_the_row_0_and_writes_nothing(
    api: ContractClient, project: Costed
) -> None:
    # « un collage ancré sur un nœud retiré est refusé en entier » (#1361): no row accepted, a
    # single refusal on the targeted column, row 0; confirmed, the plan writes nothing, the counter
    # does not move, and the refusal is stated again.
    tree = removing(api, project)
    removed = node_of(tree, "Fabrication")
    plan = planned(tree, removed, "label", [["Un"], ["Deux"]])
    refusal = {"row": 0, "column": "label", "code": "PASTE_TARGET_REMOVED"}
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (0, 0, [refusal])
    before = (counter(tree), tree.read().json())
    pasted = apply(tree, plan)
    assert pasted.status_code == 200, pasted.text
    assert pasted.json()["nodes"] == []
    assert pasted.json()["rejected"] == [refusal]
    assert (counter(tree), tree.read().json()) == before


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_paste_aimed_at_the_row_before_a_removed_one_writes_the_node_that_follows_the_removed(
    api: ContractClient, project: Costed
) -> None:
    # « un bloc de deux lignes collé sur la ligne qui précède une ligne retirée écrit cette ligne,
    # puis le nœud qui suit la ligne retirée » (#1278): the making, then the task added.
    tree = removing(api, project)
    making, tests = node_of(tree, MAKING), node_of(tree, "Essais")
    plan = planned(tree, making, "label", [["Réalisation 2"], ["Essais 2"]])
    assert (plan["accepted"], plan["created"], plan["rejected"]) == (2, 0, [])
    pasted = apply(tree, plan)
    assert pasted.status_code == 200, pasted.text
    assert {each["node_id"] for each in pasted.json()["nodes"]} == {
        making["node_id"],
        tests["node_id"],
    }
    assert pasted.json()["rejected"] == []
    assert tree.node(making["node_id"])["task"]["label"] == "Réalisation 2"
    assert tree.node(tests["node_id"])["task"]["label"] == "Essais 2"
    # The node removed is left as it was, and so is the study before them.
    assert node_of(tree, "Fabrication")["difference"] == "removed"
    assert node_of(tree, STUDY)["difference"] == "unchanged"


@pytest.mark.requirement("WF-IHM-0050-A")
def test_a_paste_aimed_at_a_node_that_is_not_removed_is_judged_as_before_on_a_differential(
    api: ContractClient, project: Costed
) -> None:
    tree = removing(api, project)
    answer = preview(tree, node_of(tree, "Essais"), "label", [["Essais 2"]])
    assert answer.status_code == 200, answer.text
    assert (answer.json()["accepted"], answer.json()["rejected"]) == (1, [])
