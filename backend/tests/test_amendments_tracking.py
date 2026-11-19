# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The inscriptions of a task, refused outside of the main structure (US-2550/L4; #2497, #2499).

An inscription is kept by the lineage of a task of the main structure, which a differential shares:
``setNodeTracking`` on the node of a differential is refused by the condition ``main_structure``
(409, the example ``node_tracking_amendment_refused``), nothing is written; two writes of the
inscriptions of one lineage come one after the other, whatever the structure they are written
under, and none ends in a failure. Every answer is checked against the contract
(``ContractClient``).
"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from amendments_support import on, opened_amendment
from estimate_support import Costing, costing
from history_support import counter
from nodes_support import mark
from project_rows import STAMP
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import STUDY, Costed, costed
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from support import wait_for_a_lock

from waterfall.core.planning.lineage_lock import lock_lineage
from waterfall.core.planning.tables import Node, TrackingEntry

if TYPE_CHECKING:
    from nodes_support import Tree
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

FIXTURES = Path(__file__).parents[2] / "fixtures" / "api"
TIME_TIME: dict[str, Any] = {"kind": "milestone_tracking"}


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


def task_of(tree: Tree, label: str) -> dict[str, Any]:
    """Read a task of a structure by its label."""
    found = [each for each in tree.items() if each["task"] and each["task"]["label"] == label]
    assert len(found) == 1, label
    return found[0]


def timeline(api: ContractClient, project: Costed, label: str = "Comité") -> str:
    """Create a timeline of the project; give its identifier."""
    answer = api.post(
        f"{PROJECTS}/{project.project_id}/timelines",
        headers=project.stage.manager.headers,
        json={"label": label},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["timeline_id"]


def track(tree: Tree, node: dict[str, Any], *sent: dict[str, Any]) -> Any:
    """Replace the inscriptions of a task at the version read, as the manager does."""
    body = {"entries": list(sent), "lock_version": node["lock_version"]}
    return tree.api.put(
        f"{tree.path}/nodes/{node['node_id']}/tracking",
        headers=tree.stage.manager.headers,
        json=body,
    )


def held(project: Costed) -> list[tuple[UUID, str, UUID | None]]:
    """Read the inscriptions the base holds."""
    with project.stage.database.transaction() as session:
        found = session.execute(
            select(TrackingEntry.lineage_id, TrackingEntry.kind, TrackingEntry.timeline_id)
        )
        return sorted(((each[0], each[1], each[2]) for each in found), key=str)


# --- The refusal ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0060-A")
def test_an_inscription_on_a_node_of_a_differential_is_refused_and_writes_nothing(
    api: ContractClient, project: Costed
) -> None:
    # « une inscription est celle d'une tâche de la structure principale » (#2497): the node of a
    # differential shares the lineage of the main structure's, which it would write.
    tree = on(project.tree, opened_amendment(api, project))
    study = task_of(tree, STUDY)
    assert "task.tracking" not in study["editable_fields"]
    committee = timeline(api, project)
    before = (held(project), counter(tree), tree.read().json())
    answer = track(tree, study, {"kind": "timeline", "timeline_id": committee})
    assert answer.status_code == 409, answer.text
    assert answer.json()["code"] == "STATE_FORBIDS_OPERATION"
    assert answer.json()["params"] == {"missing_condition": "main_structure"}
    example = json.loads((FIXTURES / "node_tracking_amendment_refused.json").read_text())["value"]
    assert answer.json()["params"] == example["params"]
    assert (held(project), counter(tree), tree.read().json()) == before
    # The task of the main structure, which the differential copies, is inscribed as before.
    main = task_of(project.tree, STUDY)
    written = track(project.tree, main, {"kind": "timeline", "timeline_id": committee})
    assert written.status_code == 200, written.text
    assert [each[1] for each in held(project)] == ["timeline"]
    assert task_of(on(project.tree, tree.structure_id), STUDY)["task"]["tracking"] == [
        {"kind": "timeline", "timeline_id": committee}
    ]


@pytest.mark.requirement("WF-PLA-0060-A")
def test_the_refusal_comes_after_the_conditions_of_the_revision_and_before_the_node_is_found(
    api: ContractClient, project: Costed
) -> None:
    tree = on(project.tree, opened_amendment(api, project))
    study = task_of(tree, STUDY)
    unknown = {**study, "node_id": str(UUID(int=5))}
    answer = track(tree, unknown, TIME_TIME)
    assert answer.status_code == 409, answer.text
    assert answer.json()["params"] == {"missing_condition": "main_structure"}
    mark(project.stage, project.tree.revision)
    answer = track(tree, study, TIME_TIME)
    assert answer.status_code == 409, answer.text
    assert answer.json()["params"] == {"missing_condition": "revision_draft"}


# --- The serialization by the lineage ----------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0060-A")
def test_two_writes_of_the_inscriptions_of_a_lineage_come_one_after_the_other_and_none_fails(
    api: ContractClient, project: Costed
) -> None:
    # A write that holds the lineage — under another structure than the one the request locks —
    # and has inscribed the same entry: the request waits for it (the lock of the lineage, not that
    # of its structure), then finds the inscription written and keeps it: one row, no failure
    # (#2499).
    stage = project.stage
    committee = timeline(api, project)
    study = task_of(project.tree, STUDY)
    with stage.database.transaction() as session:
        lineage = session.scalar(select(Node.lineage_id).where(Node.id == UUID(study["node_id"])))
    assert lineage is not None
    with ThreadPoolExecutor(1) as others, Session(stage.owner) as holding:
        lock_lineage(holding, project.project_id, lineage)
        holding.execute(
            insert(TrackingEntry).values(
                id=uuid4(),
                project_id=project.project_id,
                lineage_id=lineage,
                kind="timeline",
                timeline_id=UUID(committee),
                **STAMP,
            )
        )
        asking = others.submit(
            track, project.tree, study, {"kind": "timeline", "timeline_id": committee}
        )
        wait_for_a_lock(stage.database)
        assert not asking.done()
        holding.commit()
    answer = asking.result(timeout=10)
    assert answer.status_code == 200, answer.text
    assert held(project) == [(lineage, "timeline", UUID(committee))]
