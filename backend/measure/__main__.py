# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""``make measure-core``: the passage of the measure, its report on the terminal and in JSON."""

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy.exc import OperationalError

from measure.current import measure_current
from measure.document import (
    measure_comparison,
    measure_filtered,
    measure_kept,
    measure_marking,
)
from measure.indicators import measure_cache
from measure.reading import (
    measure_processes,
    measure_profile,
    measure_threads,
    measure_whole,
)
from measure.report import Measure, Report, render_json, render_text
from measure.risks import measure_merge, measure_occurrence
from measure.target import (
    PROJECT_CODE,
    MeasureError,
    address_from_environment,
    cache_from_environment,
    database_of,
    locate,
)
from measure.writing import measure_opening, measure_writes
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.installation import TIME_ZONE, stored_in
from waterfall.platform.logs import PLATFORM, logging_context

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from measure.target import Target
    from waterfall.core.planning.interface import Place
    from waterfall.platform.database import Database

DEFAULT_RUNS = 5
"""Identical runs of the whole reading, a cell entered and a revision opened: the spread of five is
what a gain must exceed. The profile and the waves of reads make one pass."""

PARTS = (
    "read",
    "profile",
    "parallel",
    "write",
    "revision",
    "kept",
    "current",
    "indicators",
    "merge",
    "occurrence",
)


def _at_least_one(text: str) -> int:
    try:
        runs = int(text)
    except ValueError:
        runs = 0
    if runs < 1:
        message = f"{text!r} is not a number of runs: at least 1"
        raise argparse.ArgumentTypeError(message)
    return runs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m measure",
        description="Measure the core in process, on the witness of the service platform.",
    )
    parser.add_argument(
        "--runs",
        type=_at_least_one,
        default=DEFAULT_RUNS,
        help="identical runs of the whole reading, the cell entered and the revision opened",
    )
    parser.add_argument(
        "--only",
        action="append",
        choices=PARTS,
        help="a part to play, repeatable: all of them by default",
    )
    parser.add_argument("--json", type=Path, help="also write the report, as JSON, to this file")
    return parser


def _indicators(database: Database, place: Place, runs: int) -> tuple[Measure, ...]:
    cache = cache_from_environment()
    try:
        return measure_cache(database, place.project_id, cache, runs)
    finally:
        cache.close()


def _passage(address: str, target: Target, runs: int, parts: Sequence[str]) -> tuple[Measure, ...]:
    database = database_of(address)
    place = target.place
    # The day of an indicator, of a key, of a marking is that of the time zone of the installation,
    # which the service reads from this database at its start.
    TIME_ZONE.read_from(stored_in(database))
    plan: dict[str, Callable[[], tuple[Measure, ...]]] = {
        "read": lambda: (
            measure_whole(database, place, runs, None),
            measure_whole(database, place, runs, ("task",)),
        ),
        "profile": lambda: (measure_profile(database, place),),
        "parallel": lambda: (
            measure_threads(database, place),
            measure_processes(address, place),
        ),
        "write": lambda: measure_writes(database, place, runs),
        "revision": lambda: (measure_opening(database, target, runs),),
        "indicators": lambda: _indicators(database, place, runs),
        "kept": lambda: (
            *measure_kept(database, target, runs),
            measure_marking(database, target, runs),
            *measure_comparison(database, target, runs),
            measure_filtered(database, target, runs),
        ),
        "current": lambda: measure_current(database, target, runs),
        "merge": lambda: (measure_merge(database, target, runs),),
        "occurrence": lambda: (measure_occurrence(database, target, runs),),
    }
    return tuple(measure for part in PARTS if part in parts for measure in plan[part]())


def main(argv: Sequence[str] | None = None) -> int:
    """Run the passage, print the report, write its JSON if asked; never fails on a duration."""
    arguments = _parser().parse_args(argv)
    parts = arguments.only or PARTS
    try:
        address = address_from_environment()
        target = locate(database_of(address))
        with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
            measures = _passage(address, target, arguments.runs, parts)
    except MeasureError as error:
        sys.stderr.write(f"measure: {error}\n")
        return 1
    except OperationalError as error:
        sys.stderr.write(
            f"measure: the database does not answer ({error.__class__.__name__}): start the "
            "platform of the slot and load the witness (make service-up, make service-install, "
            "make service-witness)\n"
        )
        return 1
    report = Report({"project": PROJECT_CODE, "runs": arguments.runs}, measures)
    sys.stdout.write(render_text(report))
    if arguments.json is not None:
        arguments.json.write_text(render_json(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
