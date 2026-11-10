# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a write of a line of estimate holds against the writes of the reference and of the project.

The lock of the natures of cost, shared before the lock of the structure, in the order a change of a
nature takes them (#2615); the subproject the line names, read ``FOR KEY SHARE``, so that one a
deletion takes away meanwhile is refused as unknown (#2616). Each write is seen waiting for the
transaction that holds the lock (``pg_blocking_pids``), never on a delay.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, faults, opened
from projects_support import PROJECTS
from projects_support import scene as make_scene
from sqlalchemy import delete, func, select
from sqlalchemy.exc import OperationalError
from test_estimate_lines import blocked_by

from waterfall.core.cost_settings.records import NATURES_LOCK
from waterfall.core.projects.tables import Subproject
from waterfall.core.revisions.tables import CostStructure

if TYPE_CHECKING:
    from projects_support import Scene
    from realm import TestRealm
    from sqlalchemy import Connection, Engine
    from support import ContractClient

    from waterfall.platform.database import Database


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


@pytest.fixture
def lines(tree: Tree) -> Lines:
    """Give the lines of the main structure."""
    return Lines(tree)


def material(costs: Costing, **line: Any) -> dict[str, Any]:
    """Give a line of material: one at 350.00, unless said."""
    held = {"quantity": "1", "cost_category_id": str(costs.material), "unit_disbursement": "350.00"}
    return {**held, **line}


def structure_free(stage: Scene, tree: Tree) -> bool:
    """Tell whether the structure can be locked at once by another transaction (``NOWAIT``)."""
    with stage.owner.begin() as trying:
        try:
            trying.execute(
                select(CostStructure.id)
                .where(CostStructure.id == UUID(tree.structure_id))
                .with_for_update(nowait=True)
            )
        except OperationalError:
            return False
    return True


def natures_locked(connection: Connection) -> int | None:
    """Take the lock of the natures as a change of a nature does, and give the session's pid."""
    connection.execute(select(func.pg_advisory_xact_lock(NATURES_LOCK)))
    return connection.scalar(select(func.pg_backend_pid()))


@pytest.mark.requirement("WF-REF-0040-A")
@pytest.mark.parametrize("write", ["create", "change", "move"])
def test_a_write_of_a_line_waits_for_a_change_of_a_nature_before_it_locks_its_structure(
    stage: Scene, tree: Tree, lines: Lines, costs: Costing, write: str
) -> None:
    # « Une catégorie employée par une ligne de devis [...] ne se rattache qu'à une nature du même
    # type que la sienne » : a change of a nature takes the lock of the natures, then the
    # structures it prices again; a write of a line shares that lock first, and waits for the
    # change without holding its structure — the change would wait for it otherwise (#2615).
    task = tree.made("Câblage")
    other = tree.made("Essais")
    node = lines.made(task, **material(costs))["nodes"][0]
    counter = lines.made(task, **material(costs, label="Câbles"))["structure_lock_version"]

    def run() -> Any:
        if write == "create":
            return lines.create(task, **material(costs, label="Borniers"))
        if write == "change":
            return lines.change(node, quantity="2")
        sent = {
            "node_ids": [node["node_id"]],
            "parent_id": other["node_id"],
            "lock_version": counter,
        }
        return tree.api.post(
            f"{tree.path}/nodes/move", headers=tree.stage.manager.headers, json=sent
        )

    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        holder = natures_locked(connection)
        waiting = pool.submit(run)
        assert blocked_by(stage, holder, waiting)
        assert structure_free(stage, tree)
        assert not waiting.done()
    answer = waiting.result(timeout=30)
    assert answer.status_code in {200, 201}, answer.text


@pytest.mark.requirement("WF-PRJ-0050-A")
def test_a_line_naming_a_subproject_a_deletion_takes_away_meanwhile_is_refused_as_unknown(
    api: ContractClient, stage: Scene, tree: Tree, lines: Lines, costs: Costing
) -> None:
    # A line names a subproject of its project (WF-PRJ-0050); one deleted while the write waits on
    # its key is refused as one that never was, 422 ``UNKNOWN_SUBPROJECT``, not by the key of the
    # line (500), and no line is written (#2616).
    task = tree.made("Câblage")
    answer = api.post(
        f"{PROJECTS}/{stage.project['project_id']}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-CMD", "label": "Poste de commande"},
    )
    assert answer.status_code == 201, answer.text
    subproject = answer.json()["subproject_id"]
    with ThreadPoolExecutor(max_workers=1) as pool, stage.owner.begin() as connection:
        connection.execute(delete(Subproject).where(Subproject.id == UUID(subproject)))
        holder = connection.scalar(select(func.pg_backend_pid()))
        waiting = pool.submit(lines.create, task, **material(costs, subproject_id=subproject))
        assert blocked_by(stage, holder, waiting)
    refused = waiting.result(timeout=30)
    assert faults(refused) == [("/estimate_line/subproject_id", "UNKNOWN_SUBPROJECT", {})]
    assert tree.items("?kinds=estimate_line") == []
