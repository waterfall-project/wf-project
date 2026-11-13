# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Spread the end-to-end paths over the parts of the chain by the time they take (US-1910).

Usage: ``playwright test --list | python -m wftools.e2eparts plan i/N`` prints the test list of
the i-th of N parts, which ``playwright test --test-list`` plays; ``python -m wftools.e2eparts
refresh [LOG]`` rewrites ``tools/e2e-durations.json`` from the log of a run of ``make e2e``
(standard input without LOG).

Playwright's own ``--shard`` spreads files at equal numbers of tests, and the longest files weigh:
the fourth of five parts played about 260 s of tests against about 150 s for the others. The paths
are here spread by the seconds they took on a real run, the longest first, each into the part that
holds the least so far. The unit is a file, or a test for the files played test by test
(``mode: "parallel"``), which are made of independent tests; the versioned file keeps the seconds of
each, under the line of the test list that names it. The units are those of the listing Playwright
gives, so that every test is in exactly one part: none lost, none played twice. A unit the
durations do not know weighs the mean of the known units of its kind.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Callable

DURATIONS = REPOSITORY / "tools" / "e2e-durations.json"
FRONT = REPOSITORY / "frontend"
UNKNOWN = 5.0
"""The seconds a unit weighs when the durations know no unit of its kind at all."""
SEPARATOR = " \u203a "
ANSI = re.compile(r"\x1b\[[0-9;]*m")
HEAD = r"\[[^\]]+\] \u203a (?:e2e/)?(?P<file>[^:\s]+\.spec\.ts):\d+:\d+ \u203a (?P<title>.*?)"
TEST = re.compile(HEAD + r"\s*$")
"""A test of a listing, whose title is kept whole, whatever it ends with."""
TIMED = re.compile(HEAD + r"(?: \((?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s|m|h)\))?\s*$")
"""A test of a log of the ``list`` reporter, which adds its duration."""
TOTAL = re.compile(r"^\s*Total: (?P<tests>\d+) tests? in \d+ files?\s*$", re.MULTILINE)
"""The line that closes a listing, with the number of tests Playwright counted."""
PARALLEL = re.compile(r'^test\.describe\.configure\(\{[^}]*\bmode: "parallel"', re.MULTILINE)
"""The configuration of a whole file; a comment, or a ``describe`` inside, does not match."""
PASSED = re.compile(r"[\u2713\u2718]\s+\d+ ")
SECONDS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}


def is_parallel(file: str, front: Path = FRONT) -> bool:
    """Return whether the file plays its tests one by one (``mode: "parallel"``)."""
    return PARALLEL.search((front / "e2e" / file).read_text(encoding="utf-8")) is not None


def read(durations: Path = DURATIONS) -> dict[str, float]:
    """Return the seconds of each unit the versioned file knows."""
    return {
        unit: float(seconds)
        for unit, seconds in json.loads(durations.read_text(encoding="utf-8")).items()
    }


def listed(text: str, *, timed: bool = False) -> list[tuple[str, str, float]]:
    """Return (file, title path, seconds) of the tests of a listing, or of a log if ``timed``.

    The lines of a log of the chain carry a timestamp before the mark of the result, and a test
    that failed counts as well; a test skipped has no seconds, and is left out of a log.
    """
    found: list[tuple[str, str, float]] = []
    for line in text.splitlines():
        plain = ANSI.sub("", line)
        if timed and PASSED.search(plain) is None:
            continue
        match = (TIMED if timed else TEST).search(plain)
        if match is None or (timed and match["value"] is None):
            continue
        seconds = float(match["value"]) * SECONDS[match["unit"]] if timed else 0.0
        found.append((match["file"], match["title"], seconds))
    return found


def unit(file: str, title: str, parallel: Callable[[str], bool]) -> str:
    """Return the unit a test belongs to, as the line of the test list that names it."""
    return f"{file}{SEPARATOR}{title}" if parallel(file) else file


