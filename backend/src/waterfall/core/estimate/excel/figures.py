# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the workbook « Devis » shows without a recalculation: the value of each formula (US-3640).

A formula written alone is cached by XlsxWriter as 0, and a spreadsheet that does not recalculate
— LibreOffice for a file of « Excel », Excel in protected mode, a preview — shows that 0 (#4317).
The writer therefore writes each formula with the value it gives, which this module computes the
way the formula does: in floating point, line by line, the lookups of « Paramètres » by the text of
the entry, an empty row giving the empty text, never 0. Pure: no workbook, no database.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from waterfall.core.estimate.excel.model import DISBURSEMENT, LABOUR, PROVISION

if TYPE_CHECKING:
    from collections.abc import Iterable

    from waterfall.core.estimate.excel.model import Line, Role

# The columns of a row of the reference table of « Paramètres » that the formulas read.
SERVICE, NATURE, KIND, CODE, RATE = 4, 5, 6, 7, 8
# What a lookup gives for an entry the reference does not hold.
UNKNOWN = "?"
# The calculated columns of a tab of lines that a lookup or a calculation fills.
LOOKUPS = ("Nature", "Code comptable", "Service", "Taux horaire", "Type")
CALCULATED = (
    "Description de la tâche",
    *LOOKUPS,
    "Heures totales",
    "Main-d’œuvre",
    "Débours",
    "Montant",
)
# A prepared row: nothing typed, so every formula gives the empty text.
EMPTY: dict[str, Any] = dict.fromkeys(CALCULATED, "")


def role_codes(roles: Iterable[Role]) -> tuple[str, ...]:
    """Give the accounting codes the roles carry, each once, in the order of the codes (#4319).

    The hours of a line come from a line of labour, hence from a role: a column of hours for a code
    that no role carries could never hold anything.
    """
    return tuple(sorted({role.category for role in roles}))


def reference_index(rows: Iterable[list[Any]]) -> dict[str, list[Any]]:
    """Index the rows of the reference by their entry: ``MATCH`` finds the first of them."""
    found: dict[str, list[Any]] = {}
    for row in rows:
        found.setdefault(row[0], row)
    return found


def looked_up(reference: dict[str, list[Any]], entry: str) -> dict[str, Any]:
    """Give the five lookups of « Paramètres » for an entry, as the formulas read them."""
    row = reference.get(entry)
    if row is None:
        return dict.fromkeys(LOOKUPS, UNKNOWN)
    rate = row[RATE]
    return {
        "Nature": row[NATURE],
        "Code comptable": row[CODE],
        "Service": row[SERVICE] or "",
        # An empty cell read through INDEX is 0.
        "Taux horaire": 0.0 if rate is None else float(rate),
        "Type": row[KIND],
    }


def _line_figures(found: dict[str, Any], description: str, line: Line) -> dict[str, Any]:
    """Give the cells a line of the estimate calculates, from what the formulas read."""
    quantity = float(line.quantity)
    hours = float(line.hours or 0)
    unit = float(line.disbursement or 0)
    labour = found["Type"] == LABOUR
    non_labour = found["Type"] in (DISBURSEMENT, PROVISION)
    wages = quantity * hours * found["Taux horaire"] if labour else 0.0
    disbursement = quantity * unit if non_labour else 0.0
    return {
        "Description de la tâche": description,
        **found,
        "Heures totales": quantity * hours if labour else 0.0,
        "Main-d’œuvre": wages,
        "Débours": disbursement,
        "Montant": wages + disbursement,
    }


@dataclass(frozen=True)
class TabFigures:
    """The calculated cells of the lines exported of a tab, and the amount Waterfall computed."""

    lines: tuple[dict[str, Any], ...]
    waterfall: float

    def total(self, header: str) -> float:
        """Give the total of a column, as the row of totals of the table sums it."""
        if header == "Montant Waterfall":
            return self.waterfall
        return sum(float(line[header]) for line in self.lines)

    def hours_of(self, code: str) -> float:
        """Give the hours of the lines of an accounting code (``SUMIFS``)."""
        return sum(
            float(line["Heures totales"]) for line in self.lines if line["Code comptable"] == code
        )

    def amount_of(self, nature: str) -> float:
        """Give the amount of the lines of a nature (``SUMIFS``)."""
        return sum(float(line["Montant"]) for line in self.lines if line["Nature"] == nature)


def tab_figures(
    reference: dict[str, list[Any]],
    descriptions: dict[str, str],
    rows: Iterable[tuple[str, str, Line]],
) -> TabFigures:
    """Give the figures of a tab from its lines, each with its task and its entry in the list."""
    lines: list[dict[str, Any]] = []
    waterfall = 0.0
    for task_entry, entry, line in rows:
        found = looked_up(reference, entry)
        lines.append(_line_figures(found, descriptions.get(task_entry, ""), line))
        waterfall += float(line.amount or 0)
    return TabFigures(tuple(lines), waterfall)
