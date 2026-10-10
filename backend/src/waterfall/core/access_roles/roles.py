# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the roles and of the catalogue, private to the module.

A role is never removed: its deletion marks it, and a role so marked is read by nothing here,
while its row stays for the journal of audit and the past attributions that cite it (WF-DAT-0080,
WF-ADM-0090).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import BigInteger, ColumnElement, Select, Text, func, literal, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.core.users.interface import Author, read_author
from waterfall.platform.errors import NotFoundError

NOT_FOUND = "NOT_FOUND"

# The search ignores case and accents, lowered in a collation that knows every letter: that of
# the label, the code points, lowers none but the ASCII ones (contract, README, "Une recherche").
SEARCH_COLLATION = "und-x-icu"

type SortColumn = Literal["label", "is_predefined", "holder_count"]


@dataclass(frozen=True, slots=True)
class CataloguePermission:
    """A permission of the catalogue: its code, its kind, the function of second level it covers."""

    code: str
    kind: str
    fbs_code: str | None


@dataclass(frozen=True, slots=True)
class RoleView:
    """A role as it is read: its permissions in the order of the catalogue, its holders counted."""

    access_role_id: UUID
    label: str
    permissions: tuple[str, ...]
    is_predefined: bool
    holder_count: int
    created_at: datetime
    created_by: Author | None
    updated_at: datetime
    updated_by: Author | None
    lock_version: int


@dataclass(frozen=True, slots=True)
class RoleFilters:
    """What the table of the roles keeps: each filter absent keeps everything (WF-IHM-0130)."""

    search: str | None = None
    is_predefined: bool | None = None
    holder_count_min: int | None = None
    holder_count_max: int | None = None


@dataclass(frozen=True, slots=True)
class RoleSort:
    """The column of the sort and its direction; equals are ordered by identifier (WF-IHM-0060)."""

    column: SortColumn = "label"
    descending: bool = False


def list_permissions(session: Session) -> list[CataloguePermission]:
    """Read the catalogue, in its order."""
    rows = session.execute(
        select(Permission.code, Permission.kind, Permission.fbs_code).order_by(Permission.position)
    )
    return [CataloguePermission(code, kind, fbs_code) for code, kind, fbs_code in rows]


def _holder_counts() -> Select[UUID, int]:
    return select(UserAccessRole.access_role_id, func.count().label("holder_count")).group_by(
        UserAccessRole.access_role_id
    )


def _roles() -> tuple[Select[AccessRole, int], ColumnElement[int]]:
    """Select the roles not deleted, each with the number of accounts that hold it."""
    counts = _holder_counts().subquery()
    # A count is a ``bigint``: a bound compared with it is one too, not an ``integer``.
    holder_count = func.coalesce(counts.c.holder_count, 0, type_=BigInteger)
    query = (
        select(AccessRole, holder_count)
        .outerjoin(counts, counts.c.access_role_id == AccessRole.id)
        .where(AccessRole.deleted_at.is_(None))
    )
    return query, holder_count


def _folded(text: ColumnElement[str] | InstrumentedAttribute[str]) -> ColumnElement[str]:
    return func.lower(func.unaccent(text).collate(SEARCH_COLLATION))


def list_roles(session: Session, filters: RoleFilters, sort: RoleSort) -> list[RoleView]:
    """Read the roles the filters keep, in the order of the sort, equals by their identifier."""
    query, holder_count = _roles()
    if filters.search is not None:
        searched = _folded(literal(filters.search, Text))
        query = query.where(func.strpos(_folded(AccessRole.label), searched) > 0)
    if filters.is_predefined is not None:
        query = query.where(AccessRole.is_predefined.is_(filters.is_predefined))
    if filters.holder_count_min is not None:
        query = query.where(holder_count >= filters.holder_count_min)
    if filters.holder_count_max is not None:
        query = query.where(holder_count <= filters.holder_count_max)
    # The predefined before the composed in the ascending order: true sorts after false.
    keys: dict[SortColumn, ColumnElement[Any] | InstrumentedAttribute[Any]] = {
        "label": AccessRole.label,
        "is_predefined": ~AccessRole.is_predefined,
        "holder_count": holder_count,
    }
    key = keys[sort.column]
    order = (key.desc(), AccessRole.id.desc()) if sort.descending else (key, AccessRole.id)
    return _views(session, session.execute(query.order_by(*order)).all())


def read_role(session: Session, role_id: UUID) -> RoleView:
    """Read a role that is not deleted, or refuse (404)."""
    query, _ = _roles()
    rows = session.execute(query.where(AccessRole.id == role_id)).all()
    if not rows:
        raise NotFoundError(NOT_FOUND)
    return _views(session, rows)[0]


def _views(session: Session, rows: Sequence[tuple[AccessRole, int]]) -> list[RoleView]:
    granted: dict[UUID, list[str]] = {role.id: [] for role, _ in rows}
    for role_id, code in session.execute(
        select(AccessRolePermission.access_role_id, Permission.code)
        .join(Permission, Permission.id == AccessRolePermission.permission_id)
        .where(AccessRolePermission.access_role_id.in_(granted))
        .order_by(Permission.position)
    ):
        granted[role_id].append(code)
    authors: dict[UUID | None, Author | None] = {}

    def author(user_id: UUID | None) -> Author | None:
        if user_id not in authors:
            authors[user_id] = read_author(session, user_id)
        return authors[user_id]

    return [
        RoleView(
            access_role_id=role.id,
            label=role.label,
            permissions=tuple(granted[role.id]),
            is_predefined=role.is_predefined,
            holder_count=holders,
            created_at=role.created_at,
            created_by=author(role.created_by),
            updated_at=role.updated_at,
            updated_by=author(role.updated_by),
            lock_version=role.lock_version,
        )
        for role, holders in rows
    ]
