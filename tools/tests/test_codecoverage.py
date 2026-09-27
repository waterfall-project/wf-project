# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the thresholds of code coverage."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from wftools import codecoverage
from wftools.codecoverage import Measure


def coveragepy(lines: int, covered: int, branches: int, taken: int) -> dict[str, object]:
    """Return a coverage.py report of one file with these counts."""
    summary = {
        "num_statements": lines,
        "covered_lines": covered,
        "num_branches": branches,
        "covered_branches": taken,
    }
    return {"totals": summary, "files": {"src/a.py": {"summary": summary}}}


def istanbul(lines: int, covered: int, branches: int, taken: int) -> dict[str, object]:
    """Return an Istanbul summary of one file with these counts."""
    summary = {
        "lines": {"total": lines, "covered": covered},
        "branches": {"total": branches, "covered": taken},
    }
    return {"total": summary, "/app/src/a.ts": summary}


@pytest.mark.parametrize(
    ("lines", "branches", "passes"),
    [((90, 100), (85, 100), True), ((89, 100), (85, 100), False), ((90, 100), (84, 100), False)],
)
def test_the_thresholds_are_ninety_and_eighty_five(
    lines: tuple[int, int], branches: tuple[int, int], passes: bool
) -> None:
    total = Measure(lines[1], lines[0], branches[1], branches[0])
    assert (codecoverage.problems(total, {"a": total}) == []) is passes


def test_an_if_without_its_else_is_half_the_branches() -> None:
    measure = Measure(lines=4, lines_covered=4, branches=2, branches_covered=1)
    assert measure.lines_percent == 100.0
    assert measure.branches_percent == 50.0


def test_a_shortfall_names_the_least_covered_files() -> None:
    files = {
        "good.py": Measure(10, 10, 2, 2),
        "bad.py": Measure(10, 2, 2, 0),
        "fair.py": Measure(10, 8, 2, 2),
    }
    found = codecoverage.problems(Measure(30, 20, 6, 4), files)
    assert found[0] == "lines 66.7 %, 90 % at least"
    assert found[-3:] == [
        "  bad.py: lines 20 %, branches 0 %",
        "  fair.py: lines 80 %, branches 100 %",
        "  good.py: lines 100 %, branches 100 %",
    ]


Build = Callable[[int, int, int, int], dict[str, object]]


@pytest.mark.parametrize(("kind", "build"), [("coverage.py", coveragepy), ("istanbul", istanbul)])
def test_both_report_formats_are_read(kind: str, build: Build, tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(json.dumps(build(10, 10, 4, 4)), encoding="utf-8")
    assert codecoverage.main([kind, str(report)]) == 0
    report.write_text(json.dumps(build(10, 5, 4, 1)), encoding="utf-8")
    assert codecoverage.main([kind, str(report)]) == 1
