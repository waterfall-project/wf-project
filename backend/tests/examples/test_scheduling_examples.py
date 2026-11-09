# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The examples of the planning's Vérif fields, replayed on the engine without a database (US-1390).

The calendar applicable to a task (WF-PLA-0010), the links and their lags (WF-PLA-0030), the
critical path (WF-PLA-0100) and the units of duration (WF-PLA-0160): the numeric sentences from
their fixtures under ``fixtures/planning``, the others with the data they say. The planning starts
on Monday the 2nd of March 2026, on a calendar of eight hours from Monday to Friday unless a test
says otherwise.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest

from waterfall.core.planning.scheduling import (
    Calendar,
    Duration,
    DurationUnit,
    Entry,
    Lag,
    LagUnit,
    Link,
    LinkConflict,
    LinkCycleError,
    LinkForbiddenError,
    LinkType,
    Move,
    Schedule,
    ScheduledTask,
    Structure,
    Task,
    TaskWithoutWorkingHoursError,
    UnitConstants,
    WorkInstant,
    applicable_calendar,
    horizon_of,
    schedule,
)

if TYPE_CHECKING:
    from collections.abc import Callable

Example = dict[str, object]

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MONDAY = date(2026, 3, 2)
CONSTANTS = UnitConstants(Decimal(8), Decimal(40), Decimal(20))


def hours_of_week(*hours: int) -> Calendar:
    """Return a calendar from its hours, Monday first."""
    week = tuple(Decimal(each) for each in hours)
    return Calendar((week[0], week[1], week[2], week[3], week[4], week[5], week[6]))


EIGHT_HOURS = hours_of_week(8, 8, 8, 8, 8, 0, 0)
FOUR_HOURS = hours_of_week(4, 4, 4, 4, 4, 0, 0)
EVERY_HOUR = hours_of_week(24, 24, 24, 24, 24, 24, 24)


def ident(number: int) -> UUID:
    """Return the identifier of the task of a number."""
    return UUID(int=number)


def day(offset: int, hours: int = 0) -> WorkInstant:
    """Return the instant so many days after the planning start, at so many hours of work."""
    return WorkInstant(MONDAY + timedelta(days=offset), Decimal(hours))


def duration(entered: str) -> Duration:
    """Return a duration entered as its value and its unit: ``"16 h"``, in days without one."""
    value, _, unit = entered.partition(" ")
    return Duration(Decimal(value), cast("DurationUnit", unit or "d"))


def task(
    number: int,
    entered: str = "1",
    *,
    parent: int | None = None,
    calendar: Calendar = EIGHT_HOURS,
    manual: tuple[WorkInstant, WorkInstant] | None = None,
) -> Task:
    """Return a task: automatic, of its duration entered, or manual between two instants."""
    start, finish = manual or (None, None)
    return Task(
        task_id=ident(number),
        parent_id=None if parent is None else ident(parent),
        mode="automatic" if manual is None else "manual",
        duration=duration(entered),
        calendar=calendar,
        start=start,
        finish=finish,
    )


def link(
    predecessor: int,
    successor: int,
    link_type: LinkType = "finish_to_start",
    lag: str = "0",
    unit: LagUnit = "d",
) -> Link:
    """Return a link between two tasks of numbers."""
    return Link(ident(predecessor), ident(successor), link_type, Lag(Decimal(lag), unit))


def planned(tasks: list[Task], links: list[Link] | None = None) -> Schedule:
    """Return the schedule of a structure that starts on the Monday of the tests."""
    return schedule(Structure(tuple(tasks), tuple(links or []), MONDAY, CONSTANTS))


def of(dated: Schedule, number: int) -> ScheduledTask:
    """Return a task of a schedule by its number."""
    return dated.tasks[ident(number)]


def weekday(instant: WorkInstant) -> str:
    """Return the name of the day of an instant."""
    return DAYS[instant.day.weekday()]


