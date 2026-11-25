# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs of the witness: the imports of its journal and the lines they brought.

What the files of the ERP said, as the journal of imports keeps it (WF-CRE-0010, WF-CRE-0020,
WF-CRE-0030, WF-CRE-0050); the events of the imports are those of the chronology of
``wftools.mockwitness``.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from wftools.mockwitness import COST_IMPORTS, RECEPTION_EXCLUDED, Event, fixture


@dataclass(frozen=True, slots=True)
class CostImport:
    """An import of actual costs, as its journal says it (WF-CRE-0050).

    Its event, the instant it was applied; the import of the exchanges that applied it, by its
    number, opened and analysed a few minutes before; the period it extracted, each bound
    possibly missing; and the lines of other projects it read, rejected and signalled to its
    report (WF-CRE-0020), which the journal counts among the lines rejected (WF-CRE-0050); and
    the lines it brought back as they already were, which an import leaves no trace of in the
    audit and the journal counts apart (WF-CRE-0050).
    """

    number: int
    event: Event
    exchange: int
    period: tuple[date | None, date | None]
    rejected: int = 0
    unchanged: int = 0


MARCH, APRIL, UNDATED, APRIL_AGAIN, MAY = (
    CostImport(0xC11, COST_IMPORTS[0], 0xA06, (date(2026, 3, 1), date(2026, 3, 31))),
    CostImport(0xC12, COST_IMPORTS[1], 0xA07, (date(2026, 4, 1), date(2026, 4, 30)), 1),
    CostImport(0xC13, COST_IMPORTS[2], 0xA08, (None, None), 37, 6),
    CostImport(0xC14, COST_IMPORTS[3], 0xA09, (None, date(2026, 4, 30)), 12_345),
    CostImport(0xC15, COST_IMPORTS[4], 0xA14, (date(2026, 5, 1), None)),
)
JOURNAL = (MARCH, APRIL, UNDATED, APRIL_AGAIN, MAY)
"""The imports of actual costs of the witness, in their order: the extraction of March, that of
April, a file without a period which brings back the six lines already imported as they were and
no line of the project besides, a re-extraction up to 30 April, which brings back the same six
lines, updated, and the extraction of May, from 1 May."""


@dataclass(frozen=True, slots=True)
class CostLine:
    """A line of actual cost of the witness: what the file of the ERP says of it (WF-CRE-0010).

    Its number, 0xc0n; its document, the number of its item in the document — none when the
    extraction gives none —, the two identifying the line in its project (D-4, EP-16/US-0630), its
    date of document, its signed amount; the code of the subproject its element of the work
    breakdown structure is, compared whole, which it is imputed to — none for a line whose element
    is the code of the project, imputed to the project alone (WF-CRE-0020; #3966); the columns
    kept of the file;
    the imports that brought it, the first creating it, the others updating it (WF-CRE-0010); and
    its exclusion from the tracked scope, when and why, kept by the imports after it
    (WF-CRE-0030).
    """

    number: int
    document: str
    item: str | None
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
        "10",
        date(2026, 4, 21),
        Decimal("1800.00"),
        None,
        "Câbles du Rhône",
        "Câbles de commande du pupitre",
        (APRIL, APRIL_AGAIN),
    ),
    CostLine(
        0xC02,
        "AV-2026-0388",
        None,
        date(2026, 4, 8),
        Decimal("-200.00"),
        None,
        "Câbles du Rhône",
        "Avoir sur livraison incomplète",
        (APRIL, APRIL_AGAIN),
    ),
    CostLine(
        0xC03,
        "FA-2026-0301",
        "10",
        date(2026, 3, 27),
        Decimal("1100.00"),
        None,
        "Automatismes Durand",
        "Automate de sécurité",
        (MARCH, APRIL_AGAIN),
    ),
    CostLine(
        0xC07,
        "FA-2026-0301",
        "20",
        date(2026, 3, 27),
        Decimal("300.00"),
        None,
        "Automatismes Durand",
        "Câblage de l'automate de sécurité",
        (MARCH, APRIL_AGAIN),
    ),
    CostLine(
        0xC04,
        "FA-2026-0295",
        "10",
        date(2026, 3, 20),
        Decimal("650.00"),
        None,
        "Traiteur Lumière",
        "Réception du client sur site",
        (MARCH, APRIL_AGAIN),
        (RECEPTION_EXCLUDED.instant, "Réception du client, non budgétée"),
    ),
    CostLine(
        0xC06,
        "FA-2026-0409",
        "10",
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
        "10",
        date(2026, 5, 18),
        Decimal("2400.00"),
        "PRJ-001/SP-CMD",
        "Automatismes Durand",
        "Écrans du poste de commande",
        (MAY,),
    ),
)
"""The lines of actual cost of the witness today: the purchases of cables, a credit note on them,
which bears no item, and the safety controller, under the element of the project, imputed to it
alone — the invoice of the controller, in two items of the same document, its wiring apart,
gives two lines (WF-INTF-0140, D-4) —;
the reception of the customer, excluded from the tracked scope three days after its import; the
invoice of the detailed studies, 100,000 of subcontracting dated the day they finished, under the
element of the project, as their line 527 has no subproject — its payment delay of thirty days
shifts the disbursement, not the date of the document (decision of the author, review of
EP-02/L25) —; and the screens of the control station, imputed to its subproject, whose code is
their element. Since #3966 an element is compared whole, and a line no subproject bears the code
of is rejected at its import: none waits for its subproject (US-3270/L2)."""

PASSTHROUGH: tuple[str, ...] = tuple(fixture("actual_cost_mapping")["kept_columns"])
"""The columns of the file the imports keep, read from the mapping of the extraction the witness
declares, in its order (``actual_cost_mapping``, WF-REF-0190, WF-CRE-0010). The element of the
work breakdown structure is a column read: it is not kept as well, its label would double its own
(EP-16)."""
