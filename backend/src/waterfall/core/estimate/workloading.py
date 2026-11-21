# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of a project, by role, by task and by month, private to the module (US-1520).

The hours of the labour lines of a revision — a line's quantity times its hours — are spread over
the months of the task that bears them in proportion to the hours worked on the calendar of the
line's role (``spreading``). Three bases are offered: the budgeted load of the reference revision,
spread over the whole of each task; and the load of a marked revision, or of the current one, which
is the remaining to commit — the lines of a completed task count for nothing, and the load of the
others is spread over the part of the task that follows the date of calculation (the day for the
current revision, the day of the marking for a marked one), the whole falling on the month of that
date once the task is over. The portfolio reads a fourth, the estimate of an offer, which is its
whole load: each line whole over its task, on its own figures (``estimate_workload``, EP-11).

The roles listed are the active ones, with the roles the revision employs, deactivated or not,
restricted to the node asked and its descendants; each with its capacity in the reference. A month
whose hours exceed the capacity of its role is in alert (``WorkloadZone``), WF-DEV-0070.

Each line counts by its parts, rounded to the hundredth so that they sum to its hours (``parting``,
US-2040/L2): the hours of a task, of a role and a month, and the monthly totals are sums of parts
already rounded, so that the detail of a role sums, each month, to its load (WF-DEV-0090). Each role
details the tasks that bear its lines, two lines of a task counting as one, in the order of their
start, then of the plan (decision of the author of 2026-11-14, #3181); a task, as a role, has only
the months it loads (#3096). On a remaining, a completed task is not in the detail.

The roles, the calendars and the capacities of a marked revision are read on its images, which a
revision marked before US-1500 lacks: it reads the reference as it stands (#2627). Its plan and its
detail are computed when read, never kept by the marking (#3181).
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import category_label_of
from waterfall.core.estimate.imaging import KeptReference, KeptRole, kept_reference
from waterfall.core.estimate.parting import remaining_parts, rounded_parts, summed_parts
from waterfall.core.estimate.placing import Placed, placed_lines, placement_of, role_weeks
from waterfall.core.estimate.spreading import HOURS, Month, Placement
from waterfall.core.projects.interface import current_day, project_facts
from waterfall.core.resource_settings.interface import (
    Capacity,
    RoleFilters,
    RoleSort,
    RoleView,
    RoleWindow,
    list_roles,
    node_labels,
)
from waterfall.core.revisions.interface import read_revision, read_revision_for
from waterfall.platform.errors import (
    STATE_FORBIDS_OPERATION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    NotFoundError,
    UnprocessableError,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import WorkInstant
    from waterfall.core.projects.interface import Viewer

UNKNOWN_ORG_NODE = "UNKNOWN_ORG_NODE"
PROJECT_STATE = "ProjectState"
REVISION_POINTER = "/query/revision_id"
ORG_NODE_POINTER = "/query/org_node_id"
MARKED = "marked"
DRAFT = "draft"
NOUGHT = Decimal(0)
MONTHS_PER_YEAR = 12
# Every role the reference holds: a page no installation fills.
EVERY_ROLE = RoleWindow(limit=10**9, offset=0)


class WorkloadBasis(StrEnum):
    """Where the load of the labour lines is taken (``WorkloadBasis``)."""

    REFERENCE_BUDGET = "reference_budget"
    MARKED_REMAINING = "marked_remaining"
    CURRENT_REMAINING = "current_remaining"


@dataclass(frozen=True, slots=True)
class WorkloadAsked:
    """What a plan of workload asks: its basis, the marked revision named, the node, and when.

    ``now`` is the day of the calculation of the current revision; ``viewer`` reads the marked
    revision named.
    """

    basis: WorkloadBasis
    revision_id: UUID | None
    org_node_id: UUID | None
    now: datetime
    viewer: Viewer


@dataclass(frozen=True, slots=True)
class RoleMonth:
    """The hours a role is loaded in a month, and whether they exceed its capacity."""

    month: str
    hours: Decimal
    is_alert: bool


@dataclass(frozen=True, slots=True)
class TaskLoad:
    """A task of the detail of a role (``WorkloadTask``): its hours, and its months loaded in order.

    ``node_id`` is the node of the task, ``row_number`` its row in the whole structure.
    """

    node_id: UUID
    row_number: int
    label: str
    start: WorkInstant
    finish: WorkInstant
    hours: Decimal
    months: tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True, slots=True)
class RoleLoad:
    """A role with its capacity a month in the reference, its months loaded in order, its tasks."""

    resource_role_id: UUID
    label: str
    org_node_id: UUID
    capacity_monthly_hours: Decimal
    months: tuple[RoleMonth, ...]
    tasks: tuple[TaskLoad, ...]


@dataclass(frozen=True, slots=True)
class WorkloadView:
    """The plan of workload of a project (``WorkloadPlan``): its context, node, totals and roles."""

    revision_id: UUID
    revision_status: str
    computed_at: datetime
    is_stored: bool
    basis: WorkloadBasis
    org_node_id: UUID | None
    org_node_label: str | None
    monthly_totals: tuple[tuple[str, Decimal], ...]
    roles: tuple[RoleLoad, ...]


@dataclass(frozen=True, slots=True)
class Load:
    """The hours of a labour line to spread: its role, its task, the task as the line is worked on.

    ``task_id`` is the node of the task that bears the line.
    """

    role_id: UUID
    task_id: UUID
    hours: Decimal
    placement: Placement


@dataclass(frozen=True, slots=True)
class Reading:
    """The revision a basis reads, and what its load is counted from."""

    revision_id: UUID
    status: str
    computed_at: datetime
    is_stored: bool
    # The date after which the remaining is spread; none for the budgeted load of the reference.
    as_of: date | None


def _parts_of(load: Load, as_of: date | None) -> dict[Month, Decimal]:
    """Give the parts of a load: whole, or the remaining to commit after the day of calculation."""
    if as_of is None:
        return rounded_parts(load.placement, load.hours, HOURS)
    return remaining_parts(load.placement, load.hours, HOURS, as_of=as_of)


def spread_loads(
    loads: Iterable[Load], as_of: date | None
) -> dict[UUID, dict[UUID, dict[Month, Decimal]]]:
    """Give the hours of the loads by role, then by task, month by month.

    Pure. Each load by its parts rounded to the hundredth (``rounded_parts``), the loads of a task
    summed; the tasks of a role in the order of the loads, a task without hours with no month.
    """
    found: dict[UUID, dict[UUID, list[dict[Month, Decimal]]]] = {}
    for load in loads:
        positive = load.hours > 0
        parts = _parts_of(load, as_of) if positive else {}
        found.setdefault(load.role_id, {}).setdefault(load.task_id, []).append(parts)
    return {
        role_id: {task_id: summed_parts(each) for task_id, each in tasks.items()}
        for role_id, tasks in found.items()
    }


def label_of(month: Month) -> str:
    """Name a month as the contract does: ``2026-03``."""
    return f"{month.year:04d}-{month.month:02d}"


def month_after(month: Month) -> Month:
    """Give the month that follows."""
    index = month.year * MONTHS_PER_YEAR + month.month
    year, rest = divmod(index, MONTHS_PER_YEAR)
    return Month(year, rest + 1)


def monthly_totals(
    months_by_role: Iterable[Mapping[Month, Decimal]],
    nought: Decimal = NOUGHT,
) -> list[tuple[Month, Decimal]]:
    """Add up the hours of each month, from the first month loaded to the last, none left out.

    ``nought`` is the zero of a month that loads nothing, written as the amounts are (``0.00``).
    """
    sums: dict[Month, Decimal] = {}
    for months in months_by_role:
        for month, hours in months.items():
            sums[month] = sums.get(month, nought) + hours
    if not sums:
        return []
    found: list[tuple[Month, Decimal]] = []
    month, last = min(sums), max(sums)
    while month <= last:
        found.append((month, sums.get(month, nought)))
        month = month_after(month)
    return found


def _marked_reading(session: Session, project_id: UUID, asked: WorkloadAsked) -> Reading | None:
    """Read the marked revision named, or give none if there is none to read (422 follows)."""
    if asked.revision_id is None:
        return None
    try:
        view = read_revision(session, project_id, asked.revision_id, asked.viewer)
    except NotFoundError:
        return None
    if view.status != MARKED or view.marked_at is None:
        return None
    return Reading(
        view.revision_id, MARKED, view.marked_at, is_stored=True, as_of=current_day(view.marked_at)
    )


def _refuse_absent(state: str) -> ConflictError:
    """Refuse a basis the project does not have (409)."""
    return ConflictError(STATE_FORBIDS_OPERATION, {"state": state, "state_enum": PROJECT_STATE})


def reading_of(session: Session, project_id: UUID, asked: WorkloadAsked) -> Reading | None:
    """Choose the revision a basis reads; none for a marked revision that is not one.

    Refused (409) a basis the project does not have: the reference, or the current revision.
    """
    facts = project_facts(session, project_id)
    now = asked.now
    match asked.basis:
        case WorkloadBasis.REFERENCE_BUDGET:
            if facts.reference_revision_id is None:
                raise _refuse_absent(facts.state)
            return Reading(facts.reference_revision_id, MARKED, now, is_stored=False, as_of=None)
        case WorkloadBasis.CURRENT_REMAINING:
            if facts.current_revision_id is None:
                raise _refuse_absent(facts.state)
            return Reading(
                facts.current_revision_id, DRAFT, now, is_stored=False, as_of=current_day(now)
            )
        case WorkloadBasis.MARKED_REMAINING:
            return _marked_reading(session, project_id, asked)


def loads_of(
    placed: Iterable[Placed],
    placements: Mapping[UUID, Placement],
    *,
    reference: bool,
    remaining: bool,
) -> list[Load]:
    """Give the hours of the labour lines to spread, in the order of the tree.

    On the reference, the figures of the reference where the line holds them; on a remaining, the
    lines of a completed task are left out.
    """
    loads: list[Load] = []
    for each in placed:
        line = each.line
        if line.resource_role_id is None or line.hours is None:
            continue
        if remaining and each.is_completed:
            continue
        quantity, hours = line.quantity, line.hours
        if reference:
            quantity = quantity if line.reference_quantity is None else line.reference_quantity
            hours = hours if line.reference_hours is None else line.reference_hours
        placement = placements[line.node_id]
        loads.append(Load(line.resource_role_id, each.task_id, quantity * hours, placement))
    return loads


def _roles(
    session: Session,
    node_id: UUID | None,
    employed: Collection[UUID],
    kept: KeptReference | None = None,
) -> list[RoleView]:
    """Give the active roles and those employed, under the node asked and its descendants.

    A marked revision gives its ``kept`` images: the label and the capacity a role had at marking.
    """
    asked = RoleFilters(org_node_id=node_id, states=frozenset({True, False}))
    page = list_roles(session, asked, RoleSort(category_label_of), EVERY_ROLE, may_change=False)
    images = {} if kept is None else {each.resource_role_id: each for each in kept.resource_roles}
    roles = [role for role in page.roles if role.is_active or role.resource_role_id in employed]
    return [_as_kept(role, images.get(role.resource_role_id)) for role in roles]


def _as_kept(role: RoleView, image: KeptRole | None) -> RoleView:
    """Give a role with the label and the capacity its image keeps; as it stands without one."""
    if image is None:
        return role
    capacity = Capacity(image.monthly_hours, image.headcount)
    return replace(role, label=image.label, capacity=capacity)


def _task_of(bearer: Placed, months: Mapping[Month, Decimal]) -> TaskLoad:
    """Give a task of the detail of a role: what it is, its hours and its months in order."""
    task = bearer.task
    held = tuple((label_of(month), hours) for month, hours in sorted(months.items()))
    hours = sum(months.values(), NOUGHT)
    return TaskLoad(
        bearer.task_id, bearer.row_number, task.label, task.start, task.finish, hours, held
    )


def _started(task: TaskLoad) -> tuple[WorkInstant, int]:
    """Give what orders the tasks of a role: their start, then their row in the plan."""
    return task.start, task.row_number


def _load_of(
    role: RoleView,
    months: Mapping[Month, Decimal],
    tasks: Mapping[UUID, Mapping[Month, Decimal]],
    bearers: Mapping[UUID, Placed],
) -> RoleLoad:
    """Give a role with its months, in order, each in alert past its capacity, and its tasks."""
    capacity = role.capacity.monthly_hours
    held = tuple(
        RoleMonth(label_of(month), hours, hours > capacity)
        for month, hours in sorted(months.items())
    )
    detail = sorted((_task_of(bearers[key], each) for key, each in tasks.items()), key=_started)
    return RoleLoad(
        role.resource_role_id, role.label, role.org_node_id, capacity, held, tuple(detail)
    )


def read_workload(session: Session, project_id: UUID, asked: WorkloadAsked) -> WorkloadView:
    """Give the plan of workload of a project on a basis (``getProjectWorkload``).

    Refused 409 on the basis of the reference or of the current revision a project lacks, 422 on
    a marked revision that is not one, and on a node the reference does not hold.
    """
    reading = reading_of(session, project_id, asked)
    node_id = asked.org_node_id
    label = None if node_id is None else node_labels(session, {node_id}).get(node_id)
    faults = (
        None if reading is not None else FieldError(REVISION_POINTER, VALIDATION_FAILED),
        FieldError(ORG_NODE_POINTER, UNKNOWN_ORG_NODE) if node_id and label is None else None,
    )
    if reading is None or any(faults):
        named = tuple(each for each in faults if each is not None)
        raise UnprocessableError(VALIDATION_FAILED, fields=named)
    remaining = reading.as_of is not None
    shown, totals = _plan(session, project_id, reading, node_id, reference=not remaining)
    return WorkloadView(
        reading.revision_id,
        reading.status,
        reading.computed_at,
        reading.is_stored,
        asked.basis,
        node_id,
        label,
        totals,
        shown,
    )


def _plan(
    session: Session,
    project_id: UUID,
    reading: Reading,
    node_id: UUID | None,
    *,
    reference: bool,
) -> tuple[tuple[RoleLoad, ...], tuple[tuple[str, Decimal], ...]]:
    """Give the roles of a plan of workload, under a node, and its monthly totals.

    On a remaining (``reading.as_of``), the lines of a completed task are left out and the others
    spread after that day; without one, each line whole over its task, on its figures of the
    reference if ``reference``, else on its own. The roles, calendars and capacities those a marked
    revision kept (``reading.is_stored``), else the reference as it stands.
    """
    placed = placed_lines(session, project_id, reading.revision_id)
    employed = {each.line.resource_role_id for each in placed if each.line.resource_role_id}
    kept = kept_reference(session, project_id, reading.revision_id) if reading.is_stored else None
    roles = _roles(session, node_id, employed, kept)
    weeks = role_weeks(session, employed, kept)
    placements = {
        each.line.node_id: placement_of(each, weeks)
        for each in placed
        if each.line.resource_role_id is not None
    }
    remaining = reading.as_of is not None
    loads = loads_of(placed, placements, reference=reference, remaining=remaining)
    listed = {role.resource_role_id for role in roles}
    spread = spread_loads((load for load in loads if load.role_id in listed), reading.as_of)
    # The months of a role sum those of its tasks, the totals those of the roles: parts rounded.
    hours = {role_id: summed_parts(tasks.values()) for role_id, tasks in spread.items()}
    bearers = {each.task_id: each for each in placed}
    shown = tuple(
        _load_of(
            role,
            hours.get(role.resource_role_id, {}),
            spread.get(role.resource_role_id, {}),
            bearers,
        )
        for role in roles
    )
    totals = tuple((label_of(month), sum_) for month, sum_ in monthly_totals(hours.values()))
    return shown, totals


def estimate_workload(
    session: Session, project_id: UUID, revision_id: UUID, at: datetime
) -> tuple[RoleLoad, ...]:
    """Give the load of the estimate of a revision by role: each line whole over its task.

    What the portfolio reads of an offer, whose estimate is its whole load (EP-11, "Tables et
    migrations", ``portfolio_workload``): no day of calculation, the hours of each labour line, on
    its own figures, spread over the whole of its task, a completed task's as any other. The
    roles, calendars and capacities those a marked revision kept, else the reference as it stands;
    every role listed, in the order of the plan. ``at``, the instant of the computation, changes
    nothing of it. A revision unknown is refused (404).
    """
    read = read_revision_for(session, project_id, revision_id)
    status = MARKED if read.marked else DRAFT
    reading = Reading(revision_id, status, at, is_stored=read.marked, as_of=None)
    return _plan(session, project_id, reading, None, reference=False)[0]
