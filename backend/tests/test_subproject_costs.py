# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A subproject and its actual costs: the deletion, the list, the line retained.

Laid by US-1580/L1, the socle of EP-09, so that no two stories create the same file;
US-1610/L3 writes its tests here ("Les tests du back"): the question of the actual costs that
``register_cost_facts`` gives the projects answered by the lines loaded — the deletion of a
subproject refused (``subproject_without_actual_costs``), ``has_actual_costs`` of
``listSubprojects``, its filter and its sort —, and the line of a started task that cannot leave the
subproject its costs are imputed to (``SUBPROJECT_HAS_ACTUAL_COSTS``, EP-07: ``updateEstimateLine``,
``editable_fields`` of the line read and moved by ``moveNodes``). They prepare WF-PRJ-0050-A, which
US-1620 closes. Every answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import cost, load_import
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, faults, opened, refusal, set_progress
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import func, select, update

from waterfall.core.costs.tables import CostLine
from waterfall.core.projects.tables import Subproject
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

SUBPROJECT_FIELD = "estimate_line.subproject_id"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def path(stage: Scene, *more: str) -> str:
    """Give the path of the subprojects of the project of the stage, or of one of them."""
    return "/".join([f"{PROJECTS}/{stage.project['project_id']}/subprojects", *more])


def made(api: ContractClient, stage: Scene, code: str, label: str | None = None) -> dict[str, Any]:
    """Create a subproject of the project of the stage, as its manager does; give the answer."""
    sent = {"code": code, "label": label or code}
    answer = api.post(path(stage), headers=stage.manager.headers, json=sent)
    assert answer.status_code == 201, answer.text
    return answer.json()


def charge(stage: Scene, *codes: str | None) -> None:
    """Load an import of a line of cost for each code, on the project of the stage."""
    lines = [cost(f"FA-{index}", code) for index, code in enumerate(codes)]
    project = UUID(stage.project["project_id"])
    load_import(stage, project, lines)


