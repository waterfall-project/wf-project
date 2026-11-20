# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the trial of the chart holds of services that keep no state (US-2820)."""

import json
from typing import TYPE_CHECKING, Any

import pytest

from wftools import chartstateless
from wftools.chartstateless import Stateless
from wftools.production import ProductionError
from wftools.restoration_trial import Clock

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = [pytest.mark.requirement("WF-ARC-0080-A"), pytest.mark.story("US-2820")]

PROJECT = "6d5f3b0e-0d5d-4f41-9a55-6b0d6d6a2c11"
REVISION = "0b6a1e8c-3a0c-4e0b-9d3c-1c0b7f0d2a52"
USER = "3f1c9d52-0c4e-4a43-8f55-0b7f1e5a8c70"
TASK = "5c1a7a1e-8d3e-4c3a-bb0e-4d8c8f6a9e01"
LISTED = {"project_id": PROJECT, "label": "Essai", "lock_version": 0}


class Platform:
    """A cluster that answers what the trial asks of it, and remembers what it was asked."""

    def __init__(self, workers: int = 2, **changes: Any) -> None:
        self.changed = False  # the revision is no longer a draft when the worker dies
        self.ends = "succeeded|2"  # how the task ends
        self.snapshot_changes = False  # a table is written when the worker dies
        self.resumed_by = "waterfall-worker-b"  # the pod whose logs say it took the task again
        self.marks = "1"  # the inscriptions of the marking
        self.lock_taken = True
        self.held = True  # a marking waits on the lock
        self.reference = False  # the reference holds a labour type and a department
        self.calendars = [{"calendar_id": "k1", "is_active": True}]
        self.calls: list[tuple[str, str]] = []
        self.snapshots = 0
        for name, value in changes.items():
            assert hasattr(self, name), name
            setattr(self, name, value)
        self.pods = {
            "api": "pod/waterfall-api-1\npod/waterfall-api-2\npod/waterfall-api-3\n",
            "worker": "".join(f"pod/waterfall-worker-{each}\n" for each in "ab"[:workers]),
        }
        self.asked: list[list[str]] = []
        self.stopped = 0
        self.tasks = 0
        self.revisions = 0
        self.locks = 0
        self.given: dict[str, Any] = {}

    def read(self, command: list[str]) -> tuple[int, str]:
        self.asked.append(command)
        line = " ".join(command)
        if "--selector" in command:
            component = next(each for each in self.pods if f"component={each}" in line)
            return 0, self.pods[component]
        if "XPENDING" in command:
            return 0, "1-0\nwaterfall-worker-a\n31000\n1\n"
        if "logs" in command:
            return 0, self.logs(command[-1])
        if "wait" in command:
            return 0, ""
        return 0, self.sql(line)

    def logs(self, pod: str) -> str:
        """Give the logs of a pod: JSON lines, the one that took the task up again among them."""
        noise = json.dumps({"event": "worker.started"})
        if pod != f"pod/{self.resumed_by}":
            return f"{noise}\nnot json\n"
        again = {"event": "task.started", "task_id": TASK, "attempt": 2}
        return f"{noise}\n{json.dumps(again)}\n"

    def snapshot(self) -> str:
        self.snapshots += 1
        moved = self.snapshot_changes and self.snapshots > 1
        return f"audit_entry|a1\nproject|{'p2' if moved else 'p1'}\nrevision|r1\n"

    def lock(self) -> str:
        self.locks += 1
        return "0\n" if self.locks == 1 or not self.lock_taken else "1\n"

    def revision(self) -> str:
        self.revisions += 1
        if self.revisions > 1:
            return "marked|f|f\n"
        return "marked|t|t\n" if self.changed else "draft|t|t\n"

    def task(self) -> str:
        self.tasks += 1
        return "running|1\n" if self.tasks == 1 else f"{self.ends}\n"

    def sql(self, line: str) -> str:
        # The first mark found in the query answers it: a query that ends sessions, and counts them.
        answers = (
            ("query_to_xml", self.snapshot),
            ("FROM audit_entry WHERE action", lambda: f"{self.marks}\n"),
            ("pg_terminate_backend", lambda: "1\n"),
            ("wait_event_type", lambda: "1\n" if self.held else "0\n"),
            ("pg_locks", self.lock),
            ("FROM revision r", self.revision),
            ("FROM background_task", self.task),
        )
        return next((answer() for mark, answer in answers if mark in line), "")

    def ask(self, command: list[str], given: str) -> tuple[int, str]:
        self.asked.append(command)
        asked = json.loads(given)
        method, path = asked["method"], asked["path"]
        self.calls.append((method, path))
        if method == "PUT":
            self.given = asked["body"]
        status, body = self.answer(method, path)
        return 0, json.dumps({"status": status, "body": json.dumps(body)})

    def answer(self, method: str, path: str) -> tuple[int, Any]:
        roles: list[dict[str, Any]] = [
            {"access_role_id": "r0", "permissions": []},
            {"access_role_id": "r1", "permissions": ["project_create", "revision_mark"]},
            {
                "access_role_id": "r2",
                "permissions": ["cost_settings.write", "resource_settings.write"],
            },
        ]
        created = {
            ("POST", "/projects"): (201, {"project_id": PROJECT}),
            ("POST", "/reference/org-nodes"): (201, {"org_node_id": "n1"}),
            ("POST", "/reference/cost-types"): (201, {"cost_type_id": "t1"}),
            ("POST", "/reference/cost-categories"): (201, {"cost_category_id": "c1"}),
            ("POST", "/reference/resource-roles"): (201, {"resource_role_id": "q1"}),
            ("POST", f"/projects/{PROJECT}/revisions"): (201, {"revision_id": REVISION}),
            ("POST", f"/projects/{PROJECT}/revisions/{REVISION}/mark"): (202, {"task_id": TASK}),
        }
        reads: dict[str, Any] = {
            "/me": {"user_id": USER, "access_role_ids": ["r0"], "lock_version": 3},
            "/access-roles": roles,
            "/reference/cost-types": [
                {"cost_type_id": "t0", "kind": "non_labor", "is_active": True},
                *([{"cost_type_id": "t9", "kind": "labor", "is_active": True}] * self.reference),
            ],
            "/reference/org-nodes": [{"org_node_id": "n9", "is_active": True}] * self.reference,
            "/reference/calendars": {"items": self.calendars},
            f"/projects/{PROJECT}": LISTED,
        }
        if (method, path) in created:
            return created[method, path]
        if method == "PUT":
            return 200, {"user_id": USER}
        return 200, reads.get(path, {"revision_id": REVISION, "lock_version": 0})

    def start(self, command: list[str]) -> Callable[[], None]:
        self.asked.append(command)

        def stop() -> None:
            self.stopped += 1

        return stop

    def trial(self) -> Stateless:
        # The time moves by the pauses alone: a wait that is never answered runs out.
        time = [0.0]

        def pause(seconds: float) -> None:
            time[0] += seconds

        clock = Clock(now=lambda: time[0], pause=pause)
        return Stateless(["kubectl"], self.read, self.ask, self.start, clock)


