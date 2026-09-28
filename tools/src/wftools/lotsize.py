# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Measure the real size of a lot, to set it beside the estimate of its issue (US-0310).

Usage: ``python -m wftools.lotsize BASE [HEAD]``, BASE being the branch of the lot's epic.

The size is the diff a review reads: lines added and removed, generated files left out —
lock files, the generated client, the listing of numeric examples, anything
``tools/paths.toml`` declares as generated. It is split into production code, tests, and
the rest — documentation, configuration, contract. The command informs and never fails:
the target is in ``docs/roadmap/README.md``, section « Lots », and an overrun is read in
the delivery report, not blocked (an epic delivered overnight would stall on it).
"""

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from wftools import REPOSITORY, paths
from wftools.sources import SOURCES


@dataclass(slots=True)
class Size:
    """The lines of a diff, by kind."""

    production: int = 0
    tests: int = 0
    other: int = 0
    generated: int = 0
    binary: list[str] = field(default_factory=list[str])

    @property
    def total(self) -> int:
        """Return the lines a review reads: everything but the generated files."""
        return self.production + self.tests + self.other


def measure(numstat: str, declaration: paths.Declaration) -> Size:
    """Sort the lines of a ``git diff --numstat`` by kind."""
    size = Size()
    for line in numstat.splitlines():
        added, removed, path = line.split("\t", 2)
        if added == "-":
            size.binary.append(path)
            continue
        lines = int(added) + int(removed)
        if declaration.is_generated(path):
            size.generated += lines
        elif declaration.is_test(path):
            size.tests += lines
        elif PurePosixPath(path).suffix in SOURCES:
            size.production += lines
        else:
            size.other += lines
    return size


def diff(base: str, head: str | None) -> str:
    """Return the numstat of what the lot adds to its merge base with the base."""
    target = [f"{base}...{head}"] if head else [_merge_base(base)]
    result = subprocess.run(
        ["git", "diff", "--numstat", "--no-renames", *target],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout or ""


def _merge_base(base: str) -> str:
    result = subprocess.run(
        ["git", "merge-base", base, "HEAD"],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    )
    return (result.stdout or "").strip()


def main(arguments: list[str]) -> int:
    """Print the size of the lot; never fail on it."""
    parser = argparse.ArgumentParser(prog="wftools.lotsize", description="Measure a lot.")
    parser.add_argument("base", help="the branch of the lot's epic")
    parser.add_argument("head", nargs="?", help="the tip of the lot; the working tree if absent")
    options = parser.parse_args(arguments)
    size = measure(diff(options.base, options.head), paths.read())
    print(
        f"{size.total} lines — production {size.production}, tests {size.tests}, other {size.other}"
    )
    print(f"left out: {size.generated} generated lines, {len(size.binary)} binary file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