def stored(stage: Scene) -> int:
    """Count the subprojects the base holds."""
    with stage.database.transaction() as session:
        return session.scalar(select(func.count()).select_from(Subproject)) or 0


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_the_deletion_of_a_subproject_that_bears_actual_costs_is_refused_even_excluded(
    api: ContractClient, stage: Scene
) -> None:
    # « La suppression d'un sous-projet portant des coûts réels est refusée. » A line of cost
    # imputed, tracked or excluded, retains it; the list says so beforehand.
    charged = made(api, stage, "SP-CAB")
    charge(stage, "SP-CAB")
    with stage.owner.begin() as connection:
        connection.execute(update(CostLine).values(is_in_tracked_scope=False))

    listed = api.get(path(stage), headers=stage.manager.headers).json()
    assert listed[0]["has_actual_costs"] is True
    assert listed[0]["available_commands"][1] == {
        "command": "delete",
        "is_available": False,
        "missing_conditions": ["subproject_without_actual_costs"],
    }
    refused = api.delete(
        path(stage, charged["subproject_id"]),
        headers=stage.manager.headers,
        params={"lock_version": 0},
    )
    assert refusal(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "subproject_without_actual_costs"},
    )
    assert stored(stage) == 1


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_subproject_whose_code_lines_wait_for_elsewhere_is_deleted(
    api: ContractClient, stage: Scene
) -> None:
    # A line of another code retains nothing: the subproject without a line is deleted.
    free = made(api, stage, "SP-LIB")
    charge(stage, "SP-AUTRE", None)
    answer = api.delete(
        path(stage, free["subproject_id"]),
        headers=stage.manager.headers,
        params={"lock_version": 0},
    )
    assert answer.status_code == 204, answer.text
    assert stored(stage) == 0


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_the_list_says_filters_and_sorts_the_subprojects_by_their_actual_costs(
    api: ContractClient, stage: Scene
) -> None:
    for code in ("SP-A", "SP-B", "SP-C", "SP-D"):
        made(api, stage, code)
    charge(stage, "SP-B", "SP-D", "SP-D")

    def listed(**query: object) -> list[tuple[str, bool]]:
        answer = api.get(path(stage), headers=stage.reader.headers, params=query)
        assert answer.status_code == 200, answer.text
        return [(item["code"], item["has_actual_costs"]) for item in answer.json()]

    assert listed() == [("SP-A", False), ("SP-B", True), ("SP-C", False), ("SP-D", True)]
    assert listed(has_actual_costs="true") == [("SP-B", True), ("SP-D", True)]
    assert listed(has_actual_costs="false", search="sp-c") == [("SP-C", False)]
    # Those without first ascending, the code ordering the ties in either direction.
    assert listed(sort_by="has_actual_costs") == [
        ("SP-A", False),
        ("SP-C", False),
        ("SP-B", True),
        ("SP-D", True),
    ]
    assert listed(sort_by="has_actual_costs", sort_order="desc") == [
        ("SP-B", True),
        ("SP-D", True),
        ("SP-A", False),
        ("SP-C", False),
    ]


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines of the scene name, rated for the year."""
    return costing(stage.database)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def material(costs: Costing, subproject: dict[str, Any]) -> dict[str, Any]:
    """Give a line of material of a subproject: one at 350.00."""
    return {
        "quantity": "1",
        "cost_category_id": str(costs.material),
        "unit_disbursement": "350.00",
        "subproject_id": subproject["subproject_id"],
    }


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_line_of_a_started_task_cannot_leave_a_subproject_that_received_actual_costs(
    api: ContractClient, stage: Scene, tree: Tree, costs: Costing
) -> None:
    # « Le passage à un autre sous-projet d'une ligne d'une tâche démarrée, dont le sous-projet a
    # reçu des coûts réels, est refusé et nomme ce sous-projet ; celui d'une ligne d'une tâche non
    # démarrée aboutit » : the rule of EP-07 lacks for the first time.
    lines = Lines(tree)
    cabling, elsewhere = made(api, stage, "SP-CAB", "Câblage"), made(api, stage, "SP-AUT")
    started, waiting = tree.made("Câblage"), tree.made("Essais")
    held = lines.made(started, **material(costs, cabling))["nodes"][0]
    free = lines.made(waiting, **material(costs, cabling))["nodes"][0]
    set_progress(stage, started["node_id"], "started", tree.created_at.date())
    assert SUBPROJECT_FIELD in tree.node(held["node_id"])["editable_fields"]
    charge(stage, "SP-CAB")

    # The reading says it beforehand: the subproject is no field of the line of the started task.
    assert SUBPROJECT_FIELD not in tree.node(held["node_id"])["editable_fields"]
    assert SUBPROJECT_FIELD in tree.node(free["node_id"])["editable_fields"]
    refused = lines.change(held, subproject_id=elsewhere["subproject_id"])
    assert refused.status_code == 422, refused.text
    assert faults(refused) == [
        (
            "/subproject_id",
            "SUBPROJECT_HAS_ACTUAL_COSTS",
            {"subproject": {"subproject_id": cabling["subproject_id"], "label": "Câblage"}},
        )
    ]
    assert lines.change(held, subproject_id=None).status_code == 422
    # The other fields of the line are written; that of the task not started leaves the subproject.
    assert lines.change(held, quantity="2").status_code == 200
    moved = lines.changed(free, subproject_id=elsewhere["subproject_id"])
    assert moved["nodes"][0]["estimate_line"]["subproject_id"] == elsewhere["subproject_id"]


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_line_moved_under_a_started_task_says_its_subproject_is_no_more_editable(
    api: ContractClient, stage: Scene, tree: Tree, costs: Costing
) -> None:
    # ``moveNodes`` gives back the line under its new task, read as ``listNodes`` reads it.
    lines = Lines(tree)
    cabling = made(api, stage, "SP-CAB")
    started, waiting = tree.made("Câblage"), tree.made("Essais")
    line = lines.made(waiting, **material(costs, cabling))["nodes"][0]
    set_progress(stage, started["node_id"], "started", tree.created_at.date())
    charge(stage, "SP-CAB")
    with stage.database.transaction() as session:
        counter = session.scalar(
            select(CostStructure.lock_version).where(CostStructure.id == UUID(tree.structure_id))
        )
    sent = {"node_ids": [line["node_id"]], "parent_id": started["node_id"], "lock_version": counter}
    answer = api.post(f"{tree.path}/nodes/move", headers=stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text
    [node] = [item for item in answer.json()["nodes"] if item["node_id"] == line["node_id"]]
    assert SUBPROJECT_FIELD not in node["editable_fields"]
