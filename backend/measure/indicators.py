# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the entry of the cache of the indicators of the day costs (US-2420, #3628).

The entry is one document by project and by day, that carries every scope — the project, each
subproject, the lines of the project alone — with its indicators and its three curves
(``waterfall.core.indicators.caching``). It is measured on PRJ-001 of the witness, in the Redis of
the platform of the slot: its size, and the time of reading one scope of it, against the same read
of an entry of that scope alone — the entry by scope, which the decision of #3628 would make of it
if the objective of a second were not held —, cold (no entry: the computation is paid) and hot (the
entry is kept: the document is read and parsed). The witness has the subprojects it has: the
figures are extrapolated linearly to a number of subprojects, through the entry of one scope and
the whole entry, with no larger set. Every entry written is deleted at the end.
"""

import json
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from measure.figures import summarise
from measure.report import Measure, Scalar
from measure.target import MeasureError
from waterfall.core.costs.interface import PROJECT
from waterfall.core.indicators.caching import cached_scopes, day_entry, day_key
from waterfall.core.indicators.interface import IndicatorsReading, day_reading
from waterfall.core.projects.interface import subproject_ids
from waterfall.platform.cache import PREFIX
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.indicators.interface import DayReading
    from waterfall.platform.cache import IndicatorsCache
    from waterfall.platform.database import Database

OBJECTIVE_S = 1.0
"""The objective of the indicators of the current revision (table 15 of §4.6.2)."""
SUBPROJECTS = (10, 50, 100)
"""The numbers of subprojects the figures are extrapolated to."""
CELL = ":cell"
"""What the key of the entry of one scope adds to the key of the project's entry."""
FIXED_SCOPES = 2
"""The scopes a project has beside its subprojects: itself, and its lines without a subproject."""

type Once = Callable[..., Read]


@dataclass(frozen=True, slots=True)
class Read:
    """One reading of one scope: its duration, in seconds, and the bytes of the entry kept."""

    seconds: float
    size: int


def linear(one: float, whole: float, scopes: int, wanted: int) -> float:
    """Extrapolate a figure to ``wanted`` scopes.

    On the line through its value for one scope and for the ``scopes`` of the witness, two or more.
    """
    return one + (wanted - 1) * (whole - one) / (scopes - 1)


def _reading(session: Session, project_id: UUID) -> DayReading:
    reading = day_reading(session, project_id, IndicatorsReading(PROJECT, utc_now()))
    if reading is None:
        message = "the project measured has no current day to read"
        raise MeasureError(message)
    return reading


def _key(session: Session, reading: DayReading, project_id: UUID) -> str:
    subprojects = subproject_ids(session, project_id)
    return day_key(session, reading.basis, reading.context, subprojects)


def _size(cache: IndicatorsCache, key: str) -> int:
    kept = cache.client.get(PREFIX + key)
    if kept is None:
        message = "the entry measured was not kept: does the Redis of the platform answer?"
        raise MeasureError(message)
    return len(kept if isinstance(kept, bytes) else str(kept).encode())


def _whole_once(
    database: Database, project_id: UUID, cache: IndicatorsCache, *, cold: bool
) -> Read:
    """Read the project scope as the service does: from the entry of the project, whole."""
    with database.transaction() as session:
        reading = _reading(session, project_id)
        key = _key(session, reading, project_id)
        if cold:
            cache.client.delete(PREFIX + key)
        started = perf_counter()
        cached_scopes(session, reading.basis, reading.context, (PROJECT,), cache)
        seconds = perf_counter() - started
        return Read(seconds, _size(cache, key))


