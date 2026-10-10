# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The witness project the examples of the contract describe, said once (#287).

PRJ-001, « Modernisation du poste de commande », at one instant, today: its chronology, the
identifiers of its nodes, in the families of ``mockids``, the roles its lines employ and their
calendars, and the readable core of its structure — the tasks and the lines whose identifiers and
figures are fixed, which the structure of a thousand tasks carries before the tasks it
draws, linked to them (``mockstructure``, EP-02/L27, #376). The other examples of the contract
are read from this: another reading of the same state, an earlier instant of the same chronology,
the immediate sequel of a write made today, or a counterfactual variant declared as such.

What the reference data says — the roles, the calendars — is read from its fixtures, written by
hand (``resource_roles``, ``calendars``): this module names what the witness employs, never copies.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from wftools import REPOSITORY
from wftools.mockcalendar import FINISH_TO_START, START_TO_START, Calendar
from wftools.mockids import LINEAGES, NODES, identifier, universe

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

FIXTURES = REPOSITORY / "fixtures" / "api"
"""Where the examples of the contract live, those of the universe by their name."""


def fixture(name: str) -> Any:
    """Return the value of an example of the universe, from its fixture."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["value"]


def by_identifier(name: str, key: str) -> list[Any]:
    """Return the objects of a list of the reference, in the order of their identifier.

    The list itself comes in the order a reading without sort gives — by label or by code —; what
    is drawn from it — a breakdown by nature, a workload by role — keeps the order of the
    identifiers, which no relabelling moves.
    """
    return sorted(fixture(name)["items"], key=lambda entry: str(entry[key]))


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
OFFER_YEAR = OFFER_MARKED.on.year
"""The reference year of the offer, marked in December 2025: its lines are priced at the rates of
that year, and the lines the amendment 1 did not designate keep the budget it fixed so (#467)."""
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
    "Réexamen de 751 : gravité portée à 1 250 000 ; la saisie ouvre la révision courante 102 ; "
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

# --- The nodes and their lineages ------------------------------------------------------------

GENERATED = 1_000_000
"""Where the numbers of the generated nodes start: the row r of the structure as described is
GENERATED + r, the identifier r of the family of the generated nodes and the lineage r of theirs,
numbered once: a write that adds or removes a row leaves every identifier as it was."""


def node_id(number: int) -> str:
    """Return the identifier of a node of the structure: 5nn for the core, generated otherwise."""
    if number < GENERATED:
        return universe(number)
    return identifier(NODES, number - GENERATED)


def lineage_id(number: int) -> str:
    """Return the identifier of the lineage of a node: 6nn for the node 5nn of the core."""
    if number < GENERATED:
        return universe(number + LINEAGE_OFFSET)
    return identifier(LINEAGES, number - GENERATED)


LINEAGE_OFFSET = 100
"""What separates the lineage of a node of the core from its node: 5nn is of the lineage 6nn."""


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
        for entry in fixture("calendars")["items"]
    }


def default_calendar() -> Calendar:
    """Return the calendar of a task without labour lines (WF-REF-0120)."""
    [default] = [entry for entry in fixture("calendars")["items"] if entry["is_default"]]
    return calendars()[default["calendar_id"]]


def role_calendars() -> dict[str, Calendar]:
    """Return the calendar of each active role, by identifier of the role (WF-PLA-0010)."""
    known = calendars()
    return {
        role["resource_role_id"]: known[role["calendar_id"]]
        for role in fixture("resource_roles")["items"]
        if role["is_active"]
    }


# --- The readable core of the structure -------------------------------------------------------

RISK_SCALE = 1000
"""The scale of the risks 751 and 753 to the structure of a thousand tasks: their figures of the
core, a thousand times (decision 4 of the frame of #287, option (a) of the author of 2026-10-07,
EP-14/L45b). Their severity is a share of the reference budget of the whole structure, which the
matrix reads (WF-RIS-0040): at the figures of the core, every risk would fall to its first level of
severity. The risk 752 keeps the figures of its Vérif (WF-RIS-0060)."""

REFERENCE_PROVISION_751 = Decimal("250.00") * RISK_SCALE
"""The provision of the risk 751 when the reference 101 was marked, on 1 February 2026: its
severity of 1,000,000 at 25 % (``risk_reviews``), before its review raised it to 1,250,000 at
40 %. The reserve for risks of the reference counts it (WF-RIS-0050); the line of provision is
budgeted so."""

PAYMENT_DELAY = 30
"""The payment delay of the subcontracting and of the terminal blocks, in days: paid a month
after their work (WF-IND-0100); the other lines, labour and provision included, have a delay of
nought, paid as they are worked (WF-DEV-0020)."""

SUBPROJECT_CONTROL = universe(801)
SUBPROJECT_TESTS = universe(802)
"""The subprojects of the witness: the control station, and the tests and commissioning, which no
line of the core bears (``subprojects``)."""
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

    A labour line has its hours and its role, at the one rate of its category for the reference
    year of its revision; another its quantity, a decimal, and its unit disbursement. Its budget is
    its amount, but where the reference gives another: nothing for a line merged by an occurrence
    (WF-RIS-0060) or added after the reference (WF-DEV-0020); for a provision, the one the reference
    knew, counted to the reserve, never to the budget (WF-RIS-0050); the offer's for a line the
    amendment 1 did not designate (#467). Its payment delay, nought unless said (WF-IND-0100).
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
    quantity: Decimal = Decimal(1)


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
class WorkPackage:
    """A work package of an order item of the work breakdown, and its deliverables."""

    identifier: str
    label: str
    deliverables: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class OrderItem:
    """An order item of the work breakdown of the witness, which a summary bears."""

    identifier: str
    label: str
    work_packages: tuple[WorkPackage, ...] = ()


class N:
    """The numbers of the nodes of the core, said once — the node 5nn, its lineage 6nn.

    Every module names the core by this table, never by its digits, so that it is renumbered in
    one place alone (#376, revue d'EP-02/L24).
    """

    STUDIES = 521
    DETAILED_STUDIES = 522
    DESKS = 523
    DESIGN_REVIEW = 524
    STUDIES_RECEIVED = 525
    DESIGN_FILE = 526
    STUDIES_LINE = 527
    MERGED = 541
    REMINDER = 542
    REMINDER_LINE = 543
    TRANSPORT = 544
    TRANSPORT_LINE = 545
    CONTROL_STATION = 551
    WIRING = 552
    LABOUR = 553
    BLOCKS = 554
    PROVISION = 555
    FACTORY_ACCEPTANCE = 556
    REFERENCE_PROVISION_752 = 557
    INSTALLATION = 561
    MOUNTING = 562
    WIRING_ON_SITE = 563
    TESTS_LINE = 564
    COMMISSIONING = 565
    COMMISSIONING_LINE = 566
    REFERENCE_PROVISION_753 = 567
    SITE_TRIALS = 568
    SITE_TRIALS_LINE = 569


CABINETS = WorkPackage(
    universe(712),
    "Armoires",
    ((universe(713), "Procès-verbal de réception usine des armoires"),),
)
"""The one work package of the witness, which no task bears (WF-PLA-0130), and its deliverable."""

ASSEMBLY = OrderItem(universe(711), "Fourniture et montage des armoires", (CABINETS,))
"""The one order item of the witness, which the lot « Poste de commande » bears (WF-PLA-0130),
and whose total the estimate presents (`estimate_indicators_breakdown`, WF-DEV-0060)."""

WORK_BREAKDOWN = (ASSEMBLY,)
"""The work breakdown of the witness, as its order was entered (WF-PRJ-0020)."""

DEFAULT_BREAKDOWN = (
    OrderItem(universe(714), "Commande", (WorkPackage(universe(715), "Lot unique"),)),
)
"""The work breakdown of a project whose order was not entered: one order item holding one work
package without a deliverable (WF-PRJ-0020). The document names neither: these labels are the
example's."""

STEERING = universe(1000)
CUSTOMER = universe(1001)
TIMELINES = ((STEERING, "Comité de pilotage"), (CUSTOMER, "Revue client"))
"""The named timelines of the witness (WF-PLA-0140): the steering committee follows the studies,
their reception, the factory acceptance and the commissioning; the customer, the two receptions."""

INSCRIBED: dict[int, tuple[str, ...]] = {
    N.STUDIES: (STEERING,),
    N.STUDIES_RECEIVED: (STEERING, CUSTOMER),
    N.FACTORY_ACCEPTANCE: (STEERING, CUSTOMER),
    N.COMMISSIONING: (STEERING,),
}
"""The tasks of the core inscribed to each timeline, by their number (WF-PLA-0060)."""

TRACKED = (N.STUDIES_RECEIVED, N.FACTORY_ACCEPTANCE)
"""The milestones of the core inscribed to the time/time tracking, those ``milestone_tracking``
follows (WF-PLA-0060, WF-IND-0090)."""


STUDIES = Task(
    N.STUDIES,
    "Études",
    children=(
        Task(
            N.DETAILED_STUDIES,
            "Études de détail",
            days=30,
            lines=(
                Line(
                    N.STUDIES_LINE,
                    "Ingénierie de détail",
                    SUBCONTRACTING,
                    unit=Decimal("100000.00"),
                    payment_delay_days=PAYMENT_DELAY,
                ),
            ),
        ),
        Task(
            N.DESKS,
            "Pupitres opérateurs",
            days=40,
            manual=(date(2026, 3, 2), date(2026, 4, 24)),
            progress="started",
        ),
        Task(N.DESIGN_REVIEW, "Revue de conception", days=10, links=(Link(N.DETAILED_STUDIES),)),
        Task(
            N.STUDIES_RECEIVED,
            "Réception des études",
            is_milestone=True,
            links=(Link(N.DESIGN_REVIEW), Link(N.DESKS, START_TO_START, 1, "w")),
            # Nothing completes by itself (WF-RAE-0030): the reception was declared on its day.
            progress="completed",
        ),
        Task(
            N.DESIGN_FILE,
            "Dossier de conception",
            days=5,
            links=(Link(N.DETAILED_STUDIES, lag=-2),),
        ),
    ),
)
"""The studies: the detailed studies, finished before today; the operator desks, in manual
mode, started and past their finish; the design review after them, the reception of the studies
at its end, also a week after the desks started; and the design file, two days before the
detailed studies finish, with float (WF-PLA-0030, WF-PLA-0080, WF-PLA-0100)."""

CONTROL_STATION = Task(
    N.CONTROL_STATION,
    "Poste de commande",
    order_item=ASSEMBLY,
    children=(
        Task(
            N.WIRING,
            "Câblage des armoires",
            days=42,
            links=(Link(N.STUDIES_RECEIVED, lag=1, unit="w"),),
            lines=(
                Line(
                    N.LABOUR,
                    "Raccordement des borniers",
                    ELECTRICAL_ENGINEERING,
                    hours=Decimal("12.5"),
                    role=ENGINEER,
                    subproject=SUBPROJECT_CONTROL,
                ),
                Line(
                    N.BLOCKS,
                    "Borniers",
                    EQUIPMENT,
                    unit=Decimal("1234.56"),
                    subproject=SUBPROJECT_CONTROL,
                    payment_delay_days=PAYMENT_DELAY,
                ),
                Line(
                    N.PROVISION,
                    "Provision — risque de reprise du câblage",
                    PROVISIONS,
                    unit=Decimal("500.00") * RISK_SCALE,
                    budgeted=REFERENCE_PROVISION_751,
                    is_provision=True,
                ),
            ),
        ),
        Task(
            N.MERGED,
            "Risque survenu — Retard de livraison des armoires",
            children=(
                Task(
                    N.REMINDER,
                    "Relance du fournisseur",
                    days=5,
                    links=(Link(N.WIRING, START_TO_START),),
                    lines=(
                        Line(
                            N.REMINDER_LINE,
                            "Frais de relance",
                            EQUIPMENT,
                            unit=Decimal("120.00"),
                            budgeted=Decimal(0),
                        ),
                    ),
                ),
                Task(
                    N.TRANSPORT,
                    "Transport exceptionnel",
                    days=5,
                    links=(Link(N.REMINDER),),
                    lines=(
                        Line(
                            N.TRANSPORT_LINE,
                            "Affrètement",
                            EQUIPMENT,
                            unit=Decimal("80.00"),
                            budgeted=Decimal(0),
                        ),
                    ),
                ),
            ),
        ),
        Task(N.FACTORY_ACCEPTANCE, "Réception usine", is_milestone=True, links=(Link(N.WIRING),)),
    ),
)
"""The lot of the control station: the wiring of the cabinets a week after the reception of the
studies, 12.5 hours at 80.00 — 1,000.00 —, terminal blocks at 1,234.56 and the provision of
500,000 of the risk 751, at the scale of the structure, budgeted at the 250,000 the reference knew;
the subtree merged into the current revision by the occurrence of the risk 752, its lines of 120
and 80 budgeted nothing (WF-RIS-0060); and the factory acceptance at the end of the wiring."""

OFFER_BUDGETS = {N.WIRING_ON_SITE: Decimal("9420.00"), N.COMMISSIONING_LINE: Decimal("5880.00")}
"""The budgets the offer fixed to the lines the amendment 1 did not designate, at the rates of 2025
(``mockhistory.offer``): they keep them, the merge changing the budgets of the lines it designates
alone (WF-REV-0050, #467), their amounts at the one rate of 2026 of their category (WF-DEV-0020)."""

INSTALLATION = Task(
    N.INSTALLATION,
    "Installation sur site",
    children=(
        Task(
            N.MOUNTING,
            "Montage des armoires sur site",
            days=123,
            links=(Link(N.FACTORY_ACCEPTANCE),),
            lines=(
                Line(
                    N.WIRING_ON_SITE,
                    "Câblage sur site",
                    ELECTRICAL_ENGINEERING,
                    hours=Decimal(120),
                    role=ENGINEER,
                    subproject=SUBPROJECT_CONTROL,
                    budgeted=OFFER_BUDGETS[N.WIRING_ON_SITE],
                ),
                Line(
                    N.TESTS_LINE,
                    "Assistance aux essais de câblage",
                    COMMISSIONING,
                    hours=Decimal(40),
                    role=COMMISSIONING_TECHNICIAN,
                    subproject=SUBPROJECT_CONTROL,
                ),
            ),
        ),
        Task(
            N.COMMISSIONING,
            "Mise en service",
            days=10,
            links=(Link(N.MOUNTING),),
            lines=(
                Line(
                    N.COMMISSIONING_LINE,
                    "Mise en service sur site",
                    COMMISSIONING,
                    hours=Decimal(80),
                    role=COMMISSIONING_TECHNICIAN,
                    subproject=SUBPROJECT_CONTROL,
                    budgeted=OFFER_BUDGETS[N.COMMISSIONING_LINE],
                ),
            ),
        ),
    ),
)
"""The installation on site, after the factory acceptance: the cabinets mounted on site from
1 July to 18 December 2026, wired by the electrical engineer and tested with the commissioning
technician, both on the standard week, budgeted as the offer did (#467); and the commissioning,
which follows, into January 2027, its line consumed in 2026, the year it starts (WF-DEV-0040). The
wiring on site given to the cable fitter, on the week of four days, puts the mounting on the days
both its roles work, four of eight hours (WF-PLA-0010): it finishes in 2027, and the
commissioning starts and is consumed there (EP-02/L22)."""

CORE = (STUDIES, CONTROL_STATION, INSTALLATION)
"""The readable core, the first roots of the structure, its rows its first rows (#376)."""

STUDIES_RECEIVED, STUDIES_LINE = N.STUDIES_RECEIVED, N.STUDIES_LINE
WIRING, LABOUR, FACTORY_ACCEPTANCE = N.WIRING, N.LABOUR, N.FACTORY_ACCEPTANCE
"""Short names, from N, of the nodes of the core several readings name."""

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
    ``own_structure`` its own cost structure in the current revision, of an identifier of its
    own, apart from the one the reference bore (``structures``, ``structures_amendments``;
    WF-DAT-0030, #461);
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
    204,
    (
        Review(RISKS_IDENTIFIED.instant, Decimal("0.25"), Decimal("1000.00") * RISK_SCALE),
        Review(RISK_751_REVIEWED.instant, Decimal("0.25"), Decimal("1250.00") * RISK_SCALE),
        Review(STUDIES_STARTED.instant, Decimal("0.4"), Decimal("1250.00") * RISK_SCALE),
    ),
    reference_provision_line=N.PROVISION,
    provision_line=N.PROVISION,
)
DELIVERY_DELAY = Risk(
    752,
    "Retard de livraison des armoires",
    "Le fournisseur des armoires annonce un retard de livraison possible.",
    "Relance hebdomadaire du fournisseur ; transport exceptionnel réservé.",
    205,
    (
        Review(_at(RISKS_IDENTIFIED, 10, 30), Decimal("0.3"), Decimal("200.00")),
        Review(RISK_752_OCCURRED.instant, Decimal("0.3"), Decimal("200.00"), OCCURRED),
    ),
    reference_provision_line=N.REFERENCE_PROVISION_752,
    merged=N.MERGED,
)
AUTOMATION_ENGINEER = Risk(
    753,
    "Indisponibilité de l'automaticien",
    "L'automaticien du client pourrait ne pas être disponible pour la mise en service.",
    None,
    206,
    (
        Review(_at(RISKS_IDENTIFIED, 11), Decimal("0.05"), Decimal("12000.00") * RISK_SCALE),
        Review(
            _at(RISK_751_REVIEWED, 14), Decimal("0.05"), Decimal("12000.00") * RISK_SCALE, DISMISSED
        ),
    ),
    reference_provision_line=N.REFERENCE_PROVISION_753,
)
REGISTER = (REWORK, DELIVERY_DELAY, AUTOMATION_ENGINEER)
"""The register of the witness, in the order of declaration: the rework of the wiring, still
identified, its provision the line 555 of the core; the delay of the cabinets, occurred on
20 February, its own estimate merged into the current revision (WF-RIS-0060) — the subtree 541
of the core —; the unavailability of the automation engineer, dismissed on 2 February. All three
identified on 12 January, before the reference 101 was marked, which bore their provisions: the
lines 555, 557 and 567 of its structure (``mockhistory``). The rework and the unavailability are
at the scale of the structure (``RISK_SCALE``), the delay at the figures of its Vérif."""

# --- The reference, as marked -----------------------------------------------------------------

MERGED, COMMISSIONING_TASK = N.MERGED, N.COMMISSIONING
"""The subtree the occurrence of 752 merged into the current revision, and the commissioning."""

REFERENCE_PROVISIONS = {
    752: (
        WIRING,
        Line(
            N.REFERENCE_PROVISION_752,
            "Provision — retard de livraison des armoires",
            PROVISIONS,
            is_provision=True,
        ),
    ),
    753: (
        COMMISSIONING_TASK,
        Line(
            N.REFERENCE_PROVISION_753,
            "Provision — indisponibilité de l'automaticien",
            PROVISIONS,
            is_provision=True,
        ),
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


def reference(roots: Iterable[Task] | None = None) -> tuple[Task, ...]:
    """Return the reference 101 as marked on 1 February 2026, from the core of today.

    From the structure given, the core by default: the tasks the core does not name are as today,
    nothing of them started.

    Nothing was started — the studies start on 2 March —, the subtree the occurrence of 752
    merged on 20 February is not there yet, and each identified risk bears its line of provision
    at the provision it then had: 751 at 1,000,000 at 25 %, 752 and 753 on the lines the current
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

    return rewritten(CORE if roots is None else roots, change)


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
"""The imports of actual costs of the witness, in their order: the extraction of March, that of
April, a file without a period of which no line was the project's, a re-extraction up to 30 April,
which brings back the five lines already imported, and the extraction of May, from 1 May."""


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
