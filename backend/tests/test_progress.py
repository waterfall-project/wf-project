# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The state of a task: started, completed, reopened, and what a summary derives (US-1410).

``setTaskProgress`` on the main structure of a revision a project's manager opened, every answer
checked against the contract: the day of the gesture, the dates of a leaf and of a milestone, the
state and the dates a summary derives from its subordinates, the first condition a gesture lacks
and the conditions of the entry of the remaining to commit that come after it, the counter, the
rights, the entry of the history, two gestures at once, and the state the witness loads. The state
of the project is put around the service, as EP-04 did (``put_in_state``).
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from nodes_support import (
    CHANGE,
    Tree,
    entries,
    mark,
    opened,
    refusal,
    signed_in,
)
from planning_support import node_row
from projects_support import PROJECTS, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import insert, select

from waterfall.core.planning import writing
from waterfall.core.planning.interface import ProgressLoad, load_progress
from waterfall.core.planning.tables import Node, Task
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import NotFoundError, UnprocessableError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

IN_PROGRESS = "in_progress"
MILESTONE = {"duration": {"value": "0", "unit": "d"}}
JUNE_THIRD = "2026-06-03"
JUNE_TENTH = "2026-06-10"
READ = "remaining.read"
WRITE = "remaining.write"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made, in progress."""
    scene = make_scene(api, owner, database, realm)
    put_in_state(owner, scene.project["project_id"], IN_PROGRESS)
    return scene


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def gesture(tree: Tree, node: dict[str, Any], state: str, who: Any = None, **body: Any) -> Any:
    """Send the state of a card at the counter read; give the answer."""
    sent = {"progress": state, "lock_version": node["lock_version"], **body}
    headers = (who or tree.stage.manager).headers
    return tree.api.put(f"{tree.path}/nodes/{node['node_id']}/progress", headers=headers, json=sent)


def moved(tree: Tree, node: dict[str, Any], state: str, **body: Any) -> dict[str, Any]:
    """Send a gesture that must be accepted; give the node it wrote."""
    answer = gesture(tree, node, state, **body)
    assert answer.status_code == 200, answer.text
    return answer.json()["nodes"][0]


def missing(answer: Any) -> str:
    """Give the condition a refusal of 409 names, after checking its code."""
    status, code, params = refusal(answer)
    assert (status, code) == (409, "STATE_FORBIDS_OPERATION")
    return params["missing_condition"]


def line(stage: Scene, tree: Tree, parent: dict[str, Any], **columns: object) -> UUID:
    """Write an estimate line under a task around the service, as EP-07 will; give its node."""
    row = node_row(
        UUID(stage.project["project_id"]),
        UUID(tree.revision["revision_id"]),
        UUID(tree.structure_id),
        kind="estimate_line",
        parent_id=UUID(parent["node_id"]),
        **columns,
    )
    with stage.owner.begin() as connection:
        connection.execute(insert(Node).values(**row))
    node_id = row["id"]
    assert isinstance(node_id, UUID)
    return node_id


# --- The gestures --------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_task_is_started_on_the_day_sent_and_counted_with_the_summary_above_it(
    tree: Tree,
) -> None:
    # « Le passage à l'état démarré ou terminé demande une date, proposée au jour courant et
    # modifiable. » The date sent is the one written; the dates of the plan do not move.
    studies = tree.made("Études")
    detail = tree.made("Études de détail", parent_id=studies["node_id"])
    answer = gesture(tree, detail, "started", occurred_on=JUNE_THIRD)
    assert answer.status_code == 200, answer.text
    written = answer.json()
    [node] = written["nodes"]
    assert node["task"]["progress"] == "started"
    assert node["task"]["started_on"] == JUNE_THIRD
    assert node["task"]["completed_on"] is None
    assert node["lock_version"] == detail["lock_version"] + 1
    assert node["task"]["start"] == detail["task"]["start"]
    assert node["task"]["finish"] == detail["task"]["finish"]
    [above] = written["ancestors"]
    assert (above["node_id"], above["lock_version"]) == (studies["node_id"], 1)
    assert (above["task"]["progress"], above["task"]["started_on"]) == ("started", JUNE_THIRD)
    assert tree.node(detail["node_id"])["task"]["started_on"] == JUNE_THIRD


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_gesture_without_a_date_is_dated_the_day_it_is_made(tree: Tree) -> None:
    node = tree.made("Câblage")
    before = datetime.now(UTC).date()
    started = moved(tree, node, "started")
    done = moved(tree, started, "completed")
    after = datetime.now(UTC).date()
    assert before <= date.fromisoformat(started["task"]["started_on"]) <= after
    assert before <= date.fromisoformat(done["task"]["completed_on"]) <= after
    assert done["task"]["started_on"] == started["task"]["started_on"]


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_started_task_is_completed_then_reopened_and_keeps_its_start(tree: Tree) -> None:
    node = tree.made("Câblage")
    started = moved(tree, node, "started", occurred_on=JUNE_THIRD)
    done = moved(tree, started, "completed", occurred_on=JUNE_TENTH)
    assert done["task"]["progress"] == "completed"
    assert (done["task"]["started_on"], done["task"]["completed_on"]) == (JUNE_THIRD, JUNE_TENTH)
    reopened = moved(tree, done, "started", occurred_on="2026-06-20")
    assert reopened["task"]["progress"] == "started"
    assert reopened["task"]["started_on"] == JUNE_THIRD
    assert reopened["task"]["completed_on"] is None
    assert reopened["lock_version"] == node["lock_version"] + 3


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_completion_dated_before_the_start_of_the_task_is_refused_naming_the_start(
    tree: Tree,
) -> None:
    # « Une terminaison datée avant le démarrage de la tâche est refusée. » : on the date sent,
    # the start named as the least day accepted (#2495); the day of the start itself is accepted.
    node = tree.made("Câblage")
    started = moved(tree, node, "started", occurred_on=JUNE_TENTH)
    answer = gesture(tree, started, "completed", occurred_on=JUNE_THIRD)
    assert refusal(answer)[:2] == (422, "VALIDATION_FAILED")
    assert answer.json()["fields"] == [
        {"pointer": "/occurred_on", "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": JUNE_TENTH}}
    ]
    kept = tree.node(node["node_id"])
    assert (kept["task"]["progress"], kept["lock_version"]) == ("started", started["lock_version"])
    done = moved(tree, kept, "completed", occurred_on=JUNE_TENTH)
    assert (done["task"]["started_on"], done["task"]["completed_on"]) == (JUNE_TENTH, JUNE_TENTH)


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_completion_without_date_is_refused_for_a_task_started_in_the_future(
    tree: Tree,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The default day is the current day (#2495): a task started tomorrow, completed without
    # a date, is completed before its start, whatever the field not sent (422 on /occurred_on).
    # The clock of the service is fixed a second before midnight (universal time, the service's
    # day), where the writer of the nodes takes the day of the gesture: the day after it is read
    # from that clock, not from the day the test runs on.
    now = datetime(2026, 11, 13, 23, 59, 59, tzinfo=UTC)
    monkeypatch.setattr("waterfall.api.nodes.utc_now", lambda: now)
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    node = tree.made("Câblage")
    started = moved(tree, node, "started", occurred_on=tomorrow)
    answer = gesture(tree, started, "completed")
    assert refusal(answer)[:2] == (422, "VALIDATION_FAILED")
    assert answer.json()["fields"] == [
        {"pointer": "/occurred_on", "code": "VALUE_OUT_OF_RANGE", "params": {"minimum": tomorrow}}
    ]
    assert tree.node(node["node_id"])["task"]["progress"] == "started"


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_task_started_is_completed_with_no_line_at_the_date_of_the_gesture(tree: Tree) -> None:
    # « Une tâche démarrée qui ne porte aucune ligne hors lignes de provision » is completed
    # directly (WF-RAE-0030); a provision line, written for information, does not hold it back.
    node = tree.made("Câblage")
    started = moved(tree, node, "started", occurred_on=JUNE_THIRD)
    line(tree.stage, tree, started, origin_risk_id=uuid4())
    done = moved(tree, started, "completed", occurred_on=JUNE_TENTH)
    assert done["task"]["completed_on"] == JUNE_TENTH


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_milestone_completed_carries_one_date_for_its_start_and_its_end_and_loses_both_reopened(
    tree: Tree,
) -> None:
    node = tree.made("Réception", task=MILESTONE)
    done = moved(tree, node, "completed", occurred_on=JUNE_THIRD)
    assert done["task"]["is_milestone"] is True
    assert (done["task"]["started_on"], done["task"]["completed_on"]) == (JUNE_THIRD, JUNE_THIRD)
    assert done["task"]["start"] == node["task"]["start"]
    reopened = moved(tree, done, "not_started")
    assert reopened["task"]["progress"] == "not_started"
    assert reopened["task"]["started_on"] is None
    assert reopened["task"]["completed_on"] is None
    with tree.stage.database.transaction() as session:
        row = session.get(Task, (UUID(tree.stage.project["project_id"]), UUID(node["node_id"])))
        assert row is not None
        assert (row.started_on, row.completed_on) == (None, None)


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_task_started_and_not_a_milestone_cannot_return_to_not_started(tree: Tree) -> None:
    node = tree.made("Câblage")
    assert missing(gesture(tree, node, "not_started")) == "completed_milestone"
    started = moved(tree, node, "started")
    assert missing(gesture(tree, started, "not_started")) == "completed_milestone"
    done = moved(tree, started, "completed")
    assert missing(gesture(tree, done, "not_started")) == "completed_milestone"
    milestone = tree.made("Réception", task=MILESTONE)
    assert missing(gesture(tree, milestone, "not_started")) == "completed_milestone"
    assert tree.node(node["node_id"])["task"]["progress"] == "completed"


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_gesture_that_sends_the_state_a_task_is_in_changes_no_date(tree: Tree) -> None:
    node = tree.made("Câblage")
    started = moved(tree, node, "started", occurred_on=JUNE_THIRD)
    again = moved(tree, started, "started", occurred_on=JUNE_TENTH)
    assert again["task"]["started_on"] == JUNE_THIRD


# --- The conditions of the gesture ---------------------------------------------------------------


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_task_not_started_that_is_no_milestone_is_not_completed_directly(tree: Tree) -> None:
    node = tree.made("Câblage")
    assert missing(gesture(tree, node, "completed")) == "task_is_milestone"
    assert tree.node(node["node_id"])["task"]["progress"] == "not_started"
    assert tree.node(node["node_id"])["lock_version"] == node["lock_version"]


@pytest.mark.requirement("WF-PLA-0050-A")
def test_a_milestone_does_not_go_through_the_started_state_whatever_its_state(tree: Tree) -> None:
    node = tree.made("Réception", task=MILESTONE)
    assert missing(gesture(tree, node, "started")) == "task_not_milestone"
    done = moved(tree, node, "completed", occurred_on=JUNE_THIRD)
    assert missing(gesture(tree, done, "started")) == "task_not_milestone"
    assert tree.node(node["node_id"])["task"]["progress"] == "completed"


@pytest.mark.requirement("WF-RAE-0030-A")
def test_a_task_that_bears_a_line_besides_the_provisions_is_completed_by_its_remaining(
    tree: Tree,
) -> None:
    node = tree.made("Câblage")
    started = moved(tree, node, "started")
    milestone = tree.made("Réception", task=MILESTONE)
    line(tree.stage, tree, started)
    line(tree.stage, tree, milestone)
    assert missing(gesture(tree, started, "completed")) == "task_without_lines"
    assert missing(gesture(tree, milestone, "completed")) == "task_without_lines"
    assert tree.node(node["node_id"])["task"]["progress"] == "started"
    # Reopening and starting ask nothing of the lines.
    assert missing(gesture(tree, milestone, "started")) == "task_not_milestone"


@pytest.mark.requirement("WF-RAE-0030-A")
def test_the_nature_of_a_task_is_named_before_its_lines(tree: Tree) -> None:
    node = tree.made("Câblage")
    line(tree.stage, tree, node)
    assert missing(gesture(tree, node, "completed")) == "task_is_milestone"


@pytest.mark.requirement("WF-IHM-0030-A")
def test_a_summary_task_is_refused_naming_its_subordinates_in_the_order_of_the_plan(
    tree: Tree,
) -> None:
    studies = tree.made("Études")
    first = tree.made("Avant-projet", parent_id=studies["node_id"])
    second = tree.made("Détail", parent_id=studies["node_id"])
    third = tree.made("Revue", parent_id=studies["node_id"], after_node_id=None)
    summary = tree.node(studies["node_id"])
    for state in ("started", "completed", "not_started"):
        answer = gesture(tree, summary, state)
        assert answer.status_code == 422, answer.text
        body = answer.json()
        assert body["code"] == "SUMMARY_TASK_DERIVED"
        assert body["params"] == {
            "subordinate_node_ids": [third["node_id"], first["node_id"], second["node_id"]]
        }
    assert tree.node(studies["node_id"]) == summary


# --- What a summary derives ----------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_summary_is_started_as_soon_as_a_subordinate_is_and_dated_of_the_first(
    tree: Tree,
) -> None:
    studies = tree.made("Études")
    first = tree.made("Avant-projet", parent_id=studies["node_id"])
    second = tree.made("Détail", parent_id=studies["node_id"])
    assert tree.node(studies["node_id"])["task"]["progress"] == "not_started"
    moved(tree, second, "started", occurred_on=JUNE_TENTH)
    summary = tree.node(studies["node_id"])["task"]
    assert (summary["progress"], summary["started_on"]) == ("started", JUNE_TENTH)
    moved(tree, first, "started", occurred_on=JUNE_THIRD)
    summary = tree.node(studies["node_id"])["task"]
    assert (summary["progress"], summary["started_on"]) == ("started", JUNE_THIRD)
    assert summary["completed_on"] is None


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_summary_is_completed_after_its_last_subordinate_and_dated_of_the_last(
    tree: Tree,
) -> None:
    # « Une récapitulative porte la date de terminaison de sa dernière subordonnée. »
    studies = tree.made("Études")
    first = tree.made("Avant-projet", parent_id=studies["node_id"])
    second = tree.made("Détail", parent_id=studies["node_id"])
    milestone = tree.made("Réception", parent_id=studies["node_id"], task=MILESTONE)
    first = moved(tree, first, "started", occurred_on=JUNE_THIRD)
    second = moved(tree, second, "started", occurred_on=JUNE_THIRD)
    moved(tree, milestone, "completed", occurred_on="2026-06-05")
    moved(tree, second, "completed", occurred_on=JUNE_TENTH)
    assert tree.node(studies["node_id"])["task"]["progress"] == "started"
    answer = gesture(tree, first, "completed", occurred_on="2026-06-08")
    [above] = answer.json()["ancestors"]
    assert above["task"]["progress"] == "completed"
    assert (above["task"]["started_on"], above["task"]["completed_on"]) == (JUNE_THIRD, JUNE_TENTH)
    # Reopened, a subordinate takes the summary back to started, its completion cleared.
    answer = gesture(tree, answer.json()["nodes"][0], "started")
    [above] = answer.json()["ancestors"]
    assert (above["task"]["progress"], above["task"]["started_on"]) == ("started", JUNE_THIRD)
    assert above["task"]["completed_on"] is None


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_summary_of_milestones_returns_to_not_started_when_they_all_are_reopened(
    tree: Tree,
) -> None:
    studies = tree.made("Études")
    milestone = tree.made("Réception", parent_id=studies["node_id"], task=MILESTONE)
    done = moved(tree, milestone, "completed", occurred_on=JUNE_THIRD)
    summary = tree.node(studies["node_id"])["task"]
    assert (summary["progress"], summary["completed_on"]) == ("completed", JUNE_THIRD)
    moved(tree, done, "not_started")
    summary = tree.node(studies["node_id"])["task"]
    assert summary["progress"] == "not_started"
    assert summary["started_on"] is None
    assert summary["completed_on"] is None


@pytest.mark.requirement("WF-RAE-0040-A")
def test_the_finish_of_a_started_task_is_overdue_before_the_date_of_calculation(
    tree: Tree,
) -> None:
    # « signale les tâches démarrées dont la fin est antérieure à la date de calcul. » The plan
    # starts in the past; the gesture moves the date of calculation to the day it is made.
    late = tree.made("Câblage")
    long = tree.made("Études", task={"duration": {"value": "900", "unit": "d"}})
    late = moved(tree, late, "started")
    long = moved(tree, long, "started")
    assert late["task"]["finish_overdue"] is True
    assert long["task"]["finish_overdue"] is False
    assert tree.node(late["node_id"])["task"]["finish_overdue"] is True
    assert tree.node(long["node_id"])["task"]["finish_overdue"] is False
    not_started = tree.made("Revue")
    assert not_started["task"]["finish_overdue"] is False
    overdue = tree.items("?finish_overdue=true")
    assert [item["node_id"] for item in overdue] == [late["node_id"]]
    done = moved(tree, late, "completed")
    assert done["task"]["finish_overdue"] is False
    assert tree.items("?finish_overdue=true") == []


# --- The conditions of the project, of the revision, of the node ---------------------------------


@pytest.mark.requirement("WF-RAE-0040-A")
def test_a_gesture_is_an_entry_of_the_remaining_and_asks_the_project_to_be_in_progress(
    tree: Tree, stage: Scene
) -> None:
    node = tree.made("Câblage")
    milestone = tree.made("Réception", task=MILESTONE)
    for state in ("created", "pricing"):
        put_in_state(stage.owner, stage.project["project_id"], state)
        assert missing(gesture(tree, node, "started")) == "project_in_progress"
        assert missing(gesture(tree, milestone, "completed")) == "project_in_progress"
        # The condition of the gesture comes first.
        assert missing(gesture(tree, node, "completed")) == "task_is_milestone"
        assert missing(gesture(tree, milestone, "started")) == "task_not_milestone"
    assert tree.node(node["node_id"])["task"]["progress"] == "not_started"
    put_in_state(stage.owner, stage.project["project_id"], IN_PROGRESS)
    assert moved(tree, node, "started")["task"]["progress"] == "started"


@pytest.mark.requirement("WF-RAE-0040-A")
def test_the_project_in_progress_is_asked_of_a_gesture_on_the_main_structure_alone(
    tree: Tree, stage: Scene, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only the main structure has a remaining to commit (WF-RAE-0040): the phase of the project is
    # judged by the rule of its commands (``phase_conditions``), nothing on another structure
    # (#2494). No other structure exists before EP-08: the main one is read as another.
    node = tree.made("Câblage")
    put_in_state(stage.owner, stage.project["project_id"], "created")
    assert missing(gesture(tree, node, "started")) == "project_in_progress"
    real = writing.structure_facts

    def another(*args: Any, **kwargs: Any) -> Any:
        return replace(real(*args, **kwargs), is_main=False)

    monkeypatch.setattr(writing, "structure_facts", another)
    assert missing(gesture(tree, node, "completed")) == "task_is_milestone"
    assert moved(tree, node, "started")["task"]["progress"] == "started"


@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_gesture_while_a_background_task_runs_is_refused_after_the_other_conditions(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    node = tree.made("Câblage")
    milestone = tree.made("Réception", task=MILESTONE)
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    assert missing(gesture(tree, node, "started")) == "no_background_task_running"
    assert missing(gesture(tree, node, "completed")) == "task_is_milestone"
    assert missing(gesture(tree, milestone, "started")) == "task_not_milestone"
    put_in_state(stage.owner, stage.project["project_id"], "created")
    assert missing(gesture(tree, node, "started")) == "project_in_progress"
    status, code, _ = refusal(gesture(tree, {**node, "lock_version": 9}, "started"))
    assert (status, code) == (412, "STALE_LOCK_VERSION")


@pytest.mark.requirement("WF-IHM-0090-A")
def test_a_project_not_in_progress_is_named_before_the_background_task_that_marks_a_revision(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    # Both conditions lack (the order of the contract: the project, then the task of the
    # background): the refusal of the revision is judged on the tree first and names the project.
    node = tree.made("Câblage")
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    assert missing(gesture(tree, node, "started")) == "no_background_task_running"
    put_in_state(stage.owner, stage.project["project_id"], "created")
    assert missing(gesture(tree, node, "started")) == "project_in_progress"


@pytest.mark.requirement("WF-CYC-0100-A")
def test_a_marked_revision_and_a_terminal_project_refuse_a_gesture(
    tree: Tree, stage: Scene
) -> None:
    node = tree.made("Câblage")
    studies = tree.made("Études")
    tree.made("Détail", parent_id=studies["node_id"])
    summary = tree.node(studies["node_id"])
    mark(stage, tree.revision)
    assert missing(gesture(tree, node, "started")) == "revision_draft"
    assert missing(gesture(tree, node, "completed")) == "task_is_milestone"
    # The gesture is judged on the tree first: the order of the contract holds on a marked revision.
    status, code, _ = refusal(gesture(tree, {**node, "lock_version": 9}, "started"))
    assert (status, code) == (412, "STALE_LOCK_VERSION")
    assert refusal(gesture(tree, summary, "started"))[:2] == (422, "SUMMARY_TASK_DERIVED")
    assert refusal(gesture(tree, {"node_id": str(uuid4()), "lock_version": 1}, "started"))[:2] == (
        404,
        "NOT_FOUND",
    )
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    assert missing(gesture(tree, node, "started")) == "project_not_terminal"
    assert refusal(gesture(tree, summary, "started"))[:2] == (422, "SUMMARY_TASK_DERIVED")
    assert tree.node(node["node_id"])["task"]["progress"] == "not_started"


@pytest.mark.requirement("WF-DAT-0150-A")
def test_a_gesture_at_a_stale_counter_is_refused_and_writes_nothing(tree: Tree) -> None:
    node = tree.made("Câblage")
    moved(tree, node, "started", occurred_on=JUNE_THIRD)
    answer = gesture(tree, node, "started", occurred_on=JUNE_TENTH)
    assert refusal(answer) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    assert tree.node(node["node_id"])["task"]["started_on"] == JUNE_THIRD


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_node_the_structure_does_not_hold_or_that_is_no_task_is_not_found(
    tree: Tree, stage: Scene
) -> None:
    node = tree.made("Câblage")
    kept = line(stage, tree, node)
    for unknown in (uuid4(), kept):
        answer = gesture(tree, {"node_id": str(unknown), "lock_version": 1}, "started")
        assert refusal(answer) == (404, "NOT_FOUND", {})
    moved_path = tree.path.replace(tree.revision["revision_id"], str(uuid4()))
    answer = tree.api.put(
        f"{moved_path}/nodes/{node['node_id']}/progress",
        headers=stage.manager.headers,
        json={"progress": "started", "lock_version": 1},
    )
    assert answer.status_code == 404, answer.text


# --- The rights, the history, two gestures at once ----------------------------------------------


@pytest.mark.requirement("WF-ADM-0110-A")
def test_the_remaining_to_commit_is_written_by_a_contributor_who_may_write_it(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    node = tree.made("Câblage")
    reading = person(stage.database, realm, READ, "planning.read")
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    assert refusal(gesture(tree, node, "started", reading)) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": WRITE},
    )
    blind = person(stage.database, realm, WRITE, CHANGE)
    contribute(stage.database, stage.project["project_id"], blind, "contributor")
    assert refusal(gesture(tree, node, "started", blind))[:2] == (404, "NOT_FOUND")
    seeing = person(stage.database, realm, READ, WRITE, "all_projects_read")
    assert refusal(gesture(tree, node, "started", seeing))[:2] == (403, "NOT_CONTRIBUTOR")
    assert gesture(tree, node, "started", stage.reader).status_code == 403
    assert refusal(gesture(tree, node, "started", stage.outsider))[:2] == (404, "NOT_FOUND")
    assert gesture(tree, node, "started", stage.participant).status_code == 200


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_gesture_keeps_its_entry_of_the_history_with_the_node_before_and_after(
    tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    writer = signed_in(stage, realm)
    node = tree.made("Câblage")
    started = moved(tree, node, "started", who=writer, occurred_on=JUNE_THIRD)
    [entry] = entries(stage)
    assert (entry.kind, entry.rank) == ("progress", 1)
    assert entry.node_ids == [UUID(node["node_id"])]
    [before], [after] = entry.before, entry.after
    assert before["rows"]["task"]["progress"] == "not_started"
    assert after["rows"]["task"]["progress"] == "started"
    assert after["rows"]["task"]["started_on"] == JUNE_THIRD
    assert (before["lock_version"], after["lock_version"]) == (1, started["lock_version"])
    # A refused gesture keeps nothing.
    assert gesture(tree, started, "not_started", writer).status_code == 409
    assert len(entries(stage)) == 1


@pytest.mark.requirement("WF-DEV-0050-A")
def test_two_gestures_at_once_on_a_task_are_written_one_after_the_other(tree: Tree) -> None:
    node = tree.made("Câblage")
    with ThreadPoolExecutor(2) as pool:
        pending = [
            pool.submit(gesture, tree, node, "started", occurred_on=day)
            for day in (JUNE_THIRD, JUNE_TENTH)
        ]
        answers = [each.result() for each in pending]
    assert sorted(answer.status_code for answer in answers) == [200, 412]
    [won] = [answer for answer in answers if answer.status_code == 200]
    assert (
        tree.node(node["node_id"])["task"]["started_on"]
        == won.json()["nodes"][0]["task"]["started_on"]
    )
    assert tree.node(node["node_id"])["lock_version"] == node["lock_version"] + 1


# --- The witness ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0130-A")
def test_the_state_of_the_witness_is_loaded_at_the_instant_it_imposes(
    tree: Tree, stage: Scene
) -> None:
    node = tree.made("Câblage")
    milestone = tree.made("Réception", task=MILESTONE)
    studies = tree.made("Études")
    tree.made("Détail", parent_id=studies["node_id"])
    at = utc_now()
    act = Act(None, at)
    project_id = UUID(stage.project["project_id"])
    third, tenth = date(2026, 6, 3), date(2026, 6, 10)
    with stage.database.transaction() as session:
        load_progress(
            session, project_id, ProgressLoad(UUID(node["node_id"]), "completed", third, tenth), act
        )
        load_progress(
            session,
            project_id,
            ProgressLoad(UUID(milestone["node_id"]), "completed", tenth, tenth),
            act,
        )
    read = {item["node_id"]: item for item in tree.items()}
    assert read[node["node_id"]]["task"]["completed_on"] == tenth.isoformat()
    assert read[node["node_id"]]["lock_version"] == node["lock_version"] + 1
    assert read[milestone["node_id"]]["task"]["started_on"] == tenth.isoformat()
    with stage.database.transaction() as session:
        updated = session.scalar(select(Node.updated_at).where(Node.id == UUID(node["node_id"])))
    assert updated == at


@pytest.mark.requirement("WF-PLA-0130-A")
def test_a_state_of_the_witness_that_contradicts_its_dates_or_its_task_is_refused(
    tree: Tree, stage: Scene
) -> None:
    node = tree.made("Câblage")
    milestone = tree.made("Réception", task=MILESTONE)
    studies = tree.made("Études")
    tree.made("Détail", parent_id=studies["node_id"])
    project_id = UUID(stage.project["project_id"])
    day, other = date(2026, 6, 3), date(2026, 6, 10)
    wrong = (
        ProgressLoad(UUID(node["node_id"]), "started", None, None),
        ProgressLoad(UUID(node["node_id"]), "not_started", day, None),
        ProgressLoad(UUID(node["node_id"]), "completed", day, None),
        ProgressLoad(UUID(node["node_id"]), "started", day, other),
        ProgressLoad(UUID(node["node_id"]), "finished", day, None),
        ProgressLoad(UUID(milestone["node_id"]), "started", day, None),
        ProgressLoad(UUID(milestone["node_id"]), "completed", day, other),
        ProgressLoad(UUID(studies["node_id"]), "started", day, None),
    )
    for load in wrong:
        with (
            pytest.raises(UnprocessableError) as refused,
            stage.database.transaction() as session,
        ):
            load_progress(session, project_id, load, Act(None, utc_now()))
        assert refused.value.fields
    with pytest.raises(NotFoundError), stage.database.transaction() as session:
        load_progress(
            session, project_id, ProgressLoad(uuid4(), "started", day, None), Act(None, utc_now())
        )
    assert all(item["task"]["progress"] == "not_started" for item in tree.items())
