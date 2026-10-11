# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The image of Keycloak on the service platform: its realm is applied, its extension answers.

These tests run against the Keycloak of the service platform, its realm applied
(``make test-keycloak``), not with the other tests of the back, which deselect them:
``WATERFALL_TEST_KEYCLOAK_ADDRESS`` is where the browser reaches it,
``WATERFALL_TEST_KEYCLOAK_BACKCHANNEL`` another address, where a service reaches it — both in
HTTPS, through its front end, whose authority ``SSL_CERT_FILE`` names, the only one they trust
(#680) —, ``WATERFALL_SERVICE_CLIENT_SECRET`` the secret its realm was applied with, and
``WATERFALL_KEYCLOAK_ADMIN_PASSWORD`` the administrator that applied it. Without them they
fail and say so. The mails Keycloak sends are read in the Mailpit of the platform, on the port
``WATERFALL_MAILPIT_PORT`` publishes, 8025 unless it says another, as Compose does. They try the
platform and cite no requirement: what the requirements ask of Keycloak — the lockout, a link used
or expired, the sign-in of each kind of account through the front — is proved by the tests of the
lot that closes those criteria (US-0350/L5).
"""

import base64
import html
import json
import os
import re
import secrets
import time
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx2
import pytest

pytestmark = pytest.mark.keycloak

ADDRESS_VARIABLE = "WATERFALL_TEST_KEYCLOAK_ADDRESS"
BACKCHANNEL_VARIABLE = "WATERFALL_TEST_KEYCLOAK_BACKCHANNEL"
SERVICE_CREDENTIAL_VARIABLE = "WATERFALL_SERVICE_CLIENT_SECRET"
ADMIN_CREDENTIAL_VARIABLE = "WATERFALL_KEYCLOAK_ADMIN_PASSWORD"
REALM = "waterfall"
# The person of the directory of test (deploy/keycloak/development/directory.ldif).
DIRECTORY_EMAIL = "dominique.annuaire@waterfall.test"
# The external provider the realm relays to on the development platform
# (deploy/keycloak/development/waterfall.yaml).
EXTERNAL_PROVIDER = "external"
# A password the policy of the realm accepts: long enough, neither an address nor a name.
PASSWORD = secrets.token_urlsafe(24)
# The page of a replaced link, in the login theme of Waterfall, in French by default.
REPLACED = "Ce lien a été remplacé par un plus récent"
MAILPIT_PORT_VARIABLE = "WATERFALL_MAILPIT_PORT"
# The type of the action token of a link the extension makes (PasswordSetupToken).
EXTENSION_ACTION = "waterfall-password-setup"
# The client the development platform declares for the tokens its tests sign in for by a password
# (deploy/keycloak/development/waterfall.yaml, #644).
TEST_CLIENT = "waterfall-test"
# A mail server on a port of the container of Keycloak where nothing listens.
UNREACHABLE_MAIL_SERVER = {"host": "127.0.0.1", "port": "9", "from": "waterfall@waterfall.test"}


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
def backchannel(keycloak: httpx2.Client) -> Iterator[httpx2.Client]:
    """Reach the realm at another address than the browser's, as a service of the platform does."""
    address = required(BACKCHANNEL_VARIABLE).rstrip("/")
    base_url = f"{address}/realms/{REALM}"
    if base_url == str(keycloak.base_url).rstrip("/"):
        pytest.fail(f"{BACKCHANNEL_VARIABLE} must differ from {ADDRESS_VARIABLE}")
    with httpx2.Client(base_url=base_url, timeout=30) as client:
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


@contextmanager
def administering() -> Generator[httpx2.Client]:
    """Reach the administration API of the realm as the administrator who applies it.

    The service account may not read the settings of the realm nor its clients.
    """
    address = required(ADDRESS_VARIABLE).rstrip("/")
    response = httpx2.post(
        f"{address}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "admin",
            "password": required(ADMIN_CREDENTIAL_VARIABLE),
        },
        timeout=30,
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    base = f"{address}/admin/realms/{REALM}"
    with httpx2.Client(base_url=base, headers=headers, timeout=30) as client:
        yield client


@pytest.fixture(scope="module")
def realm_admin() -> Iterator[httpx2.Client]:
    """Reach the administration API of the realm as the administrator who applies it."""
    with administering() as client:
        yield client


@contextmanager
def mail_server(settings: dict[str, str]) -> Generator[None]:
    """Give the realm the mail server ``settings`` describe for a while, then the one it had."""
    with administering() as realm:

        def configure(server: dict[str, str]) -> None:
            response = realm.put("", json={"smtpServer": server})
            assert response.status_code == 204, response.text

        kept = realm.get("").json().get("smtpServer", {})
        configure(settings)
        try:
            yield
        finally:
            configure(kept)


@dataclass(frozen=True, slots=True)
class Account:
    """An account of the realm made for a test."""

    id: str
    email: str


@pytest.fixture
def local_account(admin: httpx2.Client) -> Iterator[Account]:
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
    yield Account(user_id, email)
    admin.delete(f"/users/{user_id}")


def link_of(backchannel: httpx2.Client, user_id: str, token: str | None) -> httpx2.Response:
    """Ask the extension for the password setup link of an account, as the service does."""
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    return backchannel.post(f"/password-setup-link/users/{user_id}", headers=headers)


def set_password(admin: httpx2.Client, user_id: str, password: str) -> None:
    """Give an account a password, as an administrator does in the console."""
    response = admin.put(
        f"/users/{user_id}/reset-password",
        json={"type": "password", "value": password, "temporary": False},
    )
    assert response.status_code == 204, response.text


def password_grant(
    keycloak: httpx2.Client, account: Account, password: str, *, client: str = TEST_CLIENT
) -> httpx2.Response:
    """Sign in with a password, through the client of test of the development platform."""
    return keycloak.post(
        "/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": client,
            "username": account.email,
            "password": password,
        },
    )