def test_each_instance_of_the_api_is_asked_in_its_own_pod_and_answers_the_same() -> None:
    platform = Platform()
    project, revision = platform.trial().hold_the_same_answer("token")
    assert (project, revision) == (PROJECT, REVISION)
    assert platform.given == {"access_role_ids": ["r0", "r1", "r2"], "lock_version": 3}
    listed = [
        command[command.index("exec") + 2]
        for command in platform.asked
        if "exec" in command and "python" in command
    ]
    assert listed[-3:] == ["pod/waterfall-api-1", "pod/waterfall-api-2", "pod/waterfall-api-3"]


def test_instances_that_answer_otherwise_or_not_at_all_are_refused() -> None:
    same: dict[str, tuple[int, Any]] = dict.fromkeys(("a", "b"), (200, LISTED))
    chartstateless.check_same_answers(same, PROJECT)
    other = {"a": (200, LISTED), "b": (200, {**LISTED, "lock_version": 2})}
    with pytest.raises(ProductionError, match="answered otherwise"):
        chartstateless.check_same_answers(other, PROJECT)
    with pytest.raises(ProductionError, match="answered 503"):
        chartstateless.check_same_answers({"a": (200, LISTED), "b": (503, {})}, PROJECT)
    with pytest.raises(ProductionError, match="does not read the project"):
        chartstateless.check_same_answers(
            {"a": (200, {"project_id": "another"}), "b": (200, LISTED)}, PROJECT
        )
    with pytest.raises(ProductionError, match="two at least"):
        chartstateless.check_same_answers({"a": (200, LISTED)}, PROJECT)


def test_a_worker_killed_in_a_marking_leaves_the_database_and_another_marks() -> None:
    platform = Platform()
    platform.trial().hold("token")
    killed = [command for command in platform.asked if "delete" in command]
    assert [command[-3:] for command in killed] == [
        ["pod/waterfall-worker-a", "--grace-period=0", "--force"]
    ]
    # The pod is awaited gone before the sessions it leaves are ended.
    steps = [" ".join(command) for command in platform.asked]
    gone = next(i for i, step in enumerate(steps) if "--for=delete pod/waterfall-worker-a" in step)
    ended = next(
        i for i, step in enumerate(steps) if "wait_event_type" in step and "terminate" in step
    )
    assert next(i for i, step in enumerate(steps) if "--grace-period=0" in step) < gone < ended
    assert platform.stopped == 1
    released = [" ".join(command) for command in platform.asked if "pg_locks" in " ".join(command)]
    assert any("pg_terminate_backend" in command for command in released)


def test_a_marking_that_changed_the_database_when_its_worker_died_is_refused_and_unlocked() -> None:
    platform = Platform(changed=True)
    with pytest.raises(ProductionError, match="changed the database"):
        platform.trial().hold("token")
    assert platform.stopped == 1


def test_a_marking_that_wrote_a_table_before_its_worker_died_is_refused_by_the_snapshot() -> None:
    platform = Platform(snapshot_changes=True)
    with pytest.raises(ProductionError, match=r"changed the tables \['project'\]"):
        platform.trial().hold("token")
    assert platform.stopped == 1


