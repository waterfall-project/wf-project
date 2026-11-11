# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The tasks attached to the work breakdown, its elements removed (US-1380/L3, WF-PLA-0170).

``createNode`` and ``updateTaskFacet`` attach a task to a work package or an order item of its
project, under the rules of ``TaskFacetUpdate``: one element at most, borne by one task of the
structure, the task of an order item under that of its work package, which ``moveNodes`` keeps
too. ``setWorkBreakdown`` withdraws an element it removes from the tasks of the current revision,
marks it deleted when a marked revision cites it, deletes it otherwise; the copy of a revision
leaves the attachment to an element marked deleted null. Every answer is checked against the
contract.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file.
"""

from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
from nodes_support import Tree, faults, mark, opened, work_breakdown
from projects_support import PROJECTS
from projects_support import scene as make_scene
from sqlalchemy import select, update

from waterfall.core.planning.attachments import Bearer, judged_attachment
from waterfall.core.planning.tree import Tree as Read
from waterfall.core.projects.tables import OrderItem, WorkPackage
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database

pytestmark = pytest.mark.requirement("WF-PLA-0170-A")


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


@pytest.fixture
def elements(stage: Scene) -> tuple[str, str]:
    """Give the work package « Lot » and its order item « Poste », written around the service."""
    package, item = work_breakdown(stage)
    return str(package), str(item)


def attachment(node: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Give what a task bears: its work package, its order item, and the label resolved."""
    task = node["task"]
    return task["work_package_id"], task["order_item_id"], task["work_breakdown_label"]


def without_item(api: ContractClient, stage: Scene, item: str) -> None:
    """Write the work breakdown of the project back without an order item, as its manager does."""
    path = f"{PROJECTS}/{stage.project['project_id']}/work-breakdown"
    read = api.get(path, headers=stage.manager.headers).json()
    nothing: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = [
        {
            "work_package_id": package["work_package_id"],
            "label": package["label"],
            "order_items": [
                {
                    "order_item_id": each["order_item_id"],
                    "label": each["label"],
                    "deliverables": nothing,
                }
                for each in package["order_items"]
                if each["order_item_id"] != item
            ],
        }
        for package in read["work_packages"]
    ]
    body: dict[str, Any] = {"work_packages": packages, "lock_version": read["lock_version"]}
    answer = api.put(path, headers=stage.manager.headers, json=body)
    assert answer.status_code == 200, answer.text


def item_row(stage: Scene, item: str) -> OrderItem | None:
    """Read the row of an order item, marked deleted or not; none once deleted for good."""
    with stage.database.transaction() as session:
        found = session.scalars(select(OrderItem).where(OrderItem.id == UUID(item))).first()
        session.expunge_all()
        return found


# --- Attached ----------------------------------------------------------------------------------


def test_a_leaf_is_attached_to_an_order_item_and_a_summary_keeps_its_own_without_subordinate(
    tree: Tree, elements: tuple[str, str]
) -> None:
    # « Une feuille peut être rattachée à un poste ; une récapitulative rattachée dont on supprime
    # la dernière subordonnée garde son rattachement. »
    package, item = elements
    summary = tree.made("Chantier", task={"work_package_id": package})
    assert attachment(summary) == (package, None, "Lot")
    only = tree.made("Montage", parent_id=summary["node_id"])
    gone = tree.api.delete(
        f"{tree.path}/nodes/{only['node_id']}?lock_version=1", headers=tree.stage.manager.headers
    )
    assert gone.status_code == 200, gone.text
    left = gone.json()["ancestors"][0]
    assert left["task"]["is_summary"] is False
    assert attachment(left) == (package, None, "Lot")
    leaf = tree.made("Câblage", parent_id=summary["node_id"])
    written = tree.changed(leaf, order_item_id=item)["nodes"][0]
    assert attachment(written) == (None, item, "Poste")
    assert attachment(tree.node(leaf["node_id"])) == (None, item, "Poste")
    # ``null`` removes the attachment; the swap is one write.
    removed = tree.changed(tree.node(leaf["node_id"]), order_item_id=None)["nodes"][0]
    assert attachment(removed) == (None, None, None)
    swapped = tree.changed(tree.node(summary["node_id"]), work_package_id=None, order_item_id=item)
    assert attachment(swapped["nodes"][0]) == (None, item, "Poste")


