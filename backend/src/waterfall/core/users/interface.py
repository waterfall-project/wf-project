# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the accounts offer to the other modules: today, the label of an account.

The operations on accounts arrive with the stories that need them (US-0360).
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from waterfall.core.users.accounts import find_account


@dataclass(frozen=True, slots=True)
class AccountLabel:
    """What another module needs to show an account: who it is, and whether it may sign in."""

    user_id: UUID
    last_name: str
    first_name: str
    email: str
    is_active: bool


def read_account_label(session: Session, user_id: UUID) -> AccountLabel | None:
    """Read the label of an account, or ``None`` if there is none."""
    account = find_account(session, user_id)
    if account is None:
        return None
    return AccountLabel(
        user_id=account.id,
        last_name=account.last_name,
        first_name=account.first_name,
        email=account.email,
        is_active=account.state == "active",
    )
