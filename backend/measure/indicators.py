# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the entries of the cache of the indicators of the day cost (US-2420, #3628).

The entry is one by scope — the project, each subproject, the lines of the project alone —, with its
indicators and its three curves, under the key of the project followed by the scope
(``waterfall.core.indicators.caching``; decision of the author of 2026-11-16, #3628). It is measured
on PRJ-001 of the witness, in the Redis of the platform of the slot, as the service reads it
(``cached_scopes``): the size and the reading of the entry of the scope of the project, which
``getProjectIndicators`` reads, against those of the entries of every scope, which the evolution of
the indices without a scope reads; cold (no entry: the computation is paid) and hot (the entry is
kept: the document is read and parsed). The witness has the subprojects it has: the figures of every
scope are extrapolated linearly to a number of subprojects, through one scope and the scopes of the
witness, with no larger set; those of one scope are repeated, for the number of subprojects does not
weigh on them. Every entry written is deleted at the end.
"""

from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from measure.figures import summarise
from measure.report import Measure, Scalar
from measure.target import MeasureError
from waterfall.core.costs.interface import PROJECT, UNASSIGNED
from waterfall.core.indicators.caching import cached_scopes, day_key, scope_key
from waterfall.core.indicators.interface import IndicatorsReading, day_reading
from waterfall.core.projects.interface import subproject_ids
from waterfall.platform.cache import PREFIX
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.costs.interface import CostScope
    from waterfall.core.indicators.interface import DayReading
    from waterfall.platform.cache import IndicatorsCache
    from waterfall.platform.database import Database

OBJECTIVE_S = 1.0
"""The objective of the indicators of the current revision (table 15 of §4.6.2)."""
SUBPROJECTS = (10, 50, 100)
"""The numbers of subprojects the figures are extrapolated to."""
FIXED_SCOPES = 2
"""The scopes a project has beside its subprojects: itself, and its lines without a subproject.

Also defined, for the same count, in ``tools/src/wftools/measures.py``: keep the two equal.
"""
SHAPES = {"cell": "one scope", "all": "every scope"}
"""What is read: the scope of the project alone, or every scope of the project."""


@dataclass(frozen=True, slots=True)
class Read:
    """One reading of scopes: its duration, in seconds, and the bytes of their entries kept."""

    seconds: float
    size: int


def linear(one: float, whole: float, scopes: int, wanted: int) -> float:
    """Extrapolate a figure to ``wanted`` scopes.

    On the line through its value for one scope and for the ``scopes`` of the witness, two or more;
    flat when the scopes of the witness were measured no dearer than one, which is the spread.
    """
    return one + (wanted - 1) * max(0.0, whole - one) / (scopes - 1)


def _reading(session: Session, project_id: UUID) -> DayReading:
    reading = day_reading(session, project_id, IndicatorsReading(PROJECT, utc_now()))
    if reading is None:
        message = "the project measured has no current day to read"
        raise MeasureError(message)
    return reading


def _scopes(session: Session, project_id: UUID, shape: str) -> list[CostScope]:
    if shape == "cell":
        return [PROJECT]
    return [PROJECT, *subproject_ids(session, project_id), UNASSIGNED]


def _keys(session: Session, reading: DayReading, scopes: Sequence[CostScope]) -> list[str]:
    """Give the keys of the entries of scopes, as ``cached_scopes`` reads them."""
    subprojects = subproject_ids(session, reading.basis.project_id)
    key = day_key(session, reading.basis, reading.context, subprojects)
    return [PREFIX + scope_key(key, scope) for scope in scopes]


def _size(cache: IndicatorsCache, keys: Sequence[str]) -> int:
    kept = cache.client.mget(list(keys))
    if any(each is None for each in kept):
        message = "an entry measured was not kept: does the Redis of the platform answer?"
        raise MeasureError(message)
    return sum(len(each if isinstance(each, bytes) else str(each).encode()) for each in kept)


def _once(
    database: Database, project_id: UUID, cache: IndicatorsCache, *, shape: str, cold: bool
) -> Read:
    """Read scopes as the service does, from their entries; cold, after deleting them."""
    with database.transaction() as session:
        reading = _reading(session, project_id)
        scopes = _scopes(session, project_id, shape)
        keys = _keys(session, reading, scopes)
        if cold:
            cache.client.delete(*keys)
        started = perf_counter()
        cached_scopes(session, reading.basis, reading.context, scopes, cache)
        seconds = perf_counter() - started
        return Read(seconds, _size(cache, keys))


def _series(
    where: tuple[Database, UUID, IndicatorsCache], runs: int, *, shape: str, cold: bool
) -> tuple[Sequence[float], int]:
    """Play a reading ``runs`` times, after one that warms the statements and keeps the entries."""
    _once(*where, shape=shape, cold=True)
    reads = [_once(*where, shape=shape, cold=cold) for _ in range(runs)]
    return [each.seconds for each in reads], reads[0].size


def _seconds(value: float) -> float:
    return round(value, 3)


def measure_cache(
    database: Database, project_id: UUID, cache: IndicatorsCache, runs: int
) -> tuple[Measure, ...]:
    """Measure the size of the entries of the day of the project, and their reading, cold, hot."""
    with database.transaction() as session:
        every = _scopes(session, project_id, "all")
        keys = _keys(session, _reading(session, project_id), every)
    subprojects = len(every) - FIXED_SCOPES
    scopes = len(every)
    figures: dict[str, tuple[Sequence[float], int]] = {}
    try:
        for shape in SHAPES:
            for heat in ("cold", "hot"):
                figures[f"{shape}-{heat}"] = _series(
                    (database, project_id, cache), runs, shape=shape, cold=heat == "cold"
                )
    finally:
        cache.client.delete(*keys)
    summaries = {name: summarise(durations) for name, (durations, _) in figures.items()}
    sizes = {name: size for name, (_, size) in figures.items()}
    measures = [
        Measure(
            name=f"indicators cache, {label}, {heat}",
            summary=summaries[f"{shape}-{heat}"],
            facts={"entry_bytes": sizes[f"{shape}-{heat}"]},
        )
        for shape, label in SHAPES.items()
        for heat in ("cold", "hot")
    ]
    medians = {name: _seconds(summary.median) for name, summary in summaries.items()}
    cell, every_bytes = sizes["cell-hot"], sizes["all-hot"]
    facts: dict[str, Scalar] = {
        "subprojects": subprojects,
        "scopes": scopes,
        "cell_bytes": cell,
        "all_bytes": every_bytes,
        "cold_cell_s": medians["cell-cold"],
        "hot_cell_s": medians["cell-hot"],
        "cold_all_s": medians["all-cold"],
        "hot_all_s": medians["all-hot"],
    }

    def every_scope(one: float, whole: float, wanted: int) -> float:
        return linear(one, whole, scopes, wanted + FIXED_SCOPES)

    rows = tuple(
        {
            "subprojects": wanted,
            "cell_bytes": cell,
            "cold_cell_s": medians["cell-cold"],
            "hot_cell_s": medians["cell-hot"],
            "all_bytes": round(every_scope(cell, every_bytes, wanted)),
            "cold_all_s": _seconds(every_scope(medians["cell-cold"], medians["all-cold"], wanted)),
            "hot_all_s": _seconds(every_scope(medians["cell-hot"], medians["all-hot"], wanted)),
        }
        for wanted in SUBPROJECTS
    )
    alone = "within" if medians["cell-cold"] <= OBJECTIVE_S else "over"
    notes = (
        (
            "one entry by scope (#3628): one scope is read and computed alone, whatever the number "
            "of subprojects, its figures repeated in the rows"
        ),
        (
            f"every scope linear through one scope and the {scopes} of the witness, no larger set; "
            "flat when every scope was measured no dearer than one"
        ),
        f"one scope read cold is {alone} the {OBJECTIVE_S:g} s objective",
    )
    measures.append(Measure("indicators cache", facts=facts, rows=rows, notes=notes))
    return tuple(measures)
