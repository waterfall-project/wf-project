# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The chain cancels the runs the merge queue made stale, and only those (US-2800/L7, #5122)."""

from typing import Any

import pytest
import yaml

from wftools import REPOSITORY, queuecancel
from wftools.tracking import TrackingError

pytestmark = pytest.mark.story("US-2800")

BASE = "epic/EP-13"
MINE = f"gh-readonly-queue/{BASE}/pr-5112-aaa111"
MY_ID = 100


def run(
    identifier: int,
    ref: str,
    status: str = "queued",
    event: str = "merge_group",
) -> dict[str, object]:
    return {
        "databaseId": identifier,
        "headBranch": ref,
        "status": status,
        "event": event,
        "url": f"https://example.test/runs/{identifier}",
    }


def chosen(runs: list[dict[str, object]], in_queue: set[int] | None) -> list[object]:
    return [item["databaseId"] for item, _ in queuecancel.stale(runs, MINE, MY_ID, in_queue)]


def test_an_earlier_build_of_the_same_pull_request_is_cancelled() -> None:
    older = run(1, f"gh-readonly-queue/{BASE}/pr-5112-bbb222", "in_progress")
    assert chosen([older], {5112}) == [1]


def test_a_newer_build_of_the_same_pull_request_is_kept() -> None:
    newer = run(MY_ID + 100, f"gh-readonly-queue/{BASE}/pr-5112-bbb222")
    assert chosen([newer], {5112}) == []


def test_the_same_pull_request_on_the_same_sha_and_its_own_run_are_kept() -> None:
    same = run(2, MINE)
    own = run(MY_ID, MINE, "in_progress")
    assert chosen([same, own], {5112}) == []


def test_another_pull_request_still_in_the_queue_is_kept() -> None:
    assert chosen([run(3, f"gh-readonly-queue/{BASE}/pr-5082-ccc333")], {5112, 5082}) == []


def test_a_pull_request_that_left_the_queue_is_cancelled() -> None:
    gone = run(4, f"gh-readonly-queue/{BASE}/pr-4000-ddd444", "waiting")
    assert chosen([gone], {5112}) == [4]


def test_an_unreadable_queue_cancels_only_the_earlier_builds_of_the_pull_request() -> None:
    older = run(1, f"gh-readonly-queue/{BASE}/pr-5112-bbb222")
    gone = run(4, f"gh-readonly-queue/{BASE}/pr-4000-ddd444")
    assert chosen([older, gone], None) == [1]


def test_another_base_branch_is_kept() -> None:
    other = run(5, "gh-readonly-queue/epic/EP-11/pr-5112-eee555")
    assert chosen([other], {5112}) == []


@pytest.mark.parametrize("event", ["pull_request", "workflow_dispatch", "push"])
def test_a_run_of_another_event_is_kept(event: str) -> None:
    assert chosen([run(6, "gh-readonly-queue/epic/EP-13/pr-4000-fff666", event=event)], set()) == []
    assert chosen([run(7, "epic/EP-13", event=event)], set()) == []


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_a_finished_run_is_kept(status: str) -> None:
    assert chosen([run(8, f"gh-readonly-queue/{BASE}/pr-4000-ddd444", status)], {5112}) == []


@pytest.mark.parametrize("status", ["queued", "waiting", "pending", "requested", "in_progress"])
def test_every_waiting_or_running_status_is_cancelled(status: str) -> None:
    assert chosen([run(9, f"gh-readonly-queue/{BASE}/pr-4000-ddd444", status)], {5112}) == [9]


def test_a_current_ref_outside_the_queue_cancels_nothing() -> None:
    older = run(1, f"gh-readonly-queue/{BASE}/pr-5112-bbb222")
    assert queuecancel.stale([older], "epic/EP-13", MY_ID, {5112}) == []