def test_an_element_borne_by_another_task_or_with_another_element_is_refused(
    tree: Tree, elements: tuple[str, str]
) -> None:
    # « Le rattachement d'une tâche à un poste déjà porté par une autre est refusé, comme celui
    # d'une même tâche à un lot et à un poste. »
    package, item = elements
    bearer = tree.made("Poste de commande", task={"work_package_id": package})
    other = tree.made("Câblage", parent_id=bearer["node_id"])
    taken = {
        "conflicting_object_id": bearer["node_id"],
        "conflicting_object_label": "Poste de commande",
    }
    assert faults(tree.change(other, work_package_id=package)) == [
        ("/work_package_id", "WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED", taken)
    ]
    assert faults(tree.change(other, work_package_id=package, order_item_id=item)) == [
        ("/work_package_id", "WORK_BREAKDOWN_ITEMS_EXCLUSIVE", {}),
        ("/work_package_id", "WORK_BREAKDOWN_ITEM_ALREADY_ATTACHED", taken),
        ("/order_item_id", "WORK_BREAKDOWN_ITEMS_EXCLUSIVE", {}),
    ]
    # The work package borne, an order item sent without it set to null.
    assert faults(tree.change(tree.node(bearer["node_id"]), order_item_id=item)) == [
        ("/order_item_id", "WORK_BREAKDOWN_ITEMS_EXCLUSIVE", {})
    ]
    created = tree.create("Études", task={"work_package_id": package, "order_item_id": item})
    assert [pointer for pointer, _, _ in faults(created)] == [
        "/task/work_package_id",
        "/task/work_package_id",
        "/task/order_item_id",
    ]
    assert attachment(tree.node(other["node_id"])) == (None, None, None)
    assert len(tree.items()) == 2


def test_an_element_unknown_of_another_nature_or_marked_deleted_is_refused(
    tree: Tree, stage: Scene, elements: tuple[str, str]
) -> None:
    package, item = elements
    task = tree.made("Câblage")
    # An order item the project does not have, a work package sent as an order item.
    for sent in (str(uuid4()), package):
        assert faults(tree.change(task, order_item_id=sent)) == [
            ("/order_item_id", "UNKNOWN_WORK_BREAKDOWN_ITEM", {})
        ]
    mark_deleted(stage, item)
    assert faults(tree.change(task, order_item_id=item)) == [
        ("/order_item_id", "UNKNOWN_WORK_BREAKDOWN_ITEM", {})
    ]


def mark_deleted(stage: Scene, item: str) -> None:
    """Mark an order item deleted around the service, as ``setWorkBreakdown`` does."""
    with stage.owner.begin() as connection:
        connection.execute(
            update(OrderItem)
            .where(OrderItem.id == UUID(item))
            .values(deleted_at=OrderItem.created_at)
        )


def test_an_attachment_outside_the_main_structure_is_refused() -> None:
    # « Le rattachement n'existe que dans la structure principale » : no other structure exists
    # before EP-08, the rule is judged on what the write holds; ``null`` there changes nothing.
    bearer = Bearer(uuid4(), "Câblage", ())
    held = (uuid4(), Read({}, {}), False)
    session = cast("Session", None)
    refused = judged_attachment(session, held, bearer, {"order_item_id": uuid4()}, "")
    assert [(each.pointer, each.code) for each in refused.faults] == [
        ("/order_item_id", "WORK_BREAKDOWN_MAIN_STRUCTURE_ONLY")
    ]
    cleared = judged_attachment(session, held, bearer, {"order_item_id": None}, "")
    assert (cleared.order_item_id, cleared.faults) == (None, ())


# --- The task of an order item under that of its work package ----------------------------------


