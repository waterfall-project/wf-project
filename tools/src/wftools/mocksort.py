# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The sort of a grid of the tree, and the examples of ``listNodes`` it orders (EP-02/L42c, #526).

A grid of a tree does not sort: the tasks keep the order of the tree, and the sort is but a sort
of the lines under each task (§3.4, WF-IHM-0060). ``mockcore`` moves the lines of each task among
the places they hold; here is how two lines compare, by a column of the line as ``sort_by`` names
it (``NodeColumn``): a number by its value, a text by its characters and a reference by its label,
both in the order of the code points of Unicode; a line without a value after the others in the
ascending order, before them in the descending one; lines of one value in the order of the plan.

And the two examples it orders, read on the estimate of the control station: by the amount at the
year of reference, ascending, where the milestone of no amount stays last; by the hours,
descending, where the disbursement and the provision, which have none, come first.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, cast, get_args

from wftools import mockcore, mocktext
from wftools.mockwitness import CONTROL_STATION, TODAY

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

LineColumn = Literal[
    "label",
    "cost_category",
    "resource_role",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject",
    "payment_delay_days",
    "consumption_year",
    "base_amount",
    "budgeted_amount",
    "reestimated_amount",
    "inflated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
]
"""The columns of a line of the estimate that ``sort_by`` names (``NodeColumn``)."""

LINE_COLUMNS: tuple[str, ...] = get_args(LineColumn)

TEXTS: frozenset[str] = frozenset({"label"})
"""The columns compared as texts."""

REFERENCES: dict[str, str] = {
    "cost_category": "cost_category_label",
    "resource_role": "resource_role_label",
    "subproject": "subproject_label",
}
"""The columns that name an object of the reference data, compared by the label resolved."""

type Key = tuple[bool, Decimal | str]


@dataclass(frozen=True, slots=True)
class LineSort:
    """A sort of a grid of the tree: the lines under each task by a column of theirs."""

    column: LineColumn
    descending: bool = False

    def key(self, line: JsonObject) -> Key:
        """Return what a line is compared by: without a value, after any value once ascending."""
        value = line[REFERENCES.get(self.column, self.column)]
        if value is None:
            return (True, "")
        if self.column in TEXTS or self.column in REFERENCES:
            return (False, cast("str", value))
        return (False, Decimal(str(value)))

    def ordered(self, lines: list[mockcore.Row]) -> list[mockcore.Row]:
        """Return lines of one task in the order of the sort, those of one value in plan order.

        The sort is stable, the descending one too: lines of one value, and the lines without a
        value, keep the order they come in, the order of the plan.
        """

        def key(row: mockcore.Row) -> Key:
            return self.key(cast("JsonObject", row.node[mockcore.ESTIMATE_LINE]))

        return sorted(lines, key=key, reverse=self.descending)


def examples(rows: list[mockcore.Row]) -> dict[str, JsonObject]:
    """Return the examples of the estimate of the control station sorted, by file name."""
    day = mocktext.day(TODAY.date())
    amount = mocktext.amount
    return {
        "nodes_estimate_sorted.json": mocktext.example(
            f"Le devis du lot « Poste de commande » trié par montant à l'année de référence, "
            f"croissant (subtree_of, sort_by=base_amount, sort_order=asc), le {day} : sous le "
            f"câblage des armoires, la provision de {amount(Decimal(500))}, la main-d'œuvre de "
            f"{amount(Decimal(1_000))}, puis le débours de {amount(Decimal('1234.56'))}. Les "
            f"tâches gardent l'ordre de l'arbre — le jalon de réception usine, de montant nul, "
            f"reste le dernier —, chaque nœud son numéro de ligne, et les totaux sont ceux du "
            f"devis : une grille arborescente ne trie que les lignes de devis sous chaque tâche "
            f"(WF-IHM-0060).",
            mockcore.subtree(rows, CONTROL_STATION.number, sort=LineSort("base_amount")),
        ),
        "nodes_estimate_hours.json": mocktext.example(
            f"Le devis du lot « Poste de commande » trié par heures, décroissant (subtree_of, "
            f"sort_by=hours, sort_order=desc), le {day} : sous le câblage des armoires, le débours "
            f"de {amount(Decimal('1234.56'))} et la provision de {amount(Decimal(500))}, qui "
            f"n'ont pas d'heures, d'abord, dans l'ordre du plan — une ligne sans valeur vient "
            f"après les autres dans l'ordre croissant, avant dans le décroissant —, puis la "
            f"main-d'œuvre de 12,5 h. Les tâches gardent l'ordre de l'arbre, et les lignes sans "
            f"heures des autres tâches leur place (WF-IHM-0060).",
            mockcore.subtree(rows, CONTROL_STATION.number, sort=LineSort("hours", descending=True)),
        ),
    }
