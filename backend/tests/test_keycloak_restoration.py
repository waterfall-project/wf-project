# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the service of the restoration asks of Keycloak, asked of the Keycloak of the platform.

The service account closes every session of the realm; the client of the bootstrap, which alone
holds ``manage-realm``, clears its caches — the accounts, the keys, then the realm — with the
token it took before (#954, #991). Run by ``make test-keycloak``, with the variables of
``test_keycloak_authentication.py`` and the secret of the client of the bootstrap. The whole
restoration, the realm applied again by ``keycloak-realm`` included, is held by
``make production-trial`` (#948).
"""

from collections.abc import Collection, Iterator
from typing import Any

import httpx2
import pytest
from pydantic import SecretStr
from test_keycloak_authentication import (
    refreshed,
    served_settings,
    service_admin,
    tokens_of,
    with_password,
)
from test_keycloak_platform import PASSWORD, Account, required

from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import INSTALLATION_CLIENT, KeycloakAdmin

pytestmark = pytest.mark.keycloak

INSTALLATION_CREDENTIAL_VARIABLE = "WATERFALL_INSTALLATION_CLIENT_SECRET"


@pytest.fixture
def keycloak() -> Iterator[Keycloak]:
    """Give the client of the realm the service of the restoration reaches."""
    client = Keycloak(served_settings())
    yield client
    client.close()


@pytest.fixture
def signed_in() -> Iterator[Account]:
    """Make a local account of the realm with a password, and remove it after."""
    with service_admin(served_settings()) as admin:
        made = with_password(admin, "Camille", "Restaurée")
        yield made
        admin.delete(f"/users/{made.id}")


def test_the_service_account_closes_every_session_of_the_realm(
    keycloak: Keycloak, signed_in: Account
) -> None:
    # Proper to US-0440: during a restoration, the users are signed out. A session open before
    # gives no token once the service has closed every session of the realm.
    tokens = tokens_of(signed_in.email, PASSWORD)
    KeycloakAdmin(keycloak, served_settings()).close_every_session()
    assert refreshed(tokens["refresh_token"]).status_code == 400


def test_the_client_of_the_bootstrap_clears_the_caches_with_the_token_it_took_before(
    keycloak: Keycloak,
) -> None:
    # #954, #991: the client of the bootstrap, manage-realm, clears the caches of the accounts, of
    # the keys and of the realm, with the token taken before: each answers 204.
    secret = SecretStr(required(INSTALLATION_CREDENTIAL_VARIABLE))
    installation = KeycloakAdmin(keycloak, served_settings(), client=(INSTALLATION_CLIENT, secret))
    installation.take_token()
    installation.clear_caches()


class Recording(Keycloak):
    """The client of the realm, which keeps the path of each request it sends."""

    def __init__(self) -> None:
        """Reach the realm of the platform, nothing asked yet."""
        super().__init__(served_settings())
        self.asked: list[str] = []

    def send(
        self, method: str, path: str, *, answered: Collection[int] = (), **options: Any
    ) -> httpx2.Response:
        """Keep the path, then send."""
        self.asked.append(path)
        return super().send(method, path, answered=answered, **options)


def test_the_client_of_the_bootstrap_takes_a_new_token_each_time_it_is_asked_to() -> None:
    # #955: the token the restoration takes before the database of Keycloak is replaced is a new
    # one, never one kept since an attempt before, which the caches cleared since may refuse.
    recording = Recording()
    secret = SecretStr(required(INSTALLATION_CREDENTIAL_VARIABLE))
    client = (INSTALLATION_CLIENT, secret)
    try:
        installation = KeycloakAdmin(recording, served_settings(), client=client)
        installation.take_token()
        installation.take_token()
    finally:
        recording.close()
    assert [path for path in recording.asked if path.endswith("/token")] == [
        f"{recording.protocol}/token"
    ] * 2
