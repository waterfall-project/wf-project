# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API and the Keycloak of the service platform: its tokens, its accounts, its sessions.

Run by ``make test-keycloak``, with the variables of ``test_keycloak_platform.py``, and
``WATERFALL_FRONT_CLIENT_SECRET`` and ``WATERFALL_TEST_FRONT_ADDRESS``, the client of the front
and its address, with which a person signs in as the front signs her in: the authorization code
flow with PKCE. The API is served in the process of the tests, on a database of their own.
"""

import base64
import hashlib
import secrets
import time
from collections.abc import Iterator
from typing import Any, cast
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx2
import pytest
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from pydantic import SecretStr
from sqlalchemy import insert
from support import ContractClient, raw_account
from test_keycloak_platform import (
    ADDRESS_VARIABLE,
    BACKCHANNEL_VARIABLE,
    DIRECTORY_EMAIL,
    EXTERNAL_PROVIDER,
    PASSWORD,
    REALM,
    SERVICE_CREDENTIAL_VARIABLE,
    Account,
    Browser,
    claims,
    required,
    set_password,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users import interface
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database
from waterfall.platform.keycloak import IdentityProviderError, Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.settings import ServiceSettings

pytestmark = pytest.mark.keycloak

FRONT_CREDENTIAL_VARIABLE = "WATERFALL_FRONT_CLIENT_SECRET"
FRONT_ADDRESS_VARIABLE = "WATERFALL_TEST_FRONT_ADDRESS"
FRONT_CLIENT = "waterfall-front"
# The person of the directory of test and of the external provider, with their development
# passwords (deploy/keycloak/development/).
DIRECTORY_CREDENTIAL = "development-only-directory-password"
EXTERNAL_USERNAME = "camille.externe"
EXTERNAL_CREDENTIAL = "development-only-external-password"
ME = "/api/v1/me"
SESSIONS = "/api/v1/me/sessions"
# An identifier the realm gives to no account.
NOBODY = "00000000-0000-4000-8000-000000000000"


class FrontBrowser(Browser):
    """A browser that signs in to the front: it stops where Keycloak sends it back to the front.

    It keeps the cookies of each realm apart by their path, as a browser does: the realm of
    Waterfall and the provider it relays to set cookies of the same names.
    """

    def __init__(self) -> None:
        """Start without a cookie."""
        super().__init__()
        self.jar: dict[tuple[str, str], str] = {}

    def _send(self, method: str, url: str, data: dict[str, str] | None = None) -> httpx2.Response:
        path = urlsplit(url).path
        # The cookie of the longest path is sent when two have one name.
        scoped = sorted(self.jar.items(), key=lambda item: len(item[0][0]))
        sent = {name: value for (scope, name), value in scoped if path.startswith(scope)}
        cookie = "; ".join(f"{name}={value}" for name, value in sent.items())
        response = httpx2.request(method, url, data=data, headers={"Cookie": cookie}, timeout=30)
        for header in response.headers.get_list("set-cookie"):
            pair, *attributes = header.split(";")
            name, value = pair.split("=", 1)
            paths = [part.split("=", 1)[1] for part in attributes if "path=" in part.lower()]
            self.jar[(paths[0].strip() if paths else "/", name.strip())] = value
        return response

    def sign_in(
        self, username: str, password: str, *, provider: str | None = None
    ) -> tuple[str, str]:
        """Sign in through the login page of the realm, or of the provider it relays to.

        Give the code the front receives on its return address, and the verifier of PKCE that
        goes with it.
        """
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        query = {
            "client_id": FRONT_CLIENT,
            "response_type": "code",
            "scope": "openid",
            "redirect_uri": callback(),
            "state": secrets.token_urlsafe(16),
            "code_challenge": challenge.decode().rstrip("="),
            "code_challenge_method": "S256",
        }
        if provider is not None:
            query["kc_idp_hint"] = provider
        page = self.get(f"{realm_address()}/protocol/openid-connect/auth?{urlencode(query)}")
        assert page.status_code == 200, page.text
        response = self.submit(page, {"username": username, "password": password})
        while not response.headers.get("Location", "").startswith(callback()):
            assert response.status_code in {302, 303}, response.text
            response = self._send("GET", response.headers["Location"])
        return parse_qs(urlsplit(response.headers["Location"]).query)["code"][0], verifier


def realm_address() -> str:
    """Give where the browser reaches the realm of Waterfall."""
    return f"{required(ADDRESS_VARIABLE).rstrip('/')}/realms/{REALM}"


def callback() -> str:
    """Give the return address of the front, where Keycloak sends the code."""
    return f"{required(FRONT_ADDRESS_VARIABLE).rstrip('/')}/auth/callback"


def front_grant(**fields: str) -> httpx2.Response:
    """Ask the realm for tokens as the front does, with its secret."""
    return httpx2.post(
        f"{realm_address()}/protocol/openid-connect/token",
        data={
            "client_id": FRONT_CLIENT,
            "client_secret": required(FRONT_CREDENTIAL_VARIABLE),
            **fields,
        },
        timeout=30,
    )


def tokens_of(username: str, password: str, *, provider: str | None = None) -> dict[str, Any]:
    """Sign a person in through the front, and give the tokens the front holds for her."""
    code, verifier = FrontBrowser().sign_in(username, password, provider=provider)
    response = front_grant(
        grant_type="authorization_code",
        code=code,
        redirect_uri=callback(),
        code_verifier=verifier,
    )
    assert response.status_code == 200, response.text
    return cast("dict[str, Any]", response.json())


def refreshed(refresh_token: str) -> httpx2.Response:
    """Exchange a refresh token for new tokens, as the front does."""
    return front_grant(grant_type="refresh_token", refresh_token=refresh_token)


def bearer(tokens: dict[str, Any]) -> dict[str, str]:
    """Give the header with which the front carries the access token to the API."""
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture(scope="module")
def settings() -> ServiceSettings:
    """Give the settings of an API served on the Keycloak of the platform."""
    # The database is the test's own, given to the application apart, and Redis serves nothing yet.
    return ServiceSettings.model_validate(
        {
            "database_url": "postgresql://unused@127.0.0.1/unused",
            "redis_url": "redis://unused",
            "keycloak_address": required(ADDRESS_VARIABLE),
            "keycloak_backchannel": required(BACKCHANNEL_VARIABLE),
            "service_client_secret": required(SERVICE_CREDENTIAL_VARIABLE),
        }
    )


@pytest.fixture
def keycloak(settings: ServiceSettings) -> Iterator[Keycloak]:
    """Give the client of the realm the API reaches."""
    client = Keycloak(settings)
    yield client
    client.close()


@pytest.fixture
def keycloak_admin(keycloak: Keycloak, settings: ServiceSettings) -> KeycloakAdmin:
    """Give the client of the administration API of the realm the API reaches."""
    return KeycloakAdmin(keycloak, settings)


@pytest.fixture
def api(
    contract: OpenAPI, database: Database, keycloak: Keycloak, keycloak_admin: KeycloakAdmin
) -> ContractClient:
    """Give a client of the API on the database of the test and the Keycloak of the platform."""
    app = create_app(Services(database, keycloak, keycloak_admin))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def admin(settings: ServiceSettings) -> Iterator[httpx2.Client]:
    """Reach the administration API of the realm as the service account, as the API does."""
    token = httpx2.post(
        f"{realm_address()}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "waterfall-service",
            "client_secret": settings.service_client_secret.get_secret_value(),
        },
        timeout=30,
    ).json()["access_token"]
    base = realm_address().replace("/realms/", "/admin/realms/")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx2.Client(base_url=base, headers=headers, timeout=30) as client:
        yield client


@pytest.fixture
def local_account(admin: httpx2.Client) -> Iterator[Account]:
    """Make a local account of the realm with a password, and remove it after."""
    email = f"test-{secrets.token_hex(6)}@example.org"
    response = admin.post(
        "/users",
        json={
            "username": email,
            "email": email,
            "firstName": "Claude",
            "lastName": "Locale",
            "enabled": True,
        },
    )
    assert response.status_code == 201, response.text
    user_id = response.headers["Location"].rsplit("/", 1)[-1]
    set_password(admin, user_id, PASSWORD)
    yield Account(user_id, email)
    admin.delete(f"/users/{user_id}")


def known(database: Database, account: Account, **overrides: object) -> dict[str, Any]:
    """Give Waterfall the account the realm holds, as the creation of a local account does."""
    row = raw_account(email=account.email, idp_subject=account.id, **overrides)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    return row


@pytest.mark.requirement("WF-ARC-0030-A")
def test_a_refresh_token_already_used_is_refused(local_account: Account) -> None:
    tokens = tokens_of(local_account.email, PASSWORD)
    renewed = refreshed(tokens["refresh_token"])
    assert renewed.status_code == 200, renewed.text
    # Its use gave a new one, and it serves no more.
    assert renewed.json()["refresh_token"] != tokens["refresh_token"]
    again = refreshed(tokens["refresh_token"])
    assert (again.status_code, again.json()["error"]) == (400, "invalid_grant")


def test_an_access_token_of_the_realm_names_the_account_waterfall_holds(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    row = known(database, local_account)
    response = api.get(ME, headers=bearer(tokens_of(local_account.email, PASSWORD)))
    assert response.status_code == 200, response.text
    assert (response.json()["user_id"], response.json()["origin"]) == (str(row["id"]), "local")


def test_a_deactivated_account_is_refused_with_a_token_of_the_realm(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    known(database, local_account, state="deactivated")
    response = api.get(ME, headers=bearer(tokens_of(local_account.email, PASSWORD)))
    assert (response.status_code, response.json()["code"]) == (401, "ACCOUNT_DEACTIVATED")


def created(database: Database, tokens: dict[str, Any]) -> interface.Account | None:
    """Read the account Waterfall holds for the person the tokens are lent to."""
    with database.transaction() as session:
        return interface.read_account_of_subject(session, claims(tokens["access_token"])["sub"])


def test_a_person_of_the_directory_is_created_without_any_role_at_her_first_request(
    api: ContractClient, database: Database, admin: httpx2.Client
) -> None:
    tokens = tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL)
    assert created(database, tokens) is None
    response = api.get(ME, headers=bearer(tokens))
    assert response.status_code == 200, response.text
    # A special-use domain, `.test`: the address is given back as the provider transmits it.
    assert (response.json()["email"], response.json()["origin"]) == (DIRECTORY_EMAIL, "directory")
    account = created(database, tokens)
    assert account is not None
    # With the names and the address the provider transmits (WF-ADM-0180).
    held = admin.get(f"/users/{account.subject}").json()
    assert (account.email, account.first_name, account.last_name, account.origin) == (
        DIRECTORY_EMAIL,
        held["firstName"],
        held["lastName"],
        "directory",
    )
    assert (account.is_active, account.created_by) == (True, None)


def test_a_person_relayed_by_an_external_provider_is_created_without_any_role(
    api: ContractClient, database: Database
) -> None:
    tokens = tokens_of(EXTERNAL_USERNAME, EXTERNAL_CREDENTIAL, provider=EXTERNAL_PROVIDER)
    response = api.get(ME, headers=bearer(tokens))
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "camille.externe@external.test"
    account = created(database, tokens)
    assert account is not None
    assert (account.email, account.origin, account.created_by) == (
        "camille.externe@external.test",
        "identity_provider",
        None,
    )


def test_a_local_account_of_the_realm_unknown_to_waterfall_is_refused(
    api: ContractClient, local_account: Account
) -> None:
    # A local account is created from Waterfall, never at its first request (WF-ADM-0070).
    response = api.get(ME, headers=bearer(tokens_of(local_account.email, PASSWORD)))
    assert (response.status_code, response.json()["code"]) == (401, "ACCOUNT_DEACTIVATED")


def test_a_token_the_realm_lends_to_its_command_line_is_refused(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    # The client every realm has, which a password signs in to (#644): not the audience of the API.
    known(database, local_account)
    lent = httpx2.post(
        f"{realm_address()}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": local_account.email,
            "password": PASSWORD,
        },
        timeout=30,
    )
    assert lent.status_code == 200, lent.text
    response = api.get(ME, headers=bearer(lent.json()))
    assert (response.status_code, response.json()["code"]) == (401, "SESSION_REQUIRED")


def test_closing_my_sessions_closes_them_on_every_device(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    known(database, local_account)
    office = tokens_of(local_account.email, PASSWORD)
    home = tokens_of(local_account.email, PASSWORD)
    response = api.delete(SESSIONS, headers=bearer(office))
    assert response.status_code == 204, response.text
    for device in (office, home):
        again = refreshed(device["refresh_token"])
        assert (again.status_code, again.json()["error"]) == (400, "invalid_grant")


def test_a_service_account_with_another_secret_is_a_defect_of_the_platform(
    keycloak: Keycloak, settings: ServiceSettings
) -> None:
    wrong = settings.model_copy(update={"service_client_secret": SecretStr("not-the-secret")})
    with pytest.raises(IdentityProviderError, match="answered 401"):
        KeycloakAdmin(keycloak, wrong).close_sessions(NOBODY)


def test_an_account_the_realm_does_not_hold_is_read_as_none_and_has_no_session(
    keycloak_admin: KeycloakAdmin,
) -> None:
    assert keycloak_admin.read_account(NOBODY) is None
    keycloak_admin.close_sessions(NOBODY)


def test_a_token_of_the_service_account_refused_before_its_time_is_renewed(
    keycloak_admin: KeycloakAdmin, admin: httpx2.Client
) -> None:
    (person,) = admin.get("/users", params={"email": DIRECTORY_EMAIL, "exact": "true"}).json()
    (service,) = admin.get(
        "/users", params={"username": "service-account-waterfall-service", "exact": "true"}
    ).json()
    assert keycloak_admin.read_account(person["id"]) is not None
    # Closing the sessions of the service account refuses every token lent to it before the
    # second they are closed: the one the client keeps, and the one of `admin`, used no more.
    time.sleep(1.1)
    assert admin.post(f"/users/{service['id']}/logout").status_code == 204
    read = keycloak_admin.read_account(person["id"])
    assert read is not None
    assert (read.email, read.is_federated) == (DIRECTORY_EMAIL, True)
