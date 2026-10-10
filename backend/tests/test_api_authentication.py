# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The API knows its caller by the access token alone, and reads the rest in its base.

The tokens are signed by keys the test makes and serves as Keycloak serves its own
(``realm.py``): the validation tried is that of the service. Reading in Keycloak a person
unknown to Waterfall, and closing sessions, need Keycloak itself:
``test_keycloak_authentication.py``; what is done with the person read is tried here.
"""

import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import pytest
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import TestRealm, new_key
from sqlalchemy import insert
from sqlalchemy.orm import Session
from support import ContractClient, Logs, raw_account

from waterfall.api.app import create_app
from waterfall.api.authentication import Services, admit
from waterfall.core.users.interface import NotAdmitted
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database
from waterfall.platform.errors import UnauthenticatedError, UnavailableError
from waterfall.platform.keycloak import (
    KEYS_MAX_AGE_SECONDS,
    KEYS_REREAD_SECONDS,
    IdentityProviderError,
    Keycloak,
)
from waterfall.platform.keycloak_admin import KeycloakAdmin, ProviderAccount
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
def api(
    contract: OpenAPI, database: Database, keycloak: Keycloak, realm_settings: ServiceSettings
) -> ContractClient:
    """Give a client of the application on the database of test and the realm of test."""
    app = create_app(Services(database, keycloak, KeycloakAdmin(keycloak, realm_settings)))
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


@pytest.mark.parametrize("email", ["x@corp.local", "A@Example.ORG"])
def test_the_address_of_the_caller_is_given_as_it_is_held(
    email: str, api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # A special-use domain, capitals in the domain: neither refused nor rewritten.
    account(database, email=email)
    response = api.get(ME, headers=bearer(realm.token(SUBJECT, KEY)))
    assert (response.status_code, response.json()["email"]) == (200, email)


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


def test_reading_the_caller_while_keycloak_does_not_answer_is_a_component_unavailable(
    api: ContractClient, database: Database, realm: TestRealm
) -> None:
    # The keys of the realm not yet read, the first request cannot be told from one without a
    # session: Keycloak is the component that fails, as the contract declares it (#666).
    account(database)
    token = realm.token(SUBJECT, KEY)
    realm.stop()
    response = api.get(ME, headers=bearer(token))
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


def test_a_key_the_realm_removes_stops_serving_once_the_keys_are_old(
    realm_settings: ServiceSettings, realm: TestRealm
) -> None:
    now = [1000.0]
    keycloak = Keycloak(realm_settings, clock=lambda: now[0])
    signed = realm.token(SUBJECT, KEY)
    assert keycloak.subject_of(signed) == SUBJECT
    # The realm signs with a new key, and no longer trusts the old one: the keys are read again
    # within the life of an access token.
    realm.add_key("key-2")
    realm.remove_key(KEY)
    now[0] += KEYS_MAX_AGE_SECONDS
    with pytest.raises(UnauthenticatedError) as refused:
        keycloak.subject_of(signed)
    assert refused.value.code == "SESSION_REQUIRED"
    assert realm.reads == 2
    keycloak.close()


def test_the_keys_already_read_serve_while_keycloak_does_not_answer(
    realm_settings: ServiceSettings, realm: TestRealm, logs: Logs
) -> None:
    now = [1000.0]
    keycloak = Keycloak(realm_settings, clock=lambda: now[0])
    signed = realm.token(SUBJECT, KEY)
    assert keycloak.subject_of(signed) == SUBJECT
    realm.stop()
    now[0] += KEYS_MAX_AGE_SECONDS
    # Not a 503 at every request: the keys of a moment ago, asked for again in a while.
    for _ in range(3):
        assert keycloak.subject_of(signed) == SUBJECT
    assert len(logs.named("identity_provider.unreachable")) == 1
    assert len(logs.named("identity_provider.keys_kept")) == 1
    keycloak.close()


def test_keys_keycloak_fails_to_serve_are_a_component_unavailable(
    keycloak: Keycloak, realm: TestRealm
) -> None:
    realm.status = HTTPStatus.SERVICE_UNAVAILABLE
    with pytest.raises(UnavailableError) as refused:
        keycloak.subject_of(realm.token(SUBJECT, KEY))
    assert (refused.value.code, refused.value.params) == (
        "COMPONENT_UNAVAILABLE",
        {"component": "identity_provider"},
    )


@pytest.mark.parametrize(
    ("status", "failure", "message"),
    [
        (HTTPStatus.SERVICE_UNAVAILABLE, UnavailableError, "COMPONENT_UNAVAILABLE"),
        (HTTPStatus.NOT_FOUND, IdentityProviderError, "certs answered 404"),
    ],
    ids=["unavailable", "not served"],
)
def test_a_failure_to_read_the_keys_is_given_again_until_they_are_read_again(
    status: HTTPStatus,
    failure: type[Exception],
    message: str,
    realm_settings: ServiceSettings,
    realm: TestRealm,
) -> None:
    now = [1000.0]
    keycloak = Keycloak(realm_settings, clock=lambda: now[0])
    signed = realm.token(SUBJECT, KEY)
    realm.status = status
    with pytest.raises(failure, match=message):
        keycloak.subject_of(signed)
    # A second later, the failure of Keycloak again, not a session missing; it is not asked.
    now[0] += 1
    with pytest.raises(failure, match=message):
        keycloak.subject_of(signed)
    assert realm.reads == 1
    # Keycloak back, the token is taken once the keys may be read again.
    realm.status = HTTPStatus.OK
    now[0] += KEYS_REREAD_SECONDS
    assert keycloak.subject_of(signed) == SUBJECT
    assert realm.reads == 2
    keycloak.close()


def test_a_token_whose_key_is_not_held_while_keycloak_fails_is_a_component_unavailable(
    realm_settings: ServiceSettings, realm: TestRealm
) -> None:
    now = [1000.0]
    keycloak = Keycloak(realm_settings, clock=lambda: now[0])
    signed = realm.token(SUBJECT, KEY)
    assert keycloak.subject_of(signed) == SUBJECT
    # The realm adds a key while Keycloak fails: a token it signs is not one without a session.
    rotated = realm.token(SUBJECT, "key-2", key=realm.add_key("key-2"))
    realm.status = HTTPStatus.SERVICE_UNAVAILABLE
    now[0] += KEYS_REREAD_SECONDS
    for _ in range(2):
        with pytest.raises(UnavailableError):
            keycloak.subject_of(rotated)
        now[0] += 1
    assert keycloak.subject_of(signed) == SUBJECT
    assert realm.reads == 2
    realm.status = HTTPStatus.OK
    now[0] += KEYS_REREAD_SECONDS
    assert keycloak.subject_of(rotated) == SUBJECT
    keycloak.close()


def test_a_request_whose_key_is_held_does_not_wait_for_the_keys_being_read(
    realm_settings: ServiceSettings, realm: TestRealm
) -> None:
    # Keycloak answers later than the client waits; the delays are shortened, that between two
    # readings below the time a reading takes.
    later = [0.0]
    keycloak = Keycloak(
        realm_settings, clock=lambda: time.monotonic() + later[0], timeout=0.5, keys_reread=0.4
    )
    signed = realm.token(SUBJECT, KEY)
    assert keycloak.subject_of(signed) == SUBJECT
    realm.delay = 5.0
    later[0] += KEYS_MAX_AGE_SECONDS
    with ThreadPoolExecutor(1) as reader:
        reading = reader.submit(keycloak.subject_of, signed)
        while realm.reads < 2:
            time.sleep(0.01)
        assert keycloak.subject_of(signed) == SUBJECT
        assert not reading.done()
        assert reading.result() == SUBJECT
    # The delay between two readings counts from the end of the one that failed.
    assert keycloak.subject_of(signed) == SUBJECT
    assert realm.reads == 2
    realm.delay = 0.0
    later[0] += 0.4
    assert keycloak.subject_of(signed) == SUBJECT
    assert realm.reads == 3
    keycloak.close()


def test_keys_keycloak_does_not_serve_are_a_defect_of_the_platform(
    keycloak: Keycloak, realm: TestRealm
) -> None:
    # The address of the keys answers, but not with them: the realm is not the one configured.
    realm.status = HTTPStatus.NOT_FOUND
    with pytest.raises(IdentityProviderError, match="certs answered 404"):
        keycloak.subject_of(realm.token(SUBJECT, KEY))


def provider_account(**overrides: Any) -> ProviderAccount:
    """Describe the subject as an account the directory holds, with the changes asked for."""
    fields: dict[str, Any] = {
        "subject": SUBJECT,
        "last_name": "Annuaire",
        "first_name": "Dominique",
        "email": "dominique.annuaire@waterfall.test",
        "is_federated": True,
        "is_relayed": False,
        **overrides,
    }
    return ProviderAccount(**fields)


def test_a_person_the_provider_admits_is_given_an_account(session: Session, logs: Logs) -> None:
    admitted = admit(session, SUBJECT, provider_account())
    assert (admitted.subject, admitted.origin, admitted.email) == (
        SUBJECT,
        "directory",
        "dominique.annuaire@waterfall.test",
    )
    (record,) = logs.named("account.created")
    assert (record["user_id"], record["origin"]) == (str(admitted.user_id), "directory")


@pytest.mark.parametrize(
    ("provider", "reason"),
    [
        (None, NotAdmitted.UNKNOWN_TO_PROVIDER),
        (provider_account(is_federated=False), NotAdmitted.LOCAL_ACCOUNT),
        (provider_account(email=""), NotAdmitted.NO_ADDRESS),
    ],
    ids=["unknown to the provider", "local account", "no address"],
)
def test_a_person_refused_at_her_first_request_is_refused_with_its_cause_in_the_log(
    provider: ProviderAccount | None, reason: NotAdmitted, session: Session, logs: Logs
) -> None:
    with pytest.raises(UnauthenticatedError) as refused:
        admit(session, SUBJECT, provider)
    assert refused.value.code == "ACCOUNT_DEACTIVATED"
    (record,) = logs.named("account.not_admitted")
    assert (record["subject"], record["reason"]) == (SUBJECT, reason.value)