# --- WF-PLA-0010: the applicable calendar ------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0010-A")
@pytest.mark.parametrize(
    ("calendar", "finish"),
    [(EIGHT_HOURS, day(1, 8)), (FOUR_HOURS, day(3, 4))],
    ids=["eight-hours-tuesday", "four-hours-thursday"],
)
def test_sixteen_hours_started_on_a_monday_finish_on_the_tuesday_or_the_thursday(
    calendar: Calendar, finish: WorkInstant
) -> None:
    # « Une tâche de seize heures en mode automatique, commencée un lundi matin sur un calendrier
    # de huit heures du lundi au vendredi, finit le mardi ; sur un calendrier de quatre heures,
    # elle finit le jeudi. »
    dated = of(planned([task(1, "16 h", calendar=calendar)]), 1)
    assert (dated.start, dated.finish) == (day(0), finish)
    assert dated.work_hours == Decimal(16)


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_task_of_two_roles_working_eight_and_six_hours_is_planned_on_six_on_the_monday() -> None:
    # « Une tâche dont les deux rôles travaillent huit et six heures le lundi est planifiée sur six
    # heures ce jour-là. »
    six_on_monday = hours_of_week(6, 8, 8, 8, 8, 0, 0)
    applicable = applicable_calendar([EIGHT_HOURS, six_on_monday], EIGHT_HOURS)
    assert applicable.week == six_on_monday.week
    dated = of(planned([task(1, "8 h", calendar=applicable)]), 1)
    assert applicable.work_between(dated.start, WorkInstant(MONDAY, Decimal(24))) == Decimal(6)
    assert dated.finish == day(1, 2)


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_task_without_a_labour_line_is_planned_on_the_default_calendar() -> None:
    # « Une tâche sans ligne de main-d'œuvre est planifiée sur le calendrier par défaut. »
    assert applicable_calendar([], FOUR_HOURS) is FOUR_HOURS
    assert of(planned([task(1, calendar=applicable_calendar([], FOUR_HOURS))]), 1).finish == day(
        1, 4
    )


@pytest.mark.requirement("WF-PLA-0010-A")
def test_a_task_whose_calendar_grants_no_hour_in_the_week_is_refused_by_name() -> None:
    weekend = hours_of_week(8, 8, 8, 8, 8, 0, 0)
    weekdays = hours_of_week(0, 0, 0, 0, 0, 8, 8)
    never = applicable_calendar([weekend, weekdays], EIGHT_HOURS)
    with pytest.raises(TaskWithoutWorkingHoursError) as refused:
        planned([task(1), task(2, calendar=never)])
    assert (refused.value.code, refused.value.task_id) == ("TASK_WITHOUT_WORKING_HOURS", ident(2))


# --- WF-PLA-0160: the units of duration --------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0160-A")
def test_two_days_a_week_and_a_month_are_worth_their_hours_by_the_default_constants(
    example: Callable[[str], Example],
) -> None:
    # « Avec les valeurs par défaut, une durée saisie « 2 j » vaut seize heures, « 1 sem » quarante
    # heures et « 1 m » cent soixante heures. »
    units = example("WF-PLA-0160-A#bbe6853cf3ce")
    constants = cast("dict[str, str]", units["constants"])
    by_default = UnitConstants(
        Decimal(constants["hours_per_day"]),
        Decimal(constants["hours_per_week"]),
        Decimal(constants["days_per_month"]),
    )
    for case in cast("list[dict[str, str]]", units["durations"]):
        duration = Duration(Decimal(case["value"]), cast("DurationUnit", case["unit"]))
        assert duration.hours(by_default) == Decimal(case["hours"])


def constants_of(held: dict[str, str]) -> UnitConstants:
    """Return the constants of the units a fixture writes."""
    return UnitConstants(
        Decimal(held["hours_per_day"]),
        Decimal(held["hours_per_week"]),
        Decimal(held["days_per_month"]),
    )


