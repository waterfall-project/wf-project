# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of a whole structure, as ``listNodes`` serves it: alone, profiled, in parallel."""

import cProfile
import json
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import TYPE_CHECKING

from sqlalchemy import event

from measure.figures import ratio, summarise
from measure.report import Measure, Scalar
from measure.target import database_of
from waterfall.api.nodes import node_body, totals_body
from waterfall.core.planning.interface import NodeFilters, Place, list_nodes

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping, Sequence
    from types import CodeType

    from sqlalchemy.engine import Connection

    from waterfall.platform.database import Database

WORKERS = (1, 2, 4, 6)
"""The numbers of threads, and of processes, a wave of reads is played by."""

_TOP = 25
_MEGABYTE = 1e6
_MILLISECOND = 1000
_STARTED = "measure_statement_started"


@dataclass(frozen=True, slots=True)
class Reading:
    """One whole reading, in its three stages and what it gave, as the route serves it.

    The core reads the rows and computes (``read``), the route writes each node as the contract
    does (``bodies``), and the body is serialised (``dump``); the transfer and Next are not here.
    """

    read: float
    bodies: float
    dump: float
    size: int
    nodes: int

    @property
    def total(self) -> float:
        """The three stages, in seconds."""
        return self.read + self.bodies + self.dump


def read_once(database: Database, place: Place, kinds: tuple[str, ...] | None = None) -> Reading:
    """Read a structure whole, or only the kinds asked, and write its body as the API does."""
    started = perf_counter()
    with database.transaction() as session:
        found = list_nodes(session, place, NodeFilters(kinds=kinds))
    read = perf_counter()
    body = {
        "items": [node_body(each) for each in found.items],
        "totals": totals_body(found.task_count, found.totals),
    }
    bodies = perf_counter()
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    dumped = perf_counter()
    return Reading(read - started, bodies - read, dumped - bodies, len(raw), len(found.items))


def _stages(readings: Sequence[Reading]) -> dict[str, Scalar]:
    return {
        "read_ms": round(median(each.read for each in readings) * _MILLISECOND),
        "bodies_ms": round(median(each.bodies for each in readings) * _MILLISECOND),
        "dump_ms": round(median(each.dump for each in readings) * _MILLISECOND),
    }


def measure_whole(
    database: Database, place: Place, runs: int, kinds: tuple[str, ...] | None
) -> Measure:
    """Measure a whole reading, ``runs`` times after one that warms the statements and the pool."""
    read_once(database, place, kinds)
    readings = [read_once(database, place, kinds) for _ in range(runs)]
    first = readings[0]
    return Measure(
        name="read all" if kinds is None else f"read kinds={','.join(kinds)}",
        summary=summarise([each.total for each in readings]),
        facts={
            "nodes": first.nodes,
            "body_mb": round(first.size / _MEGABYTE, 2),
            **_stages(readings),
        },
    )


@dataclass(slots=True)
class Statements:
    """What the statements sent to PostgreSQL cost: their number, and the time spent executing."""

    count: int = 0
    seconds: float = 0.0


@contextmanager
def counting_statements(database: Database) -> Generator[Statements]:
    """Count the statements the engine sends inside the block, and the time they wait for."""
    statements = Statements()

    def before(connection: Connection, *_: object) -> None:
        connection.info[_STARTED] = perf_counter()

    def after(connection: Connection, *_: object) -> None:
        statements.count += 1
        statements.seconds += perf_counter() - connection.info.pop(_STARTED)

    engine = database.engine
    event.listen(engine, "before_cursor_execute", before)
    event.listen(engine, "after_cursor_execute", after)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before)
        event.remove(engine, "after_cursor_execute", after)


def _where(code: CodeType | str) -> str:
    if isinstance(code, str):
        return code
    return f"{Path(code.co_filename).name}:{code.co_firstlineno}({code.co_name})"


def measure_profile(database: Database, place: Place) -> Measure:
    """Profile one whole reading: where its time goes, and what PostgreSQL's share of it is.

    The profiler slows what it watches: the figures say where, not how long.
    """
    read_once(database, place)
    profile = cProfile.Profile()
    with counting_statements(database) as statements:
        profile.enable()
        reading = read_once(database, place)
        profile.disable()
    entries = sorted(profile.getstats(), key=lambda each: each.totaltime, reverse=True)
    return Measure(
        name="read all, profiled",
        facts={
            "read_ms": round(reading.read * _MILLISECOND),
            "bodies_ms": round(reading.bodies * _MILLISECOND),
            "dump_ms": round(reading.dump * _MILLISECOND),
            "statements": statements.count,
            "postgresql_wait_ms": round(statements.seconds * _MILLISECOND),
        },
        rows=tuple(
            {
                "function": _where(each.code),
                "calls": each.callcount,
                "cumulative_ms": round(each.totaltime * _MILLISECOND),
                "own_ms": round(each.inlinetime * _MILLISECOND),
            }
            for each in entries[:_TOP]
        ),
    )


def _wave(wall: float, durations: Sequence[float], workers: int, kind: str) -> Mapping[str, Scalar]:
    return {
        kind: workers,
        "each_median_ms": round(median(durations) * _MILLISECOND),
        "each_worst_ms": round(max(durations) * _MILLISECOND),
        "all_done_ms": round(wall * _MILLISECOND),
        "reads_per_second": round(ratio(workers, wall), 2),
    }


def measure_threads(database: Database, place: Place) -> Measure:
    """Play waves of reads by threads of one process: the interpreter's lock is in the way."""

    def read(_: int) -> float:
        return read_once(database, place).total

    rows: list[Mapping[str, Scalar]] = []
    for workers in WORKERS:
        with ThreadPoolExecutor(workers) as pool:
            started = perf_counter()
            durations = list(pool.map(read, range(workers)))
            wall = perf_counter() - started
        rows.append(_wave(wall, durations, workers, "threads"))
    return Measure(name="read all, by threads of one process", rows=tuple(rows))


def _connect(address: str) -> None:
    """Open the database of a worker process, which opens its own."""
    database_of(address)


def _read_in_process(job: tuple[str, Place]) -> float:
    address, place = job
    return read_once(database_of(address), place).total


def measure_processes(address: str, place: Place) -> Measure:
    """Play waves of reads by processes, each with its own interpreter and its own connections."""
    rows: list[Mapping[str, Scalar]] = []
    for workers in WORKERS:
        jobs = [(address, place)] * workers
        with ProcessPoolExecutor(workers, initializer=_connect, initargs=(address,)) as pool:
            list(pool.map(_read_in_process, jobs))
            started = perf_counter()
            durations = list(pool.map(_read_in_process, jobs))
            wall = perf_counter() - started
        rows.append(_wave(wall, durations, workers, "processes"))
    return Measure(name="read all, by processes", rows=tuple(rows))
