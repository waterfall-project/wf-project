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
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from wftools import REPOSITORY
from wftools.mockcalendar import FINISH_TO_START, START_TO_START, Calendar

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
    """A dated event of the life of the witness project, in universal time."""

    on: date
    what: str


INSTALLED = Event(date(2025, 9, 1), "Installation, référentiel et comptes")
CREATED = Event(date(2025, 10, 6), "PRJ-001 créé, à l'état Créé")
OFFER_OPENED = Event(date(2025, 11, 3), "Ouverture de l'offre 100, passage en Chiffrage")
OFFER_MARKED = Event(date(2025, 12, 15), "Offre v1.0 marquée")
RISKS_IDENTIFIED = Event(date(2026, 1, 12), "Risques 751, 752 et 753 identifiés")
ORDER_RECEIVED = Event(
    date(2026, 1, 15), "Commande reçue ; l'offre 100 désignée référence, passage En cours"
)
AMENDMENT_MERGED = Event(
    date(2026, 2, 1), "Avenant 1 fusionné ; la révision 101 « Référence » marquée, référence"
)
RISK_751_REVIEWED = Event(date(2026, 2, 2), "Réexamen de 751 : gravité portée à 1 250")
RISK_752_OCCURRED = Event(
    date(2026, 2, 20),
    "Survenance de 752 : son devis propre fusionné dans la révision en cours, la référence 101 "
    "inchangée",
)
STUDIES_STARTED = Event(
    date(2026, 3, 2), "Ouverture de la révision courante 102 ; 751 à 40 % ; début des études"
)
COST_IMPORTS = tuple(
    Event(day, "Import de coûts réels")
    for day in (
        date(2026, 4, 3),
        date(2026, 5, 4),
        date(2026, 5, 6),
        date(2026, 5, 11),
        date(2026, 6, 3),
    )
)
PLANNING_IMPORT_ABANDONED = Event(date(2026, 5, 20), "Import de planning, abandonné")
ESTIMATE_IMPORT_ANALYSED = Event(
    date(2026, 6, 1), "Import du devis analysé, en attente de confirmation"
)
APRIL_EXTRACTION_REPLAYED = Event(date(2026, 6, 2), "Extraction d'avril rejouée et analysée")

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
        key=lambda event: event.on,
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


NODES, LINEAGES, PROJECTS, CATEGORIES, RISKS = 1, 2, 3, 4, 5
"""The generated families: the nodes of the structure of a thousand tasks and their lineages; the
projects of the portfolio, the categories of the grid of rates and the risks of
the portfolio."""

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
    Family("postes du lotissement", 710, 749),
    Family("risques", 750, 799),
    Family("sous-projets", 800, 899),
    Family("sauvegardes", 900, 919),
    Family("tâches de fond", 920, 959),
    Family("collages et corrélations", 960, 999),
    Family("imports et téléversements", 0xA00, 0xAFF, hexadecimal=True),
    Family("lignes de coût réel", 0xC00, 0xC0F, hexadecimal=True),
    Family("imports de coûts réels", 0xC10, 0xCFF, hexadecimal=True),
    Family("nœuds engendrés", 1, _GENERATED, NODES),
    Family("lignées engendrées", 1, _GENERATED, LINEAGES),
    Family("projets du portefeuille", 1, _GENERATED, PROJECTS),
    Family("catégories de la grille des taux", 0, _GENERATED, CATEGORIES),
    Family("risques du portefeuille", 1, _GENERATED, RISKS),
)
"""Every family of identifier, on disjoint ranges: an identifier names one kind of object.

The examples written by hand do not all keep to it yet (#287, C16), until the examples that
carry them are moved: the order item 701 is on the range of the access roles; the background
tasks 901 to 905, the pastes 911 and 912 and the correlation 913 on that of the backups; the
correlations 921 to 927 on that of the background tasks.
"""

# --- The roles, their calendars ---------------------------------------------------------------

ENGINEER = universe(451)
COMMISSIONING_TECHNICIAN = universe(452)
CABLE_FITTER = universe(454)
"""The active roles of the witness (``resource_roles``): the electrical engineer and the
commissioning technician, whom its lines employ, on the standard week; and the cable fitter, on
the week of four days of ten hours, whom no line employs yet — a write of the estimate will give
him one (EP-02/L22)."""

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

SUBPROJECT_CONTROL = universe(801)
SUBCONTRACTING = universe(401)
ELECTRICAL_ENGINEERING = universe(402)
EQUIPMENT = universe(403)
PROVISIONS = universe(404)


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
    to the reference budget (WF-RIS-0050).
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


@dataclass(frozen=True, slots=True)
class Task:
    """A task of the core: its node is its number, 5nn, its lineage 6nn.

    Its duration in days of work of eight hours, as its links' lags are in their units, both
    converted into hours by ``mockcalendar.to_hours`` (WF-PLA-0160); its lines and its
    subordinates. The progress of a task in automatic mode is read from its dates at TODAY; a
    task in manual mode carries the dates its user entered, and the progress its user declared.
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


STUDIES = Task(
    521,
    "Études",
    children=(
        Task(
            522,
            "Études de détail",
            days=30,
            lines=(Line(527, "Ingénierie de détail", SUBCONTRACTING, unit=Decimal("100000.00")),),
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

CORE = (STUDIES, CONTROL_STATION)
"""The readable core, to be the first roots of the structure, its rows its first rows (#376)."""
