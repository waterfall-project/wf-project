# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The link that sets the password of an account: which account may have one, and its inscription.

Only a local account sets a password in the identity provider: an account of the directory or of
an external provider authenticates with it, and has none to set here (WF-ADM-0140). A deactivated
account may not sign in, and is given no link (WF-ADM-0060). The link itself is made by the
provider, and never reaches the base nor the journal: the journal keeps that one was asked for,
by whom and for which account, without its token (WF-SEC-0030).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from waterfall.core.users.accounts import lock_account
from waterfall.core.users.identity import LOCAL, inscribe
from waterfall.core.users.states import ACTIVE
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.errors import ConflictError

STATE_FORBIDS_OPERATION = "STATE_FORBIDS_OPERATION"
# The conditions a link lacks, named by the 409 of ``createPasswordSetupLink`` (CommandCondition).
IS_LOCAL_ACCOUNT = "is_local_account"
IS_ACTIVE_ACCOUNT = "is_active_account"


def not_local() -> ConflictError:
    """Refuse a link to an account that authenticates with its directory or its provider (409)."""
    return ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": IS_LOCAL_ACCOUNT})


def lock_link_holder(session: Session, user_id: UUID) -> UserAccount:
    """Lock the account a link is asked for and read it under the lock; refuse it if it has none.

    Refused if unknown (404), not local, or deactivated (409) — by the first condition it lacks,
    as the contract says. The lock keeps it local and active until the transaction ends.
    """
    account = lock_account(session, user_id)
    if account.origin != LOCAL:
        raise not_local()
    if account.state != ACTIVE:
        raise ConflictError(STATE_FORBIDS_OPERATION, {"missing_condition": IS_ACTIVE_ACCOUNT})
    return account


def inscribe_link(session: Session, user_id: UUID, act: Act) -> None:
    """Inscribe that a link was made for an account, which must still be able to have one.

    The account is locked and read again: one deactivated, or changed of origin, while the
    provider made the link is refused (409), and the link not given.
    """
    inscribe(session, "password_link_create", lock_link_holder(session, user_id), act, {})
