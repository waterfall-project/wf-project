# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The state of an account: active, or deactivated.

An account is deactivated, never deleted: its acts stay attributed to it, and it keeps its roles,
which it holds again once reactivated (WF-ADM-0060). Whether a deactivation leaves the
installation an administrator is the guard's to decide, in the module of the roles, which its
caller runs it under (WF-ADM-0120).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from waterfall.core.users.accounts import Stamp, change_columns, lock_account_at
from waterfall.core.users.identity import inscribe
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act

ACTIVE = "active"
DEACTIVATED = "deactivated"


def set_state(
    session: Session, user_id: UUID, *, is_active: bool, lock_version: int, act: Act
) -> UserAccount:
    """Activate or deactivate an account whose version is the one read, and inscribe it.

    The account is locked, then read under the lock: refused if unknown (404) or if its version is
    not the one read (412). An account already in the state asked for is not written.
    """
    account = lock_account_at(session, user_id, lock_version)
    state = ACTIVE if is_active else DEACTIVATED
    if account.state == state:
        return account
    stamp = Stamp(act.author, act.at)
    account = change_columns(session, user_id, {"state": state}, lock_version, stamp)
    inscribe(session, "user_reactivate" if is_active else "user_deactivate", account, act, {})
    return account
