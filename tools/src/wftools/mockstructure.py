# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The structure of a thousand tasks of the witness, described in tasks and lines.

The main structure of the witness project at the sizes of §4.6.2 (#376): its readable core first
(``mockwitness.CORE``), then a thousand tasks less the core's, drawn about it and linked to it —
phases, lots, their work tasks and milestones — and five thousand lines less the core's, five on
each work task and a sixth on some, as §4.6.2 counts five a task. The tasks drawn follow the core:
the lots of the control station after its factory acceptance, the others after the reception of
its studies; the commissioning of the core leads to the milestone of the commissioning of the lot
of the control station. So the float and the critical path of the core are those of the whole
structure. The whole is described here as the core is, in tasks and lines of ``mockwitness``, and
dated in hours of work on the calendar of each task, priced and emitted by ``wftools.mockcore``,
read today (WF-PLA-0010, WF-PLA-0160): the wiring, given to the cable fitter, works his week of four
days of ten hours, the rest the standard week. No line drawn is a provision: a line of provision is
created by the declaration of a risk alone (WF-DEV-0020, WF-RIS-0010), and the witness has three.
Every line drawn was in the offer, and the amendment 1 designated none of them: a labour line keeps
the budget the offer fixed, at the rates of 2025, and is re-estimated at the one rate of 2026 of its
category, as the two lines of the core the amendment did not designate (WF-REV-0050, #467).

A line names its category, its role and its subproject by the labels of the universe, as the
server resolves them. Amounts are ``Decimal``. Nothing here reads the clock or draws at random:
every drawn value comes from a hash of a fixed seed and of what it describes, so that two runs make
the same structure, whatever the version of Python. ``wftools.mockdata`` writes it, and
``wftools.mockwrites`` the writes made in it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from wftools.mockids import universe
from wftools.mockwitness import (
    CABLE_FITTER,
    COMMISSIONING,
    COMMISSIONING_TECHNICIAN,
    CORE,
    ELECTRICAL_ENGINEERING,
    ENGINEER,
    EQUIPMENT,
    GENERATED,
    OFFER_YEAR,
    PAYMENT_DELAY,
    PROVISIONS,
    SUBCONTRACTING,
    SUBPROJECT_CONTROL,
    Line,
    Link,
    N,
    Task,
    fixture,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

type JsonValue = str | int | bool | list[JsonValue] | dict[str, JsonValue] | None
type JsonObject = dict[str, JsonValue]

SEED = "waterfall-4.6.2"
"""The seed every drawn value is hashed with: changing it changes every volume."""

TASK_COUNT = 1_000
LINES_PER_TASK = 5

ELECTRICAL_RATE = Decimal("80.00")
"""The hourly rate of the electrical engineering in 2026, the reference year of the estimate:
the witness estimate reads 1,000.00 for 12.5 hours."""

COMMISSIONING_RATE = Decimal("75.00")
"""The hourly rate of the commissioning in 2026, the one the lines of the structure pay."""

LABOUR_RATES = {ELECTRICAL_ENGINEERING: ELECTRICAL_RATE, COMMISSIONING: COMMISSIONING_RATE}
"""The hourly rate of each labour category the structure employs, for the reference year."""

CENT = Decimal("0.01")
SHARE = Decimal("0.0001")

INFLATION_RATE = Decimal("0.03")
"""The inflation rate of the witness project (project.json), which projects an amount on the
year its line is consumed (WF-DEV-0040)."""

REFERENCE_YEAR = 2026
"""The reference year of the witness estimate: an amount of that year is not projected."""

RATE_STEP = Decimal("1.50")
"""How much an hourly rate of the volume of rates grew each year, up to the reference year."""


def hourly_rate(last_amount: Decimal, year: int) -> Decimal:
    """Return the rate of a category for a year, as the volume of rates gives it.

    Its rate of the reference year, less the step for each year before it (``listHourlyRates``,
    ``getHourlyRateGrid``).
    """
    return (last_amount - RATE_STEP * (REFERENCE_YEAR - year)).quantize(CENT)


# The universe of the other examples of the contract.
SUBPROJECT_TESTS = universe(802)
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


def money(value: Decimal) -> str:
    """Return an amount as the contract carries it: two decimals, never a float."""
    return str(value.quantize(CENT))


def inflated(amount: Decimal, year: int) -> Decimal:
    """Return an amount projected on a year, at the inflation rate of the witness project.

    A simplification of WF-DEV-0040: the whole line is projected on the year its task starts,
    not split across the years the task spans in proportion to its hours of work.
    """
    return (amount * (1 + INFLATION_RATE) ** (year - REFERENCE_YEAR)).quantize(CENT)


def decimal(value: Decimal) -> str:
    """Return an exact decimal without trailing zeros: 12.5, 40."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


# --- The structure of a thousand tasks --------------------------------------------------

PHASES = (
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
"""The phases drawn after the core, which holds the studies: each lot goes through them in turn."""

CABLING, COMMISSIONING_PHASE = 5, 8
"""The phase the cable fitter works, and the one the commissioning of the core leads to."""

LOTS = (
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
_CHAINS = 3
"""The work tasks of a lot run in three chains, each task after the one three places before."""

_CORE_TASKS, _CORE_LINES = 15, 9
"""The tasks and the lines of the core, which the thousand tasks and five thousand lines count."""


@dataclass(frozen=True, slots=True)
class LineKind:
    """What the n-th line of a work task is: its label, its category and its role."""

    label: str
    category: str
    role: str | None = None


LINE_KINDS = (
    LineKind("Heures d'ingénierie", ELECTRICAL_ENGINEERING, ENGINEER),
    LineKind("Heures de mise en service", COMMISSIONING, COMMISSIONING_TECHNICIAN),
    LineKind("Matériel", EQUIPMENT),
    LineKind("Sous-traitance", SUBCONTRACTING),
    LineKind("Heures de supervision", ELECTRICAL_ENGINEERING, ENGINEER),
    LineKind("Transport et manutention", SUBCONTRACTING),
)
"""The lines of a work task, in order; the sixth on some of them only."""

CABLING_KINDS = (
    LineKind("Heures de câblage", ELECTRICAL_ENGINEERING, CABLE_FITTER),
    LineKind("Heures de raccordement", ELECTRICAL_ENGINEERING, CABLE_FITTER),
    *LINE_KINDS[2:4],
    LineKind("Heures de repérage", ELECTRICAL_ENGINEERING, CABLE_FITTER),
    LINE_KINDS[5],
)
"""The lines of a work task of the wiring: its labour all the cable fitter's, on the week of four
days, so that the task works his calendar alone (WF-PLA-0010)."""


def network(core: Sequence[Task] = CORE) -> tuple[Task, ...]:
    """Return the phases drawn after the core, numbered after its rows, linked to it.

    Each phase holds the three lots, each lot its work tasks in three chains and a milestone after
    the last of each; a lot of a phase follows the milestone of the same lot in the phase before.
    The lots of the first phase follow the core: the control station its factory acceptance, the
    others the reception of the studies. The commissioning of the core leads to the milestone of
    the commissioning of the control station. The tasks a lot holds, thirty-four or thirty-five,
    make the count of a thousand with the core's; their lines, five thousand.
    """
    plan = _Plan(_rows(core))
    work = TASK_COUNT - _CORE_TASKS - len(PHASES) * (1 + 2 * len(LOTS))
    lots = len(PHASES) * len(LOTS)
    extra = TASK_COUNT * LINES_PER_TASK - _CORE_LINES - work * LINES_PER_TASK
    previous: list[int] = [N.FACTORY_ACCEPTANCE, N.STUDIES_RECEIVED, N.STUDIES_RECEIVED]
    roots: list[Task] = []
    done = 0
    for p, phase in enumerate(PHASES, start=1):
        summary = plan.number()
        children: list[Task] = []
        for n, (lot, subproject) in enumerate(LOTS, start=1):
            index = (p - 1) * len(LOTS) + n - 1
            count = (index + 1) * work // lots - index * work // lots
            lot_number = plan.number()
            tasks: list[Task] = []
            for k in range(1, count + 1):
                before = tasks[k - 1 - _CHAINS].number if k > _CHAINS else previous[n - 1]
                sixth = (done + 1) * extra // work - done * extra // work
                done += 1
                tasks.append(
                    plan.task(f"{p}.{n}.{k}", (Link(before),), subproject, LINES_PER_TASK + sixth)
                )
            ends = [Link(task.number) for task in tasks[-_CHAINS:]]
            if p == COMMISSIONING_PHASE and n == 1:
                ends.append(Link(N.COMMISSIONING))
            milestone = Task(
                plan.number(), f"Fin du lot {p}.{n}", is_milestone=True, links=tuple(ends)
            )
            previous[n - 1] = milestone.number
            children.append(Task(lot_number, f"{phase} — {lot}", children=(*tasks, milestone)))
        roots.append(Task(summary, phase, children=tuple(children)))
    return tuple(roots)


def _rows(core: Iterable[Task]) -> int:
    """Return how many rows the core takes: its tasks and their lines."""
    return sum(1 + len(task.lines) + _rows(task.children) for task in core)


@dataclass(slots=True)
class _Plan:
    """The tasks drawn, numbered in the order of their rows after those of the core."""

    row: int

    def number(self) -> int:
        """Return the number of the next row."""
        self.row += 1
        return GENERATED + self.row

    def task(self, key: str, links: tuple[Link, ...], subproject: str | None, lines: int) -> Task:
        """Return a work task, its duration drawn, its lines after it."""
        p = int(key.split(".", maxsplit=1)[0])
        verb = _VERBS[(int(key.rsplit(".", maxsplit=1)[1]) - 1) % len(_VERBS)]
        number = self.number()
        kinds = CABLING_KINDS if p == CABLING else LINE_KINDS
        drawn = tuple(
            _line(self.number(), kinds[index], f"{key}/{index}", subproject)
            for index in range(lines)
        )
        return Task(
            number,
            f"{verb} {key}",
            days=draw(f"duration/{key}", 3, 12),
            links=links,
            lines=drawn,
        )


def _line(number: int, kind: LineKind, key: str, subproject: str | None) -> Line:
    """Return a line drawn: hours for labour, a quantity and a unit disbursement otherwise.

    A labour line is budgeted as the offer priced it, at the rate of 2025 of its category: the
    amendment 1 did not designate it (WF-REV-0050, #467). The other lines are paid a month after
    their work, as the subcontracting of the core; the labour as it is worked (WF-DEV-0020,
    WF-IND-0100).
    """
    if kind.role is not None:
        hours = Decimal(draw(f"hours/{key}", 8, 160)) / 2
        return Line(
            number,
            kind.label,
            kind.category,
            hours=hours,
            role=kind.role,
            subproject=subproject,
            budgeted=offer_budget(hours, kind.category),
        )
    return Line(
        number,
        kind.label,
        kind.category,
        unit=Decimal(draw(f"unit/{key}", 1_000, 500_000)) / 100,
        subproject=subproject,
        payment_delay_days=PAYMENT_DELAY,
        quantity=Decimal(draw(f"quantity/{key}", 1, 20)),
    )


def offer_budget(hours: Decimal, category: str) -> Decimal:
    """Return the budget the offer fixed to a labour line: its hours at the rate of 2025 (#467)."""
    return hours * hourly_rate(LABOUR_RATES[category], OFFER_YEAR)


NETWORK = network()
"""The phases drawn after the core, numbered once."""


def described(core: Iterable[Task] = CORE) -> tuple[Task, ...]:
    """Return the whole structure: the core given, as described or as a write leaves it, first."""
    return (*core, *NETWORK)


def labels() -> dict[str, str]:
    """Return the labels of the categories, the roles and the subprojects of the universe."""
    labels = dict(CATEGORY_LABELS)
    labels.update(
        (role["resource_role_id"], role["label"]) for role in fixture("resource_roles")["items"]
    )
    labels.update((entry["subproject_id"], entry["label"]) for entry in fixture("subprojects"))
    return labels


@dataclass(frozen=True, slots=True)
class Fields:
    """What a node says of the fields of its facet: those computed here, those it accepts."""

    computed: list[JsonValue]
    editable: list[JsonValue]


def task_fields(*, is_summary: bool, is_milestone: bool, is_manual: bool = False) -> Fields:
    """Return what a task computes and what it accepts (WF-PLA-0130).

    A task in automatic mode computes its dates; one in manual mode enters them, and computes
    nothing. A summary computes its duration and its progress too, and accepts its label and its
    description; a milestone has no duration to enter. Every task, summary or leaf, accepts its
    attachment to an order item or a work package, last (WF-PLA-0130).
    """
    dates: list[JsonValue] = ["task.start", "task.finish"]
    editable: list[JsonValue] = ["task.label", "task.description"]
    attachment: list[JsonValue] = ["task.order_item_id", "task.work_package_id"]
    if is_summary:
        return Fields(["task.duration", *dates, "task.progress"], [*editable, *attachment])
    editable.append("task.scheduling_mode")
    if not is_milestone:
        editable.append("task.duration")
    if is_manual:
        editable.extend(dates)
        dates = []
    editable.append("task.progress")
    return Fields(dates, [*editable, *attachment])


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


def computable(value: str) -> JsonObject:
    """Return a value under the envelope of what may not be computable, computed (WF-IND-0010)."""
    return {"is_computable": True, "value": value, "reason": None}
