# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the spreading, replayed without a database (US-1520/L1).

The remaining load of a started task over the months that follow the date of calculation
(WF-DEV-0070-A), and the planned value of a budget of the reference (WF-DEV-0080-A): the inputs and
the values of the sentences, from their fixtures under ``fixtures/estimate``.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.spreading import (
    Month,
    Placement,
    PlannedLine,
    planned_value,
    spread_by_month,
)
from waterfall.core.planning.interface import Calendar, WorkInstant, weekly_calendar

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def week_of(example: Example) -> Calendar:
    """Return the calendar an example gives."""
    hours = cast("dict[str, str]", example["weekly_hours"])
    return weekly_calendar(tuple(Decimal(hours[day]) for day in DAYS))


def placement_of(week: Calendar, task: dict[str, str]) -> Placement:
    """Return a task of an example: it starts at the first hour of its day, and finishes at its."""
    return Placement(
        week,
        WorkInstant(date.fromisoformat(task["start"])),
        WorkInstant(date.fromisoformat(task["finish"]), Decimal(task["finish_hours"])),
    )


@pytest.mark.requirement("WF-DEV-0070-A")
def test_a_remaining_load_of_80_hours_is_spread_40_and_40_on_the_two_months_left(
    example: Callable[[str], Example],
) -> None:
    # « Une tâche démarrée qui couvre exactement quatre mois civils, à mi-parcours à la date de
    # calcul — le premier jour du troisième mois —, dont une ligne porte un reste de 80 heures,
    # présente ces 80 heures sur les deux mois restants au prorata de leurs heures travaillées —
    # 40 et 40 s'ils en comptent autant — et rien sur les mois écoulés. »
    data = example("WF-DEV-0070-A#e69ddd150e53")
    task = placement_of(week_of(data), cast("dict[str, str]", data["task"]))
    spread = spread_by_month(
        task,
        Decimal(cast("str", data["remaining_hours"])),
        as_of=date.fromisoformat(cast("str", data["as_of"])),
    )
    expected = {
        Month(int(month[:4]), int(month[5:])): Decimal(hours)
        for month, hours in cast("dict[str, str]", data["monthly_hours"]).items()
    }
    assert spread == expected


@pytest.mark.requirement("WF-DEV-0080-A")
def test_a_budget_of_1000_is_planned_at_1000_on_the_last_finish_and_at_0_before_the_first_start(
    example: Callable[[str], Example],
) -> None:
    # « Sur un projet dont le budget de référence est de 1 000, la valeur planifiée vaut 1 000 à
    # la date de fin de la dernière tâche de la référence, et 0 avant le début de la première. »
    data = example("WF-DEV-0080-A#97ee98949ad1")
    week = week_of(data)
    lines = [
        PlannedLine(Decimal(line["amount"]), placement_of(week, line))
        for line in cast("list[dict[str, str]]", data["lines"])
    ]
    assert sum(line.amount for line in lines) == Decimal(cast("str", data["budget"]))
    for expected in cast("list[dict[str, str]]", data["values"]):
        assert planned_value(lines, date.fromisoformat(expected["at"])) == Decimal(
            expected["value"]
        )
