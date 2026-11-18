# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading kept of a marked revision (US-2270), and the marking that would keep it.

What ``document.py`` of #3173 tried, written again: the last marked revision of the project read
whole from its rows, then made and kept, then read from what is kept, whole and projected as the
grid of the estimate asks, each against the rows; the size of the body and of what is kept, and the
volume a platform of the volumes of §4.6.2 would keep. Then the marking of the current revision,
and the keeping of its main structure after it, as the marking would do in its task. Then the
comparison of the two last marked revisions, from the rows and from the readings kept, and the
filtered readings from the rows against the least a filter of the document would cost (the rule of
the third, #3168). Every write is rolled back: the witness is left as it was.
"""

from dataclasses import dataclass
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from measure.figures import ratio, summarise
from measure.report import Measure
from measure.target import MeasureError
from waterfall.api.comparison import comparison_body, kept_comparison
from waterfall.api.nodes import kept_body, node_body, nodes_body, read_body, whole_nodes
from waterfall.core.estimate.interface import ComparisonAsked, compare_revisions
from waterfall.core.planning.interface import NodeFilters, Place, list_records
from waterfall.core.planning.tables import StructureReading
from waterfall.core.projects.interface import Viewer
from waterfall.core.revisions.interface import (
    KEPT,
    MAIN,
    last_marked_revision,
    list_cost_structures,
    mark_revision,
    marked_revisions_at,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from measure.target import Target
    from waterfall.platform.database import Database

PROJECTS = 600
"""The projects a platform keeps over twenty years (§4.6.2, table 13)."""
MARKED_REVISIONS = 180
"""The marked revisions of a project, at most: a monthly review over fifteen years (§4.6.2)."""
OBJECTS = 10_000
"""The objects of a revision, tasks and lines, all its structures (§4.6.2)."""
REVISIONS_SPACE_GB = (150, 200)
"""The space of the revisions over twenty years (§4.6.2), which the readings kept add to."""

_GIGABYTE = 1e9
_MEGABYTE = 1e6
# What the grid of the estimate asks of a node (``ESTIMATE_FIELDS`` of the front), projected.
_FIELDS = frozenset(
    (
        "origin_risk_id",
        "task.progress",
        "task.base_amount",
        "task.reestimated_amount",
        "estimate_line.cost_category_label",
        "estimate_line.quantity",
        "estimate_line.base_amount",
        "estimate_line.reestimated_amount",
    )
)


@dataclass(frozen=True, slots=True)
class Volume:
    """What the readings kept of a platform of the volumes of §4.6.2 weigh.

    Scaled from one structure kept: its bytes by node, a revision of ``OBJECTS`` nodes, the marked
    revisions of every project; and the share of the space of the revisions it adds, at each bound.
    """

    bytes_per_node: float
    revision_mb: float
    platform_gb: float
    share_of_space: tuple[float, float]


def platform_volume(kept_bytes: int, nodes: int) -> Volume:
    """Scale the bytes kept of a structure of ``nodes`` nodes to a platform (§4.6.2)."""
    per_node = kept_bytes / nodes if nodes else 0.0
    revision = per_node * OBJECTS
    platform = revision * MARKED_REVISIONS * PROJECTS / _GIGABYTE
    low, high = REVISIONS_SPACE_GB
    return Volume(
        round(per_node, 1),
        round(revision / _MEGABYTE, 3),
        round(platform, 1),
        (round(platform / high, 3), round(platform / low, 3)),
    )


def marked_place(database: Database, target: Target) -> Place:
    """Give the main structure of the last marked revision of the project measured."""
    project_id = target.place.project_id
    with database.transaction() as session:
        revision_id = last_marked_revision(session, project_id)
        if revision_id is None:
            message = "the project measured has no marked revision"
            raise MeasureError(message)
        structures = list_cost_structures(
            session, project_id, revision_id, Viewer(target.manager_id, ())
        )
    main = next((each for each in structures if each.kind == MAIN), None)
    if main is None:
        message = "the last marked revision has no main structure"
        raise MeasureError(message)
    return Place(project_id, revision_id, main.structure_id)


def _timed(work: Callable[[], object]) -> float:
    started = perf_counter()
    work()
    return perf_counter() - started


def measure_kept(database: Database, target: Target, runs: int) -> tuple[Measure, ...]:
    """Measure a marked revision read whole from its rows, made and kept, then read as kept.

    In one transaction rolled back: the reading kept by the first whole reading is read by the
    next, as a process of the service reads it after another kept it.
    """
    place = marked_place(database, target)
    with Session(database.engine) as session:
        try:

            def rows() -> bytes:
                read = list_records(session, place, NodeFilters())
                return bytes(read_body(nodes_body(read)).body)

            body = rows()
            from_rows = [_timed(rows) for _ in range(runs)]
            made = _timed(lambda: whole_nodes(session, place, None))
            kept = [_timed(lambda: whole_nodes(session, place, None)) for _ in range(runs)]
            projected = [_timed(lambda: whole_nodes(session, place, _FIELDS)) for _ in range(runs)]

            def rows_projected() -> bytes:
                read = list_records(session, place, NodeFilters())
                return bytes(read_body(nodes_body(read, _FIELDS)).body)

            from_rows_projected = [_timed(rows_projected) for _ in range(runs)]
            document = session.scalar(
                select(StructureReading.document).where(
                    StructureReading.project_id == place.project_id,
                    StructureReading.structure_id == place.structure_id,
                )
            )
            nodes = len(list_records(session, place, NodeFilters()).items)
        finally:
            session.rollback()
    stored = 0 if document is None else len(document)
    rows_summary, kept_summary = summarise(from_rows), summarise(kept)
    volume = platform_volume(stored, nodes)
    return (
        Measure("marked revision read whole from its rows", rows_summary, {"nodes": nodes}),
        Measure(
            "marked revision made and kept",
            summarise([made]),
            {"body_mb": round(len(body) / _MEGABYTE, 2), "kept_mb": round(stored / _MEGABYTE, 3)},
        ),
        Measure(
            "marked revision read as kept",
            kept_summary,
            {"kept_over_rows": round(ratio(kept_summary.median, rows_summary.median), 3)},
        ),
        Measure(
            "marked revision read whole from its rows, projected", summarise(from_rows_projected)
        ),
        Measure(
            "marked revision read as kept, projected",
            summarise(projected),
            {
                "kept_over_rows": round(
                    ratio(summarise(projected).median, summarise(from_rows_projected).median), 3
                )
            },
        ),
        Measure(
            "volume of the readings kept",
            facts={
                "bytes_per_node": volume.bytes_per_node,
                "revision_mb": volume.revision_mb,
                "platform_gb": volume.platform_gb,
                "share_of_200_gb": volume.share_of_space[0],
                "share_of_150_gb": volume.share_of_space[1],
            },
            notes=(
                (
                    f"{OBJECTS} nodes a revision, {MARKED_REVISIONS} marked revisions a project, "
                    f"{PROJECTS} projects (§4.6.2), at the bytes by node of PRJ-001 kept"
                ),
            ),
        ),
    )


def measure_marking(database: Database, target: Target, runs: int) -> Measure:
    """Measure the marking of the current revision, then the keeping of its main structure.

    Each run in a transaction rolled back, as the task of the marking runs in one: the marking
    alone, then the reading made and kept of its main structure, which the marking would add.
    """
    place = target.place

    def once() -> tuple[float, float]:
        with Session(database.engine) as session:
            try:
                act = Act(None, utc_now())
                marking = _timed(
                    lambda: mark_revision(
                        session, place.revision_id, f"measure {uuid4().hex}", KEPT, act
                    )
                )
                keeping = _timed(lambda: whole_nodes(session, place, None))
            finally:
                session.rollback()
        return marking, keeping

    once()
    timed = [once() for _ in range(runs)]
    marking = summarise([each[0] for each in timed])
    keeping = summarise([each[1] for each in timed])
    return Measure(
        "mark the current revision",
        marking,
        {
            "keep_median_ms": round(keeping.median * 1000, 1),
            "with_keeping_median_ms": round((marking.median + keeping.median) * 1000, 1),
        },
        notes=("the minute of table 15 is the bound of a marking (§4.6.2)",),
    )


def _marked_pair(database: Database, target: Target) -> ComparisonAsked:
    """Give the comparison of the two last marked revisions of the project measured, whole."""
    with database.transaction() as session:
        marked = marked_revisions_at(session, target.place.project_id)
    if len(marked) < len(("base", "compared")):
        message = "the project measured has not two marked revisions"
        raise MeasureError(message)
    base, compared = sorted(marked, key=lambda each: (marked[each], each))[-2:]
    return ComparisonAsked(base, compared, NodeFilters())


def measure_comparison(database: Database, target: Target, runs: int) -> tuple[Measure, ...]:
    """Measure the comparison of the two last marked revisions, from the rows, then as kept.

    In one transaction rolled back: the first comparison from what is kept makes and keeps the
    readings of the two structures, the next read them. ``same_body`` tells the two bodies are the
    same, to the byte.
    """
    asked = _marked_pair(database, target)
    project_id = target.place.project_id
    with Session(database.engine) as session:
        try:

            def rows() -> bytes:
                found = compare_revisions(session, project_id, asked, node_body)
                return bytes(read_body(comparison_body(found, None)).body)

            def kept() -> bytes | None:
                body = kept_comparison(session, project_id, asked, None)
                return None if body is None else bytes(read_body(body).body)

            from_rows = rows()
            timed_rows = [_timed(rows) for _ in range(runs)]
            made = _timed(kept)
            timed_kept = [_timed(kept) for _ in range(runs)]
            same = kept() == from_rows
        finally:
            session.rollback()
    rows_summary, kept_summary = summarise(timed_rows), summarise(timed_kept)
    return (
        Measure(
            "comparison of two marked revisions from the rows",
            rows_summary,
            {"body_mb": round(len(from_rows) / _MEGABYTE, 2)},
        ),
        Measure("comparison of two marked revisions, their readings made", summarise([made])),
        Measure(
            "comparison of two marked revisions from the readings kept",
            kept_summary,
            {
                "kept_over_rows": round(ratio(kept_summary.median, rows_summary.median), 3),
                "same_body": same,
            },
        ),
    )


_LEVEL = 2
# The filtered readings of ``listNodes`` measured against the document: the grid of the planning
# (``kinds=task``), a search the harness of US-2220 asks, a level; each with the test by node the
# least a filter of the document would make.
_FILTERED: dict[str, tuple[NodeFilters, Callable[[dict[str, Any]], bool]]] = {
    "kinds=task": (NodeFilters(kinds=("task",)), lambda item: item["kind"] == "task"),
    "search=revue&progress=not_started,started": (
        NodeFilters(search="revue", progress=("not_started", "started")),
        lambda item: item["task"] is not None and "revue" in item["task"]["label"].lower(),
    ),
    f"max_level={_LEVEL}": (NodeFilters(max_level=_LEVEL), lambda item: item["level"] <= _LEVEL),
}
THIRD = 1 / 3
"""The share of a reading from the rows under which a filtered reading reads the document, #3168."""


def measure_filtered(database: Database, target: Target, runs: int) -> Measure:
    """Measure filtered readings of a marked revision from its rows, and from its reading kept.

    From the reading kept, the least a filter of the document would cost: the document read, its
    inscriptions joined, a test by node and the body of the nodes retained written; neither their
    ancestors, nor their totals, nor a sort, which a filter would add. Its share of the reading from
    the rows over the third, the filtered reading keeps the rows (#3168).
    """
    place = marked_place(database, target)
    rows: list[dict[str, str | float | bool]] = []
    with Session(database.engine) as session:
        try:
            whole_nodes(session, place, None)
            for name, (filters, test) in _FILTERED.items():

                def from_rows(filters: NodeFilters = filters) -> None:
                    read_body(nodes_body(list_records(session, place, filters)))

                def from_document(test: Callable[[dict[str, Any]], bool] = test) -> None:
                    read = kept_body(session, place)
                    if read is not None:
                        read["items"] = [each for each in read["items"] if test(each)]
                        read_body(read)

                from_rows()
                timed_rows = summarise([_timed(from_rows) for _ in range(runs)]).median
                timed_document = summarise([_timed(from_document) for _ in range(runs)]).median
                share = ratio(timed_document, timed_rows)
                rows.append(
                    {
                        "filter": name,
                        "rows_ms": round(timed_rows * 1000, 1),
                        "document_ms": round(timed_document * 1000, 1),
                        "document_over_rows": round(share, 3),
                        "under_the_third": share < THIRD,
                    }
                )
        finally:
            session.rollback()
    return Measure(
        "filtered readings of a marked revision, rows against the document",
        facts={"under_the_third": sum(1 for each in rows if each["under_the_third"])},
        rows=tuple(rows),
        notes=(
            (
                "document: the least a filter of the reading kept costs, without ancestors, "
                "totals nor sort; over the third of the rows, the filtered reading keeps the rows "
                "(#3168)"
            ),
        ),
    )
