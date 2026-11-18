# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The comparison of the current revision with the marked one it copies (EP-27, US-2390).

What #3168 asks to instruct its option 3 — the difference kept at the writing, by a fingerprint of
each node —: the duration of ``compareRevisions`` of the current revision of the project against
the last marked one, which the current one copied at its opening, split into the part of the two
readings, that of the union and that of the body; and the nodes that differ between them, out of
all those of the union. Three comparisons: the whole one, unfiltered, read from the rows of both
structures (``read_structure``) — the comparison before option 1, the one the threshold of #3168
("Pour trancher", its first line) is read on —; the same, as the grid of the estimate asks it
since option 1 — the reading kept of the base and the columns of the current revision (US-2270) —;
and that of the tasks (``kinds=task``), as the grid of the planning asks it, read from the rows.

The readings are timed apart from the comparison, by the functions it calls, and the union is what
the comparison takes beyond them: a subtraction, the core giving no time of its union alone. The
two are timed in the same transaction, one after the other, the second on what the first warmed:
their order alternates from one run to the next, so that each is the first half the time; their
spreads are given, and a union the subtraction would give under nought is said. Everything is
rolled back: the reading kept the first comparison makes of the base is not left behind.
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
from waterfall.core.projects.interface import Viewer
from waterfall.core.revisions.interface import read_revision

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
_MODIFIED = "modified"
_DATES = ("dates",)
UNION_AND_BODY = 0.15
"""The share of the union and the body under which keeping the readings takes most of the gain
(#3168, "Pour trancher", its first line), read on the comparison before option 1."""
HALF = 0.5
"""The share of the nodes differing over which following the differences gains little (#3168)."""


def _ms(seconds: float) -> float:
    return round(seconds * _MILLISECOND, 1)


@dataclass(frozen=True, slots=True)
class Split:
    """A comparison in its three parts, in seconds: its two readings, its union, its body.

    ``compared`` the whole of the core, its readings included; the union is what it takes beyond
    them: the union and the marks, the totals and the differences of amounts, and the nodes placed
    in the body. The body is the response written and rendered. The total is the comparison and
    its body, which the parts share: readings timed over the comparison that includes them leave
    the union at nought, which ``clamped`` says, and count in the shares for the comparison alone.
    """

    readings: float
    compared: float
    body: float

    @property
    def union(self) -> float:
        """The comparison beyond its readings, never under nought."""
        return max(self.compared - self.readings, 0.0)

    @property
    def clamped(self) -> bool:
        """Whether the readings were timed over the comparison that includes them."""
        return self.compared < self.readings

    @property
    def total(self) -> float:
        """The comparison and its body, in seconds."""
        return self.compared + self.body

    def facts(self) -> dict[str, Scalar]:
        """Give each part in milliseconds and its share of the total, the shares summing to one."""
        total = self.total
        return {
            "total_ms": _ms(total),
            "readings_ms": _ms(self.readings),
            "union_ms": _ms(self.union),
            "body_ms": _ms(self.body),
            "readings_share": round(ratio(min(self.readings, self.compared), total), 3),
            "union_share": round(ratio(self.union, total), 3),
            "body_share": round(ratio(self.body, total), 3),
            "union_and_body_share": round(ratio(self.union + self.body, total), 3),
            "union_clamped": self.clamped,
        }


def split_of(readings: float, compared: float, body: float) -> Split:
    """Split a comparison: ``compared`` the whole of the core, its readings included."""
    return Split(readings, compared, body)


