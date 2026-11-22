# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The writes: a cell entered, the opening of a revision; each one rolled back."""

from dataclasses import dataclass
from decimal import Decimal
from statistics import median
from time import perf_counter
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from measure.figures import ratio, summarise
from measure.report import Measure
from measure.target import MeasureError
from waterfall.core.planning.interface import (
    Duration,
    NodeFilters,
    Place,
    TaskEntry,
    Writer,
    list_nodes,
    list_records,
    update_task_facet,
)
from waterfall.core.projects.interface import Viewer
from waterfall.core.revisions.interface import RevisionToAbandon, abandon_revision, create_revision
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from measure.target import Target
    from waterfall.core.planning.interface import NodeView
    from waterfall.platform.database import Database

_DURATION_STEP = Decimal(3)
_UNIT = "d"


@dataclass(frozen=True, slots=True)
class Written:
    """What a write took, in seconds, and what it moved: the tasks it redated, the summaries."""

    seconds: float
    rescheduled: int
    ancestors: int


def _followers(nodes: tuple[NodeView, ...]) -> dict[UUID, set[UUID]]:
    """Give, for each node, the nodes that name it as a predecessor."""
    followers: dict[UUID, set[UUID]] = {}
    for each in nodes:
        for link in each.predecessors:
            followers.setdefault(link.predecessor_id, set()).add(each.node_id)
    return followers


def _downstream(start: UUID, followers: dict[UUID, set[UUID]]) -> int:
    """Count the nodes a change of ``start`` can reach by the links, directly or not."""
    reached: set[UUID] = set()
    pending = [start]
    while pending:
        for follower in followers.get(pending.pop(), ()):
            if follower not in reached:
                reached.add(follower)
                pending.append(follower)
    return len(reached)


def entered_leaf(nodes: tuple[NodeView, ...]) -> NodeView:
    """Pick a task a cell can be entered in, which a duration redates: a leaf, scheduled, in days.

    The one with the most successors by the links, the first in the order of the structure among
    equals: a duration that redates needs successors, and the leaf of a witness loaded again is
    the same.
    """
    followers = _followers(nodes)
    candidates = [
        each
        for each in nodes
        if each.task is not None
        and not each.task.is_summary
        and not each.task.is_milestone
        and each.task.scheduling_mode != "manual"
        and each.task.duration_unit == _UNIT
        and "task.duration" in each.editable_fields
    ]
    if not candidates:
        message = "the structure has no task in days that a duration can be entered in"
        raise MeasureError(message)
    return max(candidates, key=lambda each: _downstream(each.node_id, followers))


def entry(leaf: NodeView, kind: str) -> TaskEntry:
    """Give the entry of a cell of a leaf: its label lengthened, or its duration stepped."""
    task = leaf.task
    if task is None:
        message = "a leaf is a task"
        raise ValueError(message)
    if kind == "label":
        return TaskEntry(
            label=f"{task.label} x", sent=frozenset({"label"}), lock_version=leaf.lock_version
        )
    return TaskEntry(
        duration=Duration(task.duration_value + _DURATION_STEP, _UNIT),
        sent=frozenset({"duration"}),
        lock_version=leaf.lock_version,
    )


def write_once(database: Database, place: Place, leaf: NodeView, kind: str) -> Written:
    """Enter one cell, as a route does, and roll the transaction back: nothing stays written."""
    entered = entry(leaf, kind)
    with Session(database.engine) as session:
        try:
            started = perf_counter()
            written = update_task_facet(
                session, place, leaf.node_id, entered, Writer(Act(None, utc_now()), None)
            )
            session.flush()
            seconds = perf_counter() - started
        finally:
            session.rollback()
    return Written(seconds, len(written.rescheduled), len(written.ancestors))


def _read_median(database: Database, place: Place, runs: int) -> float:
    durations: list[float] = []
    for _ in range(runs):
        started = perf_counter()
        with database.transaction() as session:
            list_records(session, place, NodeFilters())
        durations.append(perf_counter() - started)
    return median(durations)


def measure_writes(database: Database, place: Place, runs: int) -> tuple[Measure, ...]:
    """Measure a label and a duration entered, each against one whole reading of the structure.

    A label touches the task; a duration that redates moves its successors and the summaries above
    them: the ratio to a reading is what the grids pay for a cell (#3169).
    """
    with database.transaction() as session:
        leaf = entered_leaf(list_nodes(session, place, NodeFilters(kinds=("task",))).items)
    write_once(database, place, leaf, "label")
    reading = _read_median(database, place, runs)
    measures: list[Measure] = []
    for kind, name in (("label", "write a label"), ("duration", "write a duration, redating")):
        runs_of = [write_once(database, place, leaf, kind) for _ in range(runs)]
        summary = summarise([each.seconds for each in runs_of])
        notes = (
            ("the duration redated no task: its leaf has no successor, the figure is a label's",)
            if kind == "duration" and runs_of[0].rescheduled == 0
            else ()
        )
        measures.append(
            Measure(
                name=name,
                summary=summary,
                facts={
                    "write_over_read": round(ratio(summary.median, reading), 2),
                    "rescheduled": runs_of[0].rescheduled,
                    "ancestors": runs_of[0].ancestors,
                },
                notes=notes,
            )
        )
    return tuple(measures)


def _rolled_back[T](database: Database, work: Callable[[Session], T]) -> T:
    with Session(database.engine) as session:
        try:
            return work(session)
        finally:
            session.rollback()


def _open_revision(session: Session, target: Target, viewer: Viewer, act: Act) -> float:
    """Abandon the current revision, which the opening forbids, then time the opening itself."""
    abandon_revision(
        session,
        target.place.project_id,
        RevisionToAbandon(target.place.revision_id, target.revision_lock_version),
        act,
        viewer,
    )
    session.flush()
    started = perf_counter()
    create_revision(session, target.place.project_id, act, viewer)
    session.flush()
    return perf_counter() - started


def measure_opening(database: Database, target: Target, runs: int) -> Measure:
    """Measure the opening of a revision: a copy of the last marked one, structures and lines.

    The project has a current revision, which the opening refuses: it is abandoned first, inside
    the transaction, and everything is rolled back, the abandonment too. One opening warms the
    statements and the connections first, and is not counted.
    """
    manager: UUID = target.manager_id
    viewer = Viewer(manager, ())

    def once() -> float:
        return _rolled_back(
            database,
            lambda session: _open_revision(session, target, viewer, Act(None, utc_now())),
        )

    once()
    durations = [once() for _ in range(runs)]
    return Measure(name="open a revision", summary=summarise(durations))
