# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The conditions of the re-estimation of a line, said in advance and refused (US-1580/L2).

A project In progress (``remaining_support``): ``listNodes`` gives each line whether it accepts a
re-estimate (``remaining_entry``), the lines of the tasks not started at the asking, open; and the
subprojects of the lines read are asked for their actual costs in one statement (#2730). Every
answer is checked against the contract.
"""

from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, set_progress
from planning_support import DAY
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from remaining_support import Review, in_progress, line_named, task_named
from sqlalchemy import event

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

BASIS = "reestimated_amount_basis"
OPEN: dict[str, Any] = {"is_available": True, "missing_conditions": []}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories and the role the lines name, rated 65.00 for the year."""
    return costing(stage.database)


def subproject(api: ContractClient, stage: Scene, code: str) -> str:
    """Create a subproject of the project, as its manager does; give it."""
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": code, "label": f"Sous-projet {code}"},
    )
    assert answer.status_code == 201, answer.text
    return str(answer.json()["subproject_id"])


@pytest.fixture
def review(api: ContractClient, stage: Scene, costs: Costing) -> Review:
    """Give the project In progress: three tasks, each a line of material in a subproject."""
    codes = [subproject(api, stage, code) for code in ("SP-A", "SP-B", "SP-C")]

    def build(tree: Tree, lines: Lines) -> None:
        for label, held in zip(("Câblage", "Essais", "Réception"), codes, strict=True):
            task = tree.made(label)
            lines.made(
                task,
                label=f"Ligne {label}",
                quantity="1",
                cost_category_id=str(costs.material),
                unit_disbursement="100",
                subproject_id=held,
            )

    return in_progress(api, stage, build)


def labels(tree: Tree, query: str) -> list[str]:
    """Read the labels of the lines a query retains."""
    return [
        item["estimate_line"]["label"]
        for item in tree.items(query)
        if item["kind"] == "estimate_line"
    ]


@pytest.mark.requirement("WF-RAE-0040-A")
def test_the_lines_of_tasks_not_started_appear_at_the_asking_and_accept_a_re_estimate(
    review: Review, stage: Scene
) -> None:
    # « Les tâches non démarrées n'apparaissent qu'à la demande, et sont alors modifiables. » The
    # grid is US-1640's; the reading filters by the state of the task, and each line says whether
    # it accepts a re-estimate; a completed task's do not (``task_not_completed``).
    tree = review.tree
    set_progress(stage, task_named(tree, "Câblage")["node_id"], "started", DAY)
    set_progress(stage, task_named(tree, "Réception")["node_id"], "completed", DAY)
    assert labels(tree, "?progress=started") == ["Ligne Câblage"]
    assert labels(tree, "?progress=started,not_started") == ["Ligne Câblage", "Ligne Essais"]
    entries = {
        line["estimate_line"]["label"]: line["estimate_line"]["remaining_entry"]
        for line in tree.items()
        if line["kind"] == "estimate_line"
    }
    assert entries == {
        "Ligne Câblage": OPEN,
        "Ligne Essais": OPEN,
        "Ligne Réception": {"is_available": False, "missing_conditions": ["task_not_completed"]},
    }
    line = line_named(tree, "Ligne Essais")
    sent = {BASIS: {"unit_disbursement": "80"}, "lock_version": line["lock_version"]}
    answer = tree.api.put(
        f"{tree.path}/nodes/{line['node_id']}/remaining", headers=stage.manager.headers, json=sent
    )
    assert answer.status_code == 200, answer.text


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_the_actual_costs_of_the_subprojects_of_the_lines_read_are_asked_in_one_statement(
    review: Review, stage: Scene
) -> None:
    # #2730: a line of a task started does not leave a subproject that received actual costs
    # (``editable_fields``); the subprojects of the lines read are asked once, not one by one.
    tree = review.tree
    set_progress(stage, task_named(tree, "Câblage")["node_id"], "started", DAY)
    statements: list[str] = []

    def heard(*caught: Any) -> None:
        statements.append(caught[2])

    event.listen(stage.database.engine, "before_cursor_execute", heard)
    try:
        read = tree.items("?kinds=estimate_line")
    finally:
        event.remove(stage.database.engine, "before_cursor_execute", heard)
    assert len(read) == 3
    asked = [each for each in statements if "FROM cost_line" in each]
    assert len(asked) == 1
