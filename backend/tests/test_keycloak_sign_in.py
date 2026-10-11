# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Signing in by the identity provider, on the platform: what US-0350 asks of it (US-0350/L5).

Each kind of account — local, of the directory, of an external provider — signs in through the
page of the realm, as the front signs a person in, and acts in Waterfall according to its roles
(WF-ARC-0030, WF-ADM-0180); the password of a local account follows the rules of WF-ADM-0140; a
session left idle ends (WF-SEC-0020). Run by ``make test-keycloak``, with the variables of
``test_keycloak_authentication.py``, whose helpers it takes; the API is served in the process of
the tests, on a database of their own. A test that changes a setting of the realm gives it back
its value, whatever happens. What the browser shows of it — the screens, the return to the screen
aimed at — is proved by the paths against the service (``frontend/e2e/service/``).
"""

import html
import secrets
import time
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from access_rows import role
from openapi_core import OpenAPI
from sqlalchemy import select
from support import ContractClient, Logs
from test_keycloak_authentication import (
    DIRECTORY_CREDENTIAL,
    EXTERNAL_CREDENTIAL,
    EXTERNAL_USERNAME,
    ME,
    NOBODY,
    USERS,
    bearer,
    callback,
    changing_accounts,
    collected,
    created,
    jeanne,
    known,
    new_address,
    realm_address,
    refreshed,
    refused_sign_in,
    served_api,
    served_settings,
    service_admin,
    tokens_of,
    with_password,
)
from test_keycloak_platform import (
    DIRECTORY_EMAIL,
    EXPIRED,
    EXTERNAL_PROVIDER,
    PASSWORD,
    REPLACED,
    SPENT,
    Account,
    Browser,
    action_token,
    administering,
    ask_forgotten,
    claims,
    mailed_link,
    password_grant,
    relay,
    set_by_link,
)

from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database
from waterfall.platform.keycloak import IdentityProviderError, Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin

pytestmark = pytest.mark.keycloak

# The roles of WF-ARC-0030: one that lets its holder consult the accounts, one that does not.
CONSULTING = "users.read"
PLANNING = "planning.read"


@pytest.fixture
def keycloak() -> Iterator[Keycloak]:
    """Give the client of the realm the API reaches."""
    client = Keycloak(served_settings())
    yield client
    client.close()


@pytest.fixture
def api(contract: OpenAPI, database: Database, keycloak: Keycloak) -> ContractClient:
    """Give a client of the API on the database of the test and the Keycloak of the platform."""
    return served_api(contract, database, keycloak)


@pytest.fixture
def admin() -> Iterator[httpx2.Client]:
    """Reach the administration API of the realm as the service account, as the API does."""
    with service_admin(served_settings()) as client:
        yield client


@pytest.fixture
def local_account(admin: httpx2.Client) -> Iterator[Account]:
    """Make a local account of the realm with a password, and remove it after."""
    made = with_password(admin, "Claude", "Locale")
    yield made
    admin.delete(f"/users/{made.id}")


@pytest.fixture
def administrator(database: Database, local_account: Account) -> dict[str, str]:
    """Make the caller an account Waterfall knows, which may change the accounts; give its token."""
    return changing_accounts(database, local_account)


@pytest.fixture
def in_realm(admin: httpx2.Client, database: Database) -> Iterator[list[str]]:
    """Collect the accounts a test creates in the realm, and remove them after."""
    with collected(admin, database) as subjects:
        yield subjects


@contextmanager
def realm_set(**settings: object) -> Generator[httpx2.Client]:
    """Give the realm ``settings`` for a while, then the values it had; give its administration."""
    with administering() as realm:
        kept = {name: realm.get("").json()[name] for name in settings}
        changed = realm.put("", json=settings)
        assert changed.status_code == 204, changed.text
        try:
            yield realm
        finally:
            restored = realm.put("", json=kept)
            assert restored.status_code == 204, restored.text


def link_path(user_id: str) -> str:
    """Give the path where the API makes the password link of an account."""
    return f"{USERS}/{user_id}/password-link"


def created_by_administrator(api: ContractClient, administrator: dict[str, str]) -> str:
    """Create Jeanne Montgolfier's local account through the API; give its identifier."""
    response = api.post(USERS, headers=administrator, json=jeanne(new_address()))
    assert response.status_code == 201, response.text
    return str(response.json()["user_id"])


