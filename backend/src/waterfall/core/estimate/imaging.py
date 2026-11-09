# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a revision keeps of the reference at its marking, and how it reads it since (US-1500).

A current revision follows the reference for its roles, its calendars and its categories, and
keeps its rates alone (EP-07, "L'instantané et les taux"). Its marking, in the transaction of the
task, before its indicators (``register_marking``), keeps the images of what its lines employ — each
role of a labour line, the calendar of each such role and the default calendar, each category of a
line —, every field as the reference holds it then, its state, its audit and its counter included
(``ResourceRoleImage``, ``CalendarImage``, ``CostCategoryImage``); a rate of the reference for its
year (``reference``) for each category of labour its lines employ without a rate of its own, so
that the rates it was priced at are all its own (WF-REF-0130); and the rate of inflation and the
probability of winning of its project, on the revision (WF-REV-0030, WF-REV-0070). Nothing is read
under a lock of the reference: the marking holds the lock of the revision, which every write that
prices its lines waits for, and a rate of the reference written meanwhile is either committed
before — the lines priced at it — or after, the revision then marked and left as it is
(``repricing``).

A marked revision is read on its images (``kept_reference``, ``getRevision``'s ``snapshot``): the
labels and the states of the roles and the categories of its lines (``kept_labels``, ``listNodes``),
the calendars and the capacities of its roles (the workload of a marked revision, #2627); a revision
marked before, which keeps none, on the reference.

Written by US-1500/L2.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import insert, select

from waterfall.core.cost_settings.interface import (
    CategoryLabel,
    category_labels,
    read_cost_categories,
)
from waterfall.core.estimate.costing import reference_rates
from waterfall.core.estimate.keeping import REFERENCE, labour_categories
from waterfall.core.estimate.tables import (
    EstimateLine,
    RevisionCalendar,
    RevisionCategory,
    RevisionRate,
    RevisionRole,
)
from waterfall.core.planning.interface import lines_of_revision
from waterfall.core.resource_settings.interface import (
    CalendarFilters,
    CalendarSort,
    CalendarWindow,
    WeeklyHours,
    list_calendars,
    read_calendar,
    read_roles,
)
from waterfall.core.revisions.interface import keep_project_ratios, reference_year_of
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.cost_settings.interface import CostCategoryView
    from waterfall.core.revisions.interface import RevisionMarking

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True, slots=True)
class Stamp:
    """What an image keeps of its object besides its fields: its state, its audit, its counter."""

    is_active: bool
    created_at: datetime
    created_by: UUID | None
    updated_at: datetime
    updated_by: UUID | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class KeptRole:
    """A role of resources as a marked revision keeps it (``ResourceRoleImage``)."""

    resource_role_id: UUID
    code: str
    label: str
    org_node_id: UUID
    org_node_label: str
    cost_category_id: UUID
    cost_category_label: str
    calendar_id: UUID
    calendar_label: str
    monthly_hours: Decimal
    headcount: Decimal
    stamp: Stamp


@dataclass(frozen=True, slots=True)
class KeptCalendar:
    """A calendar as a marked revision keeps it, its hours of each day (``CalendarImage``)."""

    calendar_id: UUID
    label: str
    weekly_hours: WeeklyHours
    is_default: bool
    stamp: Stamp


@dataclass(frozen=True, slots=True)
class KeptCategory:
    """A category of cost as a marked revision keeps it, with its nature (``CostCategoryImage``)."""

    cost_category_id: UUID
    code: str
    label: str
    cost_type_id: UUID
    cost_type_label: str
    cost_type_kind: str
    cost_type_is_active: bool
    accounting_code: str
    stamp: Stamp


@dataclass(frozen=True, slots=True)
class KeptRate:
    """A rate a revision is priced at: its category, the year of the revision, its amount."""

    cost_category_id: UUID
    year: int
    amount: Decimal


@dataclass(frozen=True, slots=True)
class KeptReference:
    """What a marked revision keeps of the reference (``EmployedReference``), each list in order.

    The roles by code, the calendars by label, the categories by code, the rates by category.
    """

    resource_roles: tuple[KeptRole, ...]
    calendars: tuple[KeptCalendar, ...]
    cost_categories: tuple[KeptCategory, ...]
    hourly_rates: tuple[KeptRate, ...]


@dataclass(frozen=True, slots=True)
class KeptLabels:
    """The labels and the states a marked revision keeps of the roles and the categories it employs.

    ``roles`` by role, its label and whether it was active.
    """

    categories: Mapping[UUID, CategoryLabel]
    roles: Mapping[UUID, tuple[str, bool]]


def _stamped(marking: RevisionMarking, stamp: Stamp) -> dict[str, object]:
    """Give the columns an image shares: its row, and the state, the audit and the counter kept."""
    return {
        "project_id": marking.project_id,
        "id": new_id(),
        "revision_id": marking.revision_id,
        "is_active": stamp.is_active,
        "created_at": stamp.created_at,
        "created_by": stamp.created_by,
        "updated_at": stamp.updated_at,
        "updated_by": stamp.updated_by,
        "lock_version": stamp.lock_version,
    }


def _employed(
    session: Session, project_id: UUID, revision_id: UUID
) -> tuple[frozenset[UUID], frozenset[UUID]]:
    """Give the categories the lines of a revision employ, and the roles of its labour lines."""
    nodes = list(lines_of_revision(session, project_id, revision_id).values())
    if not nodes:
        return frozenset(), frozenset()
    rows = session.execute(
        select(EstimateLine.cost_category_id, EstimateLine.resource_role_id)
        .where(EstimateLine.project_id == project_id, EstimateLine.node_id.in_(nodes))
        .distinct()
    ).all()
    categories = frozenset(category for category, _ in rows)
    roles = frozenset(role for _, role in rows if role is not None)
    return categories, roles


def _default_calendar(session: Session) -> UUID:
    """Give the default calendar: the first in the order of ``is_default``, for it is single."""
    page = list_calendars(
        session, CalendarFilters(), CalendarSort("is_default"), CalendarWindow(1, 0)
    )
    return page.calendars[0].calendar_id


def _keep_roles(session: Session, marking: RevisionMarking, role_ids: frozenset[UUID]) -> set[UUID]:
    """Keep the images of the roles named; give their calendars."""
    roles = read_roles(session, role_ids, may_change=False)
    if not roles:
        return set()
    labels = category_labels(session, {role.cost_category_id for role in roles})
    session.execute(
        insert(RevisionRole),
        [
            {
                **_stamped(
                    marking,
                    Stamp(
                        role.is_active,
                        role.created_at,
                        role.created_by,
                        role.updated_at,
                        role.updated_by,
                        role.lock_version,
                    ),
                ),
                "resource_role_id": role.resource_role_id,
                "code": role.code,
                "label": role.label,
                "org_node_id": role.org_node_id,
                "org_node_label": role.org_node_label,
                "cost_category_id": role.cost_category_id,
                "cost_category_label": (
                    labels[role.cost_category_id].label if role.cost_category_id in labels else ""
                ),
                "calendar_id": role.calendar_id,
                "calendar_label": role.calendar_label,
                "monthly_hours": role.capacity.monthly_hours,
                "headcount": role.capacity.headcount,
            }
            for role in roles
        ],
    )
    return {role.calendar_id for role in roles}


def _keep_calendars(session: Session, marking: RevisionMarking, calendar_ids: set[UUID]) -> None:
    """Keep the images of the calendars named."""
    calendars = [read_calendar(session, each) for each in sorted(calendar_ids)]
    session.execute(
        insert(RevisionCalendar),
        [
            {
                **_stamped(
                    marking,
                    Stamp(
                        calendar.is_active,
                        calendar.created_at,
                        calendar.created_by,
                        calendar.updated_at,
                        calendar.updated_by,
                        calendar.lock_version,
                    ),
                ),
                "calendar_id": calendar.calendar_id,
                "label": calendar.label,
                **{day: calendar.weekly_hours.of(day) for day in DAYS},
                "is_default": calendar.is_default,
            }
            for calendar in calendars
        ],
    )


def _category_stamp(category: CostCategoryView) -> Stamp:
    """Give what an image of a category keeps of its audit: its authors by their account."""
    audit = category.audit
    return Stamp(
        category.is_active,
        audit.created_at,
        None if audit.created_by is None else audit.created_by.user_id,
        audit.updated_at,
        None if audit.updated_by is None else audit.updated_by.user_id,
        audit.lock_version,
    )


def _keep_categories(
    session: Session, marking: RevisionMarking, category_ids: frozenset[UUID]
) -> None:
    """Keep the images of the categories named, with their nature; their authors by account."""
    categories = read_cost_categories(session, category_ids)
    if not categories:
        return
    session.execute(
        insert(RevisionCategory),
        [
            {
                **_stamped(marking, _category_stamp(category)),
                "cost_category_id": category.cost_category_id,
                "code": category.code,
                "label": category.label,
                "cost_type_id": category.cost_type_id,
                "cost_type_label": category.cost_type_label,
                "cost_type_kind": category.cost_type_kind,
                "cost_type_is_active": category.cost_type_is_active,
                "accounting_code": category.accounting_code,
            }
            for category in categories
        ],
    )


def _keep_rates(session: Session, marking: RevisionMarking) -> None:
    """Keep the rate of the reference for its year of each category of labour it keeps none of.

    A category without a rate for the year keeps none: its lines were refused (WF-DEV-0010).
    """
    project_id, revision_id = marking.project_id, marking.revision_id
    employed = labour_categories(session, project_id, revision_id)
    held = set(
        session.scalars(
            select(RevisionRate.cost_category_id).where(
                RevisionRate.project_id == project_id, RevisionRate.revision_id == revision_id
            )
        )
    )
    year = reference_year_of(session, revision_id)
    rates = reference_rates(session, employed - held, year)
    if not rates:
        return
    session.execute(
        insert(RevisionRate),
        [
            {
                "project_id": project_id,
                "id": new_id(),
                "revision_id": revision_id,
                "cost_category_id": category,
                "amount": amount,
                "origin": REFERENCE,
            }
            for category, amount in sorted(rates.items())
        ],
    )


def keep_images(marking: RevisionMarking) -> None:
    """Keep what a revision being marked employs of the reference, its rates and its project's.

    In the transaction of the marking, under the lock of the revision and of its project.
    """
    session = marking.session
    categories, roles = _employed(session, marking.project_id, marking.revision_id)
    calendars = _keep_roles(session, marking, roles) | {_default_calendar(session)}
    _keep_calendars(session, marking, calendars)
    _keep_categories(session, marking, categories)
    _keep_rates(session, marking)
    keep_project_ratios(marking)
    session.flush()


def _stamp_of(row: RevisionRole | RevisionCalendar | RevisionCategory) -> Stamp:
    return Stamp(
        row.is_active,
        row.created_at,
        row.created_by,
        row.updated_at,
        row.updated_by,
        row.lock_version,
    )


def _kept_roles(session: Session, project_id: UUID, revision_id: UUID) -> tuple[KeptRole, ...]:
    rows = session.scalars(
        select(RevisionRole)
        .where(RevisionRole.project_id == project_id, RevisionRole.revision_id == revision_id)
        .order_by(RevisionRole.code, RevisionRole.resource_role_id)
    )
    return tuple(
        KeptRole(
            row.resource_role_id,
            row.code,
            row.label,
            row.org_node_id,
            row.org_node_label,
            row.cost_category_id,
            row.cost_category_label,
            row.calendar_id,
            row.calendar_label,
            row.monthly_hours,
            row.headcount,
            _stamp_of(row),
        )
        for row in rows
    )


def _kept_calendars(
    session: Session, project_id: UUID, revision_id: UUID
) -> tuple[KeptCalendar, ...]:
    rows = session.scalars(
        select(RevisionCalendar)
        .where(
            RevisionCalendar.project_id == project_id, RevisionCalendar.revision_id == revision_id
        )
        .order_by(RevisionCalendar.label, RevisionCalendar.calendar_id)
    )
    return tuple(
        KeptCalendar(
            row.calendar_id,
            row.label,
            WeeklyHours(*(getattr(row, day) for day in DAYS)),
            row.is_default,
            _stamp_of(row),
        )
        for row in rows
    )


def _kept_categories(
    session: Session, project_id: UUID, revision_id: UUID
) -> tuple[KeptCategory, ...]:
    rows = session.scalars(
        select(RevisionCategory)
        .where(
            RevisionCategory.project_id == project_id, RevisionCategory.revision_id == revision_id
        )
        .order_by(RevisionCategory.code, RevisionCategory.cost_category_id)
    )
    return tuple(
        KeptCategory(
            row.cost_category_id,
            row.code,
            row.label,
            row.cost_type_id,
            row.cost_type_label,
            row.cost_type_kind,
            row.cost_type_is_active,
            row.accounting_code,
            _stamp_of(row),
        )
        for row in rows
    )


def kept_reference(session: Session, project_id: UUID, revision_id: UUID) -> KeptReference:
    """Give what a revision keeps of the reference: its images, and the rates it is priced at.

    The images are a marked revision's; a current one, or one marked before US-1500, keeps none.
    """
    year = reference_year_of(session, revision_id)
    rates = session.execute(
        select(RevisionRate.cost_category_id, RevisionRate.amount)
        .where(RevisionRate.project_id == project_id, RevisionRate.revision_id == revision_id)
        .order_by(RevisionRate.cost_category_id)
    ).all()
    return KeptReference(
        _kept_roles(session, project_id, revision_id),
        _kept_calendars(session, project_id, revision_id),
        _kept_categories(session, project_id, revision_id),
        tuple(KeptRate(category, year, amount) for category, amount in rates),
    )


def kept_labels(
    session: Session, project_id: UUID, revision_ids: Collection[UUID]
) -> dict[UUID, KeptLabels]:
    """Give, of the revisions named, what each that keeps images keeps of its roles and categories.

    A revision that keeps none — current, or marked before US-1500 — is left out: it reads the
    reference.
    """
    if not revision_ids:
        return {}
    categories: dict[UUID, dict[UUID, CategoryLabel]] = {}
    for row in session.scalars(
        select(RevisionCategory).where(
            RevisionCategory.project_id == project_id,
            RevisionCategory.revision_id.in_(list(revision_ids)),
        )
    ):
        categories.setdefault(row.revision_id, {})[row.cost_category_id] = CategoryLabel(
            row.cost_category_id,
            row.label,
            row.cost_type_kind,
            row.is_active,
            row.cost_type_is_active,
            row.cost_type_id,
        )
    roles: dict[UUID, dict[UUID, tuple[str, bool]]] = {}
    for row in session.scalars(
        select(RevisionRole).where(
            RevisionRole.project_id == project_id,
            RevisionRole.revision_id.in_(list(revision_ids)),
        )
    ):
        roles.setdefault(row.revision_id, {})[row.resource_role_id] = (row.label, row.is_active)
    return {
        revision: KeptLabels(categories.get(revision, {}), roles.get(revision, {}))
        for revision in categories.keys() | roles.keys()
    }