def spread(units: list[str], durations: dict[str, float], count: int) -> list[list[str]]:
    """Return ``count`` parts of ``units``, the longest first into the lightest part."""
    means: dict[bool, float] = {}
    for per_test in (False, True):
        known = [
            durations[name]
            for name in units
            if name in durations and (SEPARATOR in name) is per_test
        ]
        means[per_test] = sum(known) / len(known) if known else UNKNOWN
    weight = {name: durations.get(name, means[SEPARATOR in name]) for name in units}
    parts: list[list[str]] = [[] for _ in range(count)]
    loads = [0.0] * count
    for name in sorted(units, key=lambda name: (-weight[name], name)):
        lightest = min(range(count), key=lambda index: (loads[index], index))
        parts[lightest].append(name)
        loads[lightest] += weight[name]
    return [sorted(part) for part in parts]


def parse_shard(shard: str) -> tuple[int, int]:
    """Return (i, N) of ``i/N``, refusing anything else."""
    match = re.fullmatch(r"(\d+)/(\d+)", shard)
    if match is None or not 1 <= int(match[1]) <= int(match[2]):
        message = f"the part must be i/N with 1 <= i <= N: {shard}"
        raise ValueError(message)
    return int(match[1]), int(match[2])


def plan(
    shard: str, listing: str, durations: dict[str, float], parallel: Callable[[str], bool]
) -> list[str]:
    """Return the lines of the test list of the part ``shard`` (``i/N``) of a listing."""
    index, count = parse_shard(shard)
    tests = listed(listing)
    totals = TOTAL.findall(ANSI.sub("", listing))
    if not tests:
        message = "no test recognised in the listing: no part is played"
        raise ValueError(message)
    if len(totals) != 1 or int(totals[0]) != len(tests):
        message = (
            f"{len(tests)} tests recognised in the listing, "
            f"{'+'.join(totals) or 'no Total line'} counted by Playwright: "
            "a test would be lost, or the format of the listing changed"
        )
        raise ValueError(message)
    units = sorted({unit(file, title, parallel) for file, title, _ in tests})
    if count > len(units):
        message = f"{count} parts for {len(units)} units: a part would be empty"
        raise ValueError(message)
    return spread(units, durations, count)[index - 1]


def measure(log: str, parallel: Callable[[str], bool]) -> dict[str, float]:
    """Return the seconds of tests of each unit of a Playwright ``list`` log, sorted by unit."""
    totals: dict[str, float] = {}
    for file, title, seconds in listed(log, timed=True):
        name = unit(file, title, parallel)
        totals[name] = totals.get(name, 0.0) + seconds
    return {name: round(totals[name], 1) for name in sorted(totals)}


def write(durations: dict[str, float], target: Path = DURATIONS) -> None:
    """Write the durations, one unit a line, so that a refresh reads as a diff."""
    lines = ",\n".join(
        f"  {json.dumps(name, ensure_ascii=False)}: {seconds}"
        for name, seconds in durations.items()
    )
    target.write_text(f"{{\n{lines}\n}}\n", encoding="utf-8")


def main(arguments: list[str]) -> int:
    """Print the test list of a part of the paths, or refresh the durations from a log."""
    parser = argparse.ArgumentParser(prog="wftools.e2eparts", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="print the test list of a part").add_argument("shard")
    refresh = commands.add_parser("refresh", help="rewrite the durations from a log")
    refresh.add_argument("log", nargs="?", help="the log of make e2e; standard input if absent")
    refresh.add_argument(
        "--drop", action="store_true", help="accept that the units the log lacks leave the file"
    )
    options = parser.parse_args(arguments)
    if options.command == "plan":
        try:
            lines = plan(options.shard, sys.stdin.read(), read(), is_parallel)
        except ValueError as error:
            print(f"e2eparts: {error}", file=sys.stderr)
            return 1
        print("\n".join(lines))
        return 0
    text = Path(options.log).read_text(encoding="utf-8") if options.log else sys.stdin.read()
    measured = measure(text, is_parallel)
    if not measured:
        print("no test result in the log: the durations are left as they were", file=sys.stderr)
        return 1
    gone = sorted(set(read(DURATIONS)) - set(measured))
    if gone and not options.drop:
        print(f"the log lacks {len(gone)} known units, file left as it was:", file=sys.stderr)
        print("\n".join(f"  {name}" for name in gone[:10]), file=sys.stderr)
        print("give the log of every job, or --drop to let them go", file=sys.stderr)
        return 1
    write(measured, DURATIONS)
    print(f"{len(measured)} units, {sum(measured.values()):.0f} s of tests")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