class Browser:
    """Follow the pages of Keycloak as a browser does, with the cookies of its session.

    Keycloak marks them ``Secure``, which a browser honours on ``localhost`` and httpx2 does
    not: they are kept here and sent back by hand.
    """

    def __init__(self) -> None:
        """Start without a cookie, as a browser that opens a link from a mail."""
        self.cookies: dict[str, str] = {}

    def _send(self, method: str, url: str, data: dict[str, str] | None = None) -> httpx2.Response:
        cookie = "; ".join(f"{name}={value}" for name, value in self.cookies.items())
        response = httpx2.request(method, url, data=data, headers={"Cookie": cookie}, timeout=30)
        for header in response.headers.get_list("set-cookie"):
            name, value = header.split(";", 1)[0].split("=", 1)
            self.cookies[name] = value
        return response

    def get(self, url: str) -> httpx2.Response:
        """Open a page, following its redirects."""
        response = self._send("GET", url)
        while response.status_code in {302, 303}:
            response = self._send("GET", response.headers["Location"])
        return response

    def submit(self, page: httpx2.Response, fields: dict[str, str]) -> httpx2.Response:
        """Submit the one form of a page."""
        action = re.search(r'<form[^>]*\baction="([^"]*)"', page.text)
        assert action is not None, page.text
        return self._send("POST", html.unescape(action.group(1)), fields)


def confirmation_target(page: httpx2.Response) -> str:
    """Read the address a confirmation page leads to, once the person goes on."""
    target = re.search(r'href="([^"]*login-actions/action-token[^"]*)"', page.text)
    assert target is not None, page.text
    return html.unescape(target.group(1))


def invite(backchannel: httpx2.Client, user_id: str, token: str | None) -> httpx2.Response:
    """Ask the extension to mail an account its invitation, as the service does."""
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    return backchannel.post(f"/password-setup-link/users/{user_id}/invitation", headers=headers)


