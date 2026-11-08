# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reader of a planning of MS Project: an MSPDI file into the model, without a database.

It reads what an import of MS Project uses (EP-06, "Le format MS Project") — the project's start
and unit constants, its calendars, its tasks and their links — and counts by kind what the file
carries besides and no import reads (``ImportReport.ignored``, WF-INTF-0040). A file it cannot
read raises ``UnreadableProjectError``, which the format turns into its refusal: not well formed,
not a ``Project`` of MSPDI, a value that is not of its type, a tree whose outline levels skip one,
two tasks of one unique identifier, a link to a task the file does not carry.
"""

import re
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.planning.msproject.model import (
    CONSTRAINT_TYPES,
    DATE_CONSTRAINTS,
    ESTIMATED,
    FORMAT_UNITS,
    LINEAGE_ALIAS,
    LINEAGE_FIELD_ID,
    LINK_TYPES,
    NO_FORMAT,
    Ignored,
    MsCalendar,
    MsProject,
    MsTask,
    PredecessorLink,
    ReadProject,
    UnreadableProjectError,
    WorkingDay,
)
from waterfall.core.planning.msproject.tree import parse

if TYPE_CHECKING:
    from waterfall.core.planning.msproject.tree import Tag
    from waterfall.core.planning.scheduling import DurationUnit, LagUnit

# An ``xsd:duration`` as MS Project writes one — ``PT16H0M0S`` —, days allowed, years and months
# not: their length is not fixed.
DURATION = re.compile(
    r"P(?:(?P<D>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<H>\d+(?:\.\d+)?)H)?(?:(?P<M>\d+(?:\.\d+)?)M)?(?:(?P<S>\d+(?:\.\d+)?)S)?)?"
)
INTEGER = re.compile(r"-?[0-9]+")
MICROSECONDS = {"D": 86_400_000_000, "H": 3_600_000_000, "M": 60_000_000, "S": 1_000_000}

# The calendar a task does not have: MS Project writes ``-1`` for it, and for a calendar without
# a base.
NO_CALENDAR = -1

# The task of unique identifier 0 is the summary of the project, which MS Project writes and makes
# again; the resource of unique identifier 0 is its "unassigned" one. Neither is the user's.
PROJECT_SUMMARY_UID = 0


def read_project(content: bytes) -> ReadProject:
    """Read a planning of MS Project, and what it carries besides, from its MSPDI file."""
    root = parse(content)
    lineage_field = _lineage_field(root)
    tasks = tuple(_task(element, lineage_field) for element in _users(root, "Tasks", "Task"))
    _check_tree(tasks)
    project = MsProject(
        start=_datetime(root, "StartDate"),
        name=root.text_of("Name"),
        currency_code=root.text_of("CurrencyCode"),
        calendar_uid=_calendar_uid(root, "CalendarUID"),
        minutes_per_day=_integer(root, "MinutesPerDay"),
        minutes_per_week=_integer(root, "MinutesPerWeek"),
        days_per_month=_integer(root, "DaysPerMonth"),
        calendars=tuple(_calendar(element) for element in _every(root, "Calendars", "Calendar")),
        tasks=tasks,
    )
    return ReadProject(project, _ignored(root, project))


def _every(root: Tag, collection: str, name: str) -> list[Tag]:
    """Return the elements of a collection of the project, none without it."""
    parent = root.child(collection)
    return [] if parent is None else parent.every(name)


def _users(root: Tag, collection: str, name: str) -> list[Tag]:
    """Return the tasks or the resources of the user: neither blank rows nor MS Project's own."""
    return [
        element
        for element in _every(root, collection, name)
        if not _boolean(element, "IsNull") and _integer(element, "UID") != PROJECT_SUMMARY_UID
    ]


def _value(element: Tag, name: str) -> str | None:
    """Return the text of a child, stripped, ``None`` for an absent or empty one."""
    text = element.text_of(name)
    return text.strip() or None if text is not None else None


def _integer(element: Tag, name: str) -> int | None:
    """Return a child read as an integer."""
    value = _value(element, name)
    if value is None:
        return None
    # ``int()`` would take ``1_0`` and the digits of other scripts: an integer of the schema is
    # an optional minus and ASCII digits.
    if INTEGER.fullmatch(value) is None:
        raise UnreadableProjectError(name)
    return int(value)


def _required(element: Tag, name: str) -> int:
    """Return a child read as an integer the schema requires."""
    value = _integer(element, name)
    if value is None:
        raise UnreadableProjectError(name)
    return value


