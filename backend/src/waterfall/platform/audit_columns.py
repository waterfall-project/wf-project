# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The columns of audit of a flat table, filtered as each other column (WF-DAT-0070, WF-IHM-0130).

Every table whose rows change has them: the moment of its creation and its author, of its last
change and its author, an account or the platform, ``None``. Each date is filtered by a period, its
start included, its end excluded, as the journal of audit reads its own; each author by an account,
deactivated or anonymised included (WF-ADM-0060), or by its kind, an account or the platform. The
module that owns a table gives its columns (``AuditColumns``): no table is named here.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import ColumnElement, SQLColumnExpression

type AuthorKind = Literal["user", "platform"]


@dataclass(frozen=True, slots=True)
class Period:
    """Instants from ``since``, included, to ``until``, excluded; a bound absent bounds nothing."""

    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True, slots=True)
class AuthorFilter:
    """The author kept: an account by its identifier, or a kind of author; absent, any."""

    user_id: UUID | None = None
    kind: AuthorKind | None = None


@dataclass(frozen=True, slots=True)
class AuditColumnFilters:
    """What the columns of audit keep: each filter absent keeps everything."""

    created: Period = Period()
    created_by: AuthorFilter = AuthorFilter()
    updated: Period = Period()
    updated_by: AuthorFilter = AuthorFilter()


@dataclass(frozen=True, slots=True)
class AuditColumns:
    """The columns of audit of a table, which its module gives."""

    created_at: SQLColumnExpression[datetime]
    created_by: SQLColumnExpression[UUID | None]
    updated_at: SQLColumnExpression[datetime]
    updated_by: SQLColumnExpression[UUID | None]


def _within(column: SQLColumnExpression[datetime], period: Period) -> list[ColumnElement[bool]]:
    kept: list[ColumnElement[bool]] = []
    if period.since is not None:
        kept.append(column >= period.since)
    if period.until is not None:
        kept.append(column < period.until)
    return kept


def _by(
    column: SQLColumnExpression[UUID | None], author: AuthorFilter
) -> list[ColumnElement[bool]]:
    kept: list[ColumnElement[bool]] = []
    if author.user_id is not None:
        kept.append(column == author.user_id)
    if author.kind == "user":
        kept.append(column.is_not(None))
    elif author.kind == "platform":
        kept.append(column.is_(None))
    return kept


def audit_criteria(columns: AuditColumns, filters: AuditColumnFilters) -> list[ColumnElement[bool]]:
    """Give the criteria the filters of the columns of audit put on a table; they combine."""
    return [
        *_within(columns.created_at, filters.created),
        *_by(columns.created_by, filters.created_by),
        *_within(columns.updated_at, filters.updated),
        *_by(columns.updated_by, filters.updated_by),
    ]
