# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the update of a differential share (EP-08, US-3050/L4).

A differential out of date (``amendments_support.out_of_date``) is updated through the service:
the report is read, and its two counters confirmed (``rebased``). The state of what the update may
write — the nodes of the differential as ``listNodes`` reads them, the base around the service —
is read before and after.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

from amendments_support import listed, node_labelled, revision_path
from sqlalchemy import select
from sqlalchemy.orm import aliased

from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from amendments_support import OutOfDate
    from nodes_support import Tree
    from risks_support import Costed
    from support import ContractClient


def rebase_path(project: Costed, structure_id: object) -> str:
    """Give the path of the update of a structure of the current revision."""
    return f"{revision_path(project)}/structures/{structure_id}/rebase"


def confirmation(found: dict[str, Any]) -> dict[str, Any]:
    """Give the confirmation of a report: it is confirmed, its two counters sent back."""
    return {
        "confirmed": True,
        "main_structure_lock_version": found["main_structure_lock_version"],
        "structure_lock_version": found["structure_lock_version"],
    }


def read_report(api: ContractClient, late: OutOfDate) -> dict[str, Any]:
    """Read the report of the update of a differential, which must be given."""
    project = late.project
    answer = api.get(rebase_path(project, late.structure_id), headers=project.stage.manager.headers)
    assert answer.status_code == 200, answer.text
    return answer.json()


def rebased(api: ContractClient, late: OutOfDate, who: Any = None, **changed: Any) -> Any:
    """Read the report of a differential and confirm it, as the manager does by default.

    ``changed`` replaces what the confirmation sends; give the answer.
    """
    project = late.project
    sent = {**confirmation(read_report(api, late)), **changed}
    headers = (who or project.stage.manager).headers
    return api.post(rebase_path(project, late.structure_id), headers=headers, json=sent)


def state_of(api: ContractClient, project: Costed, structure_id: str) -> dict[str, Any]:
    """Read a structure as the list of its revision gives it."""
    return next(each for each in listed(api, project) if each["structure_id"] == structure_id)


def marks(tree: Tree) -> dict[str, str]:
    """Read the mark of each node a differential returns, by its label."""
    return {
        (each["task"] or each["estimate_line"])["label"]: each["difference"]
        for each in tree.items()
    }


def outline(tree: Tree) -> list[tuple[int, str, str]]:
    """Read a differential as an outline: each node's level, label and mark, in order."""
    return [
        (each["level"], (each["task"] or each["estimate_line"])["label"], each["difference"])
        for each in tree.items()
    ]


def designations(tree: Tree) -> dict[str, tuple[str, list[Any]]]:
    """Read what a differential designates: the mark and the changes of each node not unchanged.

    By lineage, which an update keeps, whatever the label it changes.
    """
    return {
        each["lineage_id"]: (each["difference"], each["changes"])
        for each in tree.items()
        if each["difference"] != "unchanged"
    }


def nodes_of(tree: Tree, *, held: bool = False) -> dict[str, str]:
    """Read the node of each node a differential returns, by its lineage.

    A node it removes is returned from its base, under the base's identifier: ``held`` leaves
    those out, keeping the nodes the differential holds.
    """
    return {
        each["lineage_id"]: each["node_id"]
        for each in tree.items()
        if not held or each["difference"] != "removed"
    }


def base_of(project: Costed, structure_id: str) -> CostStructure:
    """Read the base of a differential, around the service."""
    with project.stage.database.transaction() as session:
        found = session.scalars(
            select(CostStructure).where(CostStructure.differential_id == UUID(structure_id))
        ).one()
        session.expunge(found)
        return found


def lineages(project: Costed, structure_id: UUID) -> list[tuple[UUID, str]]:
    """Read the nodes of a structure by their lineage and their kind, in that order."""
    with project.stage.database.transaction() as session:
        rows = session.execute(
            select(Node.lineage_id, Node.kind).where(Node.structure_id == structure_id)
        )
        return sorted((lineage, kind) for lineage, kind in rows)


def attachments(project: Costed, structure_id: str) -> list[tuple[Any, Any]]:
    """Read the work package and the order item of each task of a structure, around the service."""
    with project.stage.database.transaction() as session:
        rows = session.execute(
            select(Task.work_package_id, Task.order_item_id).where(
                Task.structure_id == UUID(structure_id)
            )
        )
        return [(package, item) for package, item in rows]


def lagged(
    tree: Tree, successor: str, lags: dict[str, str], link_type: str = "finish_to_start"
) -> None:
    """Give a task of a structure its predecessors, of a type, each with its lag in days."""
    node = node_labelled(tree, successor)
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": node_labelled(tree, label)["node_id"],
                "link_type": link_type,
                "lag": {"value": lag, "unit": "d"},
            }
            for label, lag in lags.items()
        ],
        "lock_version": node["lock_version"],
    }
    path = f"{tree.path}/nodes/{node['node_id']}/predecessors"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text


def links_of(project: Costed, structure_id: str) -> dict[tuple[UUID, UUID], str]:
    """Read the links of a structure by the lineages of their two tasks, around the service."""
    predecessor, successor = aliased(Node), aliased(Node)
    with project.stage.database.transaction() as session:
        rows = session.execute(
            select(predecessor.lineage_id, successor.lineage_id, TaskLink.link_type)
            .join(predecessor, predecessor.id == TaskLink.predecessor_id)
            .join(successor, successor.id == TaskLink.successor_id)
            .where(TaskLink.structure_id == UUID(structure_id))
        )
        return {(before, after): kind for before, after, kind in rows}


def moved_under(tree: Tree, label: str, parent: str) -> None:
    """Move the node of a structure that bears a label under the task that bears another."""
    path = tree.path.rsplit("/", 1)[0]
    structures = tree.api.get(path, headers=tree.stage.manager.headers).json()
    held = next(each for each in structures if each["structure_id"] == tree.structure_id)
    sent = {
        "node_ids": [node_labelled(tree, label)["node_id"]],
        "parent_id": node_labelled(tree, parent)["node_id"],
        "lock_version": held["lock_version"],
    }
    headers = tree.stage.manager.headers
    answer = tree.api.post(f"{tree.path}/nodes/move", headers=headers, json=sent)
    assert answer.status_code == 200, answer.text
