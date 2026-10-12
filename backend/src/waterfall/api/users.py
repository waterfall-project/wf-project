# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The accounts: the operations of the family ``users`` that read, create and change them.

Each asks for the permission to consult the accounts (WF-ADM-0110): without it, an account does
not exist for the caller (404); a write asks besides for the permission to change them, the
creation for that one alone. An account is read with the roles it holds, named by the server in
the order it holds them, and with the commands its reader may exercise, each available or not
(WF-IHM-0090).

A local account is created in the identity provider, then in Waterfall, and its holder invited by
the extension of Keycloak (WF-ADM-0070, WF-ADM-0140), which also makes the link that sets its
password for an authorized user to hand over. No call to the provider is made inside a
transaction (#669): what Waterfall would refuse is refused before the provider is asked, the
account is written once the provider has created it, and withdrawn from the provider if Waterfall
refuses it after all, a role deleted or an address taken meanwhile. An account deactivated, or
withdrawn all its roles, has its sessions closed by the provider once the write is committed
(WF-SEC-0020). A local account to anonymise is removed from it before the anonymisation is
written, once checked: while the provider does not answer, nothing is written (WF-ADM-0060).
"""

from collections.abc import Mapping, Sequence
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from waterfall.api.actors import actor_ref, audit_actor
from waterfall.api.authentication import Caller, Services, ServicesOf, Transaction
from waterfall.api.contract.base import Text
from waterfall.api.contract.models import (
    PaginationMeta,
    PasswordSetupLink,
    SortOrder,
    User,
    UserActivationWrite,
    UserAnonymizationWrite,
    UserCreate,
    UserCreated,
    UserOrigin,
    UserRolesWrite,
    UserUpdate,
)
from waterfall.api.evaluation import Acting, Requires
from waterfall.api.queries import Search, listed
from waterfall.core.access_roles.interface import (
    Actor,
    HeldRole,
    give_first_roles,
    guard_deactivation,
    holding_one_of,
    labels_held,
    roles_held_by,
    set_access_roles,
    sole_administrator,
    unknown_roles,
)
from waterfall.core.users.interface import (
    Account,
    AccountColumn,
    AccountFilters,
    AccountSort,
    AccountState,
    Identity,
    IdentityChange,
    Page,
    account_commands,
    address_holder,
    address_taken,
    anonymize_account,
    change_account,
    check_account_anonymization,
    check_account_change,
    create_local_account,
    display_name,
    identity_faults,
    inscribe_password_link,
    list_accounts,
    note_sessions_closed,
    password_link_holder,
    password_link_not_local,
    read_account,
    refuse,
    set_account_activation,
)
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import FieldError, UnavailableError, UnprocessableError
from waterfall.platform.keycloak import IdentityProviderError
from waterfall.platform.keycloak_admin import KeycloakAdmin, LocalIdentity
from waterfall.platform.logs import get_logger

router = APIRouter(tags=["users"])

logger = get_logger(__name__)

CONSULTATION = "users.read"
CHANGE = "users.write"
# Giving or withdrawing a role is managing the roles (FBS-1.2, WF-ADM-0090): who changes the
# accounts alone does not give himself the administration.
ROLES_CHANGE = "access_roles.write"
LOCAL = "local"
VALIDATION_FAILED = "VALIDATION_FAILED"
READ = [Depends(Requires(CONSULTATION))]
CREATE = [Depends(Requires(CHANGE))]
WRITE = [Depends(Requires(CONSULTATION, CHANGE))]
ATTRIBUTE = [Depends(Requires(CONSULTATION, CHANGE, ROLES_CHANGE))]
# The size of a page the contract gives when none is asked for, and the largest it allows.
DEFAULT_LIMIT = 50
GREATEST_LIMIT = 500

type UserColumn = Literal[
    "last_name", "first_name", "email", "origin", "access_roles", "org_node", "is_active"
]


def account_fields(account: Account, roles: Sequence[HeldRole]) -> dict[str, object]:
    """Describe an account as the contract does, without what only one reading adds to it.

    The roles are named by the server, in the order the account holds them (WF-ARC-0020). The
    attachment to the organisation arrives with EP-05.
    """
    return {
        "user_id": account.user_id,
        "last_name": account.last_name,
        "first_name": account.first_name,
        "email": account.email,
        "anonymized_at": account.anonymized_at,
        "is_active": account.is_active,
        "origin": account.origin,
        "org_node_id": None,
        "org_node_label": None,
        "access_role_ids": [held.access_role_id for held in roles],
        "access_role_labels": [held.label for held in roles],
        "has_avatar": account.has_avatar,
        "audit": {
            "created_at": account.created_at,
            "created_by": actor_ref(account.created_by),
            "updated_at": account.updated_at,
            "updated_by": actor_ref(account.updated_by),
        },
        "lock_version": account.lock_version,
    }


def users(session: Session, actor: Actor, accounts: Sequence[Account]) -> list[User]:
    """Describe accounts for the table, each with its roles and the commands its reader may use."""
    held = roles_held_by(session, [account.user_id for account in accounts])
    may_change = CHANGE in actor.permissions
    may_attribute = may_change and ROLES_CHANGE in actor.permissions
    last = sole_administrator(session) if may_change else None
    described: list[User] = []
    for account in accounts:
        state = AccountState(
            is_active=account.is_active,
            is_anonymized=account.anonymized_at is not None,
            is_last_administrator=account.user_id == last,
        )
        commands = account_commands(state, may_change=may_change, may_attribute=may_attribute)
        fields = account_fields(account, held[account.user_id])
        fields["available_commands"] = [
            {
                "command": command.command,
                "is_available": command.is_available,
                "missing_conditions": list(command.missing_conditions),
            }
            for command in commands
        ]
        described.append(User.model_validate(fields))
    return described


def account_states(
    *, include_inactive: bool = False, is_active: bool | None = None
) -> frozenset[str]:
    """Read the states the table keeps.

    ``is_active`` keeps one state and prevails over ``include_inactive``, which only adds the
    deactivated accounts to the active ones (WF-IHM-0130, WF-ADM-0060).
    """
    if is_active is None:
        return frozenset({"active", "deactivated"} if include_inactive else {"active"})
    return frozenset({"active" if is_active else "deactivated"})


def account_filters(
    states: Annotated[frozenset[str], Depends(account_states)],
    search: Search = None,
    origins: Text | None = None,
    org_node_id: UUID | None = None,
    access_role_ids: Text | None = None,
) -> AccountFilters:
    """Read the filters of the table; a list holds its values separated by commas."""
    kept_origins = listed("origins", origins, UserOrigin)
    roles = listed("access_role_ids", access_role_ids, UUID)
    return AccountFilters(
        search=search,
        origins=None if kept_origins is None else frozenset(kept_origins),
        states=states,
        org_node_id=org_node_id,
        held=None if roles is None else holding_one_of(roles),
    )


def account_sort(
    sort_by: UserColumn | None = None, sort_order: SortOrder = SortOrder.asc
) -> AccountSort:
    """Read the sort the table asks for; the roles by their labels, which their module computes."""
    descending = sort_order is SortOrder.desc
    if sort_by == "access_roles":
        return AccountSort(labels_held, descending=descending)
    column: AccountColumn | None = sort_by
    return AccountSort(column, descending=descending)


def page_of(
    limit: Annotated[int, Query(ge=1, le=GREATEST_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page:
    """Read the page asked for: fifty accounts from the first one, unless said otherwise."""
    return Page(limit, offset)


# The platform as an author has no account: its absent fields stay absent, not null.
@router.get("/users", operation_id="listUsers", dependencies=READ, response_model=None)
def get_users(
    actor: Acting,
    session: Transaction,
    filters: Annotated[AccountFilters, Depends(account_filters)],
    sort: Annotated[AccountSort, Depends(account_sort)],
    page: Annotated[Page, Depends(page_of)],
) -> dict[str, object]:
    """Give a page of the table of the accounts, filtered and sorted by the server (WF-ADM-0050)."""
    read = list_accounts(session, filters, sort, page)
    meta = PaginationMeta(limit=page.limit, offset=page.offset, total=read.total)
    return {
        "items": [
            user.model_dump(mode="json", exclude_unset=True)
            for user in users(session, actor, read.accounts)
        ],
        "meta": meta.model_dump(),
    }


@router.get(
    "/users/{user_id}",
    operation_id="getUser",
    dependencies=READ,
    response_model_exclude_unset=True,
)
def get_user(user_id: UUID, actor: Acting, session: Transaction) -> User:
    """Give an account, with its roles and its commands (WF-ADM-0050)."""
    return users(session, actor, [read_account(session, user_id)])[0]


def check_new_account(
    session: Session, identity: Identity, role_ids: Sequence[UUID] | None
) -> None:
    """Refuse an account Waterfall would refuse, before the provider creates it.

    Each field in fault, the roles included — sent null if ``None`` —, is named (422); then an
    address another account holds is refused (409). The roles and the address are read again when
    the account is written.
    """
    roles = (
        (FieldError("/access_role_ids", VALIDATION_FAILED),)
        if role_ids is None
        else unknown_roles(session, role_ids)
    )
    refuse((*identity_faults(identity.email, identity.org_node_id), *roles))
    holder = address_holder(session, identity.email)
    if holder is not None:
        raise address_taken(holder)


def write_new_account(
    session: Session,
    created: tuple[Identity, str],
    role_ids: Sequence[UUID],
    actor: Actor,
    act: Act,
) -> User:
    """Write the local account the provider holds under its subject, with its first roles.

    ``created`` is its identity and that subject. The roles are read again under the guard of the
    last administrator, and the address by the unique index: refused, nothing is written.
    """
    identity, subject = created
    account = create_local_account(session, identity, subject, act)
    label = display_name(account.first_name, account.last_name)
    give_first_roles(session, (account.user_id, label), role_ids, act)
    return users(session, actor, [account])[0]


def withdraw(admin: KeycloakAdmin, subject: str) -> None:
    """Remove from the provider the account it created and Waterfall refused after all.

    The refusal is what the caller is told; an account the provider could not remove is logged,
    and refused at its first request as a local account Waterfall did not create.
    """
    try:
        admin.remove_account(subject)
    except (UnavailableError, IdentityProviderError):
        logger.exception("account.withdrawal_failed", subject=subject)


@router.post(
    "/users",
    operation_id="createUser",
    dependencies=CREATE,
    status_code=201,
    response_model_exclude_unset=True,
)
def post_user(
    body: UserCreate, account: Caller, actor: Acting, services: ServicesOf
) -> UserCreated:
    """Create a local account in the provider and in Waterfall, and invite its holder.

    A local account is born without a password: its holder sets one by the link the extension
    mails, or that an authorized user obtains (WF-ADM-0050, WF-ADM-0070, WF-ADM-0140). The answer
    says whether the mail left: when it did not, the link is given by hand (#816).
    """
    org_node_id = None if body.org_node_id is None else body.org_node_id.root
    identity = Identity(body.last_name, body.first_name, body.email, org_node_id)
    role_ids = [role_id.root for role_id in body.access_role_ids or ()]
    sent_null = "access_role_ids" in body.model_fields_set and body.access_role_ids is None
    with services.database.transaction() as session:
        check_new_account(session, identity, None if sent_null else role_ids)
    admin = services.keycloak_admin
    subject = admin.create_account(LocalIdentity(body.last_name, body.first_name, body.email))
    if subject is None:
        # An account of the provider holds the address: one Waterfall holds too, created since it
        # was checked, is named.
        with services.database.transaction() as session:
            raise address_taken(address_holder(session, body.email))
    act = Act(audit_actor(account), utc_now())
    try:
        with services.database.transaction() as session:
            created = write_new_account(session, (identity, subject), role_ids, actor, act)
    except Exception:
        withdraw(admin, subject)
        raise
    sent = invite(admin, subject, created.user_id.root)
    return UserCreated.model_validate(
        {**created.model_dump(exclude_unset=True), "invitation_sent": sent}
    )


def invite(admin: KeycloakAdmin, subject: str, user_id: UUID) -> bool:
    """Have the extension mail the holder of an account just created the link of its password.

    The account exists whether the mail leaves or not: one that does not is said in the log with
    its reason, and the link of the account may be obtained by hand (WF-ADM-0140, WF-CMP-0030).
    Give whether it left.
    """
    try:
        reason = admin.send_invitation(subject)
    except IdentityProviderError:
        logger.exception(
            "account.invitation_not_sent", user_id=str(user_id), reason="provider_error"
        )
        return False
    if reason is not None:
        logger.warning("account.invitation_not_sent", user_id=str(user_id), reason=reason)
        return False
    return True


def identity_change(body: UserUpdate) -> IdentityChange:
    """Read the change of an account; a name, a first name or an address sent null is refused."""
    sent = body.model_fields_set
    refuse(
        tuple(
            FieldError(f"/{name}", VALIDATION_FAILED)
            for name in ("last_name", "first_name", "email")
            if name in sent and getattr(body, name) is None
        )
    )
    org_node_id = None if body.org_node_id is None else body.org_node_id.root
    return IdentityChange(body.last_name, body.first_name, body.email, org_node_id)


@router.patch(
    "/users/{user_id}",
    operation_id="updateUser",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def patch_user(
    user_id: UUID, body: UserUpdate, account: Caller, actor: Acting, services: ServicesOf
) -> User:
    """Change the names and the address of a local account, the attachment of any (WF-ADM-0050).

    For a local account Waterfall is the authority (WF-ADM-0050): its new identity is carried to
    the provider, which signs it in and mails it by its address (#810), out of any transaction
    (#669) — checked first, carried, then written; a write refused after all gives the provider
    back the identity Waterfall holds then.
    """
    sent = identity_change(body)
    lock_version = body.lock_version.root
    with services.database.transaction() as session:
        held, changed = check_account_change(session, user_id, sent, lock_version)
    carried = held.origin == "local" and bool(changed)
    if carried:
        carry_identity(services.keycloak_admin, held, changed)
    act = Act(audit_actor(account), utc_now())
    try:
        with services.database.transaction() as session:
            done = change_account(session, user_id, sent, lock_version, act)
            return users(session, actor, [done])[0]
    except Exception:
        if carried:
            restore_identity(services, user_id)
        raise


def local_identity(held: Account, changed: Mapping[str, str]) -> LocalIdentity:
    """Give the identity of a local account, with what a change sends.

    Its names and its address are held: an anonymised account changes none (409).
    """
    identity = {"last_name": held.last_name, "first_name": held.first_name, "email": held.email}
    return LocalIdentity(**{name: value or "" for name, value in {**identity, **changed}.items()})


def carry_identity(admin: KeycloakAdmin, held: Account, changed: Mapping[str, str]) -> None:
    """Give the provider the new identity of a local account; refused if it holds the address."""
    if not admin.change_identity(held.subject, local_identity(held, changed)):
        raise address_taken(None)


def restore_identity(services: Services, user_id: UUID) -> None:
    """Give the provider back the identity of a local account whose change Waterfall refused.

    The one Waterfall holds at the refusal, read again in a short transaction: the one read before
    the change may be stale — another administrator, a request sent twice (#810). The refusal is
    what the caller is told; a provider that cannot be given it back, or that holds its address for
    another account, is logged.
    """
    with services.database.transaction() as session:
        held = read_account(session, user_id)
    try:
        restored = services.keycloak_admin.change_identity(held.subject, local_identity(held, {}))
    except (UnavailableError, IdentityProviderError, UnprocessableError):
        logger.exception("account.identity_not_restored", user_id=str(user_id))
        return
    if not restored:
        logger.warning(
            "account.identity_not_restored", user_id=str(user_id), reason="address_taken"
        )


def close_sessions(admin: KeycloakAdmin, account: Account) -> None:
    """Have the provider close every session of an account a write leaves without access.

    On every device (WF-SEC-0020), once the write is committed: Keycloak notifies the front, which
    forgets them. A failure of Keycloak is said in the log and refuses nothing — the account is
    deactivated or holds no permission all the same, which the API reads at each request.
    """
    try:
        admin.close_sessions(account.subject)
    except (UnavailableError, IdentityProviderError):
        logger.exception("account.sessions_not_closed", user_id=str(account.user_id))
        return
    logger.info("account.sessions_closed", user_id=str(account.user_id))


@router.put(
    "/users/{user_id}/activation",
    operation_id="setUserActivation",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def put_user_activation(
    user_id: UUID, body: UserActivationWrite, account: Caller, actor: Acting, services: ServicesOf
) -> User:
    """Deactivate or reactivate an account, which keeps its roles (WF-ADM-0060).

    The deactivation of the last administrator is refused, as its command says in advance
    (WF-ADM-0120). A deactivation closes the sessions of the account, even of one deactivated
    already: asking again closes those a failure of the provider left open. It notes the moment
    first, with the deactivation: from then on the API refuses every token of a sign-in before
    it, refreshed or not, and a failure of the provider does not outlive a reactivation (#835).
    A local account anonymised is no longer in the provider: its deactivation asked again closes
    nothing. One of the directory or of an external provider anonymised is still the provider's,
    and has its sessions closed again, as any other.
    """
    act = Act(audit_actor(account), utc_now())
    with services.database.transaction() as session:
        with guard_deactivation(session):
            changed = set_account_activation(
                session,
                user_id,
                is_active=body.is_active,
                lock_version=body.lock_version.root,
                act=act,
            )
        is_closing = not body.is_active and not (
            changed.anonymized_at is not None and changed.origin == LOCAL
        )
        if is_closing:
            note_sessions_closed(session, user_id, utc_now())
        described = users(session, actor, [changed])[0]
    if is_closing:
        close_sessions(services.keycloak_admin, changed)
    return described


@router.post(
    "/users/{user_id}/anonymization",
    operation_id="anonymizeUser",
    dependencies=WRITE,
    response_model_exclude_unset=True,
)
def post_user_anonymization(
    user_id: UUID,
    body: UserAnonymizationWrite,
    account: Caller,
    actor: Acting,
    services: ServicesOf,
) -> User:
    """Anonymise a deactivated account at the request of its holder, for good (WF-ADM-0060).

    Its names, its address and its avatar are removed, and the journal of audit forgets its name
    (WF-SEC-0030); an active account, or one anonymised already, is refused. A local account is
    checked in a short transaction, then removed from the provider out of any (#669), then
    anonymised: while the provider does not answer, 503, nothing is written, and the
    anonymisation is asked again. An account the write refuses after all — changed meanwhile —
    is out of the provider all the same; if a reactivation slipped in between the check and the
    write, it is a local account active out of the provider, which no one can sign in to, until
    it is deactivated and anonymised again: the provider removes an account it no longer holds.
    Whether that gap is closed is #868's to decide. The account of the directory or of an
    external provider is the provider's, which Waterfall does not touch.
    """
    with services.database.transaction() as session:
        checked = check_account_anonymization(session, user_id, body.lock_version.root)
    if checked.origin == LOCAL:
        services.keycloak_admin.remove_account(checked.subject)
        logger.info("account.removed_from_provider", user_id=str(user_id))
    act = Act(audit_actor(account), utc_now())
    with services.database.transaction() as session:
        anonymized = anonymize_account(session, user_id, body.lock_version.root, act)
        return users(session, actor, [anonymized])[0]


@router.put(
    "/users/{user_id}/access-roles",
    operation_id="setUserAccessRoles",
    dependencies=ATTRIBUTE,
    response_model_exclude_unset=True,
)
def put_user_access_roles(
    user_id: UUID, body: UserRolesWrite, account: Caller, actor: Acting, services: ServicesOf
) -> User:
    """Set the roles of an account, which hold at its next request (WF-ADM-0050, WF-ADM-0090).

    Asks for the permission to change the roles besides that to change the accounts: giving a role
    is managing the roles (FBS-1.2, WF-ADM-0090), and who changes the accounts alone does not give
    himself the administration (#834).
    Roles that take the administration from the last administrator are refused (WF-ADM-0120). An
    account withdrawn all its roles has its sessions closed (WF-SEC-0020).
    """
    act = Act(audit_actor(account), utc_now())
    role_ids = [role_id.root for role_id in body.access_role_ids]
    with services.database.transaction() as session:
        attribution = set_access_roles(session, user_id, role_ids, body.lock_version.root, act)
        changed = read_account(session, user_id)
        described = users(session, actor, [changed])[0]
    if attribution.withdraws_all:
        close_sessions(services.keycloak_admin, changed)
    return described


@router.post(
    "/users/{user_id}/password-link",
    operation_id="createPasswordSetupLink",
    dependencies=WRITE,
    status_code=201,
)
def post_password_link(user_id: UUID, account: Caller, services: ServicesOf) -> PasswordSetupLink:
    """Give the link that sets the password of a local account, to hand it over (WF-ADM-0140).

    Made by the extension of Keycloak, valid one hour and once, the link made before it ceasing to
    be valid; an account that is not local, or deactivated, has none (409). The request is
    inscribed in the journal of audit once the link is made, without its token (WF-SEC-0030): a
    link the journal does not keep is never given. The account is read, the link made outside of
    any transaction (#669), then the account read again under a lock: one deactivated meanwhile is
    refused, and its link not given.
    """
    with services.database.transaction() as session:
        holder = password_link_holder(session, user_id)
    link = services.keycloak_admin.make_password_link(holder.subject)
    if link is None:
        raise password_link_not_local()
    act = Act(audit_actor(account), utc_now())
    given = PasswordSetupLink.model_validate({"url": link.url, "expires_at": link.expires_at})
    with services.database.transaction() as session:
        inscribe_password_link(session, user_id, act)
    logger.info("account.password_link_made", user_id=str(user_id))
    return given
