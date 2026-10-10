# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The image of Keycloak on the service platform: its realm is applied, its extension answers.

These tests run against the Keycloak of the service platform, its realm applied
(``make test-keycloak``), not with the other tests of the back, which deselect them:
``WATERFALL_TEST_KEYCLOAK_ADDRESS`` is where they reach it, and
``WATERFALL_SERVICE_CLIENT_SECRET`` the secret its realm was applied with. Without them they
fail and say so. What the requirements ask of Keycloak — the lockout, the links used or
expired, the sign-in of each kind of account — is proved by the tests of the stories that
use it (US-0350).
"""

import base64
import json
import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import httpx2
import pytest

pytestmark = pytest.mark.keycloak

ADDRESS_VARIABLE = "WATERFALL_TEST_KEYCLOAK_ADDRESS"
SERVICE_CREDENTIAL_VARIABLE = "WATERFALL_SERVICE_CLIENT_SECRET"
REALM = "waterfall"
# The person of the directory of test (deploy/keycloak/development/directory.ldif).
DIRECTORY_EMAIL = "dominique.annuaire@waterfall.test"


def required(variable: str) -> str:
    """Read a variable the tests of Keycloak need, or fail naming it."""
    value = os.environ.get(variable)
    if not value:
        pytest.fail(f"{variable} is not set: run these tests by make test-keycloak")
    return value


@pytest.fixture(scope="module")
def keycloak() -> Iterator[httpx2.Client]:
    """Reach the realm of Waterfall at the address the browser knows Keycloak by."""
    address = required(ADDRESS_VARIABLE).rstrip("/")
    with httpx2.Client(base_url=f"{address}/realms/{REALM}", timeout=30) as client:
        yield client


@pytest.fixture(scope="module")
def service_token(keycloak: httpx2.Client) -> str:
    """Obtain a token of the service account of Waterfall, by its client credentials."""
    response = keycloak.post(
        "/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": "waterfall-service",
            "client_secret": required(SERVICE_CREDENTIAL_VARIABLE),
        },
    )
    assert response.status_code == 200, response.text
    return cast("str", response.json()["access_token"])


@pytest.fixture(scope="module")
def admin(keycloak: httpx2.Client, service_token: str) -> Iterator[httpx2.Client]:
    """Reach the administration API of the realm as the service account."""
    base = str(keycloak.base_url).replace("/realms/", "/admin/realms/")
    headers = {"Authorization": f"Bearer {service_token}"}
    with httpx2.Client(base_url=base, headers=headers, timeout=30) as client:
        yield client


@pytest.fixture
def local_account(admin: httpx2.Client) -> Iterator[str]:
    """Make a local account without a password for the test, and remove it after."""
    email = f"test-{uuid4().hex[:12]}@waterfall.test"
    response = admin.post(
        "/users",
        json={
            "username": email,
            "email": email,
            "firstName": "Jeanne",
            "lastName": "Montgolfier-Durand",
            "enabled": True,
        },
    )
    assert response.status_code == 201, response.text
    user_id = response.headers["Location"].rsplit("/", 1)[-1]
    yield user_id
    admin.delete(f"/users/{user_id}")


def link_of(keycloak: httpx2.Client, user_id: str, token: str | None) -> httpx2.Response:
    """Ask the extension for the password setup link of an account."""
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    return keycloak.post(f"/password-setup-link/users/{user_id}", headers=headers)


def claims(token: str) -> dict[str, Any]:
    """Read the claims of a token the test was just given by Keycloak, without checking it."""
    payload = token.split(".")[1]
    decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    return cast("dict[str, Any]", json.loads(decoded))


def test_the_realm_lends_tokens_of_five_minutes_to_the_service_account(
    service_token: str,
) -> None:
    read = claims(service_token)
    assert read["exp"] - read["iat"] == 300
    assert read["azp"] == "waterfall-service"


def test_the_password_policy_holds_the_rule_of_the_extension(
    admin: httpx2.Client, local_account: str
) -> None:
    def refusal(password: str) -> str:
        response = admin.put(
            f"/users/{local_account}/reset-password",
            json={"type": "password", "value": password, "temporary": False},
        )
        assert response.status_code == 400, response.text
        return cast("str", response.json()["error"])

    assert refusal("montgolfier-DURAND") == "invalidPasswordNotLastNameMessage"
    assert refusal("eleven-char") == "invalidPasswordMinLengthMessage"


def test_a_caller_without_a_token_of_the_realm_gets_no_link(
    keycloak: httpx2.Client, local_account: str
) -> None:
    assert link_of(keycloak, local_account, None).status_code == 401
    assert link_of(keycloak, local_account, "not-a-token").status_code == 401


def test_a_link_is_valid_one_hour_and_the_next_one_invalidates_it(
    keycloak: httpx2.Client, service_token: str, local_account: str
) -> None:
    before = time.time()
    first = link_of(keycloak, local_account, service_token)
    assert first.status_code == 200, first.text
    link = first.json()
    realm = str(keycloak.base_url).rstrip("/")
    assert link["url"].startswith(f"{realm}/login-actions/action-token?key=")
    expires_at = datetime.fromisoformat(link["expires_at"])
    assert expires_at.tzinfo == UTC
    assert before + 3600 - 5 <= expires_at.timestamp() <= time.time() + 3600 + 5
    second = link_of(keycloak, local_account, service_token)
    assert second.status_code == 200, second.text
    assert second.json()["url"] != link["url"]
    # The page of Keycloak refuses the first link, and asks to confirm the second.
    assert httpx2.get(link["url"], timeout=30).status_code == 400
    page = httpx2.get(second.json()["url"], timeout=30)
    assert page.status_code == 200
    assert "login-actions/action-token" in page.text


def test_an_account_the_realm_does_not_hold_has_no_link(
    keycloak: httpx2.Client, service_token: str
) -> None:
    response = link_of(keycloak, str(uuid4()), service_token)
    assert (response.status_code, response.json()) == (404, {"error": "unknown_user"})


def test_an_account_of_the_directory_has_no_link(
    keycloak: httpx2.Client, admin: httpx2.Client, service_token: str
) -> None:
    # Searching the realm reads the person from the federated directory.
    found = admin.get("/users", params={"email": DIRECTORY_EMAIL, "exact": "true"}).json()
    assert [user["email"] for user in found] == [DIRECTORY_EMAIL]
    response = link_of(keycloak, found[0]["id"], service_token)
    assert (response.status_code, response.json()) == (409, {"error": "not_local"})
