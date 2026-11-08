# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The lines as ``listNodes`` reads them, private to the module (WF-DEV-0020, WF-DEV-0050).

The facet of a line (``EstimateLineFacet``): its figures and its kept amounts, the labels of its
category, its role and its subproject resolved, the object active or deactivated (WF-REF-0150),
whether it uses a deactivated one (``uses_inactive_object``, WF-REF-0010), whether it accepts a
re-estimate (``remaining_entry``, ``task_not_completed``) — the previous figures null until EP-09,
``is_computed`` false until the provision lines of EP-08 —, its budgeted amount read as its
re-estimated one when the project had no reference at its creation; and the fields it computes and
accepts: a labour line computes its category, and accepts its role and its hours, another its
category and its unit disbursement; a line of a completed task of the main structure accepts none
(#1767), one of a task started or completed does not name a subproject that received actual costs
(WF-PRJ-0050). The filters of the line retain lines on these values, every bound inclusive, a line
without the value retained by no bound; the sort orders them, a line without the value after the
others ascending, before them descending (WF-IHM-0060).
"""

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select

from waterfall.core.cost_settings.interface import category_labels
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import Amounts, FacetRead
from waterfall.core.projects.interface import subproject_has_actual_costs, subproject_labels
from waterfall.core.resource_settings.interface import read_roles

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Mapping
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.core.planning.interface import BearingTask, LineSort

type Bounds[T] = tuple[T | None, T | None]

COMPLETED = "completed"
NOT_STARTED = "not_started"
TASK_NOT_COMPLETED = "task_not_completed"
CATEGORY = "estimate_line.cost_category_id"
# The fields a line may accept, in the order of ``EditableField``.
EDITABLE = (
    "label",
    "cost_category_id",
    "resource_role_id",
    "quantity",
    "hours",
    "unit_disbursement",
    "payment_delay_days",
    "subproject_id",
)


@dataclass(frozen=True, slots=True)
class LineView:
    """The facet of a line as it is read (``EstimateLineFacet``), its labels resolved.

    ``remaining_missing`` the conditions a re-estimate lacks, none when it is open.
    """

    label: str
    cost_category_id: UUID
    cost_category_label: str
    resource_role_id: UUID | None
    resource_role_label: str | None
    quantity: Decimal
    hours: Decimal | None
    unit_disbursement: Decimal | None
    payment_delay_days: int
    subproject_id: UUID | None
    subproject_label: str | None
    base_amount: Decimal
    budgeted_amount: Decimal
    reestimated_amount: Decimal
    consumption_year: int
    uses_inactive_object: bool
    remaining_missing: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LineFilters:
    """What a reading retains of the lines (``listNodes``); a filter ``None`` asks nothing.

    ``unassigned`` retains the lines under no subproject (WF-IND-0020). The previous figures are
    null before EP-09: a bound on them retains no line.
    """

    subproject_id: UUID | None = None
    unassigned: bool = False
    cost_type_id: UUID | None = None
    cost_category_id: UUID | None = None
    resource_role_id: UUID | None = None
    uses_inactive_object: bool | None = None
    quantity: Bounds[Decimal] = (None, None)
    hours: Bounds[Decimal] = (None, None)
    unit_disbursement: Bounds[Decimal] = (None, None)
    payment_delay_days: Bounds[Decimal] = (None, None)
    consumption_year: Bounds[Decimal] = (None, None)
    base_amount: Bounds[Decimal] = (None, None)
    budgeted_amount: Bounds[Decimal] = (None, None)
    reestimated_amount: Bounds[Decimal] = (None, None)
    previous: tuple[Bounds[Decimal], ...] = ()


def budgeted_of(line: EstimateLine) -> Decimal:
    """Give the budgeted amount of a line as read: its re-estimated one without a reference."""
    return line.reestimated_amount if line.budgeted_amount is None else line.budgeted_amount


def rows_of(session: Session, project_id: UUID, node_ids: Collection[UUID]) -> list[EstimateLine]:
    """Read the facets of the lines named, as they are in the transaction."""
    if not node_ids:
        return []
    return list(
        session.scalars(
            select(EstimateLine)
            .where(EstimateLine.project_id == project_id, EstimateLine.node_id.in_(list(node_ids)))
            .execution_options(populate_existing=True)
        )
    )


def totals_of(
    session: Session, project_id: UUID, node_ids: Collection[UUID]
) -> dict[UUID, Amounts]:
    """Give the figures of each line named: its hours, its three amounts, its year."""
    return {
        line.node_id: Amounts(
            line.hours or Decimal(0),
            line.base_amount,
            budgeted_of(line),
            line.reestimated_amount,
            line.consumption_year,
        )
        for line in rows_of(session, project_id, node_ids)
    }


def _views(
    session: Session, project_id: UUID, rows: list[EstimateLine]
) -> dict[UUID, tuple[LineView, bool]]:
    """Give the view of each line, and whether its subproject received actual costs."""
    categories = category_labels(session, {row.cost_category_id for row in rows})
    roles = {
        role.resource_role_id: role
        for role in read_roles(
            session,
            {row.resource_role_id for row in rows if row.resource_role_id is not None},
            may_change=False,
        )
    }
    subprojects = {row.subproject_id for row in rows if row.subproject_id is not None}
    labels = subproject_labels(session, project_id, subprojects)
    costs = {each for each in subprojects if subproject_has_actual_costs(session, each)}
    found: dict[UUID, tuple[LineView, bool]] = {}
    for row in rows:
        category = categories.get(row.cost_category_id)
        role = None if row.resource_role_id is None else roles.get(row.resource_role_id)
        inactive = (
            category is None
            or not (category.is_active and category.cost_type_is_active)
            or (role is not None and not role.is_active)
        )
        view = LineView(
            label=row.label,
            cost_category_id=row.cost_category_id,
            cost_category_label="" if category is None else category.label,
            resource_role_id=row.resource_role_id,
            resource_role_label=None if role is None else role.label,
            quantity=row.quantity,
            hours=row.hours,
            unit_disbursement=row.unit_disbursement,
            payment_delay_days=row.payment_delay_days,
            subproject_id=row.subproject_id,
            subproject_label=None if row.subproject_id is None else labels.get(row.subproject_id),
            base_amount=row.base_amount,
            budgeted_amount=budgeted_of(row),
            reestimated_amount=row.reestimated_amount,
            consumption_year=row.consumption_year,
            uses_inactive_object=inactive,
            remaining_missing=(),
        )
        found[row.node_id] = (view, row.subproject_id in costs)
    return found


def _fields(view: LineView, bearer: BearingTask, *, costs: bool) -> tuple[tuple[str, ...], ...]:
    """Give the fields a line computes and those it accepts (WF-IHM-0030, WF-IHM-0040)."""
    labour = view.resource_role_id is not None
    computed = (CATEGORY,) if labour else ()
    if bearer.is_main and bearer.progress == COMPLETED:
        return computed, ()
    refused = {"cost_category_id", "unit_disbursement"} if labour else {"resource_role_id", "hours"}
    if costs and bearer.progress != NOT_STARTED:
        refused.add("subproject_id")
    editable = tuple(f"estimate_line.{name}" for name in EDITABLE if name not in refused)
    return computed, editable


def read_lines(
    session: Session, project_id: UUID, lines: Mapping[UUID, BearingTask]
) -> dict[UUID, FacetRead]:
    """Give the facet of each line named, read, with the fields it computes and accepts."""
    found: dict[UUID, FacetRead] = {}
    views = _views(session, project_id, rows_of(session, project_id, lines))
    for node_id, (view, costs) in views.items():
        bearer = lines[node_id]
        missing = (TASK_NOT_COMPLETED,) if bearer.progress == COMPLETED else ()
        whole = replace(view, remaining_missing=missing)
        computed, editable = _fields(whole, bearer, costs=costs)
        found[node_id] = FacetRead(whole, whole.label, computed, editable)
    return found


def _within(value: Decimal | int | None, bounds: Bounds[Decimal]) -> bool:
    """Tell whether a value lies between two bounds, inclusive; none lies within a bound."""
    low, high = bounds
    if low is None and high is None:
        return True
    if value is None:
        return False
    return (low is None or low <= value) and (high is None or value <= high)


def _tests(
    asked: LineFilters, cost_types: Mapping[UUID, UUID | None]
) -> list[Callable[[LineView], bool]]:
    """Give the tests of a line the filters ask for, each on the line alone."""
    tests: list[Callable[[LineView], bool]] = [
        lambda line: _within(line.quantity, asked.quantity),
        lambda line: _within(line.hours, asked.hours),
        lambda line: _within(line.unit_disbursement, asked.unit_disbursement),
        lambda line: _within(line.payment_delay_days, asked.payment_delay_days),
        lambda line: _within(line.consumption_year, asked.consumption_year),
        lambda line: _within(line.base_amount, asked.base_amount),
        lambda line: _within(line.budgeted_amount, asked.budgeted_amount),
        lambda line: _within(line.reestimated_amount, asked.reestimated_amount),
        lambda _line: all(_within(None, bounds) for bounds in asked.previous),
    ]
    if asked.unassigned:
        tests.append(lambda line: line.subproject_id is None)
    if asked.subproject_id is not None:
        tests.append(lambda line: line.subproject_id == asked.subproject_id)
    if asked.cost_category_id is not None:
        tests.append(lambda line: line.cost_category_id == asked.cost_category_id)
    if asked.resource_role_id is not None:
        tests.append(lambda line: line.resource_role_id == asked.resource_role_id)
    if asked.cost_type_id is not None:
        tests.append(lambda line: cost_types.get(line.cost_category_id) == asked.cost_type_id)
    if asked.uses_inactive_object is not None:
        tests.append(lambda line: line.uses_inactive_object is asked.uses_inactive_object)
    return tests


def filter_lines(
    session: Session, project_id: UUID, node_ids: Collection[UUID], asked: object
) -> frozenset[UUID]:
    """Keep, of the lines named, those the filters of the line retain (``listNodes``)."""
    if not isinstance(asked, LineFilters):
        return frozenset(node_ids)
    rows = rows_of(session, project_id, node_ids)
    views = _views(session, project_id, rows)
    cost_types = {
        each: label.cost_type_id
        for each, label in category_labels(session, {row.cost_category_id for row in rows}).items()
    }
    tests = _tests(asked, cost_types)
    return frozenset(
        node_id for node_id, (view, _) in views.items() if all(test(view) for test in tests)
    )


def _number(value: Decimal | int | None) -> Decimal | None:
    return None if value is None else Decimal(value)


# The value of a line each column of the sort reads (``NodeColumn``): a text, or a number; the
# previous figures are none before EP-09.
_TEXTS: dict[str, Callable[[LineView], str | None]] = {
    "label": lambda line: line.label,
    "cost_category": lambda line: line.cost_category_label,
    "resource_role": lambda line: line.resource_role_label,
    "subproject": lambda line: line.subproject_label,
}
_NUMBERS: dict[str, Callable[[LineView], Decimal | None]] = {
    "quantity": lambda line: line.quantity,
    "hours": lambda line: line.hours,
    "unit_disbursement": lambda line: line.unit_disbursement,
    "payment_delay_days": lambda line: _number(line.payment_delay_days),
    "consumption_year": lambda line: _number(line.consumption_year),
    "base_amount": lambda line: line.base_amount,
    "budgeted_amount": lambda line: line.budgeted_amount,
    "reestimated_amount": lambda line: line.reestimated_amount,
    "previous_quantity": lambda _line: None,
    "previous_hours": lambda _line: None,
    "previous_unit_disbursement": lambda _line: None,
    "previous_reestimated_amount": lambda _line: None,
}


def _ordered[T: (str, Decimal)](
    given: list[UUID], value_of: Callable[[UUID], T | None], *, descending: bool
) -> list[UUID]:
    """Order by a value, equals in the order given, those without one last ascending, else first."""
    present = [(each, value) for each in given if (value := value_of(each)) is not None]
    absent = [each for each in given if value_of(each) is None]
    ordered = [each for each, _ in sorted(present, key=lambda pair: pair[1], reverse=descending)]
    return [*absent, *ordered] if descending else [*ordered, *absent]


def sort_lines(
    session: Session, project_id: UUID, node_ids: Collection[UUID], sort: LineSort
) -> list[UUID] | None:
    """Order the lines named by a column of the line; none for a column of the task.

    Equal values keep the order given; a line without the value comes after the others ascending,
    before them descending (WF-IHM-0060).
    """
    text, number = _TEXTS.get(sort.column), _NUMBERS.get(sort.column)
    if text is None and number is None:
        return None
    views = _views(session, project_id, rows_of(session, project_id, node_ids))
    given = [each for each in node_ids if each in views]
    if text is not None:
        return _ordered(given, lambda each: text(views[each][0]), descending=sort.descending)
    if number is None:
        return None
    return _ordered(given, lambda each: number(views[each][0]), descending=sort.descending)
