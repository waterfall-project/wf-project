# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The identifiers of the universe the examples of the contract describe, by family (#287, C16).

Each kind of object has its family, on a range of its own: those the examples write by hand, in
decimal digits or for a few in hexadecimal ones, and those the generators draw. An identifier names
one kind of object (``tests/test_mockwitness.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

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


(
    NODES,
    LINEAGES,
    PROJECTS,
    CATEGORIES,
    RISKS,
    MILESTONES,
    AUDIT_EVENTS,
    CORRELATIONS,
    COST_LINES,
    AMENDMENT_NODES,
) = range(1, 11)
"""The generated families: the nodes of the structure of a thousand tasks and their lineages; the
projects, rate categories, risks and milestone lineages of the portfolio (EP-02/L26); the journal of
audit, its inscriptions and the correlations of their requests (``mockaudit``, EP-02/L42); the
lines of actual cost of the tasks drawn about the core (``mockcosts``, EP-14/L45a); and the nodes
the amendment 2 copies of those drawn (``mockamendment``, #421)."""

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
    Family("lots, postes et livrables du lotissement", 710, 749),
    Family("risques", 750, 799),
    Family("sous-projets", 800, 899),
    Family("sauvegardes", 900, 919),
    Family("tâches de fond", 920, 959),
    Family("corrélations", 960, 989),
    Family("collages", 990, 999),
    Family("chronologies", 1000, 1009),
    Family("corrélations, suite", 1010, 1199),
    Family("nœuds de l'avenant 2, celui du nœud 5nn de la principale en 12nn", 1200, 1299),
    Family("corrélations, seconde suite", 1300, 1599),
    Family("imports et téléversements", 0xA00, 0xAFF, hexadecimal=True),
    Family("lignes de coût réel", 0xC00, 0xC0F, hexadecimal=True),
    Family("imports de coûts réels", 0xC10, 0xCFF, hexadecimal=True),
    Family("nœuds engendrés", 1, _GENERATED, NODES),
    Family("lignées engendrées", 1, _GENERATED, LINEAGES),
    Family("projets du portefeuille", 1, _GENERATED, PROJECTS),
    Family("catégories de la grille des taux", 0, _GENERATED, CATEGORIES),
    Family("risques du portefeuille", 1, _GENERATED, RISKS),
    Family("jalons du portefeuille", 1, _GENERATED, MILESTONES),
    Family("inscriptions du journal d'audit", 1, _GENERATED, AUDIT_EVENTS),
    Family("corrélations engendrées", 1, _GENERATED, CORRELATIONS),
    Family("lignes de coût réel engendrées", 1, _GENERATED, COST_LINES),
    Family("nœuds engendrés de l'avenant 2", 1, _GENERATED, AMENDMENT_NODES),
)
"""Every family of identifier, on disjoint ranges: an identifier names one kind of object.

Every example keeps to it (#287, C16; DECISIONS, EP-02/L25 and L27). The lot 711, « Lot 1 », is
the one lot of the witness, at the first level of its work breakdown, which the summary « Poste de
commande » bears (WF-PLA-0130); its post 712, « Poste 1.1 », is borne by no task: the refusal to
attach it outside the subtree of the task of its lot speaks of it
(`task_attach_outside_work_package`), and the work breakdown names it, with its one deliverable
713 (`work_breakdown`, WF-PRJ-0020, C-350). The lot 714 and its post 715 make the work breakdown
of a project whose order was not entered (`work_breakdown_default`). The correlations
written by hand go on past the chronologies, their first range being full (EP-02/L42d), then past
the nodes of the amendment 2, the second being full in its turn (#1228). The nodes
of the amendment 2 have identifiers of their own, apart from those of the main structure whose
lineages they share, so that one identifier at one version names one content (#421, US-0500/L1)."""


def hex_identifier(number: int) -> str:
    """Return an identifier written by hand in hexadecimal digits: 01926f3a-…-000000000c01."""
    return f"{PREFIX}{number:012x}"
