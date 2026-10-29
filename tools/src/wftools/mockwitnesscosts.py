# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The actual costs of the witness: the imports of its journal and the lines they brought.

What the files of the ERP said, as the journal of imports keeps it (WF-CRE-0010, WF-CRE-0020,
WF-CRE-0030, WF-CRE-0050); the events of the imports are those of the chronology of
``wftools.mockwitness``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from wftools.mockwitness import COST_IMPORTS, Event, fixture


@dataclass(frozen=True, slots=True)
class CostImport:
    """An import of actual costs, as its journal says it (WF-CRE-0050).

    Its event, the instant it was applied; the import of the exchanges that applied it, by its
    number, opened and analysed a few minutes before; the period it extracted, each bound
    possibly missing; and the lines of other projects it read, rejected and signalled to its
    report (WF-CRE-0020), which the journal counts among the lines rejected (WF-CRE-0050).
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
which brings back the six lines already imported, and the extraction of May, from 1 May."""


@dataclass(frozen=True, slots=True)
class CostLine:
    """A line of actual cost of the witness: what the file of the ERP says of it (WF-CRE-0010).

    Its number, 0xc0n; its document, the number of its item in the document — none when the
    extraction gives none —, the two identifying the line in its project (D-4, EP-16/US-0630), its
    date of document, its signed amount; the code of subproject its element
    of the work breakdown structure carries, if it has a subproject part, imputed to the
    subproject of that code if the project has one, to the project alone otherwise — as is a line
    without a subproject part (WF-CRE-0020); the columns kept of the file;
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
        "SP-CAB",
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
        "SP-CAB",
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
        "SP-AUT",
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
        "SP-CAB",
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
        "SP-REC",
        "Traiteur Lumière",
        "Réception du client sur site",
        (MARCH, APRIL_AGAIN),
        (datetime(2026, 4, 6, 9, 15, tzinfo=UTC), "Réception du client, non budgétée"),
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
        "SP-CMD",
        "Automatismes Durand",
        "Écrans du poste de commande",
        (MAY,),
    ),
)
"""The lines of actual cost of the witness today: the purchases of cables, a credit note on them,
which bears no item, and the safety controller, under codes of subproject the project does not
have, imputed to it alone — the invoice of the controller spread over two elements of the work
breakdown structure, in two items of the same document, its wiring under the code of the cables,
gives two lines (WF-INTF-0140, D-4) —;
the reception of the customer, excluded from the tracked scope three days after its import; the
invoice of the detailed studies, 100,000 of subcontracting dated the day they finished, without a
subproject part, as their line 527 has none — its payment delay of thirty days shifts the
disbursement, not the date of the document (decision of the author, review of EP-02/L25) —; and
the screens of the control station, imputed to its subproject."""

PASSTHROUGH: tuple[str, ...] = tuple(fixture("actual_cost_mapping")["kept_columns"])
"""The columns of the file the imports keep, read from the mapping of the extraction the witness
declares, in its order (``actual_cost_mapping``, WF-REF-0190, WF-CRE-0010). The element of the
work breakdown structure is a column read: it is not kept as well, its label would double its own
(EP-16)."""
