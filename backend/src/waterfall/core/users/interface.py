# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the accounts offer to the other modules and to the API.

The label of an account; the author of a row, named as it is shown; which accounts are active;
the account the identity provider knows by a subject, as the account itself reads it; the account
of a person the provider knows and Waterfall not yet, created without any role (WF-ADM-0180); an
account read, and the table of the accounts, filtered, sorted and read by pages, with the commands
each one carries and the condition the deactivation of the last administrator lacks (WF-ADM-0050,
WF-IHM-0090); a local account created, and the identity of an account changed (``identity``); an
account deactivated or reactivated, and an account locked at the version read for a write of the
roles it holds, which notes the change (``states``); a deactivated account anonymised, for good
(``states``, WF-ADM-0060); the moment its holder closed its sessions, which refuses the tokens
issued before (#668); and what its holder sets alone, its preferences and its avatar
(``personal``, WF-ADM-0040, WF-ADM-0080). An anonymised account has no name nor address: what
names it is ``None``, which the front shows as the neutral label of its catalogue.
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from waterfall.core.users.accounts import (
    NOT_FOUND,
    NewAccount,
    Stamp,
    add_account_if_absent,
    address_holder,
    address_taken,
    change_columns,
    find_account,
    find_account_of_subject,
    find_active_accounts,
    lock_account_at,
    note_sessions_closed,
)
from waterfall.core.users.commands import (
    LAST_ADMINISTRATOR_CONDITION,
    AccountState,
    CommandAvailability,
    account_commands,
)
from waterfall.core.users.identity import (
    Identity,
    IdentityChange,
    change,
    create_local,
    display_name,
    identity_faults,
    inscribe,
    is_address,
    refuse,
)
from waterfall.core.users.listing import (
    AccountColumn,
    AccountExpression,
    AccountFilters,
    AccountSort,
    Page,
    find_accounts,
)
from waterfall.core.users.password_link import inscribe_link, lock_link_holder, not_local
from waterfall.core.users.personal import (
    Avatar,
    change_preferences,
    image_type,
    put_avatar,
    read_avatar,
    withdraw_avatar,
)
from waterfall.core.users.states import anonymize, check_anonymization, set_state
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act
from waterfall.platform.errors import ConflictError, NotFoundError
from waterfall.platform.keycloak_admin import ProviderAccount

__all__ = [
    "LAST_ADMINISTRATOR_CONDITION",
    "Account",
    "AccountColumn",
    "AccountExpression",
    "AccountFilters",
    "AccountLabel",
    "AccountPage",
    "AccountSort",
    "AccountState",
    "Author",
    "Avatar",
    "CommandAvailability",
    "Identity",
    "IdentityChange",
    "NotAdmitted",
    "Page",
    "account_commands",
    "active_accounts",
    "add_account_of_provider",
    "address_holder",
    "address_taken",
    "anonymize_account",
    "change_account",
    "change_preferences",
    "check_account_anonymization",
    "create_local_account",
    "display_name",
    "identity_faults",
    "image_type",
    "inscribe_password_link",
    "is_address",
    "list_accounts",
    "lock_account_for_change",
    "note_account_change",
    "note_sessions_closed",
    "origin_of",
    "password_link_holder",
    "password_link_not_local",
    "put_avatar",
    "read_account",
    "read_account_label",
    "read_account_of_subject",
    "read_author",
    "read_authors",
    "read_avatar",
    "refuse",
    "set_account_activation",
    "withdraw_avatar",
]

NAME_MAX_LENGTH = 100


class NotAdmitted(StrEnum):
    """Why a person the provider knows is not given an account at her first request."""

    # The realm holds no account for the subject of the token, or no longer.
    UNKNOWN_TO_PROVIDER = "unknown_to_provider"
    # A local account of the provider, which only Waterfall creates (WF-ADM-0070).
    LOCAL_ACCOUNT = "local_account"
    NO_ADDRESS = "no_address"
    # A name or a first name empty, or longer than a column holds.
    NAME_NOT_STORABLE = "name_not_storable"
    # The address is held by another account (WF-ADM-0050).
    ADDRESS_TAKEN = "address_taken"


@dataclass(frozen=True, slots=True)
class AccountLabel:
    """What another module needs to show an account: who it is, and whether it may sign in.

    The names and the address of an anonymised account are ``None``.
    """

    user_id: UUID
    last_name: str | None
    first_name: str | None
    email: str | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class Author:
    """The account that wrote a row, named as it is shown; the platform is no author (``None``).

    An anonymised account is named by no name (``None``).
    """

    user_id: UUID
    display_name: str | None


@dataclass(frozen=True, slots=True)
class Account:
    """An account as it is read, by the person who holds it (``getMe``) or in the table."""

    user_id: UUID
    subject: str
    last_name: str | None
    first_name: str | None
    email: str | None
    anonymized_at: datetime | None
    is_active: bool
    origin: str
    display_preferences: Mapping[str, Any]
    has_avatar: bool
    created_at: datetime
    created_by: Author | None
    updated_at: datetime
    updated_by: Author | None
    lock_version: int
    # When its sessions were last closed, ``None`` until they first are (#668, #835).
    sessions_closed_at: datetime | None


def read_account_label(session: Session, user_id: UUID) -> AccountLabel | None:
    """Read the label of an account, or ``None`` if there is none."""
    account = find_account(session, user_id)
    return None if account is None else _label(account)


def _label(account: UserAccount) -> AccountLabel:
    return AccountLabel(
        user_id=account.id,
        last_name=account.last_name,
        first_name=account.first_name,
        email=account.email,
        is_active=account.state == "active",
    )


def read_author(session: Session, user_id: UUID | None) -> Author | None:
    """Name the author of a row, an account; ``None`` for the platform."""
    if user_id is None:
        return None
    author = session.get_one(UserAccount, user_id)
    return Author(user_id, display_name(author.first_name, author.last_name))


def read_authors(session: Session, user_ids: Collection[UUID]) -> dict[UUID, Author]:
    """Name the accounts given as they are shown today, deactivated ones included.

    An identifier no account bears is left out.
    """
    if not user_ids:
        return {}
    found = session.execute(
        select(UserAccount.id, UserAccount.first_name, UserAccount.last_name).where(
            UserAccount.id.in_(user_ids)
        )
    )
    return {
        user_id: Author(user_id, display_name(first_name, last_name))
        for user_id, first_name, last_name in found
    }


def active_accounts(session: Session, user_ids: Collection[UUID]) -> frozenset[UUID]:
    """Keep, of the accounts given, those that are active."""
    return frozenset(find_active_accounts(session, user_ids)) if user_ids else frozenset()


def read_account_of_subject(session: Session, subject: str) -> Account | None:
    """Read the account the identity provider knows by ``subject``, or ``None`` if there is none."""
    account = find_account_of_subject(session, subject)
    return None if account is None else _account(session, account)


def origin_of(provider: ProviderAccount) -> str | None:
    """Say where an account of the provider comes from, if Waterfall admits it on its own.

    A person of the directory before the first reading of the accounts, and a person relayed by
    an external provider, are admitted at their first request (WF-ADM-0180, WF-ADM-0070). A
    local account of the provider is not: a local account is created from Waterfall, which
    creates it in the provider (WF-ADM-0070).
    """
    if provider.is_federated:
        return "directory"
    if provider.is_relayed:
        return "identity_provider"
    return None


def _storable(name: str) -> bool:
    return 1 <= len(name) <= NAME_MAX_LENGTH


def add_account_of_provider(
    session: Session, provider: ProviderAccount, at: datetime
) -> Account | NotAdmitted:
    """Create, without any role, the account of a person the provider knows and Waterfall not yet.

    It takes the name, the first name and the address the provider transmits, the platform as
    its author (WF-ADM-0180), and inscribes the creation in the journal of audit, under the
    correlation of the request (#703). When the provider does not admit the person
    (``origin_of``), when she lacks a name or an address, or when her address is held by another
    account, it creates nothing and says why.
    """
    origin = origin_of(provider)
    if origin is None:
        return NotAdmitted.LOCAL_ACCOUNT
    if not provider.email:
        return NotAdmitted.NO_ADDRESS
    if not (_storable(provider.last_name) and _storable(provider.first_name)):
        return NotAdmitted.NAME_NOT_STORABLE
    new = NewAccount(
        last_name=provider.last_name,
        first_name=provider.first_name,
        email=provider.email,
        idp_subject=provider.subject,
        origin=origin,
    )
    account, inserted = add_account_if_absent(session, new, Stamp(None, at))
    if account is None:
        return NotAdmitted.ADDRESS_TAKEN
    # A concurrent first request of the same person created it: that one inscribed it.
    if inserted:
        inscribe(session, "user_create", account, Act(None, at), {"origin": origin})
    return _account(session, account)


def create_local_account(session: Session, identity: Identity, subject: str, act: Act) -> Account:
    """Create the local account the provider holds under ``subject``, and inscribe it.

    Refused if a field is in fault (422), or if another account holds the address (409).
    """
    return _account(session, create_local(session, identity, subject, act))


def change_account(
    session: Session, user_id: UUID, sent: IdentityChange, lock_version: int, act: Act
) -> Account:
    """Change the identity of an account whose version is the one read (``identity``)."""
    return _account(session, change(session, user_id, sent, lock_version, act))


def set_account_activation(
    session: Session, user_id: UUID, *, is_active: bool, lock_version: int, act: Act
) -> Account:
    """Activate or deactivate an account whose version is the one read (``states``).

    Refused if unknown (404) or at another version (412). A deactivation that leaves the
    installation no administrator is refused by the guard its caller runs it under (WF-ADM-0120).
    """
    return _account(
        session,
        set_state(session, user_id, is_active=is_active, lock_version=lock_version, act=act),
    )


def check_account_anonymization(session: Session, user_id: UUID, lock_version: int) -> Account:
    """Give the account to anonymise, its origin and subject, before the provider is asked.

    Refused as its anonymisation would be (``anonymize_account``): the caller removes a local
    account from the provider out of any transaction, then anonymises it (#669, WF-ADM-0060).
    """
    return _account(session, check_anonymization(session, user_id, lock_version))


def anonymize_account(session: Session, user_id: UUID, lock_version: int, act: Act) -> Account:
    """Anonymise a deactivated account whose version is the one read, for good (``states``).

    Refused if unknown (404), at another version (412), anonymised already or active (409). The
    journal of audit forgets its name in the same transaction (WF-SEC-0030).
    """
    return _account(session, anonymize(session, user_id, lock_version, act))


def lock_account_for_change(session: Session, user_id: UUID, lock_version: int) -> AccountLabel:
    """Lock an account at the version read, for a write of the roles it holds; or refuse (404, 412).

    Taken under the guard of the last administrator, after its lock: never the reverse.
    """
    return _label(lock_account_at(session, user_id, lock_version))


def note_account_change(session: Session, user_id: UUID, lock_version: int, act: Act) -> None:
    """Note on an account locked at the version read a change of its roles: its version advances.

    With the author and the moment of the change, as for any write of the account.
    """
    change_columns(session, user_id, {}, lock_version, Stamp(act.author, act.at))


@dataclass(frozen=True, slots=True)
class AccountPage:
    """A page of the table of the accounts, and the number of accounts the filters keep."""

    accounts: list[Account]
    total: int


def read_account(session: Session, user_id: UUID) -> Account:
    """Read an account, or refuse (404)."""
    account = find_account(session, user_id)
    if account is None:
        raise NotFoundError(NOT_FOUND)
    return _account(session, account)


def list_accounts(
    session: Session, filters: AccountFilters, sort: AccountSort, page: Page
) -> AccountPage:
    """Read a page of the table of the accounts, and count those the filters keep."""
    rows, total = find_accounts(session, filters, sort, page)
    return AccountPage(_accounts(session, rows), total)


def _authors(session: Session, user_ids: Iterable[UUID | None]) -> dict[UUID, Author]:
    """Name the authors of rows at once; the platform, ``None``, is no author."""
    wanted = {user_id for user_id in user_ids if user_id is not None}
    if not wanted:
        return {}
    rows = session.execute(
        select(UserAccount.id, UserAccount.first_name, UserAccount.last_name).where(
            UserAccount.id.in_(wanted)
        )
    )
    return {user_id: Author(user_id, display_name(first, last)) for user_id, first, last in rows}


def _account(session: Session, account: UserAccount) -> Account:
    return _accounts(session, [account])[0]


def _accounts(session: Session, accounts: list[UserAccount]) -> list[Account]:
    authors = _authors(
        session, [user_id for each in accounts for user_id in (each.created_by, each.updated_by)]
    )
    return [
        Account(
            user_id=account.id,
            subject=account.idp_subject,
            last_name=account.last_name,
            first_name=account.first_name,
            email=account.email,
            anonymized_at=account.anonymized_at,
            is_active=account.state == "active",
            origin=account.origin,
            display_preferences=dict(account.display_preferences),
            # The image and its type are set and removed together (``avatar_with_its_media_type``):
            # the type says whether there is one without reading up to 8 MiB.
            has_avatar=account.avatar_media_type is not None,
            created_at=account.created_at,
            created_by=None if account.created_by is None else authors[account.created_by],
            updated_at=account.updated_at,
            updated_by=None if account.updated_by is None else authors[account.updated_by],
            lock_version=account.lock_version,
            sessions_closed_at=account.sessions_closed_at,
        )
        for account in accounts
    ]


def password_link_holder(session: Session, user_id: UUID) -> Account:
    """Read the account a link to set its password is asked for, or refuse (404, 409).

    Only a local and active account has one (WF-ADM-0140, WF-ADM-0060).
    """
    return _account(session, lock_link_holder(session, user_id))


def password_link_not_local() -> ConflictError:
    """Refuse a link to an account the provider says is not local after all (409)."""
    return not_local()


def inscribe_password_link(session: Session, user_id: UUID, act: Act) -> None:
    """Inscribe that a link was made for an account, refused if it may no longer have one (409).

    Without the token of the link, which never reaches the base (WF-SEC-0030).
    """
    inscribe_link(session, user_id, act)