# --- WF-ADM-0140: the password of a local account -----------------------------------------------


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_password_of_eleven_characters_or_the_address_of_the_account_is_refused(
    admin: httpx2.Client, local_account: Account
) -> None:
    # « Un mot de passe de onze caractères est refusé, de même que l'adresse du compte. »
    def reset(password: str) -> httpx2.Response:
        return admin.put(
            f"/users/{local_account.id}/reset-password",
            json={"type": "password", "value": password, "temporary": False},
        )

    eleven, address = reset("k7#Qw2ZpX9v"), reset(local_account.email)
    assert (eleven.status_code, eleven.json()["error"]) == (400, "invalidPasswordMinLengthMessage")
    # The address is the username too: the rule of either may say it first.
    assert address.status_code == 400, address.text
    assert address.json()["error"] in {
        "invalidPasswordNotEmailMessage",
        "invalidPasswordNotUsernameMessage",
    }
    assert reset("k7#Qw2ZpX9vR").status_code == 204


def locked_out(account: Account) -> None:
    """Fail ten sign-ins of an account, then find that its own password no longer signs it in."""
    with httpx2.Client(base_url=realm_address(), timeout=30) as realm:
        for _ in range(10):
            failed = password_grant(realm, account, "not-the-password")
            assert (failed.status_code, failed.json()["error"]) == (401, "invalid_grant")
        locked = password_grant(realm, account, PASSWORD)
        assert locked.status_code != 200, locked.text


@pytest.mark.requirement("WF-ADM-0140-A")
def test_ten_failures_lock_the_account_for_fifteen_minutes(
    admin: httpx2.Client, local_account: Account
) -> None:
    # « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes. » Locked, the
    # account refuses even its password; the realm locks it for fifteen minutes whatever the count
    # of failures, never for good — the settings of the lock, and its state. That a lock ends
    # when its time is out is proved on a lock made short, below.
    locked_out(local_account)
    state = admin.get(f"/attack-detection/brute-force/users/{local_account.id}").json()
    assert (state["disabled"], state["numFailures"]) == (True, 10)
    with administering() as realm_admin:
        realm = realm_admin.get("").json()
    lock = {
        key: realm[key]
        for key in (
            "bruteForceProtected",
            "permanentLockout",
            "failureFactor",
            "bruteForceStrategy",
            "waitIncrementSeconds",
            "maxFailureWaitSeconds",
        )
    }
    assert lock == {
        "bruteForceProtected": True,
        "permanentLockout": False,
        "failureFactor": 10,
        # A lock of waitIncrementSeconds per ten failures, capped at maxFailureWaitSeconds.
        "bruteForceStrategy": "MULTIPLE",
        "waitIncrementSeconds": 900,
        "maxFailureWaitSeconds": 900,
    }


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_locked_account_signs_in_again_once_its_lock_is_over(local_account: Account) -> None:
    # « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes » : the
    # fifteen minutes are two seconds here; once they are over, the password signs in again.
    with realm_set(waitIncrementSeconds=2, maxFailureWaitSeconds=2):
        locked_out(local_account)
        time.sleep(3)
        with httpx2.Client(base_url=realm_address(), timeout=30) as realm:
            unlocked = password_grant(realm, local_account, PASSWORD)
    assert unlocked.status_code == 200, unlocked.text


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_link_used_once_or_after_its_hour_is_refused(
    api: ContractClient, administrator: dict[str, str], in_realm: list[str]
) -> None:
    # « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé. » The hour
    # is the lifespan of the links the realm makes for an administrator: a second here.
    del in_realm
    user_id = created_by_administrator(api, administrator)
    with realm_set(actionTokenGeneratedByAdminLifespan=1):
        made = api.post(link_path(user_id), headers=administrator)
    assert made.status_code == 201, made.text
    time.sleep(2.1)
    expired = Browser().get(made.json()["url"])
    assert expired.status_code == 400, expired.text
    said = html.unescape(expired.text)
    assert EXPIRED in said
    assert SPENT not in said
    assert REPLACED not in said
    link = api.post(link_path(user_id), headers=administrator).json()
    # A link lives the hour of the realm, which the token it carries says.
    lifespan = claims(link["url"].split("key=", 1)[1].split("&", 1)[0])
    assert lifespan["exp"] - lifespan["iat"] == 3600
    _, done = set_by_link(link["url"], PASSWORD)
    assert done.status_code == 200, done.text
    used = Browser().get(link["url"])
    assert (used.status_code, SPENT in html.unescape(used.text)) == (400, True)


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_link_for_a_forgotten_password_used_once_is_refused(local_account: Account) -> None:
    # « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé » : the link
    # the page of a forgotten password mails, Keycloak's own, lives the hour of the realm, which
    # the token it carries says, and sets a password once.
    browser = Browser()
    ask_forgotten(browser, local_account)
    url = mailed_link(local_account.email, whole=True)
    lifespan = action_token(url)
    assert lifespan["exp"] - lifespan["iat"] == 3600
    form = browser.get(url)
    assert 'name="password-new"' in form.text, form.text
    password = secrets.token_urlsafe(24)
    done = browser.submit(form, {"password-new": password, "password-confirm": password})
    assert done.status_code == 302, done.text
    assert done.headers["Location"].startswith(f"{callback()}?"), done.headers["Location"]
    tokens_of(local_account.email, password)
    used = Browser().get(url)
    assert used.status_code == 400, used.text
    said = html.unescape(used.text)
    assert EXPIRED in said
    assert 'name="password-new"' not in said


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_link_for_a_forgotten_password_after_its_hour_is_refused(local_account: Account) -> None:
    # « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé. » The hour
    # is the lifespan of the links the realm mails a person who asks for one: a second here.
    browser = Browser()
    with realm_set(actionTokenGeneratedByUserLifespan=1):
        asked = time.monotonic()
        ask_forgotten(browser, local_account)
    url = mailed_link(local_account.email, whole=True)
    lifespan = action_token(url)
    assert lifespan["exp"] - lifespan["iat"] == 1
    time.sleep(max(0.0, asked + 2.1 - time.monotonic()))
    expired = Browser().get(url)
    assert expired.status_code == 400, expired.text
    said = html.unescape(expired.text)
    assert EXPIRED in said
    assert 'name="password-new"' not in said


