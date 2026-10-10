# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Who calls: the access token validated, the account read, its state checked, every request.

The API takes nothing from the token but its subject (WF-ARC-0030): the account is read in the
base by ``idp_subject``, and its state with it, so that a deactivated account is refused at its
next request even if the closing of its sessions was lost (WF-SEC-0020). A subject Waterfall
does not know yet is a person of the directory before the first reading of the accounts, or a
person relayed by an external provider: her account is created without any role, after her
origin is read from the administration API of Keycloak (WF-ADM-0180). Any other one is refused
as a deactivated account is — and not as a missing session, to which the front would answer
with a sign-in that brings back the same token, in a loop.
"""

from collections.abc import Generator
from dataclasses import dataclass
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
from waterfall.platform.keycloak import SESSION_REQUIRED, Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin, ProviderAccount
from waterfall.platform.logs import get_logger

ACCOUNT_DEACTIVATED = "ACCOUNT_DEACTIVATED"
SCHEME = "bearer"

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Services:
    """What the routes of a process reach: its database, Keycloak and its administration API."""

    database: Database
    keycloak: Keycloak
    keycloak_admin: KeycloakAdmin


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


def identify(request: Request, session: Transaction, services: ServicesOf) -> Account:
    """Give the account of the caller, created if the provider admits it, or refuse it (401)."""
    subject = services.keycloak.subject_of(bearer_token(request))
    account = read_account_of_subject(session, subject)
    if account is None:
        account = admit(session, subject, services.keycloak_admin.read_account(subject))
    if not account.is_active:
        raise UnauthenticatedError(ACCOUNT_DEACTIVATED)
    return account


def admit(session: Session, subject: str, provider: ProviderAccount | None) -> Account:
    """Create the account of a person Waterfall does not know yet, or refuse her (401).

    ``provider`` is the account the realm holds for ``subject``, ``None`` if it holds none.
    """
    admitted = (
        NotAdmitted.UNKNOWN_TO_PROVIDER
        if provider is None
        else add_account_of_provider(session, provider, utc_now())
    )
    if isinstance(admitted, NotAdmitted):
        logger.warning("account.not_admitted", subject=subject, reason=admitted.value)
        # TODO(#664): a code of its own; an account never created is not a deactivated one.
        raise UnauthenticatedError(ACCOUNT_DEACTIVATED)
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
