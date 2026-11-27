# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The consultation of the journal of audit: a flat table, filtered, sorted, read by pages.

The journal is read as ``listAuditEvents`` describes it (FBS-1.5, WF-ADM-0190): filtered by
period, author, action, project, object, correlation and a search on the label the inscription
keeps — the filters combine (WF-IHM-0130) —, and sorted on each of its seven columns
(WF-IHM-0060). Without a sort, by date, the latest first, two inscriptions of one instant in the
reverse order of their inscription; a sort on another column keeps that order between two
inscriptions it holds equal, whichever its direction. A column without a value — a backup, which
has no label, an inscription without a project — comes after the others in the ascending order,
before them in the descending one; on the author, an account anonymised, which has lost its name,
comes after the names, and the platform, which has none, after the accounts. Nothing here writes:
the journal is read only.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import (
    ColumnElement,
    Select,
    SQLColumnExpression,
    func,
    literal_column,
    select,
    true,
)
from sqlalchemy.orm import aliased

from waterfall.platform.audit import (
    ACTION_RANK,
    ACTOR_ORDER,
    OBJECT_KIND_RANK,
    AuditEntry,
    AuditProject,
)
from waterfall.platform.database import contains

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from sqlalchemy.orm import InstrumentedAttribute, Session
    from sqlalchemy.sql.elements import UnaryExpression

type AuditColumn = Literal[
    "occurred_at", "actor", "action", "object_kind", "object_label", "project", "correlation_id"
]
type ActorKind = Literal["user", "platform"]

# The expressions each column other than the date sorts by, in turn: the author is an account
# before the platform (``ACTOR_ORDER``), then by its name.
_SORTED_BY: dict[str, tuple[SQLColumnExpression[Any], ...]] = {
    "actor": (literal_column(ACTOR_ORDER[0]), AuditEntry.actor_display_name),
    "action": (literal_column(ACTION_RANK),),
    "object_kind": (literal_column(OBJECT_KIND_RANK),),
    "object_label": (AuditEntry.object_label,),
    "project": (AuditEntry.project_code,),
    "correlation_id": (AuditEntry.correlation_id,),
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
    contract does: the name of an account anonymised after the names, and the platform after the
    accounts.
    """
    latest: list[UnaryExpression[Any]] = [AuditEntry.occurred_at.desc(), AuditEntry.id.desc()]
    if sort.column is None or sort.column == "occurred_at":
        if sort.descending is False:
            return [AuditEntry.occurred_at.asc(), AuditEntry.id.asc()]
        return latest
    asked = [each.desc() if sort.descending else each.asc() for each in _SORTED_BY[sort.column]]
    return [*asked, *latest]


def journal_query(filters: AuditFilters, sort: AuditSort) -> Select[AuditEntry]:
    """Select the inscriptions the filters keep, in the order the sort asks for."""
    return select(AuditEntry).where(*_kept(filters)).order_by(*_order(sort))


def page_statement(
    filters: AuditFilters, sort: AuditSort, limit: int, offset: int
) -> Select[Any, Any, AuditEntry]:
    """Build the one statement that reads the total and the page, the page hung from the total."""
    kept = select(func.count().label("total")).select_from(AuditEntry).where(*_kept(filters))
    counted = kept.subquery()
    ranked = journal_query(filters, sort).add_columns(
        func.row_number().over(order_by=_order(sort)).label("rank")
    )
    page = ranked.limit(limit).offset(offset).subquery().lateral()
    entry = aliased(AuditEntry, page)
    read = select(counted.c.total, page.c.id, entry).select_from(counted).outerjoin(page, true())
    return read.order_by(page.c.rank)


def list_entries(
    session: Session, filters: AuditFilters, sort: AuditSort, limit: int, offset: int
) -> AuditPage:
    """Give a page of the journal, filtered and sorted, and how many inscriptions it keeps.

    The total and the page are read by one statement, so on one snapshot (#928): in ``READ
    COMMITTED``, two statements each see what was committed before it, and an inscription made
    between them would be in the page and not in the total. The isolation of a transaction already
    begun cannot be raised, and the one of the route has begun; ``count(*) OVER ()`` would give no
    total to a page past the end, which holds no row to bear it — so the page hangs, by a lateral
    join, from the one row that counts. A page past the end gives that row alone, its entry null.
    """
    rows = session.execute(page_statement(filters, sort, limit, offset)).all()
    return AuditPage([row[2] for row in rows if row.id is not None], rows[0].total)


def latest_first(key: InstrumentedAttribute[UUID | None]) -> Select[AuditEntry]:
    """Select, for each value of ``key`` the journal holds, the latest inscription that bears it.

    The values are walked one after the other, each the next above the previous in the index of
    ``key`` (a loose index scan, which PostgreSQL does not write by itself), and the latest
    inscription of each is one probe of the composite index that follows ``key`` with the date and
    the identifier, in descending order: the journal is not read whole, nor sorted, as a
    ``DISTINCT ON`` would (#934).
    """
    keys = (
        select(key.label("key"))
        .where(key.is_not(None))
        .order_by(key)
        .limit(1)
        .cte("keys", recursive=True)
    )
    after = select(key).where(key > keys.c.key).order_by(key).limit(1).scalar_subquery()
    keys = keys.union_all(select(after).where(keys.c.key.is_not(None)))
    probe = (
        select(AuditEntry)
        .where(key == keys.c.key)
        .order_by(AuditEntry.occurred_at.desc(), AuditEntry.id.desc())
        .limit(1)
        .lateral()
    )
    latest = aliased(AuditEntry, probe)
    return select(latest).select_from(keys).join(probe, true()).where(keys.c.key.is_not(None))


def journal_actors(session: Session) -> list[ActorNamed]:
    """Give each account that wrote in the journal once, by the name its latest inscription keeps.

    The platform is no account: ``actor_kind`` keeps it.
    """
    latest = session.scalars(latest_first(AuditEntry.actor_user_id))
    return [
        ActorNamed(entry.actor_user_id, entry.actor_display_name)
        for entry in latest
        if entry.actor_user_id is not None
    ]


def by_code(project: AuditProject) -> tuple[bool, str, UUID]:
    """Sort the projects of the journal by their code, those without one last, then by identifier.

    Codes are compared code point by code point; a project without code comes after the codes, as
    the sort of the journal on its project puts it (#2166).
    """
    return (project.code is None, project.code or "", project.project_id)


def journal_projects(session: Session) -> list[AuditProject]:
    """Give each project of the journal once, by the code and the label of its latest inscription.

    A project without code is given all the same, its code null (#2166); in the order of
    ``by_code``. The journal knows nothing of the projects: the API names the ones that still exist
    by their code and label of today, read through the module of the projects (#927).
    """
    latest = session.scalars(latest_first(AuditEntry.project_id))
    projects = [
        AuditProject(entry.project_id, entry.project_code, entry.project_label)
        for entry in latest
        if entry.project_id is not None and entry.project_label is not None
    ]
    return sorted(projects, key=by_code)