@pytest.mark.requirement("WF-PLA-0160-A")
def test_two_days_after_seven_hours_a_day_are_fourteen_hours_and_redated_the_marked_sixteen(
    example: Callable[[str], Example],
) -> None:
    # « Après passage des heures par jour de 8 à 7, une durée saisie « 2 j » dans une révision en
    # cours vaut quatorze heures, et ses dates sont recalculées ; dans une révision marquée, elle
    # vaut toujours seize heures. » The current revision is dated with the constants of the
    # installation, the marked one keeps what it computed with those of its time (US-1390/L2).
    changed = example("WF-PLA-0160-A#accda3317067")
    entered = cast("dict[str, str]", changed["duration"])
    two_days = Duration(Decimal(entered["value"]), cast("DurationUnit", entered["unit"]))
    calendar = hours_of_week(*(int(each) for each in cast("list[str]", changed["weekly_hours"])))
    for revision, held in (("current", "after"), ("marked", "before")):
        constants = constants_of(cast("dict[str, str]", changed[held]))
        expected = cast("dict[str, Any]", changed[revision])
        assert two_days.hours(constants) == Decimal(expected["hours"])
        planned_task = Task(ident(1), None, "automatic", two_days, calendar)
        dated = schedule(Structure((planned_task,), (), MONDAY, constants)).tasks[ident(1)]
        finish = cast("dict[str, str]", expected["finish"])
        assert (weekday(dated.finish), dated.finish.hours) == (
            finish["weekday"],
            Decimal(finish["hours"]),
        )


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize("key", ["WF-PLA-0160-A#6b5177e54497", "WF-PLA-0160-A#a1744bbc07cd"])
def test_a_lag_after_the_last_hour_of_a_friday_places_its_successor_by_its_unit(
    example: Callable[[str], Example], key: str
) -> None:
    # « Un décalage de 2 ej sur une liaison fin à début dont le prédécesseur finit à la dernière
    # heure travaillée d'un vendredi s'achève le dimanche ; le successeur, sur un calendrier du
    # lundi au vendredi, commence le lundi à la première heure travaillée, de même qu'avec un
    # décalage de 2 eh. » ; « Un décalage de 2 j sur la même liaison le fait commencer le
    # mercredi. »
    lags = example(key)
    week = cast("dict[str, str]", lags["weekly_hours"])
    calendar = hours_of_week(*(int(week[name]) for name in DAYS))
    finish = cast("dict[str, str]", lags["predecessor_finish"])
    friday = WorkInstant(date.fromisoformat(finish["date"]), Decimal(finish["hours"]))
    assert weekday(friday) == finish["weekday"]
    assert friday.hours == calendar.hours_on(friday.day)
    cases = [
        each for each in cast("list[dict[str, object]]", lags["lags"]) if each["example"] == key
    ]
    assert cases
    for case in cases:
        sent = cast("dict[str, str]", case["lag"])
        expected = cast("dict[str, str]", case["successor_start"])
        unit = cast("LagUnit", sent["unit"])
        predecessor = task(1, calendar=calendar, manual=(WorkInstant(friday.day), friday))
        tasks = [predecessor, task(2, calendar=calendar), task(3, calendar=EVERY_HOUR)]
        links = [link(1, 2, lag=sent["value"], unit=unit), link(1, 3, lag=sent["value"], unit=unit)]
        dated = planned(tasks, links)
        start = of(dated, 2).start
        assert (weekday(start), start.hours) == (expected["weekday"], Decimal(expected["hours"]))
        if "lag_ends_on" in case:
            # A successor that works every hour of every day starts where the lag ends.
            assert weekday(of(dated, 3).start) == case["lag_ends_on"]


@pytest.mark.requirement("WF-PLA-0160-A")
@pytest.mark.parametrize(
    ("value", "unit", "hours"),
    [
        ("90", "min", "1.5"),
        ("3", "h", "3"),
        ("90", "emin", "1.5"),
        ("2", "ed", "48"),
        ("1", "ew", "168"),
        ("1", "emo", "720"),
    ],
)
def test_each_unit_converts_by_its_constant_or_without_a_calendar(
    value: str, unit: DurationUnit, hours: str
) -> None:
    assert Duration(Decimal(value), unit).hours(CONSTANTS) == Decimal(hours)


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_percent_of_an_elapsed_predecessor_is_an_elapsed_lag() -> None:
    # Ten elapsed days from the Monday finish on the Thursday after, at its first hour of work, as
    # MS Project finishes them; half of them, five elapsed days, reach the Tuesday's first hour,
    # where a successor working every hour starts. Five days of work would have reached the Friday.
    tasks = [task(1, "10 ed"), task(2, calendar=EVERY_HOUR)]
    dated = planned(tasks, [link(1, 2, lag="50", unit="percent")])
    assert of(dated, 1).finish == day(10)
    assert of(dated, 2).start == day(15)


