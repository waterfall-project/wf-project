# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a write of a task sends, and how it is judged, private to the module (WF-PLA-0020).

The facet sent at the creation of a task (``TaskFacetWrite``) or at its modification
(``TaskFacetUpdate``): a modification changes only what it sends (WF-IHM-0040). A date is sent
alone or with its hours: without them, the start begins its day and the finish ends the hours the
calendar of the task grants that day; a day without any is refused, naming the next working one;
hours outside the day are refused, the bound crossed named (``WorkInstantWrite``, #1244, #1769).

The dates are a manual task's to enter (WF-PLA-0020): those of an automatic task are computed
(``COMPUTED_VALUE``), those of a summary derived from its subordinates (``SUMMARY_TASK_DERIVED``),
whose mode and duration are computed too (WF-PLA-0040); a milestone has no duration to enter
(``FIELD_NOT_ACCEPTED``, WF-PLA-0050). Every refusal of a body is named at once (422).

The duration of a manual task follows its dates: dates entered give it the work between them, in
days; a duration entered alone moves its finish from its start, on its calendar.
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from waterfall.core.planning.dating import duration_of, horizon_exceeded, in_days
from waterfall.core.planning.scheduling import Duration, Moment, WorkInstant
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, UnprocessableError

# The code of the 403 for a permission missing (the planning does not import the access roles).
PERMISSION_MISSING = "PERMISSION_MISSING"

# The permissions of the three grids, in the order of ``StructureCommand``: a write of the tree
# they make alike asks for one at least of them (#2601), the first named when none is held. One
# list for the routes and the planning, so that the 403 names the same permission in both.
PLANNING_WRITE = "planning.write"
ESTIMATE_WRITE = "estimate.write"
REMAINING_WRITE = "remaining.write"
ENTRIES = (PLANNING_WRITE, ESTIMATE_WRITE, REMAINING_WRITE)

if TYPE_CHECKING:
    from waterfall.core.planning.interface.nodes import InstantSent, TaskEntry
    from waterfall.core.planning.scheduling import Calendar, UnitConstants
    from waterfall.core.planning.tables import Task
    from waterfall.core.planning.tree import Tree

VALUE_REQUIRED = "VALUE_REQUIRED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
NON_WORKING_DAY = "NON_WORKING_DAY"
COMPUTED_VALUE = "COMPUTED_VALUE"
SUMMARY_TASK_DERIVED = "SUMMARY_TASK_DERIVED"
FIELD_NOT_ACCEPTED = "FIELD_NOT_ACCEPTED"
AUTOMATIC = "automatic"
MANUAL = "manual"
# A task created without a duration lasts a day (WF-DEV-0050, WF-RAE-0040).
ONE_DAY = Duration(Decimal(1), "d")


def decimal_text(value: Decimal) -> str:
    """Give a decimal as the contract writes it: without exponent nor trailing zeros."""
    return format(value.normalize(), "f")


@dataclass(frozen=True, slots=True)
class Facet:
    """What a write leaves of the time of a task: its mode, its duration, its manual dates."""

    scheduling_mode: str
    duration: Duration
    start: WorkInstant | None
    finish: WorkInstant | None


def _instant(
    sent: InstantSent, calendar: Calendar, pointer: str, *, finish: bool
) -> tuple[WorkInstant | None, list[FieldError]]:
    """Judge a date sent on the calendar of its task, and complete its hours."""
    day_hours = calendar.hours_on(sent.day)
    if day_hours <= 0:
        try:
            following = calendar.next_working_day(sent.day).isoformat()
        except ValueError:
            following = None
        params = {"date": sent.day.isoformat(), "next_working_day": following}
        return None, [FieldError(f"{pointer}/date", NON_WORKING_DAY, params)]
    hours = sent.hours
    if hours is None:
        return WorkInstant(sent.day, day_hours if finish else Decimal(0)), []
    if hours < 0:
        return None, [FieldError(f"{pointer}/hours", VALUE_OUT_OF_RANGE, {"minimum": "0"})]
    if hours > day_hours:
        bound = {"maximum": decimal_text(day_hours)}
        return None, [FieldError(f"{pointer}/hours", VALUE_OUT_OF_RANGE, bound)]
    return WorkInstant(sent.day, hours), []


def _duration(duration: Duration | None, pointer: str) -> list[FieldError]:
    """Refuse a duration missing or negative: a task's is never (WF-PLA-0050, WF-PLA-0160)."""
    if duration is None:
        return [FieldError(pointer, VALUE_REQUIRED)]
    if duration.value < 0:
        return [FieldError(f"{pointer}/value", VALUE_OUT_OF_RANGE, {"minimum": "0"})]
    return []


def _ordered(start: WorkInstant, finish: WorkInstant, pointer: str) -> list[FieldError]:
    """Refuse a finish before its start, the start named."""
    if finish < start:
        return [
            FieldError(f"{pointer}/date", VALUE_OUT_OF_RANGE, {"minimum": start.day.isoformat()})
        ]
    return []


def finish_after(
    start: WorkInstant, duration: Duration, calendar: Calendar, constants: UnitConstants
) -> WorkInstant:
    """Give the finish of a manual task that lasts a duration from its start (WF-PLA-0160).

    In units of work, on its calendar, hour after hour; in elapsed units, without a calendar.
    """
    hours = duration.hours(constants)
    if hours == 0:
        return start
    origin = Moment.of(start)
    if duration.is_elapsed:
        return origin.elapsed(hours).instant()
    return calendar.moment(calendar.count(origin) + hours, finish=True).instant()


def _finish_within(
    task: Task, start: WorkInstant, duration: Duration, calendar: Calendar, constants: UnitConstants
) -> WorkInstant:
    """Give the finish a duration entered leads to, or refuse a task that leaves the calendar.

    A duration so long that its finish is no date is beyond the horizon (WF-PLA-0150): refused
    naming the task (422 ``PROJECT_HORIZON_EXCEEDED``), as the engine does for an automatic one.
    """
    try:
        return finish_after(start, duration, calendar, constants)
    except (ValueError, ArithmeticError) as error:
        raise horizon_exceeded(task.node_id, task.label) from error


def days_between(
    start: WorkInstant, finish: WorkInstant, calendar: Calendar, constants: UnitConstants
) -> Duration:
    """Give the work between two dates of a manual task on its calendar, in days."""
    return Duration(in_days(calendar.work_between(start, finish), constants), "d")


def _refuse(faults: list[FieldError]) -> None:
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))


