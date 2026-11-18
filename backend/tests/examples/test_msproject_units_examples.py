# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The numeric examples of the units of a planning of MS Project (US-2780/L1), without a database.

A duration and a lag in the unit they were entered in (WF-PLA-0160), through the pure reader, the
pure writer and the translation of ``planning.msproject``, from the fixtures under
``fixtures/planning``. What the report says of a file whose constants differ, and the dates kept
rather than the durations, are those of the import, which ``test_msproject_calendar_gap.py``
replays on a database; this file cannot replay them.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, cast

import pytest

from waterfall.core.planning.msproject import (
    MsProject,
    MsTask,
    PredecessorLink,
    constants_of,
    duration_of,
    lag_of,
    read_project,
    write_project,
)
from waterfall.core.planning.scheduling import Duration, DurationUnit, Lag, LagUnit, UnitConstants

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]
START = datetime.fromisoformat("2026-03-02T08:00:00")  # wall clock of the file, as it is read


def _constants(held: dict[str, str]) -> UnitConstants:
    return UnitConstants(
        Decimal(held["hours_per_day"]),
        Decimal(held["hours_per_week"]),
        Decimal(held["days_per_month"]),
    )


@pytest.mark.requirement("WF-PLA-0160-A")
def test_two_days_entered_at_seven_hours_a_day_keep_two_days_that_are_sixteen_hours_by_default(
    example: Callable[[str], Example],
) -> None:
    # « ... importé en gardant les durées, une tâche de « 2 j » saisie à 7 h par jour vaut deux
    # jours, soit seize heures avec les valeurs par défaut ; » Only the reading is replayed here,
    # not the import that applies it (``test_msproject_calendar_gap.py``, on a database): the file
    # carries 14 hours of work in days, at 7 hours a day; read at the constants of the file, the
    # task keeps its two days, which the constants by default make sixteen hours.
    data = example("WF-PLA-0160-A#952783e2946d")
    held = cast("dict[str, int]", data["file_constants"])
    task = cast("dict[str, object]", data["task"])
    kept = cast("dict[str, str]", task["kept"])
    file = MsProject(
        START,
        minutes_per_day=held["minutes_per_day"],
        minutes_per_week=held["minutes_per_week"],
        days_per_month=held["days_per_month"],
        tasks=(
            MsTask(
                1,
                "Câblage",
                1,
                duration=timedelta(hours=cast("int", task["duration_hours"])),
                duration_unit="d",
            ),
        ),
    )
    read = read_project(write_project(file)).project
    assert constants_of(read).hours_per_day == Decimal(7)
    duration = duration_of(read.tasks[0], constants_of(read))
    assert duration == Duration(Decimal(kept["value"]), cast("DurationUnit", kept["unit"]))
    by_default = _constants(cast("dict[str, str]", data["default_constants"]))
    assert duration.hours(by_default) == Decimal(cast("str", task["default_hours"]))


@pytest.mark.requirement("WF-PLA-0160-A")
def test_a_lag_of_one_week_is_exported_then_reimported_in_weeks(
    example: Callable[[str], Example],
) -> None:
    # « Un décalage saisi « 1 sem » est exporté puis réimporté sans changer d'unité. » The export
    # itself is not replayed here (its writer of a link is private to ``planning.exporting``): the
    # lag is taken as the example says the export writes it, 24 000 tenths of a minute, in the
    # format of weeks, as the fixture holds it and not as a computation of this test; what is
    # replayed is the file written from it and read back, which gives the lag in weeks again, not
    # in days or hours.
    data = example("WF-PLA-0160-A#8e3b08233deb")
    held = cast("dict[str, int]", data["constants"])
    lag = cast("dict[str, object]", data["lag"])
    entered = Lag(Decimal(cast("str", lag["value"])), cast("LagUnit", lag["unit"]))
    written = cast("int", lag["written"])
    file = MsProject(
        START,
        minutes_per_day=held["minutes_per_day"],
        minutes_per_week=held["minutes_per_week"],
        days_per_month=held["days_per_month"],
        tasks=(
            MsTask(1, "Câblage", 1, duration=timedelta(hours=8), duration_unit="d"),
            MsTask(
                2,
                "Essais",
                1,
                duration=timedelta(hours=8),
                duration_unit="d",
                predecessors=(PredecessorLink(1, "finish_to_start", written, entered.unit),),
            ),
        ),
    )
    read = read_project(write_project(file)).project
    link = read.tasks[1].predecessors[0]
    assert link.lag_unit == "w"
    assert lag_of(link, constants_of(read)) == entered