def mailed_link(address: str) -> str:
    """Wait for the mail Keycloak sent to an address, ten seconds at most; give its link."""
    port = os.environ.get(MAILPIT_PORT_VARIABLE) or "8025"
    deadline = time.monotonic() + 10
    with httpx2.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as mailpit:
        while time.monotonic() < deadline:
            found = mailpit.get("/api/v1/search", params={"query": f'to:"{address}"'}).json()
            if found["messages"]:
                message = mailpit.get(f"/api/v1/message/{found['messages'][0]['ID']}").json()
                link = re.search(
                    r"https://\S+/login-actions/action-token\?key=[\w.-]+", message["Text"]
                )
                assert link is not None, message["Text"]
                return link.group(0)
            time.sleep(0.2)
    pytest.fail(f"no mail reached {address} within ten seconds")


def action_token(url: str) -> dict[str, Any]:
    """Read the claims of the action token a link carries."""
    return claims(parse_qs(urlsplit(url).query)["key"][0])


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


def test_the_command_line_client_of_the_realm_takes_no_password(
    keycloak: httpx2.Client, admin: httpx2.Client, local_account: Account
) -> None:
    # No second way of signing in around the page of the realm (#644): the client every realm has
    # for its command line refuses a password the client of test takes.
    set_password(admin, local_account.id, PASSWORD)
    refused = password_grant(keycloak, local_account, PASSWORD, client="admin-cli")
    assert (refused.status_code, refused.json()["error"]) == (400, "unauthorized_client")
    assert password_grant(keycloak, local_account, PASSWORD).status_code == 200


def test_the_lockout_is_ten_failures_fifteen_minutes_and_does_not_outlive_its_lock(
    realm_admin: httpx2.Client,
) -> None:
    realm = realm_admin.get("").json()
    lockout = {
        key: realm[key]
        for key in (
            "bruteForceProtected",
            "permanentLockout",
            "failureFactor",
            "bruteForceStrategy",
            "waitIncrementSeconds",
            "maxFailureWaitSeconds",
            "maxDeltaTimeSeconds",
            "quickLoginCheckMilliSeconds",
        )
    }
    assert lockout == {
        "bruteForceProtected": True,
        "permanentLockout": False,
        "failureFactor": 10,
        "bruteForceStrategy": "MULTIPLE",
        "waitIncrementSeconds": 900,
        "maxFailureWaitSeconds": 900,
        # Under the fifteen minutes of a lock: the first failure after it starts a new count.
        "maxDeltaTimeSeconds": 899,
        "quickLoginCheckMilliSeconds": 0,
    }


def test_the_front_cannot_obtain_an_offline_token(realm_admin: httpx2.Client) -> None:
    found = realm_admin.get("/clients", params={"clientId": "waterfall-front"}).json()
    assert [client["clientId"] for client in found] == ["waterfall-front"]
    front = found[0]
    assert front["fullScopeAllowed"] is False
    assert front["optionalClientScopes"] == []
    assert sorted(front["defaultClientScopes"]) == [
        "acr",
        "basic",
        "email",
        "profile",
        "roles",
        "web-origins",
    ]


def test_the_password_policy_holds_the_rule_of_the_extension(
    admin: httpx2.Client, local_account: Account
) -> None:
    def refusal(password: str) -> dict[str, str]:
        response = admin.put(
            f"/users/{local_account.id}/reset-password",
            json={"type": "password", "value": password, "temporary": False},
        )
        assert response.status_code == 400, response.text
        return cast("dict[str, str]", response.json())

    last_name = refusal("montgolfier-DURAND")
    assert last_name["error"] == "invalidPasswordNotLastNameMessage"
    # The words of the administration theme of Waterfall, not the bare key.
    assert last_name["error_description"] == "Invalid password: must not be the last name."
    assert refusal("eleven-char")["error"] == "invalidPasswordMinLengthMessage"


def test_a_caller_without_a_token_of_the_realm_gets_no_link(
    backchannel: httpx2.Client, local_account: Account
) -> None:
    for token in (None, "not-a-token"):
        response = link_of(backchannel, local_account.id, token)
        assert (response.status_code, response.json()) == (401, {"error": "not_authenticated"})


