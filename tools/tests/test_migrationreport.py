# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The outcome of each test of a run of the family ``migrations``, for its judge (US-2850).

The plugin is loaded in the run of the tests of the version N and of ``test_earlier_backup.py``;
these tests hold what it writes from the reports of pytest, built here as pytest builds them.
"""

import json
from typing import TYPE_CHECKING, Literal

import pytest

from wftools.migrationreport import REPORT, Recorder, recorder_for

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.story("US-2850")

NODE = "tests/test_projects.py::test_create"


def phase(
    when: Literal["setup", "call", "teardown"],
    outcome: Literal["passed", "failed", "skipped"],
    said: str = "",
    node: str = NODE,
) -> pytest.TestReport:
    """Return the report of a phase of a test, as pytest makes one."""
    sections = [("Captured log call", "restore.replace_failed said=schema")] if said else []
    return pytest.TestReport(
        node,
        ("tests/test_projects.py", 1, "test_create"),
        {},
        outcome,
        said or None,
        when,
        sections,
    )


def written(path: Path) -> list[dict[str, str]]:
    """Read what the plugin wrote."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.requirement("WF-DAT-0140-A")
def test_each_test_is_written_once_a_failure_of_any_phase_winning_with_what_it_logged(
    tmp_path: Path,
) -> None:
    recorder = Recorder(tmp_path / "outcomes.jsonl")
    recorder.pytest_runtest_logreport(phase("setup", "passed"))
    recorder.pytest_runtest_logreport(phase("call", "failed", "E   RestoreError: waterfall"))
    recorder.pytest_runtest_logreport(phase("teardown", "passed"))
    recorder.pytest_runtest_logreport(phase("setup", "skipped", node="tests/t.py::test_skipped"))
    recorder.pytest_runtest_logreport(phase("call", "passed", node="tests/t.py::test_passed"))
    recorder.pytest_sessionfinish()
    rows = written(tmp_path / "outcomes.jsonl")
    assert [(row["test"], row["status"]) for row in rows] == [
        (NODE, "failed"),
        ("tests/t.py::test_skipped", "skipped"),
        ("tests/t.py::test_passed", "passed"),
    ]
    assert rows[0]["message"].startswith("[call] E   RestoreError: waterfall")
    assert "--- Captured log call\nrestore.replace_failed said=schema" in rows[0]["message"]


def test_a_module_that_does_not_collect_is_a_failure_under_its_node(tmp_path: Path) -> None:
    recorder = Recorder(tmp_path / "outcomes.jsonl")
    failed = pytest.CollectReport("tests/test_broken.py", "failed", "ImportError: x", [])
    recorder.pytest_collectreport(failed)
    recorder.pytest_collectreport(pytest.CollectReport("tests/test_fine.py", "passed", None, []))
    recorder.pytest_sessionfinish()
    rows = written(tmp_path / "outcomes.jsonl")
    assert [(row["test"], row["status"]) for row in rows] == [("tests/test_broken.py", "failed")]
    assert rows[0]["message"].startswith("[collect] ImportError: x")


@pytest.mark.parametrize(
    ("environment", "worker", "recorded"),
    [({REPORT: "o.jsonl"}, False, True), ({REPORT: "o.jsonl"}, True, False), ({}, False, False)],
)
def test_the_process_that_leads_alone_records_and_only_when_a_report_is_asked(
    environment: dict[str, str], *, worker: bool, recorded: bool
) -> None:
    # Under pytest-xdist, each worker sends its reports to the process that leads.
    assert (recorder_for(environment, worker=worker) is not None) is recorded
