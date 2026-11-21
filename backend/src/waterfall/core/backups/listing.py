# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The list of the backups, filtered and sorted as ``listBackups`` describes it (WF-IHM-0130).

Each column filters: the date by a period, from its start included to its end excluded; the origin
and the verification by the values kept; the mark; the size by its two bounds, included. The
filters combine. Each column sorts (WF-IHM-0060): the date, the size, the verification and the
origin in the order of their enumeration, the mark with the backups marked first in the ascending
order. Without a sort, by date, the latest first; a tie is broken by that order, then by the
identifier, whichever the direction. Nothing here writes.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import ColumnElement, SQLColumnExpression, case, func, select

from waterfall.core.backups.tables import ORIGINS, VERIFICATIONS, Backup

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import Session

type BackupColumn = Literal["taken_at", "size_bytes", "verification", "origin", "is_retained"]


@dataclass(frozen=True, slots=True)
class BackupView:
    """A backup as the API gives it, and the key of its archive in the bucket of the backups."""

    backup_id: UUID
    taken_at: datetime
    size_bytes: int
    verification: str
    origin: str
    is_retained: bool
    object_key: str


@dataclass(frozen=True, slots=True)
class BackupFilters:
    """What the list keeps: each filter given narrows it, ``None`` leaves it whole.

    The period runs from ``since``, included, to ``until``, excluded; the size from ``size_min`` to
    ``size_max``, both included.
    """

    since: datetime | None = None
    until: datetime | None = None
    origins: frozenset[str] | None = None
    verifications: frozenset[str] | None = None
    is_retained: bool | None = None
    size_min: int | None = None
    size_max: int | None = None


@dataclass(frozen=True, slots=True)
class BackupSort:
    """The column the list sorts on, the date if none, and its direction.

    ``descending`` absent, the date sorts the latest first and any other column ascending.
    """

    column: BackupColumn | None = None
    descending: bool | None = None


# What each column sorts by: the enumerations by their rank, the mark by the marked first.
_VERIFICATION_RANK = case(
    dict(zip(VERIFICATIONS, range(len(VERIFICATIONS)), strict=True)), value=Backup.verification
)
_ORIGIN_RANK = case(dict(zip(ORIGINS, range(len(ORIGINS)), strict=True)), value=Backup.origin)
_SORTED_BY: dict[str, SQLColumnExpression[Any]] = {
    "taken_at": Backup.taken_at,
    "size_bytes": Backup.size_bytes,
    "verification": _VERIFICATION_RANK,
    "origin": _ORIGIN_RANK,
    "is_retained": case((Backup.is_retained, 0), else_=1),
}


def view_of(row: Backup) -> BackupView:
    """Describe a row of the backups as the module offers it."""
    return BackupView(
        row.id,
        row.taken_at,
        row.size_bytes,
        row.verification,
        row.origin,
        row.is_retained,
        row.object_key,
    )


def _kept(filters: BackupFilters) -> list[ColumnElement[bool]]:
    kept: list[ColumnElement[bool]] = []
    if filters.since is not None:
        kept.append(Backup.taken_at >= filters.since)
    if filters.until is not None:
        kept.append(Backup.taken_at < filters.until)
    if filters.origins is not None:
        kept.append(Backup.origin.in_(filters.origins))
    if filters.verifications is not None:
        kept.append(Backup.verification.in_(filters.verifications))
    if filters.is_retained is not None:
        kept.append(Backup.is_retained == filters.is_retained)
    if filters.size_min is not None:
        kept.append(Backup.size_bytes >= filters.size_min)
    if filters.size_max is not None:
        kept.append(Backup.size_bytes <= filters.size_max)
    return kept


def list_backups(
    session: Session, filters: BackupFilters, sort: BackupSort, limit: int, offset: int
) -> tuple[list[BackupView], int]:
    """Give a page of the backups the filters keep, sorted, and how many the filters keep."""
    kept = _kept(filters)
    total = session.scalar(select(func.count()).select_from(Backup).where(*kept))
    column = sort.column or "taken_at"
    descending = sort.descending if sort.descending is not None else column == "taken_at"
    ranked = _SORTED_BY[column]
    ordered = (
        ranked.desc() if descending else ranked.asc(),
        Backup.taken_at.desc(),
        Backup.id.desc(),
    )
    page = select(Backup).where(*kept).order_by(*ordered).limit(limit).offset(offset)
    return [view_of(row) for row in session.scalars(page)], total or 0
