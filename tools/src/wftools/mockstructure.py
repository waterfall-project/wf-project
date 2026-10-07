# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of a thousand tasks the fake back serves, and its estimate indicators.

The main structure of the witness project at the sizes of §4.6.2: a thousand tasks — phases,
lots, their work tasks and milestones — and five lines per task as §4.6.2 counts them. Each
work task carries five lines; the lines the summaries and milestones do not carry are
provisions, a sixth line spread evenly over the work tasks. The tasks are dated in working
days from their finish-to-start links, with their total float, and their progress is the
one of the day the examples of the contract are read. A task lasts whole working days: its
duration is in days, it starts at the first hour of its first day and finishes at the last
of its last (WF-DAT-0100, WF-PLA-0160). Amounts are ``Decimal``, summed exactly as the lines
are made, so that the indicators of the estimate are those of the lines the grid shows; the
amount of a line corrected for inflation is its amount projected on the year its task
starts, at the inflation rate of the witness project (WF-DEV-0040), and a task and the totals
sum both, the amount at the year of reference and the one corrected. A line names its category,
its role and its subproject by the labels of the universe, as the server resolves them.

Nothing here reads the clock or draws at random: every drawn value comes from a hash of a
fixed seed and of what it describes, so that two runs make the same structure, whatever the
version of Python. ``wftools.mockdata`` writes it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from wftools.mockcalendar import HOURS_PER_DAY
from wftools.mockwitness import (
    COMMISSIONING_TECHNICIAN,
    ELECTRICAL_ENGINEERING,
    ENGINEER,
    EQUIPMENT,
    LINEAGES,
    NODES,
    PROVISIONS,
    SUBCONTRACTING,
    SUBPROJECT_CONTROL,
    fixture,
    identifier,
    universe,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

type JsonValue = str | int | bool | list[JsonValue] | dict[str, JsonValue] | None
type JsonObject = dict[str, JsonValue]

SEED = "waterfall-4.6.2"
"""The seed every drawn value is hashed with: changing it changes every volume."""

PROJECT_START = date(2026, 3, 2)
"""The first working day of the structure, a Monday, as in the witness structure."""

AS_OF = date(2026, 3, 16)
"""The day the examples of the contract are read: the progress of the tasks is at that day."""

TASK_COUNT = 1_000
LINES_PER_TASK = 5

ELECTRICAL_RATE = Decimal("80.00")
"""The hourly rate of the electrical engineering in 2026, the reference year of the estimate:
the witness estimate reads 1,000.00 for 12.5 hours."""

CENT = Decimal("0.01")
SHARE = Decimal("0.0001")

INFLATION_RATE = Decimal("0.03")
"""The inflation rate of the witness project (project.json), which projects an amount on the
year its line is consumed (WF-DEV-0040)."""

REFERENCE_YEAR = 2026
"""The reference year of the witness estimate: an amount of that year is not projected."""

# The universe of the other examples of the contract.
SUBPROJECT_TESTS = universe(802)
COMMISSIONING = universe(405)
LABOR = universe(461)
NON_LABOR = universe(462)
PROVISION = universe(463)

CATEGORY_LABELS = {
    ELECTRICAL_ENGINEERING: "Ingénierie électrique",
    COMMISSIONING: "Mise en service",
    SUBCONTRACTING: "Sous-traitance",
    EQUIPMENT: "Matériel électrique",
    PROVISIONS: "Provisions pour risques",
}
"""The labels of the categories of the universe, which wftools.mockdata lists among the others."""


def draw(key: str, low: int, high: int) -> int:
    """Return an integer of [low, high], fixed by the seed and by the key it describes."""
    digest = hashlib.sha256(f"{SEED}/{key}".encode()).digest()
    return low + int.from_bytes(digest[:8]) % (high - low + 1)


def working_day(offset: int) -> date:
    """Return the date of a working day, counted from the start: Monday to Friday."""
    weeks, day = divmod(offset, 5)
    return PROJECT_START + timedelta(days=weeks * 7 + day)


def working_offset(day: date) -> int:
    """Return the offset of a working day from the start: the inverse of working_day."""
    weeks, rest = divmod((day - PROJECT_START).days, 7)
    return weeks * 5 + rest


def money(value: Decimal) -> str:
    """Return an amount as the contract carries it: two decimals, never a float."""
    return str(value.quantize(CENT))


def inflated(amount: Decimal, year: int) -> Decimal:
    """Return an amount projected on a year, at the inflation rate of the witness project.

    A simplification of WF-DEV-0040: the whole line is projected on the year its task starts,
    not split across the years the task spans in proportion to its hours of work.
    """
    return (amount * (1 + INFLATION_RATE) ** (year - REFERENCE_YEAR)).quantize(CENT)


def work_instant(offset: int, hours: Decimal) -> JsonObject:
    """Return an instant of work on a working day.

    Its date, and the hours of work elapsed that day (WF-DAT-0100).
    """
    return {"date": working_day(offset).isoformat(), "hours": decimal(hours)}


def decimal(value: Decimal) -> str:
    """Return an exact decimal without trailing zeros: 12.5, 40."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


# --- The structure of a thousand tasks --------------------------------------------------

_PHASES = (
    "Études",
    "Approvisionnements",
    "Génie civil",
    "Fabrication",
    "Montage",
    "Câblage",
    "Automatismes",
    "Essais en usine",
    "Mise en service",
    "Réception",
)
_LOTS = (
    ("Poste de commande", SUBPROJECT_CONTROL),
    ("Ligne d'essais", SUBPROJECT_TESTS),
    ("Utilités", None),
)
_VERBS = (
    "Préparation",
    "Conception",
    "Revue",
    "Réalisation",
    "Contrôle",
    "Reprise",
    "Documentation",
    "Validation",
)
_TASKS_PER_LOT = 31
# The work tasks of a lot run in three chains, each task after the one three places before.
_CHAINS = 3


@dataclass(frozen=True, slots=True)
class LineKind:
    """What the n-th line of a work task is: its label, category, role and rate."""

    label: str
    category: str
    role: str | None = None
    rate: Decimal | None = None
    is_provision: bool = False

    @property
    def cost_type(self) -> str:
        """Return the nature of cost of the line's category."""
        if self.is_provision:
            return PROVISION
        return NON_LABOR if self.rate is None else LABOR


LINE_KINDS = (
    LineKind("Heures d'ingénierie", ELECTRICAL_ENGINEERING, ENGINEER, ELECTRICAL_RATE),
    LineKind("Heures de mise en service", COMMISSIONING, COMMISSIONING_TECHNICIAN, Decimal(75)),
    LineKind("Matériel", EQUIPMENT),
    LineKind("Sous-traitance", SUBCONTRACTING),
    LineKind("Heures de supervision", ELECTRICAL_ENGINEERING, ENGINEER, ELECTRICAL_RATE),
    LineKind("Provision — aléas de réalisation", PROVISIONS, is_provision=True),
)
"""The lines of a work task, in order; the sixth, a provision, only on some of them.

The rate of a labour line is its category's for the reference year of the estimate.
"""


@dataclass(eq=False, slots=True)
class Task:
    """A task of the plan: a summary, a work task or a milestone, scheduled in working days."""

    label: str
    duration: int = 0
    is_milestone: bool = False
    subproject: str | None = None
    children: list[Task] = field(default_factory=list["Task"])
    predecessors: list[Task] = field(default_factory=list["Task"])
    successors: list[Task] = field(default_factory=list["Task"])
    lines: int = 0
    start: int = 0
    end: int = 0
    late_end: int = 0
    row: int = 0

    @property
    def is_summary(self) -> bool:
        """Whether the task sums its subordinates."""
        return bool(self.children)


def plan() -> tuple[list[Task], list[Task]]:
    """Return the phases of the structure, and its work tasks and milestones in link order."""
    roots: list[Task] = []
    activities: list[Task] = []
    previous: list[Task | None] = [None] * len(_LOTS)
    for p, phase in enumerate(_PHASES, start=1):
        summary = Task(phase)
        for n, (lot, subproject) in enumerate(_LOTS, start=1):
            tasks = [
                Task(
                    f"{_VERBS[(k - 1) % len(_VERBS)]} {p}.{n}.{k}",
                    duration=draw(f"duration/{p}.{n}.{k}", 3, 12),
                    subproject=subproject,
                )
                for k in range(1, _TASKS_PER_LOT + 1)
            ]
            for k, task in enumerate(tasks):
                before = tasks[k - _CHAINS] if k >= _CHAINS else previous[n - 1]
                if before is not None:
                    _link(before, task)
            milestone = Task(f"Fin du lot {p}.{n}", is_milestone=True, subproject=subproject)
            for task in tasks[-_CHAINS:]:
                _link(task, milestone)
            previous[n - 1] = milestone
            summary.children.append(Task(f"{phase} — {lot}", children=[*tasks, milestone]))
            activities.extend([*tasks, milestone])
        roots.append(summary)
    return roots, activities


def _link(predecessor: Task, successor: Task) -> None:
    predecessor.successors.append(successor)
    successor.predecessors.append(predecessor)


def schedule(roots: list[Task], activities: list[Task]) -> None:
    """Date the tasks from their finish-to-start links, and find their total float."""
    for task in activities:
        earliest = max((before.end + 1 for before in task.predecessors), default=0)
        # A milestone sits at the end of the day its predecessors finish.
        task.end = earliest + task.duration - 1
        task.start = task.end - max(task.duration, 1) + 1
    finish = max(task.end for task in activities)
    for task in reversed(activities):
        task.late_end = min(
            (after.late_end - after.duration for after in task.successors), default=finish
        )
    for root in roots:
        _roll_up(root)


def _roll_up(task: Task) -> None:
    if not task.children:
        return
    for child in task.children:
        _roll_up(child)
    task.start = min(child.start for child in task.children)
    task.end = max(child.end for child in task.children)
    task.duration = task.end - task.start + 1


def spread_lines(activities: list[Task]) -> None:
    """Give each work task its five lines, and the provisions evenly among them."""
    work = [task for task in activities if not task.is_milestone]
    extra = TASK_COUNT * LINES_PER_TASK - len(work) * LINES_PER_TASK
    for index, task in enumerate(work):
        task.lines = LINES_PER_TASK + (index + 1) * extra // len(work) - index * extra // len(work)


def number(tasks: list[Task], row: int = 1) -> int:
    """Give each task its row, depth first, its lines after it; return the next free row."""
    for task in tasks:
        task.row = row
        row = number(task.children, row + 1 + task.lines)
    return row


def progress(task: Task) -> str:
    """Return the progress of a task at the day the examples are read."""
    today = working_offset(AS_OF)
    if task.children:
        states = {progress(child) for child in task.children}
        return states.pop() if len(states) == 1 else "started"
    if task.end < today:
        return "completed"
    if task.start <= today and not task.is_milestone:
        return "started"
    return "not_started"


@dataclass(slots=True)
class Totals:
    """The totals of the structure, summed exactly as the lines are made."""

    tasks: int = 0
    lines: int = 0
    hours: Decimal = Decimal(0)
    amount: Decimal = Decimal(0)
    inflated: Decimal = Decimal(0)
    by_cost_type: dict[str, Decimal] = field(default_factory=dict[str, Decimal])
    by_subproject: dict[str | None, Decimal] = field(default_factory=dict[str | None, Decimal])

    def add(self, kind: LineKind, subproject: str | None, amounts: Amounts, hours: Decimal) -> None:
        """Count a line: its hours, its amounts, the base one under its nature and subproject."""
        amount = amounts.base
        self.lines += 1
        self.hours += hours
        self.amount += amount
        self.inflated += amounts.inflated
        self.by_cost_type[kind.cost_type] = (
            self.by_cost_type.get(kind.cost_type, Decimal(0)) + amount
        )
        self.by_subproject[subproject] = self.by_subproject.get(subproject, Decimal(0)) + amount


@dataclass(frozen=True, slots=True)
class Amounts:
    """The amounts of a line or of a task: at the year of reference, and corrected for inflation."""

    base: Decimal = Decimal(0)
    inflated: Decimal = Decimal(0)

    def __add__(self, other: Amounts) -> Amounts:
        return Amounts(self.base + other.base, self.inflated + other.inflated)


@dataclass(frozen=True, slots=True)
class Structure:
    """The answer of listNodes for the structure, and the totals its lines sum to."""

    nodes: JsonObject
    totals: Totals


def structure() -> Structure:
    """Plan, date and number the structure of a thousand tasks, and make its nodes."""
    roots, _ = _planned()
    return _emitted(roots)


def _planned() -> tuple[list[Task], list[Task]]:
    """Plan, date and number the structure: its phases, and its work tasks and milestones."""
    roots, activities = plan()
    schedule(roots, activities)
    spread_lines(activities)
    number(roots)
    return roots, activities


def _emitted(roots: list[Task]) -> Structure:
    """Make the nodes of a structure planned, and its totals."""
    emitter = _Emitter(labels())
    for position, root in enumerate(roots):
        emitter.task(root, _Place(None, position, 1))
    totals = emitter.totals
    answer: JsonObject = {
        "items": emitter.items,
        "totals": {
            "task_count": totals.tasks,
            "estimate_line_count": totals.lines,
            "hours": decimal(totals.hours),
            "base_amount": money(totals.amount),
            "budgeted_amount": money(totals.amount),
            "reestimated_amount": money(totals.amount),
            "inflated_amount": money(totals.inflated),
        },
    }
    return Structure(answer, totals)


# --- A write of the planning that moves lines into the next year ----------------------------

LENGTHENED = "Revue 3.1.27"
"""The work task whose duration the example lengthens: it finishes on 29 December 2026, with
33 working days of float, and its one successor in its chain, « Reprise 3.1.30 », starts the
next day."""

LENGTHENED_BY = 2
"""The working days the duration grows by: the task finishes on 31 December, and its successor
starts on the first working day of 2027 — its lines are consumed a year later, corrected anew at
the inflation of the witness project (WF-DEV-0040) —, within the float: the milestone of the lot
does not move, nor anything after it."""

_SCHEDULE = ("start", "finish", "total_float", "is_critical", "finish_overdue")
"""The fields of a task a write may reschedule without writing it (`NodeSchedule`)."""


def task_lengthened() -> JsonObject:
    """Return what updateTaskFacet answers when the duration of LENGTHENED grows by its days.

    The task written, whole; its successors rescheduled, by their schedule (`rescheduled`); the
    lines and the tasks, not summaries, whose amount corrected for inflation changed, by their
    amounts (`reinflated`); the summaries above the task and its successors, whole (`ancestors`);
    the totals of the whole structure, and the version the structure moved on to (WF-PLA-0020,
    WF-DEV-0040, WF-DEV-0050).
    """
    roots, activities = _planned()
    before = _by_id(_emitted(roots).nodes)
    task = next(each for each in activities if each.label == LENGTHENED)
    task.duration += LENGTHENED_BY
    schedule(roots, activities)
    built = _emitted(roots)
    after = _by_id(built.nodes)
    written = identifier(NODES, task.row)
    nodes = [{**after[written], "lock_version": 2}]
    moved = [
        node_id
        for node_id, node in after.items()
        if node_id != written
        and node["kind"] == "task"
        and not node["task"]["is_summary"]
        and any(node["task"].get(key) != before[node_id]["task"].get(key) for key in _SCHEDULE)
    ]
    above = _ancestors(after, [written, *moved])
    reinflated: list[JsonValue] = []
    for node_id, node in after.items():
        if node_id == written or node_id in above:
            continue
        facet = node.get("estimate_line") or node["task"]
        old = before[node_id].get("estimate_line") or before[node_id]["task"]
        line = node["kind"] == "estimate_line"
        if facet["inflated_amount"] != old["inflated_amount"] or (
            line and facet["consumption_year"] != old["consumption_year"]
        ):
            reinflated.append(
                {
                    "node_id": node_id,
                    "inflated_amount": facet["inflated_amount"],
                    "consumption_year": facet["consumption_year"] if line else None,
                }
            )
    return {
        "nodes": cast("list[JsonValue]", nodes),
        "ancestors": [after[node_id] for node_id in after if node_id in above],
        "rescheduled": [
            {"node_id": node_id, **{key: after[node_id]["task"].get(key) for key in _SCHEDULE}}
            for node_id in moved
        ],
        "reinflated": reinflated,
        "totals": built.nodes["totals"],
        "structure_lock_version": 2,
    }


def _by_id(answer: JsonObject) -> dict[str, dict[str, Any]]:
    """Return the nodes of an answer by their identifier, in the order of the plan."""
    items = cast("list[dict[str, Any]]", answer["items"])
    return {item["node_id"]: item for item in items}


def _ancestors(nodes: Mapping[str, dict[str, Any]], of: Sequence[str]) -> set[str]:
    """Return the ancestors of some nodes, each once."""
    found: set[str] = set()
    for node_id in of:
        parent = nodes[node_id]["parent_id"]
        while parent is not None:
            found.add(parent)
            parent = nodes[parent]["parent_id"]
    return found


def labels() -> dict[str, str]:
    """Return the labels of the categories, the roles and the subprojects of the universe."""
    labels = dict(CATEGORY_LABELS)
    labels.update((role["resource_role_id"], role["label"]) for role in fixture("resource_roles"))
    labels.update((entry["subproject_id"], entry["label"]) for entry in fixture("subprojects"))
    return labels


@dataclass(frozen=True, slots=True)
class _Place:
    """Where a node sits: under which task, at which rank among its siblings, how deep."""

    parent: Task | None
    position: int
    level: int


@dataclass(slots=True)
class _Emitter:
    """The nodes of the structure, depth first, and their totals as they are made."""

    labels: Mapping[str, str]
    items: list[JsonValue] = field(default_factory=list["JsonValue"])
    totals: Totals = field(default_factory=Totals)

    def task(self, task: Task, place: _Place) -> Amounts:
        """Append a task, its lines and its subordinates; return the amounts they carry."""
        facet = _task_facet(task)
        fields = task_fields(is_summary=task.is_summary, is_milestone=task.is_milestone)
        node = _node(task.row, place, "task", facet, fields)
        if task.predecessors:
            node["predecessors"] = [
                {
                    "predecessor_node_id": identifier(NODES, before.row),
                    "predecessor_row_number": before.row,
                    "link_type": "finish_to_start",
                    "lag": {"value": "0", "unit": "d"},
                }
                for before in task.predecessors
            ]
        self.items.append(node)
        self.totals.tasks += 1
        amounts = Amounts()
        for index in range(task.lines):
            amounts += self._line(
                task, index, place.level + 1, completed=facet["progress"] == "completed"
            )
        for rank, child in enumerate(task.children):
            amounts += self.task(child, _Place(task, rank, place.level + 1))
        facet.update(_amounts(amounts))
        return amounts

    def _line(self, task: Task, index: int, level: int, *, completed: bool) -> Amounts:
        line, amounts, hours = _line(task, index, self.labels, completed=completed)
        kind = LINE_KINDS[index]
        place = _Place(task, index, level)
        fields = line_fields(is_labour=kind.rate is not None, is_provision=kind.is_provision)
        self.items.append(_node(task.row + 1 + index, place, "estimate_line", line, fields))
        self.totals.add(kind, _subproject(task, kind), amounts, hours)
        return amounts


def _amounts(amounts: Amounts) -> JsonObject:
    """Return the four amounts of a task or a line.

    Three at the year of reference, then the one corrected for inflation: the budget and the
    re-estimate are the amount as it is made.
    """
    base = money(amounts.base)
    return {
        "base_amount": base,
        "budgeted_amount": base,
        "reestimated_amount": base,
        "inflated_amount": money(amounts.inflated),
    }


@dataclass(frozen=True, slots=True)
class Fields:
    """What a node says of the fields of its facet: those computed here, those it accepts."""

    computed: list[JsonValue]
    editable: list[JsonValue]


def _node(row: int, place: _Place, kind: str, facet: JsonObject, fields: Fields) -> JsonObject:
    return {
        "node_id": identifier(NODES, row),
        "lineage_id": identifier(LINEAGES, row),
        "kind": kind,
        "parent_id": None if place.parent is None else identifier(NODES, place.parent.row),
        "position": place.position,
        "row_number": row,
        "level": place.level,
        "lock_version": 1,
        kind: facet,
        "computed_fields": fields.computed,
        "editable_fields": fields.editable,
    }


def _task_facet(task: Task) -> JsonObject:
    state = progress(task)
    facet: JsonObject = {
        "label": task.label,
        "scheduling_mode": "automatic",
        "duration": {"value": str(task.duration), "unit": "d"},
        **_span(task),
        "progress": state,
        # A started task finishes after the day the examples are read: none is overdue.
        "finish_overdue": False,
    }
    if state != "not_started" and not task.is_summary:
        facet["started_on"] = working_day(task.start).isoformat()
    if state == "completed" and not task.is_summary:
        facet["completed_on"] = working_day(task.end).isoformat()
    facet["is_summary"] = task.is_summary
    facet["is_milestone"] = task.is_milestone
    facet.update(_amounts(Amounts()))
    if not task.is_summary:
        facet["total_float"] = {"value": str(task.late_end - task.end), "unit": "d"}
        facet["is_critical"] = task.late_end == task.end
    return facet


def _span(task: Task) -> JsonObject:
    """Return the start and the finish of a task.

    The first hour of its first day and the last of its last. A milestone, of no duration,
    sits at one instant: where its predecessors finish, or the first hour of its day when it
    has none (WF-PLA-0050).
    """
    if task.is_milestone:
        at = work_instant(task.end, HOURS_PER_DAY if task.predecessors else Decimal(0))
        return {"start": at, "finish": at}
    start = work_instant(task.start, Decimal(0))
    return {"start": start, "finish": work_instant(task.end, HOURS_PER_DAY)}


def task_fields(*, is_summary: bool, is_milestone: bool, is_manual: bool = False) -> Fields:
    """Return what a task computes and what it accepts (WF-PLA-0130).

    A task in automatic mode computes its dates; one in manual mode enters them, and computes
    nothing. A summary computes its duration and its progress too, and accepts its label, its
    description and its attachment to an order item or a work package (WF-PLA-0130); a
    milestone has no duration to enter.
    """
    dates: list[JsonValue] = ["task.start", "task.finish"]
    editable: list[JsonValue] = ["task.label", "task.description"]
    if is_summary:
        editable.extend(["task.order_item_id", "task.work_package_id"])
        return Fields(["task.duration", *dates, "task.progress"], editable)
    editable.append("task.scheduling_mode")
    if not is_milestone:
        editable.append("task.duration")
    if is_manual:
        editable.extend(dates)
        dates = []
    editable.append("task.progress")
    return Fields(dates, editable)


def line_fields(*, is_labour: bool, is_provision: bool) -> Fields:
    """Return what a line computes and what it accepts (WF-DEV-0020).

    A labour line takes its role and its hours, and no payment delay, nil for labour (§3.2.5);
    another takes its unit disbursement and its payment delay; a provision computes its
    quantity and its unit disbursement from its risk, and takes neither, nor its category
    (WF-RIS-0010): neither of its amounts, nor its nature, is ever entered.
    """
    editable: list[JsonValue] = ["estimate_line.label"]
    if is_provision:
        editable.extend(["estimate_line.payment_delay_days", "estimate_line.subproject_id"])
        return Fields(["estimate_line.quantity", "estimate_line.unit_disbursement"], editable)
    editable.append("estimate_line.cost_category_id")
    if is_labour:
        editable.extend(
            ["estimate_line.resource_role_id", "estimate_line.quantity", "estimate_line.hours"]
        )
    else:
        editable.extend(
            [
                "estimate_line.quantity",
                "estimate_line.unit_disbursement",
                "estimate_line.payment_delay_days",
            ]
        )
    editable.append("estimate_line.subproject_id")
    return Fields([], editable)


def _line(
    task: Task, index: int, labels: Mapping[str, str], *, completed: bool
) -> tuple[JsonObject, Amounts, Decimal]:
    """Return an estimate line of a work task, its amounts and its hours.

    Its category, its role and its subproject are named by their labels, as the server resolves
    them.
    """
    kind = LINE_KINDS[index]
    key = f"{task.row}/{index}"
    hours: Decimal | None = None
    unit: Decimal | None = None
    quantity = 1
    if kind.rate is not None:
        hours = Decimal(draw(f"hours/{key}", 8, 160)) / 2
        amount = hours * kind.rate
    else:
        unit = Decimal(draw(f"unit/{key}", 1_000, 500_000)) / 100
        if not kind.is_provision:
            quantity = draw(f"quantity/{key}", 1, 20)
        amount = quantity * unit
    year = working_day(task.start).year
    amounts = Amounts(amount, inflated(amount, year))
    subproject = _subproject(task, kind)
    line: JsonObject = {
        "label": kind.label,
        "cost_category_id": kind.category,
        "cost_category_label": labels[kind.category],
        "resource_role_id": kind.role,
        "resource_role_label": None if kind.role is None else labels[kind.role],
        "quantity": str(quantity),
        "hours": None if hours is None else decimal(hours),
        "unit_disbursement": None if unit is None else money(unit),
        "subproject_id": subproject,
        "subproject_label": None if subproject is None else labels[subproject],
        **_amounts(amounts),
        "previous_reestimated_amount": None,
        "consumption_year": year,
        "is_computed": kind.is_provision,
        "uses_inactive_object": False,
        "remaining_entry": {
            "is_available": not completed,
            "missing_conditions": ["task_not_completed"] if completed else [],
        },
    }
    return line, amounts, hours or Decimal(0)


def _subproject(task: Task, kind: LineKind) -> str | None:
    """Return the subproject of a line: its task's, but a provision stays outside."""
    return None if kind.is_provision else task.subproject


# --- The indicators of its estimate -------------------------------------------------------


def computable(value: str) -> JsonObject:
    """Return a value under the envelope of what may not be computable, computed (WF-IND-0010)."""
    return {"is_computable": True, "value": value, "reason": None}


def estimate_indicators(
    totals: Totals, witness: Mapping[str, JsonValue], labels: Mapping[str, str]
) -> JsonObject:
    """Return the answer of getEstimateIndicators for the lines of the structure.

    Every rate is set: each amount is computable. The calculation context and the gaps to the
    reference and to the previous revision are the witness's, the labels of the natures and
    subprojects those of the universe; the structure is phased, not cut in order items.
    """
    natures = [(nature, totals.by_cost_type[nature]) for nature in (LABOR, NON_LABOR, PROVISION)]
    subprojects = [
        (subproject, totals.by_subproject[subproject])
        for subproject in (SUBPROJECT_CONTROL, SUBPROJECT_TESTS, None)
    ]
    return {
        "context": witness["context"],
        "total": computable(money(totals.amount)),
        "by_cost_type": breakdown(natures, totals.amount, labels),
        "by_subproject": breakdown(subprojects, totals.amount, labels),
        "by_order_item": None,
        "provisions_identified": money(totals.by_cost_type[PROVISION]),
        "delta_to_reference": witness["delta_to_reference"],
        "delta_to_previous_revision": witness["delta_to_previous_revision"],
    }


def breakdown(
    entries: Sequence[tuple[str | None, Decimal]], total: Decimal, labels: Mapping[str, str]
) -> list[JsonValue]:
    """Return the parts of a total, each with its share; the shares sum to one exactly.

    A share is rounded to four decimals, and what the rounding leaves goes to the largest
    part. A part without a key is the set outside the subprojects, `unassigned`. Every amount
    and every share is computable: the rates of the universe are all set.
    """
    shares = [(amount / total).quantize(SHARE) for _, amount in entries]
    largest = max(range(len(entries)), key=lambda index: entries[index][1])
    shares[largest] += 1 - sum(shares)
    parts: list[JsonValue] = []
    for (key, amount), share in zip(entries, shares, strict=True):
        part: JsonObject = (
            {"key": "unassigned"} if key is None else {"key": key, "label": labels[key]}
        )
        part["amount"] = computable(money(amount))
        part["share"] = computable(decimal(share))
        parts.append(part)
    return parts