@dataclass(frozen=True, slots=True)
class Differing:
    """The nodes of one kind in the union of a comparison, and those that differ, by their mark.

    Of the modified ones: ``dated`` those whose changes are the dates alone — a task redated by a
    cascade, or a summary whose span moves, even when what is under it changes too —; ``content``
    those with no value of their own changed, modified by what is under them alone; ``other`` the
    rest, a change other than the dates among theirs.
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

    @property
    def other(self) -> int:
        """The modified ones neither by their dates alone nor by what is under them alone."""
        return self.modified - self.dated - self.content

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
            "other_changes": self.other,
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
        if mark == _MODIFIED and changes == _DATES:
            counts["dated"] += 1
        elif mark == _MODIFIED and not changes:
            counts["content"] += 1
    return tuple(
        Differing(
            kind,
            counts["nodes"],
            counts["added"],
            counts["removed"],
            counts[_MODIFIED],
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
            "dates_only: modified by their dates alone, a task redated by a cascade or a summary "
            "whose span moves — counted there even when what is under it changes too —; "
            "content_only: no value of their own changed, modified by what is under them alone; "
            "other_changes: the rest of the modified. Over half the nodes differing, following "
            "the differences gains little (#3168, option 3)"
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


_PARTS_NOTE = (
    "readings: the two structures read apart, as the comparison reads them; union: the rest of "
    "the comparison of the core, by subtraction, the two timed in an order that alternates from "
    "one run to the next; body: the response written and rendered. The parts are those of the "
    "median total, the readings and the body by their medians, the union what remains; "
    "union_clamped the readings over the comparison, runs_union_negative the runs where they were"
)
_ROWS_WHOLE = (
    "before option 1 of #3168: the threshold of its first line is read here. Under "
    f"{UNION_AND_BODY:.0%} of union and body, keeping the readings takes most of the gain"
)
_KEPT_WHOLE = (
    "after option 1 of #3168, as the grid of the estimate asks it: the reading kept of the base "
    "(json.loads) and the columns of the current revision; no threshold of #3168 applies to it"
)
_TASKS_ROWS = (
    "as the grid of the planning asks it, the threshold of #3168 read on the tasks alone. "
    "read_structure drops kinds (core/planning/reading.py, replace(filters, kinds=None)): each "
    "structure is read whole, and kinds=task filters the order and the body alone"
)


def _split_measure(
    name: str,
    runs: Sequence[_Run],
    facts: Mapping[str, Scalar],
    note: str,
    *,
    threshold: bool,
) -> Measure:
    """Give a comparison measured: its whole per run, and its parts on the median of that whole."""
    summary = summarise([each.compared + each.body for each in runs])
    readings = summarise([each.readings for each in runs])
    compared = summarise([each.compared for each in runs])
    body = summarise([each.body for each in runs]).median
    split = split_of(readings.median, summary.median - body, body)
    measured: dict[str, Scalar] = {
        **facts,
        **split.facts(),
        "readings_spread_ms": _ms(readings.spread),
        "compared_spread_ms": _ms(compared.spread),
        "runs_union_negative": sum(each.compared < each.readings for each in runs),
    }
    if threshold:
        measured["union_and_body_under_threshold"] = (
            ratio(split.union + split.body, split.total) < UNION_AND_BODY
        )
    return Measure(name, summary, measured, notes=(note, _PARTS_NOTE))


def _copied(database: Database, target: Target, base: Place) -> None:
    """Refuse a current revision that is not the copy of the last marked one."""
    current = target.place
    with database.transaction() as session:
        read = read_revision(
            session, current.project_id, current.revision_id, Viewer(target.manager_id, ())
        )
    if read.source_revision_id != base.revision_id:
        message = "the current revision measured is not the copy of the last marked one"
        raise MeasureError(message)


def measure_current(database: Database, target: Target, runs: int) -> tuple[Measure, ...]:
    """Measure the comparison of the current revision with the last marked one, in its parts.

    The current revision is the copy of that marked one (``source_revision_id``), or the measure
    refuses. In one transaction rolled back: the first comparison from what is kept makes and
    keeps the reading of the base, which the next read, as the service reads it after the first
    comparison kept it; one comparison of each kind warms, and is not counted.
    """
    base = marked_place(database, target)
    _copied(database, target, base)
    current = target.place
    whole = ComparisonAsked(base.revision_id, current.revision_id, NodeFilters())
    tasks = ComparisonAsked(base.revision_id, current.revision_id, NodeFilters(kinds=_TASKS))
    with Session(database.engine) as session:
        try:
            measured = _measured(session, (base, current), (whole, tasks), runs)
        finally:
            session.rollback()
    rows_runs, kept_runs, tasks_runs, body = measured
    differing = differing_of(body["items"])
    nodes = {"nodes": sum(each.nodes for each in differing)}
    named = "comparison of the current revision with the marked one it copies"
    return (
        _split_measure(
            f"{named}, whole, from the rows", rows_runs, nodes, _ROWS_WHOLE, threshold=True
        ),
        _split_measure(
            f"{named}, whole, from what is kept", kept_runs, nodes, _KEPT_WHOLE, threshold=False
        ),
        _split_measure(
            f"{named}, kinds=task, from the rows",
            tasks_runs,
            {"tasks": next((each.nodes for each in differing if each.kind == "task"), 0)},
            _TASKS_ROWS,
            threshold=True,
        ),
        _differing_measure(differing),
    )


def _rendered(found: Comparison) -> None:
    """Write a comparison read from the rows, and render it, as the route does."""
    read_body(comparison_body(found, None))


def _run[T](
    readings: Callable[[], object],
    compared: Callable[[], T],
    rendered: Callable[[T], object],
    *,
    readings_first: bool,
) -> tuple[_Run, T]:
    """Time the readings and the comparison, in the order given, then the body of the second."""
    if readings_first:
        _, read = _timed(readings)
        found, took = _timed(compared)
    else:
        found, took = _timed(compared)
        _, read = _timed(readings)
    _, rendering = _timed(rendered, found)
    return _Run(read, took, rendering), found


def _measured(
    session: Session,
    places: tuple[Place, Place],
    asked: tuple[ComparisonAsked, ComparisonAsked],
    runs: int,
) -> tuple[list[_Run], list[_Run], list[_Run], dict[str, Any]]:
    """Time each run of the three comparisons, and give the last body written from what is kept."""
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

    def rows_readings(filters: NodeFilters) -> Callable[[], None]:
        def read() -> None:
            read_structure(session, current, filters)
            read_structure(session, base, filters)

        return read

    def rows(filters: ComparisonAsked) -> Callable[[], Comparison]:
        return lambda: compare_revisions(session, project_id, filters, node_body)

    body = kept()
    compare_revisions(session, project_id, whole, node_body)
    compare_revisions(session, project_id, tasks, node_body)
    rows_runs: list[_Run] = []
    kept_runs: list[_Run] = []
    tasks_runs: list[_Run] = []
    for each in range(runs):
        first = each % 2 == 0
        run, _ = _run(rows_readings(whole.filters), rows(whole), _rendered, readings_first=first)
        rows_runs.append(run)
        run, body = _run(kept_readings, kept, read_body, readings_first=first)
        kept_runs.append(run)
        run, _ = _run(rows_readings(tasks.filters), rows(tasks), _rendered, readings_first=first)
        tasks_runs.append(run)
    return rows_runs, kept_runs, tasks_runs, body
