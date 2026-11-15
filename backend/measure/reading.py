# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of a whole structure, as ``listNodes`` serves it: alone, profiled, in parallel."""

import cProfile
import multiprocessing
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import event

from measure.figures import ratio, summarise
from measure.report import Measure, Scalar
from measure.target import database_of
from waterfall.api.nodes import nodes_body, read_body
from waterfall.core.planning.interface import NodeFilters, Place, list_records

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Mapping, Sequence
    from types import CodeType

    from sqlalchemy.engine import Connection

    from waterfall.platform.database import Database

WORKERS = (1, 2, 4, 6)
"""The numbers of threads, and of processes, a wave of reads is played by."""

_TOP = 25
_MEGABYTE = 1e6
_MILLISECOND = 1000
_STARTED = "measure_statement_started"
_EXECUTE_NOTE = (
    "postgresql_execute_ms is the time of the statements' execution alone: fetching their rows "
    "and building the objects are counted in the read, not in it"
)


@dataclass(frozen=True, slots=True)
class Reading:
    """One whole reading, in its three stages and what it gave, by the route's own functions.

    The core reads the rows and computes (``read``), the route writes each node as the contract
    does and its meta (``bodies``), and the response is rendered (``dump``); the guards, the query,
    the transfer and Next are not here.
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
        found = list_records(session, place, NodeFilters(kinds=kinds))
    read = perf_counter()
    # What ``get_nodes`` does after the read, with the same functions: the body of the nodes, their
    # totals and the meta, and the response rendered by ``read_body``. Left out: the guards of the
    # route, the parsing of the query and the transfer.
    body = nodes_body(found)
    bodies = perf_counter()
    raw = read_body(body).body
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
    """What the statements sent to PostgreSQL cost: their number, and the time of their execution.

    The time runs from the statement sent to the cursor returned; the rows are fetched after it.
    """

    count: int = 0
    seconds: float = 0.0


@contextmanager
def counting_statements(database: Database) -> Generator[Statements]:
    """Count the statements the engine sends inside the block, and the time of their execution."""
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
            "postgresql_execute_ms": round(statements.seconds * _MILLISECOND),
        },
        notes=(_EXECUTE_NOTE,),
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


class _Barrier(Protocol):
    def wait(self, timeout: float | None = None) -> int: ...


_BARRIER_TIMEOUT = 300.0
_WAVE_NOTE = (
    "each wave is one pass: a read per worker after one that warmed it, no repeat to take a "
    "median of; the spread between waves is not known"
)


@dataclass(frozen=True, slots=True)
class Span:
    """When a read began and ended, on the clock of the system, which every process shares."""

    started: float
    ended: float


def _warmed_then_timed(read: Callable[[], float], barrier: _Barrier) -> Span:
    """Read once to warm this worker, wait for all the others, then read again, timed.

    The barrier also makes sure each worker of the wave has taken one read, and one alone.
    """
    read()
    barrier.wait(_BARRIER_TIMEOUT)
    started = perf_counter()
    read()
    return Span(started, perf_counter())


def _wave(spans: Sequence[Span], workers: int, kind: str) -> Mapping[str, Scalar]:
    durations = [each.ended - each.started for each in spans]
    wall = max(each.ended for each in spans) - min(each.started for each in spans)
    return {
        kind: workers,
        "each_median_ms": round(median(durations) * _MILLISECOND),
        "each_worst_ms": round(max(durations) * _MILLISECOND),
        "all_done_ms": round(wall * _MILLISECOND),
        "reads_per_second": round(ratio(workers, wall), 2),
    }


def measure_threads(database: Database, place: Place) -> Measure:
    """Play waves of reads by threads of one process: the interpreter's lock is in the way."""

    def read() -> float:
        return read_once(database, place).total

    rows: list[Mapping[str, Scalar]] = []
    for workers in WORKERS:
        barrier = threading.Barrier(workers)
        with ThreadPoolExecutor(workers) as pool:
            futures = [pool.submit(_warmed_then_timed, read, barrier) for _ in range(workers)]
            spans = [each.result() for each in futures]
        rows.append(_wave(spans, workers, "threads"))
    return Measure(
        name="read all, by threads of one process", rows=tuple(rows), notes=(_WAVE_NOTE,)
    )


_shared: dict[str, _Barrier] = {}


def _connect(address: str, barrier: _Barrier) -> None:
    """Open the database of a worker process, which opens its own, and keep the wave's barrier."""
    database_of(address)
    _shared["barrier"] = barrier


def _read_in_process(job: tuple[str, Place]) -> Span:
    address, place = job

    def read() -> float:
        return read_once(database_of(address), place).total

    return _warmed_then_timed(read, _shared["barrier"])


def measure_processes(address: str, place: Place) -> Measure:
    """Play waves of reads by processes, each with its own interpreter and its own connections."""
    context = multiprocessing.get_context()
    rows: list[Mapping[str, Scalar]] = []
    for workers in WORKERS:
        jobs = [(address, place)] * workers
        barrier = context.Barrier(workers)
        with ProcessPoolExecutor(
            workers, mp_context=context, initializer=_connect, initargs=(address, barrier)
        ) as pool:
            spans = list(pool.map(_read_in_process, jobs))
        rows.append(_wave(spans, workers, "processes"))
    return Measure(name="read all, by processes", rows=tuple(rows), notes=(_WAVE_NOTE,))