def judged_creation(entry: TaskEntry, calendar: Calendar, constants: UnitConstants) -> Facet:
    """Judge the facet of a task created; give its mode, its duration and its manual dates.

    Without a mode or a duration, an automatic task of a day. A manual task needs both dates; an
    automatic one accepts none, its dates being computed. Pointers under ``/task``.
    """
    mode = entry.scheduling_mode or AUTOMATIC
    faults: list[FieldError] = []
    if entry.duration is not None:
        faults += _duration(entry.duration, "/task/duration")
    ends: dict[str, WorkInstant | None] = {}
    for end, sent in (("start", entry.start), ("finish", entry.finish)):
        pointer = f"/task/{end}"
        if mode == AUTOMATIC:
            if sent is not None:
                faults.append(FieldError(pointer, COMPUTED_VALUE))
        elif sent is None:
            faults.append(FieldError(pointer, VALUE_REQUIRED))
        else:
            ends[end], wrong = _instant(sent, calendar, pointer, finish=end == "finish")
            faults += wrong
    start, finish = ends.get("start"), ends.get("finish")
    if start is not None and finish is not None:
        faults += _ordered(start, finish, "/task/finish")
    _refuse(faults)
    duration = entry.duration or ONE_DAY
    if start is not None and finish is not None:
        duration = days_between(start, finish, calendar, constants)
    return Facet(mode, duration, start, finish)


def _derived(tree: Tree, task: Task, sent: frozenset[str]) -> list[FieldError]:
    """Refuse what a summary derives: its mode and its duration, its dates (WF-PLA-0040).

    A date sent names the direct subordinates it is drawn from (``SUMMARY_TASK_DERIVED``).
    """
    subordinates = [str(each) for each in tree.subtasks(task.node_id)]
    faults = [
        FieldError(f"/{name}", COMPUTED_VALUE)
        for name in ("scheduling_mode", "duration")
        if name in sent
    ]
    faults += [
        FieldError(f"/{end}", SUMMARY_TASK_DERIVED, {"subordinate_node_ids": subordinates})
        for end in ("start", "finish")
        if end in sent
    ]
    return faults


def _ends(
    entry: TaskEntry, mode: str, calendar: Calendar
) -> tuple[dict[str, WorkInstant], list[FieldError]]:
    """Judge the dates a modification sends: a manual task's alone are entered (WF-PLA-0020)."""
    ends: dict[str, WorkInstant] = {}
    faults: list[FieldError] = []
    for end, given in (("start", entry.start), ("finish", entry.finish)):
        if end not in entry.sent:
            continue
        if mode == AUTOMATIC:
            faults.append(FieldError(f"/{end}", COMPUTED_VALUE))
        elif given is None:
            faults.append(FieldError(f"/{end}", VALUE_REQUIRED))
        else:
            instant, wrong = _instant(given, calendar, f"/{end}", finish=end == "finish")
            faults += wrong
            if instant is not None:
                ends[end] = instant
    return ends, faults


def judged_change(
    tree: Tree, task: Task, entry: TaskEntry, calendar: Calendar, constants: UnitConstants
) -> Facet:
    """Judge what a modification sends of the time of a task; give what it leaves of it."""
    node_id, sent = task.node_id, entry.sent
    start = WorkInstant(task.start_date, task.start_hours)
    finish = WorkInstant(task.finish_date, task.finish_hours)
    current = Facet(task.scheduling_mode, duration_of(task), start, finish)
    if tree.is_summary(node_id):
        _refuse(_derived(tree, task, sent))
        return current
    faults: list[FieldError] = []
    if "scheduling_mode" in sent and entry.scheduling_mode is None:
        faults.append(FieldError("/scheduling_mode", VALUE_REQUIRED))
    mode = entry.scheduling_mode or current.scheduling_mode
    if "duration" in sent:
        if tree.is_milestone(node_id):
            faults.append(FieldError("/duration", FIELD_NOT_ACCEPTED))
        else:
            faults += _duration(entry.duration, "/duration")
    ends, wrong = _ends(entry, mode, calendar)
    _refuse(faults + wrong)
    duration = entry.duration if "duration" in sent and entry.duration else current.duration
    if mode == AUTOMATIC:
        return replace(current, scheduling_mode=AUTOMATIC, duration=duration)
    if ends:
        start, finish = ends.get("start", start), ends.get("finish", finish)
        _refuse(_ordered(start, finish, "/finish"))
        return Facet(MANUAL, days_between(start, finish, calendar, constants), start, finish)
    if "duration" in sent:
        finish = _finish_within(task, start, duration, calendar, constants)
        return Facet(MANUAL, duration, start, finish)
    return Facet(MANUAL, duration, start, finish)
