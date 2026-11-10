# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The hourly rates of the categories of labour, by year.

The grid, the rates of a category, one rate set (WF-REF-0050, 0060).

A rate belongs to a category of labour and a year, at most one for the pair; it is set once, then
corrected at the version read, and never deleted. A year enters the grid by its first rate: no
column is created of itself (WF-REF-0060). The grid is read in two steps: the years of the whole
grid, whatever the page, then the page of the categories with the rates of those years.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, exists, func, insert, not_, or_, select

from waterfall.core.cost_settings.records import (
    ALREADY_EXISTS,
    Audit,
    Page,
    lock_natures,
)
from waterfall.core.cost_settings.tables import CostCategory, CostType, HourlyRate
from waterfall.core.users.interface import read_authors
from waterfall.platform.database import contains
from waterfall.platform.errors import (
    NOT_FOUND,
    STALE_LOCK_VERSION,
    VALIDATION_FAILED,
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from uuid import UUID

    from sqlalchemy.orm import Session

    from waterfall.platform.audit import Act

LABOUR_CATEGORY_REQUIRED = "LABOUR_CATEGORY_REQUIRED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
# The smallest rate, and the greatest the column holds (``numeric(12, 2)``).
SMALLEST_RATE = Decimal("0.01")
GREATEST_RATE = Decimal("9999999999.99")
LABOUR = "labor"
# The counter of a rate at its first writing, as the examples of the contract say it.
FIRST_VERSION = 1

type GridColumn = Literal["code", "label", "is_active", "rate"]


@dataclass(frozen=True, slots=True)
class HourlyRateView:
    """A rate as it is read: its category and its year name it, its amount, its audit."""

    cost_category_id: UUID
    year: int
    amount: Decimal
    audit: Audit


@dataclass(frozen=True, slots=True)
class HourlyRateRow:
    """A category of the grid, and its rate of each year of the grid, in the order of the years."""

    cost_category_id: UUID
    code: str
    label: str
    is_active: bool
    cells: tuple[HourlyRateView | None, ...]


@dataclass(frozen=True, slots=True)
class HourlyRateFilters:
    """What the grid keeps; a filter absent keeps everything (WF-IHM-0130).

    ``states`` are the values of ``is_active`` kept: the active categories alone unless asked.
    The bounds, included, hold on the rate of ``rate_year``: a category without a rate that year
    is kept by none of them. ``rate_year`` alone filters nothing.
    """

    search: str | None = None
    states: frozenset[bool] = frozenset({True})
    rate_year: int | None = None
    rate_min: Decimal | None = None
    rate_max: Decimal | None = None


@dataclass(frozen=True, slots=True)
class HourlyRateSort:
    """The column of the sort and its direction; the code unless said otherwise (WF-IHM-0060).

    The column ``rate`` is the rate of ``year``.
    """

    column: GridColumn = "code"
    year: int | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class HourlyRateGridPage:
    """A page of the grid: the years of the whole grid, the categories of the page, their count."""

    years: list[int]
    rows: list[HourlyRateRow]
    total: int


def category_is_rated(session: Session, category_ids: Collection[UUID]) -> frozenset[UUID]:
    """Give, of the categories given, those that bear a rate, whatever its year (WF-REF-0030).

    A nature whose category bears one, and a category that bears one, keep their kind (WF-REF-0050).
    """
    found = session.scalars(
        select(HourlyRate.cost_category_id)
        .where(HourlyRate.cost_category_id.in_(category_ids))
        .distinct()
    )
    return frozenset(found)


def _views(session: Session, rates: Sequence[HourlyRate]) -> list[HourlyRateView]:
    authors = read_authors(
        session,
        {user for rate in rates for user in (rate.created_by, rate.updated_by) if user is not None},
    )
    return [
        HourlyRateView(
            rate.cost_category_id,
            rate.year,
            rate.amount,
            Audit(
                rate.created_at,
                None if rate.created_by is None else authors.get(rate.created_by),
                rate.updated_at,
                None if rate.updated_by is None else authors.get(rate.updated_by),
                rate.lock_version,
            ),
        )
        for rate in rates
    ]


def _scope(states: frozenset[bool]) -> list[ColumnElement[bool]]:
    """Keep the categories of labour of the states given."""
    return [CostType.kind == LABOUR, CostCategory.is_active.in_(states)]


def _years(session: Session, states: frozenset[bool]) -> list[int]:
    """Give the years of the whole grid: the ones a category in the scope of the read bears.

    The deactivated categories count only when the read asks for them, the active ones always.
    """
    scope = frozenset({True, False}) if False in states else frozenset({True})
    return list(
        session.scalars(
            select(HourlyRate.year)
            .join(CostCategory, CostCategory.id == HourlyRate.cost_category_id)
            .join(CostType, CostType.id == CostCategory.cost_type_id)
            .where(*_scope(scope))
            .distinct()
            .order_by(HourlyRate.year)
        )
    )


def _criteria(filters: HourlyRateFilters) -> list[ColumnElement[bool]]:
    criteria = _scope(filters.states)
    if filters.search is not None:
        texts = (CostCategory.code, CostCategory.label)
        criteria.append(or_(*(contains(text, filters.search) for text in texts)))
    bounded = filters.rate_min is not None or filters.rate_max is not None
    if filters.rate_year is not None and bounded:
        held = [
            HourlyRate.cost_category_id == CostCategory.id,
            HourlyRate.year == filters.rate_year,
        ]
        if filters.rate_min is not None:
            held.append(HourlyRate.amount >= filters.rate_min)
        if filters.rate_max is not None:
            held.append(HourlyRate.amount <= filters.rate_max)
        criteria.append(exists().where(*held))
    return criteria


def _keys(sort: HourlyRateSort) -> tuple[SQLColumnExpression[object], ...]:
    """Give the keys of the sort asked for, before the code and the identifier break the ties."""
    if sort.column == "rate":
        rate = (
            select(HourlyRate.amount)
            .where(HourlyRate.cost_category_id == CostCategory.id, HourlyRate.year == sort.year)
            .scalar_subquery()
        )
        # No rate that year comes after the others ascending, before them descending.
        return (rate.desc().nulls_first() if sort.descending else rate.asc().nulls_last(),)
    keys: dict[str, SQLColumnExpression[object]] = {
        "code": CostCategory.code,
        "label": CostCategory.label,
        # False before true: the active categories first in the ascending order.
        "is_active": not_(CostCategory.is_active),
    }
    key = keys[sort.column]
    return (key.desc() if sort.descending else key,)


def read_hourly_rate_grid(
    session: Session, filters: HourlyRateFilters, sort: HourlyRateSort, page: Page
) -> HourlyRateGridPage:
    """Read the grid: the years of the whole grid, then a page of the categories of labour.

    The years do not depend on the page, the search, the bounds nor the sort. Equals keep the
    order of the code, then come by identifier, ascending whatever the direction. A page beyond the
    last one is empty, and counts the same.
    """
    years = _years(session, filters.states)
    criteria = _criteria(filters)
    from_categories = select(CostCategory).join(CostType, CostType.id == CostCategory.cost_type_id)
    total = session.scalars(
        select(func.count()).select_from(from_categories.where(*criteria).subquery())
    ).one()
    order = (*_keys(sort), CostCategory.code, CostCategory.id)
    categories = list(
        session.scalars(
            from_categories.where(*criteria).order_by(*order).limit(page.limit).offset(page.offset)
        )
    )
    rates = session.scalars(
        select(HourlyRate).where(
            HourlyRate.cost_category_id.in_([category.id for category in categories])
        )
    )
    held = {(view.cost_category_id, view.year): view for view in _views(session, list(rates))}
    rows = [
        HourlyRateRow(
            category.id,
            category.code,
            category.label,
            category.is_active,
            tuple(held.get((category.id, year)) for year in years),
        )
        for category in categories
    ]
    return HourlyRateGridPage(years, rows, total)


def list_hourly_rates(session: Session, category_id: UUID) -> list[HourlyRateView]:
    """Give the rates of a category, by year; refused if the category is unknown (404)."""
    if session.get(CostCategory, category_id) is None:
        raise NotFoundError(NOT_FOUND)
    rates = session.scalars(
        select(HourlyRate)
        .where(HourlyRate.cost_category_id == category_id)
        .order_by(HourlyRate.year)
    )
    return _views(session, list(rates))


def _amount_fault(amount: Decimal) -> FieldError | None:
    """Name the bound a rate breaks: positive, and no greater than the column holds."""
    if amount < SMALLEST_RATE:
        return FieldError("/amount", VALUE_OUT_OF_RANGE, {"minimum": str(SMALLEST_RATE)})
    if amount > GREATEST_RATE:
        return FieldError("/amount", VALUE_OUT_OF_RANGE, {"maximum": str(GREATEST_RATE)})
    return None


def _refuse_unless_labour(session: Session, category_id: UUID) -> None:
    """Refuse a category that is unknown (404), or whose nature is not of labour (422)."""
    kind = session.scalars(
        select(CostType.kind)
        .join(CostCategory, CostCategory.cost_type_id == CostType.id)
        .where(CostCategory.id == category_id)
    ).first()
    if kind is None:
        raise NotFoundError(NOT_FOUND)
    if kind != LABOUR:
        raise UnprocessableError(LABOUR_CATEGORY_REQUIRED)


def set_hourly_rate(
    session: Session,
    key: tuple[UUID, int],
    amount: Decimal,
    lock_version: int | None,
    act: Act,
) -> HourlyRateView:
    """Set the rate of a category for a year, once, then correct it at the version read.

    ``key`` is the category and the year. Without ``lock_version``, the rate is set: the year must
    bear none (409 ``ALREADY_EXISTS``, nothing written). With it, the rate is corrected: refused if
    there is none (404) or if its version is another (412). An amount under 0.01, or beyond what
    the column holds, is refused (422) first; then a category whose nature is not of labour (422,
    ``LABOUR_CATEGORY_REQUIRED``), or unknown (404).

    The lock of the natures comes first, as for every write that reads the kind of a nature: a
    nature never changes kind between the reading of the category and the writing of its rate,
    and two settings of one year never meet.
    """
    category_id, year = key
    fault = _amount_fault(amount)
    if fault is not None:
        raise UnprocessableError(VALIDATION_FAILED, fields=(fault,))
    lock_natures(session)
    _refuse_unless_labour(session, category_id)
    current = session.scalars(
        select(HourlyRate)
        .where(HourlyRate.cost_category_id == category_id, HourlyRate.year == year)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if lock_version is None:
        if current is not None:
            raise ConflictError(ALREADY_EXISTS)
        session.execute(
            insert(HourlyRate).values(
                id=new_id(),
                cost_category_id=category_id,
                year=year,
                amount=amount,
                lock_version=FIRST_VERSION,
                created_at=act.at,
                created_by=act.author,
                updated_at=act.at,
                updated_by=act.author,
            )
        )
    else:
        if current is None:
            raise NotFoundError(NOT_FOUND)
        if current.lock_version != lock_version:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": current.lock_version}
            )
        current.amount = amount
        current.lock_version += 1
        current.updated_at = act.at
        current.updated_by = act.author
        session.flush()
    rate = session.scalars(
        select(HourlyRate)
        .where(HourlyRate.cost_category_id == category_id, HourlyRate.year == year)
        .execution_options(populate_existing=True)
    ).one()
    return _views(session, [rate])[0]
