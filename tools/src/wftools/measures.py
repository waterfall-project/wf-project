# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Confront the measure reports of the versions (WF-QUA-0060-A, US-2300).

Usage: ``python -m wftools.measures [DIRECTORY]``, DIRECTORY being ``docs/measures`` by default.

A version's measures are a JSON file, ``docs/measures/<version>.json``, taken on a workstation and
versioned with the code: the chain does not measure, the durations of a runner vary from simple to
double. ``reference.json``, taken before any correction, and ``processes.json``, the journey played
at one, two and four processes of the API (US-2230), are not versions and are not confronted.
The report names every operation of the table of response times (table 15 of §4.6.2) once::

    {"version": "0.4.0", "operations": [
      {"id": "open-grid", "objective_s": 1, "median_s": 0.8, "worst_s": 1.4, "dispersion_s": 0.2,
       "note": "text that documents an overrun or a degradation"},
      {"id": "portfolio-view", "objective_s": 2, "unserved": "EP-11"}]}

An operation the service does not yet serve carries ``unserved``, the epic that will measure it,
and no duration. The durations are in seconds, taken over identical passes: ``median_s`` is their
median, ``worst_s`` the longest and ``dispersion_s`` their sample standard deviation (n - 1).
Only the median is confronted; the worst duration and the dispersion say what a difference must
exceed to be a gain.

The previous version's duration is read in the previous report, not copied into the latest. The two
last reports are confronted: the command prints, for each served operation, its median and the
previous version's; an objective exceeded by the median, a median more than a quarter above the
previous version's (whatever it was, zero included), or an operation served by the previous report
and no longer by the latest, is a warning of the chain, and a failure when the latest report gives
no ``note`` for it. Without a previous report only the objectives are held; without any report the
check passes.

The identifiers of the table, each with the row of table 15 it names and the operations of the
contract that carry it (EP-26, US-2300):

- ``open-grid``: open a grid of a thousand tasks, ``listNodes``;
- ``recompute-after-entry``: recompute after an entry in a grid, ``updateTaskFacet`` and
  ``updateEstimateLine``;
- ``open-compared-grid``: open a grid of planning, of estimate or of remaining to commit compared
  with a marked revision, ``compareRevisions`` (EP-27, US-2390);
- ``filter-sort-search``: filter, sort or search in such a grid, ``listNodes``;
- ``indicators``: show the indicators of the current revision, ``getProjectIndicators`` (EP-10,
  US-2420);
- ``recompute-compared``: recompute after an entry in a compared grid, until its marks are read
  anew, ``updateTaskFacet`` or ``updateEstimateLine`` then ``compareRevisions`` (EP-27, US-2390);
- ``workload-or-projection``: show the workload or the projection of expenses,
  ``getProjectWorkload`` and ``getProjectSpending`` (EP-10, US-2420): the durations of the two
  screens are the samples of one operation;
- ``mark-revision``: mark a revision of ten thousand objects, ``markRevision``;
- ``import-costs``: analyse then apply an import of eighteen thousand cost lines, ``openImport``,
  ``applyImport`` and ``getBackgroundTask``;
- ``export-planning``: generate the export of a planning of a thousand tasks, ``requestExport`` and
  ``getBackgroundTask``.

``portfolio-view`` (EP-11) has no operation yet: it is unserved. Until EP-10 delivered them,
``indicators`` and the projection of expenses were too, and until EP-27 delivered it, the compared
grid (``open-compared-grid`` and ``recompute-compared``).

