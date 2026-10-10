# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The last administrator: an active account always holds the two permissions (WF-ADM-0120).

An administrator is an active account that holds, by its roles that are not deleted, both the
permission to change the accounts and that to change the roles. Every write that may take one of
them from an account — a role changed or deleted, the roles of an account set, an account
deactivated — runs under one advisory lock of transaction, always the same, and reads the
administrators under it: two such writes never decide each on what the other is changing.
"""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from waterfall.core.access_roles.tables import (
    AccessRole,
    AccessRolePermission,
    Permission,
    UserAccessRole,
)
from waterfall.core.users.interface import active_accounts
from waterfall.platform.errors import ConflictError

LAST_ADMINISTRATOR = "LAST_ADMINISTRATOR"
ADMINISTRATION = ("users.write", "access_roles.write")

# The key of the advisory lock of the rule, distinct from that of the migrations.
ADMINISTRATORS_LOCK = 1_200_120


def lock_administrators(session: Session) -> None:
    """Wait for, then hold until the end of the transaction, the lock of the rule."""
    session.execute(select(func.pg_advisory_xact_lock(ADMINISTRATORS_LOCK)))


def administrators(session: Session) -> frozenset[UUID]:
    """Give the active accounts that hold the two permissions of administration."""
    holders = session.scalars(
        select(UserAccessRole.user_account_id)
        .join(AccessRole, AccessRole.id == UserAccessRole.access_role_id)
        .join(AccessRolePermission, AccessRolePermission.access_role_id == AccessRole.id)
        .join(Permission, Permission.id == AccessRolePermission.permission_id)
        .where(AccessRole.deleted_at.is_(None), Permission.code.in_(ADMINISTRATION))
        .group_by(UserAccessRole.user_account_id)
        .having(func.count(distinct(Permission.code)) == len(ADMINISTRATION))
    ).all()
    return active_accounts(session, holders)


@contextmanager
def guard_last_administrator(
    session: Session, code: str = LAST_ADMINISTRATOR, params: Mapping[str, Any] | None = None
) -> Generator[None]:
    """Run a write under the lock of the rule, and refuse it if it leaves no administrator.

    The administrators are read under the lock before the write and after it: a write that takes
    the last one away raises ``ConflictError(code, params)``, the refusal of the write it guards,
    and the transaction, rolled back, writes nothing. An installation that had none — before its
    bootstrap — is not refused for having none after.
    """
    lock_administrators(session)
    held = administrators(session)
    yield
    session.flush()
    if held and not administrators(session):
        raise ConflictError(code, params)
