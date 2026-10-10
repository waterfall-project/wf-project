# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The data access of the roles and of the catalogue, private to the module.

A role is never removed: its deletion marks it, and a role so marked is read by nothing here —
neither listed, nor read, nor changed, nor deleted again —, while its row stays for the journal of
audit and the past attributions that cite it (WF-DAT-0080, WF-ADM-0090). Every creation, change
and deletion is inscribed in the journal, in its transaction (WF-SEC-0030). The author of a write
is an account, or ``None`` for the platform (WF-DAT-0070); the moment is an argument.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    ColumnElement,
    Select,
    Text,
    delete,
    func,
    insert,
    literal,
    select,
    update,
)
from sqlalchemy.orm import InstrumentedAttribute, Session

from waterfall.core.access_roles.administrators import guard_last_administrator
from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.core.users.interface import Author, read_author
from waterfall.platform.audit import AuditActor, AuditObject, AuditValue, Inscription, record
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
    UnprocessableError,
)
from waterfall.platform.identifiers import new_id

NOT_FOUND = "NOT_FOUND"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
ACCESS_ROLE_IN_USE = "ACCESS_ROLE_IN_USE"
VALIDATION_FAILED = "VALIDATION_FAILED"

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


@dataclass(frozen=True, slots=True)
class RoleWrite:
    """What a role is written with: its label and the codes of its permissions."""

    label: str
    permissions: Sequence[str]
    is_predefined: bool = False


@dataclass(frozen=True, slots=True)
class Act:
    """Who acts — an account, or ``None`` for the platform — and when."""

    actor: AuditActor | None
    at: datetime

    @property
    def author(self) -> UUID | None:
        """The account that writes the row, ``None`` for the platform."""
        return None if self.actor is None else self.actor.user_id


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


def _grant(session: Session, role_id: UUID, codes: Sequence[str]) -> None:
    """Make the permissions of the role those of ``codes``, all of the catalogue (422 otherwise)."""
    known = dict(
        session.execute(select(Permission.code, Permission.id).where(Permission.code.in_(codes)))
        .tuples()
        .all()
    )
    unknown = tuple(
        FieldError(f"/permissions/{index}", VALIDATION_FAILED)
        for index, code in enumerate(codes)
        if code not in known
    )
    if unknown:
        raise UnprocessableError(VALIDATION_FAILED, fields=unknown)
    session.execute(
        delete(AccessRolePermission).where(AccessRolePermission.access_role_id == role_id)
    )
    if known:
        session.execute(
            insert(AccessRolePermission),
            [{"access_role_id": role_id, "permission_id": known[code]} for code in known],
        )


def _inscribe(
    session: Session,
    action: Literal["access_role_create", "access_role_update", "access_role_delete"],
    role: tuple[UUID, str],
    act: Act,
    params: dict[str, AuditValue],
) -> None:
    """Inscribe an action on a role, named by its identifier and its label at that moment."""
    audited = AuditObject("access_role", *role)
    record(session, Inscription(action, act.actor, audited, act.at, params=params))


def create_role(session: Session, new: RoleWrite, act: Act) -> RoleView:
    """Create a role with its permissions, inscribe it, and read it back."""
    role_id = new_id()
    session.execute(
        insert(AccessRole).values(
            id=role_id,
            label=new.label,
            is_predefined=new.is_predefined,
            created_at=act.at,
            created_by=act.author,
            updated_at=act.at,
            updated_by=act.author,
        )
    )
    _grant(session, role_id, new.permissions)
    created = read_role(session, role_id)
    params: dict[str, AuditValue] = {"permissions": list(created.permissions)}
    _inscribe(session, "access_role_create", (role_id, new.label), act, params)
    return created


def _lock_role(session: Session, role_id: UUID) -> AccessRole:
    """Lock a role that is not deleted, then read it under the lock; or refuse (404)."""
    role = session.scalars(
        select(AccessRole)
        .where(AccessRole.id == role_id, AccessRole.deleted_at.is_(None))
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if role is None:
        raise NotFoundError(NOT_FOUND)
    return role


def update_role(
    session: Session, role_id: UUID, change: RoleWrite, lock_version: int, act: Act
) -> RoleView:
    """Rename a role and set its permissions, if its version is the one read (412 otherwise).

    The change applies at once to every holder, whose permissions are read at each request
    (WF-ADM-0090); one that would leave no administrator is refused (WF-ADM-0120).
    """
    with guard_last_administrator(session):
        role = _lock_role(session, role_id)
        before, previous_label = read_role(session, role_id).permissions, role.label
        changed = session.execute(
            update(AccessRole)
            .where(AccessRole.id == role_id, AccessRole.lock_version == lock_version)
            .values(
                label=change.label,
                lock_version=AccessRole.lock_version + 1,
                updated_at=act.at,
                updated_by=act.author,
            )
            .returning(AccessRole.id)
        ).first()
        if changed is None:
            raise PreconditionFailedError(
                STALE_LOCK_VERSION, {"expected_lock_version": role.lock_version}
            )
        _grant(session, role_id, change.permissions)
    after = read_role(session, role_id)
    params: dict[str, AuditValue] = {
        "permissions_granted": [code for code in after.permissions if code not in before],
        "permissions_withdrawn": [code for code in before if code not in after.permissions],
    }
    if previous_label != change.label:
        params["previous_label"] = previous_label
    _inscribe(session, "access_role_update", (role_id, change.label), act, params)
    return after


def delete_role(session: Session, role_id: UUID, act: Act) -> None:
    """Mark a role deleted, or refuse it while an account holds it (409).

    A role no account holds takes no permission from anyone: the guard of the last administrator
    has nothing to refuse, but its lock keeps an attribution of the role from passing between the
    reading of its holders and its deletion.
    """
    with guard_last_administrator(session):
        role = _lock_role(session, role_id)
        if _holder_count(session, role_id):
            raise ConflictError(ACCESS_ROLE_IN_USE)
        session.execute(
            update(AccessRole)
            .where(AccessRole.id == role_id)
            .values(
                deleted_at=act.at,
                lock_version=AccessRole.lock_version + 1,
                updated_at=act.at,
                updated_by=act.author,
            )
        )
    _inscribe(session, "access_role_delete", (role_id, role.label), act, {})


def _holder_count(session: Session, role_id: UUID) -> int:
    return session.scalars(
        select(func.count()).where(UserAccessRole.access_role_id == role_id)
    ).one()
