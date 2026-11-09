# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The workload of a project, by role and by month, private to the module (WF-DEV-0070, US-1520).

The hours of the labour lines of a revision — a line's quantity times its hours — are spread over
the months of the task that bears them in proportion to the hours worked on the calendar of the
line's role (``spreading``). Three bases are offered: the budgeted load of the reference revision,
spread over the whole of each task; and the load of a marked revision, or of the current one, which
is the remaining to commit — the lines of a completed task count for nothing, and the load of the
others is spread over the part of the task that follows the date of calculation (the day for the
current revision, the day of the marking for a marked one), the whole falling on the month of that
date once the task is over.

The roles listed are the active ones, with the roles the revision employs, deactivated or not,
restricted to the node asked and its descendants; each with its capacity in the reference. A month
whose hours exceed the capacity of its role is in alert (``WorkloadZone``). The hours of a role
and a month are rounded once, to the hundredth, from the exact sum of the parts of its lines.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from waterfall.core.cost_settings.interface import category_label_of
from waterfall.core.estimate.placing import Placed, placed_lines, placement_of, role_weeks
from waterfall.core.estimate.spreading import Month, Placement, spread_by_month
from waterfall.core.projects.interface import project_facts
from waterfall.core.resource_settings.interface import (
    RoleFilters,
    RoleSort,
    RoleView,
    RoleWindow,
    list_roles,
    node_labels,
)
from waterfall.core.revisions.interface import read_revision
from waterfall.platform.errors import ConflictError, FieldError, NotFoundError, UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from datetime import date, datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.projects.interface import Viewer

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
VALIDATION_FAILED = "VALIDATION_FAILED"
UNKNOWN_ORG_NODE = "UNKNOWN_ORG_NODE"
PROJECT_STATE = "ProjectState"
REVISION_POINTER = "/query/revision_id"
ORG_NODE_POINTER = "/query/org_node_id"
MARKED = "marked"
DRAFT = "draft"
NOUGHT = Decimal(0)
HUNDREDTH = Decimal("0.01")
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
class RoleLoad:
    """A role with its capacity a month in the reference, and its months loaded in order."""

    resource_role_id: UUID
    label: str
    org_node_id: UUID
    capacity_monthly_hours: Decimal
    months: tuple[RoleMonth, ...]


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
    """The hours of a labour line to spread: its role and its task as the line is worked on."""

    role_id: UUID
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


def spread_loads(loads: Iterable[Load], as_of: date | None) -> dict[UUID, dict[Month, Decimal]]:
    """Share the hours of each load among the months of its task; add them up by role.

    Pure. The sums are exact, to a ten-billionth of an hour: the caller rounds once.
    """
    found: dict[UUID, dict[Month, Decimal]] = {}
    for load in loads:
        if load.hours <= 0:
            continue
        months = found.setdefault(load.role_id, {})
        for month, hours in spread_by_month(load.placement, load.hours, as_of=as_of).items():
            months[month] = months.get(month, NOUGHT) + hours
    return found


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
) -> list[tuple[Month, Decimal]]:
    """Add up the hours of each month, from the first month loaded to the last, none left out."""
    sums: dict[Month, Decimal] = {}
    for months in months_by_role:
        for month, hours in months.items():
            sums[month] = sums.get(month, NOUGHT) + hours
    if not sums:
        return []
    found: list[tuple[Month, Decimal]] = []
    month, last = min(sums), max(sums)
    while month <= last:
        found.append((month, sums.get(month, NOUGHT)))
        month = month_after(month)
    return found


def rounded(hours: Decimal) -> Decimal:
    """Round hours once, to the hundredth, to the nearest even."""
    return hours.quantize(HUNDREDTH, rounding=ROUND_HALF_EVEN)


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
        view.revision_id, MARKED, view.marked_at, is_stored=True, as_of=view.marked_at.date()
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
            return Reading(facts.current_revision_id, DRAFT, now, is_stored=False, as_of=now.date())
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
        loads.append(Load(line.resource_role_id, quantity * hours, placements[line.node_id]))
    return loads


def _roles(session: Session, node_id: UUID | None, employed: Collection[UUID]) -> list[RoleView]:
    """Give the active roles and those employed, under the node asked and its descendants."""
    asked = RoleFilters(org_node_id=node_id, states=frozenset({True, False}))
    page = list_roles(session, asked, RoleSort(category_label_of), EVERY_ROLE, may_change=False)
    return [role for role in page.roles if role.is_active or role.resource_role_id in employed]


def _load_of(role: RoleView, months: Mapping[Month, Decimal]) -> RoleLoad:
    """Give a role with its months, in order, each in alert past the capacity of the role."""
    capacity = role.capacity.monthly_hours
    held = tuple(
        RoleMonth(label_of(month), hours, hours > capacity)
        for month, hours in sorted(months.items())
    )
    return RoleLoad(role.resource_role_id, role.label, role.org_node_id, capacity, held)


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
    placed = placed_lines(session, project_id, reading.revision_id)
    employed = {each.line.resource_role_id for each in placed if each.line.resource_role_id}
    roles = _roles(session, node_id, employed)
    weeks = role_weeks(session, employed)
    placements = {
        each.line.node_id: placement_of(each, weeks)
        for each in placed
        if each.line.resource_role_id is not None
    }
    remaining = reading.as_of is not None
    loads = loads_of(placed, placements, reference=not remaining, remaining=remaining)
    kept = {role.resource_role_id for role in roles}
    spread = spread_loads((load for load in loads if load.role_id in kept), reading.as_of)
    # One rounding, of the exact sum of a role and a month; the totals add what is rounded.
    hours = {
        role_id: {month: rounded(each) for month, each in months.items()}
        for role_id, months in spread.items()
    }
    shown = [_load_of(role, hours.get(role.resource_role_id, {})) for role in roles]
    totals = [(label_of(month), sum_) for month, sum_ in monthly_totals(hours.values())]
    return WorkloadView(
        reading.revision_id,
        reading.status,
        reading.computed_at,
        reading.is_stored,
        asked.basis,
        node_id,
        label,
        tuple(totals),
        tuple(shown),
    )
