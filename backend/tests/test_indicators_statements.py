# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The statements of the computation of the scopes of a day, counted (#3569, #3802).

The computation of the indicators and the curves of scopes reads the tree of the revision computed
and that of its reference once, the remaining to commit drawn from them, and the actual cost of
every scope by one sum by subproject: a scope more costs one statement only, the tracked lines of
its curves by day of document. The project is a project In progress priced task by task, a
subproject bearing one of its lines (``day_indicators_support``).

The tasks the indicators read of a revision are read alone (#3902): the tasks, what their lines
count and their calendars, in as many statements whatever their number, none of the links, the
tracking or the physical progress a reading of the grid adds — the gain of the screen of the
indicators, read in the report of WF-QUA-0060 (US-2300); a detail of the reading, which cites no
requirement. They are what ``listNodes`` reads of the same tasks.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import load_import
from day_indicators_support import Planned, completed, dated, priced, subproject
from indicators_support import progressed
from planning_support import DAY
from projects_support import Scene
from projects_support import scene as make_scene
from remaining_support import task_named
from sqlalchemy import event

from waterfall.core.costs.interface import PROJECT, UNASSIGNED, CostScope
from waterfall.core.indicators.caching import day_entry
from waterfall.core.indicators.interface import IndicatorsReading, day_reading
from waterfall.core.planning.interface import (
    NodeFilters,
    Place,
    list_nodes,
    tasks_for_indicators,
)
from waterfall.core.revisions.interface import aimed_structure
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Sequence

    from nodes_support import Tree
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def statements(stage: Scene, scopes: list[CostScope]) -> list[str]:
    """Give the statements the computation of the scopes of the day sends, in their order."""
    sent: list[str] = []

    def heard(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    with stage.database.transaction() as session:
        project_id = UUID(stage.project["project_id"])
        reading = day_reading(session, project_id, IndicatorsReading(PROJECT, utc_now()))
        assert reading is not None
        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", heard)
        try:
            day_entry(session, reading.basis, reading.context, scopes)
        finally:
            event.remove(engine, "before_cursor_execute", heard)
    return sent


def test_a_scope_more_costs_one_statement_and_the_actual_cost_is_summed_once(
    api: ContractClient, stage: Scene
) -> None:
    # A criterion of the lot's own (#3802), which reprises no Vérif: it cites no requirement.
    lot = UUID(subproject(api, stage, "10001", "Lot 10001"))
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600", str(lot))])
    completed(found.tree, "Études", DAY)
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    alone = statements(stage, [lot])
    every = statements(stage, [PROJECT, lot, UNASSIGNED])
    assert len(every) == len(alone) + 2, (alone, every)
    # The actual cost is read from its table once for the sum of every scope, and once by scope
    # for the days it falls on.
    for sent, scopes in ((alone, 1), (every, 3)):
        read = [each for each in sent if "FROM cost_line" in each]
        assert len(read) == 1 + scopes, sent
    # The lines of a revision are read once by revision: the remaining does not read them again.
    rows = [each for each in alone if "FROM estimate_line" in each]
    revisions = {found.reference_id, UUID(found.tree.revision["revision_id"])}
    assert len(rows) == len(revisions), alone


# The tables a reading of the grid reads beside the tasks, and the indicators never.
UNREAD = ("FROM task_link", "FROM tracking_entry", "FROM timeline", "FROM structure_reading")


def read_tasks(stage: Scene, tree: Tree) -> tuple[list[str], Sequence[tuple[object, ...]]]:
    """Read the tasks of the current revision for the indicators: the statements, and the tasks.

    Each task as ``listNodes`` reads it beside, for the comparison: its node, its state, its dates.
    """
    sent: list[str] = []

    def heard(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    project_id = UUID(stage.project["project_id"])
    revision_id = UUID(tree.revision["revision_id"])
    with stage.database.transaction() as session:
        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", heard)
        try:
            found = tasks_for_indicators(session, project_id, revision_id)
        finally:
            event.remove(engine, "before_cursor_execute", heard)
        structure_id = aimed_structure(session, project_id, revision_id, None)
        assert structure_id is not None
        place = Place(project_id, revision_id, structure_id)
        listed = list_nodes(session, place, NodeFilters(kinds=("task",))).items
    tasks = [
        (
            each.node_id,
            each.lineage_id,
            each.parent_id,
            each.label,
            each.is_summary,
            each.is_milestone,
            each.progress,
            each.started_on,
            each.completed_on,
            each.start,
            each.finish,
            each.calendar_hours,
            each.origin_risk_id,
        )
        for each in found
    ]
    expected = [
        (
            node.node_id,
            node.lineage_id,
            node.parent_id,
            task.label,
            task.is_summary,
            task.is_milestone,
            task.progress,
            task.started_on,
            task.completed_on,
            task.start,
            task.finish,
            task.calendar_hours,
            node.origin_risk_id,
        )
        for node in listed
        if (task := node.task) is not None
    ]
    assert tasks == expected
    return sent, tasks


def test_the_tasks_of_the_indicators_are_read_alone_in_as_many_statements_whatever_their_number(
    api: ContractClient, stage: Scene
) -> None:
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600")])
    completed(found.tree, "Études", DAY)
    few, tasks = read_tasks(stage, found.tree)
    # A summary over three subtasks, one of them started, and a milestone: more tasks, of each
    # shape whose state the reading derives.
    lot = found.tree.made("Lot")
    for label in ("Pose", "Essais", "Recette"):
        found.tree.made(label, parent_id=lot["node_id"])
    progressed(found.tree, task_named(found.tree, "Pose"), "started", DAY)
    found.tree.made("Livraison", task={"duration": {"value": "0", "unit": "d"}})
    many, more = read_tasks(stage, found.tree)
    assert len(more) == len(tasks) + 5
    shapes = {(each[4], each[5], each[6]) for each in more}
    assert {(True, False, "started"), (False, True, "not_started")} <= shapes, more
    assert "completed" in {each[6] for each in more}, more
    assert len(many) == len(few), (few, many)
    assert not [each for each in many if any(table in each for table in UNREAD)], many
