# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Hold the code coverage of the back and of the front to its thresholds (US-0060).

Usage: ``python -m wftools.codecoverage {coverage.py|istanbul} REPORT``.

The specification asks for the coverage of requirements only; the coverage of code is a rule
of the repository, which finds what the first cannot see — an error path never run, dead
code. Lines and branches are both measured: an ``if`` without its ``else`` covers every
line and half the cases. Below 90 % of the lines or 85 % of the branches, the command fails
and names the least covered files. It reads the JSON report of coverage.py for the back,
and the JSON summary of Istanbul, which Vitest writes, for the front.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

LINES = 90.0
"""The least share of lines the tests must run, in percent."""
BRANCHES = 85.0
"""The least share of branches the tests must take, in percent."""
SHOWN = 5
"""How many of the least covered files a failure names."""


@dataclass(frozen=True, slots=True)
class Measure:
    """What the tests ran of a file, or of a whole side."""

    lines: int
    lines_covered: int
    branches: int
    branches_covered: int

    @property
    def lines_percent(self) -> float:
        """Return the share of lines run; a file with none counts as fully covered."""
        return 100.0 * self.lines_covered / self.lines if self.lines else 100.0

    @property
    def branches_percent(self) -> float:
        """Return the share of branches taken; a file with none counts as fully covered."""
        return 100.0 * self.branches_covered / self.branches if self.branches else 100.0


def from_coveragepy(report: dict[str, object]) -> tuple[Measure, dict[str, Measure]]:
    """Read the JSON report of coverage.py: the total, and each file."""

    def measure(summary: dict[str, int]) -> Measure:
        return Measure(
            summary["num_statements"],
            summary["covered_lines"],
            summary.get("num_branches", 0),
            summary.get("covered_branches", 0),
        )

    totals = cast("dict[str, int]", report["totals"])
    files = cast("dict[str, dict[str, dict[str, int]]]", report["files"])
    return measure(totals), {name: measure(data["summary"]) for name, data in files.items()}


def from_istanbul(report: dict[str, object]) -> tuple[Measure, dict[str, Measure]]:
    """Read the JSON summary of Istanbul: the total, and each file."""

    def measure(summary: dict[str, dict[str, int]]) -> Measure:
        lines, branches = summary["lines"], summary["branches"]
        return Measure(lines["total"], lines["covered"], branches["total"], branches["covered"])

    entries = cast("dict[str, dict[str, dict[str, int]]]", report)
    files = {name: measure(data) for name, data in entries.items() if name != "total"}
    return measure(entries["total"]), files


def problems(total: Measure, files: dict[str, Measure]) -> list[str]:
    """Return what falls short of the thresholds, with the least covered files."""
    short = [
        f"{what} {percent:.1f} %, {threshold:.0f} % at least"
        for what, percent, threshold in (
            ("lines", total.lines_percent, LINES),
            ("branches", total.branches_percent, BRANCHES),
        )
        if percent < threshold
    ]
    if not short:
        return []
    ranked = sorted(
        files.items(), key=lambda item: (item[1].lines_percent, item[1].branches_percent)
    )
    least = [
        f"  {name}: lines {measure.lines_percent:.0f} %, branches {measure.branches_percent:.0f} %"
        for name, measure in ranked[:SHOWN]
    ]
    return [*short, "least covered:", *least]


READERS = {"coverage.py": from_coveragepy, "istanbul": from_istanbul}


def main(arguments: list[str]) -> int:
    """Print the coverage of a report, and fail below the thresholds."""
    parser = argparse.ArgumentParser(
        prog="wftools.codecoverage", description="Hold code coverage to its thresholds."
    )
    parser.add_argument("kind", choices=sorted(READERS), help="the format of the report")
    parser.add_argument("report", type=Path, help="the JSON report")
    options = parser.parse_args(arguments)
    report = cast("dict[str, object]", json.loads(options.report.read_text(encoding="utf-8")))
    total, files = READERS[options.kind](report)
    print(f"lines {total.lines_percent:.1f} %, branches {total.branches_percent:.1f} %")
    found = problems(total, files)
    for problem in found:
        print(problem, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
