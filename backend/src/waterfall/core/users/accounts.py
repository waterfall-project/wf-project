# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The data access of the accounts, private to the module.

It offers no deletion: an account is deactivated, never removed (WF-DAT-0080). The author of a
write is the identifier of an account, or ``None`` for the platform itself (WF-DAT-0070); the
moment is an argument, never read here.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from waterfall.core.users.tables import UserAccount
from waterfall.platform.errors import NotFoundError, PreconditionFailedError
from waterfall.platform.identifiers import new_id

NOT_FOUND = "NOT_FOUND"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"


@dataclass(frozen=True, slots=True)
class Stamp:
    """Who writes, and when: the author is an account, or ``None`` for the platform."""

    author: UUID | None
    at: datetime


@dataclass(frozen=True, slots=True)
class NewAccount:
    """What an account is born with."""

    last_name: str
    first_name: str
    email: str
    idp_subject: str
    origin: str


def add_account(session: Session, new: NewAccount, stamp: Stamp) -> UserAccount:
    """Insert an active account, with a new identifier, and return it."""
    account = UserAccount(
        id=new_id(),
        last_name=new.last_name,
        first_name=new.first_name,
        email=new.email,
        idp_subject=new.idp_subject,
        origin=new.origin,
        created_at=stamp.at,
        created_by=stamp.author,
        updated_at=stamp.at,
        updated_by=stamp.author,
    )
    session.add(account)
    session.flush()
    session.refresh(account)
    return account


def add_account_if_absent(session: Session, new: NewAccount, stamp: Stamp) -> UserAccount | None:
    """Insert an active account unless its subject or address is taken; give that of its subject.

    Two first requests of one person at once insert her once: the second waits for the first,
    then finds its row. An address another account holds inserts nothing, and the subject then
    has no account (``None``).
    """
    session.execute(
        insert(UserAccount)
        .values(
            id=new_id(),
            last_name=new.last_name,
            first_name=new.first_name,
            email=new.email,
            idp_subject=new.idp_subject,
            origin=new.origin,
            created_at=stamp.at,
            created_by=stamp.author,
            updated_at=stamp.at,
            updated_by=stamp.author,
        )
        .on_conflict_do_nothing()
    )
    return find_account_of_subject(session, new.idp_subject)


def find_account(session: Session, user_id: UUID) -> UserAccount | None:
    """Read an account, or ``None`` if there is none."""
    return session.get(UserAccount, user_id)


def find_account_of_subject(session: Session, subject: str) -> UserAccount | None:
    """Read the account the identity provider knows by ``subject``, or ``None`` if there is none."""
    return session.scalars(
        select(UserAccount)
        .where(UserAccount.idp_subject == subject)
        .execution_options(populate_existing=True)
    ).first()


def change_email(
    session: Session, user_id: UUID, email: str, lock_version: int, stamp: Stamp
) -> UserAccount:
    """Change the address of an account whose version is the one read, and return it.

    The version is tested by the write itself: a write that finds another version changes
    nothing and is refused (412), whatever happened between the reading and now.
    """
    changed = session.scalars(
        update(UserAccount)
        .where(UserAccount.id == user_id, UserAccount.lock_version == lock_version)
        .values(
            email=email,
            lock_version=UserAccount.lock_version + 1,
            updated_at=stamp.at,
            updated_by=stamp.author,
        )
        .returning(UserAccount.id)
    ).first()
    if changed is None:
        current = session.scalars(
            select(UserAccount.lock_version).where(UserAccount.id == user_id)
        ).first()
        if current is None:
            raise NotFoundError(NOT_FOUND)
        raise PreconditionFailedError(STALE_LOCK_VERSION, {"expected_lock_version": current})
    return session.get_one(UserAccount, user_id, populate_existing=True)
