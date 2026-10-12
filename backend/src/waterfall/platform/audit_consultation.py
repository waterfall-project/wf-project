# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The consultation of the journal of audit: a flat table, filtered, sorted, read by pages.

The journal is read as ``listAuditEvents`` describes it (FBS-1.5, WF-ADM-0190): filtered by
period, author, action, project, object, correlation and a search on the label the inscription
keeps — the filters combine (WF-IHM-0130) —, and sorted on each of its seven columns
(WF-IHM-0060). Without a sort, by date, the latest first, two inscriptions of one instant in the
reverse order of their inscription; a sort on another column keeps that order between two
inscriptions it holds equal, whichever its direction. A column without a value — the platform,
which shows no name, a backup, which has no label, an inscription without a project — comes
after the others in the ascending order, before them in the descending one. Nothing here writes:
the journal is read only.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import ColumnElement, Select, SQLColumnExpression, func, literal_column, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.elements import UnaryExpression

from waterfall.platform.audit import (
    ACTION_RANK,
    OBJECT_KIND_RANK,
    AuditEntry,
    AuditProject,
)
from waterfall.platform.database import contains

type AuditColumn = Literal[
    "occurred_at", "actor", "action", "object_kind", "object_label", "project", "correlation_id"
]
type ActorKind = Literal["user", "platform"]

# The expression each column other than the date sorts by.
_SORTED_BY: dict[str, SQLColumnExpression[Any]] = {
    "actor": AuditEntry.actor_display_name,
    "action": literal_column(ACTION_RANK),
    "object_kind": literal_column(OBJECT_KIND_RANK),
    "object_label": AuditEntry.object_label,
    "project": AuditEntry.project_code,
    "correlation_id": AuditEntry.correlation_id,
}


@dataclass(frozen=True, slots=True)
class AuditFilters:
    """What the journal keeps: each filter given narrows it, ``None`` leaves it whole.

    The period runs from ``since``, included, to ``until``, excluded; ``search`` looks for a text
    in the label of the object, whatever its case and accents.
    """

    since: datetime | None = None
    until: datetime | None = None
    user_id: UUID | None = None
    actor_kind: ActorKind | None = None
    actions: frozenset[str] | None = None
    project_id: UUID | None = None
    object_kind: str | None = None
    object_id: UUID | None = None
    correlation_id: str | None = None
    search: str | None = None


@dataclass(frozen=True, slots=True)
class AuditSort:
    """The column the journal sorts on, the date if none, and its direction.

    ``descending`` absent, the date sorts the latest first and any other column ascending.
    """

    column: AuditColumn | None = None
    descending: bool | None = None


@dataclass(frozen=True, slots=True)
class AuditPage:
    """The inscriptions of a page, and how many the filters keep."""

    entries: list[AuditEntry]
    total: int


@dataclass(frozen=True, slots=True)
class ActorNamed:
    """An account that wrote in the journal, with the name its latest inscription keeps."""

    user_id: UUID
    display_name: str | None


def _kept(filters: AuditFilters) -> list[ColumnElement[bool]]:
    kept: list[ColumnElement[bool]] = []
    if filters.since is not None:
        kept.append(AuditEntry.occurred_at >= filters.since)
    if filters.until is not None:
        kept.append(AuditEntry.occurred_at < filters.until)
    if filters.user_id is not None:
        kept.append(AuditEntry.actor_user_id == filters.user_id)
    if filters.actor_kind == "user":
        kept.append(AuditEntry.actor_user_id.is_not(None))
    elif filters.actor_kind == "platform":
        kept.append(AuditEntry.actor_user_id.is_(None))
    if filters.actions is not None:
        kept.append(AuditEntry.action.in_(filters.actions))
    if filters.project_id is not None:
        kept.append(AuditEntry.project_id == filters.project_id)
    if filters.object_kind is not None:
        kept.append(AuditEntry.object_kind == filters.object_kind)
    if filters.object_id is not None:
        kept.append(AuditEntry.object_id == filters.object_id)
    if filters.correlation_id is not None:
        kept.append(AuditEntry.correlation_id == filters.correlation_id)
    if filters.search is not None:
        kept.append(contains(AuditEntry.object_label, filters.search))
    return kept


def _order(sort: AuditSort) -> list[UnaryExpression[Any]]:
    """Give the order of the page: the column asked for, then the journal's own order.

    PostgreSQL puts a null last in the ascending order and first in the descending one, as the
    contract does.
    """
    latest: list[UnaryExpression[Any]] = [AuditEntry.occurred_at.desc(), AuditEntry.id.desc()]
    if sort.column is None or sort.column == "occurred_at":
        if sort.descending is False:
            return [AuditEntry.occurred_at.asc(), AuditEntry.id.asc()]
        return latest
    expression = _SORTED_BY[sort.column]
    return [expression.desc() if sort.descending else expression.asc(), *latest]


def journal_query(filters: AuditFilters, sort: AuditSort) -> Select[AuditEntry]:
    """Select the inscriptions the filters keep, in the order the sort asks for."""
    return select(AuditEntry).where(*_kept(filters)).order_by(*_order(sort))


def list_entries(
    session: Session, filters: AuditFilters, sort: AuditSort, limit: int, offset: int
) -> AuditPage:
    """Give a page of the journal, filtered and sorted, and how many inscriptions it keeps."""
    total = session.scalar(select(func.count()).select_from(AuditEntry).where(*_kept(filters)))
    page = journal_query(filters, sort).limit(limit).offset(offset)
    return AuditPage(list(session.scalars(page)), total or 0)


def _latest_first(key: InstrumentedAttribute[UUID | None]) -> Select[AuditEntry]:
    """Select, for each value of ``key`` the journal holds, the latest inscription that bears it."""
    return (
        select(AuditEntry)
        .where(key.is_not(None))
        .ext(distinct_on(key))
        .order_by(key, AuditEntry.occurred_at.desc(), AuditEntry.id.desc())
    )


def journal_actors(session: Session) -> list[ActorNamed]:
    """Give each account that wrote in the journal once, by the name its latest inscription keeps.

    The platform is no account: ``actor_kind`` keeps it.
    """
    latest = session.scalars(_latest_first(AuditEntry.actor_user_id))
    return [
        ActorNamed(entry.actor_user_id, entry.actor_display_name)
        for entry in latest
        if entry.actor_user_id is not None
    ]


def journal_projects(session: Session) -> list[AuditProject]:
    """Give each project of the journal once, by the code and the label of its latest inscription.

    In the order of the codes, compared code point by code point, then of the identifiers. The
    contract names a project by its code and its label of today, those of its latest inscription
    only for one that no longer exists: there are no projects yet, and the code and the label are
    always those of the latest inscription, until the module of the projects reads them (#927,
    EP-04).
    """
    latest = session.scalars(_latest_first(AuditEntry.project_id))
    projects = [
        AuditProject(entry.project_id, entry.project_code, entry.project_label)
        for entry in latest
        if entry.project_id is not None
        and entry.project_code is not None
        and entry.project_label is not None
    ]
    return sorted(projects, key=lambda project: (project.code, project.project_id))
