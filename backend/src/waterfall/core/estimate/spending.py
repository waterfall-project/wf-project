# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The spending projection of a project, by nature of cost and by month, private to the module.

``getProjectSpending`` (US-2050, WF-DEV-0100): the amount of each line of a revision, its provisions
left out, spread over the months of its task in proportion to the hours worked on the calendar of
the line (``disbursing``), each part rounded to the cent so that the parts of a line sum to its
amount (``parting``). The revision and its basis are those of the plan of workload (``reading_of``,
WF-DEV-0070): the budgeted amounts of the reference, spread over the whole of each task; the
re-estimated amounts of a marked revision, or of the current one, which are the remaining to commit
— nothing for the lines of a completed task —, spread over the part of the task after the date of
calculation, the whole falling on the month of that date once the task is over, so that no month
precedes it and that the total is the remaining to commit of the project without its provisions
(WF-RAE-0010). On request each part is shifted by the payment delay of its line: the disbursements.

A category sums the parts of its lines, a nature those of its categories, a month those of its
natures: every amount is a sum of parts already rounded, so that the total of a month is the sum of
its natures and that of a nature the sum of its categories. The natures and the categories are those
that carry an amount, in the order of the reference data — their code, then their identifier —, and
each has only the months it loads (#3096); the total of a month runs from the first to the last
without a gap. A marked revision is read on the images its marking kept, its categories and its
calendars, and is computed when read: nothing is stored. A labour category that has no hourly rate
for the reference year of the revision read refuses the projection, which has meaning only complete
(``HOURLY_RATE_MISSING``, WF-DEV-0010, #3565).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from waterfall.core.cost_settings.interface import (
    CostTypeFilters,
    CostTypeSort,
    Page,
    list_cost_types,
    read_cost_categories,
)
from waterfall.core.estimate.costing import HOURLY_RATE_MISSING
from waterfall.core.estimate.disbursing import amount_parts
from waterfall.core.estimate.imaging import KeptCategory, kept_reference
from waterfall.core.estimate.indicating import (
    PROJECT,
    UNASSIGNED,
    UNKNOWN_SUBPROJECT,
    MissingRate,
    missing_rates_of,
)
from waterfall.core.estimate.parting import summed_parts
from waterfall.core.estimate.placing import Placed, placed_lines, placement_of, role_weeks
from waterfall.core.estimate.reading import budgeted_of
from waterfall.core.estimate.remaining.reviewing import provisions_of, remaining_of_placed
from waterfall.core.estimate.workloading import (
    REVISION_POINTER,
    WorkloadAsked,
    WorkloadBasis,
    label_of,
    monthly_totals,
    reading_of,
)
from waterfall.core.projects.interface import subproject_labels
from waterfall.core.revisions.interface import read_revision_for
from waterfall.platform.errors import VALIDATION_FAILED, FieldError, UnprocessableError
from waterfall.platform.identifiers import read_identifier

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping
    from datetime import datetime

    from sqlalchemy.orm import Session

    from waterfall.core.estimate.spreading import Month
    from waterfall.core.projects.interface import Viewer

SUBPROJECT_POINTER = "/query/subproject_id"
ZERO = Decimal("0.00")
EVERY_TYPE = Page(limit=10**9, offset=0)

type Months = tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True, slots=True)
class SpendingAsked:
    """What a projection asks: its basis, the marked revision named, its scope, and when.

    ``subproject`` is ``unassigned`` or the identifier of a subproject, as the query writes it,
    none for the whole project; ``now`` the day of the calculation of the current revision;
    ``viewer`` reads the marked revision named.
    """

    basis: WorkloadBasis
    revision_id: UUID | None
    subproject: str | None
    payment_delays: bool
    now: datetime
    viewer: Viewer


@dataclass(frozen=True, slots=True)
class SpendingCategory:
    """A category of cost of the projection: its total, and its months loaded in order."""

    cost_category_id: UUID
    label: str
    total: Decimal
    months: Months