def test_the_task_of_an_order_item_out_of_that_of_its_work_package_is_refused(
    tree: Tree, elements: tuple[str, str]
) -> None:
    # « Le déplacement de la tâche d'un poste hors du sous-arbre de la tâche de son lot est
    # refusé. »
    package, item = elements
    summary = tree.made("Poste de commande", task={"work_package_id": package})
    inside = tree.made("Câblage", parent_id=summary["node_id"], task={"order_item_id": item})
    outside = tree.made("Installation sur site")
    named = {
        "work_package_task": {"node_id": summary["node_id"], "label": "Poste de commande"},
        "order_item_tasks": [{"node_id": inside["node_id"], "label": "Câblage"}],
    }
    with tree.stage.database.transaction() as session:
        counter = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    sent = {
        "node_ids": [inside["node_id"]],
        "parent_id": outside["node_id"],
        "lock_version": counter,
    }
    answer = tree.api.post(f"{tree.path}/nodes/move", headers=tree.stage.manager.headers, json=sent)
    assert faults(answer) == [("/node_ids/0", "ORDER_ITEM_OUTSIDE_WORK_PACKAGE", named)]
    assert tree.node(inside["node_id"])["parent_id"] == summary["node_id"]
    # The attachment that would take it out: the order item elsewhere, the package elsewhere.
    tree.changed(tree.node(inside["node_id"]), order_item_id=None)
    moved_out = {
        **named,
        "order_item_tasks": [{"node_id": outside["node_id"], "label": "Installation sur site"}],
    }
    assert faults(tree.change(outside, order_item_id=item)) == [
        ("/order_item_id", "ORDER_ITEM_OUTSIDE_WORK_PACKAGE", moved_out)
    ]
    tree.changed(tree.node(inside["node_id"]), order_item_id=item)
    taken = tree.change(tree.node(summary["node_id"]), work_package_id=None)
    assert taken.status_code == 200, taken.text
    elsewhere = tree.change(outside, work_package_id=package)
    assert faults(elsewhere) == [
        (
            "/work_package_id",
            "ORDER_ITEM_OUTSIDE_WORK_PACKAGE",
            {
                "work_package_task": {
                    "node_id": outside["node_id"],
                    "label": "Installation sur site",
                },
                "order_item_tasks": [{"node_id": inside["node_id"], "label": "Câblage"}],
            },
        )
    ]
    # A task created under the task of its work package is attached; elsewhere, refused.
    tree.changed(tree.node(summary["node_id"]), work_package_id=package)
    tree.changed(tree.node(inside["node_id"]), order_item_id=None)
    created = tree.create("Pupitres", task={"order_item_id": item})
    assert faults(created) == [
        (
            "/task/order_item_id",
            "ORDER_ITEM_OUTSIDE_WORK_PACKAGE",
            {
                "work_package_task": {"node_id": summary["node_id"], "label": "Poste de commande"},
                "order_item_tasks": [{"node_id": None, "label": "Pupitres"}],
            },
        )
    ]
    under = tree.made("Pupitres", parent_id=summary["node_id"], task={"order_item_id": item})
    assert attachment(under) == (None, item, "Poste")


# --- The elements removed ----------------------------------------------------------------------


def test_an_order_item_removed_leaves_the_current_task_and_stays_on_the_marked_one(
    api: ContractClient, tree: Tree, stage: Scene, elements: tuple[str, str]
) -> None:
    # « La suppression d'un poste porté par une tâche de la révision en cours aboutit ; la tâche
    # reste et ne porte plus de rattachement ; une révision marquée qui la citait l'affiche
    # toujours rattachée. »
    _, item = elements
    task = tree.made("Câblage", task={"order_item_id": item})
    mark(stage, tree.revision)
    current = Tree(api, stage, opened(api, stage))
    copied = current.items()[0]
    assert attachment(copied) == (None, item, "Poste")
    without_item(api, stage, item)
    assert attachment(current.items()[0]) == (None, None, None)
    assert attachment(tree.node(task["node_id"])) == (None, item, "Poste")
    row = item_row(stage, item)
    assert row is not None
    assert row.deleted_at is not None
    listed = api.get(
        f"{PROJECTS}/{stage.project['project_id']}/work-breakdown", headers=stage.manager.headers
    ).json()
    assert item not in [
        each["order_item_id"] for p in listed["work_packages"] for each in p["order_items"]
    ]


def test_an_order_item_no_marked_revision_cites_is_deleted_for_good_from_its_task(
    api: ContractClient, tree: Tree, stage: Scene, elements: tuple[str, str]
) -> None:
    _, item = elements
    task = tree.made("Câblage", task={"order_item_id": item})
    without_item(api, stage, item)
    assert attachment(tree.node(task["node_id"])) == (None, None, None)
    assert item_row(stage, item) is None


def test_a_revision_opened_after_an_order_item_removed_does_not_take_its_attachment_up(
    api: ContractClient, tree: Tree, stage: Scene, elements: tuple[str, str]
) -> None:
    # « Après suppression d'un poste sur un projet sans révision en cours, la révision créée
    # ensuite ne porte plus ce rattachement ; la révision marquée l'affiche toujours. »
    package, item = elements
    summary = tree.made("Chantier", task={"work_package_id": package})
    task = tree.made("Câblage", parent_id=summary["node_id"], task={"order_item_id": item})
    mark(stage, tree.revision)
    without_item(api, stage, item)
    following = Tree(api, stage, opened(api, stage))
    assert [attachment(each) for each in following.items()] == [
        (package, None, "Lot"),
        (None, None, None),
    ]
    assert attachment(tree.node(task["node_id"])) == (None, item, "Poste")


# --- The work packages removed, a selection moved ----------------------------------------------


def without_package(api: ContractClient, stage: Scene, package: str) -> None:
    """Write the work breakdown of the project back without a work package, and its order items."""
    path = f"{PROJECTS}/{stage.project['project_id']}/work-breakdown"
    read = api.get(path, headers=stage.manager.headers).json()
    kept: list[dict[str, Any]] = [
        {
            "work_package_id": each["work_package_id"],
            "label": each["label"],
            "order_items": [
                {
                    "order_item_id": held["order_item_id"],
                    "label": held["label"],
                    "deliverables": [],
                }
                for held in each["order_items"]
            ],
        }
        for each in read["work_packages"]
        if each["work_package_id"] != package
    ]
    body: dict[str, Any] = {"work_packages": kept, "lock_version": read["lock_version"]}
    answer = api.put(path, headers=stage.manager.headers, json=body)
    assert answer.status_code == 200, answer.text


