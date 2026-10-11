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
from contextlib import AbstractContextManager, contextmanager
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
from waterfall.core.users.interface import LAST_ADMINISTRATOR as LAST_ADMINISTRATOR_LACKING
from waterfall.core.users.interface import active_accounts
from waterfall.platform.errors import ConflictError

LAST_ADMINISTRATOR = "LAST_ADMINISTRATOR"
STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
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


def sole_administrator(session: Session) -> UUID | None:
    """Give the account that alone holds the administration, if a single one does.

    Its deactivation is unavailable, which its commands say (WF-ADM-0120, WF-IHM-0090): a reading,
    not a guard — the write that would take the administration away runs under the guard.
    """
    held = administrators(session)
    return next(iter(held)) if len(held) == 1 else None


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


def guard_deactivation(session: Session) -> AbstractContextManager[None]:
    """Run the change of the state of an account under the guard of the last administrator.

    The deactivation that takes the last one away is refused as its command says in advance
    (WF-ADM-0120, WF-IHM-0090): ``STATE_FORBIDS_OPERATION``, with the condition the command lacks,
    which the accounts name. A reactivation takes the administration from nobody.
    """
    return guard_last_administrator(
        session, STATE_FORBIDS_OPERATION, {"missing_condition": LAST_ADMINISTRATOR_LACKING}
    )
