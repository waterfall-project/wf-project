# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The risks of the witness and the reference 101 as marked, which bore their provisions.

The register of the witness (``REGISTER``), its three risks and their reviews, and the reference
revision the current one is compared with: the core of ``wftools.mockwitness`` as it was on
1 February 2026, each identified risk bearing its line of provision at the provision it then had
(WF-RIS-0010, WF-RIS-0050, WF-RAE-0040).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from wftools.mockwitness import (
    AMENDMENT_MERGED,
    CORE,
    PROVISIONS,
    RISK_751_REVIEWED,
    RISK_752_OCCURRED,
    RISK_SCALE,
    RISKS_IDENTIFIED,
    STUDIES_STARTED,
    Event,
    Line,
    N,
    Task,
    rewritten,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

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
    ``merged`` the task of the core its occurrence merged its own estimate under (WF-RIS-0060);
    ``provision_category`` and ``provision_subproject`` the category of provision for risks and
    the subproject it designated for its provision, which its line of provision bears while it is
    identified — the one category of provision of the universe, and no subproject (WF-RIS-0010).
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
    provision_category: str = PROVISIONS
    provision_subproject: str | None = None

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
        N.CONTROL_STATION,
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
