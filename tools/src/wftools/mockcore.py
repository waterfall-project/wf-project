# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The readable core of the witness structure, dated and priced, read as ``listNodes`` reads it.

The core is described once in ``wftools.mockwitness`` (#287): here it is dated in hours of work
on the calendar of each task (``wftools.mockcalendar``, WF-PLA-0010), its total float and its
critical path found from its own links (WF-PLA-0100), its lines priced at the rates of the
universe (WF-DEV-0020) and its summaries summed (WF-DEV-0050), and its nodes emitted as the
server renders them, numbered from the first row of the structure, where the structure of a
thousand tasks is to carry them (EP-02/L27, #376). The named examples of ``listNodes`` —
``nodes``, ``nodes_planning``, ``nodes_estimate``, ``nodes_milestone``, ``nodes_risk_occurred``
— are readings of this one tree, by ``subtree_of``, ``kinds`` and ``search``, and the
``dependencies_*`` examples say what its computed values depend on: one identifier, one lineage
and one figure for each node, whatever the example (EP-02/L21).

The formulas are simple and said here, to be replaced by the kernel of EP-06 to EP-08: a
backward pass gives each task the latest it may finish, its float being the hours of work from
its finish to that instant; the physical progress of a summary is the budget of its completed
tasks over the budget of its subtree; a line is consumed in the year its task starts. Nothing
here reads the clock: the examples are read at ``mockwitness.TODAY``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, cast

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
from wftools.mockstructure import (
    COMMISSIONING_RATE,
    ELECTRICAL_RATE,
    JsonObject,
    JsonValue,
    computable,
    decimal,
    inflated,
    labels,
    line_fields,
    money,
    task_fields,
)
from wftools.mockwitness import (
    COMMISSIONING,
    CORE,
    ELECTRICAL_ENGINEERING,
    INSCRIBED,
    STUDIES_STARTED,
    TODAY,
    TRACKED,
    Line,
    Task,
    default_calendar,
    role_calendars,
    universe,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import date

READ_ON = TODAY.date()
"""The day the examples are read: the progress of the tasks is at that day."""

LABOUR_RATES = {ELECTRICAL_ENGINEERING: ELECTRICAL_RATE, COMMISSIONING: COMMISSIONING_RATE}
"""The hourly rate of each labour category the core employs, for the reference year."""

LINEAGE = 100
"""What separates the lineage of a node of the core from its node: 5nn is of the lineage 6nn."""

TASK, ESTIMATE_LINE = "task", "estimate_line"

NO_BUDGET = "no_budgeted_amount"
"""Why the physical progress of a summary without any budget cannot be computed (WF-IND-0010)."""

SHARE = Decimal("0.0001")


def lineage(number: int) -> str:
    """Return the identifier of the lineage of a node of the core."""
    return universe(number + LINEAGE)


# --- Dating the core --------------------------------------------------------------------------


@dataclass(slots=True)
class Dated:
    """A task of the core placed in time: its calendar, its dates, the latest it may finish.

    A summary and a task in manual mode have no latest finish: the first is not scheduled, the
    second is a date imposed, with no float and never critical (WF-PLA-0100).
    """

    task: Task
    calendar: Calendar
    start: Instant
    finish: Instant
    late_finish: Instant | None = None

    @property
    def hours(self) -> Decimal:
        """Return the duration of the task in hours of work (WF-PLA-0160)."""
        return to_hours(self.task.days, "d")

    @property
    def total_float(self) -> Decimal | None:
        """Return the float in days of work: the hours from the finish to the latest finish."""
        if self.late_finish is None:
            return None
        return self.calendar.work_between(self.finish, self.late_finish) / HOURS_PER_DAY


def tasks_in_order(roots: Iterable[Task] = CORE) -> list[Task]:
    """Return the tasks of the core depth first, in the order of the plan."""
    found: list[Task] = []
    for root in roots:
        found.append(root)
        found.extend(tasks_in_order(root.children))
    return found


def schedule(roots: Iterable[Task] = CORE) -> dict[int, Dated]:
    """Date the core from its links, by number of task, and find the latest finish of each.

    Forward: each task in automatic mode starts where its links allow, at the start of the
    studies without any, on the calendar of the roles of its labour lines (WF-PLA-0010,
    WF-PLA-0030); a task in manual mode keeps its dates; a summary spans its subordinates
    (WF-PLA-0040). The tasks are dated in the order of their links, each after its
    predecessors, whatever their order in the plan. Backward: a task may finish as late as its
    successors allow, at the finish of the core without any.
    """
    roles, default = role_calendars(), default_calendar()
    origin = Instant(STUDIES_STARTED.on)
    tasks = tasks_in_order(roots)
    linked = in_link_order(tasks)
    dated: dict[int, Dated] = {}
    for task in linked:
        if task.children:
            continue
        if task.manual is not None:
            # A milestone in manual mode is an instant, like any other (WF-PLA-0050).
            first, last = task.manual
            finish = Instant(last, HOURS_PER_DAY)
            start = finish if task.is_milestone else Instant(first)
            dated[task.number] = Dated(task, default, start, finish)
            continue
        calendar = applicable(
            [roles[line.role] for line in task.lines if line.role is not None], default
        )
        predecessors = [
            Predecessor(
                dated[link.predecessor].start,
                dated[link.predecessor].finish,
                link.link_type,
                to_hours(link.lag, link.unit),
            )
            for link in task.links
        ]
        start, finish = follow(calendar, predecessors, to_hours(task.days, "d"), origin)
        dated[task.number] = Dated(task, calendar, start, finish)
    for task in reversed(tasks):
        if task.children:
            placed = [dated[child.number] for child in task.children]
            start = min(each.start for each in placed)
            finish = max(each.finish for each in placed)
            dated[task.number] = Dated(task, default, start, finish)
    _backward(dated, linked)
    return dated


def in_link_order(tasks: list[Task]) -> list[Task]:
    """Return the tasks so that each comes after its predecessors, else in the order of the plan.

    A link that closes a loop is refused, as the server refuses it (WF-PLA-0030).
    """
    placed: set[int] = set()
    ordered: list[Task] = []
    waiting = list(tasks)
    while waiting:
        ready = next(
            (task for task in waiting if all(link.predecessor in placed for link in task.links)),
            None,
        )
        if ready is None:
            # Each task left waits for another left: a loop, and what follows it.
            names = ", ".join(task.label for task in waiting)
            message = f"the links close a loop among the tasks left undated: {names}"
            raise ValueError(message)
        waiting.remove(ready)
        placed.add(ready.number)
        ordered.append(ready)
    return ordered


def _backward(dated: dict[int, Dated], tasks: list[Task]) -> None:
    """Give each task in automatic mode the latest it may finish (WF-PLA-0100), in link order.

    Its successors, each by its link, say where it must finish or start: a finish-to-start
    link, its lag before the successor's latest start; a start-to-start link, there for the
    task's start, its own duration after. The lag is placed on the successor's calendar, as the
    forward pass places it. A successor in manual mode imposes nothing: its dates are entered.
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
            if successor.late_finish is None:
                continue
            calendar = successor.calendar
            latest_start = calendar.elapsed(successor.late_finish) - successor.hours - lag
            if link_type == FINISH_TO_START:
                bound = calendar.instant(latest_start, finish=True)
            else:
                start = calendar.instant(latest_start, finish=False)
                bound = each.calendar.finish_after(start, each.hours)
            latest = min(latest, bound)
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
    if placed.task.progress is not None:
        return placed.task.progress
    if placed.finish.day < today:
        return "completed"
    if placed.start.day <= today and not placed.task.is_milestone:
        return "started"
    return "not_started"


# --- Pricing the lines, summing the tasks -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Amounts:
    """The four amounts of a line or of a task (WF-DEV-0020, WF-DEV-0040)."""

    base: Decimal = Decimal(0)
    budgeted: Decimal = Decimal(0)
    reestimated: Decimal = Decimal(0)
    inflated: Decimal = Decimal(0)

    def __add__(self, other: Amounts) -> Amounts:
        return Amounts(
            self.base + other.base,
            self.budgeted + other.budgeted,
            self.reestimated + other.reestimated,
            self.inflated + other.inflated,
        )

    def rendered(self) -> JsonObject:
        """Return the amounts as the contract carries them."""
        return {
            "base_amount": money(self.base),
            "budgeted_amount": money(self.budgeted),
            "reestimated_amount": money(self.reestimated),
            "inflated_amount": money(self.inflated),
        }


def price(line: Line, year: int, rates: Mapping[str, Decimal] = LABOUR_RATES) -> Amounts:
    """Return the amounts of a line: hours at the rate of its category, or its disbursement.

    The amount at the year of reference is the product of the quantity, one, and of the hours
    by the hourly rate for a labour line, of the quantity and the unit disbursement otherwise
    (WF-DEV-0030); the budget is what the reference revision gives it, the amount unless the
    line says otherwise; the re-estimate is the amount; the amount corrected for inflation is
    the amount projected on the year of consumption (WF-DEV-0040). The hourly rates are those
    of the reference year of the revision priced: by default, the core's, of 2026.
    """
    if line.hours is not None:
        amount = line.hours * rates[line.category]
    elif line.unit is not None:
        amount = line.unit
    else:
        message = f"the line {line.number} has neither hours nor a unit disbursement"
        raise ValueError(message)
    budgeted = amount if line.budgeted is None else line.budgeted
    return Amounts(amount, budgeted, amount, inflated(amount, year))


# --- Emitting the nodes -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Row:
    """A node of the core as the readings filter it: its place in the tree, what it carries."""

    number: int
    parent: int | None
    row: int
    kind: str
    label: str
    node: JsonObject
    hours: Decimal = Decimal(0)
    amounts: Amounts = field(default_factory=Amounts)


@dataclass(frozen=True, slots=True)
class Place:
    """Where a node sits: under which task, at which rank among its siblings, its row, its level."""

    parent: Task | None
    position: int
    row: int
    level: int

    @property
    def bearing(self) -> Task:
        """Return the task that bears a line: a line is never a root."""
        if self.parent is None:
            message = "a line is borne by a task"
            raise ValueError(message)
        return self.parent


@dataclass(slots=True)
class _Emitter:
    """The nodes of the core in the order of the plan, numbered as they are made."""

    dated: Mapping[int, Dated]
    labels: Mapping[str, str]
    today: date
    rates: Mapping[str, Decimal] = field(default_factory=lambda: dict(LABOUR_RATES))
    rows: list[Row] = field(default_factory=list[Row])
    row_of: dict[int, int] = field(default_factory=dict[int, int])

    def task(self, task: Task, parent: Task | None, position: int, level: int) -> Amounts:
        """Append a task, its lines and its subordinates; return the amounts it sums."""
        place = Place(parent, position, self._number(task.number), level)
        facet = self._task_facet(self.dated[task.number])
        node = self._node(task.number, place, TASK, facet)
        if task.links:
            node["predecessors"] = [
                {
                    "predecessor_node_id": universe(link.predecessor),
                    "predecessor_row_number": self.row_of[link.predecessor],
                    "link_type": link.link_type,
                    "lag": {"value": str(link.lag), "unit": link.unit},
                }
                for link in task.links
            ]
        fields = task_fields(
            is_summary=bool(task.children),
            is_milestone=task.is_milestone,
            is_manual=task.manual is not None,
        )
        node["computed_fields"] = fields.computed
        node["editable_fields"] = fields.editable
        above = None if parent is None else parent.number
        self.rows.append(Row(task.number, above, place.row, TASK, task.label, node))
        completed = facet["progress"] == "completed"
        amounts = Amounts()
        for index, line in enumerate(task.lines):
            below = Place(task, index, self._number(line.number), level + 1)
            amounts += self._line(line, below, completed=completed)
        for rank, child in enumerate(task.children):
            amounts += self.task(child, task, rank, level + 1)
        facet.update(amounts.rendered())
        if task.children:
            facet["physical_progress"] = self._physical_progress(task)
        return amounts

    def _line(self, line: Line, place: Place, *, completed: bool) -> Amounts:
        """Append a line of a task, consumed in the year its task starts; return its amounts."""
        task = place.bearing
        year = self.dated[task.number].start.day.year
        amounts = price(line, year, self.rates)
        facet: JsonObject = {
            "label": line.label,
            "cost_category_id": line.category,
            "cost_category_label": self.labels[line.category],
            "resource_role_id": line.role,
            "resource_role_label": None if line.role is None else self.labels[line.role],
            "quantity": "1",
            "hours": None if line.hours is None else decimal(line.hours),
            "unit_disbursement": None if line.unit is None else money(line.unit),
            "subproject_id": line.subproject,
            "subproject_label": None if line.subproject is None else self.labels[line.subproject],
            **amounts.rendered(),
            "previous_reestimated_amount": None,
            "consumption_year": year,
            "is_computed": line.is_provision,
            "uses_inactive_object": False,
            "remaining_entry": {
                "is_available": not completed,
                "missing_conditions": ["task_not_completed"] if completed else [],
            },
        }
        node = self._node(line.number, place, ESTIMATE_LINE, facet)
        fields = line_fields(is_labour=line.hours is not None, is_provision=line.is_provision)
        node["computed_fields"] = fields.computed
        node["editable_fields"] = fields.editable
        hours = Decimal(0) if line.hours is None else line.hours
        self.rows.append(
            Row(
                line.number, task.number, place.row, ESTIMATE_LINE, line.label, node, hours, amounts
            )
        )
        return amounts

    def _number(self, number: int) -> int:
        """Return the row of a node in the structure, numbered before any was made."""
        return self.row_of[number]

    def _task_facet(self, placed: Dated) -> JsonObject:
        """Return the facet of a task: its mode, its dates, its progress, its float."""
        task = placed.task
        state = progress_at(self.dated, task.number, self.today)
        duration = placed.calendar.work_between(placed.start, placed.finish) / HOURS_PER_DAY
        facet: JsonObject = {
            "label": task.label,
            "scheduling_mode": "automatic" if task.manual is None else "manual",
            "duration": {"value": decimal(duration), "unit": "d"},
            "start": _instant(placed.start),
            "finish": _instant(placed.finish),
            "progress": state,
            # Overdue: started, and past its finish at the day the examples are read.
            "finish_overdue": state == "started" and placed.finish.day < self.today,
        }
        started_on, completed_on = self._dates_of(task, state)
        if started_on is not None:
            facet["started_on"] = started_on.isoformat()
        if completed_on is not None:
            facet["completed_on"] = completed_on.isoformat()
        facet["is_summary"] = bool(task.children)
        facet["is_milestone"] = task.is_milestone
        if task.order_item is not None:
            # A summary bears its order item, named, that the grid shows without reading the
            # work breakdown (WF-PLA-0130, WF-ARC-0020).
            facet["order_item_id"] = task.order_item.identifier
            facet["work_package_id"] = None
            facet["work_breakdown_label"] = task.order_item.label
        tracking = _tracking(task.number)
        if tracking:
            facet["tracking"] = tracking
        if not task.children:
            total_float = placed.total_float
            facet["total_float"] = (
                None if total_float is None else {"value": decimal(total_float), "unit": "d"}
            )
            facet["is_critical"] = total_float is not None and total_float == 0
        return facet

    def _dates_of(self, task: Task, state: str) -> tuple[date | None, date | None]:
        """Return when a task started and when it completed, as far as it has (WF-PLA-0130).

        A task starts on its first day and completes on its last; a milestone goes from not
        started to completed and never starts (WF-PLA-0050); a summary starts with the first of
        its subordinates and completes with the last.
        """
        if task.children:
            starts: list[date] = []
            ends: list[date] = []
            for child in task.children:
                started, completed = self._dates_of(
                    child, progress_at(self.dated, child.number, self.today)
                )
                starts.extend([started] if started is not None else [])
                ends.extend([completed] if completed is not None else [])
            return min(starts, default=None), max(
                ends, default=None
            ) if state == "completed" else None
        placed = self.dated[task.number]
        completed = placed.finish.day if state == "completed" else None
        if task.is_milestone or state == "not_started":
            return None, completed
        return placed.start.day, completed

    def _physical_progress(self, summary: Task) -> JsonObject:
        """Return the physical progress of a summary (WF-IND-0060).

        The budget of the lines of its completed tasks over the budget of the lines of its
        subtree; not computable without any budget (WF-IND-0010).
        """
        below = {task.number for task in tasks_in_order(summary.children)}
        budgeted = Decimal(0)
        completed = Decimal(0)
        for row in self.rows:
            if row.kind != ESTIMATE_LINE or row.parent not in below:
                continue
            budgeted += row.amounts.budgeted
            if progress_at(self.dated, row.parent, self.today) == "completed":
                completed += row.amounts.budgeted
        if budgeted == 0:
            return {"is_computable": False, "value": None, "reason": NO_BUDGET}
        return computable(decimal((completed / budgeted).quantize(SHARE)))

    @staticmethod
    def _node(number: int, place: Place, kind: str, facet: JsonObject) -> JsonObject:
        return {
            "node_id": universe(number),
            "lineage_id": lineage(number),
            "kind": kind,
            "parent_id": None if place.parent is None else universe(place.parent.number),
            "position": place.position,
            "row_number": place.row,
            "level": place.level,
            "lock_version": 1,
            kind: facet,
        }


def _tracking(number: int) -> list[JsonValue]:
    """Return the inscriptions of a task: to its timelines, and to the time/time tracking."""
    entries: list[JsonValue] = [
        {"kind": "timeline", "timeline_id": timeline} for timeline in INSCRIBED.get(number, ())
    ]
    if number in TRACKED:
        entries.append({"kind": "milestone_tracking", "timeline_id": None})
    return entries


def _instant(at: Instant) -> JsonObject:
    """Return an instant of work as the contract carries it (WF-DAT-0100)."""
    return {"date": at.day.isoformat(), "hours": decimal(at.hours)}


def rows_of(roots: Iterable[Task]) -> dict[int, int]:
    """Return the row of each node, by its number: depth first, a task, its lines, its tasks.

    Numbered before any node is made, so that a link names a predecessor further down.
    """
    rows: dict[int, int] = {}

    def number(task: Task) -> None:
        rows[task.number] = len(rows) + 1
        for line in task.lines:
            rows[line.number] = len(rows) + 1
        for child in task.children:
            number(child)

    for root in roots:
        number(root)
    return rows


def core(
    roots: Iterable[Task] = CORE,
    today: date = READ_ON,
    rates: Mapping[str, Decimal] = LABOUR_RATES,
) -> list[Row]:
    """Date, price and emit the core: its nodes in the order of the plan, rows numbered from one.

    Its labour lines at the hourly rates given, those of the reference year of the revision.
    """
    roots = tuple(roots)
    emitter = _Emitter(schedule(roots), labels(), today, rates, row_of=rows_of(roots))
    for position, root in enumerate(roots):
        emitter.task(root, None, position, 1)
    return emitter.rows


# --- The readings of listNodes ----------------------------------------------------------------


def subtree(rows: list[Row], root: int, kinds: frozenset[str] | None = None) -> JsonObject:
    """Return the reading of the subtree of a task, it included, restricted to some kinds.

    ``subtree_of``, then ``kinds``: the nodes under the task, in the order of the plan. The
    totals are those of the lines retained: a reading of the tasks alone sums nothing.
    """
    below = {root}
    for row in rows:
        if row.parent in below:
            below.add(row.number)
    retained = [row for row in rows if row.number in below and (kinds is None or row.kind in kinds)]
    return _answer(retained, [])


def whole(rows: list[Row]) -> JsonObject:
    """Return the reading of the whole structure, without a filter: every node, every total."""
    return _answer(rows, [])


def search(rows: list[Row], text: str) -> JsonObject:
    """Return the reading of a search: the nodes whose label holds the text, and their ancestors.

    An ancestor rendered for the readability of the tree alone is not counted in the totals.
    """
    by_number = {row.number: row for row in rows}
    found = {row.number for row in rows if text.casefold() in row.label.casefold()}
    ancestors: set[int] = set()
    for number in found:
        parent = by_number[number].parent
        while parent is not None and parent not in found:
            ancestors.add(parent)
            parent = by_number[parent].parent
    retained = [row for row in rows if row.number in found]
    readable = [row for row in rows if row.number in ancestors]
    return _answer(retained, readable)


def startable(rows: list[Row]) -> JsonObject:
    """Return the answer of listStartableTasks: the tasks of the Kanban (WF-RAE-0030).

    The tasks not started whose predecessors are all completed, and the tasks started, in the
    order of the plan; never a summary, whose progress derives from its subordinates.
    """
    facets = {
        cast("str", row.node["node_id"]): cast("JsonObject", row.node["task"])
        for row in rows
        if row.kind == TASK
    }
    leaves = [row.node for row in rows if row.kind == TASK]
    leaves = [node for node in leaves if not facets[cast("str", node["node_id"])]["is_summary"]]

    def progress(node: JsonObject) -> str:
        return cast("str", facets[cast("str", node["node_id"])]["progress"])

    def ready(node: JsonObject) -> bool:
        links = cast("list[JsonObject]", node.get("predecessors", []))
        return all(
            facets[cast("str", link["predecessor_node_id"])]["progress"] == "completed"
            for link in links
        )

    return {
        "not_started": [node for node in leaves if progress(node) == "not_started" and ready(node)],
        "started": [node for node in leaves if progress(node) == "started"],
    }


def _answer(retained: list[Row], readable: list[Row]) -> JsonObject:
    """Return the answer of listNodes: the nodes in the order of the plan, and the totals.

    The totals count the retained nodes and sum the retained lines (`NodeTotals`), never the
    amounts of the tasks, which would count the lines twice.
    """
    shown = sorted([*retained, *readable], key=lambda row: row.row)
    lines = [row for row in retained if row.kind == ESTIMATE_LINE]
    amounts = sum((row.amounts for row in lines), Amounts())
    return {
        "items": [row.node for row in shown],
        "totals": {
            "task_count": sum(1 for row in retained if row.kind == TASK),
            "estimate_line_count": len(lines),
            "hours": decimal(sum((row.hours for row in lines), Decimal(0))),
            **amounts.rendered(),
        },
    }


# --- What a computed value depends on ---------------------------------------------------------


def dependencies(rows: list[Row], number: int, name: str, inserted_above: int = 0) -> JsonObject:
    """Return what a computed value of a node of the core depends on (WF-IHM-0030).

    The finish of a summary, its direct subordinates (WF-PLA-0040); the amount of a task, its
    lines and its direct subordinates (WF-DEV-0050); the amount of a labour line, the hourly
    rate (WF-DEV-0020); the quantity of a provision, its risk (WF-RIS-0010); the float of a
    task in manual mode, its mode (WF-PLA-0100). The rows are named by their number in the
    whole structure and their label; read again after rows were inserted above them, they
    bear their new numbers (WF-PLA-0080).
    """
    row = next(each for each in rows if each.number == number)
    children = [each for each in rows if each.parent == number]
    rules: list[JsonValue]
    named: list[Row] = []
    if row.kind == TASK and name == "task.finish":
        rules, named = ["subordinates"], [each for each in children if each.kind == TASK]
    elif row.kind == TASK and name == "task.base_amount":
        rules, named = ["lines_and_subordinates"], children
    elif row.kind == TASK and name == "task.total_float":
        rules = ["manual_mode"]
    elif row.kind == ESTIMATE_LINE and name == "estimate_line.base_amount":
        rules = ["hourly_rate" if row.hours else "unit_disbursement"]
    elif row.kind == ESTIMATE_LINE and name == "estimate_line.quantity":
        rules = ["risk"]
    else:
        message = f"{name} of {row.label} is not a computed value the core explains"
        raise ValueError(message)
    return {
        "node_id": universe(number),
        "field": name,
        "depends_on": rules,
        "rows": [
            {
                "node_id": universe(each.number),
                "row_number": each.row + inserted_above,
                "label": each.label,
            }
            for each in named
        ],
    }