def _boolean(element: Tag, name: str) -> bool:
    """Return a child read as a boolean of the schema, false when absent."""
    value = _value(element, name)
    if value in {None, "0", "false"}:
        return False
    if value in {"1", "true"}:
        return True
    raise UnreadableProjectError(name)


def _decimal(element: Tag, name: str) -> Decimal:
    """Return a child read as a finite number, nought when absent (``NaN``, infinity: refused)."""
    value = _value(element, name)
    try:
        number = Decimal(value or 0)
    except InvalidOperation as error:
        raise UnreadableProjectError(name) from error
    if not number.is_finite():
        raise UnreadableProjectError(name)
    return number


def _datetime(element: Tag, name: str) -> datetime | None:
    """Return a child read as a date and an hour of the wall clock of the project.

    The date is naive, as the model promises: one that carries a time zone (``Z``, ``+02:00``) is
    refused, MSPDI having none.
    """
    value = _value(element, name)
    if value is None:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as error:
        raise UnreadableProjectError(name) from error
    if moment.tzinfo is not None:
        raise UnreadableProjectError(name)
    return moment


def _time(element: Tag, name: str) -> time:
    """Return a child read as an hour of the day."""
    value = _value(element, name)
    try:
        return time.fromisoformat(value or "")
    except ValueError as error:
        raise UnreadableProjectError(name) from error


def _calendar_uid(element: Tag, name: str) -> int | None:
    """Return a child read as the unique identifier of a calendar, ``None`` for none."""
    value = _integer(element, name)
    return None if value == NO_CALENDAR else value


def _duration(element: Tag, name: str) -> timedelta | None:
    """Return a child read as an ``xsd:duration``, in exact microseconds."""
    value = _value(element, name)
    if value is None:
        return None
    match = DURATION.fullmatch(value)
    if match is None or value.endswith(("P", "T")):
        raise UnreadableProjectError(name)
    microseconds = sum(
        Decimal(amount) * MICROSECONDS[part] for part, amount in match.groupdict().items() if amount
    )
    return timedelta(microseconds=int(microseconds))


def _unit(element: Tag, name: str) -> LagUnit | None:
    """Return the unit a format says, estimated or not; ``None`` for a format that says none."""
    code = _integer(element, name)
    if code is None or code in NO_FORMAT:
        return None
    unit = FORMAT_UNITS.get(code) or FORMAT_UNITS.get(code - ESTIMATED)
    if unit is None:
        raise UnreadableProjectError(name)
    return unit


def _duration_unit(element: Tag) -> DurationUnit | None:
    """Return the unit of the duration of a task: a task has no duration in percent."""
    unit = _unit(element, "DurationFormat")
    if unit == "percent":
        raise UnreadableProjectError(element="DurationFormat")
    return unit


def _code[T](element: Tag, name: str, codes: tuple[T, ...], absent: int) -> T:
    """Return the member of an enumeration of the schema that a child gives by its position."""
    code = _integer(element, name)
    code = absent if code is None else code
    if not 0 <= code < len(codes):
        raise UnreadableProjectError(name)
    return codes[code]


def _lineage_field(root: Tag) -> str | None:
    """Return the identifier of the custom field the export writes the lineage in, if defined."""
    for definition in _every(root, "ExtendedAttributes", "ExtendedAttribute"):
        if _value(definition, "Alias") == LINEAGE_ALIAS:
            return _value(definition, "FieldID")
    return None


def _lineage(element: Tag, lineage_field: str | None) -> UUID | None:
    """Return the lineage of a task: its custom field of the export, else its ``GUID``.

    The field is found by the alias the file defines, and by the identifier of the export's field
    too, so that a lineage survives an alias the user renamed in MS Project.

    A value that is not an identifier, typed by hand in MS Project, is no lineage: the task is
    matched as one the file creates.
    """
    values = [
        _value(attribute, "Value")
        for attribute in element.every("ExtendedAttribute")
        if _value(attribute, "FieldID") in {lineage_field, LINEAGE_FIELD_ID}
    ]
    for value in [*values, _value(element, "GUID")]:
        if value is not None:
            try:
                return UUID(value)
            except ValueError:
                continue
    return None


def _link(element: Tag) -> PredecessorLink:
    """Read a link of a task to its predecessor."""
    return PredecessorLink(
        predecessor_uid=_required(element, "PredecessorUID"),
        # A link without a type is finish to start, MS Project's default.
        link_type=_code(element, "Type", LINK_TYPES, absent=1),
        lag=_integer(element, "LinkLag") or 0,
        lag_unit=_unit(element, "LagFormat"),
    )


