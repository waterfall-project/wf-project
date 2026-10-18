# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The language a person chooses, also hers in the identity provider, on the platform (US-0400).

The provider mails in the language of the account (WF-INTF-0160, WF-ADM-0140): a language chosen
in Waterfall is written in the attribute ``locale`` of the account of the realm, and withdrawn
when the account follows its browser again. Run by ``make test-keycloak``, with the variables of
``test_keycloak_authentication.py``, whose helpers it takes; the API is served in the process of
the tests, on a database of their own.
"""

from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from support import ContractClient, Watching, nowhere
from test_keycloak_authentication import (
    DIRECTORY_CREDENTIAL,
    EXTERNAL_CREDENTIAL,
    EXTERNAL_USERNAME,
    bearer,
    known,
    served_settings,
    service_admin,
    tokens_of,
    with_password,
)
from test_keycloak_platform import (
    DIRECTORY_EMAIL,
    EXTERNAL_PROVIDER,
    PASSWORD,
    Account,
    Browser,
    ask_forgotten,
    claims,
    mailed,
)
from test_keycloak_sign_in import locked_out

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.database import Database
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin

pytestmark = pytest.mark.keycloak

PREFERENCES = "/api/v1/me/preferences"
# The subject of the mail that resets a password, in each language of the email theme.
RESET_SUBJECTS = {
    "fr": "Réinitialiser votre mot de passe Waterfall",
    "en": "Reset your Waterfall password",
}
# An identifier the realm gives to no account.
NOBODY = "00000000-0000-4000-8000-000000000000"
# What may go in the write of a language: the identity the realm requires with the attributes.
SENT_WITH_A_LANGUAGE = {"username", "email", "firstName", "lastName", "attributes"}


@pytest.fixture
def keycloak() -> Iterator[Keycloak]:
    """Give the client of the realm the API reaches."""
    client = Keycloak(served_settings())
    yield client
    client.close()


@pytest.fixture
def watching(keycloak: Keycloak, database: Database) -> Watching:
    """Give the client of the administration API, noting the connections held at each call."""
    return Watching(keycloak, served_settings(), database)


@pytest.fixture
def api(
    contract: OpenAPI, database: Database, keycloak: Keycloak, watching: Watching
) -> ContractClient:
    """Give a client of the API on the database of the test and the Keycloak of the platform."""
    app = create_app(Services(database, keycloak, watching, *nowhere()))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def admin() -> Iterator[httpx2.Client]:
    """Reach the administration API of the realm as the service account, as the API does."""
    with service_admin(served_settings()) as client:
        yield client


@pytest.fixture
def local_account(admin: httpx2.Client) -> Iterator[Account]:
    """Make a local account of the realm with a password, and remove it after."""
    made = with_password(admin, "Claude", "Langue")
    yield made
    admin.delete(f"/users/{made.id}")


def held(admin: httpx2.Client, subject: str) -> dict[str, Any]:
    """Read an account of the realm."""
    response = admin.get(f"/users/{subject}")
    assert response.status_code == 200, response.text
    return response.json()


def locale_of(admin: httpx2.Client, subject: str) -> list[str] | None:
    """Read the language an account of the realm holds, ``None`` if it holds none."""
    attributes: dict[str, list[str]] = held(admin, subject).get("attributes") or {}
    return attributes.get("locale")


def test_the_language_chosen_is_the_account_s_in_the_identity_provider(
    api: ContractClient,
    database: Database,
    admin: httpx2.Client,
    local_account: Account,
    watching: Watching,
) -> None:
    # The provider sends the mails of the account in the language it holds: chosen in Waterfall,
    # it is written there; followed from the browser again, withdrawn. The rest of the account is
    # kept as it was.
    known(database, local_account)
    before = held(admin, local_account.id)
    headers = bearer(tokens_of(local_account.email, PASSWORD))
    response = api.patch(PREFERENCES, headers=headers, json={"language": "en"})
    assert response.status_code == 200, response.text
    assert response.json() == {"language": "en"}
    after = held(admin, local_account.id)
    assert after["attributes"]["locale"] == ["en"]
    kept = ("username", "email", "firstName", "lastName", "enabled", "emailVerified")
    assert {name: after.get(name) for name in kept} == {name: before.get(name) for name in kept}
    assert api.patch(PREFERENCES, headers=headers, json={"language": "fr"}).status_code == 200
    assert locale_of(admin, local_account.id) == ["fr"]
    assert api.patch(PREFERENCES, headers=headers, json={"language": "default"}).status_code == 200
    assert locale_of(admin, local_account.id) is None
    # Asked outside of any transaction (#669); a grid changed does not ask it.
    assert (
        api.patch(PREFERENCES, headers=headers, json={"grids": {"users": None}}).status_code == 200
    )
    assert watching.held == [("set_locale", 0)] * 3


def test_the_language_shown_chosen_again_repairs_a_language_the_provider_holds_otherwise(
    api: ContractClient, database: Database, admin: httpx2.Client, local_account: Account
) -> None:
    # The provider's language may part from Waterfall's — another tab, or the language picker of
    # the realm's sign-in page, which writes ``locale`` too: choosing again the language Waterfall
    # shows gives it back to the provider.
    known(database, local_account)
    headers = bearer(tokens_of(local_account.email, PASSWORD))
    assert api.patch(PREFERENCES, headers=headers, json={"language": "en"}).status_code == 200
    account = held(admin, local_account.id)
    account["attributes"] = {**(account.get("attributes") or {}), "locale": ["fr"]}
    written = admin.put(f"/users/{local_account.id}", json=account)
    assert written.status_code == 204, written.text
    assert locale_of(admin, local_account.id) == ["fr"]
    response = api.patch(PREFERENCES, headers=headers, json={"language": "en"})
    assert response.status_code == 200, response.text
    assert response.json() == {"language": "en"}
    assert locale_of(admin, local_account.id) == ["en"]


def test_the_language_chosen_by_a_person_relayed_by_an_external_provider_is_hers_in_the_realm(
    api: ContractClient, keycloak: Keycloak, admin: httpx2.Client
) -> None:
    tokens = tokens_of(EXTERNAL_USERNAME, EXTERNAL_CREDENTIAL, provider=EXTERNAL_PROVIDER)
    subject = claims(tokens["access_token"])["sub"]
    try:
        response = api.patch(PREFERENCES, headers=bearer(tokens), json={"language": "en"})
        assert response.status_code == 200, response.text
        assert locale_of(admin, subject) == ["en"]
    finally:
        KeycloakAdmin(keycloak, served_settings()).set_locale(subject, None)
    assert locale_of(admin, subject) is None


def test_the_language_of_a_person_of_the_directory_stays_in_waterfall(
    api: ContractClient, admin: httpx2.Client, watching: Watching
) -> None:
    # The directory is federated read only: the realm refuses to write any attribute of hers
    # ("Federated storage is not writable"), and mails her nothing; it is not asked.
    tokens = tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL)
    response = api.patch(PREFERENCES, headers=bearer(tokens), json={"language": "en"})
    assert response.status_code == 200, response.text
    assert response.json() == {"language": "en"}
    assert locale_of(admin, claims(tokens["access_token"])["sub"]) is None
    assert [call for call, _ in watching.held] == ["read_account"]


class Meanwhile(KeycloakAdmin):
    """An administration client before whose write of a language the account is otherwise changed.

    Between the read and the write of ``set_locale``, the account is verified, disabled and asked
    an action, as the extension or the console may do; the body of the write is noted.
    """

    def __init__(self, keycloak: Keycloak, admin: httpx2.Client) -> None:
        """Change the account through ``admin``; nothing is written yet."""
        super().__init__(keycloak, served_settings())
        self.admin = admin
        self.sent: list[dict[str, Any]] = []

    def _as_service(self, method: str, path: str, **options: Any) -> httpx2.Response:
        if method == "PUT":
            subject = path.rsplit("/", 1)[-1]
            meanwhile = {
                "emailVerified": True,
                "enabled": False,
                "requiredActions": ["CONFIGURE_TOTP"],
            }
            changed = self.admin.put(f"/users/{subject}", json=meanwhile)
            assert changed.status_code == 204, changed.text
            self.sent.append(options["json"])
        return super()._as_service(method, path, **options)


def test_a_language_set_keeps_what_the_account_was_given_meanwhile(
    keycloak: Keycloak, admin: httpx2.Client, local_account: Account
) -> None:
    # Only the identity and the attributes go back: an address verified by the extension, an
    # account disabled or asked an action from the console while the language is written are
    # not undone by what was read before.
    meanwhile = Meanwhile(keycloak, admin)
    meanwhile.set_locale(local_account.id, "en")
    assert [set(sent) for sent in meanwhile.sent] == [SENT_WITH_A_LANGUAGE]
    after = held(admin, local_account.id)
    assert after["attributes"]["locale"] == ["en"]
    kept = (after["emailVerified"], after["enabled"], after["requiredActions"])
    assert kept == (True, False, ["CONFIGURE_TOTP"])


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_language_set_leaves_a_locked_account_locked(
    keycloak: Keycloak, admin: httpx2.Client, local_account: Account
) -> None:
    # « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes » — not as
    # soon as its holder, signed in on another device, changes their language: Keycloak clears
    # the failures of a locked account written ``enabled: true``, and the write names none.
    locked_out(admin, local_account)
    KeycloakAdmin(keycloak, served_settings()).set_locale(local_account.id, "en")
    assert locale_of(admin, local_account.id) == ["en"]
    state = admin.get(f"/attack-detection/brute-force/users/{local_account.id}").json()
    assert (state["disabled"], state["numFailures"]) == (True, 10)


def test_an_account_the_realm_does_not_hold_has_no_language_to_set(
    keycloak: Keycloak, admin: httpx2.Client
) -> None:
    # Nothing to set, and nothing created to set it on.
    KeycloakAdmin(keycloak, served_settings()).set_locale(NOBODY, "en")
    assert admin.get(f"/users/{NOBODY}").status_code == 404


@pytest.mark.requirement("WF-ARC-0110-A")
@pytest.mark.parametrize(("language", "other"), [("en", "fr"), ("fr", "en")])
def test_a_mail_to_reset_a_password_leaves_the_provider_in_the_language_of_the_account(
    api: ContractClient,
    database: Database,
    local_account: Account,
    language: str,
    other: str,
) -> None:
    # « Un courriel de réinitialisation part du fournisseur d'identité, dans la langue du compte » :
    # the language chosen in Waterfall, whatever the browser that asks for the mail has chosen on
    # the sign-in page of the realm.
    known(database, local_account)
    headers = bearer(tokens_of(local_account.email, PASSWORD))
    assert api.patch(PREFERENCES, headers=headers, json={"language": language}).status_code == 200
    browser = Browser()
    browser.cookies["KEYCLOAK_LOCALE"] = other
    ask_forgotten(browser, local_account)
    mail = mailed(local_account.email)
    assert mail["Subject"] == RESET_SUBJECTS[language]
    assert mail["Subject"] != RESET_SUBJECTS[other]
