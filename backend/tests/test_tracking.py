# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The inscriptions of the tasks to the timelines and to the time/time tracking (US-1400/L2).

``setNodeTracking`` on the main structure of a revision a project's manager opened, every answer
checked against the contract: the inscriptions of a task replaced, rendered by ``listNodes`` with
``task.tracking`` and its ``timeline_id`` filter, kept by lineage from a revision to the next; the
time/time tracking of the milestones alone; every refusal of the entries at once, nothing being
written; the state, the rights, the version read, the entry of the history; two writes at once.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from nodes_support import (
    CHANGE,
    CONSULT,
    SESSION,
    Tree,
    entries,
    faults,
    mark,
    opened,
    refusal,
    signed_in,
)
from projects_support import PROJECTS, Person, Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from sqlalchemy import delete, select, text
from support import WITNESS

from waterfall.core.planning.tables import Timeline, TrackingEntry

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Connection, Engine
    from support import ContractClient

    from waterfall.platform.database import Database

MILESTONE = {"duration": {"value": "0", "unit": "d"}}
TIME_TIME: dict[str, Any] = {"kind": "milestone_tracking"}
TIME_TIME_READ = {"kind": "milestone_tracking", "timeline_id": None}


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def tree(api: ContractClient, stage: Scene) -> Tree:
    """Give the main structure of the revision the manager opened on the project of the stage."""
    return Tree(api, stage, opened(api, stage))


def timeline(api: ContractClient, stage: Scene, label: str, project_id: str | None = None) -> str:
    """Create a timeline of a project (the one of the stage by default); give its identifier."""
    answer = api.post(
        f"{PROJECTS}/{project_id or stage.project['project_id']}/timelines",
        headers=stage.manager.headers,
        json={"label": label},
    )
    assert answer.status_code == 201, answer.text
    return answer.json()["timeline_id"]


def on(timeline_id: str) -> dict[str, Any]:
    """Write an entry that inscribes a task to a timeline."""
    return {"kind": "timeline", "timeline_id": timeline_id}


def track(
    tree: Tree, node: dict[str, Any], *sent: dict[str, Any], who: Person | None = None
) -> Any:
    """Replace the inscriptions of a task at the version read; give the answer."""
    body = {"entries": list(sent), "lock_version": node["lock_version"]}
    headers = (who or tree.stage.manager).headers
    return tree.api.put(f"{tree.path}/nodes/{node['node_id']}/tracking", headers=headers, json=body)


def tracked(tree: Tree, node: dict[str, Any], *sent: dict[str, Any]) -> dict[str, Any]:
    """Replace the inscriptions of a task that must be replaced; give the node written."""
    answer = track(tree, node, *sent)
    assert answer.status_code == 200, answer.text
    return answer.json()["nodes"][0]


def rows(stage: Scene) -> list[tuple[str, UUID | None]]:
    """Read the inscriptions the base holds: kind and timeline, in no order."""
    with stage.database.transaction() as session:
        found = session.execute(select(TrackingEntry.kind, TrackingEntry.timeline_id))
        return sorted(((each[0], each[1]) for each in found), key=str)


