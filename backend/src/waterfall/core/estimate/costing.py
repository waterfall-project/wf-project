# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What prices a line, read from the base, private to the module (EP-07, "Le calcul des montants").

The base amount of a line is its quantity times its hours times the hourly rate of its category
for the reference year of its revision — the rate the revision keeps (``revision_rate``), that of
the reference otherwise — for a labour line, its quantity times its unit disbursement otherwise;
without a rate, the entry is refused, each category without one named with its year
(``HOURLY_RATE_MISSING``, WF-DEV-0010). The hours worked of the task that bears it are shared among
the years on the calendar of its role — the task's for another line —, each share projected once a
year elapsed since the reference year at the inflation rate of the project, the re-estimated amount
their sum, rounded once (``pricing``, ``spreading``; WF-DEV-0030, WF-DEV-0040); the year of
consumption is the year of the heaviest share, the first on a tie.

A labour line whose role would leave its task without an hour in its week — the calendars of the
roles of its lines intersected day by day — is refused, the roles and the task named
(``TASK_WITHOUT_WORKING_HOURS``, WF-PLA-0010).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.cost_settings.interface import list_hourly_rates
from waterfall.core.estimate.pricing import (
    Share,
    projected_amount,
    round_to_cent,
    unrounded_disbursement_amount,
    unrounded_labour_amount,
)
from waterfall.core.estimate.spreading import Placement, spread_by_year
from waterfall.core.estimate.tables import EstimateLine, RevisionRate
from waterfall.core.planning.interface import lines_of, weekly_calendar
from waterfall.core.projects.interface import project_facts
from waterfall.core.resource_settings.interface import read_calendar, read_roles, role_calendars
from waterfall.core.revisions.interface import reference_year_of
from waterfall.platform.errors import UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import BearingTask
    from waterfall.core.resource_settings.interface import WeeklyHours

NOUGHT = Decimal(0)
HOURLY_RATE_MISSING = "HOURLY_RATE_MISSING"
TASK_WITHOUT_WORKING_HOURS = "TASK_WITHOUT_WORKING_HOURS"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True, slots=True)
class Basis:
    """What a revision prices its lines on: its year of reference, the inflation, its reference.

    ``has_reference`` tells whether the project has a reference revision: the budgeted amount of a
    line created then is nought, and confounded with the re-estimated one otherwise (WF-DEV-0020).
    """

    revision_id: UUID
    reference_year: int
    inflation_rate: Decimal
    has_reference: bool


@dataclass(frozen=True, slots=True)
class Priced:
    """The amounts of a line as computed: its base amount, its re-estimated one, its year."""

    base: Decimal
    reestimated: Decimal
    consumption_year: int


@dataclass(frozen=True, slots=True)
class Figures:
    """What a line is priced from: its figures, its category, its role's calendar, if any."""

    quantity: Decimal
    hours: Decimal | None
    unit_disbursement: Decimal | None
    cost_category_id: UUID
    calendar_id: UUID | None


def basis_of(session: Session, project_id: UUID, revision_id: UUID) -> Basis:
    """Read what a revision of a project prices its lines on.

    The inflation of the project, which a current revision follows; a marked one writes none.
    """
    facts = project_facts(session, project_id)
    return Basis(
        revision_id,
        reference_year_of(session, revision_id),
        facts.inflation_rate,
        facts.reference_revision_id is not None,
    )


def rates_of(
    session: Session, project_id: UUID, basis: Basis, category_ids: Collection[UUID]
) -> dict[UUID, Decimal]:
    """Give the hourly rate of each category named for the year of reference of the revision.

    The rate the revision keeps, that of the reference for the year otherwise; a category without
    either is left out.
    """
    return held_rates(session, (project_id, basis.revision_id, basis.reference_year), category_ids)


def held_rates(
    session: Session, revision: tuple[UUID, UUID, int], category_ids: Collection[UUID]
) -> dict[UUID, Decimal]:
    """Give the rate each category named is priced at in a revision, of its year of reference.

    ``revision`` is its project, itself and its year: the rate it keeps (``revision_rate``), that
    of the reference for the year otherwise (EP-07, "Le calcul des montants").
    """
    project_id, revision_id, year = revision
    if not category_ids:
        return {}
    kept: dict[UUID, Decimal] = dict(
        session.execute(
            select(RevisionRate.cost_category_id, RevisionRate.amount).where(
                RevisionRate.project_id == project_id,
                RevisionRate.revision_id == revision_id,
                RevisionRate.cost_category_id.in_(category_ids),
            )
        ).all()
    )
    return {**reference_rates(session, set(category_ids) - kept.keys(), year), **kept}


