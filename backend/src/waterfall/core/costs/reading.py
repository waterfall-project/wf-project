# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the lines of the actual costs of a project, private to the module (US-1620/L1).

One query retains the lines — the subproject, the period on the date of the document, the scope
tracked —, and serves the page, sorted and paginated, and the aggregates of the whole set retained:
the three totals, the instant of the last import and the columns kept of the files (WF-CRE-0040,
WF-CRE-0010). A filter the service cannot apply is refused on its parameter, never answered by an
empty list (422).
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ColumnElement, case, collate, func, select

from waterfall.core.costs.tables import CostImport, CostLine
from waterfall.core.projects.interface import subproject_labels
from waterfall.core.users.interface import read_authors
from waterfall.platform.database import CODE_POINTS
from waterfall.platform.errors import FieldError, UnprocessableError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date, datetime

    from sqlalchemy.orm import Session

    from waterfall.core.users.interface import Author

VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
UNKNOWN_SUBPROJECT = "UNKNOWN_SUBPROJECT"
UNASSIGNED = "unassigned"
PASSTHROUGH = "passthrough."
# The columns of the grid a sort names, and the column of the table each sorts by. The subproject
# is the code read in the WBS element, whether or not a subproject bears it (``ActualCostColumn``).
COLUMNS = {
    "document_date": CostLine.document_date,
    "document_number": CostLine.document_number,
    "document_item": CostLine.document_item,
    "amount": CostLine.amount,
    "subproject": CostLine.subproject_code,
    "in_tracked_scope": CostLine.is_in_tracked_scope,
    "excluded_reason": CostLine.excluded_reason,
}
# An empty sum is written to the cent, as every amount is.
ZERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class CostLineFilters:
    """What retains the lines: a subproject (or ``unassigned``), a period, the scope tracked.

    The subproject is the text the query carries: the identifier of a subproject of the project, or
    ``unassigned`` for the lines charged to the project alone. The period is on the date of the
    document, its ends included; ``in_tracked_scope`` true keeps the tracked lines, false the
    excluded ones, none all of them.
    """

    subproject: str | None = None
    since: date | None = None
    until: date | None = None
    in_tracked_scope: bool | None = None


@dataclass(frozen=True, slots=True)
class CostLineSort:
    """The column a page is sorted by, none for the most recent documents first, and its way.

    ``passthrough.<column>`` names a column kept of the files; each column compares as text, in
    code point order, a line without a value after the others in ascending order.
    """

    column: str | None = None
    descending: bool = False


@dataclass(frozen=True, slots=True)
class CostLinePage:
    """The page asked for: its size, and the lines skipped before it."""

    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class CostLineView:
    """A line of the actual costs as it is read: its charging resolved, its authors named."""

    cost_line_id: UUID
    document_number: str
    document_item: str | None
    document_date: date
    amount: Decimal
    project_id: UUID
    subproject_id: UUID | None
    subproject_code: str | None
    subproject_label: str | None
    is_in_tracked_scope: bool
    excluded_reason: str | None
    passthrough: dict[str, str]
    created_at: datetime
    created_by: Author | None
    updated_at: datetime
    updated_by: Author | None


@dataclass(frozen=True, slots=True)
class CostTotals:
    """The three totals of the lines retained: the tracked scope, the excluded, and their sum."""

    tracked: Decimal
    excluded: Decimal
    overall: Decimal


@dataclass(frozen=True, slots=True)
class CostLineList:
    """A page of the lines retained, and what the whole set retained says.

    ``total`` counts the lines retained, ``totals`` sums them, ``last_import_at`` is the latest
    instant of the imports they name, none without a line, and ``passthrough_columns`` the columns
    kept of the files of those imports, in the order the imports declared them.
    """

    views: list[CostLineView]
    total: int
    totals: CostTotals
    last_import_at: datetime | None
    passthrough_columns: list[str] = field(default_factory=list[str])


def _refuse_filters(session: Session, project_id: UUID, filters: CostLineFilters) -> UUID | None:
    """Refuse a period whose end precedes its start and an unknown subproject; give the subproject.

    Both are named together, each on its own parameter: the end of the period, the start its
    minimum, and the subproject asked (``UNKNOWN_SUBPROJECT``, WF-CRE-0040).
    """
    faults: list[FieldError] = []
    since, until = filters.since, filters.until
    if since is not None and until is not None and until < since:
        faults.append(FieldError("/query/to", VALUE_OUT_OF_RANGE, {"minimum": since}))
    subproject_id = None
    asked = filters.subproject
    if asked is not None and asked != UNASSIGNED:
        try:
            subproject_id = UUID(asked)
        except ValueError:
            subproject_id = None
        if subproject_id is None or not subproject_labels(session, project_id, [subproject_id]):
            faults.append(FieldError("/query/subproject_id", UNKNOWN_SUBPROJECT))
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=tuple(faults))
    return subproject_id


