# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the portfolio of the witness: ten projects in small numbers (EP-11/US-2770).

The witness loads them beside PRJ-001 and PRJ-002, so that the portfolio has something to sum: the
offers of different probabilities of winning, one of them marked; a project completed in the
default period; an offer lost and one abandoned; projects in progress, one in alert, one whose
review is overdue. Each project is described here once, with its tasks, its lines, its actual
costs and their imports, its risks and their reviews, its revisions and their markings, its
transitions; ``description`` writes it in the form of the schemas of the contract — the writes the
loader replays, each validated by its model (``ProjectCreate``, ``NodeCreate``, ``RiskWrite``,
``RiskReviewWrite``, ``ActualCostLine``, ``StateTransition``, ``CurrentRevisionMark``…) —, under
``fixtures/witness/portfolio/`` (``make mock-data``), and ``mockslicereadings`` computes from it
the readings of the eight views of the portfolio the service must answer.

The slice lives out of the contract (EP-11, « Ce que le cadrage décide »). Its figures are chosen
so that every amount can be checked by hand, and so that no reading depends on a rule a lot of the
back has still to decide: every project has an inflation rate of nought, its revisions are all of
one reference year — the rate of a labour line is that of its category that year —, every task
lies within one month, and at each marking each task is either completed, at its finish, or ahead
of the marking, but the one task of PRJ-304 left started past its finish. Each line has a
quantity of one: a labour line costs its hours at the rate, another its unit disbursement.

A node has one identifier, the one its lineage has in the description: the loader derives those of
each revision from it, as it does for the tasks and lines of PRJ-001 (``witness.filling``). Nothing
here reads the clock or draws at random.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import cache

from wftools.mockids import (
    SLICE_COST_LINES,
    SLICE_IMPORTS,
    SLICE_NODES,
    SLICE_PROJECTS,
    SLICE_REVISIONS,
    SLICE_RISKS,
    identifier,
)
from wftools.mockstructure import LABOUR_RATES, JsonObject, JsonValue, decimal, hourly_rate, money
from wftools.mockwitness import (
    COMMISSIONING,
    COMMISSIONING_TECHNICIAN,
    ELECTRICAL_ENGINEERING,
    ENGINEER,
    EQUIPMENT,
    PROVISIONS,
    SUBCONTRACTING,
)

CREATED, PRICING, IN_PROGRESS = "created", "pricing", "in_progress"
COMPLETED, LOST, ABANDONED = "completed", "lost", "abandoned"
IDENTIFIED, DISMISSED = "identified", "dismissed"

ROLE_CATEGORIES = {ENGINEER: ELECTRICAL_ENGINEERING, COMMISSIONING_TECHNICIAN: COMMISSIONING}
"""The category each role of the slice holds (``resource_roles``), whose rate prices its lines."""

PLATFORM: JsonObject = {"kind": "platform"}
"""The author of every write of the witness: the platform (EP-05, « Le chargeur du témoin »)."""

DESCRIPTION = (
    "Description de la tranche du portefeuille engendrée par `make mock-data` "
    "(`wftools.mockslice`) : elle ne se retouche pas."
)