def _cell_once(database: Database, project_id: UUID, cache: IndicatorsCache, *, cold: bool) -> Read:
    """Read the project scope from an entry that holds it alone: what an entry by scope would do."""
    with database.transaction() as session:
        reading = _reading(session, project_id)
        key = _key(session, reading, project_id) + CELL
        if cold:
            cache.client.delete(PREFIX + key)
        started = perf_counter()
        # The steps of ``cached_scopes``: the subprojects and the key, the lookup, then the document
        # parsed or, an entry absent, computed and written, for the one scope.
        asked = _key(session, reading, project_id) + CELL
        found = cache.lookup(asked)
        if isinstance(found, str):
            json.loads(found)["scopes"][PROJECT]
        else:
            entry = day_entry(session, reading.basis, reading.context, (PROJECT,))
            cache.write(asked, json.dumps({"scopes": entry}, separators=(",", ":")))
        seconds = perf_counter() - started
        return Read(seconds, _size(cache, key))


def _series(
    once: Once, where: tuple[Database, UUID, IndicatorsCache], runs: int, *, cold: bool
) -> tuple[Sequence[float], int]:
    """Play a reading ``runs`` times, after one that warms the statements and keeps the entry."""
    once(*where, cold=True)
    reads = [once(*where, cold=cold) for _ in range(runs)]
    return [each.seconds for each in reads], reads[0].size


def _seconds(value: float) -> float:
    return round(value, 3)


def measure_cache(
    database: Database, project_id: UUID, cache: IndicatorsCache, runs: int
) -> tuple[Measure, ...]:
    """Measure the size of the entry of the day of the project, and its reading, cold and hot."""
    with database.transaction() as session:
        key = _key(session, _reading(session, project_id), project_id)
        subprojects = len(subproject_ids(session, project_id))
    scopes = subprojects + FIXED_SCOPES
    figures: dict[str, tuple[Sequence[float], int]] = {}
    try:
        for shape, once in (("whole", _whole_once), ("cell", _cell_once)):
            for heat in ("cold", "hot"):
                figures[f"{shape}-{heat}"] = _series(
                    once, (database, project_id, cache), runs, cold=heat == "cold"
                )
    finally:
        cache.client.delete(PREFIX + key, PREFIX + key + CELL)
    summaries = {name: summarise(durations) for name, (durations, _) in figures.items()}
    sizes = {name: size for name, (_, size) in figures.items()}
    labels = {"whole": "the whole entry", "cell": "one scope alone"}
    measures = [
        Measure(
            name=f"indicators cache, {labels[shape]}, {heat}",
            summary=summaries[f"{shape}-{heat}"],
            facts={"entry_bytes": sizes[f"{shape}-{heat}"]},
        )
        for shape in labels
        for heat in ("cold", "hot")
    ]
    medians = {name: summary.median for name, summary in summaries.items()}
    entry, cell = sizes["whole-hot"], sizes["cell-hot"]
    facts: dict[str, Scalar] = {
        "subprojects": subprojects,
        "scopes": scopes,
        "entry_bytes": entry,
        "cell_bytes": cell,
        "cold_whole_s": _seconds(medians["whole-cold"]),
        "cold_cell_s": _seconds(medians["cell-cold"]),
        "hot_whole_s": _seconds(medians["whole-hot"]),
        "hot_cell_s": _seconds(medians["cell-hot"]),
    }
    rows = tuple(
        {
            "subprojects": wanted,
            "entry_bytes": round(linear(cell, entry, scopes, wanted + FIXED_SCOPES)),
            "cold_whole_s": _seconds(
                linear(medians["cell-cold"], medians["whole-cold"], scopes, wanted + FIXED_SCOPES)
            ),
            "hot_whole_s": _seconds(
                linear(medians["cell-hot"], medians["whole-hot"], scopes, wanted + FIXED_SCOPES)
            ),
        }
        for wanted in SUBPROJECTS
    )
    notes = [
        f"rows linear through one scope and the whole entry of {subprojects} subprojects, no more"
    ]
    if medians["whole-cold"] > OBJECTIVE_S:
        alone = "within" if medians["cell-cold"] <= OBJECTIVE_S else "still over"
        notes.append(
            f"the cold reading of the whole entry exceeds the {OBJECTIVE_S:g} s objective (#3628); "
            f"one scope alone, cold, is {alone} it"
        )
    measures.append(Measure("indicators cache", facts=facts, rows=rows, notes=tuple(notes)))
    return tuple(measures)
