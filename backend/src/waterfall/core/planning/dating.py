# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The engine replayed on a structure, and what it changes written, private to the module.

Every write of a node replays the engine (``scheduling``, pure) on the whole structure, under the
lock of the structure (EP-06, "Modules"): the tasks in the order of the plan, each on its
applicable calendar (``calendar_of``, WF-PLA-0010), the links, the planning start of the structure
and the constants of the units of the installation. What it computes is kept on the facet: the
dates of each task — those of a task in manual mode are its own and stay —, its float and its
criticality, and, for a summary, its duration — the work between its dates on its calendar, in
days (WF-PLA-0040) — and its mode, always automatic; the links in conflict are marked, and the
tasks in manual mode each cannot satisfy kept (``task_link_conflict``, WF-PLA-0020, #3984). A
recalculation advances no counter of a node (``LockVersion``).
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, cast

from sqlalchemy import delete, insert, select, tuple_

from waterfall.core.planning.scheduling import (
    Duration,
    Lag,
    Link,
    LinkCycleError,
    LinkForbiddenError,
    Schedule,
    Structure,
    UnitConstants,
    WorkInstant,
    decimal_of,
    schedule,
)
from waterfall.core.planning.scheduling import Task as Planned
from waterfall.core.planning.tables import TaskLinkConflict
from waterfall.core.planning.tree import Conflict, read_links
from waterfall.core.resource_settings.interface import get_duration_units
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.calendars import Applicable
    from waterfall.core.planning.scheduling import (
        DurationUnit,
        LagUnit,
        LinkType,
        Origin,
        ScheduledTask,
    )
    from waterfall.core.planning.tables import Task, TaskLink
    from waterfall.core.planning.tree import TaskColumns, Tree

AUTOMATIC = "automatic"
MANUAL = "manual"
DAYS = "d"
PROJECT_HORIZON_EXCEEDED = "PROJECT_HORIZON_EXCEEDED"
LINK_CYCLE = "LINK_CYCLE"
LINK_FORBIDDEN = "LINK_FORBIDDEN"


def constants_of(session: Session) -> UnitConstants:
    """Read the constants of the units of the installation (WF-PLA-0160)."""
    units = get_duration_units(session).units
    return UnitConstants(units.hours_per_day, units.hours_per_week, units.days_per_month)


def in_days(hours: Decimal | Fraction, constants: UnitConstants) -> Decimal:
    """Give hours of work in days of the installation, as the unit ``d`` counts them.

    Rendered as the engine renders its hours, whatever the context of ``decimal`` (#2460).
    """
    return decimal_of(Fraction(hours) / Fraction(constants.hours_per_day))


def days_of(task: TaskColumns, constants: UnitConstants) -> Decimal:
    """Give the duration of a task in days of work of the installation, elapsed units included."""
    return in_days(duration_of(task).hours(constants), constants)


def duration_of(task: TaskColumns) -> Duration:
    """Give the duration of a facet as the engine reads it, in the unit of its entry."""
    return Duration(task.duration_value, cast("DurationUnit", task.duration_unit))


@dataclass(frozen=True, slots=True)
class Replay:
    """A structure as the engine dates it: its tree, its links, the calendars and the constants.

    ``place`` its project and itself, where the links in conflict are written (``kept``).
    """

    place: tuple[UUID, UUID]
    tree: Tree
    links: list[TaskLink]
    calendars: dict[UUID, Applicable]
    constants: UnitConstants
    planning_start: date


def horizon_exceeded(
    node_id: UUID | None, label: str, row: int | None = None
) -> UnprocessableError:
    """Give the refusal of a project that would end beyond fifteen years, the task named.

    ``row`` the row of the block of a paste that writes the task, absent from the refusal of any
    other write (``Problem.params``, #3624).
    """
    named: dict[str, object] = {
        "node_id": None if node_id is None else str(node_id),
        "label": label,
    }
    if row is not None:
        named["row"] = row
    return UnprocessableError(PROJECT_HORIZON_EXCEEDED, {"task": named})


def replay_of(
    session: Session,
    structure: tuple[UUID, UUID, date],
    tree: Tree,
    calendars: dict[UUID, Applicable],
) -> Replay:
    """Gather what the engine reads of a structure — its project, itself, its start — read."""
    project_id, structure_id, planning_start = structure
    links = read_links(session, project_id, structure_id)
    return Replay(
        (project_id, structure_id), tree, links, calendars, constants_of(session), planning_start
    )


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


def dated(replay: Replay, origin: Origin = None) -> Schedule:
    """Run the engine on the structure; beyond the horizon, the schedule names the task.

    A loop of links is refused naming its tasks, from ``origin`` — the task whose predecessors
    are entered —, by their node and their label (422 ``LINK_CYCLE``, ``params.cycle``); a link
    between a summary and its subordinate without a parameter (422 ``LINK_FORBIDDEN``,
    WF-PLA-0030, WF-PLA-0040).
    """
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
    structure = Structure(planned, links, replay.planning_start, replay.constants)
    try:
        return schedule(structure, origin)
    except LinkCycleError as loop:
        cycle = [{"node_id": str(each), "label": tree.tasks[each].label} for each in loop.cycle]
        raise UnprocessableError(LINK_CYCLE, {"cycle": cycle}) from None
    except LinkForbiddenError:
        raise UnprocessableError(LINK_FORBIDDEN) from None


def _ends(conflicts: Collection[Conflict]) -> dict[UUID, set[Conflict]]:
    """Give, by task, the conflicts it is named by: as the predecessor, or as the manual task."""
    held: dict[UUID, set[Conflict]] = {}
    for conflict in conflicts:
        for end in (conflict.predecessor_id, conflict.manual_node_id):
            held.setdefault(end, set()).add(conflict)
    return held


def _conflicts_kept(session: Session, replay: Replay, computed: Schedule) -> frozenset[Conflict]:
    """Write the links in conflict the engine found, the manual task each names; give the former.

    Each link bears ``in_conflict`` as soon as it names a task in manual mode, which its row of
    ``task_link_conflict`` keeps (WF-PLA-0020, #3984); the rows that no longer hold are deleted,
    those that do not yet are inserted. Gives the conflicts the structure held before, as their
    rows tell after the write deleted its own links and tasks.
    """
    project_id, structure_id = replay.place
    links = {(link.predecessor_id, link.successor_id): link for link in replay.links}
    by_id = {link.id: link for link in replay.links}
    found = {(each.predecessor_id, each.successor_id) for each in computed.link_conflicts}
    for pair, link in links.items():
        if link.in_conflict != (pair in found):
            link.in_conflict = pair in found
    wanted = {
        (links[(each.predecessor_id, each.successor_id)].id, each.manual_node_id)
        for each in computed.link_conflicts
    }
    held = {
        (link_id, node_id)
        for link_id, node_id in session.execute(
            select(TaskLinkConflict.link_id, TaskLinkConflict.node_id).where(
                TaskLinkConflict.project_id == project_id,
                TaskLinkConflict.structure_id == structure_id,
            )
        )
    }
    gone = held - wanted
    if gone:
        session.execute(
            delete(TaskLinkConflict).where(
                TaskLinkConflict.project_id == project_id,
                tuple_(TaskLinkConflict.link_id, TaskLinkConflict.node_id).in_(gone),
            )
        )
    born = wanted - held
    if born:
        session.execute(
            insert(TaskLinkConflict),
            [
                {
                    "project_id": project_id,
                    "link_id": link_id,
                    "node_id": node_id,
                    "revision_id": by_id[link_id].revision_id,
                    "structure_id": structure_id,
                }
                for link_id, node_id in sorted(born)
            ],
        )
    return frozenset(
        Conflict(by_id[link_id].predecessor_id, by_id[link_id].successor_id, node_id)
        for link_id, node_id in held
        if link_id in by_id
    )


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


def kept(
    session: Session,
    replay: Replay,
    computed: Schedule,
    conflicts: Collection[Conflict] | None = None,
) -> set[UUID]:
    """Write what the engine computed on the facets and the links; give the tasks it moved.

    A task moves when its dates, its float, its criticality or the conflicts that name it change:
    as the predecessor of a link in conflict, or as the task in manual mode it cannot satisfy.
    ``conflicts`` are those of the structure before the write, read before it wrote any link: a
    link it deleted in conflict moves the tasks it named that stay. Without them, the conflicts the
    structure holds are taken as they were, which a recalculation writes none of.
    """
    tree = replay.tree
    held = _conflicts_kept(session, replay, computed)
    before = _ends(held if conflicts is None else conflicts)
    after = _ends(
        [
            Conflict(each.predecessor_id, each.successor_id, each.manual_node_id)
            for each in computed.link_conflicts
        ]
    )
    moved: set[UUID] = set()
    for task_id, placed in computed.tasks.items():
        summary = None
        if tree.is_summary(task_id):
            summary = Duration(in_days(placed.work_hours, replay.constants), DAYS)
        changed = _kept(tree.tasks[task_id], placed, summary)
        if changed or before.get(task_id, set()) != after.get(task_id, set()):
            moved.add(task_id)
    return moved
