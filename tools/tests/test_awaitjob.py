# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the wait for a job of the run (US-1910); the chain is in test_frontimage.py."""

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, awaitjob

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

ENVIRONMENT = {"GITHUB_REPOSITORY": "waterfall-project/wf-project", "GITHUB_RUN_ID": "42"}


def job(name: str, status: str = "completed", conclusion: str | None = "success") -> dict[str, Any]:
    """Return a job as the API lists it."""
    return {"name": name, "status": status, "conclusion": conclusion}


class Run:
    """A run whose jobs ``gh`` answers, one listing a reading, and a clock the pauses move."""

    def __init__(self, *readings: Sequence[dict[str, Any]] | Exception) -> None:
        self.readings = list(readings)
        self.calls: list[list[str]] = []
        self.now = 0.0

    def call(self, arguments: list[str]) -> str:
        self.calls.append(arguments)
        reading = self.readings.pop(0) if len(self.readings) > 1 else self.readings[0]
        if isinstance(reading, Exception):
            raise reading
        return json.dumps({"total_count": len(reading), "jobs": list(reading)})

    def wait(self, seconds: float) -> None:
        self.now += seconds

    def world(self) -> awaitjob.World:
        return awaitjob.World(call=self.call, wait=self.wait, clock=lambda: self.now)

    def await_build(self, within: float = awaitjob.WITHIN) -> float:
        return awaitjob.await_job("front-build", within, ENVIRONMENT, self.world())


# The tool.


def test_a_job_that_succeeded_is_not_waited_for() -> None:
    run = Run([job("mirror"), job("front-build")])
    assert run.await_build() == 0
    (called,) = run.calls
    assert called == [
        "api",
        "repos/waterfall-project/wf-project/actions/runs/42/jobs?filter=latest&per_page=100&page=1",
    ]


def test_a_job_queued_or_in_progress_is_waited_for_until_it_succeeds() -> None:
    run = Run(
        [job("front-build", "queued", None)],
        [job("front-build", "in_progress", None)],
        [job("front-build")],
    )
    assert run.await_build() == 2 * awaitjob.POLL
    assert len(run.calls) == 3


def test_a_job_not_created_yet_is_waited_for() -> None:
    run = Run([job("changes")], [job("changes"), job("front-build")])
    assert run.await_build() == awaitjob.POLL


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "timed_out"])
def test_a_job_that_ended_otherwise_fails_the_wait_naming_it(conclusion: str) -> None:
    run = Run([job("front-build", conclusion=conclusion)])
    with pytest.raises(awaitjob.AwaitError, match=f"front-build ended {conclusion}"):
        run.await_build()


def test_a_job_that_never_ends_fails_the_wait_at_its_bound() -> None:
    run = Run([job("front-build", "in_progress", None)])
    with pytest.raises(awaitjob.AwaitError, match="front-build has not succeeded within 30 s"):
        run.await_build(within=30)
    assert run.now == 30


def test_a_job_whose_name_only_begins_like_it_is_not_the_one_waited_for() -> None:
    run = Run([job("front-build-other")], [job("front-build-other"), job("front-build")])
    assert run.await_build() == awaitjob.POLL


def test_github_unserved_is_read_again_at_the_next_poll() -> None:
    run = Run(awaitjob.UnreadableError("gh api failed: HTTP 503"), [job("front-build")])
    assert run.await_build() == awaitjob.POLL


def test_a_connection_that_fails_twice_is_read_again_until_the_job_succeeds() -> None:
    run = Run(
        awaitjob.UnreadableError("gh api failed: error connecting to api.github.com"),
        awaitjob.UnreadableError("gh api failed: error connecting to api.github.com"),
        [job("front-build")],
    )
    assert run.await_build() == 2 * awaitjob.POLL


def test_what_may_pass_is_read_again_and_bounded_by_the_delay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for stderr, again in [
        ("error connecting to api.github.com", True),
        ("HTTP 429: rate limit", True),
        ("HTTP 502: bad gateway", True),
        ("HTTP 404: Not Found", False),
        ("HTTP 403: forbidden", False),
    ]:
        script = tmp_path / "gh"
        script.write_text(f"#!/bin/sh\necho '{stderr}' >&2\nexit 1\n", encoding="utf-8")
        script.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))
        with pytest.raises(awaitjob.AwaitError) as caught:
            awaitjob.gh(["api", "repos"])
        assert isinstance(caught.value, awaitjob.UnreadableError) is again, stderr


def test_an_answer_that_is_not_json_is_read_again() -> None:
    answers = iter(["<html>", json.dumps({"jobs": [job("front-build")]})])
    world = awaitjob.World(call=lambda _: next(answers), wait=lambda _: None, clock=lambda: 0.0)
    assert awaitjob.await_job("front-build", 60, ENVIRONMENT, world) == 0


def test_a_reading_that_always_fails_ends_at_the_bound() -> None:
    run = Run(awaitjob.UnreadableError("gh api failed: HTTP 504"))
    with pytest.raises(awaitjob.AwaitError, match="has not succeeded within 30 s"):
        run.await_build(within=30)


def test_the_default_bound_exceeds_the_timeout_of_the_build() -> None:
    chain = yaml.safe_load((REPOSITORY / ".github" / "workflows" / "ci.yml").read_text())["jobs"]
    assert chain["front-build"]["timeout-minutes"] * 60 < awaitjob.WITHIN


def test_another_failure_of_gh_fails_the_wait_at_once() -> None:
    run = Run(
        awaitjob.AwaitError("gh api failed: HTTP 403: Resource not accessible by integration")
    )
    with pytest.raises(awaitjob.AwaitError, match="HTTP 403"):
        run.await_build()
    assert len(run.calls) == 1


def test_the_jobs_are_read_page_by_page() -> None:
    first = [job(f"job {i}") for i in range(awaitjob.PAGE)]
    run = Run(first, [job("front-build")])
    assert run.await_build() == 0
    assert run.calls[1][1].endswith("&page=2")


def test_an_answer_without_jobs_fails_the_wait() -> None:
    def call(_: list[str]) -> str:
        return json.dumps({"message": "Not Found"})

    world = awaitjob.World(call=call, wait=lambda _: None, clock=lambda: 0.0)
    with pytest.raises(awaitjob.AwaitError, match="did not answer the jobs of run 42"):
        awaitjob.await_job("front-build", 60, ENVIRONMENT, world)


def test_gh_that_fails_is_said_with_what_it_wrote(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "gh"
    script.write_text("#!/bin/sh\necho 'HTTP 503: unavailable' >&2\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(awaitjob.AwaitError, match="gh api failed: HTTP 503: unavailable"):
        awaitjob.gh(["api", "repos"])


def test_gh_missing_is_said(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(awaitjob.AwaitError, match="gh is not installed"):
        awaitjob.gh(["api", "repos"])


def test_outside_a_job_of_github_actions_the_wait_refuses(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
    assert awaitjob.main(["front-build"]) == 1
    assert "made for a job of GitHub Actions" in capsys.readouterr().err