def _task(element: Tag, lineage_field: str | None) -> MsTask:
    """Read a task, its links and its lineage."""
    return MsTask(
        uid=_required(element, "UID"),
        name=element.text_of("Name") or "",
        outline_level=_required(element, "OutlineLevel"),
        manual=_boolean(element, "Manual"),
        duration=_duration(element, "Duration"),
        duration_unit=_duration_unit(element),
        start=_datetime(element, "Start"),
        finish=_datetime(element, "Finish"),
        milestone=_boolean(element, "Milestone"),
        constraint=_code(element, "ConstraintType", CONSTRAINT_TYPES, absent=0),
        calendar_uid=_calendar_uid(element, "CalendarUID"),
        constraint_date=_datetime(element, "ConstraintDate"),
        notes=element.text_of("Notes"),
        lineage=_lineage(element, lineage_field),
        predecessors=tuple(_link(link) for link in element.every("PredecessorLink")),
    )


def _check_tree(tasks: tuple[MsTask, ...]) -> None:
    """Refuse a tree whose levels skip one, a unique identifier twice, a link to no task."""
    level = 0
    for task in tasks:
        if not 1 <= task.outline_level <= level + 1:
            raise UnreadableProjectError(element="OutlineLevel")
        level = task.outline_level
    uids = {task.uid for task in tasks}
    if len(uids) != len(tasks):
        raise UnreadableProjectError(element="UID")
    if any(link.predecessor_uid not in uids for task in tasks for link in task.predecessors):
        raise UnreadableProjectError(element="PredecessorUID")


def _day(element: Tag) -> WorkingDay:
    """Read a day of the week of a calendar and its working times."""
    times = element.child("WorkingTimes")
    return WorkingDay(
        day_type=_required(element, "DayType"),
        working=_boolean(element, "DayWorking"),
        times=tuple(
            (_time(period, "FromTime"), _time(period, "ToTime"))
            for period in ([] if times is None else times.every("WorkingTime"))
        ),
    )


def _calendar(element: Tag) -> MsCalendar:
    """Read a calendar and the days of the week it sets.

    A ``WeekDay`` of type 0 is an exception of an older MS Project, which Waterfall does not know
    (WF-REF-0110): it is not a day of the week.
    """
    return MsCalendar(
        uid=_required(element, "UID"),
        name=element.text_of("Name"),
        is_base=_boolean(element, "IsBaseCalendar"),
        base_uid=_calendar_uid(element, "BaseCalendarUID"),
        days=tuple(
            _day(day) for day in _every(element, "WeekDays", "WeekDay") if _required(day, "DayType")
        ),
    )


def _named(*names: str | None) -> tuple[str, ...]:
    """Return the names of what has one, in order."""
    return tuple(name for name in names if name)


def _ignored(root: Tag, project: MsProject) -> tuple[Ignored, ...]:
    """Count by kind what the file carries and no import reads, in the order of the contract.

    The resources and the calendars are Waterfall's alone; an assignment is of a resource, and
    goes with it. A custom field is any but the one the lineage travels in. Progress and costs are
    counted on the tasks without children only: MS Project accumulates them on a summary from its
    children, which would count twice what is one.
    """
    resources = _users(root, "Resources", "Resource")
    tasks = _users(root, "Tasks", "Task")
    fields = [
        element
        for element in _every(root, "ExtendedAttributes", "ExtendedAttribute")
        if _value(element, "Alias") != LINEAGE_ALIAS
    ]
    summaries = {uid for uid in project.parents().values() if uid is not None}
    leaves = [task for task in tasks if _required(task, "UID") not in summaries]
    constrained = [task for task in project.tasks if task.constraint in DATE_CONSTRAINTS]
    kinds = (
        Ignored("resources", len(resources), _named(*(r.text_of("Name") for r in resources))),
        Ignored(
            "calendars",
            len(project.calendars),
            _named(*(calendar.name for calendar in project.calendars)),
        ),
        Ignored("progress", sum(_decimal(task, "PercentComplete") > 0 for task in leaves)),
        Ignored(
            "costs",
            sum(_decimal(task, "FixedCost") != 0 or _decimal(task, "Cost") != 0 for task in leaves),
        ),
        Ignored(
            "custom_fields",
            len(fields),
            _named(*(_value(f, "Alias") or _value(f, "FieldName") for f in fields)),
        ),
        Ignored("date_constraints", len(constrained), _named(*(t.name for t in constrained))),
    )
    return tuple(kind for kind in kinds if kind.count)
