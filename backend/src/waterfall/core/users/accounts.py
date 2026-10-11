# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The data access of the accounts, private to the module.

It offers no deletion: an account is deactivated, never removed (WF-DAT-0080). The author of a
write is the identifier of an account, or ``None`` for the platform itself (WF-DAT-0070); the
moment is an argument, never read here.
"""

from collections.abc import Collection, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Text, func, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from waterfall.core.users.tables import ADDRESS_INDEX, UserAccount
from waterfall.platform.database import EVERY_LETTER, unique_violated
from waterfall.platform.errors import (
    ConflictError,
    FieldError,
    NotFoundError,
    PreconditionFailedError,
)
from waterfall.platform.identifiers import new_id

NOT_FOUND = "NOT_FOUND"
STALE_LOCK_VERSION = "STALE_LOCK_VERSION"
ALREADY_EXISTS = "ALREADY_EXISTS"


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


def add_account_if_absent(
    session: Session, new: NewAccount, stamp: Stamp
) -> tuple[UserAccount | None, bool]:
    """Insert an active account unless its subject or address is taken; give that of its subject.

    Two first requests of one person at once insert her once: the second waits for the first,
    then finds its row. An address another account holds inserts nothing, and the subject then
    has no account (``None``). The flag says whether this call inserted the account.
    """
    inserted = session.scalars(
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
        .returning(UserAccount.id)
    ).first()
    return find_account_of_subject(session, new.idp_subject), inserted is not None


def address_holder(session: Session, email: str) -> UUID | None:
    """Give the account that holds an address, whatever its case (WF-ADM-0050), if one does.

    The address is lowered as the unique index lowers it, in every letter: the index serves it.
    """
    lowered = func.lower(literal(email, Text).collate(EVERY_LETTER))
    return session.scalars(
        select(UserAccount.id).where(func.lower(UserAccount.email.collate(EVERY_LETTER)) == lowered)
    ).first()


def address_taken(holder: UUID | None) -> ConflictError:
    """Refuse an address another account holds, naming that account when Waterfall has it (409)."""
    params = {} if holder is None else {"conflicting_object_id": str(holder)}
    return ConflictError(ALREADY_EXISTS, fields=(FieldError("/email", ALREADY_EXISTS, params),))


@contextmanager
def unique_address(session: Session, email: str) -> Generator[None]:
    """Run a write that gives an account ``email``, refused if another account holds it (409).

    The unique index decides, whatever wrote first: a write that breaks it is undone alone, in a
    savepoint, and refused with the account that holds the address — by then committed, since the
    index made the write wait for it.
    """
    try:
        with session.begin_nested():
            yield
    except IntegrityError as error:
        if unique_violated(error) != ADDRESS_INDEX:
            raise
        raise address_taken(address_holder(session, email)) from None


def lock_account(session: Session, user_id: UUID) -> UserAccount:
    """Lock an account, then read it under the lock; or refuse (404)."""
    account = session.scalars(
        select(UserAccount)
        .where(UserAccount.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if account is None:
        raise NotFoundError(NOT_FOUND)
    return account


def lock_account_at(session: Session, user_id: UUID, lock_version: int) -> UserAccount:
    """Lock an account and read it under the lock, at the version read; or refuse (404, 412)."""
    account = lock_account(session, user_id)
    if account.lock_version != lock_version:
        raise PreconditionFailedError(
            STALE_LOCK_VERSION, {"expected_lock_version": account.lock_version}
        )
    return account


def find_account(session: Session, user_id: UUID) -> UserAccount | None:
    """Read an account, or ``None`` if there is none."""
    return session.get(UserAccount, user_id)


def find_active_accounts(session: Session, user_ids: Collection[UUID]) -> list[UUID]:
    """Give, of the accounts given, the identifiers of those that are active."""
    return list(
        session.scalars(
            select(UserAccount.id).where(
                UserAccount.id.in_(user_ids), UserAccount.state == "active"
            )
        )
    )


def find_account_of_subject(session: Session, subject: str) -> UserAccount | None:
    """Read the account the identity provider knows by ``subject``, or ``None`` if there is none."""
    return session.scalars(
        select(UserAccount)
        .where(UserAccount.idp_subject == subject)
        .execution_options(populate_existing=True)
    ).first()


def find_first_local_account_of_platform(session: Session) -> UserAccount | None:
    """Read the first local account the platform created, or ``None`` if it created none.

    The platform creates no other local account than the administrator of the bootstrap: an
    authorized user creates the others, and the provider admits none (WF-ADM-0070).
    """
    return session.scalars(
        select(UserAccount)
        .where(UserAccount.origin == "local", UserAccount.created_by.is_(None))
        .order_by(UserAccount.created_at, UserAccount.id)
        .limit(1)
    ).first()


def change_columns(
    session: Session, user_id: UUID, values: Mapping[str, str], lock_version: int, stamp: Stamp
) -> UserAccount:
    """Change columns of an account whose version is the one read, and advance its version.

    The version is tested by the write itself: a write that finds another version changes
    nothing and is refused (412), whatever happened between the reading and now. No column
    changed notes all the same a change of what the account holds, its roles.
    """
    changed = session.scalars(
        update(UserAccount)
        .where(UserAccount.id == user_id, UserAccount.lock_version == lock_version)
        .values(
            **values,
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


def note_sessions_closed(session: Session, user_id: UUID, at: datetime) -> None:
    """Note that the sessions of an account were closed at ``at``, unless later already.

    By its holder's sign-out, or by its deactivation (#835). Not a change of the account: neither
    its version nor its audit columns move, and a form opened on it stays valid. Two closings at
    once keep the later moment, whichever writes last.
    """
    # GREATEST passes over a null: the first sign-out writes its moment.
    moment = literal(at, UserAccount.sessions_closed_at.type)
    session.execute(
        update(UserAccount)
        .where(UserAccount.id == user_id)
        .values(sessions_closed_at=func.greatest(UserAccount.sessions_closed_at, moment))
    )
