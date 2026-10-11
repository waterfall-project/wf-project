# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The state of an account: active, or deactivated; and a deactivated account anonymised.

An account is deactivated, never deleted: its acts stay attributed to it, and it keeps its roles,
which it holds again once reactivated (WF-ADM-0060). Whether a deactivation leaves the
installation an administrator is the guard's to decide, in the module of the roles, which its
caller runs it under (WF-ADM-0120).

A deactivated account is anonymised at the request of its holder, for good: its names, its address
and its avatar are removed, the journal of audit forgets its name, and it is never reactivated
(WF-ADM-0060, WF-SEC-0030). Its row stays, its identifier, its roles and the subject the provider
knows it by with it: its acts stay attributed to it.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from waterfall.core.users.accounts import Stamp, change_columns, lock_account_at
from waterfall.core.users.commands import STATE_FORBIDS_OPERATION, anonymized
from waterfall.core.users.identity import inscribe
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act, forget_account
from waterfall.platform.errors import ConflictError

ACTIVE = "active"
DEACTIVATED = "deactivated"
# What an anonymised account no longer holds: nothing replaces it (#832).
FORGOTTEN = ("last_name", "first_name", "email", "avatar", "avatar_media_type")


def set_state(
    session: Session, user_id: UUID, *, is_active: bool, lock_version: int, act: Act
) -> UserAccount:
    """Activate or deactivate an account whose version is the one read, and inscribe it.

    The account is locked, then read under the lock: refused if unknown (404), if its version is
    not the one read (412), or if it is anonymised and asked to be active (409). An account already
    in the state asked for is not written.
    """
    account = lock_account_at(session, user_id, lock_version)
    state = ACTIVE if is_active else DEACTIVATED
    if account.state == state:
        return account
    if account.anonymized_at is not None:
        raise anonymized()
    stamp = Stamp(act.author, act.at)
    account = change_columns(session, user_id, {"state": state}, lock_version, stamp)
    inscribe(session, "user_reactivate" if is_active else "user_deactivate", account, act, {})
    return account


def anonymize(session: Session, user_id: UUID, lock_version: int, act: Act) -> UserAccount:
    """Anonymise a deactivated account whose version is the one read, and inscribe it.

    The account is locked, then read under the lock: refused if unknown (404), if its version is
    not the one read (412), or if it is active (409). Its names, its address and its avatar become
    null, and the journal forgets its name, in the same transaction; the anonymisation is then
    inscribed, naming the account by no label. An account anonymised already is not written.
    """
    account = lock_account_at(session, user_id, lock_version)
    if account.anonymized_at is not None:
        return account
    if account.state != DEACTIVATED:
        raise ConflictError(STATE_FORBIDS_OPERATION)
    values: dict[str, object] = {**dict.fromkeys(FORGOTTEN), "anonymized_at": act.at}
    account = change_columns(session, user_id, values, lock_version, Stamp(act.author, act.at))
    forget_account(session, user_id)
    inscribe(session, "user_anonymize", account, act, {})
    return account
