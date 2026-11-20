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

    def __init__(
        self, *, changed: bool = False, ends: str = "succeeded|2", workers: int = 2
    ) -> None:
        self.changed = changed
        self.ends = ends
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
        return 0, self.sql(line)

    def sql(self, line: str) -> str:
        if "pg_terminate_backend" in line or "wait_event_type" in line:
            return "1\n"
        if "pg_locks" in line:
            self.locks += 1
            return "0\n" if self.locks == 1 else "1\n"
        if "FROM revision r" in line:
            self.revisions += 1
            if self.revisions > 1:
                return "marked|f|f\n"
            return "marked|t|t\n" if self.changed else "draft|t|t\n"
        if "FROM background_task" in line:
            self.tasks += 1
            return "running|1\n" if self.tasks == 1 else f"{self.ends}\n"
        return ""

    def ask(self, command: list[str], given: str) -> tuple[int, str]:
        self.asked.append(command)
        asked = json.loads(given)
        method, path = asked["method"], asked["path"]
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
            ],
            "/reference/org-nodes": [],
            "/reference/calendars": {"items": [{"calendar_id": "k1", "is_active": True}]},
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
        clock = Clock(now=lambda: 0.0, pause=lambda _seconds: None)
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
    assert platform.stopped == 1
    released = [" ".join(command) for command in platform.asked if "pg_locks" in " ".join(command)]
    assert any("pg_terminate_backend" in command for command in released)


def test_a_marking_that_changed_the_database_when_its_worker_died_is_refused_and_unlocked() -> None:
    platform = Platform(changed=True)
    with pytest.raises(ProductionError, match="changed the database"):
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


def test_an_object_is_found_among_those_a_body_lists_or_nests() -> None:
    body = {"items": [{"id": "a", "kind": "x"}, {"children": [{"id": "b", "kind": "y"}]}]}
    assert chartstateless.found(body, "id") == "a"
    assert chartstateless.found(body, "id", {"kind": "y"}) == "b"
    with pytest.raises(ProductionError, match="no id"):
        chartstateless.found(body, "id", {"kind": "z"})