@pytest.mark.requirement("WF-ADM-0140-A")
@pytest.mark.usefixtures("in_realm")
def test_an_account_created_by_an_administrator_signs_in_once_its_password_is_set_by_the_link(
    api: ContractClient,
    database: Database,
    administrator: dict[str, str],
    local_account: Account,
    logs: Logs,
) -> None:
    # « Un compte créé par un administrateur ne peut pas se connecter avant que son porteur n'ait
    # fixé son mot de passe par le lien reçu ou remis. » And the criterion of the link: obtained
    # by an authorized user for a local active account, valid one hour and once, the one before
    # it ceasing to be valid, its request inscribed in the journal without the token.
    user_id = created_by_administrator(api, administrator)
    with database.transaction() as session:
        email = session.get_one(UserAccount, user_id).email.lower()
    refused_sign_in(email, PASSWORD)
    before = time.time()
    first, second = (api.post(link_path(user_id), headers=administrator) for _ in range(2))
    assert (first.status_code, second.status_code) == (201, 201), first.text
    # What the service logged: the browser of the test, which opens the links, logs them too.
    service_log = logs.text
    link = second.json()
    assert link["url"].startswith(f"{realm_address()}/login-actions/action-token?key=")
    expires_at = datetime.fromisoformat(link["expires_at"]).timestamp()
    assert before + 3600 - 5 <= expires_at <= time.time() + 3600 + 5
    replaced = Browser().get(first.json()["url"])
    assert (replaced.status_code, REPLACED in html.unescape(replaced.text)) == (400, True)
    _, done = set_by_link(link["url"], PASSWORD)
    assert done.status_code == 200, done.text
    assert api.get(ME, headers=bearer(tokens_of(email, PASSWORD))).status_code == 200
    with database.transaction() as session:
        caller = session.scalars(
            select(UserAccount.id).where(UserAccount.idp_subject == local_account.id)
        ).one()
        entries = session.scalars(
            select(AuditEntry)
            .where(AuditEntry.action == "password_link_create")
            .order_by(AuditEntry.id)
        ).all()
        kept = [(str(entry.object_id), entry.actor_user_id, entry.params) for entry in entries]
        written = " ".join(repr(vars(entry)) for entry in entries)
    assert kept == [(user_id, caller, {}), (user_id, caller, {})]
    # Neither the journal nor the log of the service holds the token of either link.
    for url in (first.json()["url"], link["url"]):
        token = url.split("key=", 1)[1].split("&", 1)[0]
        assert token not in written
        assert token not in service_log


@pytest.mark.requirement("WF-ADM-0140-A")
def test_an_account_of_the_directory_has_no_link_and_signs_in_with_its_directory_credentials(
    api: ContractClient, administrator: dict[str, str]
) -> None:
    # « Un compte importé n'a pas d'écran de mot de passe et se connecte avec ses identifiants
    # d'annuaire. »
    tokens = tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL)
    me = api.get(ME, headers=bearer(tokens))
    assert (me.status_code, me.json()["origin"]) == (200, "directory")
    refused = api.post(link_path(me.json()["user_id"]), headers=administrator)
    assert (refused.status_code, refused.json()["params"]) == (
        409,
        {"missing_condition": "is_local_account"},
    )