@pytest.mark.requirement("WF-PLA-0160-A")
def test_an_elapsed_duration_runs_over_the_days_without_hours_of_work() -> None:
    # Two elapsed days from a Friday morning end on the Sunday: the task finishes on the day it
    # reaches, as MS Project finishes it, its hours bounded to the none of that day (#2342); its
    # work is the Friday's eight hours, and its successor starts on the Monday.
    dated = planned([task(1, "4"), task(2, "2 ed"), task(3)], [link(1, 2), link(2, 3)])
    assert (of(dated, 2).start, of(dated, 2).finish) == (day(4), day(6))
    assert of(dated, 2).work_hours == Decimal(8)
    assert of(dated, 3).start == day(7)


# --- WF-PLA-0030: the links --------------------------------------------------------------------


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_lag_of_half_the_predecessor_of_ten_days_is_worth_five_days_of_work(
    example: Callable[[str], Example],
) -> None:
    # « Un décalage de 50 % sur un prédécesseur de dix jours vaut cinq jours de travail. »
    lag = example("WF-PLA-0030-A#0db0c7e480a9")
    before, sent, worth = (
        cast("dict[str, str]", lag[name]) for name in ("predecessor", "lag", "worth")
    )
    dated = planned(
        [task(1, f"{before['value']} {before['unit']}"), task(2)],
        [link(1, 2, lag=sent["value"], unit=cast("LagUnit", sent["unit"]))],
    )
    expected = Duration(Decimal(worth["value"]), cast("DurationUnit", worth["unit"]))
    between = EIGHT_HOURS.work_between(of(dated, 1).finish, of(dated, 2).start)
    assert between == expected.hours(CONSTANTS)


@pytest.mark.requirement("WF-PLA-0030-A")
@pytest.mark.parametrize(
    ("link_type", "lag"),
    [
        ("finish_to_start", "-1"),
        ("start_to_start", "1"),
        ("finish_to_finish", "0"),
        ("start_to_finish", "2"),
    ],
)
def test_each_of_the_four_types_places_its_successor_with_its_lag(
    link_type: LinkType, lag: str
) -> None:
    # A predecessor of two days, from the Monday: each link, its lag a lead for the first, makes a
    # successor of one day start on the Tuesday.
    dated = planned([task(1, "2"), task(2)], [link(1, 2, link_type, lag)])
    assert (of(dated, 2).start, of(dated, 2).finish) == (day(1), day(1, 8))


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_link_closing_a_loop_is_refused_naming_its_tasks_from_the_task_entered() -> None:
    # « La création d'une liaison fermant un cycle […] est refusée, et la raison en est nommée à
    # l'utilisateur » : from the task entered to the predecessor sent that already follows it.
    tasks = [task(1), task(2), task(3), task(4)]
    links = [link(1, 2), link(2, 3), link(4, 2), link(3, 1)]
    with pytest.raises(LinkCycleError) as refused:
        schedule(Structure(tuple(tasks), tuple(links), MONDAY, CONSTANTS), Entry(ident(1)))
    assert refused.value.code == "LINK_CYCLE"
    assert refused.value.cycle == (ident(1), ident(2), ident(3))


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_task_entered_as_its_own_predecessor_is_a_loop_of_itself() -> None:
    structure = Structure((task(1), task(2)), (link(1, 1),), MONDAY, CONSTANTS)
    with pytest.raises(LinkCycleError) as refused:
        schedule(structure, Entry(ident(1)))
    assert refused.value.cycle == (ident(1),)


