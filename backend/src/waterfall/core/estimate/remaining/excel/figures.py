# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the workbook « Reste à engager » shows without a recalculation (US-3640, #4317).

The writer writes each formula with the value it gives, so that a spreadsheet that does not
recalculate — LibreOffice for a file of « Excel », Excel in protected mode, a preview — does not
show the 0 that XlsxWriter caches for a formula alone. The values are computed the way the formulas
compute them (``layout.line_formulas``): in floating point, the lookups of « Paramètres » by the
text of the entry, an empty row giving the empty text. Pure: no workbook, no database.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from waterfall.core.estimate.excel.figures import looked_up
from waterfall.core.estimate.excel.model import DISBURSEMENT, LABOUR
from waterfall.core.estimate.remaining.excel.layout import STATES, TOTALS
from waterfall.core.estimate.remaining.excel.model import remaining_days

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from decimal import Decimal

    from waterfall.core.estimate.remaining.excel.model import (
        RemainingLine,
        RemainingTab,
        RemainingTask,
    )

# A prepared row: nothing typed, so every formula gives the empty text — but the coefficient,
# which reads the task of the row and gives 1 when it finds none.
EMPTY: dict[str, Any] = {
    "Description de la tâche": "",
    "État": "",
    "Nature": "",
    "Code comptable": "",
    "Service": "",
    "Taux horaire": "",
    "Type": "",
    "Coefficient": 1,
    "Main-d’œuvre": "",
    "Débours": "",
    "Reste à engager": "",
}
# What a task gives to the lookups of a line: its state, its coefficient, its description.
TaskFacts = tuple[str, float, str]


def task_facts(
    tasks: Iterable[RemainingTask], entry: Callable[[RemainingTask], str]
) -> dict[str, TaskFacts]:
    """Give the facts of each task by its entry in the list: ``MATCH`` finds the first of them."""
    found: dict[str, TaskFacts] = {}
    for task in tasks:
        found.setdefault(entry(task), (STATES[task.state], float(task.inflation), task.description))
    return found


@dataclass(frozen=True)
class TabFigures:
    """The calculated cells of the lines exported of a tab, and the totals of its columns."""

    lines: tuple[dict[str, Any], ...]
    totals: dict[str, float]

    def remaining_of(self, nature: str) -> float:
        """Give the remaining of the lines of a nature (``SUMIFS``)."""
        return sum(
            float(line["Reste à engager"]) for line in self.lines if line["Nature"] == nature
        )

    def days_of(self, code: str) -> float:
        """Give the days of the lines of an accounting code (``SUMIFS``)."""
        return sum(
            float(line["Jours restants"]) for line in self.lines if line["Code comptable"] == code
        )


@dataclass(frozen=True)
class Indicators:
    """The amounts and the indicators of the header of a tab, as its formulas give them."""

    values: dict[str, float | str]


def indicators(tab: RemainingTab, figures: TabFigures) -> Indicators:
    """Give the header of a tab: the remaining of its table, then the indicators drawn from it."""
    table = figures.totals["Reste à engager"]
    provisions = float(tab.provisions)
    actual = float(tab.actual_costs)
    remaining = table + provisions
    projection = actual + remaining
    return Indicators(
        {
            "budget": float(tab.budget),
            "actual": actual,
            "table": table,
            "provisions": provisions,
            "remaining": remaining,
            "projection": projection,
            "gap": projection - float(tab.budget),
            "progress": "non calculable" if projection == 0 else actual / projection,
        }
    )


def _line_figures(
    found: dict[str, Any],
    facts: TaskFacts | None,
    line: RemainingLine,
    days: float,
    hours_per_day: float,
) -> dict[str, Any]:
    """Give the cells a line of the review calculates, from what the formulas read."""
    state, coefficient, description = facts if facts is not None else ("", 1.0, "")
    wages = (
        days * hours_per_day * found["Taux horaire"] * coefficient
        if found["Type"] == LABOUR
        else 0.0
    )
    disbursement = float(line.reestimated_amount) if found["Type"] == DISBURSEMENT else 0.0
    return {
        "Description de la tâche": description,
        "État": state,
        **found,
        "Coefficient": coefficient,
        "Main-d’œuvre": wages,
        "Débours": disbursement,
        "Reste à engager": wages + disbursement,
        "Jours restants": days,
    }


def tab_figures(
    reference: dict[str, list[Any]],
    facts: dict[str, TaskFacts],
    rows: Iterable[tuple[str, str, RemainingLine]],
    hours_per_day: Decimal,
) -> TabFigures:
    """Give the figures of a tab from its lines, each with its task and its entry in the list."""
    lines: list[dict[str, Any]] = []
    totals: dict[str, float] = dict.fromkeys(TOTALS, 0.0)
    for task_entry, entry, line in rows:
        days = (
            float(remaining_days(line.quantity, line.hours, hours_per_day))
            if line.role is not None
            else 0.0
        )
        figures = _line_figures(
            looked_up(reference, entry), facts.get(task_entry), line, days, float(hours_per_day)
        )
        lines.append(figures)
        totals["Budget"] += float(line.budget)
        totals["Reste précédent"] += float(line.previous or 0)
        totals["Jours restants"] += days
        if line.role is None:
            totals["Débours restant"] += float(line.reestimated_amount)
        for header in ("Main-d’œuvre", "Débours", "Reste à engager"):
            totals[header] += figures[header]
    return TabFigures(tuple(lines), totals)
