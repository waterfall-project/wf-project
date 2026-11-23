# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The differences of a modified node of a comparison, without a base (US-2340/L1, WF-IHM-0150).

``core/estimate/subtracting.py`` is pure: of the values of a node that differ, those that are a
date, a duration or an amount bear a difference, the revision read less the base, written as the
node writes its values. The cases the service reaches with difficulty are proved here: two
durations of different units, of work or elapsed, a value null on one side, a date of entry.
"""

from decimal import Decimal
from typing import Any

import pytest

from waterfall.core.estimate.subtracting import deltas_of
from waterfall.core.planning.interface import Duration, UnitConstants

# The constants of the units by default: eight hours a day, forty a week, twenty days a month.
CONSTANTS = UnitConstants(Decimal(8), Decimal(40), Decimal(20))


def task(**facet: Any) -> dict[str, Any]:
    """Give a task written whole as the API writes it, its facet written with ``facet``."""
    return {"kind": "task", "task": facet, "estimate_line": None}


def duration(value: str, unit: str) -> dict[str, str]:
    """Give a duration as a node writes it."""
    return {"value": value, "unit": unit}


@pytest.mark.requirement("WF-IHM-0150-A")
@pytest.mark.parametrize(
    ("read", "base", "delta"),
    [
        # Of the same unit, the difference of their values, exact.
        (duration("12.5", "d"), duration("10", "d"), duration("2.5", "d")),
        # Of two units of work, in the unit read: a week less two days is 0.6 week.
        (duration("1", "w"), duration("2", "d"), duration("0.6", "w")),
        # Twenty days less a month of twenty days: nought, the unit alone differing.
        (duration("20", "d"), duration("1", "mo"), duration("0", "d")),
        # Shorter than the base: signed.
        (duration("4", "h"), duration("1", "d"), duration("-4", "h")),
        # Elapsed, an elapsed day of twenty-four hours, read in days of work of eight hours.
        (duration("4", "d"), duration("1", "ed"), duration("1", "d")),
        # Read elapsed: in elapsed days, the days of work at their hours.
        (duration("2", "ed"), duration("3", "d"), duration("1", "ed")),
        # Mixed: an elapsed day of 24 hours less a day of work of eight, in elapsed days: 16/24.
        (duration("1", "ed"), duration("1", "d"), duration("0.6666666667", "ed")),
        # The reverse, in days of work: a day of work less an elapsed day, sixteen hours short.
        (duration("1", "d"), duration("1", "ed"), duration("-2", "d")),
        # An elapsed hour counts for an hour, and an elapsed day for the 24 hours of a day.
        (duration("1", "eh"), duration("1", "h"), duration("0", "eh")),
        (duration("24", "h"), duration("1", "ed"), duration("0", "h")),
        # A third of an hour of difference, given as the engine renders a value.
        (duration("1", "h"), duration("40", "min"), duration("0.3333333333", "h")),
    ],
)
def test_a_duration_differs_in_working_time_in_the_unit_of_the_one_read(
    read: dict[str, str], base: dict[str, str], delta: dict[str, str]
) -> None:
    # « l'écart à la base [...] de chaque durée, en temps de travail » : two units converted into
    # hours by the constants of the installation (WF-PLA-0160), the difference in the unit read.
    found = deltas_of(["task.duration"], task(duration=base), task(duration=read), CONSTANTS)
    assert found == {"task.duration": delta}


@pytest.mark.requirement("WF-IHM-0150-A")
def test_a_date_differs_in_calendar_days_and_an_amount_to_the_cent() -> None:
    # The date alone of an instant of work, the hours of the day aside; a date of entry as it is;
    # an amount to the cent; a value that bears no difference left out.
    base = task(
        start={"date": "2026-03-06", "hours": "8"},
        started_on="2026-03-09",
        reestimated_amount="1000.00",
        label="Câblage",
    )
    read = task(
        start={"date": "2026-03-09", "hours": "0"},
        started_on="2026-03-02",
        reestimated_amount="1200.5",
        label="Câblage sur site",
    )
    names = ["task.label", "task.start", "task.started_on", "task.reestimated_amount"]
    assert deltas_of(names, base, read, CONSTANTS) == {
        "task.start": 3,
        "task.started_on": -7,
        "task.reestimated_amount": "200.50",
    }


@pytest.mark.requirement("WF-IHM-0150-A")
def test_a_difference_is_null_when_either_value_is() -> None:
    # A task not started in the base, started in the revision read; one completed in the base, its
    # completion withdrawn in the revision read.
    base = task(started_on=None, completed_on="2026-03-06")
    read = task(started_on="2026-03-02", completed_on=None)
    found = deltas_of(["task.started_on", "task.completed_on"], base, read, CONSTANTS)
    assert found == {"task.started_on": None, "task.completed_on": None}


@pytest.mark.requirement("WF-IHM-0150-A")
def test_a_duration_less_another_keeps_the_unit_of_the_first() -> None:
    # ``Duration.less``, which the planning gives the estimate: the values of the same unit
    # subtracted exactly, those of two units by their hours.
    week = Duration(Decimal(1), "w")
    assert week.less(Duration(Decimal("0.5"), "w"), CONSTANTS) == Duration(Decimal("0.5"), "w")
    assert week.less(Duration(Decimal(5), "d"), CONSTANTS) == Duration(Decimal(0), "w")


@pytest.mark.requirement("WF-REV-0080-A")
def test_the_total_float_bears_no_difference() -> None:
    # A value the planning engine computes, which modifies no task (#4312): named, it bears none.
    found = deltas_of(
        ["task.total_float"],
        task(total_float=duration("2", "d")),
        task(total_float=duration("5", "d")),
        CONSTANTS,
    )
    assert found == {}