# --- Writing -----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0060-A")
def test_a_task_inscribed_appears_in_the_timeline_and_disappears_when_removed(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité de pilotage")
    study = tree.made("Études")
    other = tree.made("Revue")
    assert tree.items(f"?timeline_id={committee}") == []
    written = tracked(tree, study, on(committee))
    assert written["task"]["tracking"] == [on(committee)]
    assert written["lock_version"] == study["lock_version"] + 1
    assert tree.labels(f"?timeline_id={committee}") == ["Études"]
    assert tree.node(other["node_id"])["task"]["tracking"] == []
    # Removed: the entries sent are the inscriptions the task keeps, and none is sent.
    removed = tracked(tree, written)
    assert removed["task"]["tracking"] == []
    assert tree.items(f"?timeline_id={committee}") == []
    assert rows(stage) == []


@pytest.mark.requirement("WF-PLA-0060-A")
def test_the_entries_replace_the_inscriptions_and_an_entry_repeated_makes_only_one(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    first, second = timeline(api, stage, "Comité"), timeline(api, stage, "Client")
    node = tree.made("Livraison", task=MILESTONE)
    node = tracked(tree, node, on(first), on(first), TIME_TIME, TIME_TIME)
    assert node["task"]["tracking"] == [TIME_TIME_READ, on(first)]
    assert len(rows(stage)) == 2
    node = tracked(tree, node, on(second), on(first))
    # The time/time tracking is gone, the timeline kept, the other one added.
    ids = sorted(each["timeline_id"] for each in node["task"]["tracking"])
    assert ids == sorted([first, second])
    assert {kind for kind, _ in rows(stage)} == {"timeline"}
    assert len(rows(stage)) == 2


@pytest.mark.requirement("WF-PLA-0140-A")
def test_two_timelines_of_a_project_carry_distinct_selections(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee, client = timeline(api, stage, "Comité"), timeline(api, stage, "Client")
    study, review, delivery = tree.made("Études"), tree.made("Revue"), tree.made("Livraison")
    tracked(tree, study, on(committee))
    tracked(tree, review, on(committee), on(client))
    tracked(tree, delivery, on(client))
    assert tree.labels(f"?timeline_id={committee}") == ["Études", "Revue"]
    assert tree.labels(f"?timeline_id={client}") == ["Revue", "Livraison"]


@pytest.mark.requirement("WF-PLA-0140-A")
def test_the_selection_of_a_timeline_is_retrieved_in_the_revision_that_follows_by_the_lineage(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    study = tree.made("Études")
    tree.made("Revue")
    tracked(tree, study, on(committee))
    mark(stage, tree.revision)
    following = Tree(api, stage, opened(api, stage))
    # The task is another node of another revision, of the same lineage: the reading finds it.
    read = following.items(f"?timeline_id={committee}")
    assert [item["task"]["label"] for item in read] == ["Études"]
    assert read[0]["node_id"] != study["node_id"]
    assert read[0]["lineage_id"] == study["lineage_id"]
    assert read[0]["task"]["tracking"] == [on(committee)]
    # The marked revision reads the same, and the task that was not inscribed still is not.
    assert tree.labels(f"?timeline_id={committee}") == ["Études"]
    assert len(rows(stage)) == 1


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_deleted_takes_its_inscriptions_and_leaves_the_others(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee, client = timeline(api, stage, "Comité"), timeline(api, stage, "Client")
    node = tracked(tree, tree.made("Études"), on(committee), on(client))
    gone = api.delete(
        f"{PROJECTS}/{stage.project['project_id']}/timelines/{committee}",
        headers=stage.manager.headers,
    )
    assert gone.status_code == 204
    assert tree.node(node["node_id"])["task"]["tracking"] == [on(client)]
    assert tree.items(f"?timeline_id={committee}") == []


@pytest.mark.requirement("WF-PLA-0060-A")
def test_a_milestone_is_inscribed_to_the_time_time_tracking_and_to_a_timeline_together(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    milestone = tree.made("Réception", task=MILESTONE)
    written = tracked(tree, milestone, on(committee), TIME_TIME)
    assert written["task"]["is_milestone"] is True
    assert written["task"]["tracking"] == [TIME_TIME_READ, on(committee)]
    # The time/time tracking targets no timeline: no filter finds it.
    assert tree.labels(f"?timeline_id={uuid4()}") == []
    assert tree.labels(f"?timeline_id={committee}") == ["Réception"]
    assert [kind for kind, _ in rows(stage)] == ["milestone_tracking", "timeline"]


@pytest.mark.requirement("WF-PLA-0060-A")
def test_every_task_of_the_main_structure_states_the_inscription_in_its_editable_fields(
    tree: Tree,
) -> None:
    summary = tree.made("Études")
    tree.made("Détail", parent_id=summary["node_id"])
    milestone = tree.made("Réception", task=MILESTONE)
    for item in tree.items():
        assert item["editable_fields"][-1] == "task.tracking"
    # The written node says it too, and nothing else of the facet changed.
    written = tracked(tree, milestone)
    assert written["editable_fields"][-1] == "task.tracking"
    assert written["task"]["duration"] == {"value": "0", "unit": "d"}


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_retains_a_subtask_inscribed_without_its_ancestors(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    summary = tree.made("Études")
    detail = tree.made("Détail", parent_id=summary["node_id"])
    written = tracked(tree, detail, on(committee))
    # The summary is an ancestor of the written node, and is given back; the reading drops it.
    read = tree.items(f"?timeline_id={committee}")
    assert [item["task"]["label"] for item in read] == ["Détail"]
    assert read[0]["level"] == 2
    assert written["lock_version"] == detail["lock_version"] + 1
    assert tree.node(summary["node_id"])["task"]["tracking"] == []


# --- Refusals ----------------------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0060-A")
def test_the_time_time_tracking_of_a_task_that_is_no_milestone_is_refused_and_nothing_is_written(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    node = tree.made("Mise en service")
    answer = track(tree, node, on(committee), TIME_TIME)
    assert faults(answer) == [("/entries/1/kind", "MILESTONE_REQUIRED", {})]
    assert answer.json()["code"] == "VALIDATION_FAILED"
    assert rows(stage) == []
    assert tree.node(node["node_id"])["lock_version"] == node["lock_version"]
    # A summary task is no milestone either.
    summary = tree.made("Études")
    tree.made("Détail", parent_id=summary["node_id"], task=MILESTONE)
    refused = track(tree, tree.node(summary["node_id"]), TIME_TIME)
    assert faults(refused) == [("/entries/0/kind", "MILESTONE_REQUIRED", {})]


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_entry_without_a_timeline_is_refused_with_value_required(
    tree: Tree, stage: Scene
) -> None:
    node = tree.made("Études")
    answer = track(tree, node, {"kind": "timeline"})
    assert faults(answer) == [("/entries/0/timeline_id", "VALUE_REQUIRED", {})]
    null = track(tree, node, {"kind": "timeline", "timeline_id": None})
    assert faults(null) == [("/entries/0/timeline_id", "VALUE_REQUIRED", {})]
    assert rows(stage) == []


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_of_another_project_or_that_does_not_exist_is_refused_as_unknown(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    created = api.post(PROJECTS, headers=stage.manager.headers, json={"label": "Autre projet"})
    alien = timeline(api, stage, "Étrangère", created.json()["project_id"])
    mine = timeline(api, stage, "Comité")
    node = tree.made("Études")
    answer = track(tree, node, on(mine), on(alien), on(str(uuid4())))
    assert faults(answer) == [
        ("/entries/1/timeline_id", "UNKNOWN_TIMELINE", {}),
        ("/entries/2/timeline_id", "UNKNOWN_TIMELINE", {}),
    ]
    assert rows(stage) == []


@pytest.mark.requirement("WF-PLA-0060-A")
def test_the_time_time_tracking_refuses_a_timeline_it_does_not_target(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    milestone = tree.made("Réception", task=MILESTONE)
    answer = track(tree, milestone, {"kind": "milestone_tracking", "timeline_id": committee})
    assert faults(answer) == [("/entries/0/timeline_id", "FIELD_NOT_ACCEPTED", {})]
    assert rows(stage) == []
    # A null timeline is none sent.
    accepted = track(tree, milestone, {"kind": "milestone_tracking", "timeline_id": None})
    assert accepted.status_code == 200, accepted.text
    assert rows(stage) == [("milestone_tracking", None)]


@pytest.mark.requirement("WF-PLA-0060-A")
def test_every_fault_of_every_entry_is_named_at_once(tree: Tree, stage: Scene) -> None:
    node = tree.made("Mise en service")
    answer = track(
        tree,
        node,
        {"kind": "timeline"},
        {"kind": "milestone_tracking", "timeline_id": str(uuid4())},
    )
    assert [(pointer, code) for pointer, code, _ in faults(answer)] == [
        ("/entries/0/timeline_id", "VALUE_REQUIRED"),
        ("/entries/1/kind", "MILESTONE_REQUIRED"),
        ("/entries/1/timeline_id", "FIELD_NOT_ACCEPTED"),
    ]
    assert rows(stage) == []


@pytest.mark.requirement("WF-DAT-0150-A")
def test_a_stale_version_and_an_unknown_node_are_refused(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    node = tree.made("Études")
    tracked(tree, node, on(committee))
    stale = track(tree, node, on(committee))
    assert refusal(stale) == (412, "STALE_LOCK_VERSION", {"expected_lock_version": 2})
    unknown = track(tree, {"node_id": str(uuid4()), "lock_version": 1})
    assert refusal(unknown)[:2] == (404, "NOT_FOUND")
    assert len(rows(stage)) == 1


@pytest.mark.requirement("WF-DAT-0020-A")
def test_a_marked_revision_and_a_terminal_project_refuse_the_inscription(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    node = tree.made("Études")
    mark(stage, tree.revision)
    assert refusal(track(tree, node, on(committee))) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "revision_draft"},
    )
    put_in_state(stage.owner, stage.project["project_id"], "completed")
    assert refusal(track(tree, node, on(committee)))[2] == {
        "missing_condition": "project_not_terminal"
    }
    assert rows(stage) == []


@pytest.mark.requirement("WF-IHM-0090-A")
def test_an_inscription_while_a_background_task_runs_in_the_project_is_refused(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    node = tree.made("Études")
    path = f"{PROJECTS}/{stage.project['project_id']}/revisions/{tree.revision['revision_id']}"
    revision = api.get(path, headers=stage.manager.headers).json()
    asked = api.post(
        f"{path}/mark",
        headers=stage.manager.headers,
        json={"version_name": "v1.0", "lock_version": revision["lock_version"]},
    )
    assert asked.status_code == 202, asked.text
    assert refusal(track(tree, node, on(committee))) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "no_background_task_running"},
    )
    assert rows(stage) == []


@pytest.mark.requirement("WF-ADM-0110-A")
def test_a_reader_an_outsider_and_a_contributor_without_planning_write_do_not_write(
    api: ContractClient, tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    committee = timeline(api, stage, "Comité")
    node = tree.made("Études")
    reading = person(stage.database, realm, "project_settings.read", CONSULT)
    contribute(stage.database, stage.project["project_id"], reading, "contributor")
    assert refusal(track(tree, node, on(committee), who=reading)) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": CHANGE},
    )
    assert track(tree, node, on(committee), who=stage.reader).status_code == 403
    assert refusal(track(tree, node, on(committee), who=stage.outsider))[:2] == (404, "NOT_FOUND")
    assert rows(stage) == []
    assert track(tree, node, on(committee), who=stage.participant).status_code == 200


# --- History and concurrency -------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_inscription_is_kept_by_the_history_as_a_tracking_change_before_and_after(
    api: ContractClient, tree: Tree, stage: Scene, realm: TestRealm
) -> None:
    committee = timeline(api, stage, "Comité")
    writer = signed_in(stage, realm)
    node = tree.made("Études")
    answer = track(tree, node, on(committee), who=writer)
    assert answer.status_code == 200, answer.text
    (entry,) = entries(stage)
    assert (entry.kind, entry.user_account_id, entry.session_id) == (
        "tracking",
        writer.user_id,
        SESSION,
    )
    assert [each["rows"]["tracking"] for each in entry.before] == [[]]
    after = entry.after[0]["rows"]["tracking"]
    assert [(row["kind"], row["timeline_id"]) for row in after] == [("timeline", committee)]


@pytest.mark.requirement("WF-PLA-0140-A")
def test_two_writes_at_the_same_version_are_judged_one_after_the_other(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    first, second = timeline(api, stage, "Comité"), timeline(api, stage, "Client")
    node = tree.made("Études")
    with ThreadPoolExecutor(2) as pool:
        pending = [pool.submit(track, tree, node, on(each)) for each in (first, second)]
        answers = [each.result() for each in pending]
    assert sorted(answer.status_code for answer in answers) == [200, 412]
    assert len(rows(stage)) == 1


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_deleted_while_a_task_is_inscribed_to_it_leaves_no_orphan_inscription(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    node = tree.made("Études")

    def remove() -> int:
        path = f"{PROJECTS}/{stage.project['project_id']}/timelines/{committee}"
        return api.delete(path, headers=stage.manager.headers).status_code

    with ThreadPoolExecutor(2) as pool:
        writing = pool.submit(track, tree, node, on(committee))
        deleting = pool.submit(remove)
        answer, deleted = writing.result(), deleting.result()
    assert deleted == 204
    assert answer.status_code in (200, 422)
    with stage.database.transaction() as session:
        assert session.scalars(select(Timeline.id)).all() == []
    assert rows(stage) == []


def _wait_for_a_lock(stage: Scene, blocker: Connection, seconds: float = 10.0) -> None:
    """Wait until the request of the inscription waits for the lock that ``blocker`` holds.

    The backend counted is the one that ``blocker``, the connection of the deletion, blocks
    (``pg_blocking_pids``), not any backend of the base that waits for a lock (#2569): the text of
    a statement cannot name the request, the backend still showing the ``BEGIN`` the driver sent.
    """
    holder = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
    deadline = time.monotonic() + seconds
    with stage.owner.connect() as watcher:
        while time.monotonic() < deadline:
            waiting = watcher.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE wait_event_type = 'Lock' AND datname = current_database() "
                    "AND :holder = ANY(pg_blocking_pids(pid))"
                ),
                {"holder": holder},
            ).scalar_one()
            if waiting:
                return
            time.sleep(0.05)
    pytest.fail("the inscription never waited for the lock of the deletion")


@pytest.mark.requirement("WF-PLA-0140-A")
def test_a_timeline_that_goes_while_the_inscription_waits_is_refused_as_unknown(
    api: ContractClient, tree: Tree, stage: Scene
) -> None:
    committee = timeline(api, stage, "Comité")
    node = tree.made("Études")
    # The timeline is deleted, not yet committed: the judgement still finds it, and the key of the
    # inscription waits for the deletion to end, then refuses it.
    with stage.owner.connect() as connection:
        deletion = connection.begin()
        connection.execute(delete(Timeline).where(Timeline.id == UUID(committee)))
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(track, tree, node, on(committee))
            _wait_for_a_lock(stage, connection)
            deletion.commit()
            answer = pending.result()
    assert faults(answer) == [("/entries/0/timeline_id", "UNKNOWN_TIMELINE", {})]
    assert rows(stage) == []
    assert tree.node(node["node_id"])["lock_version"] == node["lock_version"]


@pytest.mark.requirement("WF-PLA-0060-A")
@pytest.mark.parametrize(
    ("body", "pointer"),
    [
        ({"entries": [{"kind": "unknown"}], "lock_version": 1}, "/entries/0/kind"),
        ({"entries": "timeline", "lock_version": 1}, "/entries"),
        ({"entries": []}, "/lock_version"),
    ],
    ids=["unknown-kind", "entries-not-a-list", "lock-version-absent"],
)
def test_a_malformed_body_is_refused_by_the_envelope_and_nothing_is_written(
    tree: Tree, stage: Scene, body: dict[str, Any], pointer: str
) -> None:
    node = tree.made("Études")
    answer = tree.api.put(
        f"{tree.path}/nodes/{node['node_id']}/tracking",
        headers=stage.manager.headers,
        json=body,
    )
    assert answer.status_code == 422, answer.text
    assert answer.json()["code"] == "VALIDATION_FAILED"
    assert [each["pointer"] for each in answer.json()["fields"]] == [pointer]
    assert rows(stage) == []
    assert tree.node(node["node_id"])["lock_version"] == node["lock_version"]


@pytest.mark.requirement("WF-PLA-0140-A")
def test_the_witness_is_loaded_with_its_timelines_and_the_inscriptions_of_its_tasks_by_lineage(
    witness_loaded: Database,
) -> None:
    described = json.loads((WITNESS / "witness_tasks.json").read_text(encoding="utf-8"))["value"]
    # The last revision that describes a lineage says what it keeps.
    expected: dict[str, set[tuple[str, str | None]]] = {}
    for task in sorted(described["tasks"], key=lambda each: each["revision"]):
        expected[task["lineage_id"]] = {
            (each["kind"], each["timeline_id"]) for each in task["inscriptions"]
        }
    with witness_loaded.transaction() as session:
        found = session.execute(
            select(TrackingEntry.lineage_id, TrackingEntry.kind, TrackingEntry.timeline_id)
        ).all()
        timelines = {str(each) for each in session.scalars(select(Timeline.id))}
    held: dict[str, set[tuple[str, str | None]]] = {}
    for lineage, kind, timeline_id in found:
        held.setdefault(str(lineage), set()).add(
            (kind, None if timeline_id is None else str(timeline_id))
        )
    inscribed = {lineage: entries for lineage, entries in expected.items() if entries}
    assert held == inscribed
    assert len(timelines) == 2
    assert {each for entries in held.values() for _, each in entries if each} == timelines
    assert any(kind == "milestone_tracking" for entries in held.values() for kind, _ in entries)
