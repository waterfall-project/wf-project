# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The bounds of the reader of MS Project, and the calendar of a file that names none (US-3180).

Without a database: a hostile value of a file deposited — too many tasks, too deep a tree, an
integer or a duration no column nor ``timedelta`` holds — is refused by the reader, one test each,
as the refusal of the format; a planning at the bounds is read. A file of another tool than MS
Project, which names no calendar of its project or one it does not carry, is dated on the calendar
MS Project assumes. Their import, against the service, is in ``test_msproject_bounds_import.py``.
"""

import time
from datetime import datetime, timedelta

import pytest

from waterfall.core.planning.msproject import (
    STANDARD,
    MsProject,
    MsTask,
    UnreadableProjectError,
    calendar_of,
    calendars_of,
    read_project,
)
from waterfall.core.planning.tables import EXTERNAL_ID_LENGTH

pytestmark = pytest.mark.requirement("WF-INTF-0040-A")

NAMESPACE = "http://schemas.microsoft.com/project"


def task(uid: int | str, level: int = 1, besides: str = "") -> str:
    """Write a task of a file: its unique identifier, its outline level, and what is said."""
    return f"<Task><UID>{uid}</UID><OutlineLevel>{level}</OutlineLevel>{besides}</Task>"


def project(*tasks: str, besides: str = "") -> bytes:
    """Write a file of the tasks given, as another tool than MS Project may."""
    body = f"{besides}<Tasks>{''.join(tasks)}</Tasks>"
    return f'<Project xmlns="{NAMESPACE}">{body}</Project>'.encode()


def tasks_on_levels(count: int, levels: int) -> list[str]:
    """Write tasks going down the levels one by one, from the first to the deepest, and again."""
    return [task(uid, (uid - 1) % levels + 1) for uid in range(1, count + 1)]


def refused(content: bytes) -> str:
    """Read a file the reader refuses; name the element it refuses."""
    with pytest.raises(UnreadableProjectError) as refusal:
        read_project(content)
    return refusal.value.element


def test_a_planning_of_10_000_tasks_on_50_levels_is_read() -> None:
    # « Un planning de 10 000 tâches sur 50 niveaux est accepté. »
    started = time.monotonic()
    read = read_project(project(*tasks_on_levels(10_000, 50))).project
    assert len(read.tasks) == 10_000
    assert max(each.outline_level for each in read.tasks) == 50
    assert time.monotonic() - started < 10


def test_a_planning_of_more_than_10_000_tasks_is_refused_before_any_task_is_read() -> None:
    # « Au-delà de 10 000 tâches […], l'import échoue à l'analyse sur FILE_FORMAT_UNREADABLE. » The
    # tasks are counted before any is read: the last one, which no reader could read, is not.
    tasks = [*tasks_on_levels(10_000, 1), task(10_001, besides="<Duration>P1M</Duration>")]
    assert refused(project(*tasks)) == "Tasks"


def test_the_summary_of_the_project_and_the_blank_rows_are_no_tasks_of_the_bound() -> None:
    # MS Project writes the summary of the project (UID 0) and a blank row as tasks: they are not
    # the user's, and a planning of 10 000 tasks of the user saved by it is read.
    besides = [task(0, 0), "<Task><UID>99999</UID><IsNull>1</IsNull></Task>"]
    read = read_project(project(*besides, *tasks_on_levels(10_000, 1))).project
    assert len(read.tasks) == 10_000


def test_a_planning_of_more_than_50_levels_is_refused() -> None:
    # « Au-delà […] de 50 niveaux, l'import échoue à l'analyse » : the bound closes the recursion
    # of the engine through the summaries.
    assert refused(project(*tasks_on_levels(51, 51))) == "OutlineLevel"


@pytest.mark.parametrize(
    ("besides", "element"),
    [
        ("<MinutesPerDay>4800000000000000000</MinutesPerDay>", "MinutesPerDay"),
        ("<CalendarUID>-1000000000000000000</CalendarUID>", "CalendarUID"),
        ("<MinutesPerDay>0000000000000000480</MinutesPerDay>", "MinutesPerDay"),
    ],
)
def test_an_integer_of_more_than_18_digits_is_refused(besides: str, element: str) -> None:
    # « De même […] un entier au-delà de la borne de chiffres du lecteur. »
    assert refused(project(besides=besides)) == element


def test_an_integer_of_18_digits_is_read() -> None:
    # « De même […] un entier au-delà de la borne de chiffres du lecteur » : 18 digits are read,
    # positive on a constant of unit, negative on an identifier of calendar.
    read = read_project(project(besides="<MinutesPerDay>999999999999999999</MinutesPerDay>"))
    assert read.project.minutes_per_day == 999_999_999_999_999_999
    negative = read_project(project(besides="<CalendarUID>-999999999999999999</CalendarUID>"))
    assert negative.project.calendar_uid == -999_999_999_999_999_999


@pytest.mark.parametrize("element", ["MinutesPerDay", "MinutesPerWeek", "DaysPerMonth"])
@pytest.mark.parametrize("value", ["0", "-480"])
def test_a_constant_of_unit_that_is_not_positive_is_refused(element: str, value: str) -> None:
    # « et une constante d'unité — `MinutesPerDay`, `MinutesPerWeek`, `DaysPerMonth` — nulle ou »
    # (US-3180b, #4830): the conversions of the engine divide by the constants
    # of unit, so a zero or a negative one is refused at the reading, an unreadable format, never
    # an internal error of the analysis or of the application. No upper bound is added: the digits
    # of the reader are the bound.
    assert refused(project(besides=f"<{element}>{value}</{element}>")) == element


@pytest.mark.parametrize(
    ("element", "attribute"),
    [
        ("MinutesPerDay", "minutes_per_day"),
        ("MinutesPerWeek", "minutes_per_week"),
        ("DaysPerMonth", "days_per_month"),
    ],
)
def test_a_constant_of_unit_of_1_is_read(element: str, attribute: str) -> None:
    # The positive value next to the refused ones: the smallest constant of unit is read.
    read = read_project(project(besides=f"<{element}>1</{element}>"))
    assert getattr(read.project, attribute) == 1


@pytest.mark.parametrize(
    ("tasks", "element"),
    [
        ((task("1" * 19),), "UID"),
        ((task("9" * 300),), "UID"),
        (
            (
                task(1),
                task(
                    2,
                    besides="<PredecessorLink><PredecessorUID>1</PredecessorUID>"
                    f"<LinkLag>{'4' * 19}</LinkLag></PredecessorLink>",
                ),
            ),
            "LinkLag",
        ),
    ],
)
def test_a_unique_identifier_or_a_lag_beyond_the_digits_of_the_reader_is_refused(
    tasks: tuple[str, ...], element: str
) -> None:
    # « Dont un UID que external_id ne garderait pas » : refused at the reading, never at the
    # application, where the constraint ``external_id_length`` would have failed it.
    assert refused(project(*tasks)) == element


def test_the_largest_unique_identifier_read_is_kept_by_external_id() -> None:
    largest = -(10**18 - 1)
    read = read_project(project(task(largest))).project
    assert read.tasks[0].uid == largest
    assert len(str(read.tasks[0].uid)) <= EXTERNAL_ID_LENGTH


@pytest.mark.parametrize(
    ("duration", "element"),
    [
        ("<Duration>PT1000001H</Duration>", "Duration"),
        ("<Duration>PT1000000H0M1S</Duration>", "Duration"),
        ("<Duration>P41667D</Duration>", "Duration"),
        ("<Duration>PT60000001M</Duration>", "Duration"),
        (f"<Duration>PT{'9' * 5000}H</Duration>", "Duration"),
        (f"<Duration>PT{'9' * 5000}.5S</Duration>", "Duration"),
        (
            f"<Manual>1</Manual><ManualDuration>PT{'9' * 400}H</ManualDuration>",
            "ManualDuration",
        ),
    ],
)
def test_a_duration_of_more_than_a_million_hours_is_refused(duration: str, element: str) -> None:
    # « De même une durée que le lecteur ne peut pas porter (PT999…H). »
    assert refused(project(task(1, besides=duration))) == element


def test_a_duration_of_a_million_hours_is_read_and_one_of_thousands_of_decimals_too() -> None:
    read = read_project(
        project(
            task(1, besides="<Duration>PT1000000H</Duration>"),
            task(2, besides=f"<Duration>PT0.{'0' * 3000}1S</Duration>"),
        )
    ).project
    assert [each.duration for each in read.tasks] == [timedelta(hours=1_000_000), timedelta(0)]


TUESDAY = datetime.fromisoformat("2026-11-03T10:00:00")


def manual(calendar_uid: int | None = None) -> MsTask:
    """Give a manual task of a file, on the calendar given or on the project's."""
    return MsTask(uid=1, name="Revue", outline_level=1, manual=True, calendar_uid=calendar_uid)


