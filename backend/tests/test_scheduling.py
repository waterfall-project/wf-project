# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The engine of the dates, the floats and the critical path, without a database.

Laid by US-1380/L1, the socle of EP-06, so that no two stories create the same file; US-1390/L1
writes its tests of the Vérif fields under ``examples``. Here, US-1390/L2: the hours the engine
renders, at a scale that does not depend on the context of ``decimal`` and that a date read back
meets exactly (#2460); the float of a predecessor working a day its successor does not (#2461).
"""

from datetime import date, timedelta
from decimal import Decimal, localcontext
from typing import cast
from uuid import UUID

import pytest

from waterfall.core.planning.scheduling import (
    Calendar,
    Duration,
    DurationUnit,
    Lag,
    Link,
    Schedule,
    Structure,
    Task,
    UnitConstants,
    WorkInstant,
    schedule,
)

MONDAY = date(2026, 3, 2)
CONSTANTS = UnitConstants(Decimal(8), Decimal(40), Decimal(20))
EIGHT = Decimal(8)
NONE = Decimal(0)
WEEKDAYS = Calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, NONE, NONE))
SIX_DAYS = Calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, NONE))


def ident(number: int) -> UUID:
    """Return the identifier of the task of a number."""
    return UUID(int=number)


def automatic(number: int, entered: str, calendar: Calendar = WEEKDAYS) -> Task:
    """Return a task in automatic mode of a duration entered, ``"20 min"``."""
    value, _, unit = entered.partition(" ")
    duration = Duration(Decimal(value), cast("DurationUnit", unit))
    return Task(ident(number), None, "automatic", duration, calendar)


def manual(number: int, start: WorkInstant, finish: WorkInstant) -> Task:
    """Return a task in manual mode between two instants, of a day."""
    return Task(ident(number), None, "manual", Duration(Decimal(1), "d"), WEEKDAYS, start, finish)


def finish_to_start(predecessor: int, successor: int) -> Link:
    """Return a link finish to start without lag."""
    return Link(ident(predecessor), ident(successor), "finish_to_start", Lag(NONE, "d"))


def planned(tasks: list[Task], links: list[Link]) -> Schedule:
    """Return the schedule of a structure that starts on a Monday."""
    return schedule(Structure(tuple(tasks), tuple(links), MONDAY, CONSTANTS))


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_third_of_an_hour_is_rendered_at_a_fixed_scale_whatever_the_decimal_context() -> None:
    # #2460: the engine computes in fractions and renders ten decimals, rounded half to even,
    # without reading the context of the ``decimal`` module.
    with localcontext() as context:
        context.prec = 6
        narrow = planned([automatic(1, "20 min")], []).tasks[ident(1)]
    wide = planned([automatic(1, "20 min")], []).tasks[ident(1)]
    assert narrow.finish == wide.finish == WorkInstant(MONDAY, Decimal("0.3333333333"))
    assert wide.work_hours == Decimal("0.3333333333")


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_manual_task_started_at_the_finish_rendered_of_its_predecessor_is_in_no_conflict() -> (
    None
):
    # #2460: a third of an hour rendered, then sent back as the start of a manual successor, meets
    # the finish it was rendered from: no conflict, and a float of exactly nought — not a
    # negative ten-billionth. Nought is the critical path (WF-PLA-0100).
    alone = planned([automatic(1, "20 min")], []).tasks[ident(1)]
    successor = manual(2, alone.finish, WorkInstant(MONDAY, EIGHT))
    both = planned([automatic(1, "20 min"), successor], [finish_to_start(1, 2)])
    first = both.tasks[ident(1)]
    assert both.link_conflicts == ()
    assert first.link_conflicts == ()
    assert first.total_float == Decimal(0)
    assert str(first.total_float) == "0"
    assert first.is_critical


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_predecessor_working_the_saturday_floats_to_the_end_of_it_before_a_monday_successor() -> (
    None
):
    # #2461: a predecessor on a calendar of six days, linked finish to start to a successor on a
    # calendar from Monday to Friday whose latest start is a Monday: the predecessor may finish as
    # late as the end of its Saturday, the successor not starting before the Monday anyway. From
    # the end of its Monday to the end of the next Saturday, five of its days: a float of five.
    # A task of six days from Monday to the next Monday carries the finish of the structure.
    dated = planned(
        [automatic(1, "1 d", SIX_DAYS), automatic(2, "1 d"), automatic(3, "6 d")],
        [finish_to_start(1, 2)],
    )
    predecessor, successor = dated.tasks[ident(1)], dated.tasks[ident(2)]
    assert predecessor.finish == WorkInstant(MONDAY, EIGHT)
    assert successor.start == WorkInstant(MONDAY + timedelta(days=1), NONE)
    assert successor.total_float == Decimal(4)
    assert predecessor.total_float == Decimal(5)
    assert not predecessor.is_critical
    assert dated.tasks[ident(3)].total_float == Decimal(0)
