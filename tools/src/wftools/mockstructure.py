# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of a thousand tasks the fake back serves, and its estimate indicators.

The main structure of the witness project at the sizes of §4.6.2: a thousand tasks — phases,
lots, their work tasks and milestones — and five lines per task as §4.6.2 counts them. Each
work task carries five lines; the lines the summaries and milestones do not carry are
provisions, a sixth line spread evenly over the work tasks. The tasks are dated in working
days from their finish-to-start links, with their total float, and their progress is the
one of the day the examples of the contract are read. Amounts are ``Decimal``, summed
exactly as the lines are made, so that the indicators of the estimate are those of the
lines the grid shows.

Nothing here reads the clock or draws at random: every drawn value comes from a hash of a
fixed seed and of what it describes, so that two runs make the same structure, whatever the
version of Python. ``wftools.mockdata`` writes it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

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

# The universe of the other examples of the contract.
SUBPROJECT_CONTROL = "01926f3a-7c00-7000-8000-000000000801"
SUBPROJECT_TESTS = "01926f3a-7c00-7000-8000-000000000802"
SUBCONTRACTING = "01926f3a-7c00-7000-8000-000000000401"
ELECTRICAL_ENGINEERING = "01926f3a-7c00-7000-8000-000000000402"
EQUIPMENT = "01926f3a-7c00-7000-8000-000000000403"
PROVISIONS = "01926f3a-7c00-7000-8000-000000000404"
COMMISSIONING = "01926f3a-7c00-7000-8000-000000000405"
ENGINEER = "01926f3a-7c00-7000-8000-000000000451"
COMMISSIONING_TECHNICIAN = "01926f3a-7c00-7000-8000-000000000452"
LABOR = "01926f3a-7c00-7000-8000-000000000461"
NON_LABOR = "01926f3a-7c00-7000-8000-000000000462"
PROVISION = "01926f3a-7c00-7000-8000-000000000463"

# The families of the identifiers of the nodes; wftools.mockdata numbers the others from 3.
_NODE, _LINEAGE = 1, 2


def draw(key: str, low: int, high: int) -> int:
    """Return an integer of [low, high], fixed by the seed and by the key it describes."""
    digest = hashlib.sha256(f"{SEED}/{key}".encode()).digest()
    return low + int.from_bytes(digest[:8]) % (high - low + 1)


def identifier(family: int, number: int) -> str:
    """Return the identifier of a generated object, apart from those of the universe."""
    return f"01926f3a-7c00-7000-8000-{family:04d}{number:08d}"


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
    by_cost_type: dict[str, Decimal] = field(default_factory=dict[str, Decimal])
    by_subproject: dict[str | None, Decimal] = field(default_factory=dict[str | None, Decimal])

    def add(self, kind: LineKind, subproject: str | None, amount: Decimal, hours: Decimal) -> None:
        """Count a line: its hours, its amount, under its nature and its subproject."""
        self.lines += 1
        self.hours += hours
        self.amount += amount
        self.by_cost_type[kind.cost_type] = (
            self.by_cost_type.get(kind.cost_type, Decimal(0)) + amount
        )
        self.by_subproject[subproject] = self.by_subproject.get(subproject, Decimal(0)) + amount


@dataclass(frozen=True, slots=True)
class Structure:
    """The answer of listNodes for the structure, and the totals its lines sum to."""

    nodes: JsonObject
    totals: Totals


def structure() -> Structure:
    """Plan, date and number the structure of a thousand tasks, and make its nodes."""
    roots, activities = plan()
    schedule(roots, activities)
    spread_lines(activities)
    number(roots)
    emitter = _Emitter()
    for position, root in enumerate(roots):
        emitter.task(root, _Place(None, position, 1))
    totals = emitter.totals
    answer: JsonObject = {
        "items": emitter.items,
        "totals": {
            "task_count": totals.tasks,
            "estimate_line_count": totals.lines,
            "hours": decimal(totals.hours),
            "budgeted_amount": money(totals.amount),
            "reestimated_amount": money(totals.amount),
        },
    }
    return Structure(answer, totals)


@dataclass(frozen=True, slots=True)
class _Place:
    """Where a node sits: under which task, at which rank among its siblings, how deep."""

    parent: Task | None
    position: int
    level: int


@dataclass(slots=True)
class _Emitter:
    """The nodes of the structure, depth first, and their totals as they are made."""

    items: list[JsonValue] = field(default_factory=list["JsonValue"])
    totals: Totals = field(default_factory=Totals)

    def task(self, task: Task, place: _Place) -> Decimal:
        """Append a task, its lines and its subordinates; return the amount they carry."""
        facet = _task_facet(task)
        node = _node(task.row, place, "task", facet, _task_computed(task))
        if task.predecessors:
            node["predecessors"] = [
                {
                    "predecessor_node_id": identifier(_NODE, before.row),
                    "link_type": "finish_to_start",
                    "lag_days": 0,
                }
                for before in task.predecessors
            ]
        self.items.append(node)
        self.totals.tasks += 1
        amount = Decimal(0)
        for index in range(task.lines):
            amount += self._line(
                task, index, place.level + 1, completed=facet["progress"] == "completed"
            )
        for rank, child in enumerate(task.children):
            amount += self.task(child, _Place(task, rank, place.level + 1))
        facet["budgeted_amount"] = money(amount)
        facet["reestimated_amount"] = money(amount)
        return amount

    def _line(self, task: Task, index: int, level: int, *, completed: bool) -> Decimal:
        line, amount, hours = _line(task, index, completed=completed)
        kind = LINE_KINDS[index]
        computed: list[JsonValue] = (
            ["estimate_line.quantity", "estimate_line.unit_disbursement"]
            if kind.is_provision
            else []
        )
        place = _Place(task, index, level)
        self.items.append(_node(task.row + 1 + index, place, "estimate_line", line, computed))
        self.totals.add(kind, _subproject(task, kind), amount, hours)
        return amount