def reference_rates(
    session: Session, category_ids: Collection[UUID], year: int
) -> dict[UUID, Decimal]:
    """Give the hourly rate of the reference for a year of each category named that has one."""
    found: dict[UUID, Decimal] = {}
    for category_id in category_ids:
        for rate in list_hourly_rates(session, category_id):
            if rate.year == year:
                found[category_id] = rate.amount
    return found


def refuse_missing_rate(category: tuple[UUID, str], basis: Basis) -> UnprocessableError:
    """Refuse a line whose category has no rate for the year of reference (WF-DEV-0010)."""
    category_id, label = category
    named = {"cost_category_id": str(category_id), "label": label, "year": basis.reference_year}
    return UnprocessableError(HOURLY_RATE_MISSING, {"missing_rates": [named]})


def week_of(hours: WeeklyHours) -> tuple[Decimal, ...]:
    """Give the hours of a calendar, Monday first."""
    return tuple(hours.of(day) for day in DAYS)


def product_of(figures: Figures, rate: Decimal | None) -> Decimal | None:
    """Give the product of a line, unrounded: none for a labour line without a rate."""
    if figures.hours is not None:
        if rate is None:
            return None
        return unrounded_labour_amount(figures.quantity, figures.hours, rate)
    return unrounded_disbursement_amount(figures.quantity, figures.unit_disbursement or NOUGHT)


def priced(
    product: Decimal, bearer: BearingTask, basis: Basis, week: tuple[Decimal, ...] | None
) -> Priced:
    """Share a product on the years of its task, project each share; give the amounts and year.

    ``week`` the hours of the calendar the line is worked on — its role's —, the task's if none.
    """
    placement = Placement(weekly_calendar(week or bearer.week), bearer.start, bearer.finish)
    shares = spread_by_year(placement, product)
    reestimated = projected_amount(
        [Share(year, amount) for year, amount in shares.items()],
        basis.reference_year,
        basis.inflation_rate,
    )
    year = max(shares.items(), key=lambda share: share[1])[0]
    return Priced(round_to_cent(product), reestimated, year)


def calendar_hours(
    session: Session, calendar_ids: Collection[UUID]
) -> dict[UUID, tuple[Decimal, ...]]:
    """Give the hours of each calendar named, Monday first."""
    return {each: week_of(read_calendar(session, each).weekly_hours) for each in set(calendar_ids)}


def judge_working_hours(
    session: Session,
    held: tuple[UUID, BearingTask, UUID | None],
    role_id: UUID,
    earlier: Mapping[UUID, UUID | None] | None = None,
) -> None:
    """Refuse a role that would leave the task of a line without an hour in its week (0010).

    ``held`` is the project, the task that bears the line, and the line itself, none at its
    creation: the roles of the other labour lines of the task and this one are intersected day by
    day; none left, the roles are named by their label, and the task. ``earlier`` gives the role a
    paste has left, or gives, to lines of the task (a line created included) before this one is
    judged: it takes the place of the role they have in the base.
    """
    project_id, bearer, line_id = held
    others = [
        each
        for each in lines_of(session, project_id, (bearer.task_id,)).get(bearer.task_id, ())
        if each != line_id
    ]
    held_roles: dict[UUID, UUID | None] = {}
    if others:
        held_roles = dict(
            session.execute(
                select(EstimateLine.node_id, EstimateLine.resource_role_id).where(
                    EstimateLine.project_id == project_id, EstimateLine.node_id.in_(others)
                )
            ).all()
        )
    held_roles.update({node: role for node, role in (earlier or {}).items() if node != line_id})
    roles = {role_id} | {each for each in held_roles.values() if each is not None}
    calendars = role_calendars(session, roles)
    weeks = calendar_hours(session, calendars.values()).values()
    if any(min(day) > 0 for day in zip(*weeks, strict=True)):
        return
    named = [
        {"resource_role_id": str(role.resource_role_id), "code": role.code, "label": role.label}
        for role in read_roles(session, roles, may_change=False)
    ]
    task = {"project_id": str(project_id), "node_id": str(bearer.task_id), "label": bearer.label}
    raise UnprocessableError(TASK_WITHOUT_WORKING_HOURS, {"resource_roles": named, "tasks": [task]})