def test_the_lock_is_on_the_last_write_of_the_marking_not_the_first() -> None:
    assert "audit_entry" in chartstateless.LOCK
    assert "revision IN" not in chartstateless.LOCK
    # What waits is the inscription of the journal, as a worker that is held by the lock.
    assert "INSERT INTO audit_entry" in chartstateless.WAITING


def test_a_pod_the_deployment_made_in_place_of_the_killed_one_did_not_take_over() -> None:
    platform = Platform(resumed_by="waterfall-worker-c")
    with pytest.raises(ProductionError, match=r"none of .* took up the task"):
        platform.trial().hold("token")
    assert platform.stopped == 1


def test_the_worker_that_took_the_task_up_again_is_named_by_its_logs() -> None:
    logs = "\n".join(
        [
            "not json",
            json.dumps(["a", "list"]),
            json.dumps({"event": "task.started", "task_id": TASK, "attempt": 1}),
            json.dumps({"event": "task.started", "task_id": "another", "attempt": 2}),
            json.dumps({"event": "task.succeeded", "task_id": TASK, "attempt": 2}),
        ]
    )
    assert not chartstateless.started_again(logs, TASK)
    again = json.dumps({"event": "task.started", "task_id": TASK, "attempt": 2})
    assert chartstateless.started_again(f"{logs}\n{again}", TASK)


def test_a_marking_inscribed_twice_or_not_at_all_is_refused() -> None:
    chartstateless.check_marked_once("1\n")
    for count in ("0", "2"):
        with pytest.raises(ProductionError, match="not one"):
            chartstateless.check_marked_once(count)
    with pytest.raises(ProductionError, match="not one"):
        Platform(marks="2").trial().hold("token")


def test_a_lock_that_is_never_taken_or_a_worker_never_held_runs_out_of_patience() -> None:
    with pytest.raises(ProductionError, match="lock of the table of the journal was not taken"):
        Platform(lock_taken=False).trial().hold("token")
    platform = Platform(held=False)
    with pytest.raises(ProductionError, match="no worker is held in a marking"):
        platform.trial().hold("token")
    assert platform.stopped == 1


def test_a_task_that_the_other_worker_did_not_take_again_is_refused() -> None:
    with pytest.raises(ProductionError, match="not 'succeeded"):
        Platform(ends="failed|2").trial().hold("token")


def test_the_task_must_have_been_attempted_once_and_not_ended() -> None:
    chartstateless.check_attempted_once("running|1\n")
    for row in ("succeeded|1", "running|2", "failed|1"):
        with pytest.raises(ProductionError, match="one attempt, not ended"):
            chartstateless.check_attempted_once(row)


def test_the_consumers_of_the_pending_entries_are_read_four_lines_an_entry() -> None:
    output = "1-0\nworker-a\n31000\n1\n2-0\nworker-b\n12\n3\n"
    assert chartstateless.pending_consumers(output) == {"1-0": "worker-a", "2-0": "worker-b"}
    assert chartstateless.pending_consumers("") == {}


def test_a_query_takes_an_identifier_that_is_a_uuid_alone() -> None:
    assert chartstateless.asked("WHERE id = :id", PROJECT) == f"WHERE id = '{PROJECT}'"
    with pytest.raises(ValueError, match="UUID"):
        chartstateless.asked("WHERE id = :id", "x'; DROP TABLE project; --")


def test_a_chart_with_one_worker_has_none_to_take_the_task_again() -> None:
    with pytest.raises(ProductionError, match="fewer than two"):
        Platform(workers=1).trial().hold("token")


def test_an_object_is_found_among_those_a_list_or_its_items_hold() -> None:
    items = [{"id": "a", "kind": "x"}, {"id": "b", "kind": "y"}]
    for body in (items, {"items": items}):
        assert chartstateless.found(body, "id") == "a"
        assert chartstateless.found(body, "id", {"kind": "y"}) == "b"
        assert chartstateless.found(body, "id", {"kind": "z"}) is None
    nested = {"children": [{"id": "c", "kind": "y"}], "items": [{"kind": "y"}]}
    assert chartstateless.found(nested, "id", {"kind": "y"}) is None
    assert chartstateless.found("not a list", "id") is None


def test_the_reference_is_made_from_nothing_and_used_when_it_exists() -> None:
    new = Platform()
    new.trial().make_the_reference(new.trial().api_on("pod/x"), "token")
    assert ("POST", "/reference/cost-types") in new.calls
    assert ("POST", "/reference/org-nodes") in new.calls
    held = Platform(reference=True)
    held.trial().make_the_reference(held.trial().api_on("pod/x"), "token")
    assert ("POST", "/reference/cost-types") not in held.calls
    assert ("POST", "/reference/org-nodes") not in held.calls
    assert ("POST", "/reference/resource-roles") in held.calls
    none = Platform(calendars=[])
    with pytest.raises(ProductionError, match="no active calendar"):
        none.trial().make_the_reference(none.trial().api_on("pod/x"), "token")
