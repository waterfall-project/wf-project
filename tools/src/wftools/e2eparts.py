# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Spread the end-to-end paths over the parts of the chain by the time they take (US-1910).

Usage: ``playwright test --list | python -m wftools.e2eparts plan [--service] i/N`` prints the
test list of the i-th of N parts, which ``playwright test --test-list`` plays; ``python -m
wftools.e2eparts service-part i/N`` says whether the i-th of N parts of the paths against the
service plays the paths that play one at a time (``serial``) or a share of the others
(``spread``); ``python -m wftools.e2eparts refresh [LOG]`` rewrites ``tools/e2e-durations.json``
and ``tools/e2e-service-durations.json`` from the log of a run of ``make e2e`` or of ``make
e2e-service`` (standard input without LOG).

Playwright's own ``--shard`` spreads files at equal numbers of tests, and the longest files weigh:
the fourth of five parts played about 260 s of tests against about 150 s for the others. The paths
are here spread by the seconds they took on a real run, the longest first, each into the part that
holds the least so far. The unit is a file, or a test for the files played test by test
(``mode: "parallel"``), which are made of independent tests; the versioned file keeps the seconds of
each, under the line of the test list that names it. The units are those of the listing Playwright
gives, so that every test is in exactly one part: none lost, none played twice. A unit the
durations do not know weighs the mean of the known units of its kind.

