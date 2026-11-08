# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The dates, the floats and the critical path of a structure (WF-PLA-0010 to WF-PLA-0100).

Forward, in the order of the links (``links.dating_order``), each task in automatic mode starts at
the latest its links allow, or at the planning start of the structure without any, on its own
calendar, hour after hour (WF-PLA-0010, WF-PLA-0020). A link counts from the finish of its
predecessor, or its start, its lag placed on the successor's calendar (WF-PLA-0030, WF-PLA-0160),
and binds the successor's start, or its finish. A link to a summary binds each of its subordinates,
as what precedes a summary precedes them; a task in manual mode keeps its dates, whatever its
links; a summary spans its subordinates (WF-PLA-0040).

Backward, in the reverse order, each task in automatic mode may finish as late as its successors
allow, at the finish of the structure without any — a link from a summary binding each of its
subordinates, as what follows a summary follows them. A task in manual mode is a date imposed: its
predecessors are bound by its dates, not by a latest date of its own (WF-PLA-0100). The total float
is the work, in days, from a task's finish to its latest finish; the critical path, the tasks in
automatic mode whose float is nil or negative.
"""

from dataclasses import dataclass
from datetime import MAXYEAR, date
from fractions import Fraction
from typing import TYPE_CHECKING

from waterfall.core.planning.scheduling.calendar import Moment
from waterfall.core.planning.scheduling.links import (
    FINISH,
    START,
    Plan,
    dating_order,
    plan_of,
)
from waterfall.core.planning.scheduling.structure import (
    FROM_FINISH,
    TO_START,
    LinkConflict,
    Schedule,
    ScheduledTask,
    TaskWithoutWorkingHoursError,
)
from waterfall.core.planning.scheduling.units import Span, decimal_of, rounded

if TYPE_CHECKING:
    from uuid import UUID

    from waterfall.core.planning.scheduling.calendar import Calendar
    from waterfall.core.planning.scheduling.links import Point
    from waterfall.core.planning.scheduling.structure import (
        Link,
        Origin,
        Structure,
        Task,
    )
    from waterfall.core.planning.scheduling.units import Duration

HORIZON_YEARS = 15
"""The longest a project lasts, from the start of its first task to the finish of its last."""


@dataclass(frozen=True, slots=True)
class _Span:
    """Where a task lies: its start and its finish."""

    start: Moment
    finish: Moment


def schedule(structure: Structure, origin: Origin = None) -> Schedule:
    """Date a structure, find its floats, its critical path and its conflicts.

    Refuses, in this order, a link between a summary and its subordinate
    (``LinkForbiddenError``), a loop of links named from ``origin`` (``LinkCycleError``), and a
    task whose calendar grants no hour of work (``TaskWithoutWorkingHoursError``): a loop leaves
    the dates without a calculation, and the horizon is then not judged. A structure dated beyond
    fifteen years is rendered without its dates, naming the task that finishes last (WF-PLA-0150).
    """
    plan = plan_of(structure)
    order = dating_order(structure, plan, origin)
    for task in structure.tasks:
        if task.calendar.weekly <= 0:
            raise TaskWithoutWorkingHoursError(task.task_id)
    if not structure.tasks:
        return Schedule({}, ())
    engine = _Engine(structure, plan)
    engine.forward(order)
    beyond = engine.beyond_horizon()
    if beyond is not None:
        return Schedule({}, (), beyond)
    engine.backward(order)
    return engine.rendered()


def horizon_of(start: date) -> date | None:
    """Return the last day a project started on a day may finish: fifteen years later.

    Fifteen years after a 29th of February is the 28th; none past the last year a date holds.
    """
    if start.year > MAXYEAR - HORIZON_YEARS:
        return None
    try:
        return start.replace(year=start.year + HORIZON_YEARS)
    except ValueError:
        return start.replace(year=start.year + HORIZON_YEARS, day=28)


class _Engine:
    """One calculation of a structure: its early dates, then its latest finishes."""

    def __init__(self, structure: Structure, plan: Plan) -> None:
        self.structure = structure
        self.plan = plan
        self.tasks = {task.task_id: task for task in structure.tasks}
        self.leaves = [
            task.task_id for task in structure.tasks if task.task_id not in plan.children
        ]
        self.early: dict[UUID, _Span] = {}
        self.late: dict[UUID, Moment] = {}

    def span(self, duration: Duration) -> Span:
        """Return a duration in exact hours, by the constants of the structure."""
        return duration.span(self.structure.constants)

    def is_automatic_leaf(self, task_id: UUID) -> bool:
        """Whether a task is placed by its links: in automatic mode, without subordinates."""
        return task_id not in self.plan.children and self.tasks[task_id].mode == "automatic"

    # --- Placing on a calendar ---------------------------------------------------------------

    def shifted(self, calendar: Calendar, at: Moment, span: Span) -> Fraction:
        """Return the count of work on a calendar a span reaches from a moment.

        Work is added hour of work after hour of work; elapsed time without a calendar, a moment
        past the hours of its day counting as their end (WF-PLA-0160).
        """
        if span.is_elapsed:
            return calendar.count(at.elapsed(span.hours))
        return calendar.count(at) + span.hours

    def start_for(self, calendar: Calendar, finish: Fraction, duration: Duration) -> Fraction:
        """Return the count a task of a duration starts at to finish at a count."""
        span = self.span(duration)
        if span.is_elapsed:
            return calendar.count(calendar.moment(finish, finish=True).elapsed(-span.hours))
        return finish - span.hours

    def placed(
        self, calendar: Calendar, start: Fraction, duration: Duration, *, finish_reading: bool
    ) -> _Span:
        """Return the span of a task of a duration started at a count.

        A milestone sits at one moment (WF-PLA-0050): where its predecessor finishes when a link
        from a finish drives it, the first hour of work of its day otherwise.
        """
        span = self.span(duration)
        if span.hours == 0:
            at = calendar.moment(start, finish=finish_reading)
            return _Span(at, at)
        first = calendar.moment(start, finish=False)
        if span.is_elapsed:
            # The first moment lies within the hours of work of its day: an elapsed span always
            # reaches further.
            last = calendar.count(first.elapsed(span.hours))
            return _Span(first, calendar.moment(last, finish=True))
        return _Span(first, calendar.moment(start + span.hours, finish=True))

    def span_of_lag(self, link: Link) -> Span:
        """Return the lag of a link in hours: a percent of its predecessor's (WF-PLA-0030).

        A summary's duration is its work between its dates on its own calendar (WF-PLA-0040).
        """
        if link.predecessor_id in self.plan.children:
            predecessor = Span(self.work(link.predecessor_id), is_elapsed=False)
        else:
            predecessor = self.span(self.tasks[link.predecessor_id].duration)
        return link.lag.span(predecessor, self.structure.constants)

    def work(self, task_id: UUID) -> Fraction:
        """Return the hours of work between the dates of a task, on its calendar."""
        span, calendar = self.early[task_id], self.tasks[task_id].calendar
        return calendar.count(span.finish) - calendar.count(span.start)

    def anchor(self, link: Link) -> Moment:
        """Return where a link counts from: its predecessor's finish, or its start."""
        span = self.early[link.predecessor_id]
        return span.finish if link.link_type in FROM_FINISH else span.start

    # --- Forward ------------------------------------------------------------------------------

    def forward(self, order: list[Point]) -> None:
        """Give each task its early dates, each after the ends that lead to it."""
        for task_id, end in order:
            if task_id in self.plan.children:
                if end == FINISH:
                    spans = [self.early[child] for child in self.plan.children[task_id]]
                    first = min(span.start for span in spans)
                    self.early[task_id] = _Span(first, max(span.finish for span in spans))
            elif end == START:
                self.early[task_id] = self.place(self.tasks[task_id])

    def place(self, task: Task) -> _Span:
        """Return the early dates of a task without subordinates."""
        if task.mode == "manual":
            if task.start is None or task.finish is None:
                message = f"the task {task.task_id} is in manual mode without its dates"
                raise ValueError(message)
            return _Span(Moment.of(task.start), Moment.of(task.finish))
        calendar = task.calendar
        bounds: list[tuple[Fraction, bool]] = []
        for holder in [task.task_id, *self.plan.ancestors(task.task_id)]:
            for link in self.plan.incoming.get(holder, []):
                at = self.shifted(calendar, self.anchor(link), self.span_of_lag(link))
                if link.link_type not in TO_START:
                    at = self.start_for(calendar, at, task.duration)
                bounds.append((at, link.link_type in FROM_FINISH))
        if not bounds:
            origin = Moment(self.structure.planning_start.toordinal())
            return self.placed(
                calendar, calendar.count(origin), task.duration, finish_reading=False
            )
        latest = max(count for count, _ in bounds)
        driven = any(count == latest and from_finish for count, from_finish in bounds)
        return self.placed(calendar, latest, task.duration, finish_reading=driven)

    def beyond_horizon(self) -> UUID | None:
        """Return the task, not a summary, that finishes last when the project lasts too long.

        The first in the order of the plan among those finishing last; none within fifteen years
        of the start of the first task (WF-PLA-0150). A task that starts before the first day a
        date holds — a lead of centuries from a planning start in the first years — has dates the
        engine cannot render any more than past the last: the structure is refused the same way,
        by the only refusal of the contract for dates out of reach, naming as always the task that
        finishes last, rather than by a code the contract does not have.
        """
        last = self.leaves[0]
        for task_id in self.leaves:
            if self.early[task_id].finish > self.early[last].finish:
                last = task_id
        first = min(self.early[task_id].start.ordinal for task_id in self.leaves)
        finish = self.early[last].finish.ordinal
        if first < 1 or finish > date.max.toordinal():
            return last
        limit = horizon_of(date.fromordinal(first))
        return last if limit is not None and finish > limit.toordinal() else None

    # --- Backward -----------------------------------------------------------------------------

    def backward(self, order: list[Point]) -> None:
        """Give each task in automatic mode its latest finish, after those of its successors."""
        finish = max(self.early[task_id].finish for task_id in self.leaves)
        for task_id, end in reversed(order):
            if end == FINISH and self.is_automatic_leaf(task_id):
                bounds = [finish]
                for holder in [task_id, *self.plan.ancestors(task_id)]:
                    for link in self.plan.outgoing.get(holder, []):
                        span = self.span_of_lag(link)
                        bounds.extend(
                            self.bound(task_id, link, span, successor)
                            for successor in self.plan.leaves(link.successor_id)
                        )
                self.late[task_id] = min(bounds)

    def late_span(self, task_id: UUID) -> _Span:
        """Return the latest dates of a successor: its own dates when in manual mode."""
        if not self.is_automatic_leaf(task_id):
            return self.early[task_id]
        task, finish = self.tasks[task_id], self.late[task_id]
        if self.span(task.duration).hours == 0:
            return _Span(finish, finish)
        start = self.start_for(task.calendar, task.calendar.count(finish), task.duration)
        return _Span(task.calendar.moment(start, finish=False), finish)

    def bound(self, task_id: UUID, link: Link, span: Span, successor_id: UUID) -> Moment:
        """Return the latest finish a link to one successor leaves a task.

        The lag goes back from the successor's latest start, or finish, on its calendar, as the
        forward pass placed it; a link from a start bounds the task's start, its finish following.
        The count reached is the successor's: the task's end may lie up to the last instant that
        count holds — read as a start, the first hour of work that follows —, and is then counted
        on the task's own calendar, whose hours do not measure the same day (WF-PLA-0010).
        """
        calendar = self.tasks[successor_id].calendar
        latest = self.late_span(successor_id)
        target = latest.start if link.link_type in TO_START else latest.finish
        count = self.shifted(calendar, target, -span)
        task = self.tasks[task_id]
        end = task.calendar.count(calendar.moment(count, finish=False))
        if link.link_type in FROM_FINISH:
            return task.calendar.moment(end, finish=True)
        return self.placed(task.calendar, end, task.duration, finish_reading=False).finish

    # --- Rendering ----------------------------------------------------------------------------

    def conflicts(self) -> list[LinkConflict]:
        """Return the links a predecessor in automatic mode does not satisfy with a manual task.

        In the order of the plan of their predecessor, then of their successor (WF-PLA-0020).
        """
        found: list[LinkConflict] = []
        for link in self.structure.links:
            successor = self.tasks[link.successor_id]
            manual = link.successor_id not in self.plan.children and successor.mode == "manual"
            predecessor_manual = (
                link.predecessor_id not in self.plan.children
                and self.tasks[link.predecessor_id].mode == "manual"
            )
            if not manual or predecessor_manual:
                continue
            calendar = successor.calendar
            needed = self.shifted(calendar, self.anchor(link), self.span_of_lag(link))
            span = self.early[link.successor_id]
            imposed = span.start if link.link_type in TO_START else span.finish
            # At the scale of the rendering: a manual date is one the engine rendered (#2460).
            if rounded(needed) > calendar.count(imposed):
                found.append(LinkConflict(link.predecessor_id, link.successor_id, link.link_type))
        rank = self.plan.rank
        return sorted(found, key=lambda each: (rank[each.predecessor_id], rank[each.successor_id]))

    def total_float(self, task_id: UUID) -> Fraction | None:
        """Return the total float of a task in days, a summary's from its subordinates.

        The float is the hours of work on the task's own calendar from its finish to its latest
        finish, and a day is worth the installation's hours per day, as the unit « j » is
        (WF-PLA-0160) — not the hours of a day of that calendar: sixteen hours of float on a
        calendar of four hours a day are two days, not four. The floats of the subordinates of a
        summary, on different calendars, are so measured alike and compared. A summary bears the
        smallest float of those of its subordinates that bear one, none when none does; a task in
        manual mode none (WF-PLA-0100).
        """
        if task_id in self.plan.children:
            floats = [self.total_float(child) for child in self.plan.children[task_id]]
            return min((each for each in floats if each is not None), default=None)
        if not self.is_automatic_leaf(task_id):
            return None
        calendar = self.tasks[task_id].calendar
        work = calendar.count(self.late[task_id]) - calendar.count(self.early[task_id].finish)
        return work / Fraction(self.structure.constants.hours_per_day)

    def rendered(self) -> Schedule:
        """Return the schedule: each task's dates, float, criticality and conflicts."""
        conflicts = self.conflicts()
        tasks: dict[UUID, ScheduledTask] = {}
        for task in self.structure.tasks:
            task_id = task.task_id
            float_days = self.total_float(task_id)
            # Judged as it is rendered: a ten-billionth short of a manual date is no float lost.
            rendered = None if float_days is None else decimal_of(float_days)
            span = self.early[task_id]
            tasks[task_id] = ScheduledTask(
                start=span.start.instant(),
                finish=span.finish.instant(),
                work_hours=decimal_of(self.work(task_id)),
                total_float=rendered,
                is_critical=rendered is not None and rendered <= 0,
                link_conflicts=tuple(
                    each
                    for each in conflicts
                    if task_id in {each.predecessor_id, each.successor_id}
                ),
            )
        return Schedule(tasks, tuple(conflicts))
