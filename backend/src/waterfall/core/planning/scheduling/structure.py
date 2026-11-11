# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the engine reads and what it renders: a structure, then its schedule, or a refusal.

A structure is given whole — its tasks in the order of the plan, depth first, their links, the
planning start of the structure and the constants of the units —, the calendar of each task
already resolved (WF-PLA-0010). The engine reads nothing else: no database, no setting, no clock.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from waterfall.core.planning.scheduling.calendar import Calendar, WorkInstant
    from waterfall.core.planning.scheduling.units import Duration, Lag, UnitConstants

type SchedulingMode = Literal["automatic", "manual"]
"""The mode of a task: dates computed from its links, or entered (WF-PLA-0020)."""

type LinkType = Literal["finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish"]
"""The four types of a link (WF-PLA-0030)."""

FROM_FINISH: frozenset[str] = frozenset({"finish_to_start", "finish_to_finish"})
"""The types that count from the finish of the predecessor; the others count from its start."""

TO_START: frozenset[str] = frozenset({"finish_to_start", "start_to_start"})
"""The types that bind the start of the successor; the others bind its finish."""


@dataclass(frozen=True, slots=True)
class Task:
    """A task of the structure, as the engine reads it.

    A task with subordinates is a summary: it spans them, always in automatic mode, and its own
    mode and duration are not read (WF-PLA-0040). A task in manual mode carries the dates entered,
    their hours completed (WF-PLA-0020); one in automatic mode carries none.
    """

    task_id: UUID
    parent_id: UUID | None
    mode: SchedulingMode
    duration: Duration
    calendar: Calendar
    start: WorkInstant | None = None
    finish: WorkInstant | None = None


@dataclass(frozen=True, slots=True)
class Link:
    """A link from a predecessor to a successor, its type and its lag (WF-PLA-0030)."""

    predecessor_id: UUID
    successor_id: UUID
    link_type: LinkType
    lag: Lag


@dataclass(frozen=True, slots=True)
class Structure:
    """A structure of costs as its planning is computed: tasks in the order of the plan, links."""

    tasks: tuple[Task, ...]
    links: tuple[Link, ...]
    planning_start: date
    constants: UnitConstants


@dataclass(frozen=True, slots=True)
class Entry:
    """The task whose predecessors are entered: a loop is named from it (`setPredecessors`)."""

    task_id: UUID


@dataclass(frozen=True, slots=True)
class Move:
    """Tasks moved under a parent, in the order of the plan of the structure read (`moveNodes`).

    The structure given is the one the move would leave, each task moved under its parent.
    """

    task_ids: tuple[UUID, ...]
    parent_id: UUID


type Origin = Entry | Move | None
"""What a loop is named from: an entry, a move, or nothing, for a structure whole."""


@dataclass(frozen=True, slots=True)
class LinkConflict:
    """A link a predecessor in automatic mode cannot satisfy with a task in manual mode.

    Named by its two tasks and its type, as the grid and the Gantt name it (WF-PLA-0020).
    """

    predecessor_id: UUID
    successor_id: UUID
    link_type: LinkType


@dataclass(frozen=True, slots=True)
class ScheduledTask:
    """A task placed in time: its dates, its hours of work, its float and its conflicts.

    The total float is in days of work, signed, nil for a task in manual mode and for a summary
    none of whose subordinates bears one (WF-PLA-0100). A summary's hours of work are those
    between its dates on its own calendar (WF-PLA-0040).
    """

    start: WorkInstant
    finish: WorkInstant
    work_hours: Decimal
    total_float: Decimal | None
    is_critical: bool
    link_conflicts: tuple[LinkConflict, ...]


@dataclass(frozen=True, slots=True)
class Schedule:
    """The planning of a structure, or the task that carries it beyond the horizon.

    Beyond fifteen years (WF-PLA-0150) the structure is refused whole, and its dates, which may
    lie past the last day a date holds, are not given: ``tasks`` is then empty, and
    ``horizon_exceeded_by`` names the task, not a summary, that finishes last.
    """

    tasks: Mapping[UUID, ScheduledTask]
    link_conflicts: tuple[LinkConflict, ...]
    horizon_exceeded_by: UUID | None = None


class SchedulingRefusalError(Exception):
    """A structure the engine refuses to date: a code of the contract, and what it names."""

    code: ClassVar[str]


class LinkForbiddenError(SchedulingRefusalError):
    """A link between a summary and one of its subordinates (WF-PLA-0030, WF-PLA-0040)."""

    code = "LINK_FORBIDDEN"

    def __init__(self, summary_id: UUID, subordinate_id: UUID) -> None:
        super().__init__(self.code)
        self.summary_id = summary_id
        self.subordinate_id = subordinate_id


class LinkCycleError(SchedulingRefusalError):
    """A loop of links, its tasks each preceding the next, the shortest (WF-PLA-0030)."""

    code = "LINK_CYCLE"

    def __init__(self, cycle: tuple[UUID, ...]) -> None:
        super().__init__(self.code)
        self.cycle = cycle


class TaskWithoutWorkingHoursError(SchedulingRefusalError):
    """A task whose calendar grants no hour of work in a week, which cannot be placed."""

    code = "TASK_WITHOUT_WORKING_HOURS"

    def __init__(self, task_id: UUID) -> None:
        super().__init__(self.code)
        self.task_id = task_id
