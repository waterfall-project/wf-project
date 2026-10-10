# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API knows its caller by the access token alone, and reads the rest in its base.

The tokens are signed by keys the test makes and serves as Keycloak serves its own
(``realm.py``): the validation tried is that of the service. A person unknown to Waterfall and
the closing of sessions need Keycloak itself: ``test_keycloak_authentication.py``.
"""

import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import TestRealm, new_key
from sqlalchemy import insert
from support import ContractClient, Logs, raw_account

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database
from waterfall.platform.errors import UnauthenticatedError
from waterfall.platform.keycloak import (
    KEYS_REREAD_SECONDS,
    IdentityProviderError,
    Keycloak,
)
from waterfall.platform.settings import ServiceSettings

ME = "/api/v1/me"
SESSIONS = "/api/v1/me/sessions"
KEY = "key-1"
SUBJECT = "4b1f0c1e-9a51-4c47-8d0e-2f6a1c3e5b70"


@pytest.fixture
def realm() -> Iterator[TestRealm]:
    """Serve one key of the realm of test, then stop."""
    served = TestRealm()
    served.add_key(KEY)
    yield served
    served.stop()


@pytest.fixture
def realm_settings(platform_settings: ServiceSettings, realm: TestRealm) -> ServiceSettings:
    """Give the settings of the API, Keycloak being the realm of test."""
    return platform_settings.model_copy(update={"keycloak_address": realm.address})


@pytest.fixture
def keycloak(realm_settings: ServiceSettings) -> Iterator[Keycloak]:
    """Give the client of the realm of test."""
    client = Keycloak(realm_settings)
    yield client
    client.close()


@pytest.fixture
def api(contract: OpenAPI, database: Database, keycloak: Keycloak) -> ContractClient:
    """Give a client of the application on the database of test and the realm of test."""
    app = create_app(Services(database, keycloak))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


def account(database: Database, **overrides: object) -> dict[str, Any]:
    """Write an account whose subject is ``SUBJECT``, with the changes a test asks for."""
    row = raw_account(idp_subject=SUBJECT, **overrides)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    return row


def bearer(token: str) -> dict[str, str]:
    """Give the header that carries an access token."""
    return {"Authorization": f"Bearer {token}"}


def refusal(response: Any) -> tuple[int, str]:
    """Give the status and the code of a refusal."""
    return response.status_code, response.json()["code"]


def test_the_account_of_the_subject_of_the_token_is_the_caller(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    row = account(database, display_preferences={"theme": "dark"})
    response = api.get(ME, headers=bearer(realm.token(SUBJECT, KEY)))
    assert response.status_code == 200
    me = response.json()
    assert (me["user_id"], me["email"], me["origin"]) == (str(row["id"]), row["email"], "local")
    assert (me["is_active"], me["lock_version"], me["has_avatar"]) == (True, 0, False)
    # A preference never chosen is absent, not null.
    assert me["display_preferences"] == {"theme": "dark"}
    assert me["audit"]["created_by"] == {"kind": "platform"}
    assert (me["org_node_id"], me["org_node_label"]) == (None, None)


def test_an_account_without_any_role_has_no_permission(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    account(database, origin="identity_provider")
    me = api.get(ME, headers=bearer(realm.token(SUBJECT, KEY))).json()
    assert (me["access_role_ids"], me["access_role_labels"], me["permissions"]) == ([], [], [])


def test_the_author_of_an_account_is_named_as_it_is_shown(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    author = raw_account(first_name="Inès", last_name="Roux", email="ines.roux@example.org")
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**author))
    account(database, updated_by=author["id"], updated_at=datetime(2026, 10, 2, tzinfo=UTC))
    me = api.get(ME, headers=bearer(realm.token(SUBJECT, KEY))).json()
    assert me["audit"]["updated_by"] == {
        "kind": "user",
        "user_id": str(author["id"]),
        "display_name": "Inès Roux",
    }
    assert me["audit"]["updated_at"] == "2026-10-02T00:00:00Z"


def test_the_caller_is_the_author_of_the_records_of_its_request(
    api: ContractClient, database: Database, realm: TestRealm, logs: Logs
) -> None:
    row = account(database)
    api.get(ME, headers=bearer(realm.token(SUBJECT, KEY)))
    (record,) = logs.named("request.completed")
    assert (record["actor"], record["status"]) == (str(row["id"]), 200)


def test_a_deactivated_account_is_refused_whatever_its_token(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    account(database, state="deactivated")
    response = api.get(ME, headers=bearer(realm.token(SUBJECT, KEY)))
    assert refusal(response) == (401, "ACCOUNT_DEACTIVATED")


@pytest.mark.requirement("WF-ARC-0030-A")
def test_an_expired_access_token_is_refused(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    account(database)
    response = api.get(ME, headers=bearer(realm.token(SUBJECT, KEY, lifetime=-1)))
    assert refusal(response) == (401, "SESSION_EXPIRED")


@pytest.mark.requirement("WF-ARC-0030-A")
def test_an_access_token_signed_by_another_key_is_refused(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    account(database)
    # The identifier of a key of the realm, the signature of another key.
    forged = realm.token(SUBJECT, KEY, key=new_key())
    assert refusal(api.get(ME, headers=bearer(forged))) == (401, "SESSION_REQUIRED")
    # Expired as well, it is still refused for its signature, not for its expiry.
    expired = realm.token(SUBJECT, KEY, key=new_key(), lifetime=-1)
    assert refusal(api.get(ME, headers=bearer(expired))) == (401, "SESSION_REQUIRED")


@pytest.mark.requirement("WF-ARC-0030-A")
@pytest.mark.usefixtures("realm")
def test_an_access_token_signed_by_a_key_the_realm_does_not_have_is_refused(
    api: ContractClient, database: Database
) -> None:
    account(database)
    unknown = TestRealm()
    try:
        unknown.add_key("key-of-another-realm")
        token = unknown.token(SUBJECT, "key-of-another-realm")
    finally:
        unknown.stop()
    assert refusal(api.get(ME, headers=bearer(token))) == (401, "SESSION_REQUIRED")


def test_a_key_the_realm_adds_is_read_when_a_token_first_names_it(
    realm_settings: ServiceSettings, realm: TestRealm
) -> None:
    now = [1000.0]
    keycloak = Keycloak(realm_settings, clock=lambda: now[0])
    assert keycloak.subject_of(realm.token(SUBJECT, KEY)) == SUBJECT
    # The realm rotates its keys: the new one is read at the first token it signs.
    realm.add_key("key-2")
    now[0] += KEYS_REREAD_SECONDS
    assert keycloak.subject_of(realm.token(SUBJECT, "key-2")) == SUBJECT
    assert keycloak.subject_of(realm.token(SUBJECT, KEY)) == SUBJECT
    assert realm.reads == 2
    keycloak.close()


@pytest.mark.parametrize(
    "claims",
    [
        # A token the realm lends to another client, its command line for one (#644).
        {"aud": "account"},
        {"iss": "http://127.0.0.1:9/auth/realms/waterfall"},
        {"sub": ""},
    ],
    ids=["another audience", "another issuer", "no subject"],
)
def test_a_token_that_is_not_for_the_api_of_this_realm_is_refused(
    claims: dict[str, str], api: ContractClient, database: Database, realm: TestRealm
) -> None:
    account(database)
    token = realm.token(SUBJECT, KEY, claims=claims)
    assert refusal(api.get(ME, headers=bearer(token))) == (401, "SESSION_REQUIRED")


def test_a_token_issued_by_a_clock_a_little_ahead_is_taken(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    account(database)
    ahead = realm.token(SUBJECT, KEY, claims={"iat": int(time.time()) + 60})
    assert api.get(ME, headers=bearer(ahead)).status_code == 200


@pytest.mark.parametrize(
    "header",
    [None, "Basic dXNlcjpwYXNz", "Bearer", "Bearer not-a-token", "Bearer e30.e30.e30"],
)
def test_a_request_without_a_readable_access_token_is_refused(
    header: str | None, api: ContractClient
) -> None:
    headers = {} if header is None else {"Authorization": header}
    response = api.get(ME, headers=headers)
    assert refusal(response) == (401, "SESSION_REQUIRED")
    response = api.delete(SESSIONS, headers=headers)
    assert refusal(response) == (401, "SESSION_REQUIRED")


def test_closing_the_sessions_while_keycloak_does_not_answer_is_a_component_unavailable(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    account(database)
    token = realm.token(SUBJECT, KEY)
    assert api.get(ME, headers=bearer(token)).status_code == 200
    realm.stop()
    response = api.delete(SESSIONS, headers=bearer(token))
    assert refusal(response) == (503, "COMPONENT_UNAVAILABLE")
    assert response.json()["params"] == {"component": "identity_provider"}


def test_a_key_unknown_to_the_realm_is_not_read_again_more_than_once_in_a_while(
    realm_settings: ServiceSettings, realm: TestRealm
) -> None:
    now = [1000.0]
    keycloak = Keycloak(realm_settings, clock=lambda: now[0])
    stranger = realm.token(SUBJECT, "no-such-key", key=new_key())
    for _ in range(3):
        with pytest.raises(UnauthenticatedError):
            keycloak.subject_of(stranger)
    assert realm.reads == 1
    now[0] += KEYS_REREAD_SECONDS
    with pytest.raises(UnauthenticatedError):
        keycloak.subject_of(stranger)
    assert realm.reads == 2
    assert keycloak.subject_of(realm.token(SUBJECT, KEY)) == SUBJECT
    assert realm.reads == 2
    keycloak.close()


def test_keys_the_realm_cannot_sign_with_are_a_defect_of_the_platform(
    realm_settings: ServiceSettings,
) -> None:
    # A realm that serves its key for encryption alone.
    empty = TestRealm()
    keycloak = Keycloak(realm_settings.model_copy(update={"keycloak_address": empty.address}))
    try:
        with pytest.raises(IdentityProviderError, match="not usable"):
            keycloak.subject_of(empty.token(SUBJECT, KEY, key=new_key()))
    finally:
        keycloak.close()
        empty.stop()


def test_an_answer_keycloak_does_not_give_is_a_defect_of_the_platform(
    keycloak: Keycloak,
) -> None:
    # The realm of test answers nothing but its keys: the service account gets no token.
    with pytest.raises(IdentityProviderError, match="answered 404"):
        keycloak.close_sessions(SUBJECT)