def _retaining(
    project_id: UUID, filters: CostLineFilters, subproject_id: UUID | None
) -> list[ColumnElement[bool]]:
    conditions = [CostLine.project_id == project_id]
    if filters.subproject == UNASSIGNED:
        conditions.append(CostLine.subproject_id.is_(None))
    elif subproject_id is not None:
        conditions.append(CostLine.subproject_id == subproject_id)
    if filters.since is not None:
        conditions.append(CostLine.document_date >= filters.since)
    if filters.until is not None:
        conditions.append(CostLine.document_date <= filters.until)
    if filters.in_tracked_scope is not None:
        conditions.append(CostLine.is_in_tracked_scope == filters.in_tracked_scope)
    return conditions


def _sorted_by(sort: CostLineSort) -> list[ColumnElement[Any]]:
    """Order the lines: the column asked for, the identifier last so that no line is read twice."""
    if sort.column is None:
        return [CostLine.document_date.desc(), CostLine.id.asc()]
    if sort.column.startswith(PASSTHROUGH):
        name = sort.column.removeprefix(PASSTHROUGH)
        key = collate(func.jsonb_extract_path_text(CostLine.passthrough, name), CODE_POINTS)
    else:
        key = COLUMNS[sort.column]
    # PostgreSQL puts the nulls last in ascending order and first in descending order.
    ordered = key.desc().nulls_first() if sort.descending else key.asc().nulls_last()
    return [ordered, CostLine.id.asc()]


def _passthrough_columns(session: Session, conditions: Sequence[ColumnElement[bool]]) -> list[str]:
    """Give the columns kept of the imports the lines retained name, each at its first declaration.

    The imports in the order they were applied, the columns of an import in the order of its file.
    """
    named = select(CostLine.last_import_id).where(*conditions).distinct()
    declared = session.scalars(
        select(CostImport.passthrough_columns)
        .where(CostImport.id.in_(named))
        .order_by(CostImport.imported_at, CostImport.id)
    )
    return list(dict.fromkeys(column for columns in declared for column in columns))


def views_of(session: Session, project_id: UUID, rows: Sequence[CostLine]) -> list[CostLineView]:
    """Describe lines as they are read: their subproject labelled, their authors named today."""
    labels = subproject_labels(
        session, project_id, {row.subproject_id for row in rows if row.subproject_id is not None}
    )
    authors = read_authors(
        session,
        {
            author
            for row in rows
            for author in (row.created_by, row.updated_by)
            if author is not None
        },
    )
    return [
        CostLineView(
            cost_line_id=row.id,
            document_number=row.document_number,
            document_item=row.document_item,
            document_date=row.document_date,
            amount=row.amount,
            project_id=row.project_id,
            subproject_id=row.subproject_id,
            subproject_code=row.subproject_code,
            subproject_label=None if row.subproject_id is None else labels.get(row.subproject_id),
            is_in_tracked_scope=row.is_in_tracked_scope,
            excluded_reason=row.excluded_reason,
            passthrough=dict(row.passthrough),
            created_at=row.created_at,
            created_by=None if row.created_by is None else authors.get(row.created_by),
            updated_at=row.updated_at,
            updated_by=None if row.updated_by is None else authors.get(row.updated_by),
        )
        for row in rows
    ]


def read_lines(
    session: Session,
    project_id: UUID,
    filters: CostLineFilters,
    sort: CostLineSort,
    page: CostLinePage,
) -> CostLineList:
    """Read a page of the lines retained, and the totals of the whole set retained."""
    subproject_id = _refuse_filters(session, project_id, filters)
    conditions = _retaining(project_id, filters, subproject_id)
    tracked = func.sum(case((CostLine.is_in_tracked_scope, CostLine.amount), else_=0))
    excluded = func.sum(case((CostLine.is_in_tracked_scope, 0), else_=CostLine.amount))
    count, tracked_sum, excluded_sum, last_import_at = session.execute(
        select(func.count(), tracked, excluded, func.max(CostImport.imported_at))
        .select_from(CostLine)
        .join(CostImport, CostImport.id == CostLine.last_import_id)
        .where(*conditions)
    ).one()
    rows = session.scalars(
        select(CostLine)
        .where(*conditions)
        .order_by(*_sorted_by(sort))
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    kept, dropped = tracked_sum or ZERO, excluded_sum or ZERO
    return CostLineList(
        views_of(session, project_id, rows),
        count,
        CostTotals(kept, dropped, kept + dropped),
        last_import_at,
        _passthrough_columns(session, conditions),
    )
