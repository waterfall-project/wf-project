# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The report of the merge queue, and the classification of its failures (US-1880).

The logs are excerpts of real jobs of the chain, reduced, under ``tests/queue/``; the reading by
``gh`` is replaced by a fake source, or a fake call. No test reaches GitHub.
"""

import json
import subprocess
from dataclasses import replace
from datetime import date
from typing import TYPE_CHECKING

import pytest

from wftools import REPOSITORY, queue

if TYPE_CHECKING:
    from pathlib import Path

LOGS = REPOSITORY / "tools" / "tests" / "queue"
SERVICE = queue.Job(7, "service / paths", "failure", None, None, "Run make check-service")


def log(name: str) -> str:
    return (LOGS / f"{name}.log").read_text(encoding="utf-8")


def failures(name: str, job: queue.Job = SERVICE) -> list[queue.Failure]:
    return queue.failures_of(42, job, log(name))


def known(**entry: object) -> queue.Known:
    base: dict[str, object] = {
        "class": queue.FLAKY,
        "family": "F",
        "issue": "#1",
        "frequency": "1 passage",
        "cause": "hypothèse : la charge",
    }
    return queue.read_entry({**base, **entry}, "known 1")


def moment(minute: int) -> str:
    return f"2026-11-10T08:{minute:02}:00Z"


def job_data(
    identifier: int, name: str, conclusion: str, start: int, end: int
) -> dict[str, object]:
    steps = [{"name": "Set up job", "conclusion": "success"}]
    if conclusion != "success":
        steps.append({"name": f"Run {name}", "conclusion": conclusion})
    return {
        "id": identifier,
        "name": name,
        "conclusion": conclusion,
        "started_at": moment(start),
        "completed_at": moment(end),
        "steps": steps,
    }


def run_data(identifier: int, branch: str, conclusion: str = "success") -> dict[str, object]:
    return {
        "id": identifier,
        "head_branch": f"gh-readonly-queue/{branch}/pr-{identifier}-0123abcd",
        "status": "completed",
        "conclusion": conclusion,
        "created_at": moment(0),
        "run_started_at": moment(0),
    }


class FakeSource:
    """Pages of runs, jobs by run and logs by job, kept in memory; the logs it read, noted."""

    def __init__(
        self,
        pages: list[list[dict[str, object]]],
        jobs: dict[int, list[dict[str, object]]],
        logs: dict[int, str],
    ) -> None:
        self.pages = pages
        self.job_lists = jobs
        self.logs = logs
        self.read: list[int] = []
        self.asked: list[tuple[int, date | None]] = []

    def runs(self, page: int, since: date | None) -> list[dict[str, object]]:
        self.asked.append((page, since))
        return self.pages[page - 1] if page <= len(self.pages) else []

    def jobs(self, run: int) -> list[dict[str, object]]:
        return self.job_lists.get(run, [])

    def log(self, job: int) -> str:
        self.read.append(job)
        if job not in self.logs:
            message = "gh api failed: HTTP 410"
            raise queue.QueueError(message)
        return self.logs[job]


# The reading of the logs


def test_a_playwright_log_gives_each_failed_path_with_its_file_line_frame_and_error() -> None:
    found = failures("playwright-service-paths")
    assert [(f.test, f.where, f.message, f.target) for f in found] == [
        (
            "e2e/projects.spec.ts:113",
            "e2e/projects.spec.ts:135",
            "Error: expect(locator).toBeVisible() failed",
            "e2e-service",
        ),
        (
            "e2e/structure.spec.ts:417",
            "e2e/own-project.ts:39",
            "Error: expect(page).toHaveURL(expected) failed",
            "e2e-service",
        ),
    ]
    assert found[1].name.startswith("deletes a task at once and a summary")
    assert all(f.run == 42 and f.job == "service / paths" for f in found)
    assert "createOwnProject" in found[1].evidence


def test_a_pytest_log_gives_the_test_its_last_frame_and_the_section_as_evidence() -> None:
    (found,) = failures("pytest-back-tests")
    assert found.file == "tests/test_resource_settings_nodes.py"
    assert found.name.startswith("test_the_witness_loads_the_nodes_of_the_example")
    # The traceback never passes through the test's own file: a fixture failed.
    assert found.line is None
    assert found.test == "tests/test_resource_settings_nodes.py"
    assert found.where == "tests/conftest.py:474"
    assert found.message == "AssertionError: assert 1 == 0"
    assert found.target == "coverage-back"
    assert "LockNotAvailable" in found.evidence


def test_a_vitest_log_gives_the_test_its_line_and_error_without_colours() -> None:
    (found,) = failures("vitest-front-tests")
    assert found.test == "src/i18n/text-guard.test.ts:116"
    assert found.name.startswith('the text guard > refuses the text "<p>Bonjour</p>"')
    assert found.message == "Error: Test timed out in 60000ms."
    assert found.target == "coverage-front"
    assert "\x1b" not in found.name + found.message + found.evidence


@pytest.mark.parametrize(
    ("name", "message", "target"),
    [
        ("install-make", "curl: (6) Could not resolve host: archive.ubuntu.com", ""),
        ("pandoc", "curl: (22) The requested URL returned error: 503", ""),
        (
            "keycloak-import",
            (
                "E   ImportError: cannot import name 'Author' from partially initialized module "
                "'waterfall.core.users.interface' (most likely due to a circular import) "
                "(/home/runner/work/wf-project/wf-project/backend/src/waterfall/core/users/"
                "interface.py)"
            ),
            "test-keycloak",
        ),
    ],
)
def test_a_log_without_tests_gives_the_job_with_its_telling_line(
    name: str, message: str, target: str
) -> None:
    (found,) = failures(name, queue.Job(3, "e2e / paths (2/5)", "failure", None, None, "Install"))
    assert (found.test, found.message, found.target) == ("", message, target)
    assert found.step == "Install"
    assert "Process completed with exit code" in found.evidence


def test_the_same_failure_said_twice_in_a_log_counts_once() -> None:
    twice = log("vitest-front-tests") + "\n" + log("vitest-front-tests")
    assert len(queue.failures_of(1, SERVICE, twice)) == 1


# The classification


def test_an_entry_recognizes_a_failure_only_when_all_its_patterns_match() -> None:
    (projects, structure) = failures("playwright-service-paths")
    entry = known(job="^service / paths$", test=r"e2e/structure\.spec\.ts:", lines=[414, 452])
    assert entry.recognizes(structure)
    assert not entry.recognizes(projects)
    assert not entry.recognizes(replace(structure, job="e2e / paths (1/5)"))
    assert not entry.recognizes(replace(structure, line=453))
    assert known(message=r"own-project\.ts:39").recognizes(structure)
    assert known(step="e2e-service").recognizes(projects)


def test_an_entry_that_names_runs_recognizes_nothing_outside_them() -> None:
    (found,) = failures("keycloak-import")
    entry = known(**{"class": queue.REGRESSION}, job="^service / paths$", runs=[42])
    assert entry.recognizes(found)
    assert not entry.recognizes(replace(found, run=43))


def test_the_first_entry_that_recognizes_a_failure_classifies_it_and_none_says_to_classify() -> (
    None
):
    (found,) = failures("install-make")
    catalogue = queue.Catalogue(
        entries=[
            known(**{"class": queue.INFRASTRUCTURE}, message="Could not resolve host", issue="#2"),
            known(message="curl"),
        ]
    )
    kind, entry = catalogue.classify(found)
    assert (kind, entry.issue if entry else None) == (queue.INFRASTRUCTURE, "#2")
    assert queue.Catalogue().classify(found) == (queue.TO_CLASSIFY, None)


@pytest.mark.parametrize(
    ("entry", "said"),
    [
        ({"jobs": "x"}, "unknown keys jobs"),
        ({"class": "flaky", "job": "x"}, "class 'flaky' is none of"),
        ({"cause": "la charge", "job": "x"}, "« établie : » or « hypothèse : »"),
        ({"class": queue.REGRESSION, "job": "x"}, "names the runs"),
        ({"lines": [3, 4], "job": "x"}, "lines is [first, last], beside a test"),
        ({"lines": [4, 3], "test": "x"}, "lines is [first, last], beside a test"),
        ({"test": "("}, "test is not a regular expression"),
        ({"issue": " ", "job": "x"}, "issue is missing"),
        ({}, "recognizes nothing"),
    ],
)
def test_an_entry_that_would_recognize_badly_is_refused(
    entry: dict[str, object], said: str
) -> None:
    with pytest.raises(queue.QueueError, match=None) as refused:
        known(**entry)
    assert said in str(refused.value)


def test_the_versioned_list_classifies_the_failures_of_its_inventory() -> None:
    catalogue = queue.read_catalogue()
    (projects, structure) = failures("playwright-service-paths")
    assert catalogue.classify(structure)[0] == queue.FLAKY
    assert catalogue.classify(projects)[0] == queue.FLAKY
    infrastructure = failures(
        "install-make", queue.Job(3, "e2e / paths (2/5)", "failure", None, None, "Install make")
    )
    kind, entry = catalogue.classify(infrastructure[0])
    assert (kind, entry.issue if entry else None) == (queue.INFRASTRUCTURE, "#2913")
    (witness,) = failures(
        "pytest-back-tests", queue.Job(5, "back / tests (1/2)", "failure", None, None, "x")
    )
    assert catalogue.classify(witness)[0] == queue.FLAKY
    (cycle,) = failures(
        "keycloak-import", queue.Job(4, "keycloak / check", "failure", None, None, "x")
    )
    assert catalogue.classify(cycle) == (queue.TO_CLASSIFY, None)


def test_the_versioned_list_holds_its_inventory_and_the_reference() -> None:
    catalogue = queue.read_catalogue()
    assert catalogue.entries
    assert all(entry.issue.startswith("#") for entry in catalogue.entries)
    assert catalogue.reference == (
        "reference, every branch, from 2026-11-05 to 2026-11-12: 370 runs, 88 failed "
        "(68 in service / paths); median wall time 16 min on 2026-11-10 and 2026-11-11"
    )


def test_a_list_that_cannot_be_read_is_said(tmp_path: Path) -> None:
    broken = tmp_path / "known.toml"
    broken.write_text("[[known]\n")
    with pytest.raises(queue.QueueError, match=r"known\.toml cannot be read"):
        queue.read_catalogue(broken)
    broken.write_text("known = 3\n")
    with pytest.raises(queue.QueueError, match="known is not a list of tables"):
        queue.read_catalogue(broken)
    broken.write_text("[reference]\nruns = 3\n")
    with pytest.raises(queue.QueueError, match="reference of the known failures is incomplete"):
        queue.read_catalogue(broken)


# The durations


def test_the_90th_percentile_is_the_nearest_rank() -> None:
    values = [float(n) for n in range(1, 11)]
    assert queue.percentile(values, 0.9) == 9.0
    assert queue.percentile([5.0, 1.0, 3.0], 0.9) == 5.0
    assert queue.percentile([4.0], 0.9) == 4.0


def test_the_wall_time_runs_from_the_start_of_the_run_to_its_last_job() -> None:
    run = queue.read_run(run_data(1, "main"))
    jobs = (
        queue.read_job(job_data(1, "a", "success", 1, 5)),
        queue.read_job(job_data(2, "b", "success", 0, 12)),
    )
    run = replace(run, jobs=jobs)
    assert run.wall == 12.0
    assert sum(job.minutes for job in run.jobs) == 16.0
    assert replace(run, status="in_progress").wall is None


# The reading by gh


def test_gh_is_asked_for_the_merge_group_runs_of_the_chain_the_jobs_and_a_log() -> None:
    calls: list[list[str]] = []

    def call(arguments: list[str]) -> str:
        calls.append(arguments)
        if arguments[-1].endswith("/logs"):
            return "a log"
        if "/jobs?" in arguments[-1]:
            return json.dumps({"jobs": [{"id": 1}]})
        return json.dumps({"workflow_runs": [{"id": 2}]})

    github = queue.GitHub(call)
    assert github.runs(2, date(2026, 11, 5)) == [{"id": 2}]
    assert github.jobs(9) == [{"id": 1}]
    assert github.log(5) == "a log"
    assert calls == [
        [
            "api",
            (
                "repos/{owner}/{repo}/actions/workflows/ci.yml/runs?"
                "event=merge_group&per_page=100&page=2&created=>=2026-11-05"
            ),
        ],
        ["api", "repos/{owner}/{repo}/actions/runs/9/jobs?per_page=100"],
        ["api", "--allow-escape-sequences", "repos/{owner}/{repo}/actions/jobs/5/logs"],
    ]


@pytest.mark.parametrize("answer", ["not json", "[]", '{"jobs": 3}'])
def test_an_answer_of_gh_that_is_not_what_was_asked_is_refused(answer: str) -> None:
    github = queue.GitHub(lambda _: answer)
    with pytest.raises(queue.QueueError, match="gh api did not answer"):
        github.runs(1, None)
    with pytest.raises(queue.QueueError, match="gh api did not answer"):
        github.jobs(1)


def test_the_runs_of_the_branch_are_read_page_by_page_up_to_the_last_asked() -> None:
    first = [run_data(n, "epic/EP-09" if n % 2 else "main") for n in range(100, 0, -1)]
    second = [run_data(n, "epic/EP-09") for n in range(1000, 1010)]
    source = FakeSource([first, second], {}, {})
    kept = list(queue.select(source, "epic/EP-09", 55, date(2026, 11, 5)))
    assert len(kept) == 55
    assert {queue.queued_branch(run.branch) for run in kept} == {"epic/EP-09"}
    assert source.asked == [(1, date(2026, 11, 5)), (2, date(2026, 11, 5))]
    assert len(list(queue.select(source, None, None, None))) == 110


def test_the_branch_of_a_queue_reference_keeps_its_slashes() -> None:
    assert queue.queued_branch("gh-readonly-queue/epic/EP-24/pr-2929-99cad15") == "epic/EP-24"
    assert queue.queued_branch("gh-readonly-queue/main/pr-2979-b9cc1f5") == "main"
    assert queue.queued_branch("main") == "main"


# The report


def fake_queue() -> FakeSource:
    runs = [
        run_data(1, "epic/EP-09"),
        run_data(2, "epic/EP-09", "failure"),
        run_data(3, "epic/EP-09", "failure"),
        run_data(4, "epic/EP-09", "cancelled"),
    ]
    jobs = {
        1: [job_data(10, "back / tests (1/2)", "success", 0, 16)],
        2: [
            job_data(20, "service / paths", "failure", 1, 15),
            job_data(21, "gate", "failure", 15, 16),
        ],
        3: [
            job_data(30, "keycloak / check", "failure", 1, 5),
            job_data(31, "gate", "failure", 5, 6),
        ],
        4: [job_data(40, "gate", "cancelled", 0, 1)],
    }
    logs = {20: log("playwright-service-paths"), 30: log("keycloak-import")}
    return FakeSource([runs], jobs, logs)


def test_the_shards_of_a_job_that_failed_alike_are_listed_once_with_their_number() -> None:
    jobs = [job_data(n, f"e2e / paths ({n}/5)", "failure", 1, 4) for n in range(1, 6)]
    for job in jobs:
        job["steps"] = [{"name": "Install make", "conclusion": "failure"}]
    logs = dict.fromkeys(range(1, 6), log("install-make"))
    source = FakeSource([[run_data(8, "main", "failure")]], {8: jobs}, logs)
    runs, found = queue.gather(source, queue.select(source, "main", None, None))
    text = queue.report(runs, found, queue.Catalogue(), "main")
    assert len(found) == 5
    assert "     1  e2e / paths — Install make\n" in text
    assert text.count("Could not resolve host") == 1
    assert text.endswith(
        "  8  e2e / paths — Install make: curl: (6) Could not resolve host: archive.ubuntu.com"
        "  [to classify] (5 jobs)\n"
    )


def test_gate_is_not_read_when_another_job_failed_and_is_when_none_did() -> None:
    source = fake_queue()
    source.job_lists[3] = [job_data(31, "gate", "failure", 5, 6)]
    runs, found = queue.gather(source, queue.select(source, None, None, None))
    assert source.read == [20, 31]
    assert len(runs) == 4
    unreadable = found[-1]
    assert (unreadable.job, unreadable.message) == (
        "gate",
        "log unreadable: gh api failed: HTTP 410",
    )


def test_the_report_counts_classifies_and_measures_the_runs() -> None:
    source = fake_queue()
    runs, found = queue.gather(source, queue.select(source, "epic/EP-09", None, None))
    catalogue = queue.Catalogue(
        entries=[known(job="^service / paths$", issue="#2940")], reference="reference: 1 run"
    )
    text = queue.report(runs, found, catalogue, "epic/EP-09")
    assert text.splitlines()[:5] == [
        (
            "chain, merge_group, epic/EP-09: 4 runs created from 2026-11-10 08:00 "
            "to 2026-11-10 08:00 UTC"
        ),
        "  1 succeeded, 2 failed, 1 cancelled, 0 not finished",
        (
            "  failed without regression: 1 of 3 finished runs (33.3 %) — known flakiness 1, "
            "infrastructure 0; to classify 1; regression 0"
        ),
        "  wall time of the 1 succeeded runs: median 16.0 min, 90th percentile 16.0 min",
        "  runner minutes of the 4 finished runs: 37.0 in all, median 10.0 a run",
    ]
    assert "     1  service / paths — Run service / paths (make e2e-service)" in text
    assert "     1  keycloak / check — Run keycloak / check (make test-keycloak)" in text
    assert "     1  e2e/structure.spec.ts:417  deletes a task at once" in text
    assert "[known flakiness (F, #2940)]" in text
    assert "  3  keycloak / check — Run keycloak / check: E   ImportError" in text
    assert text.rstrip().endswith("[to classify]\nreference: 1 run")


def test_a_window_without_runs_says_so() -> None:
    assert queue.report([], [], queue.Catalogue(), "main") == (
        "no run of the merge queue for main in the window\n"
    )


@pytest.mark.parametrize(
    ("last", "since", "said"),
    [
        ("x", "", "LAST is a number of runs"),
        ("0", "", "LAST is at least 1"),
        ("", "11/05", "SINCE a date"),
    ],
)
def test_a_window_the_command_cannot_read_is_refused(
    last: str, since: str, said: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert queue.main(["--last", last, "--since", since], fake_queue()) == 1
    assert said in capsys.readouterr().err


def test_the_command_prints_the_report_of_the_last_runs(capsys: pytest.CaptureFixture[str]) -> None:
    assert queue.window("", "", "") == (None, queue.DEFAULT_LAST, None)
    assert queue.main(["--branch", "epic/EP-09", "--last", "2"], fake_queue()) == 0
    printed = capsys.readouterr().out
    assert printed.startswith("chain, merge_group, epic/EP-09: 2 runs")
    assert "reference, every branch" in printed


def test_make_runs_the_report_with_its_window() -> None:
    process = subprocess.run(
        [
            *("make", "--no-print-directory", "-n", "-C", str(REPOSITORY), "queue-report"),
            *("BRANCH=epic/EP-09", "LAST=20", "SINCE=2026-11-10"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert 'python -m wftools.queue --branch "epic/EP-09" --last "20" --since "2026-11-10"' in (
        process.stdout
    )