def test_a_token_without_the_role_of_the_extension_gets_no_link_nor_invitation(
    keycloak: httpx2.Client,
    backchannel: httpx2.Client,
    admin: httpx2.Client,
    local_account: Account,
) -> None:
    set_password(admin, local_account.id, PASSWORD)
    signed_in = password_grant(keycloak, local_account, PASSWORD)
    assert signed_in.status_code == 200, signed_in.text
    token = signed_in.json()["access_token"]
    response = link_of(backchannel, local_account.id, token)
    assert (response.status_code, response.json()) == (403, {"error": "not_allowed"})
    invitation = invite(backchannel, local_account.id, token)
    assert (invitation.status_code, invitation.json()) == (403, {"error": "not_allowed"})


def test_a_link_is_valid_one_hour_and_the_next_one_invalidates_it(
    keycloak: httpx2.Client, backchannel: httpx2.Client, service_token: str, local_account: Account
) -> None:
    before = time.time()
    first = link_of(backchannel, local_account.id, service_token)
    assert first.status_code == 200, first.text
    link = first.json()
    # Asked for at the address of the service, the link carries the address of the browser.
    realm = str(keycloak.base_url).rstrip("/")
    assert link["url"].startswith(f"{realm}/login-actions/action-token?key=")
    expires_at = datetime.fromisoformat(link["expires_at"])
    assert expires_at.tzinfo == UTC
    assert before + 3600 - 5 <= expires_at.timestamp() <= time.time() + 3600 + 5
    second = link_of(backchannel, local_account.id, service_token)
    assert second.status_code == 200, second.text
    assert second.json()["url"] != link["url"]
    # The page of Keycloak refuses the first link, saying it was replaced, and asks to confirm
    # the second.
    replaced = Browser().get(link["url"])
    assert replaced.status_code == 400
    assert REPLACED in html.unescape(replaced.text)
    page = Browser().get(second.json()["url"])
    assert page.status_code == 200
    assert confirmation_target(page).startswith(f"{realm}/login-actions/action-token?key=")


def test_a_link_sets_the_password_once(
    keycloak: httpx2.Client, backchannel: httpx2.Client, service_token: str, local_account: Account
) -> None:
    made = link_of(backchannel, local_account.id, service_token)
    assert made.status_code == 200, made.text
    url = made.json()["url"]
    browser = Browser()
    form = browser.get(confirmation_target(browser.get(url)))
    assert form.status_code == 200
    assert 'name="password-new"' in form.text
    done = browser.submit(form, {"password-new": PASSWORD, "password-confirm": PASSWORD})
    assert done.status_code == 200, done.text
    assert password_grant(keycloak, local_account, PASSWORD).status_code == 200
    # Opened again, in the same browser or another one, the link is spent.
    assert browser.get(url).status_code == 400
    assert Browser().get(url).status_code == 400


def test_a_link_is_spent_once_confirmed_and_its_form_stays_open(
    keycloak: httpx2.Client, backchannel: httpx2.Client, service_token: str, local_account: Account
) -> None:
    # Spent in the base of Keycloak, not in its memory alone: neither a restart nor a password
    # set another way makes the link valid again.
    made = link_of(backchannel, local_account.id, service_token)
    assert made.status_code == 200, made.text
    url = made.json()["url"]
    browser = Browser()
    form = browser.get(confirmation_target(browser.get(url)))
    assert 'name="password-new"' in form.text
    assert Browser().get(url).status_code == 400
    done = browser.submit(form, {"password-new": PASSWORD, "password-confirm": PASSWORD})
    assert done.status_code == 200, done.text
    assert password_grant(keycloak, local_account, PASSWORD).status_code == 200


def test_a_link_outlives_an_update_of_its_account(
    backchannel: httpx2.Client, admin: httpx2.Client, service_token: str, local_account: Account
) -> None:
    # The nonce of the link is an attribute the user profile of the realm does not declare: an
    # update through the administration API, which the service makes, must leave it in place.
    made = link_of(backchannel, local_account.id, service_token)
    assert made.status_code == 200, made.text
    account = admin.get(f"/users/{local_account.id}").json()
    updated = admin.put(f"/users/{local_account.id}", json={**account, "firstName": "Jeanne-Marie"})
    assert updated.status_code == 204, updated.text
    assert Browser().get(made.json()["url"]).status_code == 200


