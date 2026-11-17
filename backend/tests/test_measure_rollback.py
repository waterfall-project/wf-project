# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the measure of the writes leaves behind: nothing (US-2210/L1).

``make measure-core`` enters a cell and opens a revision on the witness of the service platform,
and rolls each one back so that the next measure starts from the same witness. The tool is no
requirement's: these tests hold it to that promise, on the database of the tests, by counting the
rows of the tables a write touches before and after.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from nodes_support import Tree, opened
from projects_support import scene as make_scene
from sqlalchemy import Engine, func, select

from measure.target import Target
from measure.writing import measure_opening, measure_writes, write_once
from waterfall.core.history.tables import UndoEntry
from waterfall.core.planning.interface import NodeFilters, Place, list_nodes
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.logs import PLATFORM, logging_context

if TYPE_CHECKING:
    from projects_support import Scene
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

_COUNTED = (Node, Task, TaskLink, CostStructure, Revision, UndoEntry)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened, two tasks linked in it."""
    made = Tree(api, stage, opened(api, stage))
    first, second = made.made("A"), made.made("B")
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": first["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "0", "unit": "d"},
            }
        ],
        "lock_version": second["lock_version"],
    }
    answer = api.put(
        f"{made.path}/nodes/{second['node_id']}/predecessors",
        headers=stage.manager.headers,
        json=sent,
    )
    assert answer.status_code == 200, answer.text
    return made


def _place(tree: Tree) -> Place:
    return Place(
        UUID(tree.stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
    )


def _state(database: Database) -> dict[str, Any]:
    """Count the rows of the tables a write touches, and read what a cell enters."""
    with database.transaction() as session:
        counts = {
            table.__tablename__: session.scalar(select(func.count()).select_from(table))
            for table in _COUNTED
        }
        cells = sorted(session.execute(select(Task.label, Task.duration_value)).all())
        revisions = sorted(session.execute(select(Revision.id, Revision.status)).all())
    return {"counts": counts, "cells": cells, "revisions": revisions}


def test_a_label_and_a_duration_entered_by_the_measure_leave_nothing_written(tree: Tree) -> None:
    place = _place(tree)
    with tree.stage.database.transaction() as session:
        leaf = next(
            each
            for each in list_nodes(session, place, NodeFilters(kinds=("task",))).items
            if each.task is not None and each.task.label == "A"
        )
    before = _state(tree.stage.database)

    label = write_once(tree.stage.database, place, leaf, "label")
    duration = write_once(tree.stage.database, place, leaf, "duration")

    assert _state(tree.stage.database) == before
    assert label.rescheduled == 0
    assert duration.rescheduled == 1


def test_the_writes_measured_pick_the_leaf_that_redates_and_leave_nothing_written(
    tree: Tree,
) -> None:
    before = _state(tree.stage.database)

    measures = measure_writes(tree.stage.database, _place(tree), 2)

    assert _state(tree.stage.database) == before
    assert measures[1].facts["rescheduled"] == 1
    assert measures[1].notes == ()


def test_a_revision_opened_by_the_measure_leaves_the_current_one_and_nothing_else(
    tree: Tree,
) -> None:
    target = Target(_place(tree), int(tree.revision["lock_version"]), tree.stage.manager.user_id)
    before = _state(tree.stage.database)

    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        measure = measure_opening(tree.stage.database, target, 2)

    assert _state(tree.stage.database) == before
    assert measure.summary is not None
    assert measure.summary.runs == 2