def at(day: date, hour: int = 9, minute: int = 0) -> datetime:
    """Return an instant of the slice, in universal time: a day, at nine by default."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)


def stamp(instant: datetime) -> str:
    """Return an instant as the contract carries it: 2026-06-03T09:00:00Z."""
    return instant.strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True, slots=True)
class Line:
    """A line of the estimate: a labour line by its role and hours, another by its disbursement."""

    label: str
    category: str
    role: str | None = None
    hours: Decimal | None = None
    unit: Decimal | None = None

    def amount(self, year: int) -> Decimal:
        """Return its amount in a revision of a reference year, inflation being nought."""
        if self.hours is not None:
            return self.hours * hourly_rate(LABOUR_RATES[self.category], year)
        return Decimal(str(self.unit))


@dataclass(frozen=True, slots=True)
class Task:
    """A task in manual mode, within one month, with its lines and its progress."""

    label: str
    start: date
    finish: date
    lines: tuple[Line, ...]
    started_on: date | None = None
    completed_on: date | None = None

    def completed_by(self, day: date) -> bool:
        """Whether the task is completed on a day: its completion day or after it (WF-IND-0030)."""
        return self.completed_on is not None and self.completed_on <= day


@dataclass(frozen=True, slots=True)
class Review:
    """A review of a risk, the first its declaration: the probability and state it retains."""

    at: datetime
    probability: Decimal
    state: str = IDENTIFIED


@dataclass(frozen=True, slots=True)
class Risk:
    """A risk: its severity, the total of its own estimate of one line, and its reviews.

    Its provision is its severity at the probability of its last review (WF-RIS-0010), borne by
    the task of rank ``task`` of the main structure while it is identified.
    """

    label: str
    severity: Decimal
    task: int
    reviews: tuple[Review, ...]

    def known_at(self, instant: datetime) -> Review | None:
        """Return its last review made at an instant or before, none before its declaration."""
        known = [review for review in self.reviews if review.at <= instant]
        return known[-1] if known else None

    def provision_at(self, instant: datetime) -> Decimal:
        """Return its provision at an instant, nought when it is not identified then."""
        known = self.known_at(instant)
        if known is None or known.state != IDENTIFIED:
            return Decimal("0.00")
        return (self.severity * known.probability).quantize(Decimal("0.01"))


@dataclass(frozen=True, slots=True)
class Import:
    """An import of actual costs: its instant, and its lines by date of document."""

    at: datetime
    costs: tuple[tuple[date, Decimal], ...]


@dataclass(frozen=True, slots=True)
class Revision:
    """A revision: opened, then marked under a version name, or abandoned, or left current."""

    opened: datetime
    marked: datetime | None = None
    version_name: str | None = None
    abandoned: datetime | None = None


@dataclass(frozen=True, slots=True)
class Transition:
    """A transition of the project, after its creation and its passage to pricing."""

    at: datetime
    to: str
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class Project:
    """A project of the slice: the first revision is its offer, designated at In progress."""

    rank: int
    label: str
    probability: Decimal
    created: datetime
    tasks: tuple[Task, ...]
    revisions: tuple[Revision, ...]
    transitions: tuple[Transition, ...] = ()
    risks: tuple[Risk, ...] = ()
    imports: tuple[Import, ...] = ()

    @property
    def project_id(self) -> str:
        """The identifier the witness imposes on the project."""
        return identifier(SLICE_PROJECTS, self.rank)

    @property
    def code(self) -> str:
        """Its code, after the three hundred projects of the volumes of §4.6.2."""
        return f"PRJ-{300 + self.rank}"

    @property
    def year(self) -> int:
        """The reference year of its revisions: that of the opening of its first (WF-REV-0060)."""
        return self.revisions[0].opened.year

    def revision_id(self, number: int) -> str:
        """Return the identifier of its revision of a number, from one."""
        return identifier(SLICE_REVISIONS, self.rank * 100 + number)

    def task_id(self, number: int) -> str:
        """Return the identifier of its task of a rank, from one."""
        return identifier(SLICE_NODES, self.rank * 1000 + number)

    def line_id(self, task: int, number: int) -> str:
        """Return the identifier of a line of a task, by their ranks."""
        return identifier(SLICE_NODES, self.rank * 1000 + 10 * task + number)

    def risk_id(self, number: int) -> str:
        """Return the identifier of its risk of a rank, from one."""
        return identifier(SLICE_RISKS, self.rank * 10 + number)

    def history(self) -> list[tuple[datetime, str | None, str]]:
        """Return its transitions in order, from its creation: instant, state left, state taken."""
        found: list[tuple[datetime, str | None, str]] = [
            (self.created, None, CREATED),
            (self.revisions[0].opened, CREATED, PRICING),
        ]
        for transition in self.transitions:
            found.append((transition.at, found[-1][2], transition.to))
        return found

    def state_on(self, day: date) -> str | None:
        """Return its state on a day: that of its last transition dated that day or before."""
        held = [to for instant, _, to in self.history() if instant.date() <= day]
        return held[-1] if held else None

    def state_before(self, instant: datetime) -> str:
        """Return its state just before an instant: the one a marking at that instant sees."""
        return [to for moment, _, to in self.history() if moment < instant][-1]

    def designated(self) -> datetime | None:
        """Return when its offer was designated reference: its passage to In progress."""
        return next((t.at for t in self.transitions if t.to == IN_PROGRESS), None)


def _d(text: str) -> date:
    return date.fromisoformat(text)


def _money(text: str) -> Decimal:
    return Decimal(text)


def _labour(label: str, role: str, hours: int) -> Line:
    return Line(label, ROLE_CATEGORIES[role], role=role, hours=Decimal(hours))


def _bought(label: str, category: str, amount: str) -> Line:
    return Line(label, category, unit=_money(amount))


def _task(label: str, start: str, finish: str, *lines: Line, done: bool = False) -> Task:
    """Return a task; ``done`` completes it at its finish, started at its start."""
    started, completed = (_d(start), _d(finish)) if done else (None, None)
    return Task(label, _d(start), _d(finish), lines, started, completed)


def _offer(created: str, marked: str | None = None) -> Revision:
    """Return the first revision: opened at half past nine the day of creation, marked « Offre »."""
    return Revision(
        at(_d(created), 9, 30), at(_d(marked)) if marked else None, "Offre" if marked else None
    )


def _review(opened: str, marked: str | None, name: str | None) -> Revision:
    """Return a revision opened at ten, at the marking of the previous one, then marked or not."""
    return Revision(at(_d(opened), 10), at(_d(marked)) if marked else None, name)


def _imported(on: str, *costs: tuple[str, str]) -> Import:
    return Import(at(_d(on)), tuple((_d(day), _money(amount)) for day, amount in costs))


def _risk(label: str, severity: str, task: int, *reviews: tuple[str, str, str]) -> Risk:
    return Risk(
        label,
        _money(severity),
        task,
        tuple(Review(at(_d(day)), Decimal(chance), state) for day, chance, state in reviews),
    )


def _in_progress(day: str) -> Transition:
    """Return the passage to In progress: the offer designated, the code entered (WF-CYC-0030)."""
    return Transition(at(_d(day)), IN_PROGRESS)


R1 = Project(
    1,
    "Modernisation de la chaufferie — Valence",
    Decimal("0.7"),
    at(_d("2025-09-08")),
    (
        _task(
            "Études",
            "2025-10-06",
            "2025-10-24",
            _labour("Études de détail", ENGINEER, 100),
            done=True,
        ),
        _task(
            "Fabrication",
            "2026-01-05",
            "2026-01-30",
            _bought("Fabrication de la chaudière", SUBCONTRACTING, "20000.00"),
            done=True,
        ),
        _task(
            "Mise en service",
            "2026-07-06",
            "2026-07-24",
            _labour("Mise en service", COMMISSIONING_TECHNICIAN, 80),
        ),
    ),
    (
        _offer("2025-09-08", "2025-09-22"),
        _review("2025-09-29", "2025-11-10", "Revue de novembre"),
        _review("2025-11-10", "2026-05-04", "Revue de mai"),
    ),
    (_in_progress("2025-09-29"),),
    # Declared before the review of November, and not reviewed since: its risks are not
    # re-examined between the last two marked revisions (WF-PTF-0110).
    (_risk("Défaillance d'un sous-traitant", "3000.00", 3, ("2025-10-13", "0.1", IDENTIFIED)),),
    (
        _imported("2025-11-04", ("2025-10-31", "7500.00")),
        _imported("2026-02-03", ("2026-01-30", "19000.00")),
        _imported("2026-04-07", ("2026-03-31", "500.00")),
    ),
)
"""In progress since 29 September 2025, nominal, reviewed on 4 May 2026: its risk not reviewed."""

R2 = Project(
    2,
    "Extension de l'unité de traitement — Valence",
    Decimal("0.5"),
    at(_d("2025-09-15")),
    (
        _task(
            "Études",
            "2025-11-03",
            "2025-11-21",
            _labour("Études de détail", ENGINEER, 150),
            done=True,
        ),
        _task(
            "Approvisionnement",
            "2026-02-02",
            "2026-02-27",
            _bought("Armoires électriques", EQUIPMENT, "30000.00"),
            done=True,
        ),
        _task(
            "Essais",
            "2026-09-07",
            "2026-09-25",
            _labour("Essais sur site", COMMISSIONING_TECHNICIAN, 120),
        ),
    ),
    (
        _offer("2025-09-15", "2025-10-01"),
        _review("2025-10-15", "2025-12-08", "Revue de décembre"),
        _review("2025-12-08", "2026-04-13", "Revue d'avril"),
    ),
    (_in_progress("2025-10-15"),),
    (
        _risk(
            "Dérive du coût de l'acier",
            "4000.00",
            3,
            ("2025-12-15", "0.5", IDENTIFIED),
            ("2026-03-02", "0.75", IDENTIFIED),
        ),
    ),
    (
        _imported("2025-12-01", ("2025-11-28", "16000.00")),
        _imported("2026-03-03", ("2026-02-27", "38000.00")),
    ),
)
"""In progress since 15 October 2025, its actual cost beyond its earned value: in alert."""

R3 = Project(
    3,
    "Rénovation de la sous-station — Valence",
    Decimal("0.6"),
    at(_d("2025-11-03")),
    (
        _task("Études", "2026-01-12", "2026-01-30", _labour("Études", ENGINEER, 60), done=True),
        _task(
            "Travaux",
            "2026-06-08",
            "2026-06-26",
            _bought("Travaux de génie électrique", SUBCONTRACTING, "25000.00"),
        ),
        _task("Réception", "2026-10-05", "2026-10-23", _labour("Réception", ENGINEER, 40)),
    ),
    (
        _offer("2025-11-03", "2025-12-01"),
        _review("2025-12-15", "2026-02-09", "Revue de février"),
        # Its current revision, never marked: what it holds is no reading of a past date.
        _review("2026-02-09", None, None),
    ),
    (_in_progress("2025-12-15"),),
    (_risk("Retard d'approvisionnement", "10000.00", 2, ("2026-01-05", "0.2", IDENTIFIED)),),
    (
        _imported("2026-02-02", ("2026-01-30", "4500.00")),
        _imported("2026-05-05", ("2026-04-30", "1200.00")),
    ),
)
"""In progress since 15 December 2025, last reviewed on 9 February 2026: its review overdue."""

R4 = Project(
    4,
    "Construction de l'atelier de montage — Valence",
    Decimal("0.8"),
    at(_d("2025-10-13")),
    (
        _task(
            "Génie civil",
            "2025-12-01",
            "2025-12-19",
            _bought("Dalle et fondations", SUBCONTRACTING, "9000.00"),
            done=True,
        ),
        Task(
            "Charpente",
            _d("2026-02-02"),
            _d("2026-02-20"),
            (_bought("Charpente métallique", SUBCONTRACTING, "1500.00"),),
            started_on=_d("2026-02-02"),
        ),
        _task("Montage", "2026-08-03", "2026-08-21", _labour("Montage", ENGINEER, 50)),
    ),
    (
        _offer("2025-10-13", "2025-11-03"),
        _review("2025-11-17", "2026-04-20", "Revue d'avril"),
    ),
    (_in_progress("2025-11-17"),),
    (),
    (_imported("2026-04-14", ("2025-12-31", "8600.00"), ("2026-02-27", "700.00")),),
)
"""In progress since 17 November 2025, its frame started past its finish: its schedule watched."""

C1 = Project(
    5,
    "Automatisation du banc de mesure — Valence",
    Decimal("0.6"),
    at(_d("2025-09-08")),
    (
        _task(
            "Études",
            "2025-10-06",
            "2025-10-24",
            _labour("Études", ENGINEER, 50),
            done=True,
        ),
        _task(
            "Réalisation",
            "2025-11-03",
            "2025-11-28",
            _bought("Réalisation du banc", SUBCONTRACTING, "12000.00"),
            done=True,
        ),
        _task(
            "Mise en service",
            "2026-01-12",
            "2026-01-30",
            _labour("Mise en service", COMMISSIONING_TECHNICIAN, 40),
            done=True,
        ),
    ),
    (
        _offer("2025-09-08", "2025-09-22"),
        _review("2025-09-29", "2025-12-08", "Revue de décembre"),
        _review("2025-12-08", "2026-03-16", "Clôture"),
    ),
    # Its current revision marked at the exit, the transition applied a minute later (WF-CYC-0090).
    (_in_progress("2025-09-29"), Transition(at(_d("2026-03-16"), 9, 1), COMPLETED)),
    # Identified in the offer, which its reserve keeps; dismissed in the period (WF-RIS-0050).
    (
        _risk(
            "Indisponibilité d'un poste d'essais",
            "5000.00",
            3,
            ("2025-09-15", "0.3", IDENTIFIED),
            ("2025-12-15", "0.3", DISMISSED),
        ),
    ),
    (
        _imported("2025-12-02", ("2025-10-31", "3800.00"), ("2025-11-28", "12500.00")),
        _imported("2026-02-03", ("2026-01-30", "2900.00")),
    ),
)
"""In progress from 29 September 2025, completed on 16 March 2026: in the default period."""

O1 = Project(
    6,
    "Extension du système de supervision — Valence",
    Decimal("0.6"),
    at(_d("2026-03-02")),
    (
        _task("Études", "2026-09-07", "2026-09-25", _labour("Études", ENGINEER, 120)),
        _task(
            "Fourniture",
            "2026-11-02",
            "2026-11-27",
            _bought("Serveurs de supervision", EQUIPMENT, "15000.00"),
        ),
        _task(
            "Mise en service",
            "2027-01-11",
            "2027-01-29",
            _labour("Mise en service", COMMISSIONING_TECHNICIAN, 60),
        ),
    ),
    (_offer("2026-03-02", "2026-04-20"),),
)
"""The offer marked, at 60 %: it contributes, weighted, at a past date (WF-PRJ-0090)."""

O2 = Project(
    7,
    "Mise en conformité de la station de pompage — Valence",
    Decimal("0.3"),
    at(_d("2026-04-07")),
    (_task("Études", "2026-10-05", "2026-10-23", _labour("Études", ENGINEER, 40)),),
    (_offer("2026-04-07"),),
)
"""An offer at 30 %, never marked: listed at a past date, it contributes to no sum."""

O3 = Project(
    8,
    "Remplacement du magasin automatisé — Valence",
    Decimal("0.8"),
    at(_d("2026-05-11")),
    (
        _task(
            "Fourniture",
            "2026-12-07",
            "2026-12-18",
            _bought("Transtockeurs", EQUIPMENT, "50000.00"),
        ),
    ),
    (_offer("2026-05-11"),),
)
"""An offer at 80 %, never marked: listed at a past date, it contributes to no sum."""

L1 = Project(
    9,
    "Rénovation du banc de mesure — Valence",
    Decimal("0.2"),
    at(_d("2025-10-06")),
    (
        _task(
            "Fourniture",
            "2026-03-02",
            "2026-03-20",
            _bought("Bancs de mesure", EQUIPMENT, "40000.00"),
        ),
    ),
    (_offer("2025-10-06", "2025-11-17"),),
    (Transition(at(_d("2026-02-16")), LOST, "Offre concurrente retenue"),),
)
"""An offer marked, then lost in the period: it counts in the conversion rate (WF-PTF-0050)."""

A1 = Project(
    10,
    "Modernisation de la ligne d'essais — Valence",
    Decimal("0.5"),
    at(_d("2025-11-17")),
    (_task("Études", "2026-02-02", "2026-02-20", _labour("Études", ENGINEER, 30)),),
    (Revision(at(_d("2025-11-17"), 9, 30), abandoned=at(_d("2026-01-19"))),),
    (Transition(at(_d("2026-01-19")), ABANDONED, "Projet suspendu par le client"),),
)
"""An offer abandoned in the period, its revision abandoned: it counts nowhere (WF-PTF-0050)."""

SLICE = (R1, R2, R3, R4, C1, O1, O2, O3, L1, A1)
"""The ten projects of the slice, in the order of their rank."""


# --- The description, in the form of the contract ---------------------------------------------


def _task_node(project: Project, number: int, task: Task) -> JsonObject:
    return {
        "node_id": project.task_id(number),
        "node": {
            "kind": "task",
            "parent_id": None,
            "task": {
                "label": task.label,
                "scheduling_mode": "manual",
                "start": {"date": task.start.isoformat()},
                "finish": {"date": task.finish.isoformat()},
            },
        },
        "started_on": None if task.started_on is None else task.started_on.isoformat(),
        "completed_on": None if task.completed_on is None else task.completed_on.isoformat(),
    }


def _line_node(parent: str, node_id: str, line: Line) -> JsonObject:
    return {
        "node_id": node_id,
        "node": {
            "kind": "estimate_line",
            "parent_id": parent,
            "estimate_line": {
                "label": line.label,
                "cost_category_id": line.category,
                "quantity": "1",
                "resource_role_id": line.role,
                "hours": None if line.hours is None else decimal(line.hours),
                "unit_disbursement": None if line.unit is None else money(line.unit),
                "payment_delay_days": 0,
            },
        },
    }


def _risk_entry(project: Project, number: int, risk: Risk) -> JsonObject:
    """Return a risk as declared, its own estimate, and its reviews after its declaration."""
    own = identifier(SLICE_NODES, project.rank * 1000 + 500 + 10 * number)
    first, *later = risk.reviews
    return {
        "risk_id": project.risk_id(number),
        "declared_at": stamp(first.at),
        "risk": {
            "label": risk.label,
            "description": None,
            "mitigation_notes": None,
            "probability": decimal(first.probability),
            "provision_cost_category_id": PROVISIONS,
            "provision_subproject_id": None,
            "provision_task_id": project.task_id(risk.task),
        },
        "own_estimate": [
            {
                "node_id": own,
                "node": {"kind": "task", "parent_id": None, "task": {"label": risk.label}},
            },
            _line_node(
                own,
                identifier(SLICE_NODES, project.rank * 1000 + 501 + 10 * number),
                Line(risk.label, SUBCONTRACTING, unit=risk.severity),
            ),
        ],
        "reviews": [
            {
                "at": stamp(review.at),
                "review": {
                    "probability": decimal(review.probability),
                    "state": review.state,
                    "lock_version": rank + 1,
                },
            }
            for rank, review in enumerate(later, start=1)
        ],
    }


def _import_entry(project: Project, number: int, imported: Import) -> JsonObject:
    audit: JsonObject = {
        "created_at": stamp(imported.at),
        "created_by": PLATFORM,
        "updated_at": stamp(imported.at),
        "updated_by": PLATFORM,
    }
    lines: list[JsonValue] = [
        {
            "cost_line_id": identifier(SLICE_COST_LINES, project.rank * 100 + number * 10 + item),
            "document_number": f"FA-{project.code}-{number:02d}",
            "document_item": str(item),
            "document_date": day.isoformat(),
            "amount": money(amount),
            "project_id": project.project_id,
            "subproject_id": None,
            "subproject_code": None,
            "subproject_label": None,
            "is_in_tracked_scope": True,
            "excluded_reason": None,
            "passthrough": {},
            "audit": audit,
        }
        for item, (day, amount) in enumerate(imported.costs, start=1)
    ]
    return {
        "cost_import_id": identifier(SLICE_IMPORTS, project.rank * 10 + number),
        "imported_at": stamp(imported.at),
        "lines": lines,
    }


def _revision_entry(project: Project, number: int, revision: Revision) -> JsonObject:
    mark: JsonValue = (
        None
        if revision.version_name is None
        else {"action": "mark", "version_name": revision.version_name}
    )
    return {
        "revision_id": project.revision_id(number),
        "opened_at": stamp(revision.opened),
        "create": {"description": None},
        "marked_at": None if revision.marked is None else stamp(revision.marked),
        "mark": mark,
        "abandoned_at": None if revision.abandoned is None else stamp(revision.abandoned),
    }


def value(project: Project) -> JsonObject:
    """Return the description of a project, each write in the form of its schema."""
    lines: list[JsonValue] = [
        _line_node(project.task_id(number), project.line_id(number, rank), line)
        for number, task in enumerate(project.tasks, start=1)
        for rank, line in enumerate(task.lines, start=1)
    ]
    return {
        "project_id": project.project_id,
        "created_at": stamp(project.created),
        "project": {
            "label": project.label,
            "description": None,
            "client": None,
            "code": project.code,
        },
        "inflation_rate": "0",
        "win_probability": decimal(project.probability),
        "reference_revision_id": project.revision_id(1) if project.designated() else None,
        "transitions": [
            {
                "from_state": left,
                "to_state": to,
                "occurred_at": stamp(instant),
                "actor": PLATFORM,
                "reason": next((t.reason for t in project.transitions if t.at == instant), None),
            }
            for instant, left, to in project.history()
        ],
        "revisions": [
            _revision_entry(project, number, revision)
            for number, revision in enumerate(project.revisions, start=1)
        ],
        "tasks": [
            _task_node(project, number, task) for number, task in enumerate(project.tasks, start=1)
        ],
        "lines": lines,
        "risks": [
            _risk_entry(project, number, risk) for number, risk in enumerate(project.risks, start=1)
        ],
        "imports": [
            _import_entry(project, number, imported)
            for number, imported in enumerate(project.imports, start=1)
        ],
    }


_STATES = {
    PRICING: "en chiffrage",
    IN_PROGRESS: "en cours",
    COMPLETED: "terminé",
    LOST: "perdu",
    ABANDONED: "abandonné",
}


def _summary(project: Project) -> str:
    final = project.history()[-1]
    return (
        f"{project.code}, « {project.label} », de la tranche du portefeuille du témoin : "
        f"{_STATES[final[2]]} depuis le {final[0].date().isoformat()}, "
        f"{len(project.tasks)} tâche(s), {len(project.revisions)} révision(s), "
        f"{len(project.risks)} risque(s), {len(project.imports)} import(s) de coûts réels "
        "(WF-QUA-0040, EP-11/US-2770)."
    )


@cache
def description() -> dict[str, JsonObject]:
    """Return the description of the slice, one document per project, by file name."""
    return {
        f"{project.code}.json": {
            "summary": _summary(project),
            "description": DESCRIPTION,
            "value": value(project),
        }
        for project in SLICE
    }


def instants(project: Project) -> list[datetime]:
    """Return every instant the description dates, for the checks of its chronology."""
    found = [project.created, *(t.at for t in project.transitions)]
    for revision in project.revisions:
        found.extend(
            each for each in (revision.opened, revision.marked, revision.abandoned) if each
        )
    found.extend(review.at for risk in project.risks for review in risk.reviews)
    found.extend(imported.at for imported in project.imports)
    return found
