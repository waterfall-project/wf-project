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
year of reference, descending, which reverses the lines under the wiring — the provision of 751 at
the scale of the structure first (EP-14/L45b) —; by the hours, descending, where the disbursement
and the provision, which have none, come first. And one it filters, by the two bounds of a column
of a line (``<column>_min``, ``<column>_max``, US-0701/L3, F-06).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, cast, get_args

from wftools import mockcore, mocktext
from wftools.mockids import universe
from wftools.mockwitness import CONTROL_STATION, TODAY, N

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


def _wiring(answer: JsonObject) -> list[JsonObject]:
    """Return the lines under the wiring of the cabinets, in the order read."""
    items = cast("list[JsonObject]", answer["items"])
    wiring = mockcore.lineage(N.WIRING)
    [parent] = [item["node_id"] for item in items if item["lineage_id"] == wiring]
    return [
        cast("JsonObject", item[mockcore.ESTIMATE_LINE])
        for item in items
        if item["kind"] == mockcore.ESTIMATE_LINE and item["parent_id"] == parent
    ]


def _said(line: JsonObject) -> str:
    """Return a line of the estimate as a summary names it: its label, then its amount."""
    return f"« {line['label']} » ({mocktext.amount(Decimal(cast('str', line['base_amount'])))})"


BOUNDS = (Decimal(1000), Decimal(10_000))
"""The bounds of the re-estimated amount the filtered estimate retains, both included."""


def bounded(rows: list[mockcore.Row]) -> JsonObject:
    """Return the estimate of the control station filtered by the bounds of a column of a line.

    ``subtree_of``, ``reestimated_amount_min`` and ``reestimated_amount_max``: the lines of the
    subtree whose re-estimated amount lies within the bounds, both included, and their tasks for
    the readability of the tree (README of the contract, WF-IHM-0060, WF-IHM-0130).
    """
    below = {CONTROL_STATION.number}
    for row in rows:
        if row.parent in below:
            below.add(row.number)
    low, high = BOUNDS
    return mockcore.filtered(
        rows,
        lambda row: (
            row.kind == mockcore.ESTIMATE_LINE
            and row.number in below
            and low <= row.amounts.reestimated <= high
        ),
    )


INVERTED = (date(2026, 5, 1), date(2026, 4, 1))
"""The period of the start of the tasks asked inverted: its end before its start."""


def period_inverted() -> JsonObject:
    """Return what listNodes answers to a period of the start whose end precedes its start.

    The rule of every period of the contract (README): 422, the end of the column named by
    VALUE_OUT_OF_RANGE, ``params.minimum`` the start given.
    """
    start, end = INVERTED
    if end >= start:
        message = "the period asked is not inverted"
        raise ValueError(message)
    return {
        "code": "VALIDATION_FAILED",
        "status": 422,
        "fields": [
            {
                "pointer": "/query/start_to",
                "code": "VALUE_OUT_OF_RANGE",
                "params": {"minimum": start.isoformat()},
            }
        ],
        "correlation_id": universe(1075),
    }


def examples(rows: list[mockcore.Row]) -> dict[str, JsonObject]:
    """Return the examples of the estimate of the control station sorted or filtered, by file name.

    What each says of the order of the lines under the wiring is read from its answer.
    """
    filtered = bounded(rows)
    kept = [
        f"« {cast('JsonObject', item[mockcore.ESTIMATE_LINE])['label']} »"
        for item in cast("list[JsonObject]", filtered["items"])
        if item["kind"] == mockcore.ESTIMATE_LINE
    ]
    total = cast("JsonObject", filtered["totals"])["reestimated_amount"]
    day = mocktext.day(TODAY.date())
    amount = mocktext.amount
    [provision] = [row.amounts.base for row in rows if row.number == N.PROVISION]
    by_amount = mockcore.subtree(
        rows, CONTROL_STATION.number, sort=LineSort("base_amount", descending=True)
    )
    by_hours = mockcore.subtree(
        rows, CONTROL_STATION.number, sort=LineSort("hours", descending=True)
    )
    *first, last = map(_said, _wiring(by_amount))
    return {
        "nodes_estimate_sorted.json": mocktext.example(
            f"Le devis du lot « Poste de commande » trié par montant à l'année de référence, "
            f"décroissant (subtree_of, sort_by=base_amount, sort_order=desc), le {day} : sous le "
            f"câblage des armoires, {', '.join(first)}, puis {last}. Les tâches gardent l'ordre "
            f"de l'arbre, chaque nœud son numéro de ligne, et les totaux sont ceux du devis : une "
            f"grille arborescente ne trie que les lignes de devis sous chaque tâche (WF-IHM-0060).",
            by_amount,
        ),
        "nodes_estimate_hours.json": mocktext.example(
            f"Le devis du lot « Poste de commande » trié par heures, décroissant (subtree_of, "
            f"sort_by=hours, sort_order=desc), le {day} : sous le câblage des armoires, le débours "
            f"de {amount(Decimal('1234.56'))} et la provision de {amount(provision)}, qui "
            f"n'ont pas d'heures, d'abord, dans l'ordre du plan — une ligne sans valeur vient "
            f"après les autres dans l'ordre croissant, avant dans le décroissant —, puis la "
            f"main-d'œuvre de 12,5 h. Les tâches gardent l'ordre de l'arbre, et les lignes sans "
            f"heures des autres tâches leur place (WF-IHM-0060).",
            by_hours,
        ),
        "nodes_estimate_filtered.json": mocktext.example(
            f"Le devis du lot « Poste de commande » filtré par montant réestimé, de "
            f"{amount(BOUNDS[0])} à {amount(BOUNDS[1])}, bornes comprises (subtree_of, "
            f"reestimated_amount_min, reestimated_amount_max), le {day} : les seules lignes "
            f"retenues, {mocktext.listed(kept)}, et leurs "
            f"tâches, rendues pour la lisibilité de l'arbre et absentes des totaux ; ni la "
            f"provision, au-dessus de la borne haute, ni les frais du risque survenu, au-dessous "
            f"de la borne basse. Les totaux sont ceux des lignes retenues, "
            f"{amount(Decimal(str(total)))} réestimés (WF-IHM-0060, WF-IHM-0130).",
            filtered,
        ),
        "nodes_period_inverted.json": mocktext.example(
            f"Les tâches de la structure demandées le {day} par la période de leur début, du "
            f"{mocktext.day(INVERTED[0])} au {mocktext.day(INVERTED[1])} (start_from, start_to) : "
            f"la fin de la période précède son début, et le paramètre start_to est refusé, "
            f"désigné par /query/start_to, le début nommé (README du contrat, WF-IHM-0130).",
            period_inverted(),
        ),
    }