@dataclass(frozen=True, slots=True)
class SpendingCostType:
    """A nature of cost of the projection: its total, its months, its categories in order."""

    cost_type_id: UUID
    label: str
    total: Decimal
    months: Months
    categories: tuple[SpendingCategory, ...]


@dataclass(frozen=True, slots=True)
class SpendingView:
    """The projection of spending of a project (``SpendingProjection``): context, totals, natures.

    ``scope`` is ``project``, ``unassigned`` or the identifier of a subproject.
    """

    revision_id: UUID
    revision_status: str
    computed_at: datetime
    scope: str
    basis: WorkloadBasis
    payment_delays: bool
    total: Decimal
    monthly_totals: Months
    cost_types: tuple[SpendingCostType, ...]


@dataclass(frozen=True, slots=True)
class Named:
    """A category as the projection names it: its code, its label, its nature."""

    code: str
    label: str
    cost_type_id: UUID
    cost_type_label: str


def _scope_of(session: Session, project_id: UUID, asked: str | None) -> UUID | str | None:
    """Read the scope asked: the project, what falls under no subproject, a subproject; or none.

    None when the subproject is not one of the project, or is no identifier (422 follows).
    """
    if asked is None:
        return PROJECT
    if asked == UNASSIGNED:
        return UNASSIGNED
    subproject_id = read_identifier(asked)
    if subproject_id is None:
        return None
    return subproject_id if subproject_labels(session, project_id, [subproject_id]) else None


def _in_scope(scope: UUID | str, subproject_id: UUID | None) -> bool:
    """Tell whether a line of a subproject, or of none, falls in the scope."""
    if isinstance(scope, UUID):
        return subproject_id == scope
    return scope == PROJECT or subproject_id is None


def _refuse_rates(missing: Iterable[MissingRate]) -> UnprocessableError:
    """Refuse a projection that a labour category without a rate for its year leaves wrong."""
    named = [
        {"cost_category_id": str(each.cost_category_id), "label": each.label, "year": each.year}
        for each in missing
    ]
    return UnprocessableError(HOURLY_RATE_MISSING, {"missing_rates": named})


def _named(
    session: Session, category_ids: Collection[UUID], kept: Iterable[KeptCategory]
) -> dict[UUID, Named]:
    """Name each category: on the images of a marked revision, else on the reference as it is."""
    found = {
        each.cost_category_id: Named(each.code, each.label, each.cost_type_id, each.cost_type_label)
        for each in kept
        if each.cost_category_id in category_ids
    }
    for view in read_cost_categories(session, set(category_ids) - found.keys()):
        found[view.cost_category_id] = Named(
            view.code, view.label, view.cost_type_id, view.cost_type_label
        )
    return found


def _type_codes(session: Session) -> dict[UUID, str]:
    """Give the code of every nature of the reference as it is, deactivated ones too.

    The order of the natures of a marked revision reads these codes too: the images of its marking
    (``KeptCategory``) keep the identifier and the label of a nature, not its code, and the
    interface of the cost settings reads no nature by identifier with its code. A code changed
    since the marking can therefore reorder the natures; the amounts are unaffected.
    """
    filters = CostTypeFilters(states=frozenset({True, False}))
    page = list_cost_types(session, filters, CostTypeSort(), EVERY_TYPE, may_change=False)
    return {each.cost_type_id: each.code for each in page.types}


def _months(months: Mapping[Month, Decimal]) -> Months:
    """Give the months of a part in order, as the contract names them."""
    return tuple((label_of(month), amount) for month, amount in sorted(months.items()))


def _total(months: Mapping[Month, Decimal]) -> Decimal:
    return sum(months.values(), ZERO)