# --- WF-ARC-0030, WF-ADM-0180: each kind of account ---------------------------------------------


def acts(api: ContractClient, tokens: dict[str, Any]) -> tuple[int, int]:
    """Give how the API answers a person reading her account, then the table of the accounts."""
    headers = bearer(tokens)
    return api.get(ME, headers=headers).status_code, api.get(USERS, headers=headers).status_code


@pytest.mark.requirement("WF-ARC-0030-A")
@pytest.mark.requirement("WF-ADM-0180-A")
def test_each_kind_of_account_signs_in_and_acts_according_to_its_roles(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    # « Un compte local, un compte de l'annuaire et un compte venu d'un fournisseur externe
    # obtiennent chacun un jeton, et agissent selon leurs rôles dans Waterfall. » « Après
    # fédération d'un annuaire, un compte de l'annuaire se connecte avec ses identifiants
    # d'annuaire et un compte local avec son mot de passe. » « Avec un fournisseur externe, la
    # première connexion d'une personne inconnue crée son compte, sans rôle, et elle n'a aucun
    # droit tant qu'un rôle ne lui est pas donné. »
    known(database, local_account)
    people = {
        "local": tokens_of(local_account.email, PASSWORD),
        "directory": tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL),
        "identity_provider": tokens_of(
            EXTERNAL_USERNAME, EXTERNAL_CREDENTIAL, provider=EXTERNAL_PROVIDER
        ),
    }
    # Without a role, each reads her own account, and the accounts do not exist for her.
    assert {kind: acts(api, tokens) for kind, tokens in people.items()} == dict.fromkeys(
        people, (200, 404)
    )
    accounts = {kind: created(database, tokens) for kind, tokens in people.items()}
    assert {kind: (each.origin if each else None) for kind, each in accounts.items()} == {
        kind: kind for kind in people
    }
    holders = tuple(each.user_id for each in accounts.values() if each)
    role(database, "Consultation des comptes", permissions=(CONSULTING,), holders=holders)
    # Given a role, each acts as it allows, with the same token.
    assert {kind: acts(api, tokens) for kind, tokens in people.items()} == dict.fromkeys(
        people, (200, 200)
    )


@pytest.fixture
def colleague(admin: httpx2.Client) -> Iterator[Account]:
    """Make a second local account of the realm with a password, and remove it after."""
    made = with_password(admin, "Paul", "Durand")
    yield made
    admin.delete(f"/users/{made.id}")


@pytest.mark.requirement("WF-ARC-0030-A")
def test_a_role_withdrawn_takes_effect_at_the_next_request_with_the_same_token(
    api: ContractClient, database: Database, administrator: dict[str, str], colleague: Account
) -> None:
    # « Le retrait d'un rôle prend effet à la requête suivante, sans attendre l'expiration du
    # jeton. » One role of two withdrawn: what it gave goes, what the other gives stays.
    row = known(database, colleague)
    consulting = role(database, "Consultation", permissions=(CONSULTING,), holders=(row["id"],))
    planning = role(database, "Planification", permissions=(PLANNING,), holders=(row["id"],))
    tokens = tokens_of(colleague.email, PASSWORD)
    assert api.get(USERS, headers=bearer(tokens)).status_code == 200
    body = {"access_role_ids": [str(planning)], "lock_version": 0}
    path = f"{USERS}/{row['id']}/access-roles"
    withdrawn = api.request("PUT", path, headers=administrator, json=body)
    assert withdrawn.status_code == 200, withdrawn.text
    assert api.get(USERS, headers=bearer(tokens)).status_code == 404
    me = api.get(ME, headers=bearer(tokens)).json()
    assert (me["access_role_ids"], me["permissions"]) == ([str(planning)], [PLANNING])
    assert str(consulting) not in me["access_role_ids"]


@contextmanager
def without_directory_nor_provider() -> Generator[None]:
    """Disable the directory and the external provider of the realm, then enable them."""
    with administering() as realm:
        (directory,) = realm.get(
            "/components", params={"type": "org.keycloak.storage.UserStorageProvider"}
        ).json()
        provider = realm.get(f"/identity-provider/instances/{EXTERNAL_PROVIDER}").json()

        def enable(*, enabled: bool) -> None:
            config = {**directory["config"], "enabled": [str(enabled).lower()]}
            done = realm.put(f"/components/{directory['id']}", json={**directory, "config": config})
            assert done.status_code == 204, done.text
            done = realm.put(
                f"/identity-provider/instances/{EXTERNAL_PROVIDER}",
                json={**provider, "enabled": enabled},
            )
            assert done.status_code == 204, done.text

        enable(enabled=False)
        try:
            yield
        finally:
            enable(enabled=True)