@pytest.mark.requirement("WF-PLA-0030-A")
@pytest.mark.parametrize(
    ("predecessor", "successor"), [(1, 3), (3, 1)], ids=["summary-first", "subordinate-first"]
)
def test_a_link_between_a_summary_and_its_subordinate_is_refused(
    predecessor: int, successor: int
) -> None:
    # « La création d'une liaison […] reliant une récapitulative à l'une de ses subordonnées, est
    # refusée » : at any depth, before the loop it would close.
    tasks = [task(1), task(2, parent=1), task(3, parent=2)]
    with pytest.raises(LinkForbiddenError) as refused:
        planned(tasks, [link(predecessor, successor)])
    assert refused.value.code == "LINK_FORBIDDEN"
    assert (refused.value.summary_id, refused.value.subordinate_id) == (ident(1), ident(3))


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_loop_through_a_summary_is_named_from_its_first_task_in_the_order_of_the_plan() -> None:
    # P precedes W, W spans Z, Z precedes M, M under P: the loop P, W, Z, M (#1169).
    tasks = [task(1), task(2, parent=1), task(3), task(4, parent=3)]
    links = [link(1, 3), link(4, 2)]
    with pytest.raises(LinkCycleError) as refused:
        planned(tasks, links)
    assert refused.value.cycle == (ident(1), ident(3), ident(4), ident(2))
    structure = Structure(tuple(tasks), tuple(links), MONDAY, CONSTANTS)
    with pytest.raises(LinkCycleError) as moved:
        schedule(structure, Move((ident(2),), ident(1)))
    assert moved.value.cycle == (ident(1), ident(3), ident(4), ident(2))


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_loop_entered_by_the_start_of_a_summary_alone_is_named_from_that_summary() -> None:
    # S spans C, C precedes X, X precedes S: the loop leaves S by its subordinate, never by its
    # finish, and is named from S, first in the order of the plan.
    tasks = [task(1), task(2, parent=1), task(3)]
    with pytest.raises(LinkCycleError) as refused:
        planned(tasks, [link(2, 3), link(3, 1)])
    assert refused.value.cycle == (ident(1), ident(2), ident(3))


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_move_names_the_loop_from_a_subordinate_moved_to_the_summary_received() -> None:
    # M moved under P, M precedes Q, Q precedes P: the chain from M left at its finish to P
    # entered at its start; a loop that does not pass the task entered is the structure's.
    tasks = [task(1), task(2, parent=1), task(3)]
    structure = Structure(tuple(tasks), (link(2, 3), link(3, 1)), MONDAY, CONSTANTS)
    with pytest.raises(LinkCycleError) as moved:
        schedule(structure, Move((ident(2),), ident(1)))
    assert moved.value.cycle == (ident(2), ident(3), ident(1))
    with pytest.raises(LinkCycleError) as entered:
        schedule(structure, Entry(ident(2)))
    assert entered.value.cycle == (ident(1), ident(2), ident(3))


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_link_to_or_from_a_summary_binds_each_of_its_subordinates() -> None:
    # What precedes a summary precedes its subordinates, what follows it follows them; a percent
    # of a summary is a share of its work between its dates.
    tasks = [task(1, "2"), task(2), task(3, "1", parent=2), task(4, "3", parent=2), task(5)]
    dated = planned(tasks, [link(1, 2), link(2, 5, lag="50", unit="percent")])
    assert (of(dated, 3).start, of(dated, 4).start) == (day(2), day(2))
    assert (of(dated, 2).start, of(dated, 2).finish) == (day(2), day(4, 8))
    assert of(dated, 2).work_hours == Decimal(24)
    assert of(dated, 5).start == day(8, 4)
    assert of(dated, 3).total_float == Decimal(2)
    assert of(dated, 2).total_float == Decimal(0)


@pytest.mark.requirement("WF-PLA-0030-A")
def test_a_milestone_sits_where_its_predecessor_finishes_or_where_its_day_starts() -> None:
    tasks = [task(1, "5"), task(2, "0"), task(3, "0")]
    dated = planned(tasks, [link(1, 2), link(1, 3, "start_to_start")])
    assert (of(dated, 2).start, of(dated, 2).finish) == (day(4, 8), day(4, 8))
    assert of(dated, 3).start == day(0)


