# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The core of the witness dated and priced: its schedule, its float, its amounts.

The whole structure, the core first, is dated in hours of work on the calendar of each task
(``wftools.mockcalendar``, WF-PLA-0010), its total float and its critical path found from its
links (WF-PLA-0100) and its lines priced at the rates of the universe (WF-DEV-0020). The
summaries are summed (WF-DEV-0050), the nodes emitted from these and read as ``listNodes`` reads
them, in ``wftools.mockcore``.

The formulas are simple and said here, to be replaced by the kernel of EP-06 to EP-08: a
backward pass gives each task the latest it may finish, its float being the hours of work from
its finish to that instant. The physical progress of a summary, the budget of its completed
tasks over the budget of its subtree, is not found here: ``wftools.mockcore`` computes it.
"""

from __future__ import annotations

import functools
import heapq
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from wftools.mockcalendar import (
    FINISH_TO_START,
    HOURS_PER_DAY,
    Calendar,
    Instant,
    Predecessor,
    applicable,
    follow,
    to_hours,
)
from wftools.mocklinks import refuse_through_summaries
from wftools.mockstructure import (
    LABOUR_RATES,
    WITNESS,
    JsonObject,
    Projection,
    money,
)
from wftools.mockwitness import (
    CORE,
    PLANNING_START,
    Line,
    Task,
    default_calendar,
    role_calendars,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date


@dataclass(frozen=True, slots=True)
class Conflict:
    """A link a predecessor in automatic mode cannot satisfy with a task in manual mode.

    Named by both its tasks and its type, as the grid and the Gantt name it (WF-PLA-0020).
    """

    predecessor: int
    successor: int
    link_type: str


@dataclass(slots=True)
class Dated:
    """A task of the core placed in time: its calendar, its dates, the latest it may finish.

    A summary and a task in manual mode have no latest finish: the first is not scheduled, the
    second is a date imposed, with no float and never critical (WF-PLA-0100). The links a task
    cannot satisfy, or that are not satisfied for it, are its conflicts (WF-PLA-0020).
    """

    task: Task
    calendar: Calendar
    start: Instant
    finish: Instant
    late_finish: Instant | None = None
    conflicts: list[Conflict] = field(default_factory=list[Conflict])

    @property
    def hours(self) -> Decimal:
        """Return the duration of the task in hours of work (WF-PLA-0160)."""
        return to_hours(self.task.days, self.task.unit)

    @property
    def total_float(self) -> Decimal | None:
        """Return the float in days of work: the hours from the finish to the latest finish.

        Negative when a date entered by hand downstream asks the task to finish earlier than it
        can (WF-PLA-0100).
        """
        if self.late_finish is None:
            return None
        return self.calendar.work_between(self.finish, self.late_finish) / HOURS_PER_DAY


def float_of(dated: Mapping[int, Dated], number: int) -> Decimal | None:
    """Return the total float of a task in days of work, a summary's from its subordinates.

    A summary bears the smallest float of those of its subordinates that bear one, and none when
    none does (WF-PLA-0100): it is critical as soon as one of them is, its float nil or negative.
    """
    placed = dated[number]
    if not placed.task.children:
        return placed.total_float
    floats = [float_of(dated, child.number) for child in placed.task.children]
    return min((each for each in floats if each is not None), default=None)


def tasks_in_order(roots: Iterable[Task] = CORE) -> list[Task]:
    """Return the tasks of the core depth first, in the order of the plan."""
    found: list[Task] = []
    for root in roots:
        found.append(root)
        found.extend(tasks_in_order(root.children))
    return found


def schedule(roots: Iterable[Task] = CORE, start: date = PLANNING_START) -> Mapping[int, Dated]:
    """Date the core from its links, by number of task, and find the latest finish of each.

    Forward: each task in automatic mode starts where its links allow, at the planning start of
    the structure without any — ``start``, the witness's by default —, on the calendar of the
    roles of its labour lines (WF-PLA-0010, WF-PLA-0020, WF-PLA-0030); a task in manual mode keeps
    its dates; a summary spans its subordinates, on the calendar of its own lines (WF-PLA-0040).
    The tasks are dated in the order of their links, each after its predecessors, whatever their
    order in the plan. Backward: a task may finish as late as its successors allow, at the finish
    of the core without any. A structure is dated once: the readings of the indicators and of the
    curves date it again and again. A structure whose links close a loop, or bind a summary to
    one of its subordinates, is not dated: the server refuses it (``in_link_order``,
    ``wftools.mocklinks``).
    """
    return _schedule(tuple(roots), start)


@functools.cache
def _schedule(roots: tuple[Task, ...], planning_start: date) -> Mapping[int, Dated]:
    roles, default = role_calendars(), default_calendar()
    origin = Instant(planning_start)
    tasks = tasks_in_order(roots)
    linked = in_link_order(tasks)
    refuse_through_summaries(tasks)
    dated: dict[int, Dated] = {}
    calendars = {
        task.number: applicable(
            [roles[line.role] for line in task.lines if line.role is not None], default
        )
        for task in tasks
    }
    for task in linked:
        if task.children:
            continue
        calendar = calendars[task.number]
        if task.manual is not None:
            # The dates entered are days: the server completes their hours, the start at the
            # start of its day, the finish at the end of that day's hours on the applicable
            # calendar (#1244). A day without hours, refused entered, is kept imported, at no
            # hour (#1271). A milestone in manual mode is an instant, like any other
            # (WF-PLA-0050).
            first, last = task.manual
            finish = Instant(last, calendar.hours_on(last))
            start = finish if task.is_milestone else Instant(first)
            dated[task.number] = Dated(task, calendar, start, finish)
            continue
        predecessors = [
            Predecessor(
                dated[link.predecessor].start,
                dated[link.predecessor].finish,
                link.link_type,
                to_hours(link.lag, link.unit),
            )
            for link in task.links
        ]
        start, finish = follow(calendar, predecessors, to_hours(task.days, task.unit), origin)
        dated[task.number] = Dated(task, calendar, start, finish)
    for task in reversed(tasks):
        if task.children:
            # A summary has its own calendar, that of the lines it bears: its duration is the work
            # between its dates on it (WF-PLA-0040), not on those of its subordinates.
            placed = [dated[child.number] for child in task.children]
            start = min(each.start for each in placed)
            finish = max(each.finish for each in placed)
            dated[task.number] = Dated(task, calendars[task.number], start, finish)
    _backward(dated, linked)
    return dated


def in_link_order(tasks: list[Task]) -> list[Task]:
    """Return the tasks so that each comes after its predecessors, else in the order of the plan.

    A link that closes a loop is refused, as the server refuses it (WF-PLA-0030).
    """
    rank = {task.number: index for index, task in enumerate(tasks)}
    waits = {task.number: len(task.links) for task in tasks}
    followers: dict[int, list[Task]] = {}
    for task in tasks:
        for link in task.links:
            followers.setdefault(link.predecessor, []).append(task)
    entries = [(rank[task.number], task.number) for task in tasks if not task.links]
    heapq.heapify(entries)
    by_number = {task.number: task for task in tasks}
    ordered: list[Task] = []
    while entries:
        _, number = heapq.heappop(entries)
        ordered.append(by_number[number])
        for follower in followers.get(number, []):
            waits[follower.number] -= 1
            if waits[follower.number] == 0:
                heapq.heappush(entries, (rank[follower.number], follower.number))
    if len(ordered) < len(tasks):
        # Each task left waits for another left: a loop, and what follows it.
        placed = {task.number for task in ordered}
        names = ", ".join(task.label for task in tasks if task.number not in placed)
        message = f"the links close a loop among the tasks left undated: {names}"
        raise ValueError(message)
    return ordered


def _backward(dated: dict[int, Dated], tasks: list[Task]) -> None:
    """Give each task in automatic mode the latest it may finish (WF-PLA-0100), in link order.

    Its successors, each by its link, say where it must finish or start: a finish-to-start
    link, its lag before the successor's latest start; a start-to-start link, there for the
    task's start, its own duration after. The lag is placed on the successor's calendar, as the
    forward pass places it. A successor in manual mode bounds its predecessors by the dates
    entered, its latest start being its start (WF-PLA-0100, #402): a predecessor that cannot
    finish in time has a negative float, and the link is a conflict both tasks bear (WF-PLA-0020).
    """
    activities = [each for each in dated.values() if not each.task.children]
    core_finish = max(each.finish for each in activities)
    successors: dict[int, list[tuple[Dated, Decimal, str]]] = {}
    for task in tasks:
        for link in task.links:
            successors.setdefault(link.predecessor, []).append(
                (dated[task.number], to_hours(link.lag, link.unit), link.link_type)
            )
    for task in reversed(tasks):
        each = dated[task.number]
        if task.children or task.manual is not None:
            continue
        latest = core_finish
        for successor, lag, link_type in successors.get(task.number, []):
            calendar = successor.calendar
            if successor.task.manual is not None:
                latest_start = calendar.elapsed(successor.start) - lag
            elif successor.late_finish is None:
                continue
            else:
                latest_start = calendar.elapsed(successor.late_finish) - successor.hours - lag
            if link_type == FINISH_TO_START:
                bound = calendar.instant(latest_start, finish=True)
            else:
                start = calendar.instant(latest_start, finish=False)
                bound = each.calendar.finish_after(start, each.hours)
            latest = min(latest, bound)
            manual = successor.task.manual is not None
            if manual and each.calendar.work_between(each.finish, bound) < 0:
                conflict = Conflict(task.number, successor.task.number, link_type)
                each.conflicts.append(conflict)
                successor.conflicts.append(conflict)
        each.late_finish = latest


def progress_at(dated: Mapping[int, Dated], number: int, today: date) -> str:
    """Return the progress of a task at a day: read from its dates in automatic mode.

    A task in manual mode carries the progress its user declared; a summary is completed after
    the last of its subordinates, not started before the first, started otherwise — one
    completed and one not started, none started, still make it started (WF-PLA-0040).
    """
    placed = dated[number]
    if placed.task.children:
        states = {progress_at(dated, child.number, today) for child in placed.task.children}
        return states.pop() if len(states) == 1 else "started"
    declared, on = placed.task.progress, placed.task.declared_on or placed.finish.day
    # A completion declared is a gesture made on the day the task completed: before it, the
    # task reads as its dates say (WF-PLA-0130).
    if declared is not None and not (declared == "completed" and on > today):
        return declared
    if placed.task.is_milestone:
        # Nothing completes by itself (WF-RAE-0030): a milestone is completed by a gesture
        # alone, its date passed or not.
        return "not_started"
    if placed.finish.day < today:
        return "completed"
    if placed.start.day <= today and not placed.task.is_milestone:
        return "started"
    return "not_started"


# --- Pricing the lines, summing the tasks -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Amounts:
    """The three amounts of a line or of a task (WF-DEV-0020, WF-DEV-0050).

    The amount at the rates of the reference year, before inflation, a value read; the budgeted
    and the re-estimated amounts, inflation included, at the year of consumption.
    """

    base: Decimal = Decimal(0)
    budgeted: Decimal = Decimal(0)
    reestimated: Decimal = Decimal(0)

    def __add__(self, other: Amounts) -> Amounts:
        return Amounts(
            self.base + other.base,
            self.budgeted + other.budgeted,
            self.reestimated + other.reestimated,
        )

    def rendered(self) -> JsonObject:
        """Return the amounts as the contract carries them."""
        return {
            "base_amount": money(self.base),
            "budgeted_amount": money(self.budgeted),
            "reestimated_amount": money(self.reestimated),
        }


def payment_delay(line: Line) -> int | None:
    """Return the payment delay a line renders, in days: nought unless the witness gives one.

    Every line of the estimate has a payment delay (WF-DEV-0020) — labour included, paid as it is
    worked unless said otherwise —, but a provision, which carries none and stays at the date of
    its task (WF-DEV-0020, WF-IND-0100; EP-14/L42s): it renders nil. The curve of the
    disbursements shifts each line by the delay its node renders.
    """
    return None if line.is_provision else line.payment_delay_days


def price(
    line: Line,
    year: int,
    rates: Mapping[str, Decimal] = LABOUR_RATES,
    *,
    budget_year: int | None = None,
    projection: Projection = WITNESS,
) -> Amounts:
    """Return the amounts of a line: hours at the rate of its category, or its disbursement.

    The amount at the rates of the reference year, before inflation, is the product of the
    quantity and of the hours by the hourly rate for a labour line, of the quantity and the unit
    disbursement otherwise (WF-DEV-0030). The re-estimate is that amount projected on the year of
    consumption, ``year``, compounded once a year elapsed since the reference year; the budget,
    what the reference revision gives the line — the amount unless the line says otherwise —,
    projected on the year the reference consumed it, ``budget_year``, that of the line by
    default (WF-DEV-0020, WF-RAE-0010). A line of provision is not projected: its amount is the
    one its risk computes, the own estimate of the risk bearing its projection already
    (WF-DEV-0030, WF-PRJ-0040). The hourly rates are those of the reference year of the revision
    priced, one for each category: by default, the core's, of 2026 (WF-DEV-0020, WF-REV-0060).
    """
    if line.hours is not None:
        amount = line.quantity * line.hours * rates[line.category]
    elif line.unit is not None:
        amount = line.quantity * line.unit
    else:
        message = f"the line {line.number} has neither hours nor a unit disbursement"
        raise ValueError(message)
    budgeted = amount if line.budgeted is None else line.budgeted
    if line.is_provision:
        return Amounts(amount, budgeted, amount)
    on = year if budget_year is None else budget_year
    return Amounts(amount, projection(budgeted, on), projection(amount, year))
