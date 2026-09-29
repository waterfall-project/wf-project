# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Generate the volumes the fake back serves: the sizes of §4.6.2 (EP-02/L2).

Usage: ``python -m wftools.mockdata [--check]``.

Four examples of the contract, written under ``fixtures/api/volume/`` and cited by it:

- ``nodes_thousand.json``, ``listNodes``: the main structure of the witness project, a
  thousand tasks — ten phases, thirty lots and their milestones — and five thousand
  estimate lines, five per task as §4.6.2 counts them: each work task carries five, and the
  lines the summaries and milestones do not carry are provisions, a sixth line spread
  evenly over the work tasks;
- ``portfolio_projects.json``, ``getPortfolioProjects``: the three hundred projects of the
  portfolio, the witness project and the offer of the other examples first;
- ``cost_categories.json``, ``listCostCategories``: the two hundred categories of §4.6.2,
  a hundred and fifty of them labour — the rows of the grid of hourly rates;
- ``hourly_rates.json``, ``listHourlyRates``: fifteen years of rates of one labour category,
  the contract serving the rates one category at a time.

They live in the universe of the other examples — the project, its revision and structure,
its subprojects, categories and roles keep their identifiers. Nothing here reads the clock
or draws at random: the day the examples are read is fixed, as their ``computed_at`` says,
and every drawn value comes from a hash of a fixed seed and of what it describes, so that
two runs write the same bytes, whatever the version of Python. Amounts are ``Decimal``,
summed exactly, and travel as the strings of the contract.

With ``--check``, nothing is written: the files on disk are compared with what the
generator writes, and a file missing, outdated or left over fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from wftools import REPOSITORY

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

type JsonValue = str | int | bool | list[JsonValue] | dict[str, JsonValue] | None
type JsonObject = dict[str, JsonValue]

VOLUME = REPOSITORY / "fixtures" / "api" / "volume"
"""Where the volumes are written: a directory the generator owns, file by file."""

SEED = "waterfall-4.6.2"
"""The seed every drawn value is hashed with: changing it changes every volume."""

PROJECT_START = date(2026, 3, 2)
"""The first working day of the structure, a Monday, as in the witness structure."""

AS_OF = date(2026, 3, 16)
"""The day the examples of the contract are read: the progress of the tasks is at that day."""

TASK_COUNT = 1_000
LINES_PER_TASK = 5
PROJECT_COUNT = 300
LABOR_CATEGORY_COUNT = 150
CATEGORY_COUNT = 200
RATE_YEARS = range(2012, 2027)
"""Fifteen years of rates, up to the reference year of the witness estimate."""

WATCH_THRESHOLD = Decimal("0.9")
ALERT_THRESHOLD = Decimal("0.8")
"""The thresholds of the zones of an index, those of the Vérif of WF-REF-0170-A."""

CENT = Decimal("0.01")

# The universe of the other examples of the contract.
PROJECT = "01926f3a-7c00-7000-8000-000000000001"
OFFER = "01926f3a-7c00-7000-8000-000000000002"
REFERENCE_MARKED_AT = "2026-02-01T09:00:00Z"
USER = "01926f3a-7c00-7000-8000-000000000301"
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

# The families of the identifiers this generator makes, apart from the universe's.
_NODE, _LINEAGE, _PROJECT, _CATEGORY = 1, 2, 3, 4

_AUDIT: JsonObject = {
    "created_at": "2026-01-05T09:00:00Z",
    "created_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
    "updated_at": "2026-01-05T09:00:00Z",
    "updated_by": {"kind": "user", "user_id": USER, "display_name": "Camille Martin"},
}

_DESCRIPTION = "Exemple engendré par `make mock-data` (`wftools.mockdata`) : il ne se retouche pas."


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