@pytest.mark.requirement("WF-PLA-0030-A")
def test_an_elapsed_lead_ending_after_the_hours_of_a_day_starts_its_successor_the_next() -> None:
    # Ten elapsed hours before the Wednesday's fourth hour are the Tuesday's eighteenth: past its
    # hours of work, the successor starts on the Wednesday.
    tasks = [task(1, "2.5"), task(2)]
    dated = planned(tasks, [link(1, 2, lag="-10", unit="eh")])
    assert of(dated, 2).start == day(2)


# --- WF-PLA-0100: the critical path ------------------------------------------------------------


def two_branches(short: str) -> Schedule:
    """Return two parallel branches from the planning start: 4 then 6 days, and two of ``short``."""
    tasks = [task(1, "4"), task(2, "6"), task(3, short), task(4, short)]
    return planned(tasks, [link(1, 2), link(3, 4)])


@pytest.mark.requirement("WF-PLA-0100-A")
def test_the_longest_of_two_branches_is_critical_and_the_other_floats_by_their_difference() -> None:
    # « Sur un planning à deux branches parallèles de durées différentes, la branche la plus longue
    # est critique et l'autre porte une marge égale à leur écart. »
    dated = two_branches("3")
    assert [(of(dated, n).total_float, of(dated, n).is_critical) for n in (1, 2)] == [
        (Decimal(0), True),
        (Decimal(0), True),
    ]
    assert [(of(dated, n).total_float, of(dated, n).is_critical) for n in (3, 4)] == [
        (Decimal(4), False),
        (Decimal(4), False),
    ]


@pytest.mark.requirement("WF-PLA-0100-A")
def test_lengthening_the_short_branch_beyond_its_float_makes_it_critical() -> None:
    # « Allonger une tâche de la branche courte au-delà de sa marge la rend critique à son tour. »
    dated = two_branches("5.5")
    assert [of(dated, n).is_critical for n in (3, 4)] == [True, True]
    assert [of(dated, n).total_float for n in (1, 2)] == [Decimal(1), Decimal(1)]


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_manual_task_bears_no_float_and_its_successors_float_from_its_dates() -> None:
    # « Une tâche en mode manuel n'affiche aucune marge et n'apparaît jamais sur le chemin
    # critique, alors que ses successeurs automatiques voient leurs marges calculées à partir de ses
    # dates. »
    tasks = [task(1, manual=(day(2), day(3, 8))), task(2, "2"), task(3, "10")]
    dated = planned(tasks, [link(1, 2)])
    assert (of(dated, 1).total_float, of(dated, 1).is_critical) == (None, False)
    assert (of(dated, 2).start, of(dated, 2).finish) == (day(4), day(7, 8))
    assert of(dated, 2).total_float == Decimal(4)


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_predecessor_unable_to_finish_before_a_manual_task_floats_negative_and_is_signalled() -> (
    None
):
    # « Un prédécesseur automatique qui ne peut pas finir avant le début d'une tâche manuelle porte
    # une marge négative, apparaît sur le chemin critique et est signalé. »
    tasks = [task(1, "5"), task(2, manual=(day(3), day(4, 8)))]
    dated = planned(tasks, [link(1, 2)])
    conflict = LinkConflict(ident(1), ident(2), "finish_to_start")
    assert (of(dated, 1).total_float, of(dated, 1).is_critical) == (Decimal(-2), True)
    assert of(dated, 1).link_conflicts == of(dated, 2).link_conflicts == (conflict,)
    assert dated.link_conflicts == (conflict,)
    assert of(dated, 2).total_float is None


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_summary_of_a_critical_subordinate_is_critical_with_its_float() -> None:
    # « Une récapitulative dont une subordonnée est critique est critique et affiche la marge de
    # cette subordonnée, nulle ou négative. »
    tasks = [
        task(1),
        task(2, "5", parent=1),
        task(3, parent=1),
        task(4, manual=(day(3), day(4, 8))),
    ]
    tasks += [task(5), task(6, "2", parent=5), task(7, "1", parent=5)]
    dated = planned(tasks, [link(2, 4)])
    assert (of(dated, 1).total_float, of(dated, 1).is_critical) == (Decimal(-2), True)
    assert of(dated, 3).total_float == Decimal(4)
    assert (of(dated, 5).total_float, of(dated, 5).is_critical) == (Decimal(3), False)
    nil = planned([task(1), task(2, "4", parent=1), task(3, "1", parent=1)])
    assert (of(nil, 1).total_float, of(nil, 1).is_critical) == (Decimal(0), True)
    manual = planned([task(1), task(2, parent=1, manual=(day(0), day(0, 8)))])
    assert (of(manual, 1).total_float, of(manual, 1).is_critical) == (None, False)


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_predecessor_start_to_start_that_cannot_start_before_a_manual_task_is_signalled() -> None:
    # « Un prédécesseur lié début à début à une tâche manuelle, et qui ne peut pas commencer avant
    # elle, porte une marge négative et est signalé. »
    tasks = [task(1, "5"), task(2, "2"), task(3, manual=(day(2), day(4, 8)))]
    dated = planned(tasks, [link(1, 2), link(2, 3, "start_to_start")])
    assert of(dated, 2).start == day(7)
    assert (of(dated, 2).total_float, of(dated, 2).is_critical) == (Decimal(-3), True)
    conflict = LinkConflict(ident(2), ident(3), "start_to_start")
    assert of(dated, 2).link_conflicts == of(dated, 3).link_conflicts == (conflict,)
    assert of(dated, 1).total_float == Decimal(-3)


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_float_on_a_calendar_of_four_hours_is_in_days_of_the_installation() -> None:
    # Four hours on four a day beside five days on eight: the task may finish on the Friday,
    # sixteen hours of its calendar later, four of its days, rendered as two of eight hours.
    dated = planned([task(1, "5"), task(2, "4 h", calendar=FOUR_HOURS)])
    assert of(dated, 2).finish == day(0, 4)
    assert of(dated, 2).total_float == Decimal(2)