The operation ``indicators``, once served, also says what the entries of the cache of the
indicators of the day cost (US-2420, #3628): a ``cache`` object, taken by ``make measure-core
ONLY=indicators`` on the same witness (the ``facts`` and the ``rows`` of its measure "indicators
cache")::

    "cache": {"subprojects": 2, "scopes": 4, "cell_bytes": 15000, "all_bytes": 48000,
              "cold_cell_s": 1.1, "hot_cell_s": 0.02, "cold_all_s": 1.5, "hot_all_s": 0.03,
              "extrapolation": [{"subprojects": 100, "cell_bytes": 15000, "cold_cell_s": 1.1,
                                 "hot_cell_s": 0.02, "all_bytes": 1100000, "cold_all_s": 15.0,
                                 "hot_all_s": 0.4}]}

The entry is one by scope (#3628). ``cell_bytes``, ``cold_cell_s`` and ``hot_cell_s`` are those of
the entry of the scope of the project, which ``getProjectIndicators`` reads; ``all_bytes``,
``cold_all_s`` and ``hot_all_s`` those of the entries of every scope, which the evolution of the
indices without a scope reads. The extrapolation is linear for every scope, never taken on a larger
set; a scope alone does not depend on the number of subprojects, its figures repeated. One scope
read cold over the objective of the operation is a finding, as a median over it; it is documented
by the ``note`` of the ``cache`` object alone, and the ``note`` of the operation documents only the
median over the objective and the degradation.
"""

import itertools
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from wftools import REPOSITORY

MEASURES = REPOSITORY / "docs" / "measures"
DEGRADATION = 1.25
"""The ratio above which a duration, against the previous version's, is a degradation."""
VERSION = re.compile(r"\d+\.\d+\.\d+")
# Reports kept beside those of the versions, which are not one: the reference and the processes.
NOT_VERSIONS = frozenset({"reference", "processes"})
EPIC = re.compile(r"EP-\d+")
DURATIONS = ("median_s", "worst_s", "dispersion_s")


@dataclass(frozen=True, slots=True)
class Operation:
    """A line of table 15: its identifier, its wording and its objective, in seconds."""

    id: str
    label: str
    objective_s: float


TABLE = (
    Operation("open-grid", "Open a grid of a thousand tasks", 1),
    Operation("recompute-after-entry", "Recompute after an entry in a grid", 1),
    Operation("indicators", "Show the indicators of the current revision", 1),
    Operation("portfolio-view", "Show a portfolio view of three hundred projects", 2),
    Operation("open-compared-grid", "Open a grid compared with a marked revision", 2),
    Operation("filter-sort-search", "Filter, sort or search in such a grid", 2),
    Operation("recompute-compared", "Recompute after an entry in a compared grid", 2),
    Operation("workload-or-projection", "Show the workload or the expense projection", 2),
    Operation("mark-revision", "Mark a revision of ten thousand objects", 60),
    Operation("import-costs", "Analyse then apply an import of eighteen thousand lines", 300),
    Operation("export-planning", "Generate the export of a planning of a thousand tasks", 30),
)


CACHED = "indicators"
"""The operation that carries the cost of the entry of the cache of the indicators."""
CACHE_COUNTS = ("subprojects", "scopes")
CACHE_FIGURES = (
    "cell_bytes",
    "all_bytes",
    "cold_cell_s",
    "hot_cell_s",
    "cold_all_s",
    "hot_all_s",
)
CACHE_ROW = ("subprojects", *CACHE_FIGURES)
FIXED_SCOPES = 2
"""The scopes a project has beside its subprojects: itself, and its lines without a subproject.

Also defined, for the same count, in ``backend/measure/indicators.py``: keep the two equal.
"""


@dataclass(frozen=True, slots=True)
class Cache:
    """What the entries of the cache of the indicators cost, as far as it is confronted."""

    cold_cell_s: float
    scopes: int
    cell_bytes: float
    all_bytes: float
    extrapolated: int
    note: str = ""


@dataclass(frozen=True, slots=True)
class Measured:
    """An operation of a report: served, with its durations, or named for the epic to serve it."""

    median_s: float | None
    worst_s: float | None
    dispersion_s: float | None
    note: str
    unserved: str | None
    cache: Cache | None = None


@dataclass(frozen=True, slots=True)
class Report:
    """The measures of a version."""

    version: str
    operations: dict[str, Measured]


@dataclass(frozen=True, slots=True)
class Finding:
    """An objective exceeded or a degradation, with whether the report documents it."""

    operation: str
    message: str
    documented: bool


def version_key(version: str) -> tuple[int, ...]:
    """Return the sort key of a version, ``0.10.0`` after ``0.9.0``."""
    if not VERSION.fullmatch(version):
        message = f"{version}: a version is numbered as 0.4.0"
        raise ValueError(message)
    return tuple(int(part) for part in version.split("."))


def _number(entry: dict[str, object], key: str, where: str) -> float:
    value = entry.get(key)
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value < 0
    ):
        message = f"{where}: {key} must be a number of seconds, not {value!r}"
        raise ValueError(message)
    return float(value)


def _cache(entry: dict[str, object], where: str) -> Cache:
    body = entry.get("cache")
    if not isinstance(body, dict):
        message = f"{where}: the cost of the entry of the cache is an object, cache"
        raise TypeError(message)
    given = cast("dict[str, object]", body)
    here = f"{where}, cache"
    figures = {key: _number(given, key, here) for key in (*CACHE_COUNTS, *CACHE_FIGURES)}
    rows = given.get("extrapolation")
    if not isinstance(rows, list) or not rows:
        message = f"{here}: extrapolation is a list of sizes extrapolated, one at least"
        raise TypeError(message)
    listed = cast("list[object]", rows)
    sizes: list[float] = []
    for row in listed:
        if not isinstance(row, dict):
            message = f"{here}: a row of extrapolation is an object, not {row!r}"
            raise TypeError(message)
        figures_of_row = {
            key: _number(cast("dict[str, object]", row), key, f"{here}, extrapolation")
            for key in CACHE_ROW
        }
        sizes.append(figures_of_row["subprojects"])
    if any(before >= after for before, after in itertools.pairwise(sizes)):
        message = (
            f"{here}: the rows of extrapolation are sorted by subprojects, strictly ascending,"
            " one row per size"
        )
        raise ValueError(message)
    note = given.get("note", "")
    if not isinstance(note, str):
        message = f"{here}: note must be a text"
        raise TypeError(message)
    if figures["scopes"] != figures["subprojects"] + FIXED_SCOPES:
        message = f"{here}: scopes are the subprojects, the project and its own lines"
        raise ValueError(message)
    if figures["all_bytes"] < figures["cell_bytes"]:
        message = f"{here}: the entries of every scope weigh at least the one of the project"
        raise ValueError(message)
    return Cache(
        figures["cold_cell_s"],
        int(figures["scopes"]),
        figures["cell_bytes"],
        figures["all_bytes"],
        len(listed),
        note.strip(),
    )


def _operation(entry: dict[str, object], where: str, objective: float) -> Measured:
    if _number(entry, "objective_s", where) != objective:
        message = f"{where}: the objective of table 15 is {objective:g} s"
        raise ValueError(message)
    note = entry.get("note", "")
    if not isinstance(note, str):
        message = f"{where}: note must be a text"
        raise TypeError(message)
    unserved = entry.get("unserved")
    if unserved is None:
        median, worst, dispersion = (_number(entry, key, where) for key in DURATIONS)
        if worst < median:
            message = f"{where}: the worst duration is below the median"
            raise ValueError(message)
        cache = None
        if entry.get("id") == CACHED:
            cache = _cache(entry, where)
        elif "cache" in entry:
            message = f"{where}: only {CACHED} carries the cost of the cache"
            raise ValueError(message)
        return Measured(median, worst, dispersion, note.strip(), None, cache)
    if not isinstance(unserved, str) or not EPIC.fullmatch(unserved):
        message = f"{where}: unserved must name an epic, as EP-10, not {unserved!r}"
        raise ValueError(message)
    if any(key in entry for key in (*DURATIONS, "cache")):
        message = f"{where}: an operation the service does not serve has no duration"
        raise ValueError(message)
    return Measured(None, None, None, note.strip(), unserved)


def parse(text: str, name: str) -> Report:
    """Read a report, which names every operation of the table once, with its objective."""
    data: object = json.loads(text)
    if not isinstance(data, dict):
        message = f"{name}: a report is an object"
        raise TypeError(message)
    body = cast("dict[str, object]", data)
    if body.get("version") != name:
        message = f"{name}: version must be the name of the file, not {body.get('version')!r}"
        raise ValueError(message)
    listed = body.get("operations")
    if not isinstance(listed, list):
        message = f"{name}: operations must be a list"
        raise TypeError(message)
    for entry in cast("list[object]", listed):
        if not isinstance(entry, dict):
            message = f"{name}: an operation is an object, not {entry!r}"
            raise TypeError(message)
    entries = cast("list[dict[str, object]]", listed)
    given = {str(entry.get("id")): entry for entry in entries}
    wanted = {line.id: line for line in TABLE}
    if len(given) != len(entries) or set(given) != set(wanted):
        missing = sorted(set(wanted) - set(given))
        extra = sorted(set(given) - set(wanted))
        message = (
            f"{name}: the operations are those of table 15, once each "
            f"(missing {missing}, unknown {extra})"
        )
        raise ValueError(message)
    operations = {
        identifier: _operation(entry, f"{name}, {identifier}", wanted[identifier].objective_s)
        for identifier, entry in given.items()
    }
    return Report(name, operations)


def read(directory: Path) -> list[Report]:
    """Return the reports of the versions under ``directory``, oldest first."""
    if not directory.is_dir():
        return []
    files = [file for file in directory.glob("*.json") if file.stem not in NOT_VERSIONS]
    for file in files:
        if not VERSION.fullmatch(file.stem):
            message = f"{file.name}: a report is named for its version, as 0.4.0.json"
            raise ValueError(message)
    files.sort(key=lambda file: version_key(file.stem))
    return [parse(file.read_text("utf-8"), file.stem) for file in files]


def confront(latest: Report, previous: Report | None) -> list[Finding]:
    """Return what the latest report exceeds or degrades, and whether its notes document it.

    Each kind of finding has its own note: the median over its objective, and a degradation, the
    ``note`` of the operation; one scope read cold over the objective, the ``note`` of its
    ``cache``.
    """
    findings: list[Finding] = []
    for line in TABLE:
        measured = latest.operations[line.id]
        median = measured.median_s
        documented = bool(measured.note)
        before = None if previous is None else previous.operations[line.id].median_s
        if median is None:
            if before is not None and previous is not None:
                text = f"{line.label}: served by {previous.version}, no longer served"
                findings.append(Finding(line.id, text, documented))
            continue
        if median > line.objective_s:
            text = f"{line.label}: {median:g} s, above its objective of {line.objective_s:g} s"
            findings.append(Finding(line.id, text, documented))
        cache = measured.cache
        if cache is not None and cache.cold_cell_s > line.objective_s:
            text = (
                f"{line.label}: the entry of one scope read cold, {cache.cold_cell_s:g} s, is "
                f"above the objective of {line.objective_s:g} s"
            )
            findings.append(Finding(line.id, text, bool(cache.note)))
        if previous is None or before is None:
            continue
        if median > before * DEGRADATION:
            above = f"{median / before - 1:.0%} above" if before else "above"
            text = f"{line.label}: {median:g} s, {above} the {before:g} s of {previous.version}"
            findings.append(Finding(line.id, text, documented))
    return findings


def compare(latest: Report, previous: Report | None) -> list[str]:
    """Return a line per served operation: its median and the previous version's."""
    lines: list[str] = []
    for line in TABLE:
        median = latest.operations[line.id].median_s
        if median is None:
            continue
        before = None if previous is None else previous.operations[line.id].median_s
        against = "no previous measure" if before is None else f"{before:g} s before"
        lines.append(f"{line.id}: {median:g} s, {against} (objective {line.objective_s:g} s)")
        cache = latest.operations[line.id].cache
        if cache is not None:
            lines.append(
                f"{line.id}: entry of the cache {cache.cell_bytes:g} bytes a scope, "
                f"{cache.all_bytes:g} for {cache.scopes} scopes, one scope read cold "
                f"{cache.cold_cell_s:g} s, {cache.extrapolated} extrapolations"
            )
    return lines


def main(arguments: list[str]) -> int:
    """Warn of each objective exceeded or degradation; fail on one the report does not document."""
    directory = Path(arguments[0]) if arguments else MEASURES
    try:
        reports = read(directory)
    except (ValueError, TypeError) as error:
        print(f"::error::{error}")
        return 1
    if not reports:
        print("no report of a version: nothing to confront")
        return 0
    latest = reports[-1]
    previous = reports[-2] if len(reports) > 1 else None
    print(f"report {latest.version}, against {previous.version if previous else 'the objectives'}")
    for line in compare(latest, previous):
        print(line)
    failed = False
    for finding in confront(latest, previous):
        print(f"::warning::{finding.message}")
        if not finding.documented:
            print(f"::error::{finding.operation}: not documented in the report {latest.version}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