@pytest.mark.requirement("WF-ADM-0180-A")
def test_on_an_installation_without_directory_nor_provider_a_local_account_signs_in(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    # « Sur une installation sans annuaire ni fournisseur externe, un compte local se connecte. »
    known(database, local_account)
    with without_directory_nor_provider():
        refused_sign_in(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL)
        tokens = tokens_of(local_account.email, PASSWORD)
    assert api.get(ME, headers=bearer(tokens)).status_code == 200


# --- WF-SEC-0020: a session left idle -----------------------------------------------------------


@pytest.mark.requirement("WF-SEC-0020-A")
def test_a_refresh_token_idle_beyond_its_two_hours_is_refused(local_account: Account) -> None:
    # « Un jeton de rafraîchissement inactif au-delà de deux heures est refusé » : it is lent for
    # the two hours of the session left idle, which a second plays here. The return to the
    # sign-in, then to the screen aimed at, is the front's (frontend/e2e/service/).
    tokens = tokens_of(local_account.email, PASSWORD)
    assert tokens["refresh_expires_in"] == 7200
    with realm_set(ssoSessionIdleTimeout=1):
        idle = tokens_of(local_account.email, PASSWORD)
        assert idle["refresh_expires_in"] == 1
        time.sleep(2.1)
        again = refreshed(idle["refresh_token"])
    assert (again.status_code, again.json()["error"]) == (400, "invalid_grant")


# --- The link, as the service reads the answer of the extension ---------------------------------


@pytest.mark.usefixtures("in_realm")
def test_an_account_the_realm_relays_since_waterfall_created_it_has_no_link(
    api: ContractClient, admin: httpx2.Client, database: Database, administrator: dict[str, str]
) -> None:
    # Local for Waterfall, which created it, but linked since to an external provider in the
    # realm: the extension refuses it, and so does the API, by the condition it lacks.
    user_id = created_by_administrator(api, administrator)
    with database.transaction() as session:
        held = session.get_one(UserAccount, user_id)
        relay(admin, Account(held.idp_subject, held.email.lower()))
    refused = api.post(link_path(user_id), headers=administrator)
    assert (refused.status_code, refused.json()["params"]) == (
        409,
        {"missing_condition": "is_local_account"},
    )


class Answering(Keycloak):
    """The client of the realm behind a proxy that answers the extension ``answer``."""

    def __init__(self, answer: object) -> None:
        """Answer the link with ``answer`` as a body of 200."""
        super().__init__(served_settings())
        self.answer = answer

    def send(self, method: str, path: str, **options: Any) -> httpx2.Response:
        """Answer the making of a link; send any other request."""
        if "/password-setup-link/" in path:
            request = httpx2.Request(method, f"{realm_address()}{path}")
            return httpx2.Response(200, json=self.answer, request=request)
        return super().send(method, path, **options)


@pytest.mark.parametrize(
    "answer",
    [
        {"expires_at": "2026-10-11T12:00:00Z"},
        {"url": "https://example.org/x", "expires_at": "tomorrow"},
        {"url": "https://example.org/x", "expires_at": "2026-10-11T12:00:00"},
        ["not", "an", "object"],
    ],
    ids=["no address", "no moment", "a moment without a zone", "no object"],
)
def test_an_answer_of_the_extension_without_a_link_is_a_defect(answer: object) -> None:
    keycloak = Answering(answer)
    with pytest.raises(IdentityProviderError, match="answered no link"):
        KeycloakAdmin(keycloak, served_settings()).make_password_link(NOBODY)
    keycloak.close()


def test_a_link_read_from_the_extension_never_shows_itself() -> None:
    keycloak = Answering(
        {"url": "https://example.org/x?key=secret", "expires_at": "2026-10-11T12:00:00Z"}
    )
    link = KeycloakAdmin(keycloak, served_settings()).make_password_link(NOBODY)
    keycloak.close()
    assert link is not None
    assert (link.url, link.expires_at) == (
        "https://example.org/x?key=secret",
        datetime(2026, 10, 11, 12, tzinfo=UTC),
    )
    assert "secret" not in repr(link)