def test_an_account_the_realm_does_not_hold_has_no_link(
    backchannel: httpx2.Client, service_token: str
) -> None:
    response = link_of(backchannel, str(uuid4()), service_token)
    assert (response.status_code, response.json()) == (404, {"error": "unknown_user"})


def test_a_service_account_has_no_link(backchannel: httpx2.Client, service_token: str) -> None:
    # The account the token of the service account names: it holds the role of the extension.
    response = link_of(backchannel, claims(service_token)["sub"], service_token)
    assert (response.status_code, response.json()) == (409, {"error": "not_local"})


def test_an_account_of_the_directory_has_no_link(
    backchannel: httpx2.Client, admin: httpx2.Client, service_token: str
) -> None:
    # Searching the realm reads the person from the federated directory.
    found = admin.get("/users", params={"email": DIRECTORY_EMAIL, "exact": "true"}).json()
    assert [user["email"] for user in found] == [DIRECTORY_EMAIL]
    response = link_of(backchannel, found[0]["id"], service_token)
    assert (response.status_code, response.json()) == (409, {"error": "not_local"})


def test_an_account_relayed_by_an_external_provider_has_no_link(
    backchannel: httpx2.Client, admin: httpx2.Client, service_token: str, local_account: Account
) -> None:
    # The link a first sign-in through the provider of the development platform leaves.
    relayed = admin.post(
        f"/users/{local_account.id}/federated-identity/{EXTERNAL_PROVIDER}",
        json={
            "identityProvider": EXTERNAL_PROVIDER,
            "userId": str(uuid4()),
            "userName": local_account.email,
        },
    )
    assert relayed.status_code == 204, relayed.text
    response = link_of(backchannel, local_account.id, service_token)
    assert (response.status_code, response.json()) == (409, {"error": "not_local"})


def test_an_invitation_mails_a_link_of_the_extension_that_a_later_link_replaces(
    keycloak: httpx2.Client, backchannel: httpx2.Client, service_token: str, local_account: Account
) -> None:
    # The link of the mail is the extension's, under its nonce: the link obtained afterwards for
    # the same account invalidates it (#651).
    sent = invite(backchannel, local_account.id, service_token)
    assert (sent.status_code, sent.content) == (204, b"")
    url = mailed_link(local_account.email)
    assert url.startswith(f"{str(keycloak.base_url).rstrip('/')}/login-actions/action-token?key=")
    assert action_token(url)["typ"] == EXTENSION_ACTION
    later = link_of(backchannel, local_account.id, service_token)
    assert later.status_code == 200, later.text
    replaced = Browser().get(url)
    assert replaced.status_code == 400
    assert REPLACED in html.unescape(replaced.text)


def test_an_invitation_is_refused_as_a_link_is(
    backchannel: httpx2.Client, service_token: str, local_account: Account
) -> None:
    for token in (None, "not-a-token"):
        response = invite(backchannel, local_account.id, token)
        assert (response.status_code, response.json()) == (401, {"error": "not_authenticated"})
    unknown = invite(backchannel, str(uuid4()), service_token)
    assert (unknown.status_code, unknown.json()) == (404, {"error": "unknown_user"})
    service = invite(backchannel, claims(service_token)["sub"], service_token)
    assert (service.status_code, service.json()) == (409, {"error": "not_local"})


def test_a_realm_without_a_mail_server_or_whose_server_fails_sends_no_invitation(
    backchannel: httpx2.Client, service_token: str, local_account: Account
) -> None:
    made = link_of(backchannel, local_account.id, service_token)
    assert made.status_code == 200, made.text
    # An installation without a mail server gives the link by hand (WF-CMP-0030).
    with mail_server({}):
        none = invite(backchannel, local_account.id, service_token)
    assert (none.status_code, none.json()) == (409, {"error": "no_mail_server"})
    with mail_server(UNREACHABLE_MAIL_SERVER):
        failing = invite(backchannel, local_account.id, service_token)
    assert (failing.status_code, failing.json()) == (502, {"error": "not_sent"})
    # The invitation that did not leave replaced nothing: the link obtained before still serves.
    kept = Browser().get(made.json()["url"])
    assert kept.status_code == 200, kept.text
