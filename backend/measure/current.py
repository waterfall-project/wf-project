# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of the current revision with the marked one it copies (EP-27, US-2390).

What #3168 asks to instruct its option 3 — the difference kept at the writing, by a fingerprint of
each node —: the duration of ``compareRevisions`` of the current revision of the project against
the last marked one, which the current one copied at its opening, split into the part of the two
readings, that of the union and that of the body; and the nodes that differ between them, out of
all those of the union. Two comparisons, those the grids ask: the whole one, unfiltered, as the
grid of the estimate asks it — the reading kept of the base and the columns of the current
revision (US-2270) —, and that of the tasks (``kinds=task``), as the grid of the planning asks it,
which reads the rows of both. The parts are timed apart from the comparison, by the functions it
calls; the union is what the comparison takes beyond its readings. Everything is rolled back: the
reading kept the first comparison makes of the base is not left behind.
"""

from collections import Counter
from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from measure.document import marked_place
from measure.figures import ratio, summarise
from measure.report import Measure
from measure.target import MeasureError
from waterfall.api.comparison import comparison_body, kept_comparison
from waterfall.api.nodes import kept_body, node_body, nodes_body, read_body
from waterfall.core.estimate.interface import ComparisonAsked, compare_revisions
from waterfall.core.planning.interface import NodeFilters, list_records, read_structure

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence
    from typing import Any

    from measure.report import Scalar
    from measure.target import Target
    from waterfall.core.estimate.interface import Comparison
    from waterfall.core.planning.interface import Place
    from waterfall.platform.database import Database

_MILLISECOND = 1000
_TASKS = ("task",)
_UNCHANGED = "unchanged"
_DATES = ("dates",)
UNION_AND_BODY = 0.15
"""The share of the union and the body under which keeping the readings takes most of the gain
(#3168, "Pour trancher", option 1, 2 or 3)."""
HALF = 0.5
"""The share of the nodes differing over which following the differences gains little (#3168)."""


@dataclass(frozen=True, slots=True)
class Split:
    """A comparison in its three parts, in seconds: its two readings, its union, its body.

    The union is all the comparison computes beyond its readings: the union and the marks, the
    totals and the differences of amounts, and, from what is kept, the nodes placed in the body.
    The body is the response written and rendered.
    """

    readings: float
    union: float
    body: float

    @property
    def total(self) -> float:
        """The three parts, in seconds."""
        return self.readings + self.union + self.body

    def facts(self) -> dict[str, Scalar]:
        """Give each part in milliseconds and its share of the whole."""
        total = self.total
        return {
            "readings_ms": round(self.readings * _MILLISECOND, 1),
            "union_ms": round(self.union * _MILLISECOND, 1),
            "body_ms": round(self.body * _MILLISECOND, 1),
            "readings_share": round(ratio(self.readings, total), 3),
            "union_share": round(ratio(self.union, total), 3),
            "body_share": round(ratio(self.body, total), 3),
            "union_and_body_share": round(ratio(self.union + self.body, total), 3),
        }


def split_of(readings: float, compared: float, body: float) -> Split:
    """Split a comparison: ``compared`` the whole of the core, its readings included.

    Its union is what it takes beyond the readings timed apart, never under nought: two timings
    of one reading differ by their noise.
    """
    return Split(readings, max(compared - readings, 0.0), body)


@dataclass(frozen=True, slots=True)
class Differing:
    """The nodes of one kind in the union of a comparison, and those that differ, by their mark.

    ``dated`` the modified ones whose dates alone change — redated by a cascade, or a summary
    whose span moves —; ``content`` those modified by what is under them alone.
    """

    kind: str
    nodes: int
    added: int
    removed: int
    modified: int
    dated: int
    content: int

    @property
    def differing(self) -> int:
        """The nodes added, removed or modified."""
        return self.added + self.removed + self.modified

    def row(self) -> dict[str, Scalar]:
        """Give the counts of the kind as a row of the report."""
        return {
            "kind": self.kind,
            "nodes": self.nodes,
            "differing": self.differing,
            "added": self.added,
            "removed": self.removed,
            "modified": self.modified,
            "dates_only": self.dated,
            "content_only": self.content,
        }


def differing_of(items: Iterable[Mapping[str, Any]]) -> tuple[Differing, ...]:
    """Count the nodes of a comparison written (``ComparedNode``) by kind, in the order of kinds."""
    counted: dict[str, Counter[str]] = {}
    for item in items:
        counts = counted.setdefault(item["kind"], Counter())
        counts["nodes"] += 1
        mark = item["difference"]
        if mark == _UNCHANGED:
            continue
        counts[mark] += 1
        changes = tuple(item["changes"])
        if mark == "modified" and changes == _DATES:
            counts["dated"] += 1
        elif mark == "modified" and not changes:
            counts["content"] += 1
    return tuple(
        Differing(
            kind,
            counts["nodes"],
            counts["added"],
            counts["removed"],
            counts["modified"],
            counts["dated"],
            counts["content"],
        )
        for kind, counts in sorted(counted.items())
    )


def _differing_measure(kinds: Sequence[Differing]) -> Measure:
    nodes = sum(each.nodes for each in kinds)
    differing = sum(each.differing for each in kinds)
    modified = sum(each.modified for each in kinds)
    dated = sum(each.dated for each in kinds)
    notes = [
        (
            "dates_only: modified by their dates alone, redated by a cascade or a summary whose "
            "span moves; content_only: modified by what is under them alone. Over half the nodes "
            "differing, following the differences gains little (#3168, option 3)"
        )
    ]
    if differing == 0:
        notes.append("the current revision is the copy of the marked one, unchanged")
    return Measure(
        "nodes differing between the current revision and the marked one it copies",
        facts={
            "nodes": nodes,
            "differing": differing,
            "differing_share": round(ratio(differing, nodes), 3),
            "over_half": ratio(differing, nodes) > HALF,
            "dates_only_share_of_modified": round(ratio(dated, modified), 3),
        },
        rows=tuple(each.row() for each in kinds),
        notes=tuple(notes),
    )


def _timed[**P, T](work: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> tuple[T, float]:
    started = perf_counter()
    found = work(*args, **kwargs)
    return found, perf_counter() - started


@dataclass(frozen=True, slots=True)
class _Run:
    readings: float
    compared: float
    body: float


def _split_measure(name: str, runs: Sequence[_Run], facts: Mapping[str, Scalar]) -> Measure:
    """Give a comparison measured: its whole per run, and its parts by their medians."""
    split = split_of(
        summarise([each.readings for each in runs]).median,
        summarise([each.compared for each in runs]).median,
        summarise([each.body for each in runs]).median,
    )
    return Measure(
        name,
        summarise([each.compared + each.body for each in runs]),
        {**facts, **split.facts()},
        notes=(
            (
                "readings: the two structures read apart, as the comparison reads them; union: "
                "the rest of the comparison of the core; body: the response written and rendered. "
                f"Under {UNION_AND_BODY:.0%} of union and body, keeping the readings takes most "
                "of the gain (#3168)"
            ),
        ),
    )


def measure_current(database: Database, target: Target, runs: int) -> tuple[Measure, ...]:
    """Measure the comparison of the current revision with the last marked one, in its parts.

    In one transaction rolled back: the first whole comparison makes and keeps the reading of the
    base, which the next read, as the service reads it after the first comparison kept it; one
    comparison of each kind warms, and is not counted.
    """
    base = marked_place(database, target)
    current = target.place
    whole = ComparisonAsked(base.revision_id, current.revision_id, NodeFilters())
    tasks = ComparisonAsked(base.revision_id, current.revision_id, NodeFilters(kinds=_TASKS))
    with Session(database.engine) as session:
        try:
            measured = _measured(session, (base, current), (whole, tasks), runs)
        finally:
            session.rollback()
    kept_runs, rows_runs, body = measured
    differing = differing_of(body["items"])
    nodes = {"nodes": sum(each.nodes for each in differing)}
    return (
        _split_measure(
            "comparison of the current revision with the marked one it copies, whole",
            kept_runs,
            nodes,
        ),
        _split_measure(
            "comparison of the current revision with the marked one it copies, kinds=task",
            rows_runs,
            {"tasks": next((each.nodes for each in differing if each.kind == "task"), 0)},
        ),
        _differing_measure(differing),
    )


def _rendered(found: Comparison) -> None:
    """Write a comparison read from the rows, and render it, as the route does."""
    read_body(comparison_body(found, None))


def _measured(
    session: Session,
    places: tuple[Place, Place],
    asked: tuple[ComparisonAsked, ComparisonAsked],
    runs: int,
) -> tuple[list[_Run], list[_Run], dict[str, Any]]:
    """Time each run of the two comparisons, and give the last whole body written."""
    base, current = places
    whole, tasks = asked
    project_id = current.project_id

    def kept() -> dict[str, Any]:
        found = kept_comparison(session, project_id, whole, None)
        if found is None:
            message = "the marked revision compared has no reading kept"
            raise MeasureError(message)
        return found

    def kept_readings() -> None:
        kept_body(session, base)
        nodes_body(list_records(session, current, NodeFilters()))

    def rows_readings() -> None:
        read_structure(session, current, tasks.filters)
        read_structure(session, base, tasks.filters)

    body = kept()
    compare_revisions(session, project_id, tasks, node_body)
    kept_runs: list[_Run] = []
    rows_runs: list[_Run] = []
    for _ in range(runs):
        _, readings = _timed(kept_readings)
        body, compared = _timed(kept)
        _, rendering = _timed(read_body, body)
        kept_runs.append(_Run(readings, compared, rendering))
        _, readings = _timed(rows_readings)
        found, compared = _timed(compare_revisions, session, project_id, tasks, node_body)
        _, rendering = _timed(_rendered, found)
        rows_runs.append(_Run(readings, compared, rendering))
    return kept_runs, rows_runs, body