@pytest.mark.parametrize("named", [None, 7], ids=["names-none", "names-one-absent"])
def test_a_file_without_the_calendar_of_its_project_is_dated_on_the_standard_one(
    named: int | None,
) -> None:
    # « Un fichier qui ne nomme pas le calendrier de son projet, ou qui nomme un calendrier qu'il
    # ne porte pas, se lit sur le calendrier « Standard » de MS Project » : from 8:00 to 12:00 and
    # from 13:00 to 17:00, ten o'clock the second hour of work of its day.
    planning = MsProject(start=None, calendar_uid=named, tasks=(manual(),))
    calendar = calendar_of(planning, calendars_of(planning), planning.tasks[0])
    assert calendar == STANDARD
    assert calendar.instant(TUESDAY).hours == 2


SAVED = """<Calendars><Calendar><UID>1</UID><Name>Long</Name><WeekDays>{}</WeekDays></Calendar>
</Calendars>""".format(
    "".join(
        f"<WeekDay><DayType>{day}</DayType><DayWorking>1</DayWorking><WorkingTimes><WorkingTime>"
        "<FromTime>06:00:00</FromTime><ToTime>18:00:00</ToTime></WorkingTime></WorkingTimes>"
        "</WeekDay>"
        for day in range(1, 8)
    )
)


def test_a_task_naming_a_calendar_the_file_does_not_carry_is_on_the_calendar_of_its_project() -> (
    None
):
    # As the calendar gap reads it: a task whose own calendar is not in the file has none of its
    # own, and is dated on the calendar of its project.
    content = project(
        task(1, besides="<Manual>1</Manual><CalendarUID>9</CalendarUID>"),
        besides=f"<CalendarUID>1</CalendarUID>{SAVED}",
    )
    planning = read_project(content).project
    calendars = calendars_of(planning)
    calendar = calendar_of(planning, calendars, planning.tasks[0])
    assert calendar == calendars[1]
    assert calendar.instant(TUESDAY).hours == 4
