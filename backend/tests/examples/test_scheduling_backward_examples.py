# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The backward pass of the engine on the links of a summary and the short elapsed durations.

US-3300/L2, without a database: a link from the start of a summary bounds only the subordinates
that carry that start (#3335, WF-PLA-0100); a link finish to finish toward a summary binds each of
its subordinates (WF-PLA-0030, 1.0.7); an elapsed duration shorter than a day goes back as far as
the same hours of work do (#4412, WF-PLA-0160); and the finish of a manual task of an elapsed
duration is bounded to the hours of the day it reaches, as the engine bounds it (#4412). The
planning starts on Monday the 2nd of March 2026, on a calendar of eight hours from Monday to
Friday.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from waterfall.core.planning.entries import finish_after
from waterfall.core.planning.scheduling import (
    Calendar,
    Duration,
    DurationUnit,
    Lag,
    Link,
    LinkType,
    Schedule,
    ScheduledTask,
    Structure,
    Task,
    UnitConstants,
    WorkInstant,
    schedule,
)

MONDAY = date(2026, 3, 2)
CONSTANTS = UnitConstants(Decimal(8), Decimal(40), Decimal(20))
EIGHT, NONE = Decimal(8), Decimal(0)
EIGHT_HOURS = Calendar((EIGHT, EIGHT, EIGHT, EIGHT, EIGHT, NONE, NONE))


def ident(number: int) -> UUID:
    """Return the identifier of the task of a number."""
    return UUID(int=number)


def day(offset: int, hours: str = "0") -> WorkInstant:
    """Return the instant so many days after the planning start, at so many hours of work."""
    return WorkInstant(MONDAY + timedelta(days=offset), Decimal(hours))


def duration(entered: str) -> Duration:
    """Return a duration entered as its value and its unit: ``"0.5 eh"``, in days without one."""
    value, _, unit = entered.partition(" ")
    return Duration(Decimal(value), cast("DurationUnit", unit or "d"))


def task(number: int, entered: str = "1", parent: int | None = None) -> Task:
    """Return a task in automatic mode of its duration entered, under a summary when given."""
    parent_id = None if parent is None else ident(parent)
    return Task(ident(number), parent_id, "automatic", duration(entered), EIGHT_HOURS)


def link(
    predecessor: int, successor: int, link_type: LinkType = "finish_to_start", lag: str = "0"
) -> Link:
    """Return a link between two tasks of numbers, its lag in days of work."""
    return Link(ident(predecessor), ident(successor), link_type, Lag(Decimal(lag), "d"))


def planned(tasks: list[Task], links: list[Link], start: date = MONDAY) -> Schedule:
    """Return the schedule of a structure that starts on a day, by default the tests' Monday."""
    return schedule(Structure(tuple(tasks), tuple(links), start, CONSTANTS))


def of(dated: Schedule, number: int) -> ScheduledTask:
    """Return a task of a schedule by its number."""
    return dated.tasks[ident(number)]


# --- WF-PLA-0100: a link from the start of a summary --------------------------------------------


@pytest.mark.requirement("WF-PLA-0100-A")
@pytest.mark.parametrize(
    ("link_type", "lag"),
    # Start to finish, a lag of five days finishes T where start to start starts it: on the Friday
    # and on the Monday, the same dates.
    [("start_to_start", "0"), ("start_to_finish", "5")],
    ids=["start-to-start", "start-to-finish"],
)
def test_a_link_from_the_start_of_a_summary_bounds_only_the_subordinates_that_carry_it(
    link_type: LinkType, lag: str
) -> None:
    # « Sur un planning à deux branches parallèles de durées différentes, la branche la plus longue
    # est critique et l'autre porte une marge égale à leur écart. », its form for a link from the
    # start of a summary (#3335): S = {A 1 j ; B 1 j ; A → B}, and S before T of five days. A
    # carries the start of S, and T the finish of the structure: both are critical; B, which
    # does not, may slip to the Friday, three days.
    tasks = [task(1), task(2, parent=1), task(3, parent=1), task(4, "5")]
    dated = planned(tasks, [link(2, 3), link(1, 4, link_type, lag)])
    assert dated.link_conflicts == ()
    assert (of(dated, 2).start, of(dated, 2).finish) == (day(0), day(0, "8"))
    assert (of(dated, 3).start, of(dated, 3).finish) == (day(1), day(1, "8"))
    assert (of(dated, 4).start, of(dated, 4).finish) == (day(0), day(4, "8"))
    floats = [(of(dated, n).total_float, of(dated, n).is_critical) for n in (2, 3, 1, 4)]
    assert floats == [
        (Decimal(0), True),
        (Decimal(3), False),
        (Decimal(0), True),
        (Decimal(0), True),
    ]


# --- WF-PLA-0030: a link finish to finish toward a summary --------------------------------------


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_link_finish_to_finish_toward_a_summary_binds_the_finish_of_each_subordinate() -> None:
    # « Une liaison fin à début vers une récapitulative fait commencer chacune de ses subordonnées
    # automatiques sans prédécesseur après la fin du prédécesseur. » The forward pass is unchanged,
    # and the other types bind each subordinate as well, as the specification 1.0.7 settled it
    # (« s'impose à chacune de ses subordonnées », #3368): P of five days finishes on the Friday,
    # finish to finish toward S = {A 1 j ; B 1 j ; A → B}; A finishes on the Friday, B on the
    # Monday after.
    tasks = [task(1, "5"), task(2), task(3, parent=2), task(4, parent=2)]
    dated = planned(tasks, [link(3, 4), link(1, 2, "finish_to_finish")])
    assert of(dated, 1).finish == day(4, "8")
    assert (of(dated, 3).start, of(dated, 3).finish) == (day(4), day(4, "8"))
    assert (of(dated, 4).start, of(dated, 4).finish) == (day(7), day(7, "8"))
    assert (of(dated, 2).start, of(dated, 2).finish) == (day(4), day(7, "8"))
    # The backward pass mirrors it: P may finish no later than A, the four on the critical path.
    assert dated.link_conflicts == ()
    assert [of(dated, n).total_float for n in (1, 2, 3, 4)] == [Decimal(0)] * 4


# --- WF-PLA-0160: an elapsed duration shorter than a day, backward ------------------------------


def elapsed_branch(entered: str) -> Schedule:
    """Return A (13 h) before B (``entered``) before C (1 j), and D (2 j) before C."""
    tasks = [task(1, "13 h"), task(2, entered), task(3), task(4, "2")]
    return planned(tasks, [link(1, 2), link(2, 3), link(4, 3)])


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize(
    ("elapsed", "worked", "floats"),
    [
        # B from the Tuesday's fifth hour to its fifth and a half: two hours and a half to the end
        # of the Tuesday's work, where D finishes.
        ("0.5 eh", "0.5 h", Decimal("0.3125")),
        ("2 eh", "2 h", Decimal("0.125")),
        ("30 emin", "30 min", Decimal("0.3125")),
    ],
    ids=["half-an-elapsed-hour", "two-elapsed-hours", "thirty-elapsed-minutes"],
)
def test_an_elapsed_duration_shorter_than_a_day_floats_as_its_hours_of_work_do(
    elapsed: str, worked: str, floats: Decimal
) -> None:
    # « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur finit à la dernière
    # heure travaillée d'un vendredi s'achève le dimanche ; le successeur, sur un calendrier du
    # lundi au vendredi, commence le lundi à la première heure travaillée, de même qu'avec un
    # décalage de 2 eh. » The forward pass is unchanged; backward, an elapsed duration of less than
    # a day goes back as far as the same hours of work (#4412): gone back to the Tuesday's first
    # hour, half an elapsed hour gave A a float of minus 0.625 day, critical without a conflict.
    dated, same = elapsed_branch(elapsed), elapsed_branch(worked)
    assert (of(dated, 2).start, of(dated, 2).finish) == (of(same, 2).start, of(same, 2).finish)
    assert of(dated, 3).start == day(2)
    assert dated.link_conflicts == ()
    for n in (1, 2):
        assert of(dated, n).total_float == of(same, n).total_float == floats
        assert not of(dated, n).is_critical


@pytest.mark.story("US-3300")
def test_elapsed_hours_finishing_at_the_end_of_a_day_from_any_start_leave_a_nil_float() -> None:
    # Propre à l'US, « une durée écoulée recule juste » (#4412) pour les heures qui outrepassent
    # celles du jour : an elapsed duration finishes on the day it reaches, its hours bounded to
    # that day's. A of thirty elapsed hours finishes on the Tuesday at its sixth hour of work; B,
    # ten elapsed hours after it, at the Tuesday's eighth, as it would from the Tuesday's first.
    # Gone back to that first hour, B's latest start gave A a float of minus 0.75 day, critical
    # without a conflict; B starts no earlier at the latest than it does, and A is critical with a
    # float of nil — a float is what A may slip by with the finish kept, and the latest start of B
    # that keeps it is not a count a start can be placed at (the end of the day's work is the next
    # day's first hour).
    dated = planned([task(1, "30 eh"), task(2, "10 eh")], [link(1, 2)])
    assert (of(dated, 1).finish, of(dated, 2).start) == (day(1, "6"), day(1, "6"))
    assert of(dated, 2).finish == day(1, "8")
    assert dated.link_conflicts == ()
    assert [of(dated, n).total_float for n in (1, 2)] == [Decimal(0), Decimal(0)]


@pytest.mark.story("US-3300")
def test_a_late_automatic_task_of_elapsed_hours_keeps_its_negative_float() -> None:
    # Propre à l'US (#4412, #3984) : the floor on the latest start of a task finishing on time does
    # not lift the float of one that finishes late. A (10 j) → B (10 eh, automatic) → M, manual and
    # dated on the Monday of the second week, before the end of A and of B: both keep a negative
    # float, and are critical.
    manual = Task(ident(3), None, "manual", duration("1"), EIGHT_HOURS, day(7), day(7, "8"))
    tasks = [task(1, "10"), task(2, "10 eh"), manual]
    dated = planned(tasks, [link(1, 2), link(2, 3)])
    assert of(dated, 2).finish > of(dated, 3).start
    for n in (1, 2):
        total = of(dated, n).total_float
        assert total is not None
        assert total < 0
        assert of(dated, n).is_critical


# --- The finish of a manual task of an elapsed duration (US-3300) -------------------------------


@pytest.mark.story("US-3300")
def test_ten_elapsed_hours_of_a_manual_task_finish_at_the_end_of_the_monday_work() -> None:
    # « commencée un lundi à la première heure sur un calendrier de 8 h, une durée saisie « 10 eh »
    # finit le lundi à 8 h, non à 10 h » — where the engine finishes the same task automatic.
    entered = duration("10 eh")
    finish = finish_after(day(0), entered, EIGHT_HOURS, CONSTANTS)
    assert finish == day(0, "8")
    assert of(planned([task(1, "10 eh")], []), 1).finish == finish


@pytest.mark.story("US-3300")
@pytest.mark.parametrize("hours", ["0", "4"], ids=["at-its-first-hour", "at-its-fourth-hour"])
def test_an_elapsed_day_entered_from_a_friday_finishes_where_the_engine_finishes_it(
    hours: str,
) -> None:
    # « « 1 ej » saisi depuis un vendredi finit où le moteur le finit en automatique »: on the
    # Saturday, which grants no hour of work, at none, whatever the hour of the Friday it starts at.
    friday = MONDAY + timedelta(days=4)
    finish = finish_after(day(4, hours), duration("1 ed"), EIGHT_HOURS, CONSTANTS)
    tasks = [task(1, f"{hours} h"), task(2, "1 ed")]
    automatic = of(planned(tasks, [link(1, 2)], friday), 2)
    assert automatic.start == day(4, hours)
    assert finish == automatic.finish == day(5)
