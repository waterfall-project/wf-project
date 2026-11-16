# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric example of the projection of spending, replayed without a database (US-2050/L1).

The line of 1 200 on a task of two civil months (WF-DEV-0100-A): the inputs and the values of the
sentence, from its fixture under ``fixtures/estimate``.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.estimate.interface import Month, Placement, amount_parts
from waterfall.core.planning.interface import WorkInstant, weekly_calendar

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@pytest.mark.requirement("WF-DEV-0100-A")
def test_a_line_of_1200_on_a_task_of_two_civil_months_is_spread_on_them_by_their_hours_worked(
    example: Callable[[str], Example],
) -> None:
    # « Une ligne de 1 200 portée par une tâche qui couvre exactement deux mois civils apparaît sur
    # ces deux mois, au prorata des heures travaillées de la tâche dans chacun. »
    data = example("WF-DEV-0100-A#72d0671c3c33")
    hours = cast("dict[str, str]", data["weekly_hours"])
    task = cast("dict[str, str]", data["task"])
    placement = Placement(
        weekly_calendar(tuple(Decimal(hours[day]) for day in DAYS)),
        WorkInstant(date.fromisoformat(task["start"])),
        WorkInstant(date.fromisoformat(task["finish"]), Decimal(task["finish_hours"])),
    )
    parts = amount_parts(placement, Decimal(cast("str", data["line_amount"])))
    expected = {
        Month(int(month[:4]), int(month[5:])): Decimal(amount)
        for month, amount in cast("dict[str, str]", data["monthly_amounts"]).items()
    }
    assert parts == expected
    assert sum(parts.values()) == Decimal(cast("str", data["line_amount"]))