def package_row(stage: Scene, package: str) -> WorkPackage | None:
    """Read the row of a work package, marked deleted or not; none once deleted for good."""
    with stage.database.transaction() as session:
        found = session.scalars(select(WorkPackage).where(WorkPackage.id == UUID(package))).first()
        session.expunge_all()
        return found


def move_sent(tree: Tree, node_ids: list[str], parent: str) -> Any:
    """Move nodes under a parent at the counter of the structure; give the answer."""
    with tree.stage.database.transaction() as session:
        counter = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    sent = {"node_ids": node_ids, "parent_id": parent, "lock_version": counter}
    return tree.api.post(f"{tree.path}/nodes/move", headers=tree.stage.manager.headers, json=sent)


def test_a_work_package_removed_leaves_the_current_task_and_stays_on_the_marked_one(
    api: ContractClient, tree: Tree, stage: Scene, elements: tuple[str, str]
) -> None:
    # « La suppression d'un lot [...] retire le rattachement des tâches de la révision en cours
    # qui le portaient ; les révisions marquées le conservent, et le lot est alors marqué
    # supprimé. »
    package, _ = elements
    task = tree.made("Chantier", task={"work_package_id": package})
    mark(stage, tree.revision)
    current = Tree(api, stage, opened(api, stage))
    assert attachment(current.items()[0]) == (package, None, "Lot")
    without_package(api, stage, package)
    assert attachment(current.items()[0]) == (None, None, None)
    assert attachment(tree.node(task["node_id"])) == (package, None, "Lot")
    row = package_row(stage, package)
    assert row is not None
    assert row.deleted_at is not None


def test_a_work_package_no_marked_revision_cites_is_deleted_for_good_from_its_task(
    api: ContractClient, tree: Tree, stage: Scene, elements: tuple[str, str]
) -> None:
    package, _ = elements
    task = tree.made("Chantier", task={"work_package_id": package})
    without_package(api, stage, package)
    assert attachment(tree.node(task["node_id"])) == (None, None, None)
    assert package_row(stage, package) is None


def test_a_work_package_over_an_order_item_a_marked_revision_cites_is_marked_deleted(
    api: ContractClient, tree: Tree, stage: Scene, elements: tuple[str, str]
) -> None:
    # The package is cited by no revision, but the order item marked deleted still under it keeps
    # its key: the package is marked, not deleted.
    package, item = elements
    tree.made("Câblage", task={"order_item_id": item})
    mark(stage, tree.revision)
    without_package(api, stage, package)
    row = package_row(stage, package)
    assert row is not None
    assert row.deleted_at is not None


def test_a_refusal_of_a_selection_names_the_first_node_concerned_at_its_place_sent(
    tree: Tree, elements: tuple[str, str]
) -> None:
    # « Le déplacement de la tâche d'un poste hors du sous-arbre de la tâche de son lot est
    # refusé. » The pointer is the index among the nodes sent, not the first.
    package, item = elements
    summary = tree.made("Poste de commande", task={"work_package_id": package})
    inside = tree.made("Câblage", parent_id=summary["node_id"], task={"order_item_id": item})
    free = tree.made("Libre")
    outside = tree.made("Installation sur site")
    answer = move_sent(tree, [free["node_id"], inside["node_id"]], outside["node_id"])
    assert [(pointer, code) for pointer, code, _ in faults(answer)] == [
        ("/node_ids/1", "ORDER_ITEM_OUTSIDE_WORK_PACKAGE")
    ]


def test_a_selection_that_holds_a_node_and_its_descendant_keeps_the_item_under_its_package(
    tree: Tree, elements: tuple[str, str]
) -> None:
    # The task of the package and the task of its order item sent together under another task: the
    # descendant is left to its ancestor, the group moved whole (#2507), and the task of the item
    # stays in the subtree of the task of its package.
    package, item = elements
    summary = tree.made("Poste de commande", task={"work_package_id": package})
    inside = tree.made("Câblage", parent_id=summary["node_id"], task={"order_item_id": item})
    outside = tree.made("Installation sur site")
    answer = move_sent(tree, [summary["node_id"], inside["node_id"]], outside["node_id"])
    assert answer.status_code == 200, answer.text
    assert tree.node(summary["node_id"])["parent_id"] == outside["node_id"]
    assert tree.node(inside["node_id"])["parent_id"] == summary["node_id"]
