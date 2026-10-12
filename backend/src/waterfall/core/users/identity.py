# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The identity of an account — its name, first name and address —, as Waterfall writes it.

A local account is Waterfall's: it is created in the identity provider, then here, and a change of
its identity is carried to the provider before it is written here (#810). That of an account of the
directory or of an external provider is the provider's: a value that differs from the one held is
refused, the field sent unchanged is not (WF-ADM-0050, WF-ADM-0070). An address is received as
written, case included, and compared without regard to it: one ``@``, a local part and a domain
not empty, no space, 254 characters at most, the special-use domains and those without a dot
admitted (contract, README; #665). An account is attached to no node of the organisation before
EP-05 creates the tree: any node is unknown.

Every creation and change is inscribed in the journal of audit, which names the account by its
label and keeps neither its names nor its address in its data: the anonymisation of the account
rewrites the label alone (WF-SEC-0030, WF-ADM-0060).
"""

from contextlib import nullcontext
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from waterfall.core.users.accounts import (
    NewAccount,
    Stamp,
    add_account,
    change_columns,
    lock_account_at,
    unique_address,
)
from waterfall.core.users.commands import anonymized
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import (
    Act,
    AuditActor,
    AuditObject,
    AuditValue,
    Inscription,
    record,
)
from waterfall.platform.errors import FieldError, UnprocessableError

VALIDATION_FAILED = "VALIDATION_FAILED"
VALUE_REQUIRED = "VALUE_REQUIRED"
FIELD_READ_ONLY = "FIELD_READ_ONLY"
UNKNOWN_ORG_NODE = "UNKNOWN_ORG_NODE"
ADDRESS_MAX_LENGTH = 254
LOCAL = "local"


def display_name(first_name: str | None, last_name: str | None) -> str | None:
    """Name an account as it is shown: its first name, then its name.

    ``None`` for an anonymised account, which has neither: the front shows the neutral label of its
    catalogue (WF-ADM-0060, WF-ARC-0110).
    """
    if first_name is None or last_name is None:
        return None
    return f"{first_name} {last_name}"


def is_address(text: str) -> bool:
    """Tell whether a text is an address the service receives (contract, README; #665)."""
    local, _, domain = text.partition("@")
    return (
        bool(local)
        and bool(domain)
        and "@" not in domain
        and len(text) <= ADDRESS_MAX_LENGTH
        and not any(character.isspace() for character in text)
    )


@dataclass(frozen=True, slots=True)
class Identity:
    """What a local account is created with: its names, its address, and its attachment."""

    last_name: str
    first_name: str
    email: str
    org_node_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class IdentityChange:
    """What a change of an account sends: a field left ``None`` is not sent, and keeps its value.

    ``org_node_id`` is the attachment sent, ``None`` when it is not sent or sent empty: both leave
    the account attached to nothing, the only attachment before EP-05.
    """

    last_name: str | None = None
    first_name: str | None = None
    email: str | None = None
    org_node_id: UUID | None = None


type IdentityField = Literal["last_name", "first_name", "email"]
IDENTITY_FIELDS: tuple[IdentityField, ...] = ("last_name", "first_name", "email")


def identity_faults(email: str | None, org_node_id: UUID | None) -> tuple[FieldError, ...]:
    """Point at an address the service does not receive, and at a node it does not have."""
    faults: list[FieldError] = []
    if email == "":
        faults.append(FieldError("/email", VALUE_REQUIRED))
    elif email is not None and not is_address(email):
        faults.append(FieldError("/email", VALIDATION_FAILED))
    if org_node_id is not None:
        faults.append(FieldError("/org_node_id", UNKNOWN_ORG_NODE))
    return tuple(faults)


def refuse(faults: tuple[FieldError, ...]) -> None:
    """Refuse an entity if one of its fields is in fault, naming each one (422)."""
    if faults:
        raise UnprocessableError(VALIDATION_FAILED, fields=faults)


def inscribed_actor(session: Session, author: UUID | None) -> AuditActor | None:
    """Name the author of an action as the journal inscribes it; ``None`` for the platform.

    Read in the transaction that inscribes the action, under a share lock on the row of the
    account (#867): an anonymisation, which locks it for update, either waits for the inscription
    to be committed, then forgets the name in it, or is waited for, and the name read is the null
    of an anonymised account. A request in flight never inscribes the name of an account the
    anonymisation has forgotten (WF-SEC-0030). Taken after every other lock the transaction may
    wait for, just before the inscription: a write on the account of its own author already holds
    its row. A transaction that inscribes twice takes the locks of its second write before its
    first inscription — the creation of an account with roles takes the lock of the last
    administrator before it is written; writing its roles, it then takes only that lock, held
    already, and the key share of their foreign keys on the roles, rows the guard protects. The
    lock of the forgetting alone comes after: an anonymisation takes it once it holds the account
    it anonymises, and names its author before.
    """
    if author is None:
        return None
    first_name, last_name = session.execute(
        select(UserAccount.first_name, UserAccount.last_name)
        .where(UserAccount.id == author)
        .with_for_update(read=True)
    ).one()
    return AuditActor(author, display_name(first_name, last_name))


def inscribe(
    session: Session,
    action: Literal[
        "user_create",
        "user_update",
        "user_deactivate",
        "user_reactivate",
        "password_link_create",
    ],
    account: UserAccount,
    act: Act,
    params: dict[str, AuditValue],
) -> None:
    """Inscribe an action on an account, named by its identifier and its label at that moment."""
    label = display_name(account.first_name, account.last_name)
    audited = AuditObject("user", account.id, label)
    actor = inscribed_actor(session, act.author)
    record(session, Inscription(action, actor, audited, act.at, params=params))


def create_local(session: Session, identity: Identity, subject: str, act: Act) -> UserAccount:
    """Create the local account the identity provider holds under ``subject``, and inscribe it.

    Refused if a field is in fault (422), or if another account holds the address (409).
    """
    refuse(identity_faults(identity.email, identity.org_node_id))
    new = NewAccount(identity.last_name, identity.first_name, identity.email, subject, LOCAL)
    with unique_address(session, identity.email):
        account = add_account(session, new, Stamp(act.author, act.at))
    inscribe(session, "user_create", account, act, {"origin": LOCAL})
    return account


def planned_change(
    session: Session, user_id: UUID, sent: IdentityChange, lock_version: int
) -> tuple[UserAccount, dict[str, str]]:
    """Lock an account and give what a change would write of its identity, or refuse it.

    The account is locked, then read under the lock: refused if unknown (404), if its version is
    not the one read (412), if the account is anonymised and a name or the address is sent — the
    anonymisation is irreversible (409, WF-ADM-0060) —, or if a field is in fault — the identity of
    an account the provider holds changed included (422).
    """
    account = lock_account_at(session, user_id, lock_version)
    changed = {
        name: value
        for name in IDENTITY_FIELDS
        if (value := getattr(sent, name)) is not None and value != getattr(account, name)
    }
    if changed and account.anonymized_at is not None:
        raise anonymized()
    # An address sent unchanged is the one held, whatever form the provider gave it.
    # The address of an account the provider holds is refused as read-only, not as malformed.
    email = changed.get("email") if account.origin == LOCAL else None
    faults = list(identity_faults(email, sent.org_node_id))
    if account.origin != LOCAL:
        faults.extend(FieldError(f"/{name}", FIELD_READ_ONLY) for name in changed)
    refuse(tuple(faults))
    return account, changed


def change(
    session: Session, user_id: UUID, sent: IdentityChange, lock_version: int, act: Act
) -> UserAccount:
    """Change the identity of an account whose version is the one read, and inscribe it.

    Refused as ``planned_change`` refuses, or if another account holds the new address (409). A
    change that changes nothing writes nothing.
    """
    account, changed = planned_change(session, user_id, sent, lock_version)
    if not changed:
        return account
    # Only a new address may be held by another account.
    guard = unique_address(session, changed["email"]) if "email" in changed else nullcontext()
    with guard:
        account = change_columns(session, user_id, changed, lock_version, Stamp(act.author, act.at))
    inscribe(session, "user_update", account, act, {"fields": list(changed)})
    return account