def _cost_types(
    by_category: Mapping[UUID, list[dict[Month, Decimal]]],
    named: Mapping[UUID, Named],
    codes: Mapping[UUID, str],
) -> tuple[list[SpendingCostType], list[dict[Month, Decimal]]]:
    """Group the parts of the lines by category, then by nature, in the order of the reference.

    Give the natures, and the months of each, which the total of a month sums.
    """
    sums = {category: summed_parts(parts) for category, parts in by_category.items()}
    held = {category: months for category, months in sums.items() if months}
    natures: dict[UUID, list[UUID]] = {}
    for category in sorted(held, key=lambda each: (named[each].code, each)):
        natures.setdefault(named[category].cost_type_id, []).append(category)
    found: list[SpendingCostType] = []
    by_month: list[dict[Month, Decimal]] = []
    for nature in sorted(natures, key=lambda each: (codes.get(each, ""), each)):
        members = natures[nature]
        months = summed_parts(held[each] for each in members)
        by_month.append(months)
        categories = tuple(
            SpendingCategory(each, named[each].label, _total(held[each]), _months(held[each]))
            for each in members
        )
        label = named[members[0]].cost_type_label
        found.append(SpendingCostType(nature, label, _total(months), _months(months), categories))
    return found, by_month


def read_spending(session: Session, project_id: UUID, asked: SpendingAsked) -> SpendingView:
    """Give the projection of spending of a project on a basis (``getProjectSpending``).

    Refused 409 on the basis of the reference or of the current revision a project lacks; 422 on a
    marked revision that is not one, on a subproject the project does not have, and on a labour
    category without a rate for the reference year of the revision read.
    """
    place = WorkloadAsked(asked.basis, asked.revision_id, None, asked.now, asked.viewer)
    reading = reading_of(session, project_id, place)
    scope = _scope_of(session, project_id, asked.subproject)
    faults = (
        None if reading is not None else FieldError(REVISION_POINTER, VALIDATION_FAILED),
        None if scope is not None else FieldError(SUBPROJECT_POINTER, UNKNOWN_SUBPROJECT),
    )
    if reading is None or scope is None:
        named = tuple(each for each in faults if each is not None)
        raise UnprocessableError(VALIDATION_FAILED, fields=named)
    read = read_revision_for(session, project_id, reading.revision_id)
    if lacking := missing_rates_of(session, project_id, read):
        raise _refuse_rates(lacking)
    placed = placed_lines(session, project_id, reading.revision_id)
    kept = kept_reference(session, project_id, reading.revision_id) if read.marked else None
    employed = {each.line.resource_role_id for each in placed if each.line.resource_role_id}
    weeks = role_weeks(session, employed, kept)
    provisions = provisions_of(session, [each.line for each in placed])
    remaining = remaining_of_placed(session, placed)[1] if reading.as_of is not None else {}

    def amount_of(each: Placed) -> Decimal:
        if reading.as_of is None:
            return budgeted_of(each.line)
        return remaining.get(each.line.node_id, Decimal(0))

    by_category: dict[UUID, list[dict[Month, Decimal]]] = {}
    for each in placed:
        line = each.line
        amount = amount_of(each)
        if line.node_id in provisions or not amount or not _in_scope(scope, line.subproject_id):
            continue
        parts = amount_parts(
            placement_of(each, weeks),
            amount,
            as_of=reading.as_of,
            delay_days=line.payment_delay_days if asked.payment_delays else 0,
        )
        by_category.setdefault(line.cost_category_id, []).append(parts)
    images = () if kept is None else kept.cost_categories
    named = _named(session, set(by_category), images)
    cost_types, by_month = _cost_types(by_category, named, _type_codes(session))
    totals = monthly_totals(by_month, ZERO)
    return SpendingView(
        reading.revision_id,
        reading.status,
        reading.computed_at,
        scope if isinstance(scope, str) else str(scope),
        asked.basis,
        asked.payment_delays,
        sum((each.total for each in cost_types), ZERO),
        tuple((label_of(month), amount) for month, amount in totals),
        tuple(cost_types),
    )
