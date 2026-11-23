# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The conflict of a manual task under a summary linked: judged, kept, given (US-3300/L3).

A link toward a summary binds each of its subordinates: its predecessor that cannot satisfy a
subordinate in manual mode is signalled with that task, which the conflict names
(``LinkConflict.manual_node_id``, #3984), on the predecessor and on the task, never on the summary.
The engine writes the task in ``task_link_conflict`` with the link; a revision opened copies it with
the links, a marked one keeps it read only, an abandoned one takes it away. Through the service, on
the main structure of a revision its project's manager opened, every answer checked against the
contract; the planning starts on Monday the 2nd of November 2026, on the default calendar of eight
hours from Monday to Friday.
"""

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from nodes_support import Tree, instant, mark, opened
from planning_support import DAY
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from waterfall.core.planning.tables import Node, TaskLink, TaskLinkConflict

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

WEDNESDAY = DAY + timedelta(days=2)
NEXT_WEDNESDAY = DAY + timedelta(days=9)
NEXT_MONDAY = DAY + timedelta(days=14)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def summary_after(tree: Tree, duration: str, day: Any) -> tuple[dict[str, Any], ...]:
    """Make P of a duration in days, linked finish to start to S, whose subordinate M is manual.

    M, the only subordinate of S, lasts the day given. Gives P, S, M as created, and the answer of
    the link.
    """
    predecessor = tree.made("P", task={"duration": {"value": duration, "unit": "d"}})
    summary = tree.made("S")
    fixed = tree.made(
        "M",
        parent_id=summary["node_id"],
        task={
            "scheduling_mode": "manual",
            "start": instant(day, "0"),
            "finish": instant(day, "8"),
        },
    )
    sent = {
        "predecessors": [
            {
                "predecessor_node_id": predecessor["node_id"],
                "link_type": "finish_to_start",
                "lag": {"value": "0", "unit": "d"},
            }
        ],
        "lock_version": tree.node(summary["node_id"])["lock_version"],
    }
    path = f"{tree.path}/nodes/{summary['node_id']}/predecessors"
    answer = tree.api.put(path, headers=tree.stage.manager.headers, json=sent)
    assert answer.status_code == 200, answer.text
    return predecessor, summary, fixed, answer.json()


def conflict_of(
    predecessor: dict[str, Any], summary: dict[str, Any], fixed: dict[str, Any]
) -> dict[str, str]:
    """Give the conflict of the link P → S that names M, as the contract writes it."""
    return {
        "predecessor_node_id": predecessor["node_id"],
        "successor_node_id": summary["node_id"],
        "manual_node_id": fixed["node_id"],
        "link_type": "finish_to_start",
    }


def scheduled(written: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Give the tasks a write redated without writing them, by node."""
    return {each["node_id"]: each for each in written["rescheduled"]}


def kept(owner: Engine, revision_id: str) -> int:
    """Count the tasks in conflict a revision keeps."""
    with owner.connect() as connection:
        return connection.execute(
            select(func.count())
            .select_from(TaskLinkConflict)
            .where(TaskLinkConflict.revision_id == UUID(revision_id))
        ).scalar_one()


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_predecessor_of_the_summary_of_a_manual_task_is_critical_and_signalled_with_it(
    tree: Tree,
) -> None:
    # « Un prédécesseur automatique qui ne peut pas finir avant le début d'une tâche manuelle porte
    # une marge négative, apparaît sur le chemin critique et est signalé. », its form when the link
    # aims at the summary of the manual task (BPL-06): P of five days, finish to start toward S,
    # whose subordinate M is manual and dated on the Wednesday: P carries a float of minus three
    # days, is on the critical path, and P and M are signalled by the link P → S.
    predecessor, summary, fixed, _ = summary_after(tree, "5", WEDNESDAY)
    conflict = conflict_of(predecessor, summary, fixed)
    read = {item["node_id"]: item["task"] for item in tree.items()}
    signalled = read[predecessor["node_id"]]
    assert (signalled["total_float"], signalled["is_critical"]) == (
        {"value": "-3", "unit": "d"},
        True,
    )
    assert signalled["link_conflicts"] == read[fixed["node_id"]]["link_conflicts"] == [conflict]
    assert read[summary["node_id"]]["link_conflicts"] == []


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_predecessor_of_a_summary_is_signalled_with_its_manual_subordinate_until_delayed(
    tree: Tree, owner: Engine
) -> None:
    # « Un prédécesseur lié fin à début à une récapitulative, dont une subordonnée manuelle est
    # datée avant sa fin, est signalé avec cette subordonnée. » A (here P, ten days, automatic)
    # precedes the summary S finish to start, whose only subordinate M is manual and dated on the
    # Wednesday of the second week, before A finishes on its Friday: A floats negative, and
    # link_conflicts signals A and M by the link A → S; delaying M past the finish of A makes the
    # signal disappear (#3984). The write that links S gives M back, its conflict changed.
    predecessor, summary, fixed, written = summary_after(tree, "10", NEXT_WEDNESDAY)
    conflict = conflict_of(predecessor, summary, fixed)
    moved = scheduled(written)
    assert moved[predecessor["node_id"]]["link_conflicts"] == [conflict]
    assert moved[predecessor["node_id"]]["total_float"] == {"value": "-3", "unit": "d"}
    assert moved[fixed["node_id"]]["link_conflicts"] == [conflict]
    assert written["nodes"][0]["task"]["link_conflicts"] == []
    assert tree.node(fixed["node_id"])["task"]["link_conflicts"] == [conflict]
    assert kept(owner, tree.revision["revision_id"]) == 1
    delayed = tree.changed(
        tree.node(fixed["node_id"]),
        start=instant(NEXT_MONDAY, "0"),
        finish=instant(NEXT_MONDAY, "8"),
    )
    assert delayed["nodes"][0]["task"]["link_conflicts"] == []
    lifted = scheduled(delayed)[predecessor["node_id"]]
    assert lifted["link_conflicts"] == []
    assert lifted["total_float"] == {"value": "0", "unit": "d"}
    assert tree.node(predecessor["node_id"])["task"]["link_conflicts"] == []
    assert kept(owner, tree.revision["revision_id"]) == 0


@pytest.mark.story("US-3300")
def test_a_conflict_follows_the_deletion_of_its_link_and_of_its_task(
    tree: Tree, owner: Engine
) -> None:
    # Propre à l'US (« Tables et migrations ») : the row of a conflict follows the deletion of its
    # link, and of its task, inside a current revision, by the keys that cascade.
    revision = tree.revision["revision_id"]
    summary_after(tree, "10", NEXT_WEDNESDAY)
    assert kept(owner, revision) == 1
    with owner.begin() as connection:
        connection.execute(delete(TaskLink).where(TaskLink.revision_id == UUID(revision)))
    assert kept(owner, revision) == 0
    _, _, fixed, _ = summary_after(tree, "10", NEXT_WEDNESDAY)
    assert kept(owner, revision) == 1
    with owner.begin() as connection:
        connection.execute(delete(Node).where(Node.id == UUID(fixed["node_id"])))
    assert kept(owner, revision) == 0


@pytest.mark.story("US-3300")
def test_a_conflict_is_copied_with_its_link_kept_read_only_once_marked_and_abandoned_with_it(
    api: ContractClient, stage: Scene, tree: Tree, owner: Engine
) -> None:
    # Propre à l'US (« Tables et migrations ») : the task in conflict is copied at the opening of a
    # revision with the links, then written again by its replay; a marked revision keeps it, which
    # the database refuses to delete; the abandonment takes it away with the links (WF-DAT-0010).
    _, _, fixed, _ = summary_after(tree, "10", NEXT_WEDNESDAY)
    marked = tree.revision["revision_id"]
    mark(stage, tree.revision)
    assert tree.node(fixed["node_id"])["task"]["link_conflicts"] != []
    with pytest.raises(IntegrityError, match="never written"), owner.begin() as connection:
        connection.execute(
            delete(TaskLinkConflict).where(TaskLinkConflict.revision_id == UUID(marked))
        )
    current = Tree(api, stage, opened(api, stage))
    read = {item["task"]["label"]: item for item in current.items()}
    conflict = {
        "predecessor_node_id": read["P"]["node_id"],
        "successor_node_id": read["S"]["node_id"],
        "manual_node_id": read["M"]["node_id"],
        "link_type": "finish_to_start",
    }
    assert read["P"]["task"]["link_conflicts"] == read["M"]["task"]["link_conflicts"] == [conflict]
    assert read["M"]["node_id"] != fixed["node_id"]
    assert (kept(owner, marked), kept(owner, current.revision["revision_id"])) == (1, 1)
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{current.revision['revision_id']}"
    lock_version = api.get(path, headers=stage.manager.headers).json()["lock_version"]
    answer = api.delete(f"{path}?lock_version={lock_version}", headers=stage.manager.headers)
    assert answer.status_code == 204, answer.text
    assert (kept(owner, marked), kept(owner, current.revision["revision_id"])) == (1, 0)
