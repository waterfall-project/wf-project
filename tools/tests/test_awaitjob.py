# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the wait for a job of the run, and of service started beside the build (US-1910)."""

import json
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY, awaitjob

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

WORKFLOWS = REPOSITORY / ".github" / "workflows"
ENVIRONMENT = {"GITHUB_REPOSITORY": "waterfall-project/wf-project", "GITHUB_RUN_ID": "42"}


def workflow(name: str) -> dict[Any, Any]:
    """Return a workflow of the chain, read."""
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


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
    run = Run(awaitjob.AwaitError("gh api failed: HTTP 503"), [job("front-build")])
    assert run.await_build() == awaitjob.POLL


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


# The chain.


def test_service_starts_beside_the_build_of_the_front_and_waits_for_it_before_its_download() -> (
    None
):
    # US-1910/L5: service no longer needs front-build, whose end it waited for (1.4 minutes into
    # the run, in the median of ten runs of the queue of 2026-11-14), and waits for it in the step
    # before the download, after the work image and Keycloak's image; front-build runs whenever
    # service does, and both are judged by the gate.
    chain = workflow("ci.yml")["jobs"]
    service = chain["service"]
    assert service["needs"] == ["changes", "mirror", "e2e-image"]
    assert service["permissions"]["actions"] == "read"
    build = " ".join(chain["front-build"]["if"].split())
    assert "needs.changes.outputs.tier == 'full'" in build
    assert "needs.changes.outputs.service == 'true'" in build
    assert {"front-build", "service"} <= set(chain["gate"]["needs"])

    (paths,) = workflow("service.yml")["jobs"].values()
    assert paths["permissions"]["actions"] == "read"
    steps = paths["steps"]
    waited = next(
        i for i, s in enumerate(steps) if s.get("run") == "make await-job JOB=front-build"
    )
    assert steps[waited]["env"] == {"GH_TOKEN": "${{ github.token }}"}
    downloads = [i for i, s in enumerate(steps) if "download-artifact" in s.get("uses", "")]
    built = next(i for i, s in enumerate(steps) if s.get("run") == "make build-keycloak")
    assert built < waited
    assert downloads == [waited + 1]


def test_the_gate_judges_every_job_of_the_chain() -> None:
    # A job that starts earlier is still judged: the gate needs every other job of ci.yml.
    chain = workflow("ci.yml")["jobs"]
    assert set(chain["gate"]["needs"]) == set(chain) - {"gate"}
    assert chain["gate"]["if"] == "always()"
