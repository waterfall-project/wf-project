# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Accounts and roles written around the service, for the tests of the roles to read or change."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import insert, select
from support import raw_account

from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database

DAY = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
# The two permissions an administrator holds, which an active account always keeps (WF-ADM-0120).
ADMINISTRATION = ("users.write", "access_roles.write")


def holder(database: Database, *, active: bool = True) -> UUID:
    """Write an account that holds no role yet, and give its identifier."""
    state = "active" if active else "deactivated"
    row = raw_account(email=f"{uuid4().hex}@example.org", state=state)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    return UUID(str(row["id"]))


@dataclass(frozen=True, slots=True)
class Row:
    """A role as a test writes it: its label, permissions, nature, holders, deletion and author."""

    label: str
    permissions: tuple[str, ...] = ()
    is_predefined: bool = False
    holders: tuple[UUID, ...] = ()
    deleted: bool = False
    author: UUID | None = None


def role(database: Database, label: str, **columns: Any) -> UUID:
    """Write a role around the service, as ``Row`` describes it; give its identifier."""
    row = Row(label, **columns)
    identifier = uuid4()
    with database.transaction() as session:
        session.execute(
            insert(AccessRole).values(
                id=identifier,
                label=row.label,
                is_predefined=row.is_predefined,
                deleted_at=DAY + timedelta(days=1) if row.deleted else None,
                created_at=DAY,
                created_by=row.author,
                updated_at=DAY,
                updated_by=row.author,
            )
        )
        granted = session.scalars(
            select(Permission.id).where(Permission.code.in_(row.permissions))
        ).all()
        for permission_id in granted:
            session.execute(
                insert(AccessRolePermission).values(
                    access_role_id=identifier, permission_id=permission_id
                )
            )
        for user_id in row.holders:
            session.execute(
                insert(UserAccessRole).values(user_account_id=user_id, access_role_id=identifier)
            )
    return identifier
