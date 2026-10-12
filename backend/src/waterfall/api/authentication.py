# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Who calls: the access token validated, the account read, its state checked, every request.

The API takes nothing from the token but its subject and the moment of its sign-in (WF-ARC-0030):
the account is read in the base by ``idp_subject``, and its state with it, so that a deactivated
account is refused at its next request even if the closing of its sessions was lost
(WF-SEC-0020); a token of a sign-in before the account last closed its sessions — signed out
(#668), deactivated (#835) or withdrawn all its roles (#855) — is refused as revoked, whichever
client it was lent to, refreshed or not: not as expired, since a session of Keycloak the closing
missed would give back a token of the same sign-in, and only a sign-in that asks for the
identifiers again renews it (#855).
A subject Waterfall does not know yet is a person of the directory before the first reading of
the accounts, or a person relayed by an external provider: her account is created without any
role, after her origin is read from the administration API of Keycloak (WF-ADM-0180) — or, for a
person of the directory whose address an account holds, that account is hers (#707). Any other
one is refused as an account Waterfall does not admit (#664) — not as a deactivated account,
which it never was, nor as a missing session, to which the front would answer with a sign-in that
brings back the same token, in a loop.

No call to Keycloak is made inside a transaction (#669): the account is read, then admitted, each
in a short transaction of its own, the origin being read between the two; a route that reads or
writes the base takes its own transaction, ``Transaction``. A connection held while Keycloak is
slow would exhaust the pool, and requests that do not need Keycloak would fail (WF-EXP-0040).
"""

from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session
from structlog.contextvars import bind_contextvars

from waterfall.core.users.interface import (
    Account,
    NotAdmitted,
    add_account_of_provider,
    read_account_of_subject,
)
from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import UnauthenticatedError
from waterfall.platform.keycloak import SESSION_REQUIRED, Bearer, Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin, ProviderAccount
from waterfall.platform.logs import get_logger
from waterfall.platform.queue import TaskQueue
from waterfall.platform.storage import Bucket

ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"
ACCOUNT_NOT_ADMITTED = "ACCOUNT_NOT_ADMITTED"
SESSION_REVOKED = "SESSION_REVOKED"
SCHEME = "bearer"

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Services:
    """What the routes of a process reach: its database, Keycloak and its administration API.

    And the queue its tasks are deposited in, and the bucket of the backups.
    """

    database: Database
    keycloak: Keycloak
    keycloak_admin: KeycloakAdmin
    queue: TaskQueue
    backups: Bucket


def services_of(request: Request) -> Services:
    """Give the services of the application that serves the request."""
    return cast("Services", request.app.state.services)


ServicesOf = Annotated[Services, Depends(services_of)]


def transaction(services: ServicesOf) -> Generator[Session]:
    """Run the request in one transaction, committed once the route has built its answer."""
    with services.database.transaction() as session:
        yield session


# Closed when the route returns, before the answer leaves: a commit that fails is a 500, never
# an answer that says done (defect no. 3 of the guide).
Transaction = Annotated[Session, Depends(transaction, scope="function")]


def bearer_token(request: Request) -> str:
    """Read the access token of the ``Authorization`` header, or refuse the request (401)."""
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != SCHEME or not token.strip():
        raise UnauthenticatedError(SESSION_REQUIRED)
    return token.strip()


def identify(request: Request, services: ServicesOf) -> Account:
    """Give the account of the caller, created if the provider admits it, or refuse it (401).

    A token of a sign-in that precedes the last closing of the sessions of the account — its
    holder's sign-out (#668), its deactivation (#835), the withdrawal of all its roles — is refused
    as revoked, ``SESSION_REVOKED``, on which alone the front asks for the identifiers again
    (#855).
    """
    bearer = services.keycloak.validate(bearer_token(request))
    subject = bearer.subject
    with services.database.transaction() as session:
        account = read_account_of_subject(session, subject)
    if account is None:
        provider = services.keycloak_admin.read_account(subject)
        with services.database.transaction() as session:
            account = admit(session, subject, provider)
    if not account.is_active:
        raise UnauthenticatedError(ACCOUNT_DEACTIVATED)
    if signed_in_before_sessions_closed(bearer, account.sessions_closed_at):
        raise UnauthenticatedError(SESSION_REVOKED)
    return account


def signed_in_before_sessions_closed(bearer: Bearer, sessions_closed_at: datetime | None) -> bool:
    """Tell whether the sign-in of a token may precede the last closing of the account's sessions.

    The sign-in, not the issue: a token refreshed since, of a session Keycloak failed to close,
    is refused all the same, and an account deactivated then reactivated signs in again (#835).
    The moment is written to the second: a sign-in of the very second of the closing may precede
    it, and is refused, rather than let a session the closing missed act on — the person signs in
    again, giving her identifiers, as after any closing (#855).
    """
    return sessions_closed_at is not None and bearer.signed_in_at <= sessions_closed_at


def admit(session: Session, subject: str, provider: ProviderAccount | None) -> Account:
    """Create or attach the account of a person Waterfall does not know yet, or refuse her (401).

    ``provider`` is the account the realm holds for ``subject``, ``None`` if it holds none. The
    creation or the attachment is inscribed in the journal of audit by the platform (#703, #707).
    A refusal says
    ``ACCOUNT_NOT_ADMITTED``; its cause is written in the log only.
    """
    admitted = (
        NotAdmitted.UNKNOWN_TO_PROVIDER
        if provider is None
        else add_account_of_provider(session, provider, utc_now())
    )
    if isinstance(admitted, NotAdmitted):
        logger.warning("account.not_admitted", subject=subject, reason=admitted.value)
        raise UnauthenticatedError(ACCOUNT_NOT_ADMITTED)
    logger.info("account.created", user_id=str(admitted.user_id), origin=admitted.origin)
    return admitted


async def caller(account: Annotated[Account, Depends(identify)]) -> Account:
    """Name the caller as the author of every record the request writes from now on.

    It runs in the task of the request, unlike ``identify`` which runs in a thread of its own:
    what it binds reaches the route and the record that closes the request (WF-OBS-0020).
    """
    bind_contextvars(actor=str(account.user_id))
    return account


Caller = Annotated[Account, Depends(caller)]
