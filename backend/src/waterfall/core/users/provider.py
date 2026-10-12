# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The accounts of the identity provider, as Waterfall follows them (WF-ADM-0070, WF-ADM-0180).

A person the provider holds and Waterfall does not yet gets an account without any role, the
platform for its author, at her first request or at the reading of the accounts. A person of the
directory whose address an account holds already is attached to that account — the directory
recognises a person by her address (motif of WF-ADM-0050) —, and the attachment is inscribed; one
relayed by an external provider is not: a provider lax about addresses would open the account of
another (#707). The reading follows besides the name, the first name and the address of the
accounts the provider holds, and deactivates those it no longer holds. A local account is
Waterfall's, which the reading never changes: the identity the provider holds of it otherwise is the
provider's to take back (WF-ADM-0050, #919). An anonymised one stays so: the reading finds it by the
subject the anonymisation keeps, and neither renames it nor creates another (WF-ADM-0070). Each
write is inscribed in the journal of audit, by the platform (WF-DAT-0070). The report names an
account of Waterfall by its identifier alone, read as it is shown when consulted (#920).
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from sqlalchemy import desc, insert, select
from sqlalchemy.orm import Session

from waterfall.core.users.accounts import (
    NewAccount,
    Stamp,
    add_account_if_absent,
    address_holder,
    change_columns,
    find_account_of_subject,
    lock_account,
    unique_address,
)
from waterfall.core.users.identity import IDENTITY_FIELDS, LOCAL, inscribe
from waterfall.core.users.tables import IdentitySyncReport, UserAccount
from waterfall.platform.audit import Act, AuditValue
from waterfall.platform.errors import ConflictError
from waterfall.platform.keycloak_admin import LocalIdentity, ProviderAccount

NAME_MAX_LENGTH = 100
DIRECTORY = "directory"
DEACTIVATED = "deactivated"

# What the reading did of a person of the provider; ``restored``, a local account whose identity
# the provider holds otherwise, for it to take back Waterfall's (#919).
type Followed = Literal["created", "updated", "unchanged", "restored"]


class NotAdmitted(StrEnum):
    """Why a person the provider holds has no account in Waterfall."""

    # The realm holds no account for the subject of the token, or no longer.
    UNKNOWN_TO_PROVIDER = "unknown_to_provider"
    # A local account of the provider, which only Waterfall creates (WF-ADM-0070).
    LOCAL_ACCOUNT = "local_account"
    NO_ADDRESS = "no_address"
    # A name or a first name empty, or longer than a column holds.
    NAME_NOT_STORABLE = "name_not_storable"
    # The address is held by another account, and the person is not of the directory.
    ADDRESS_TAKEN = "address_taken"


def origin_of(provider: ProviderAccount) -> str | None:
    """Say where an account of the provider comes from, if Waterfall admits it on its own.

    A person of the directory and a person relayed by an external provider are admitted
    (WF-ADM-0180, WF-ADM-0070); a local account of the provider is not: a local account is created
    from Waterfall, which creates it in the provider (WF-ADM-0070).
    """
    if provider.is_federated:
        return DIRECTORY
    if provider.is_relayed:
        return "identity_provider"
    return None


def _refusal(provider: ProviderAccount) -> NotAdmitted | None:
    if not provider.email:
        return NotAdmitted.NO_ADDRESS
    names = (provider.last_name, provider.first_name)
    if not all(1 <= len(name) <= NAME_MAX_LENGTH for name in names):
        return NotAdmitted.NAME_NOT_STORABLE
    return None


def _identity(provider: ProviderAccount) -> dict[str, str]:
    return {
        "last_name": provider.last_name,
        "first_name": provider.first_name,
        "email": provider.email,
    }


def admit(
    session: Session, provider: ProviderAccount, at: datetime
) -> tuple[UserAccount, Followed] | NotAdmitted:
    """Give the account of a person the provider holds: created, attached, or found as it was.

    Created without any role, or attached by its address for a person of the directory, the
    platform its author, and inscribed under the correlation of the request or of the task (#703).
    """
    origin = origin_of(provider)
    if origin is None:
        return NotAdmitted.LOCAL_ACCOUNT
    refusal = _refusal(provider)
    if refusal is not None:
        return refusal
    new = NewAccount(
        provider.last_name, provider.first_name, provider.email, provider.subject, origin
    )
    account, inserted = add_account_if_absent(session, new, Stamp(None, at))
    if account is None:
        return _attach(session, provider, at) if origin == DIRECTORY else NotAdmitted.ADDRESS_TAKEN
    # A concurrent first request of the same person created it: that one inscribed it.
    if inserted:
        inscribe(session, "user_create", account, Act(None, at), {"origin": origin})
    return account, "created" if inserted else "unchanged"


def _attach(
    session: Session, provider: ProviderAccount, at: datetime
) -> tuple[UserAccount, Followed] | NotAdmitted:
    """Attach a person of the directory to the account that holds her address (#707).

    The account takes her subject, her names and her address, and comes from the directory from
    now on; it keeps its roles and its state. A concurrent attachment of hers is found as it is.
    """
    holder = address_holder(session, provider.email)
    if holder is None:
        return NotAdmitted.ADDRESS_TAKEN
    account = lock_account(session, holder)
    if account.idp_subject == provider.subject:
        return account, "unchanged"
    identity = _identity(provider)
    fields = [name for name in IDENTITY_FIELDS if identity[name] != getattr(account, name)]
    values = {**identity, "idp_subject": provider.subject, "origin": DIRECTORY}
    account = change_columns(session, holder, values, account.lock_version, Stamp(None, at))
    params: dict[str, AuditValue] = {"fields": fields, "attached": True}
    inscribe(session, "user_update", account, Act(None, at), params)
    return account, "updated"


@dataclass(frozen=True, slots=True)
class NotFollowed:
    """Why the reading left a person as it was, and her account, ``None`` if she has none."""

    reason: NotAdmitted
    user_id: UUID | None


def follow(session: Session, provider: ProviderAccount, at: datetime) -> Followed | NotFollowed:
    """Bring Waterfall to what the provider holds of a person (WF-ADM-0070).

    Her account is created or attached if she has none; else its name, its first name and its
    address follow the provider's, refused if another account holds the address — unless it is
    local: Waterfall's identity is then the provider's to take back, if it holds another (#919).
    An account is locked only to be written, then read again under the lock: the reading holds no
    row it leaves as it was.
    """
    found = find_account_of_subject(session, provider.subject)
    if found is None:
        admitted = admit(session, provider, at)
        if isinstance(admitted, NotAdmitted):
            return NotFollowed(admitted, None)
        return admitted[1]
    if found.origin == LOCAL:
        return "restored" if _held_otherwise(found, provider) else "unchanged"
    return _follow_account(session, found, provider, at)


def _follow_account(
    session: Session, found: UserAccount, provider: ProviderAccount, at: datetime
) -> Followed | NotFollowed:
    """Bring an account of the directory or of a provider to what the provider holds of it."""
    changed = _changes(found, provider)
    if not isinstance(changed, dict):
        return _not_followed(changed, found.id)
    account = lock_account(session, found.id)
    changed = _changes(account, provider)
    if not isinstance(changed, dict):
        return _not_followed(changed, found.id)
    stamp = Stamp(None, at)
    try:
        with unique_address(session, provider.email):
            account = change_columns(session, account.id, changed, account.lock_version, stamp)
    except ConflictError:
        return NotFollowed(NotAdmitted.ADDRESS_TAKEN, found.id)
    inscribe(session, "user_update", account, Act(None, at), {"fields": list(changed)})
    return "updated"


def _not_followed(
    outcome: Literal["unchanged"] | NotAdmitted, user_id: UUID
) -> Literal["unchanged"] | NotFollowed:
    return NotFollowed(outcome, user_id) if isinstance(outcome, NotAdmitted) else outcome


def _held_otherwise(account: UserAccount, provider: ProviderAccount) -> bool:
    """Tell whether the provider holds of a local account another identity than Waterfall's.

    The address compared whatever its case, which the provider does not keep; an anonymised
    account is out of the provider, and never given its identity back (WF-ADM-0060).
    """
    if account.anonymized_at is not None:
        return False
    held = (account.last_name, account.first_name, (account.email or "").lower())
    return held != (provider.last_name, provider.first_name, provider.email.lower())


def _changes(
    account: UserAccount, provider: ProviderAccount
) -> dict[str, str] | Literal["unchanged"] | NotAdmitted:
    """Give what of the identity of an account would follow the provider's, if anything.

    Waterfall's own (#919), anonymised for good (WF-ADM-0060), or attached meanwhile to another
    subject: the reading changes none.
    """
    if (
        account.origin == LOCAL
        or account.anonymized_at is not None
        or account.idp_subject != provider.subject
    ):
        return "unchanged"
    refusal = _refusal(provider)
    if refusal is not None:
        return refusal
    identity = _identity(provider)
    changed = {
        name: identity[name] for name in IDENTITY_FIELDS if identity[name] != getattr(account, name)
    }
    return changed or "unchanged"


@dataclass(frozen=True, slots=True)
class HeldAccount:
    """An account of Waterfall the provider holds by a subject."""

    user_id: UUID
    subject: str


def known_subjects(session: Session) -> frozenset[str]:
    """Give the subjects of every account Waterfall holds, whatever its origin or state."""
    return frozenset(session.scalars(select(UserAccount.idp_subject)))


def unheld_accounts(session: Session, held: Collection[str]) -> list[HeldAccount]:
    """Give the active accounts of the directory or of a provider whose subject is not held."""
    rows = session.execute(
        select(UserAccount.id, UserAccount.idp_subject).where(
            UserAccount.origin != LOCAL, UserAccount.state == "active"
        )
    )
    kept = frozenset(held)
    return [HeldAccount(*row) for row in rows if row[1] not in kept]


def deactivate_unheld(session: Session, held: HeldAccount, at: datetime) -> bool:
    """Deactivate an account the provider no longer holds, by the platform; ``False`` if it is not.

    Locked, then read under the lock: one local, deactivated or attached to another subject
    meanwhile is left as it is. Whether the installation keeps an administrator is the guard's its
    caller runs it under.
    """
    account = lock_account(session, held.user_id)
    if (
        account.origin == LOCAL
        or account.state == DEACTIVATED
        or account.idp_subject != held.subject
    ):
        return False
    user_id = held.user_id
    stamp = Stamp(None, at)
    account = change_columns(session, user_id, {"state": DEACTIVATED}, account.lock_version, stamp)
    inscribe(session, "user_deactivate", account, Act(None, at), {})
    return True


def identity_to_restore(session: Session, subject: str) -> LocalIdentity | None:
    """Read the identity Waterfall holds of a local account, for the provider to take it back.

    ``None`` if no local account bears the subject, or if it is anonymised: it is out of the
    provider, which is never given its identity back (WF-ADM-0060, #919).
    """
    account = find_account_of_subject(session, subject)
    if account is None or account.origin != LOCAL or account.anonymized_at is not None:
        return None
    return LocalIdentity(account.last_name or "", account.first_name or "", account.email or "")


@dataclass(frozen=True, slots=True)
class SkippedAccount:
    """An account of Waterfall the reading left as it was: its identifier alone (#920)."""

    user_id: UUID
    code: str


@dataclass(frozen=True, slots=True)
class SkippedPerson:
    """A person of the provider the reading gave no account, as the provider holds her (#918)."""

    subject: str
    last_name: str
    first_name: str
    # ``None`` if the provider holds no address of hers.
    email: str | None
    code: str


type Skipped = SkippedAccount | SkippedPerson


@dataclass(frozen=True, slots=True)
class SyncReport:
    """What a reading of the accounts did, as its report says it (``IdentitySyncReport``)."""

    task_id: UUID
    finished_at: datetime
    created: int
    updated: int
    deactivated: int
    # The local accounts whose identity the provider is given back (#919): given back, or to be —
    # it follows the commit; one that fails is logged, and the next reading counts it again.
    restored: int
    # What the reading left as it was, and the code of why.
    skipped: list[Skipped]
    # The addresses of the local accounts the reading removes from the provider (#811): removed,
    # or to be removed — the removal follows the commit; one that fails is logged, and the next
    # reading names the address again.
    removed: list[str]


def _kept(skipped: Skipped) -> dict[str, str | None]:
    if isinstance(skipped, SkippedAccount):
        return {"kind": "account", "user_id": str(skipped.user_id), "code": skipped.code}
    return {
        "kind": "person",
        "subject": skipped.subject,
        "last_name": skipped.last_name,
        "first_name": skipped.first_name,
        "email": skipped.email,
        "code": skipped.code,
    }


def _read(kept: dict[str, str | None]) -> Skipped:
    code = str(kept["code"])
    if kept["kind"] == "account":
        return SkippedAccount(UUID(str(kept["user_id"])), code)
    return SkippedPerson(
        str(kept["subject"]), str(kept["last_name"]), str(kept["first_name"]), kept["email"], code
    )


def record_report(session: Session, report: SyncReport) -> None:
    """Keep the report of a reading of the accounts."""
    session.execute(
        insert(IdentitySyncReport).values(
            task_id=report.task_id,
            finished_at=report.finished_at,
            created=report.created,
            updated=report.updated,
            deactivated=report.deactivated,
            restored=report.restored,
            skipped=[_kept(each) for each in report.skipped],
            removed=report.removed,
        )
    )


def latest_report(session: Session) -> SyncReport | None:
    """Read the report of the latest reading of the accounts, or ``None`` if none has ended."""
    row = session.scalars(
        select(IdentitySyncReport).order_by(desc(IdentitySyncReport.finished_at)).limit(1)
    ).first()
    if row is None:
        return None
    return SyncReport(
        row.task_id,
        row.finished_at,
        row.created,
        row.updated,
        row.deactivated,
        row.restored,
        [_read(each) for each in row.skipped],
        row.removed,
    )
