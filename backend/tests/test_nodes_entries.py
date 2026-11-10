# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writes of the tree the three grids make alike, under the permission of any of them (#2601).

``createNode``, ``deleteNode``, ``moveNodes``, ``previewPaste`` and ``applyPaste`` of a task or of
a line of estimate ask for one at least of ``planning.write``, ``estimate.write`` and
``remaining.write``, as ``StructureCommand`` says of the three grids: a contributor who may write
the estimate alone structures the tree from the estimate grid (WF-DEV-0050), one who may write
none of them is refused, ``planning.write`` named. Every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from access_rows import role
from estimate_support import Costing, Lines, costing
from nodes_support import SESSION, Tree, opened, refusal
from projects_support import Person, contribute
from projects_support import scene as make_scene
from realm import KEY
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