The paths against the service (``make e2e-service SHARD=i/N``, US-1910/L3) play on N platforms,
one a part. The parts 1 to N-1 share the projects ``service`` and ``shared``, spread the same way;
their units name their project first (``[service]``, then the file), since the test list of a part
must not reach the projects that wait for the others: a file without its project would make
``realm`` play its tests there, and with them, unfiltered, every project it depends on. The last
part plays ``shared-serial``, ``realm`` and ``restoration``, which play one at a time after the
others: alone on its platform, they no longer wait for them (``E2E_SERVICE_SERIAL``,
``frontend/playwright.config.ts``).
"""

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Callable

DURATIONS = REPOSITORY / "tools" / "e2e-durations.json"
SERVICE_DURATIONS = REPOSITORY / "tools" / "e2e-service-durations.json"
FRONT = REPOSITORY / "frontend"
PATHS = ("chromium",)
"""The project of the paths against the fake back, which ``make e2e SHARD=i/N`` spreads."""
SERVICE = ("service", "shared")
"""The projects of the paths against the service that the parts but the last share."""
LEAST_SERVICE_PARTS = 2
"""The parts of the paths against the service, at least: those that share, and the last."""
SERIAL = "serial"
SPREAD = "spread"
UNKNOWN = 5.0
"""The seconds a unit weighs when the durations know no unit of its kind at all."""
MINIMUM_WEIGHT = 0.1
"""The least seconds a unit weighs, so that a unit measured at 0 s still loads its part."""
SEPARATOR = " \u203a "
ANSI = re.compile(r"\x1b\[[0-9;]*m")
PROJECT = re.compile(r"^\[[^\]]+\]" + SEPARATOR)
"""The project a unit of the paths against the service names first."""
HEAD = (
    r"\[(?P<project>[^\]]+)\] \u203a (?:e2e/)?(?P<file>[^:\s]+\.ts):\d+:\d+ \u203a "
    r"(?P<title>.*?)"
)
TEST = re.compile(HEAD + r"\s*$")
"""A test of a listing, whose title is kept whole, whatever it ends with."""
TIMED = re.compile(HEAD + r"(?: \((?P<value>\d+(?:\.\d+)?)(?P<unit>ms|s|m|h)\))?\s*$")
"""A test of a log of the ``list`` reporter, which adds its duration."""
TOTAL = re.compile(r"^\s*Total: (?P<tests>\d+) tests? in \d+ files?\s*$", re.MULTILINE)
"""The line that closes a listing, with the number of tests Playwright counted."""
PARALLEL = re.compile(
    r"""^test\.describe\.configure\(\{[^}]*\bmode: (?P<quote>["'])parallel(?P=quote)""",
    re.MULTILINE,
)
"""The configuration of a whole file; a comment, or a ``describe`` inside, does not match."""
PASSED = re.compile(r"[\u2713\u2718]\s+\d+ ")
SECONDS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}


class Test(NamedTuple):
    """A test of a listing or of a log: its project, its file, its title path, its seconds."""

    project: str
    file: str
    title: str
    seconds: float


def is_parallel(file: str, front: Path = FRONT) -> bool:
    """Return whether the file plays its tests one by one (``mode: "parallel"``)."""
    return PARALLEL.search((front / "e2e" / file).read_text(encoding="utf-8")) is not None


def read(durations: Path = DURATIONS) -> dict[str, float]:
    """Return the seconds of each unit the versioned file knows, each a finite number, 0 or more."""
    found: dict[str, float] = {}
    for name, value in json.loads(durations.read_text(encoding="utf-8")).items():
        seconds = float(value)
        # json reads NaN and Infinity, which would weigh nothing, or everything, in a part
        if not math.isfinite(seconds) or seconds < 0:
            message = f"{durations.name}: the seconds of {name} are not a duration: {value}"
            raise ValueError(message)
        found[name] = seconds
    return found


def listed(text: str, *, timed: bool = False) -> list[Test]:
    """Return the tests of a listing, or of a log if ``timed``, with their seconds in a log.

    The lines of a log of the chain carry a timestamp before the mark of the result, and a test
    that failed counts as well; a test skipped has no seconds, and is left out of a log.
    """
    found: list[Test] = []
    for line in text.splitlines():
        plain = ANSI.sub("", line)
        if timed and PASSED.search(plain) is None:
            continue
        match = (TIMED if timed else TEST).search(plain)
        if match is None or (timed and match["value"] is None):
            continue
        seconds = float(match["value"]) * SECONDS[match["unit"]] if timed else 0.0
        found.append(Test(match["project"], match["file"], match["title"], seconds))
    return found


def unit(test: Test, parallel: Callable[[str], bool], *, named: bool = False) -> str:
    """Return the unit a test belongs to, as the line of the test list that names it.

    ``named``, the line names the project too, which a test list reads as a filter of its own.
    """
    name = f"{test.file}{SEPARATOR}{test.title}" if parallel(test.file) else test.file
    return f"[{test.project}]{SEPARATOR}{name}" if named else name


def spread(units: list[str], durations: dict[str, float], count: int) -> list[list[str]]:
    """Return ``count`` parts of ``units``, the longest first into the lightest part."""
    means: dict[bool, float] = {}
    for per_test in (False, True):
        known = [
            durations[name] for name in units if name in durations and is_per_test(name) is per_test
        ]
        means[per_test] = sum(known) / len(known) if known else UNKNOWN
    # a floor keeps a unit measured at 0 s from leaving the part it joins the lightest
    weight = {
        name: max(durations.get(name, means[is_per_test(name)]), MINIMUM_WEIGHT) for name in units
    }
    parts: list[list[str]] = [[] for _ in range(count)]
    loads = [0.0] * count
    for name in sorted(units, key=lambda name: (-weight[name], name)):
        lightest = min(range(count), key=lambda index: (loads[index], index))
        parts[lightest].append(name)
        loads[lightest] += weight[name]
    return [sorted(part) for part in parts]


def is_per_test(name: str) -> bool:
    """Tell whether a unit is a test of its file rather than the file, its project aside."""
    return SEPARATOR in PROJECT.sub("", name)


def parse_shard(shard: str) -> tuple[int, int]:
    """Return (i, N) of ``i/N``, refusing anything else."""
    match = re.fullmatch(r"(\d+)/(\d+)", shard)
    if match is None or not 1 <= int(match[1]) <= int(match[2]):
        message = f"the part must be i/N with 1 <= i <= N: {shard}"
        raise ValueError(message)
    return int(match[1]), int(match[2])


def units(listing: str, parallel: Callable[[str], bool], projects: tuple[str, ...]) -> list[str]:
    """Return the units of the tests of ``projects`` in a listing, which must be read whole.

    The units of the paths against the fake back (``PATHS``) are named without their project,
    the only one their listing holds; those of the paths against the service name it.
    """
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
    named = projects != PATHS
    kept = {unit(test, parallel, named=named) for test in tests if test.project in projects}
    if not kept:
        message = f"no test of the projects {', '.join(projects)} in the listing"
        raise ValueError(message)
    return sorted(kept)


def part(index: int, count: int, names: list[str], durations: dict[str, float]) -> list[str]:
    """Return the ``index``-th of ``count`` parts of the units, none of the parts empty."""
    if count > len(names):
        message = f"{count} parts for {len(names)} units: a part would be empty"
        raise ValueError(message)
    parts = spread(names, durations, count)
    if not all(parts):
        message = f"a part of the {count} would be empty: the units are badly spread"
        raise ValueError(message)
    return parts[index - 1]


def plan(
    shard: str, listing: str, durations: dict[str, float], parallel: Callable[[str], bool]
) -> list[str]:
    """Return the lines of the test list of the part ``shard`` (``i/N``) of the paths."""
    index, count = parse_shard(shard)
    return part(index, count, units(listing, parallel, PATHS), durations)


def service_part(shard: str) -> tuple[int, int] | None:
    """Return the share (i, N-1) a part ``i/N`` of the paths against the service plays.

    None for the last part, which plays the projects that play one at a time. Two parts at least:
    a single one would leave either the paths spread or those in series unplayed.
    """
    index, count = parse_shard(shard)
    if count < LEAST_SERVICE_PARTS:
        message = f"the paths against the service play in two parts at least, N >= 2: {shard}"
        raise ValueError(message)
    return None if index == count else (index, count - 1)


def service_plan(
    shard: str, listing: str, durations: dict[str, float], parallel: Callable[[str], bool]
) -> list[str]:
    """Return the lines of the test list of the part ``shard`` of the paths against the service."""
    share = service_part(shard)
    if share is None:
        message = (
            f"the part {shard} plays shared-serial, realm and restoration alone, "
            "with E2E_SERVICE_SERIAL and no test list"
        )
        raise ValueError(message)
    return part(*share, units(listing, parallel, SERVICE), durations)


def measure(
    log: str, parallel: Callable[[str], bool], projects: tuple[str, ...] = PATHS
) -> dict[str, float]:
    """Return the seconds of tests of each unit of ``projects`` in a Playwright ``list`` log."""
    named = projects != PATHS
    totals: dict[str, float] = {}
    for test in listed(log, timed=True):
        if test.project not in projects:
            continue
        name = unit(test, parallel, named=named)
        totals[name] = totals.get(name, 0.0) + test.seconds
    return {name: round(totals[name], 1) for name in sorted(totals)}


def write(durations: dict[str, float], target: Path = DURATIONS) -> None:
    """Write the durations, one unit a line, so that a refresh reads as a diff."""
    lines = ",\n".join(
        f"  {json.dumps(name, ensure_ascii=False)}: {seconds}"
        for name, seconds in durations.items()
    )
    target.write_text(f"{{\n{lines}\n}}\n", encoding="utf-8")


def refresh(text: str, *, drop: bool) -> int:
    """Rewrite each file of durations the log has results for; refuse a log that loses units."""
    kinds = ((PATHS, DURATIONS), (SERVICE, SERVICE_DURATIONS))
    found = [(target, measure(text, is_parallel, projects)) for projects, target in kinds]
    found = [(target, measured) for target, measured in found if measured]
    if not found:
        print("no test result in the log: the durations are left as they were", file=sys.stderr)
        return 1
    for target, measured in found:
        gone = sorted(set(read(target)) - set(measured)) if target.exists() else []
        if gone and not drop:
            print(
                f"the log lacks {len(gone)} units {target.name} knows, file left as it was:",
                file=sys.stderr,
            )
            print("\n".join(f"  {name}" for name in gone[:10]), file=sys.stderr)
            print("give the log of every job, or --drop to let them go", file=sys.stderr)
            return 1
    for target, measured in found:
        write(measured, target)
        print(f"{target.name}: {len(measured)} units, {sum(measured.values()):.0f} s of tests")
    return 0


def main(arguments: list[str]) -> int:
    """Print the test list of a part of the paths, or refresh the durations from a log."""
    parser = argparse.ArgumentParser(prog="wftools.e2eparts", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    planning = commands.add_parser("plan", help="print the test list of a part")
    planning.add_argument("shard")
    planning.add_argument(
        "--service", action="store_true", help="a part of the paths against the service"
    )
    commands.add_parser(
        "service-part", help="say whether a part of the paths against the service is the last"
    ).add_argument("shard")
    refreshing = commands.add_parser("refresh", help="rewrite the durations from a log")
    refreshing.add_argument("log", nargs="?", help="the log of a run; standard input if absent")
    refreshing.add_argument(
        "--drop", action="store_true", help="accept that the units the log lacks leave the file"
    )
    options = parser.parse_args(arguments)
    try:
        if options.command == "service-part":
            print(SERIAL if service_part(options.shard) is None else SPREAD)
            return 0
        if options.command == "plan":
            if options.service:
                lines = service_plan(
                    options.shard, sys.stdin.read(), read(SERVICE_DURATIONS), is_parallel
                )
            else:
                lines = plan(options.shard, sys.stdin.read(), read(DURATIONS), is_parallel)
            print("\n".join(lines))
            return 0
        text = Path(options.log).read_text(encoding="utf-8") if options.log else sys.stdin.read()
        return refresh(text, drop=options.drop)
    except ValueError as error:
        print(f"e2eparts: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