@pytest.mark.requirement("WF-PLA-0100-A")
def test_three_tasks_of_twenty_minutes_against_one_of_sixty_are_both_critical() -> None:
    # Both branches last an hour exactly: the chain's float is nil, not a remainder of a third.
    tasks = [task(1, "20 min"), task(2, "20 min"), task(3, "20 min"), task(4, "60 min")]
    dated = planned(tasks, [link(1, 2), link(2, 3)])
    assert of(dated, 3).finish == of(dated, 4).finish == day(0, 1)
    assert [(of(dated, n).total_float, of(dated, n).is_critical) for n in (1, 2, 3, 4)] == [
        (Decimal(0), True)
    ] * 4


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_chain_of_minutes_reaching_a_manual_task_exactly_is_no_conflict() -> None:
    # Three tasks of forty minutes finish at the Monday's second hour, where a manual task starts.
    tasks = [task(1, "40 min"), task(2, "40 min"), task(3, "40 min")]
    tasks.append(task(4, manual=(day(0, 2), day(0, 8))))
    dated = planned(tasks, [link(1, 2), link(2, 3), link(3, 4)])
    assert of(dated, 3).finish == day(0, 2)
    assert dated.link_conflicts == ()
    assert (of(dated, 3).total_float, of(dated, 3).is_critical) == (Decimal(0), True)


@pytest.mark.requirement("WF-PLA-0100-A")
def test_a_predecessor_on_another_calendar_floats_by_its_own_hours_and_not_its_successors() -> None:
    # A, sixteen hours on eight a day, finishes on the Tuesday at 8; B, four hours on four a day,
    # follows it on the Wednesday: no conflict. Their latest dates are read each on its calendar.
    alone = planned([task(1, "16 h"), task(2, "4 h", calendar=FOUR_HOURS)], [link(1, 2)])
    assert (of(alone, 1).finish, of(alone, 2).start) == (day(1, 8), day(2))
    assert [(of(alone, n).total_float, of(alone, n).is_critical) for n in (1, 2)] == [
        (Decimal(0), True),
        (Decimal(0), True),
    ]
    # Beside a branch of five days, both may slip two working days: A finishing on the Thursday,
    # B on the Friday. A's float is sixteen hours, B's eight, each in days of eight hours.
    tasks = [task(1, "16 h"), task(2, "4 h", calendar=FOUR_HOURS), task(3, "5")]
    beside = planned(tasks, [link(1, 2)])
    assert [(of(beside, n).total_float, of(beside, n).is_critical) for n in (1, 2)] == [
        (Decimal(2), False),
        (Decimal(1), False),
    ]