LINE_KINDS = (
    LineKind("Heures d'ingénierie", ELECTRICAL_ENGINEERING, ENGINEER, Decimal("80.00")),
    LineKind("Heures de mise en service", COMMISSIONING, COMMISSIONING_TECHNICIAN, Decimal(75)),
    LineKind("Matériel", EQUIPMENT),
    LineKind("Sous-traitance", SUBCONTRACTING),
    LineKind("Heures de supervision", ELECTRICAL_ENGINEERING, ENGINEER, Decimal("80.00")),
    LineKind("Provision — aléas de réalisation", PROVISIONS, is_provision=True),
)
"""The lines of a work task, in order; the sixth, a provision, only on some of them.

The rate of a labour line is its category's for the reference year: 80.00 an hour for the
electrical engineering, as the witness estimate reads it (12.5 hours, 1,000.00).
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


def nodes() -> JsonObject:
    """Return the answer of listNodes for the structure of a thousand tasks."""
    roots, activities = plan()
    schedule(roots, activities)
    spread_lines(activities)
    number(roots)
    emitter = _Emitter()
    for position, root in enumerate(roots):
        emitter.task(root, _Place(None, position, 1))
    totals = emitter.totals
    return {
        "items": emitter.items,
        "totals": {
            "task_count": totals.tasks,
            "estimate_line_count": totals.lines,
            "hours": decimal(totals.hours),
            "budgeted_amount": money(totals.amount),
            "reestimated_amount": money(totals.amount),
        },
    }


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
        computed: list[JsonValue] = (
            ["estimate_line.quantity", "estimate_line.unit_disbursement"]
            if LINE_KINDS[index].is_provision
            else []
        )
        place = _Place(task, index, level)
        self.items.append(_node(task.row + 1 + index, place, "estimate_line", line, computed))
        self.totals.lines += 1
        self.totals.hours += hours
        self.totals.amount += amount
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
        "subproject_id": None if kind.is_provision else task.subproject,
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


# --- The portfolio of three hundred projects -------------------------------------------

_SUBJECTS = (
    "Modernisation",
    "Extension",
    "Rénovation",
    "Automatisation",
    "Mise en conformité",
    "Remplacement",
    "Construction",
)
_OBJECTS = (
    "du poste de commande",
    "de la ligne d'essais",
    "de la station de pompage",
    "du banc de mesure",
    "de l'atelier de montage",
    "du réseau de distribution",
    "de la sous-station",
    "du système de supervision",
    "de l'unité de traitement",
    "du magasin automatisé",
    "de la chaufferie",
)
_WIN_PROBABILITIES = ("0.2", "0.3", "0.4", "0.6", "0.8")


def zone(index: Decimal) -> str:
    """Return the zone of an index, as the server classes it by the thresholds (WF-REF-0170)."""
    if index >= WATCH_THRESHOLD:
        return "nominal"
    if index >= ALERT_THRESHOLD:
        return "watch"
    return "alert"


_WITNESS_ROW: JsonObject = {
    "project_id": PROJECT,
    "label": "Modernisation du poste de commande",
    "code": "PRJ-001",
    "state": "in_progress",
    "reference_budget": "100000.00",
    "current_estimate": None,
    "win_probability": "1",
    "project_manager_projection": "100000.00",
    "cost_index": {
        "value": {
            "is_computable": False,
            "value": None,
            "reason": "Aucun coût réel à la date de calcul : le dénominateur de l’indice est nul.",
        },
        "zone": None,
    },
    "schedule_index": {
        "value": {"is_computable": True, "value": "0", "reason": None},
        "zone": "alert",
    },
    "last_marked_at": REFERENCE_MARKED_AT,
}

_OFFER_ROW: JsonObject = {
    "project_id": OFFER,
    "label": "Extension de la ligne d'essais",
    "code": "PRJ-002",
    "state": "pricing",
    "reference_budget": None,
    "current_estimate": None,
    "win_probability": "0.4",
    "project_manager_projection": None,
    "cost_index": None,
    "schedule_index": None,
    "last_marked_at": None,
}


def portfolio() -> JsonObject:
    """Return the answer of getPortfolioProjects for the three hundred projects."""
    items: list[JsonValue] = [_WITNESS_ROW, _OFFER_ROW]
    items.extend(_portfolio_row(n) for n in range(3, PROJECT_COUNT + 1))
    return {
        "scope": {
            "states": ["in_progress", "pricing"],
            "as_of": AS_OF.isoformat(),
            "from": None,
            "to": None,
            "org_node_id": None,
            "project_count": PROJECT_COUNT,
        },
        "items": items,
        # The whole portfolio in one page: the largest page the contract allows.
        "meta": {"limit": 500, "offset": 0, "total": PROJECT_COUNT},
    }


def _portfolio_row(n: int) -> JsonObject:
    amount = Decimal(draw(f"amount/{n}", 2_000, 200_000)) * 100
    row: JsonObject = {
        "project_id": identifier(_PROJECT, n),
        "label": f"{_SUBJECTS[n % len(_SUBJECTS)]} {_OBJECTS[n // len(_SUBJECTS) % len(_OBJECTS)]}",
        "code": f"PRJ-{n:03d}",
    }
    if n % 10 == 0:
        pricing: JsonObject = {
            "state": "pricing",
            "reference_budget": None,
            "current_estimate": money(amount),
            "win_probability": _WIN_PROBABILITIES[draw(f"win/{n}", 0, len(_WIN_PROBABILITIES) - 1)],
            "project_manager_projection": None,
            "cost_index": None,
            "schedule_index": None,
            "last_marked_at": None,
        }
        return row | pricing
    projection = amount * draw(f"projection/{n}", 95, 115) / 100
    marked = date(2026, 2, 2) + timedelta(days=draw(f"marked/{n}", 0, 25))
    progressing: JsonObject = {
        "state": "in_progress",
        "reference_budget": money(amount),
        "current_estimate": None,
        "win_probability": "1",
        "project_manager_projection": money(projection),
        "cost_index": _index(Decimal(draw(f"cost/{n}", 70, 120)) / 100),
        "schedule_index": _index(Decimal(draw(f"schedule/{n}", 70, 120)) / 100),
        "last_marked_at": f"{marked.isoformat()}T17:00:00Z",
    }
    return row | progressing


def _index(value: Decimal) -> JsonObject:
    return {
        "value": {"is_computable": True, "value": decimal(value), "reason": None},
        "zone": zone(value),
    }


# --- The grid of hourly rates -------------------------------------------------------------

_TRADES = (
    "Ingénierie mécanique",
    "Automatisme",
    "Électricité",
    "Instrumentation",
    "Génie civil",
    "Tuyauterie",
    "Chaudronnerie",
    "Informatique industrielle",
    "Qualité",
    "Méthodes",
)
_PURCHASES = (
    "Matériel mécanique",
    "Câbles",
    "Instruments",
    "Location d'engins",
    "Transport",
    "Essais en laboratoire",
    "Études externes",
)


def categories() -> list[JsonValue]:
    """Return the answer of listCostCategories: two hundred, a hundred and fifty of them labour."""
    labor = [
        (ELECTRICAL_ENGINEERING, "Ingénierie électrique"),
        (COMMISSIONING, "Mise en service"),
    ]
    labor.extend(
        (identifier(_CATEGORY, n), f"{_TRADES[n % len(_TRADES)]} — niveau {n // len(_TRADES) + 1}")
        for n in range(LABOR_CATEGORY_COUNT - len(labor))
    )
    non_labor = [(SUBCONTRACTING, "Sous-traitance"), (EQUIPMENT, "Matériel électrique")]
    others = CATEGORY_COUNT - LABOR_CATEGORY_COUNT - 1
    non_labor.extend(
        (
            identifier(_CATEGORY, LABOR_CATEGORY_COUNT + n),
            f"{_PURCHASES[n % len(_PURCHASES)]} — lot {n // len(_PURCHASES) + 1}",
        )
        for n in range(others - len(non_labor))
    )
    return [
        *_categories(labor, "MO", "641", LABOR),
        *_categories(non_labor, "ACH", "604", NON_LABOR),
        *_categories([(PROVISIONS, "Provisions pour risques")], "PRV", "681", PROVISION),
    ]


def _categories(
    entries: Iterable[tuple[str, str]], code: str, account: str, cost_type: str
) -> list[JsonValue]:
    return [
        {
            "cost_category_id": category,
            "code": f"{code}-{rank:03d}",
            "label": label,
            "cost_type_id": cost_type,
            "accounting_code": f"{account}{rank:03d}",
            "is_active": True,
            "audit": _AUDIT,
            "lock_version": 1,
        }
        for rank, (category, label) in enumerate(entries, start=1)
    ]


def hourly_rates() -> list[JsonValue]:
    """Return the answer of listHourlyRates: fifteen years of the electrical engineering."""
    last = RATE_YEARS[-1]
    return [
        {
            "cost_category_id": ELECTRICAL_ENGINEERING,
            "year": year,
            "amount": money(Decimal("80.00") - Decimal("1.50") * (last - year)),
            "audit": _AUDIT,
            "lock_version": 1,
        }
        for year in RATE_YEARS
    ]


# --- Writing and checking ------------------------------------------------------------------


def volumes() -> dict[str, JsonObject]:
    """Return every volume, as the example of the contract its file holds, by file name."""
    return {
        "nodes_thousand.json": _example(
            "La structure principale du projet aux volumes du §4.6.2 : mille tâches — dix "
            "phases, trente lots, leurs neuf cent trente tâches de travail et leurs jalons, "
            "datés en jours ouvrés, avec leur chemin critique — et cinq mille lignes de devis, "
            "cinq par tâche : cinq sur chaque tâche de travail, et une provision en sixième "
            "ligne sur trois cent cinquante d'entre elles.",
            nodes(),
        ),
        "portfolio_projects.json": _example(
            "Les trois cents projets du portefeuille du §4.6.2, en cours et en chiffrage, "
            "indices classés par les seuils de 0,9 et 0,8.",
            portfolio(),
        ),
        "cost_categories.json": _example(
            "Les deux cents catégories de coût du §4.6.2, dont cent cinquante de "
            "main-d'œuvre : les lignes de la grille des taux horaires.",
            categories(),
        ),
        "hourly_rates.json": _example(
            "Quinze ans de taux horaires de l'ingénierie électrique, de 2012 à 2026, "
            "l'année de référence du devis, à 80,00 de l'heure.",
            hourly_rates(),
        ),
    }


def _example(summary: str, value: JsonValue) -> JsonObject:
    return {"summary": summary, "description": _DESCRIPTION, "value": value}


# The envelope of an example and its value are laid out; below them, one line per item.
_EXPANDED_DEPTH = 2


def render(example: JsonObject) -> str:
    """Return the text of an example: one line for each item of its lists, for readable diffs."""
    return _render(example, 0) + "\n"


def _render(value: JsonValue, depth: int) -> str:
    indent = "  " * depth
    inner = indent + "  "
    if isinstance(value, list) and value:
        items = ",\n".join(inner + _compact(item) for item in value)
        return f"[\n{items}\n{indent}]"
    if isinstance(value, dict) and depth < _EXPANDED_DEPTH:
        fields = ",\n".join(
            f"{inner}{_compact(key)}: {_render(item, depth + 1)}" for key, item in value.items()
        )
        return f"{{\n{fields}\n{indent}}}"
    return _compact(value)


def _compact(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def write(directory: Path) -> list[Path]:
    """Write every volume in the directory, removing a file it no longer makes."""
    directory.mkdir(parents=True, exist_ok=True)
    expected = {name: render(example) for name, example in volumes().items()}
    for stale in sorted(set(_files(directory)) - expected.keys()):
        (directory / stale).unlink()
    written: list[Path] = []
    for name, text in expected.items():
        path = directory / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def check(directory: Path) -> list[str]:
    """Return what differs between the directory and what the generator writes."""
    expected = {name: render(example) for name, example in volumes().items()}
    present = _files(directory)
    problems = [f"{name} is left over" for name in sorted(set(present) - expected.keys())]
    for name, text in expected.items():
        path = directory / name
        if name not in present:
            problems.append(f"{name} is missing")
        elif path.read_text(encoding="utf-8") != text:
            problems.append(f"{name} is outdated")
    return problems


def _files(directory: Path) -> list[str]:
    return sorted(path.name for path in directory.glob("*.json")) if directory.is_dir() else []


def main(arguments: list[str], directory: Path = VOLUME) -> int:
    """Write the volumes, or check that the versioned ones are what the generator writes."""
    parser = argparse.ArgumentParser(
        prog="wftools.mockdata", description="Generate the volumes the fake back serves."
    )
    parser.add_argument("--check", action="store_true", help="compare, write nothing")
    options = parser.parse_args(arguments)
    if options.check:
        problems = check(directory)
        for problem in problems:
            print(f"  {directory}: {problem}, run make mock-data", file=sys.stderr)
        return 1 if problems else 0
    for path in write(directory):
        print(f"  -> {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
