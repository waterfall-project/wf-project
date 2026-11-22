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
allow, at the finish of the structure without any. A link from the finish of a summary binds each of
its subordinates, as what follows a summary follows them; a link from its start binds only those
that start with it, the others leaving its start where it is (#3335). The bound a link leaves is
found once, in the measure of its successors, then read on the calendar of each task it binds
(#4414). A task in manual mode is a date imposed: its
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
from waterfall.core.planning.scheduling.units import (
    HOURS_PER_ELAPSED_DAY,
    Span,
    decimal_of,
    rounded,
)

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
    calculated = _calculated(structure, origin)
    return calculated if isinstance(calculated, Schedule) else calculated.rendered()


def counted_bounds(structure: Structure) -> int:
    """Return how many bounds the backward pass of a structure computes, refusing as ``schedule``.

    What a test counts the work of the backward pass by, rather than by a clock (#4414): the
    bounds a link leaves at the latest dates of the tasks it reaches, and those it leaves the tasks
    it binds. Nought for a structure without dates to render, empty or beyond its horizon.
    """
    calculated = _calculated(structure, None)
    return 0 if isinstance(calculated, Schedule) else calculated.bounds


def _calculated(structure: Structure, origin: Origin) -> Schedule | _Engine:
    """Return the calculation of a structure, or its schedule when it has no dates to render."""
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
    return engine


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
        self.bounds = 0

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
        """Return the earliest count a task of a duration starts at to finish at a count.

        An elapsed duration goes back from the end of the hours of work that reach it.
        """
        span = self.span(duration)
        if span.is_elapsed:
            return calendar.count(calendar.moment(finish, finish=True).elapsed(-span.hours))
        return finish - span.hours

    def latest_start(self, calendar: Calendar, finish: Fraction, duration: Duration) -> Fraction:
        """Return the latest count a task of a duration starts at to finish by a count.

        The mirror of ``placed``: the task placed forward from it finishes no later (#2648). An
        elapsed duration finishes on the day it reaches, even without hours of work: it goes back
        from the last moment that still holds the count, the first hour of work that follows. A
        start reached outside the hours of work would be placed at the first hour of work after
        it, and finish too late: it starts then on the last working day before, as late as its
        elapsed hours still end within that day's hours of work — the end of that work less them,
        its first hour when they outlast it (#4412). Half an elapsed hour that may finish by the end
        of a Tuesday starts half an hour before that end, as half an hour of work does, rather than
        at the Tuesday's first hour of work. Two elapsed days that may finish by the end of a
        Friday start on the Friday's first hour of work and finish on the Sunday; started at the
        end of the Friday's work, they would be placed on the Monday and finish on the Wednesday.
        """
        span = self.span(duration)
        if not span.is_elapsed:
            return finish - span.hours
        start = calendar.count(calendar.moment(finish, finish=False).elapsed(-span.hours))
        reached = self.placed(calendar, start, duration, finish_reading=False).finish
        if calendar.count(reached) <= finish:
            return start
        day = calendar.moment(start, finish=True).ordinal
        first = calendar.count(Moment(day))
        # A moment at the last hour of a day of twenty-four counts as the end of that day's work.
        end = calendar.count(Moment(day, Fraction(HOURS_PER_ELAPSED_DAY)))
        return max(first, end - span.hours)

    def placed(
        self, calendar: Calendar, start: Fraction, duration: Duration, *, finish_reading: bool
    ) -> _Span:
        """Return the span of a task of a duration started at a count.

        A milestone sits at one moment (WF-PLA-0050): where its predecessor finishes when a link
        from a finish drives it, the first hour of work of its day otherwise. An elapsed duration
        finishes on the day it reaches, its hours bounded to those of that day, as MS Project
        finishes it (decision of the 2026-11-09, #2342): two elapsed days from a Monday's first
        hour of work finish at the Wednesday's, not at the end of the Tuesday's work — the same
        count of work, a successor without an elapsed lag starting at the same hour.
        """
        span = self.span(duration)
        if span.hours == 0:
            at = calendar.moment(start, finish=finish_reading)
            return _Span(at, at)
        first = calendar.moment(start, finish=False)
        if span.is_elapsed:
            return _Span(first, calendar.bounded(first.elapsed(span.hours)))
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
        """Give each task in automatic mode its latest finish, after those of its successors.

        A link held by a summary above the task binds it when it counts from the summary's finish,
        or from a start the task carries: what follows the start of a summary follows that of the
        subordinates it starts with, not of the others (#3335). The moment a link leaves is reached
        once (``reached``), whatever the count of the tasks it binds (#4414).
        """
        finish = max(self.early[task_id].finish for task_id in self.leaves)
        reached: dict[Link, Moment] = {}
        for task_id, end in reversed(order):
            if end != FINISH or not self.is_automatic_leaf(task_id):
                continue
            start = self.early[task_id].start
            bounds = [finish]
            for holder in [task_id, *self.plan.ancestors(task_id)]:
                carried = self.early[holder].start == start
                for link in self.plan.outgoing.get(holder, []):
                    if link.link_type not in FROM_FINISH and not carried:
                        continue
                    if link not in reached:
                        reached[link] = self.reached(link)
                    bounds.append(self.bound(task_id, link, reached[link]))
            self.late[task_id] = min(bounds)

    def late_span(self, task_id: UUID) -> _Span:
        """Return the latest dates of a successor: its own dates when in manual mode.

        A task that finishes by its latest finish starts no earlier at the latest than it does: an
        elapsed duration finishes at the end of the hours of its day from any start late enough
        that day, and the latest start found for that end may lie before the one the forward pass
        gave it — ten elapsed hours started at a Tuesday's sixth hour of work finish at its eighth,
        as from its first (#4412). For a duration of work, its own start is never the later.
        """
        if not self.is_automatic_leaf(task_id):
            return self.early[task_id]
        task, finish = self.tasks[task_id], self.late[task_id]
        if self.span(task.duration).hours == 0:
            return _Span(finish, finish)
        calendar, early = task.calendar, self.early[task_id]
        count = calendar.count(finish)
        start = self.latest_start(calendar, count, task.duration)
        if calendar.count(early.finish) <= count:
            start = max(start, calendar.count(early.start))
        return _Span(calendar.moment(start, finish=False), finish)

    def reached(self, link: Link) -> Moment:
        """Return the latest moment the successors of a link leave the end it counts from.

        The earliest of those each task without subordinates under the successor leaves, as the
        forward pass binds each of them. The lag goes back from the successor's latest start, or
        finish, on its calendar, as the forward pass placed it; the count reached is the
        successor's, and the end may lie up to the last instant that count holds — read as a
        start, the first hour of work that follows. A moment rather than a count: the calendars of
        the tasks it binds do not measure the same day (WF-PLA-0010), and each counts it in its own
        hours (``bound``) — the earliest moment the earliest count on any of them, a count never
        falling as its moment grows.

        An elapsed lag reached forward past the hours of a day counts as their end, even on a day
        without hours of work (WF-PLA-0160): it goes back, as the latest start of an elapsed
        duration does, from the last moment that still holds the successor's count, the first
        hour of work that follows. Two elapsed days forward from the end of a Friday's work reach
        the Sunday, counted as that end; back from that end itself, they would reach the
        Wednesday's, two days short; back from the Monday's first hour, they reach the Saturday,
        counted as the Friday's end again (#2816).

        The rule holds for any successor: a manual one, whose own dates stand for its latest ones,
        as an automatic one, and for a link to a start as to a finish.
        """
        span = -self.span_of_lag(link)
        found: list[Moment] = []
        for successor_id in self.plan.leaves(link.successor_id):
            self.bounds += 1
            calendar = self.tasks[successor_id].calendar
            latest = self.late_span(successor_id)
            target = latest.start if link.link_type in TO_START else latest.finish
            if span.is_elapsed:
                target = calendar.moment(calendar.count(target), finish=False)
            found.append(calendar.moment(self.shifted(calendar, target, span), finish=False))
        return min(found)

    def bound(self, task_id: UUID, link: Link, reached: Moment) -> Moment:
        """Return the latest finish a link leaves a task, from the moment its successors leave.

        Counted on the task's own calendar; a link from a start bounds the task's start, its
        finish following.
        """
        self.bounds += 1
        task = self.tasks[task_id]
        end = task.calendar.count(reached)
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