def _node(
    row: int, place: _Place, kind: str, facet: JsonObject, computed: list[JsonValue]
) -> JsonObject:
    return {
        "node_id": identifier(_NODE, row),
        "lineage_id": identifier(_LINEAGE, row),
        "kind": kind,
        "parent_id": None if place.parent is None else identifier(_NODE, place.parent.row),
        "position": place.position,
        "row_number": row,
        "level": place.level,
        "lock_version": 1,
        kind: facet,
        "computed_fields": computed,
    }


def _task_facet(task: Task) -> JsonObject:
    state = progress(task)
    facet: JsonObject = {
        "label": task.label,
        "scheduling_mode": "automatic",
        "duration_days": task.duration,
        "start_date": working_day(task.start).isoformat(),
        "finish_date": working_day(task.end).isoformat(),
        "progress": state,
    }
    if state != "not_started" and not task.is_summary:
        facet["started_on"] = working_day(task.start).isoformat()
    if state == "completed" and not task.is_summary:
        facet["completed_on"] = working_day(task.end).isoformat()
    facet["is_summary"] = task.is_summary
    facet["is_milestone"] = task.is_milestone
    facet["budgeted_amount"] = money(Decimal(0))
    facet["reestimated_amount"] = money(Decimal(0))
    if not task.is_summary:
        facet["total_float_days"] = task.late_end - task.end
        facet["is_critical"] = task.late_end == task.end
    return facet


def _task_computed(task: Task) -> list[JsonValue]:
    dates: list[JsonValue] = ["task.start_date", "task.finish_date"]
    if task.is_summary:
        return ["task.duration_days", *dates, "task.progress"]
    return dates


def _line(task: Task, index: int, *, completed: bool) -> tuple[JsonObject, Decimal, Decimal]:
    """Return an estimate line of a work task, its amount and its hours."""
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
    line: JsonObject = {
        "label": kind.label,
        "cost_category_id": kind.category,
        "resource_role_id": kind.role,
        "quantity": str(quantity),
        "hours": None if hours is None else decimal(hours),
        "unit_disbursement": None if unit is None else money(unit),
        "subproject_id": _subproject(task, kind),
        "budgeted_amount": money(amount),
        "reestimated_amount": money(amount),
        "previous_reestimated_amount": None,
        "is_computed": kind.is_provision,
        "remaining_entry": {
            "is_available": not completed,
            "missing_conditions": ["task_not_completed"] if completed else [],
        },
    }
    return line, amount, hours or Decimal(0)


def _subproject(task: Task, kind: LineKind) -> str | None:
    """Return the subproject of a line: its task's, but a provision stays outside."""
    return None if kind.is_provision else task.subproject


# --- The indicators of its estimate -------------------------------------------------------


def estimate_indicators(
    totals: Totals, context: JsonValue, delta: JsonValue, labels: Mapping[str, str]
) -> JsonObject:
    """Return the answer of getEstimateIndicators for the lines of the structure.

    The calculation context and the gap to the previous revision are the witness's, the
    labels of the natures and subprojects those of the universe.
    """
    natures = [(nature, totals.by_cost_type[nature]) for nature in (LABOR, NON_LABOR, PROVISION)]
    subprojects = [
        (subproject, totals.by_subproject[subproject])
        for subproject in (SUBPROJECT_CONTROL, SUBPROJECT_TESTS, None)
    ]
    return {
        "context": context,
        "total": money(totals.amount),
        "by_cost_type": breakdown(natures, totals.amount, labels),
        "by_subproject": breakdown(subprojects, totals.amount, labels),
        "provisions_identified": money(totals.by_cost_type[PROVISION]),
        "delta_to_previous_revision": delta,
    }


def breakdown(
    entries: Sequence[tuple[str | None, Decimal]], total: Decimal, labels: Mapping[str, str]
) -> list[JsonValue]:
    """Return the parts of a total, each with its share; the shares sum to one exactly.

    A share is rounded to four decimals, and what the rounding leaves goes to the largest
    part. A part without a key is the set outside the subprojects, `unassigned`.
    """
    shares = [(amount / total).quantize(SHARE) for _, amount in entries]
    largest = max(range(len(entries)), key=lambda index: entries[index][1])
    shares[largest] += 1 - sum(shares)
    parts: list[JsonValue] = []
    for (key, amount), share in zip(entries, shares, strict=True):
        part: JsonObject = (
            {"key": "unassigned"} if key is None else {"key": key, "label": labels[key]}
        )
        part["amount"] = money(amount)
        part["share"] = decimal(share)
        parts.append(part)
    return parts