@pytest.mark.requirement("WF-PLA-0100-A")
@pytest.mark.parametrize(
    ("link_type", "lag", "floats"),
    [
        ("finish_to_finish", "1", Decimal(1)),
        ("start_to_finish", "3", Decimal(1)),
        ("finish_to_start", "1", Decimal(-1)),
    ],
)
def test_a_manual_task_bounds_its_predecessor_by_the_type_of_their_link(
    link_type: LinkType, lag: str, floats: Decimal
) -> None:
    # A predecessor of two days, before a manual task from the Wednesday to the Thursday.
    tasks = [task(1, "2"), task(2, manual=(day(2), day(3, 8)))]
    dated = planned(tasks, [link(1, 2, link_type, lag)])
    assert of(dated, 1).total_float == floats
    assert bool(dated.link_conflicts) is (floats < 0)


# --- The horizon, the calendar, what the engine is given ---------------------------------------


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_project_finishing_fifteen_years_and_a_day_after_its_start_is_beyond_its_horizon() -> (
    None
):
    # « Le déplacement d'une tâche qui porterait la fin du projet à quinze ans et un jour de son
    # début est refusé, et la tâche est nommée. »
    last = date(2041, 3, 2)
    within = planned([task(1), task(2, manual=(WorkInstant(last), WorkInstant(last, Decimal(8))))])
    assert within.horizon_exceeded_by is None
    assert of(within, 2).finish.day == last
    later = last + timedelta(days=1)
    beyond = planned(
        [task(1), task(2, manual=(WorkInstant(later), WorkInstant(later, Decimal(8))))]
    )
    assert (beyond.horizon_exceeded_by, dict(beyond.tasks)) == (ident(2), {})
    assert planned([task(1, "200000 mo")]).horizon_exceeded_by == ident(1)
    assert horizon_of(date(2028, 2, 29)) == date(2043, 2, 28)
    assert horizon_of(date(9990, 1, 1)) is None


@pytest.mark.requirement("WF-PLA-0150-A")
def test_a_task_led_before_the_first_day_a_date_holds_is_refused_as_beyond_the_horizon() -> None:
    # From the first Monday of the year 1, a lead of ten days would start the successor before
    # it: the structure is refused, naming the task that finishes last.
    first = date(1, 1, 1)
    tasks = (task(1, "2"), task(2))
    structure = Structure(tasks, (link(1, 2, lag="-10"),), first, CONSTANTS)
    assert schedule(structure).horizon_exceeded_by == ident(1)
    assert schedule(Structure(tasks, (link(1, 2),), first, CONSTANTS)).horizon_exceeded_by is None


@pytest.mark.requirement("WF-PLA-0020-A")
def test_a_task_without_predecessor_starts_at_the_first_hour_of_work_from_the_planning_start() -> (
    None
):
    saturday = MONDAY - timedelta(days=2)
    structure = Structure((task(1),), (), saturday, CONSTANTS)
    assert of(schedule(structure), 1).start == day(0)
    assert EIGHT_HOURS.next_working_day(saturday) == MONDAY
    with pytest.raises(ValueError, match="no hour of work"):
        hours_of_week(0, 0, 0, 0, 0, 0, 0).next_working_day(saturday)


@pytest.mark.requirement("WF-PLA-0020-A")
def test_an_empty_structure_has_no_date_and_a_manual_task_needs_both_of_its_own() -> None:
    assert planned([]) == Schedule({}, ())
    undated = Task(ident(1), None, "manual", Duration(Decimal(1), "d"), EIGHT_HOURS)
    with pytest.raises(ValueError, match="manual mode without its dates"):
        planned([undated])