def test_each_cancellation_is_written_to_the_log(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    older = run(1, f"gh-readonly-queue/{BASE}/pr-5112-bbb222")
    cancelled: list[str] = []
    monkeypatch.setattr(queuecancel, "list_runs", lambda: [older, run(MY_ID, MINE)])

    def queued(_repository: str, _base: str) -> set[int]:
        return {5112}

    def cancel(arguments: list[str]) -> str:
        cancelled.append(arguments[-1])
        return ""

    monkeypatch.setattr(queuecancel, "queued_numbers", queued)
    monkeypatch.setattr(queuecancel, "gh", cancel)
    monkeypatch.setenv("GITHUB_REF_NAME", MINE)
    monkeypatch.setenv("GITHUB_RUN_ID", str(MY_ID))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/name")
    assert queuecancel.main() == 0
    assert cancelled == ["1"]
    printed = capsys.readouterr().out
    assert "https://example.test/runs/1" in printed
    assert "#5112" in printed
    assert "pr-5112-bbb222" in printed


def _environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_REF_NAME", MINE)
    monkeypatch.setenv("GITHUB_RUN_ID", str(MY_ID))
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/name")


def test_the_runs_are_read_before_the_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []

    def runs() -> list[dict[str, object]]:
        order.append("runs")
        return []

    def queue(_repository: str, _base: str) -> set[int]:
        order.append("queue")
        return set()

    monkeypatch.setattr(queuecancel, "list_runs", runs)
    monkeypatch.setattr(queuecancel, "queued_numbers", queue)
    _environment(monkeypatch)
    assert queuecancel.main() == 0
    assert order == ["runs", "queue"]


def test_a_pull_request_that_left_the_queue_is_cancelled_even_if_newer() -> None:
    gone = run(MY_ID + 50, f"gh-readonly-queue/{BASE}/pr-4000-ddd444")
    assert chosen([gone], {5112}) == [MY_ID + 50]


def test_a_truncated_queue_is_unread(monkeypatch: pytest.MonkeyPatch) -> None:
    nodes = ",".join(f'{{"pullRequest":{{"number":{n}}}}}' for n in range(100))
    answer = (
        '{"data":{"repository":{"mergeQueue":{"entries":{"totalCount":150,"nodes":['
        + nodes
        + "]}}}}}"
    )

    def read(_arguments: list[str]) -> str:
        return answer

    monkeypatch.setattr(queuecancel, "gh", read)
    assert queuecancel.queued_numbers("owner/name", BASE) is None


def test_unreadable_runs_are_a_warning_not_a_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refuse() -> list[dict[str, object]]:
        message = "boom"
        raise TrackingError(message)

    monkeypatch.setattr(queuecancel, "list_runs", refuse)
    _environment(monkeypatch)
    assert queuecancel.main() == 0
    assert "::warning::" in capsys.readouterr().out


def test_a_run_that_has_just_finished_is_a_warning_not_a_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    older = run(1, f"gh-readonly-queue/{BASE}/pr-5112-bbb222")

    def conflict(_arguments: list[str]) -> str:
        message = "409"
        raise TrackingError(message)

    monkeypatch.setattr(queuecancel, "list_runs", lambda: [older])

    def queued(_repository: str, _base: str) -> set[int]:
        return {5112}

    monkeypatch.setattr(queuecancel, "queued_numbers", queued)
    monkeypatch.setattr(queuecancel, "gh", conflict)
    _environment(monkeypatch)
    assert queuecancel.main() == 0
    assert "::warning::" in capsys.readouterr().out


def test_an_error_of_the_graphql_api_leaves_the_queue_unread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(_arguments: list[str]) -> str:
        message = "forbidden"
        raise TrackingError(message)

    monkeypatch.setattr(queuecancel, "gh", refuse)
    assert queuecancel.queued_numbers("owner/name", BASE) is None


def test_the_queue_is_read_from_the_entries_of_the_graphql_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answer = (
        '{"data":{"repository":{"mergeQueue":{"entries":{"totalCount":2,"nodes":'
        '[{"pullRequest":{"number":5112}},{"pullRequest":{"number":5082}}]}}}}}'
    )

    def read(_arguments: list[str]) -> str:
        return answer

    monkeypatch.setattr(queuecancel, "gh", read)
    assert queuecancel.queued_numbers("owner/name", BASE) == {5112, 5082}


def test_only_the_cancelling_job_of_the_chain_may_write_actions() -> None:
    chain: dict[str, Any] = yaml.safe_load(
        (REPOSITORY / ".github" / "workflows" / "ci.yml").read_text("utf-8")
    )
    assert chain["permissions"] == {"contents": "read"}
    writers = [
        name for name, job in chain["jobs"].items() if "actions" in job.get("permissions", {})
    ]
    assert writers == ["cancel-stale"]
    job = chain["jobs"]["cancel-stale"]
    assert job["permissions"]["actions"] == "write"
    assert job["if"] == "github.event_name == 'merge_group'"


def test_no_job_of_the_chain_waits_for_the_cancelling_job() -> None:
    jobs: dict[str, Any] = yaml.safe_load(
        (REPOSITORY / ".github" / "workflows" / "ci.yml").read_text("utf-8")
    )["jobs"]
    for name, job in jobs.items():
        needs = job.get("needs", [])
        assert "cancel-stale" not in ([needs] if isinstance(needs, str) else needs), name
