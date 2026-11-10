# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writes of the tree the three grids make alike, under the permission of any of them (#2601).

``createNode``, ``deleteNode``, ``moveNodes``, ``previewPaste`` and ``applyPaste`` of a task or of
a line of estimate ask for one at least of ``planning.write``, ``estimate.write`` and
``remaining.write``, as ``StructureCommand`` says of the three grids: a contributor who may write
the estimate alone structures the tree from the estimate grid (WF-DEV-0050), one who may write
none of them is refused, ``planning.write`` named. The columns of a task's own stay the planning's
whatever the path that writes them (#2775), and an undoing or a redoing asks for the permission of
the write it turns (#2774). Every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import role
from estimate_support import Costing, Lines, costing
from history_support import redo, redone, undo, undone
from nodes_support import SESSION, Tree, opened, refusal
from projects_support import Person, contribute
from projects_support import scene as make_scene
from realm import KEY
from sqlalchemy import delete as delete_rows
from sqlalchemy import insert, select
from support import bearer, raw_account

from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.users.tables import UserAccount

if TYPE_CHECKING:
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

ENTRIES = ("planning.write", "estimate.write", "remaining.write")
READS = ("planning.read", "estimate.read", "remaining.read")


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def contributor(stage: Scene, realm: TestRealm, *permissions: str) -> Person:
    """Write a contributor of the project who holds ``permissions`` and the three readings.

    Its token carries a session of sign-in, which a paste keeps its plan by.
    """
    account = raw_account(email=f"{uuid4().hex}@example.org", first_name="Inès")
    held = role(stage.database, f"Rôle {uuid4().hex}", permissions=(*READS, *permissions))
    with stage.database.transaction() as session:
        session.execute(insert(UserAccount).values(**account))
        session.execute(
            insert(UserAccessRole).values(user_account_id=account["id"], access_role_id=held)
        )
    token = realm.token(str(account["idp_subject"]), KEY, claims={"sid": SESSION})
    who = Person(bearer(token), UUID(str(account["id"])))
    contribute(stage.database, stage.project["project_id"], who, "contributor")
    return who


def counter(tree: Tree) -> int:
    """Read the counter of the structure, which every write of its tree advances."""
    with tree.stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    assert found is not None
    return found


def move(tree: Tree, nodes: list[dict[str, Any]], parent: dict[str, Any], who: Person) -> Any:
    """Move nodes under a parent at the counter of the structure; give the answer."""
    sent = {
        "node_ids": [each["node_id"] for each in nodes],
        "parent_id": parent["node_id"],
        "lock_version": counter(tree),
    }
    return tree.api.post(f"{tree.path}/nodes/move", headers=who.headers, json=sent)


def delete(tree: Tree, node: dict[str, Any], who: Person) -> Any:
    """Delete a node at its counter as the tree reads it; give the answer."""
    held = tree.node(node["node_id"])["lock_version"]
    path = f"{tree.path}/nodes/{node['node_id']}?lock_version={held}"
    return tree.api.delete(path, headers=who.headers)


def preview(tree: Tree, target: dict[str, Any], rows: list[list[str]], who: Person) -> Any:
    """Preview a block pasted on the label of a node; give the answer."""
    sent = {"target_node_id": target["node_id"], "target_column": "label", "rows": rows}
    return tree.api.post(f"{tree.path}/nodes/paste-preview", headers=who.headers, json=sent)


def apply(tree: Tree, plan: dict[str, Any], who: Person) -> Any:
    """Confirm a plan at the counter of the structure; give the answer."""
    sent = {"paste_id": plan["paste_id"], "confirmed": True, "lock_version": counter(tree)}
    return tree.api.post(f"{tree.path}/nodes/paste", headers=who.headers, json=sent)


@pytest.mark.requirement("WF-DEV-0050-A")
@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.parametrize("permission", ENTRIES)
def test_a_contributor_who_may_write_one_grid_creates_moves_pastes_and_deletes_tasks_and_lines(
    stage: Scene, tree: Tree, costs: Costing, realm: TestRealm, permission: str
) -> None:
    # WF-DEV-0050 : la grille de devis « permet de créer, modifier, déplacer et supprimer des
    # lignes [...], de créer, déplacer et supprimer des tâches, d'indenter et de désindenter une
    # tâche » ; the same writes from the three grids, under the permission of each (#2601).
    who = contributor(stage, realm, permission)
    lines = Lines(tree)
    created = tree.create("Câblage", who)
    assert created.status_code == 201, created.text
    task = created.json()["nodes"][0]
    other = tree.create("Essais", who).json()["nodes"][0]
    line = lines.create(
        task, who, quantity="1", cost_category_id=str(costs.material), unit_disbursement="350"
    )
    assert line.status_code == 201, line.text
    [node] = line.json()["nodes"]
    moved = move(tree, [node], other, who)
    assert moved.status_code == 200, moved.text
    assert moved.json()["nodes"][0]["parent_id"] == other["node_id"]
    answer = preview(tree, node, [["Câbles"]], who)
    assert answer.status_code == 200, answer.text
    pasted = apply(tree, answer.json(), who)
    assert pasted.status_code == 200, pasted.text
    assert tree.node(node["node_id"])["estimate_line"]["label"] == "Câbles"
    gone = delete(tree, node, who)
    assert gone.status_code == 200, gone.text
    assert delete(tree, task, who).status_code == 200
    assert [item["node_id"] for item in tree.items()] == [other["node_id"]]


@pytest.mark.requirement("WF-ADM-0100-A")
def test_a_contributor_who_may_write_no_grid_is_refused_the_writes_of_the_tree_naming_one(
    stage: Scene, tree: Tree, costs: Costing, realm: TestRealm
) -> None:
    # A contributor who may read the three grids and write none is refused each write of the
    # tree, ``planning.write`` named, the first of the three; nothing is written.
    who = contributor(stage, realm)
    lines = Lines(tree)
    task = tree.made("Câblage")
    other = tree.made("Essais")
    node = lines.made(task, quantity="1", resource_role_id=str(costs.role), hours="10")["nodes"][0]
    before = (counter(tree), tree.items())
    missing = (403, "PERMISSION_MISSING", {"missing_permission": "planning.write"})
    assert refusal(tree.create("Étude", who)) == missing
    assert refusal(lines.create(task, who, quantity="1", resource_role_id=str(costs.role))) == (
        missing
    )
    assert refusal(move(tree, [node], other, who)) == missing
    assert refusal(preview(tree, node, [["Câbles"]], who)) == missing
    plan = preview(tree, node, [["Câbles"]], contributor(stage, realm, "estimate.write"))
    assert plan.status_code == 200, plan.text
    assert refusal(apply(tree, plan.json(), who)) == missing
    assert refusal(delete(tree, node, who)) == missing
    assert refusal(delete(tree, task, who)) == missing
    assert (counter(tree), tree.items()) == before
    # The task of a contributor who may write the estimate alone still asks for the planning to be
    # changed: its duration and its dates are the planning's (WF-PLA-0080), not one of these writes.
    estimating = contributor(stage, realm, "estimate.write")
    changed = tree.change(tree.node(task["node_id"]), estimating, label="Câblage des armoires")
    assert refusal(changed) == missing


# --- The columns of a task, the planning's whatever the grid (#2775) -----------------------------

PLANNING_MISSING = (403, "PERMISSION_MISSING", {"missing_permission": "planning.write"})


def pasted(
    tree: Tree, target: dict[str, Any], column: str, rows: list[list[str]], who: Person
) -> Any:
    """Preview a block pasted on a column of a node; give the answer."""
    sent = {"target_node_id": target["node_id"], "target_column": column, "rows": rows}
    return tree.api.post(f"{tree.path}/nodes/paste-preview", headers=who.headers, json=sent)


def labels(tree: Tree) -> list[str]:
    """Read the labels of the nodes of the structure, tasks and lines, in their order."""
    return [(item["task"] or item["estimate_line"])["label"] for item in tree.items()]


def regrant(stage: Scene, who: Person, *permissions: str) -> None:
    """Give a contributor a role of ``permissions`` and the three readings in place of its own."""
    held = role(stage.database, f"Rôle {uuid4().hex}", permissions=(*READS, *permissions))
    with stage.database.transaction() as session:
        session.execute(
            delete_rows(UserAccessRole).where(UserAccessRole.user_account_id == who.user_id)
        )
        session.execute(
            insert(UserAccessRole).values(user_account_id=who.user_id, access_role_id=held)
        )


@pytest.mark.requirement("WF-DEV-0050-A")
@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.parametrize("permission", ["estimate.write", "remaining.write"])
def test_without_planning_write_a_task_is_created_by_its_label_not_with_its_mode_or_duration(
    stage: Scene, tree: Tree, realm: TestRealm, permission: str
) -> None:
    # WF-DEV-0050 : « La création d'une tâche depuis la grille de devis la fait apparaître dans la
    # grille de planning, en mode automatique, d'une durée d'un jour » ; its mode, its duration
    # and its dates are the planning's, as ``updateTaskFacet`` writes them (#2775): a creation that
    # carries one of them asks for ``planning.write``, and nothing is written.
    who = contributor(stage, realm, permission)
    before = (counter(tree), tree.items())
    for facet in (
        {"duration": {"value": "3", "unit": "d"}},
        {"scheduling_mode": "manual"},
        {"scheduling_mode": "automatic"},
        {"description": "Câbles et armoires"},
    ):
        assert refusal(tree.create("Étude", who, task=facet)) == PLANNING_MISSING
    assert (counter(tree), tree.items()) == before
    created = tree.create("Étude", who)
    assert created.status_code == 201, created.text
    task = created.json()["nodes"][0]["task"]
    assert (task["scheduling_mode"], task["duration"]) == ("automatic", {"value": "1", "unit": "d"})


@pytest.mark.requirement("WF-ADM-0100-A")
def test_estimate_write_alone_pasting_the_columns_of_a_task_is_refused_naming_planning_write(
    stage: Scene, tree: Tree, costs: Costing, realm: TestRealm
) -> None:
    # The paste does not open what ``updateTaskFacet`` refuses (#2775): the duration, the mode or
    # the label of a task, or a task created with its duration, are refused whole by 403 to whoever
    # may write the estimate alone; nothing is kept nor written.
    who = contributor(stage, realm, "estimate.write")
    task = tree.made("Câblage")
    made = Lines(tree).made(task, quantity="1", resource_role_id=str(costs.role), hours="10")
    line = made["nodes"][0]
    last = tree.made("Essais")
    before = (counter(tree), tree.items())
    assert refusal(pasted(tree, task, "duration", [["3"]], who)) == PLANNING_MISSING
    assert refusal(pasted(tree, task, "scheduling_mode", [["manual"]], who)) == PLANNING_MISSING
    assert refusal(pasted(tree, task, "label", [["Câblage du poste"]], who)) == PLANNING_MISSING
    # A block of lines that runs onto the task after them would write its label: refused too.
    assert refusal(pasted(tree, line, "label", [["Câbles"], ["Mesures"]], who)) == (
        PLANNING_MISSING
    )
    # Past the last task, its own row empty, a block creates a task: with its duration, refused.
    creating = [[""], ["Recette", "", "", "3"]]
    assert refusal(pasted(tree, last, "label", creating, who)) == PLANNING_MISSING
    assert (counter(tree), tree.items()) == before
    # A line is still pasted, and a task still created by its label alone, as by ``createNode``.
    plan = pasted(tree, line, "label", [["Câbles"]], who)
    assert plan.status_code == 200, plan.text
    assert apply(tree, plan.json(), who).status_code == 200
    plan = pasted(tree, last, "label", [[""], ["Recette"]], who)
    assert plan.status_code == 200, plan.text
    assert plan.json()["created"] == 1
    assert apply(tree, plan.json(), who).status_code == 200
    assert labels(tree) == ["Câblage", "Câbles", "Essais", "Recette"]


@pytest.mark.requirement("WF-ADM-0100-A")
def test_a_plan_of_the_columns_of_a_task_is_not_applied_once_planning_write_is_withdrawn(
    stage: Scene, tree: Tree, realm: TestRealm
) -> None:
    # A paste is judged at its preview and again at its confirmation (#2601, #2775): a plan of the
    # duration of a task, previewed under ``planning.write``, is refused once it is withdrawn.
    who = contributor(stage, realm, "planning.write", "estimate.write")
    task = tree.made("Câblage")
    plan = pasted(tree, task, "duration", [["3"]], who)
    assert plan.status_code == 200, plan.text
    regrant(stage, who, "estimate.write")
    before = (counter(tree), tree.items())
    assert refusal(apply(tree, plan.json(), who)) == PLANNING_MISSING
    assert (counter(tree), tree.items()) == before


# --- The undoing, under the permission of the write it turns (#2774) -----------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-ADM-0100-A")
def test_a_line_created_under_estimate_write_alone_is_undone_and_redone_under_it(
    stage: Scene, tree: Tree, costs: Costing, realm: TestRealm
) -> None:
    # The history is that of the three grids: what a contributor who may write the estimate alone
    # creates, changes, moves or deletes there, he undoes and redoes (#2774), a task created by its
    # label included.
    who = contributor(stage, realm, "estimate.write")
    lines = Lines(tree)
    task = tree.made("Câblage")
    made = lines.made(task, who, quantity="1", resource_role_id=str(costs.role), hours="10")
    line = made["nodes"][0]
    assert lines.change(line, who, hours="12").status_code == 200
    created = tree.create("Essais", who)
    assert created.status_code == 201, created.text
    assert [undone(tree, who)["undone"]["kind"] for _ in range(3)] == [
        "node_create",
        "cell",
        "node_create",
    ]
    assert labels(tree) == ["Câblage"]
    assert [redone(tree, who)["undone"]["kind"] for _ in range(3)] == [
        "node_create",
        "cell",
        "node_create",
    ]
    assert tree.node(line["node_id"])["estimate_line"]["hours"] == "12"
    assert len(tree.items()) == 3
    other = tree.made("Études")
    assert move(tree, [tree.node(line["node_id"])], other, who).status_code == 200
    assert delete(tree, tree.node(line["node_id"]), who).status_code == 200
    assert [undone(tree, who)["undone"]["kind"] for _ in range(2)] == ["node_delete", "node_move"]
    assert tree.node(line["node_id"])["parent_id"] == task["node_id"]


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-ADM-0100-A")
def test_a_write_of_a_task_is_not_undone_nor_redone_without_planning_write(
    stage: Scene, tree: Tree, costs: Costing, realm: TestRealm
) -> None:
    # An undoing asks for the permission the write it undoes asked for (#2774): a task changed, or
    # created with its duration, asks for ``planning.write`` (#2775); a cell of a line for
    # ``estimate.write``. Refused 403, naming it; nothing is undone.
    who = contributor(stage, realm, "planning.write", "estimate.write")
    lines = Lines(tree)
    task = tree.made("Câblage")
    made = lines.made(task, who, quantity="1", resource_role_id=str(costs.role), hours="10")
    line = made["nodes"][0]
    created = tree.create("Essais", who, task={"duration": {"value": "3", "unit": "d"}})
    assert created.status_code == 201, created.text
    assert tree.change(tree.node(task["node_id"]), who, label="Câblage du poste").status_code == 200
    assert lines.change(tree.node(line["node_id"]), who, hours="12").status_code == 200
    regrant(stage, who, "planning.write")
    assert refusal(undo(tree, who)) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "estimate.write"},
    )
    assert tree.node(line["node_id"])["estimate_line"]["hours"] == "12"
    regrant(stage, who, "estimate.write")
    assert undone(tree, who)["undone"]["kind"] == "cell"
    assert refusal(undo(tree, who)) == PLANNING_MISSING
    assert labels(tree)[0] == "Câblage du poste"
    regrant(stage, who, "planning.write")
    assert undone(tree, who)["undone"]["kind"] == "cell"
    regrant(stage, who, "estimate.write")
    assert refusal(undo(tree, who)) == PLANNING_MISSING
    assert refusal(redo(tree, who)) == PLANNING_MISSING
    assert labels(tree)[0] == "Câblage"
    regrant(stage, who, "planning.write")
    assert undone(tree, who)["undone"]["kind"] == "node_create"
    regrant(stage, who, "remaining.write")
    assert refusal(redo(tree, who)) == PLANNING_MISSING
    assert "Essais" not in labels(tree)
