# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The witness project the examples of the contract describe, said once (#287).

PRJ-001, « Modernisation du poste de commande », at one instant, today: its chronology, the
families of the identifiers of the universe, the roles its lines employ and their calendars,
and the readable core of its structure — the tasks and the lines whose identifiers and
figures are fixed, which the structure of a thousand tasks is to carry before the tasks
it draws, linked to them (EP-02/L27, #376). The other examples of the contract are read
from this: another reading of the same state, an earlier instant of the same chronology, the
immediate sequel of a write made today, or a counterfactual variant declared as such.

What the reference data says — the labels and calendars of the roles, the hours of the
calendars — is read from its fixtures (``resource_roles``, ``calendars``), written by hand:
this module names the roles the witness employs, it does not copy them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from wftools import REPOSITORY
from wftools.mockcalendar import FINISH_TO_START, START_TO_START, Calendar

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

FIXTURES = REPOSITORY / "fixtures" / "api"
"""Where the examples of the contract live, those of the universe by their name."""


def fixture(name: str) -> Any:
    """Return the value of an example of the universe, from its fixture."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["value"]


# --- Today and the chronology -----------------------------------------------------------------

TODAY = datetime(2026, 6, 3, 14, 5, tzinfo=UTC)
"""The instant every first example describes (decision of the user of 2026-10-05)."""


@dataclass(frozen=True, slots=True)
class Event:
    """A dated event of the life of the witness project, in universal time.

    Its hour is the one the examples write it at — the audit of what it creates or changes, the
    transition it makes —, midnight for an event no example dates to the hour.
    """

    on: date
    what: str
    at: time = time(0, 0)

    @property
    def instant(self) -> datetime:
        """Return the instant of the event, as an audit or a transition carries it."""
        return datetime.combine(self.on, self.at, UTC)


INSTALLED = Event(date(2025, 9, 1), "Installation, référentiel et comptes", time(9, 0))
CREATED = Event(date(2025, 10, 6), "PRJ-001 créé, à l'état Créé", time(9, 0))
OFFER_OPENED = Event(
    date(2025, 11, 3), "Ouverture de l'offre 100, passage en Chiffrage", time(8, 30)
)
OFFER_MARKED = Event(date(2025, 12, 15), "Offre v1.0 marquée", time(16, 0))
RISKS_IDENTIFIED = Event(
    date(2026, 1, 12),
    "Risques 751, 752 et 753 identifiés ; la première saisie ouvre la révision 101",
    time(10, 0),
)
ORDER_RECEIVED = Event(
    date(2026, 1, 15),
    "Commande reçue ; l'offre 100 désignée référence, passage En cours",
    time(11, 0),
)
AMENDMENT_MERGED = Event(
    date(2026, 2, 1),
    "Avenant 1 fusionné ; la révision 101 « Référence » marquée, référence",
    time(9, 0),
)
RISK_751_REVIEWED = Event(
    date(2026, 2, 2),
    "Réexamen de 751 : gravité portée à 1 250 ; la saisie ouvre la révision courante 102 ; "
    "753 écarté",
    time(9, 0),
)
RISK_752_OCCURRED = Event(
    date(2026, 2, 20),
    "Survenance de 752 : son devis propre fusionné dans la révision en cours, 102, la référence "
    "101 inchangée",
    time(16, 0),
)
STUDIES_STARTED = Event(date(2026, 3, 2), "Réexamen de 751 à 40 % ; début des études", time(9, 15))
COST_IMPORTS = tuple(
    Event(day, "Import de coûts réels", at)
    for day, at in (
        (date(2026, 4, 3), time(8, 30)),
        (date(2026, 5, 4), time(8, 30)),
        (date(2026, 5, 6), time(14, 0)),
        (date(2026, 5, 11), time(9, 0)),
        (date(2026, 6, 3), time(8, 30)),
    )
)
PLANNING_IMPORT_ABANDONED = Event(date(2026, 5, 20), "Import de planning, abandonné")
APRIL_EXTRACTION_REPLAYED = Event(
    date(2026, 6, 2), "Extraction d'avril rejouée et analysée ; expirée le lendemain", time(9, 1)
)
ESTIMATE_IMPORT_ANALYSED = Event(
    date(2026, 6, 3), "Import du devis analysé, applicable jusqu'au lendemain", time(8, 41)
)
"""The estimate imported this morning is still applicable today, an import analysed expiring a
day after its analysis (WF-ARC-0100): the frame of #287 analysed it on 1 June, which would have
let it expire before today (EP-02/L25)."""

CHRONOLOGY = tuple(
    sorted(
        (
            INSTALLED,
            CREATED,
            OFFER_OPENED,
            OFFER_MARKED,
            RISKS_IDENTIFIED,
            ORDER_RECEIVED,
            AMENDMENT_MERGED,
            RISK_751_REVIEWED,
            RISK_752_OCCURRED,
            STUDIES_STARTED,
            *COST_IMPORTS,
            PLANNING_IMPORT_ABANDONED,
            ESTIMATE_IMPORT_ANALYSED,
            APRIL_EXTRACTION_REPLAYED,
        ),
        key=lambda event: event.instant,
    )
)
"""The events up to today, in their order; what follows today is the sequel of a write."""

# --- The families of the identifiers ----------------------------------------------------------

PREFIX = "01926f3a-7c00-7000-8000-"


def identifier(family: int, number: int) -> str:
    """Return an identifier of a family: 0 for those written by hand, the others generated."""
    return f"{PREFIX}{family:04d}{number:08d}"


def universe(number: int) -> str:
    """Return an identifier the examples write by hand: 01926f3a-…-000000000521."""
    return identifier(0, number)


@dataclass(frozen=True, slots=True)
class Family:
    """A family of identifiers: a range of those written by hand, or a generated family."""

    what: str
    first: int
    last: int
    generated: int = 0
    hexadecimal: bool = False

    def holds(self, value: str) -> bool:
        """Whether an identifier is of the family: its prefix, its family, its number in range.

        The number of a family is written in decimal digits, or in hexadecimal ones for the few
        written by hand so (…0a01, …0c11); an identifier of the other writing is not of it.
        """
        tail = value.removeprefix(PREFIX)
        if not value.startswith(PREFIX) or len(tail) != len("000000000000"):
            return False
        family, number = tail[:4], tail[4:]
        digits = "0123456789abcdef" if self.hexadecimal else "0123456789"
        if not family.isdigit() or int(family) != self.generated:
            return False
        if not all(digit in digits for digit in number):
            return False
        return self.first <= int(number, 16 if self.hexadecimal else 10) <= self.last


NODES, LINEAGES, PROJECTS, CATEGORIES, RISKS, MILESTONES = 1, 2, 3, 4, 5, 6
"""The generated families: the nodes of the structure of a thousand tasks and their lineages; the
projects of the portfolio, the categories of the grid of rates, the risks of the portfolio and the
lineages of the milestones the health of its steering names (EP-02/L26)."""

_GENERATED = 99_999_999

IDENTIFIERS = (
    Family("projets", 1, 99),
    Family("révisions", 100, 199),
    Family("structures", 200, 299),
    Family("comptes", 300, 399),
    Family("catégories de coût", 400, 449),
    Family("rôles de ressources", 450, 459),
    Family("natures de coût", 460, 469),
    Family("nœuds d'organisation", 470, 479),
    Family("calendriers", 480, 499),
    Family("nœuds de la structure", 500, 599),
    Family("lignées, celle du nœud 5nn en 6nn", 600, 699),
    Family("rôles d'habilitation", 700, 709),
    Family("postes et lots du lotissement", 710, 749),
    Family("risques", 750, 799),
    Family("sous-projets", 800, 899),
    Family("sauvegardes", 900, 919),
    Family("tâches de fond", 920, 959),
    Family("collages et corrélations", 960, 999),
    Family("chronologies", 1000, 1009),
    Family("imports et téléversements", 0xA00, 0xAFF, hexadecimal=True),
    Family("lignes de coût réel", 0xC00, 0xC0F, hexadecimal=True),
    Family("imports de coûts réels", 0xC10, 0xCFF, hexadecimal=True),
    Family("nœuds engendrés", 1, _GENERATED, NODES),
    Family("lignées engendrées", 1, _GENERATED, LINEAGES),
    Family("projets du portefeuille", 1, _GENERATED, PROJECTS),
    Family("catégories de la grille des taux", 0, _GENERATED, CATEGORIES),
    Family("risques du portefeuille", 1, _GENERATED, RISKS),
    Family("jalons du portefeuille", 1, _GENERATED, MILESTONES),
)
"""Every family of identifier, on disjoint ranges: an identifier names one kind of object.

Every example keeps to it (#287, C16): EP-02/L25 moved the background tasks off the range of
the backups (901 to 905, now 931 to 935), and the pastes and the correlations onto theirs (911 to
913, now 971 to 973; 921 to 927, now 975 to 982). The order item 711, « Fourniture et montage des
armoires », is the one order item of the witness, which the lot « Poste de commande » bears
(WF-PLA-0130); its work package 712, « Armoires », is borne by no task: only the refusal to attach
it outside the subtree of the task of its order item speaks of it
(`task_attach_outside_order_item`).
"""

# --- The roles, their calendars ---------------------------------------------------------------

ENGINEER = universe(451)
COMMISSIONING_TECHNICIAN = universe(452)
CABLE_FITTER = universe(454)
"""The active roles of the witness (``resource_roles``): the electrical engineer and the
commissioning technician, whom its lines employ, on the standard week; and the cable fitter, on
the week of four days of ten hours, whom no line employs today — the write of the estimate that
gives him the wiring on site redates its task (EP-02/L22, ``mockwrites``)."""

STANDARD_WEEK = universe(481)
FOUR_DAY_WEEK = universe(482)


def calendars() -> dict[str, Calendar]:
    """Return the active calendars of the installation, by identifier (``calendars``)."""
    days = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    return {
        entry["calendar_id"]: Calendar(
            entry["calendar_id"], tuple(Decimal(entry["weekly_hours"][day]) for day in days)
        )
        for entry in fixture("calendars")
    }


def default_calendar() -> Calendar:
    """Return the calendar of a task without labour lines (WF-REF-0120)."""
    [default] = [entry for entry in fixture("calendars") if entry["is_default"]]
    return calendars()[default["calendar_id"]]


def role_calendars() -> dict[str, Calendar]:
    """Return the calendar of each active role, by identifier of the role (WF-PLA-0010)."""
    known = calendars()
    return {
        role["resource_role_id"]: known[role["calendar_id"]]
        for role in fixture("resource_roles")
        if role["is_active"]
    }


# --- The readable core of the structure -------------------------------------------------------

REFERENCE_PROVISION_751 = Decimal("250.00")
"""The provision of the risk 751 when the reference 101 was marked, on 1 February 2026: its
severity of 1,000 at 25 % (``risk_reviews``), before its review raised it to 1,250 at 40 %. The
reserve for risks of the reference counts it (WF-RIS-0050); the line of provision is budgeted so."""

PAYMENT_DELAY = 30
"""The payment delay of the subcontracting and of the terminal blocks, in days: paid a month
after their work (WF-IND-0100); the other lines, labour and provision included, have a delay of
nought, paid as they are worked (WF-DEV-0020)."""

SUBPROJECT_CONTROL = universe(801)
SUBCONTRACTING = universe(401)
ELECTRICAL_ENGINEERING = universe(402)
EQUIPMENT = universe(403)
PROVISIONS = universe(404)
COMMISSIONING = universe(405)


@dataclass(frozen=True, slots=True)
class Link:
    """A link of a task of the core to its predecessor, by the predecessor's number."""

    predecessor: int
    link_type: str = FINISH_TO_START
    lag: int = 0
    unit: str = "d"


@dataclass(frozen=True, slots=True)
class Line:
    """A line of the core: its node is its number, 5nn, its lineage 6nn.

    A labour line has its hours and its role, at the rate of its category; another its
    quantity and its unit disbursement. Its budget is its amount, but where the reference
    revision gives it another: nothing for a line merged by the occurrence of a risk
    (WF-RIS-0060) or added after the reference (WF-DEV-0020); for a provision, the provision
    the risk had when the reference was marked, which counts to the reserve for risks, never
    to the reference budget (WF-RIS-0050). Every line has a payment delay, the days after its work
    it is paid, which shifts it on the curve of the disbursements: nought unless said, as for the
    labour and the provision (WF-DEV-0020, WF-IND-0100).
    """

    number: int
    label: str
    category: str
    hours: Decimal | None = None
    role: str | None = None
    unit: Decimal | None = None
    subproject: str | None = None
    budgeted: Decimal | None = None
    is_provision: bool = False
    payment_delay_days: int = 0


@dataclass(frozen=True, slots=True)
class Task:
    """A task of the core: its node is its number, 5nn, its lineage 6nn.

    Its duration in days of work of eight hours, as its links' lags are in their units, both
    converted into hours by ``mockcalendar.to_hours`` (WF-PLA-0160); its lines and its
    subordinates. The progress of a task in automatic mode is read from its dates at TODAY; a
    task in manual mode carries the dates its user entered, and the progress its user declared.
    A summary may bear an order item of the work breakdown (WF-PLA-0130).
    """

    number: int
    label: str
    days: int = 0
    is_milestone: bool = False
    links: tuple[Link, ...] = ()
    lines: tuple[Line, ...] = ()
    children: tuple[Task, ...] = ()
    manual: tuple[date, date] | None = None
    progress: str | None = None
    order_item: OrderItem | None = None


@dataclass(frozen=True, slots=True)
class OrderItem:
    """An order item of the work breakdown of the witness, which a summary bears."""

    identifier: str
    label: str


ASSEMBLY = OrderItem(universe(711), "Fourniture et montage des armoires")
"""The one order item of the witness, which the lot « Poste de commande » bears (WF-PLA-0130),
and whose total the estimate presents (`estimate_indicators_breakdown`, WF-DEV-0060)."""

STEERING = universe(1000)
CUSTOMER = universe(1001)
TIMELINES = ((STEERING, "Comité de pilotage"), (CUSTOMER, "Revue client"))
"""The named timelines of the witness (WF-PLA-0140): the steering committee follows the studies,
their reception, the factory acceptance and the commissioning; the customer, the two receptions."""

INSCRIBED: dict[int, tuple[str, ...]] = {
    521: (STEERING,),
    525: (STEERING, CUSTOMER),
    556: (STEERING, CUSTOMER),
    565: (STEERING,),
}
"""The tasks of the core inscribed to each timeline, by their number (WF-PLA-0060)."""

TRACKED = frozenset({525, 556})
"""The milestones of the core inscribed to the time/time tracking, those ``milestone_tracking``
follows (WF-PLA-0060, WF-IND-0090)."""


STUDIES = Task(
    521,
    "Études",
    children=(
        Task(
            522,
            "Études de détail",
            days=30,
            lines=(
                Line(
                    527,
                    "Ingénierie de détail",
                    SUBCONTRACTING,
                    unit=Decimal("100000.00"),
                    payment_delay_days=PAYMENT_DELAY,
                ),
            ),
        ),
        Task(
            523,
            "Pupitres opérateurs",
            days=40,
            manual=(date(2026, 3, 2), date(2026, 4, 24)),
            progress="started",
        ),
        Task(524, "Revue de conception", days=10, links=(Link(522),)),
        Task(
            525,
            "Réception des études",
            is_milestone=True,
            links=(Link(524), Link(523, START_TO_START, 1, "w")),
        ),
        Task(526, "Dossier de conception", days=5, links=(Link(522, lag=-2),)),
    ),
)
"""The studies: the detailed studies, finished before today; the operator desks, in manual
mode, started and past their finish; the design review after them, the reception of the studies
at its end, also a week after the desks started; and the design file, two days before the
detailed studies finish, with float (WF-PLA-0030, WF-PLA-0080, WF-PLA-0100)."""

CONTROL_STATION = Task(
    551,
    "Poste de commande",
    order_item=ASSEMBLY,
    children=(
        Task(
            552,
            "Câblage des armoires",
            days=42,
            links=(Link(525, lag=1, unit="w"),),
            lines=(
                Line(
                    553,
                    "Raccordement des borniers",
                    ELECTRICAL_ENGINEERING,
                    hours=Decimal("12.5"),
                    role=ENGINEER,
                    subproject=SUBPROJECT_CONTROL,
                ),
                Line(
                    554,
                    "Borniers",
                    EQUIPMENT,
                    unit=Decimal("1234.56"),
                    subproject=SUBPROJECT_CONTROL,
                    payment_delay_days=PAYMENT_DELAY,
                ),
                Line(
                    555,
                    "Provision — risque de reprise du câblage",
                    PROVISIONS,
                    unit=Decimal("500.00"),
                    budgeted=REFERENCE_PROVISION_751,
                    is_provision=True,
                ),
            ),
        ),
        Task(
            541,
            "Risque survenu — Retard de livraison des armoires",
            children=(
                Task(
                    542,
                    "Relance du fournisseur",
                    days=5,
                    links=(Link(552, START_TO_START),),
                    lines=(
                        Line(
                            543,
                            "Frais de relance",
                            EQUIPMENT,
                            unit=Decimal("120.00"),
                            budgeted=Decimal(0),
                        ),
                    ),
                ),
                Task(
                    544,
                    "Transport exceptionnel",
                    days=5,
                    links=(Link(542),),
                    lines=(
                        Line(
                            545,
                            "Affrètement",
                            EQUIPMENT,
                            unit=Decimal("80.00"),
                            budgeted=Decimal(0),
                        ),
                    ),
                ),
            ),
        ),
        Task(556, "Réception usine", is_milestone=True, links=(Link(552),)),
    ),
)
"""The lot of the control station: the wiring of the cabinets a week after the reception of the
studies, 12.5 hours at 80.00 — 1,000.00 —, terminal blocks at 1,234.56 and the provision of 500
of the risk 751, budgeted at the 250 the reference knew; the subtree merged into the current
revision by the occurrence of the risk 752, its lines of 120 and 80 budgeted nothing
(WF-RIS-0060); and the factory acceptance at the end of the wiring."""

INSTALLATION = Task(
    561,
    "Installation sur site",
    children=(
        Task(
            562,
            "Montage des armoires sur site",
            days=123,
            links=(Link(556),),
            lines=(
                Line(
                    563,
                    "Câblage sur site",
                    ELECTRICAL_ENGINEERING,
                    hours=Decimal(120),
                    role=ENGINEER,
                    subproject=SUBPROJECT_CONTROL,
                ),
                Line(
                    564,
                    "Assistance aux essais de câblage",
                    COMMISSIONING,
                    hours=Decimal(40),
                    role=COMMISSIONING_TECHNICIAN,
                    subproject=SUBPROJECT_CONTROL,
                ),
            ),
        ),
        Task(
            565,
            "Mise en service",
            days=10,
            links=(Link(562),),
            lines=(
                Line(
                    566,
                    "Mise en service sur site",
                    COMMISSIONING,
                    hours=Decimal(80),
                    role=COMMISSIONING_TECHNICIAN,
                    subproject=SUBPROJECT_CONTROL,
                ),
            ),
        ),
    ),
)
"""The installation on site, after the factory acceptance: the cabinets mounted on site from
1 July to 18 December 2026, wired by the electrical engineer and tested with the commissioning
technician, both on the standard week; and the commissioning, which follows, from 21 December
2026 into January 2027, its line consumed in 2026, the year it starts (WF-DEV-0040). The wiring
on site given to the cable fitter, on the week of four days, puts the mounting on the days both
its roles work, four of eight hours (WF-PLA-0010): it finishes in 2027, and the commissioning
starts and is consumed there (EP-02/L22)."""

CORE = (STUDIES, CONTROL_STATION, INSTALLATION)
"""The readable core, to be the first roots of the structure, its rows its first rows (#376)."""

STUDIES_RECEIVED, STUDIES_LINE = 525, 527
WIRING, LABOUR, FACTORY_ACCEPTANCE = 552, 553, 556
"""The nodes of the core several readings name, said once: the reception of the studies and the
line of the detailed studies; the wiring of the cabinets, its labour line, and the factory
acceptance."""

# --- The risks ---------------------------------------------------------------------------------

IDENTIFIED, OCCURRED, DISMISSED = "identified", "occurred", "dismissed"


@dataclass(frozen=True, slots=True)
class Review:
    """A review of a risk: the instant it was made, the probability, severity and state retained.

    The first review of a risk is its identification; the declaration of its occurrence is a
    review too, the last (WF-RIS-0010, WF-RIS-0020).
    """

    at: datetime
    probability: Decimal
    severity: Decimal
    state: str = IDENTIFIED


@dataclass(frozen=True, slots=True)
class Risk:
    """A risk of the witness: what its user entered, its reviews, where its provision lies.

    Its severity is the total of its own estimate, as its reviews retain it, and its provision
    that severity at its probability: neither is entered (WF-RIS-0010). ``provision_line`` is
    the line of provision it bears in the structure of the current revision, while identified;
    ``reference_provision_line`` the one the reference revision bore, which the reserve for risks
    counts (WF-RIS-0050) — none for a risk identified after the reference was marked;
    ``own_structure`` its own cost structure in the current revision;
    ``merged`` the task of the core its occurrence merged its own estimate under (WF-RIS-0060).
    """

    number: int
    label: str
    description: str
    mitigation_notes: str | None
    own_structure: int
    reviews: tuple[Review, ...]
    reference_provision_line: int | None = None
    provision_line: int | None = None
    merged: int | None = None

    @property
    def last(self) -> Review:
        """Return the last review of the risk, which says its probability, severity and state."""
        return self.reviews[-1]

    def known_on(self, day: date) -> Review | None:
        """Return the last review of the risk made on a day or before, if any (WF-RIS-0010)."""
        known = [review for review in self.reviews if review.at.date() <= day]
        return known[-1] if known else None


def _at(event: Event, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(event.on, time(hour, minute), UTC)


REWORK = Risk(
    751,
    "Risque de reprise du câblage",
    "Les essais de l'armoire de commande peuvent révéler des défauts de câblage à reprendre "
    "sur site.",
    "Contrôle du câblage en atelier avant expédition ; essais de continuité systématiques.",
    214,
    (
        Review(RISKS_IDENTIFIED.instant, Decimal("0.25"), Decimal("1000.00")),
        Review(RISK_751_REVIEWED.instant, Decimal("0.25"), Decimal("1250.00")),
        Review(STUDIES_STARTED.instant, Decimal("0.4"), Decimal("1250.00")),
    ),
    reference_provision_line=555,
    provision_line=555,
)
DELIVERY_DELAY = Risk(
    752,
    "Retard de livraison des armoires",
    "Le fournisseur des armoires annonce un retard de livraison possible.",
    "Relance hebdomadaire du fournisseur ; transport exceptionnel réservé.",
    215,
    (
        Review(_at(RISKS_IDENTIFIED, 10, 30), Decimal("0.3"), Decimal("200.00")),
        Review(RISK_752_OCCURRED.instant, Decimal("0.3"), Decimal("200.00"), OCCURRED),
    ),
    reference_provision_line=557,
    merged=541,
)
AUTOMATION_ENGINEER = Risk(
    753,
    "Indisponibilité de l'automaticien",
    "L'automaticien du client pourrait ne pas être disponible pour la mise en service.",
    None,
    216,
    (
        Review(_at(RISKS_IDENTIFIED, 11), Decimal("0.05"), Decimal("12000.00")),
        Review(_at(RISK_751_REVIEWED, 14), Decimal("0.05"), Decimal("12000.00"), DISMISSED),
    ),
    reference_provision_line=567,
)
REGISTER = (REWORK, DELIVERY_DELAY, AUTOMATION_ENGINEER)
"""The register of the witness, in the order of declaration: the rework of the wiring, still
identified, its provision the line 555 of the core; the delay of the cabinets, occurred on
20 February, its own estimate merged into the current revision (WF-RIS-0060) — the subtree 541
of the core —; the unavailability of the automation engineer, dismissed on 2 February. All three
identified on 12 January, before the reference 101 was marked, which bore their provisions: the
lines 555, 557 and 567 of its structure (``mockhistory``)."""

# --- The reference, as marked -----------------------------------------------------------------

MERGED, COMMISSIONING_TASK = 541, 565
"""The subtree the occurrence of 752 merged into the current revision, and the commissioning."""

REFERENCE_PROVISIONS = {
    752: (
        WIRING,
        Line(557, "Provision — retard de livraison des armoires", PROVISIONS, is_provision=True),
    ),
    753: (
        COMMISSIONING_TASK,
        Line(567, "Provision — indisponibilité de l'automaticien", PROVISIONS, is_provision=True),
    ),
}
"""The lines of provision the reference bore and the current revision no longer does, by risk,
with the task that bore each: that of 752, retired by its occurrence (WF-RIS-0060), that of 753,
by its dismissal (WF-RIS-0010)."""


def rewritten(roots: Iterable[Task], change: Callable[[Task], Task]) -> tuple[Task, ...]:
    """Return the description with each task changed, its subordinates first."""

    def walk(each: Task) -> Task:
        return change(replace(each, children=tuple(walk(child) for child in each.children)))

    return tuple(walk(root) for root in roots)


def reference_provision(risk: Risk) -> Decimal:
    """Return the provision of a risk when the reference was marked, on 1 February 2026.

    Its severity at its probability, as its last review before then retained them (WF-RIS-0010,
    WF-RIS-0050); nothing for a risk identified after it, which has no share in the reserve.
    """
    known = risk.known_on(AMENDMENT_MERGED.on)
    if known is None:
        return Decimal("0.00")
    return (known.severity * known.probability).quantize(Decimal("0.01"))


def reference() -> tuple[Task, ...]:
    """Return the reference 101 as marked on 1 February 2026, from the core of today.

    Nothing was started — the studies start on 2 March —, the subtree the occurrence of 752
    merged on 20 February is not there yet, and each identified risk bears its line of provision
    at the provision it then had: 751 at 1,000 at 25 %, 752 and 753 on the lines the current
    revision no longer bears. Marked while the project was in progress, it is the previous
    review of the current revision, whose lines show its quantities (WF-RAE-0040).
    """
    provisions = {
        risk.reference_provision_line: reference_provision(risk)
        for risk in REGISTER
        if risk.reference_provision_line is not None
    }

    def change(task: Task) -> Task:
        # A line of provision of a risk not identified on 1 February was not in the reference.
        lines = tuple(
            replace(line, unit=provisions[line.number], budgeted=None)
            if line.is_provision
            else line
            for line in task.lines
            if not line.is_provision or line.number in provisions
        )
        added = tuple(
            replace(line, unit=provisions[line.number])
            for bearer, line in REFERENCE_PROVISIONS.values()
            if bearer == task.number
        )
        children = tuple(child for child in task.children if child.number != MERGED)
        return replace(task, lines=lines + added, children=children, progress=None)

    return rewritten(CORE, change)


# --- The actual costs --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CostImport:
    """An import of actual costs, as its journal says it (WF-CRE-0050).

    Its event, the instant it was applied; the import of the exchanges that applied it, by its
    number, opened and analysed a few minutes before; the period it extracted, each bound
    possibly missing; and the lines of other projects it read, rejected and signalled to its
    report (WF-CRE-0020), which the journal counts among the lines ignored.
    """

    number: int
    event: Event
    exchange: int
    period: tuple[date | None, date | None]
    rejected: int = 0


MARCH, APRIL, UNDATED, APRIL_AGAIN, MAY = (
    CostImport(0xC11, COST_IMPORTS[0], 0xA06, (date(2026, 3, 1), date(2026, 3, 31))),
    CostImport(0xC12, COST_IMPORTS[1], 0xA07, (date(2026, 4, 1), date(2026, 4, 30)), 1),
    CostImport(0xC13, COST_IMPORTS[2], 0xA08, (None, None), 37),
    CostImport(0xC14, COST_IMPORTS[3], 0xA09, (None, date(2026, 4, 30)), 12_345),
    CostImport(0xC15, COST_IMPORTS[4], 0xA14, (date(2026, 5, 1), None)),
)
JOURNAL = (MARCH, APRIL, UNDATED, APRIL_AGAIN, MAY)
"""The imports of actual costs of the witness, in their order: the extraction of March, that
of April, a file without a period of which no line was the project's, a re-extraction up to
30 April, which brings back the five lines already imported, and the extraction of May, from
1 May."""


@dataclass(frozen=True, slots=True)
class CostLine:
    """A line of actual cost of the witness: what the file of the ERP says of it (WF-CRE-0010).

    Its number, 0xc0n; its document, dated, its signed amount; the code of subproject its element
    of the work breakdown structure carries, if it has a subproject part, imputed to the
    subproject of that code if the project has one, to the project alone otherwise — as is a line
    without a subproject part (WF-CRE-0020); the columns kept of the file;
    the imports that brought it, the first creating it, the others updating it (WF-CRE-0010); and
    its exclusion from the tracked scope, when and why, kept by the imports after it
    (WF-CRE-0030).
    """

    number: int
    document: str
    on: date
    amount: Decimal
    code: str | None
    supplier: str
    text: str
    imports: tuple[CostImport, ...]
    excluded: tuple[datetime, str] | None = None


COSTS = (
    CostLine(
        0xC01,
        "FA-2026-0412",
        date(2026, 4, 21),
        Decimal("1800.00"),
        "SP-CAB",
        "Câbles du Rhône",
        "Câbles de commande du pupitre",
        (APRIL, APRIL_AGAIN),
    ),
    CostLine(
        0xC02,
        "AV-2026-0388",
        date(2026, 4, 8),
        Decimal("-200.00"),
        "SP-CAB",
        "Câbles du Rhône",
        "Avoir sur livraison incomplète",
        (APRIL, APRIL_AGAIN),
    ),
    CostLine(
        0xC03,
        "FA-2026-0301",
        date(2026, 3, 27),
        Decimal("1400.00"),
        "SP-AUT",
        "Automatismes Durand",
        "Automate de sécurité",
        (MARCH, APRIL_AGAIN),
    ),
    CostLine(
        0xC04,
        "FA-2026-0295",
        date(2026, 3, 20),
        Decimal("650.00"),
        "SP-REC",
        "Traiteur Lumière",
        "Réception du client sur site",
        (MARCH, APRIL_AGAIN),
        (datetime(2026, 4, 6, 9, 15, tzinfo=UTC), "Réception du client, non budgétée"),
    ),
    CostLine(
        0xC06,
        "FA-2026-0409",
        date(2026, 4, 10),
        Decimal("100000.00"),
        None,
        "Ingélec Études",
        "Études de détail du poste de commande",
        (APRIL, APRIL_AGAIN),
    ),
    CostLine(
        0xC05,
        "FA-2026-0521",
        date(2026, 5, 18),
        Decimal("2400.00"),
        "SP-CMD",
        "Automatismes Durand",
        "Écrans du poste de commande",
        (MAY,),
    ),
)
"""The lines of actual cost of the witness today: the purchases of cables, a credit note on them and
the safety controller, under codes of subproject the project does not have, imputed to it alone;
the reception of the customer, excluded from the tracked scope three days after its import; the
invoice of the detailed studies, 100,000 of subcontracting dated the day they finished, without a
subproject part, as their line 527 has none — its payment delay of thirty days shifts the
disbursement, not the date of the document (decision of the author, review of EP-02/L25) —; and
the screens of the control station, imputed to its subproject."""

PASSTHROUGH = ("Fournisseur", "Texte de commande", "Élément d'OTP")
"""The columns of the file the imports keep, in the order they declare them (WF-CRE-0010)."""


def hex_identifier(number: int) -> str:
    """Return an identifier written by hand in hexadecimal digits: 01926f3a-…-000000000c01."""
    return f"{PREFIX}{number:012x}"
