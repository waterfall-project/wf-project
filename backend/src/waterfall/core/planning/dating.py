# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The engine replayed on a structure, and what it changes written, private to the module.

Every write of a node replays the engine (``scheduling``, pure) on the whole structure, under the
lock of the structure (EP-06, "Modules"): the tasks in the order of the plan, each on its
applicable calendar (``calendar_of``, WF-PLA-0010), the links, the planning start of the structure
and the constants of the units of the installation. What it computes is kept on the facet: the
dates of each task — those of a task in manual mode are its own and stay —, its float and its
criticality, and, for a summary, its duration — the work between its dates on its calendar, in
days (WF-PLA-0040) — and its mode, always automatic; the links in conflict are marked
(WF-PLA-0020). A recalculation advances no counter of a node (``LockVersion``).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, cast

from waterfall.core.planning.scheduling import (
    Duration,
    Lag,
    Link,
    Schedule,
    Structure,
    UnitConstants,
    WorkInstant,
    schedule,
)
from waterfall.core.planning.scheduling import Task as Planned
from waterfall.core.planning.tree import read_links
from waterfall.core.resource_settings.interface import get_duration_units

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import date
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import (
        DurationUnit,
        LagUnit,
        LinkType,
        ScheduledTask,
    )
    from waterfall.core.planning.tables import Task, TaskLink
    from waterfall.core.planning.tree import Tree

AUTOMATIC = "automatic"
MANUAL = "manual"
DAYS = "d"


def constants_of(session: Session) -> UnitConstants:
    """Read the constants of the units of the installation (WF-PLA-0160)."""
    units = get_duration_units(session).units
    return UnitConstants(units.hours_per_day, units.hours_per_week, units.days_per_month)


def in_days(hours: Decimal, constants: UnitConstants) -> Decimal:
    """Give hours of work in days of the installation, as the unit ``d`` counts them."""
    return hours / constants.hours_per_day


def days_of(task: Task, constants: UnitConstants) -> Decimal:
    """Give the duration of a task in days of work of the installation, elapsed units included."""
    hours = duration_of(task).hours(constants)
    return in_days(Decimal(hours.numerator) / Decimal(hours.denominator), constants)


def duration_of(task: Task) -> Duration:
    """Give the duration of a facet as the engine reads it, in the unit of its entry."""
    return Duration(task.duration_value, cast("DurationUnit", task.duration_unit))


@dataclass(frozen=True, slots=True)
class Replay:
    """A structure as the engine dates it: its tree, its links, the calendars and the constants."""

    tree: Tree
    links: list[TaskLink]
    calendars: dict[UUID, Applicable]
    constants: UnitConstants
    planning_start: date


def replay_of(
    session: Session,
    structure: tuple[UUID, UUID, date],
    tree: Tree,
    calendars: dict[UUID, Applicable],
) -> Replay:
    """Gather what the engine reads of a structure — its project, itself, its start — read."""
    project_id, structure_id, planning_start = structure
    links = read_links(session, project_id, structure_id)
    return Replay(tree, links, calendars, constants_of(session), planning_start)


def _planned(replay: Replay, node_id: UUID) -> Planned:
    tree = replay.tree
    task = tree.tasks[node_id]
    manual = task.scheduling_mode == MANUAL and not tree.is_summary(node_id)
    return Planned(
        task_id=node_id,
        parent_id=tree.nodes[node_id].parent_id,
        mode=MANUAL if manual else AUTOMATIC,
        duration=duration_of(task),
        calendar=replay.calendars[node_id].calendar,
        start=WorkInstant(task.start_date, task.start_hours) if manual else None,
        finish=WorkInstant(task.finish_date, task.finish_hours) if manual else None,
    )


def dated(replay: Replay) -> Schedule:
    """Run the engine on the structure; beyond the horizon, the schedule names the task."""
    tree = replay.tree
    links = tuple(
        Link(
            link.predecessor_id,
            link.successor_id,
            cast("LinkType", link.link_type),
            Lag(link.lag_value, cast("LagUnit", link.lag_unit)),
        )
        for link in replay.links
    )
    planned = tuple(_planned(replay, node_id) for node_id in tree.order if node_id in tree.tasks)
    return schedule(Structure(planned, links, replay.planning_start, replay.constants))


def _conflicts(pairs: Collection[tuple[UUID, UUID]]) -> dict[UUID, set[tuple[UUID, UUID]]]:
    """Give, by task, the links in conflict it is an end of, each by its two tasks."""
    held: dict[UUID, set[tuple[UUID, UUID]]] = {}
    for pair in pairs:
        for end in pair:
            held.setdefault(end, set()).add(pair)
    return held


def _kept(task: Task, placed: ScheduledTask, summary: Duration | None) -> bool:
    """Write on a facet what the engine computed for it; tell whether its schedule moved."""
    values: dict[str, object] = {
        "start_date": placed.start.day,
        "start_hours": placed.start.hours,
        "finish_date": placed.finish.day,
        "finish_hours": placed.finish.hours,
        "total_float_days": placed.total_float,
        "is_critical": placed.is_critical,
    }
    moved = any(getattr(task, name) != value for name, value in values.items())
    if summary is not None:
        values |= {
            "scheduling_mode": AUTOMATIC,
            "duration_value": summary.value,
            "duration_unit": summary.unit,
        }
    for name, value in values.items():
        if getattr(task, name) != value:
            setattr(task, name, value)
    return moved


def kept(replay: Replay, computed: Schedule) -> set[UUID]:
    """Write what the engine computed on the facets and the links; give the tasks it moved.

    A task moves when its dates, its float, its criticality or its links in conflict change.
    """
    tree = replay.tree
    in_conflict = {(each.predecessor_id, each.successor_id) for each in computed.link_conflicts}
    before = _conflicts(
        [(link.predecessor_id, link.successor_id) for link in replay.links if link.in_conflict]
    )
    after = _conflicts(in_conflict)
    for link in replay.links:
        flagged = (link.predecessor_id, link.successor_id) in in_conflict
        if link.in_conflict != flagged:
            link.in_conflict = flagged
    moved: set[UUID] = set()
    for task_id, placed in computed.tasks.items():
        summary = None
        if tree.is_summary(task_id):
            summary = Duration(in_days(placed.work_hours, replay.constants), DAYS)
        changed = _kept(tree.tasks[task_id], placed, summary)
        if changed or before.get(task_id, set()) != after.get(task_id, set()):
            moved.add(task_id)
    return moved
