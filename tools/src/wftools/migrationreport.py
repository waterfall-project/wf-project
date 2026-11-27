# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The outcome of each test of a run of the family ``migrations``, for its judge (US-2850).

A plugin of pytest, loaded by ``-p wftools.migrationreport`` in the run of the tests of the back
of the version N (``wftools.migrationtests``) or of ``test_earlier_backup.py`` (``make
migrations-backup``), with ``tools/src`` on the path of Python. When ``WATERFALL_MIGRATIONS_REPORT``
names a file, it writes there, at the end of the session, one object of JSON per test: its node,
``passed``, ``failed`` or ``skipped``, and the text of its failure — of its setting up, its call or
its teardown, each kept, with what the test wrote and logged meanwhile, where the error of another
process shows (the service of the restoration). A module that does not collect is a failure under
its own node. Under pytest-xdist, the process that leads receives the outcomes of its workers and
writes alone.
``wftools.migrationknown`` judges the file against the known failures.
"""

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pytest

REPORT = "WATERFALL_MIGRATIONS_REPORT"
PASSED, FAILED, SKIPPED = "passed", "failed", "skipped"


class Recorder:
    """What the tests of the session came to, by their node."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.seen: dict[str, dict[str, str]] = {}

    def record(self, test: str, report: pytest.TestReport | pytest.CollectReport) -> None:
        """Fold a report of a phase of the test into its outcome: a failure wins, then a skip."""
        entry = self.seen.setdefault(test, {"test": test, "status": PASSED, "message": ""})
        if report.failed:
            entry["status"] = FAILED
            when = getattr(report, "when", "collect")
            said = [f"--- {title}\n{text}" for title, text in report.sections]
            entry["message"] += "\n".join([f"[{when}] {report.longreprtext}", *said, ""])
        elif report.skipped and entry["status"] == PASSED:
            entry["status"] = SKIPPED

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Record a phase of a test."""
        self.record(report.nodeid, report)

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        """Record a module that does not collect, under its node."""
        if report.failed:
            self.record(report.nodeid, report)

    def pytest_sessionfinish(self) -> None:
        """Write the outcomes, one object per line."""
        lines = [json.dumps(each, ensure_ascii=False) for each in self.seen.values()]
        self.path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def recorder_for(environment: Mapping[str, str], *, worker: bool) -> Recorder | None:
    """Return the recorder of the session where the report is asked, in the process that leads."""
    named = environment.get(REPORT)
    return Recorder(Path(named)) if named and not worker else None


def pytest_configure(config: pytest.Config) -> None:
    """Record the session where the report is asked, in the process that leads alone."""
    if recorder := recorder_for(os.environ, worker=hasattr(config, "workerinput")):
        config.pluginmanager.register(recorder, "wftools-migration-report")
