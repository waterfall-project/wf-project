# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Signing in by the identity provider, on the platform: what US-0350 asks of it (US-0350/L5).

Each kind of account — local, of the directory, of an external provider — signs in through the
page of the realm, as the front signs a person in, and acts in Waterfall according to its roles
(WF-ARC-0030, WF-ADM-0180); the password of a local account follows the rules of WF-ADM-0140; a
session left idle ends, a sign-out ends them all, and a session revoked signs in again by giving
its identifiers (WF-SEC-0020, US-0350/L5c). Run by ``make test-keycloak``, with the variables of
``test_keycloak_authentication.py``, whose helpers it takes; the API is served in the process of
the tests, on a database of their own. A test that changes a setting of the realm gives it back
its value, whatever happens. What the browser shows of it — the screens, the return to the screen
aimed at — is proved by the paths against the service (``frontend/e2e/service/``).
"""

import html
import secrets
import subprocess
import threading
import time
from collections.abc import Generator, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, NamedTuple

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
    FrontBrowser,
    bearer,
    callback,
    changing_accounts,
    collected,
    created,
    exchanged,
    jeanne,
    known,
    new_address,
    realm_address,
    refreshed,
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
    lasts,
    mailed_link,
    password_grant,
    relay,
    required,
    set_by_link,
    set_password,
)

from waterfall.core.users import interface
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database, utc_now
from waterfall.platform.keycloak import IdentityProviderError, Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin

pytestmark = pytest.mark.keycloak

# The roles of WF-ARC-0030: one that lets its holder consult the accounts, one that does not.
CONSULTING = "users.read"
PLANNING = "planning.read"
SESSIONS = "/api/v1/me/sessions"


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


def refused_sign_in(username: str, password: str) -> httpx2.Response:
    """Try to sign in through the login page of the realm; give the page that refuses it."""
    browser = FrontBrowser()
    page, _ = browser.login_page()
    response = browser.submit(page, {"username": username, "password": password})
    # The login page again, with its error, and no way back to the front.
    assert response.status_code == 200, response.headers.get("Location")
    assert 'name="password"' in response.text
    return response


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


def locked_out(admin: httpx2.Client, account: Account) -> None:
    """Fail ten sign-ins of an account, then find that its own password no longer signs it in.

    Keycloak counts a failure in the background (``DefaultBruteForceProtector``): the account is
    locked once its detection says so, which is waited for, five seconds at most (#853).
    """
    with httpx2.Client(base_url=realm_address(), timeout=30) as realm:
        for _ in range(10):
            failed = password_grant(realm, account, "not-the-password")
            assert (failed.status_code, failed.json()["error"]) == (400, "invalid_grant")
        detection = f"/attack-detection/brute-force/users/{account.id}"
        deadline = time.monotonic() + 5
        while not admin.get(detection).json()["disabled"]:
            assert time.monotonic() < deadline, "the tenth failure locked nothing"
            time.sleep(0.1)
        locked = password_grant(realm, account, PASSWORD)
        assert (locked.status_code, locked.json()["error"]) == (400, "invalid_grant"), locked.text


@pytest.mark.requirement("WF-ADM-0140-A")
def test_ten_failures_lock_the_account_for_fifteen_minutes(
    admin: httpx2.Client, local_account: Account
) -> None:
    # « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes. » Locked, the
    # account refuses even its password; the realm locks it for fifteen minutes whatever the count
    # of failures, never for good — the settings of the lock, and its state. That a lock ends
    # when its time is out is proved on a lock made short, below.
    locked_out(admin, local_account)
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
            "maxTemporaryLockouts",
            "maxDeltaTimeSeconds",
            "quickLoginCheckMilliSeconds",
            "minimumQuickLoginWaitSeconds",
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
        # No count of temporary locks that would turn into a permanent one.
        "maxTemporaryLockouts": 0,
        # The ten failures are those within fifteen minutes; no lock for failures in quick
        # succession, which would lock the account before its tenth.
        "maxDeltaTimeSeconds": 899,
        "quickLoginCheckMilliSeconds": 0,
        "minimumQuickLoginWaitSeconds": 0,
    }


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_locked_account_signs_in_again_once_its_lock_is_over(
    admin: httpx2.Client, local_account: Account
) -> None:
    # « Dix échecs verrouillent le compte, qui se déverrouille après quinze minutes » : the
    # fifteen minutes are two seconds here; once they are over, the password signs in again.
    with realm_set(waitIncrementSeconds=2, maxFailureWaitSeconds=2):
        locked_out(admin, local_account)
        time.sleep(3)
        with httpx2.Client(base_url=realm_address(), timeout=30) as realm:
            unlocked = password_grant(realm, local_account, PASSWORD)
    assert unlocked.status_code == 200, unlocked.text


# Rounds of two sign-ins at once: one would let a race pass unseen (#972).
SIMULTANEOUS_ROUNDS = 10


class Attempt(NamedTuple):
    """A sign-in through the login page: its browser, its verifier of PKCE, the realm's answer."""

    browser: FrontBrowser
    verifier: str
    answer: httpx2.Response


def simultaneous_sign_ins(fields: dict[str, str]) -> list[Attempt]:
    """Open the login page in two browsers, then submit ``fields`` in both at once."""
    browsers = [FrontBrowser(), FrontBrowser()]
    pages = [browser.login_page() for browser in browsers]
    start = threading.Barrier(len(browsers))

    def submitted(index: int) -> Attempt:
        page, verifier = pages[index]
        start.wait(timeout=30)
        return Attempt(browsers[index], verifier, browsers[index].submit(page, fields))

    with ThreadPoolExecutor(len(browsers)) as pool:
        return list(pool.map(submitted, range(len(browsers))))


def test_two_simultaneous_sign_ins_are_both_admitted_or_one_refused_once_without_failure(
    admin: httpx2.Client, local_account: Account
) -> None:
    # #972: Keycloak's guard against guesses sent at once refuses a sign-in of an account while
    # another is being checked — a few tens of milliseconds. Two sign-ins with the password at
    # the same instant are both admitted, or one is refused, ``user_temporarily_disabled`` its
    # only cause in the realm's events; no failure is counted, the account is not locked, and
    # the refused one, tried again, is admitted at once.
    fields = {"username": local_account.email, "password": PASSWORD}
    query = {"user": local_account.id, "type": "LOGIN_ERROR"}
    detection = f"/attack-detection/brute-force/users/{local_account.id}"
    with realm_set(eventsEnabled=True) as realm:
        seen = 0
        for _ in range(SIMULTANEOUS_ROUNDS):
            attempts = simultaneous_sign_ins(fields)
            errors = realm.get("/events", params=query).json()
            # The newest events come first: those of this round, before those already seen.
            causes = tuple(event.get("error") for event in errors[: len(errors) - seen])
            seen = len(errors)
            returned = tuple(sorted(attempt.answer.status_code for attempt in attempts))
            assert (returned, causes) in {
                ((302, 302), ()),
                ((200, 302), ("user_temporarily_disabled",)),
            }, (returned, causes)
            state = admin.get(detection).json()
            assert (state["disabled"], state["numFailures"]) == (False, 0), state
            for browser, verifier, answer in attempts:
                again = answer if answer.status_code == 302 else browser.submit(answer, fields)
                assert again.status_code == 302, again.text
                exchanged(browser.returned(again), verifier)


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
    assert lasts(lifespan, 3600)
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
    assert lasts(lifespan, 3600)
    form = browser.get(url)
    assert 'name="password-new"' in form.text, form.text
    password = secrets.token_urlsafe(24)
    past_its_second(url)
    done = browser.submit(form, {"password-new": password, "password-confirm": password})
    assert done.status_code == 302, done.text
    assert done.headers["Location"].startswith(f"{callback()}?"), done.headers["Location"]
    tokens_of(local_account.email, password)
    used = Browser().get(url)
    assert used.status_code == 400, used.text
    said = html.unescape(used.text)
    assert SPENT in said
    assert 'name="password-new"' not in said


KEYCLOAK_CONTAINER_VARIABLE = "WATERFALL_TEST_KEYCLOAK_CONTAINER"


def restart_keycloak() -> None:
    """Restart the container of Keycloak, then wait until the realm answers, three minutes at most.

    ``make test-keycloak`` names the container: no other test runs while it restarts.
    """
    container = required(KEYCLOAK_CONTAINER_VARIABLE)
    subprocess.run(["docker", "restart", container], check=True, capture_output=True)
    deadline = time.monotonic() + 180
    while True:
        try:
            if httpx2.get(realm_address(), timeout=5).status_code == 200:
                return
        except httpx2.HTTPError:
            pass
        assert time.monotonic() < deadline, "Keycloak did not answer again"
        time.sleep(2)


def past_its_second(url: str) -> None:
    """Wait until the second the link of a forgotten password was made is over.

    The extension holds such a link spent once the password of its account was set in a later
    second than the one it was made in (#852): a test that sets the password by the link waits
    for that second to end, two seconds more for a clock that drifts a little (#853).
    """
    time.sleep(max(0.0, action_token(url)["iat"] + 2 - time.time()))


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_link_for_a_forgotten_password_used_once_stays_refused_after_a_restart(
    local_account: Account,
) -> None:
    # « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé » : refused
    # still once Keycloak restarted within its hour, whatever Keycloak keeps of its use (#852).
    browser = Browser()
    ask_forgotten(browser, local_account)
    url = mailed_link(local_account.email, whole=True)
    form = browser.get(url)
    assert 'name="password-new"' in form.text, form.text
    password = secrets.token_urlsafe(24)
    past_its_second(url)
    done = browser.submit(form, {"password-new": password, "password-confirm": password})
    assert done.status_code == 302, done.text
    restart_keycloak()
    used = Browser().get(url)
    said = html.unescape(used.text)
    assert used.status_code == 400, said
    assert SPENT in said
    assert 'name="password-new"' not in said


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_link_for_a_forgotten_password_is_refused_once_a_password_is_set_another_way(
    admin: httpx2.Client, local_account: Account
) -> None:
    # « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé » : the mark
    # of its use is the date of the password, so a password set after the link was mailed — here
    # by the console — spends it too (#852).
    ask_forgotten(Browser(), local_account)
    url = mailed_link(local_account.email, whole=True)
    past_its_second(url)
    set_password(admin, local_account.id, secrets.token_urlsafe(24))
    refused = Browser().get(url)
    said = html.unescape(refused.text)
    assert refused.status_code == 400, said
    assert SPENT in said
    assert 'name="password-new"' not in said


@pytest.mark.requirement("WF-ADM-0140-A")
def test_a_link_for_a_forgotten_password_after_its_hour_is_refused(local_account: Account) -> None:
    # « Un lien de réinitialisation utilisé une fois, ou après une heure, est refusé. » The hour
    # is the lifespan of the links the realm mails a person who asks for one: a second here.
    browser = Browser()
    with realm_set(actionTokenGeneratedByUserLifespan=1):
        ask_forgotten(browser, local_account)
    url = mailed_link(local_account.email, whole=True)
    lifespan = action_token(url)
    assert lasts(lifespan, 1)
    # Keycloak refuses a token once its whole-second clock is past "exp": wait from the token's
    # own hour, not from the request, which the mail it sends makes last. Host and container share
    # the clock; two seconds more would cover one that drifts a little (#853).
    time.sleep(max(0.0, lifespan["exp"] + 2 - time.time()))
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
        email = session.get_one(UserAccount, user_id).email
    assert email is not None
    email = email.lower()
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
    # the two hours of the session left idle, which a second plays here, set once the tokens are
    # obtained — the exchange of the code takes what it takes (#860). The return to the sign-in,
    # then to the screen aimed at, is the front's (frontend/e2e/service/).
    tokens = tokens_of(local_account.email, PASSWORD)
    # Keycloak returns the remaining lifetime, not the configured one: the exchange of the code
    # can cost a second or more under load (#1510).
    assert 7190 <= tokens["refresh_expires_in"] <= 7200
    with realm_set(ssoSessionIdleTimeout=1):
        time.sleep(2.1)
        again = refreshed(tokens["refresh_token"])
    assert (again.status_code, again.json()["error"]) == (400, "invalid_grant")


# --- WF-SEC-0020: a sign-out, and a session revoked ---------------------------------------------


@pytest.mark.requirement("WF-SEC-0020-A")
def test_closing_my_sessions_closes_them_on_every_device(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    # « Un utilisateur qui se déconnecte ne peut plus agir avec ses jetons. » Neither the refresh
    # tokens of his devices, which Keycloak refuses, nor their access tokens, which the API
    # refuses without waiting for their expiry (#668), as revoked (#855).
    known(database, local_account)
    office = tokens_of(local_account.email, PASSWORD)
    home = tokens_of(local_account.email, PASSWORD)
    assert api.get(ME, headers=bearer(home)).status_code == 200
    response = api.delete(SESSIONS, headers=bearer(office))
    assert response.status_code == 204, response.text
    for device in (office, home):
        again = refreshed(device["refresh_token"])
        assert (again.status_code, again.json()["error"]) == (400, "invalid_grant")
        acting = api.get(ME, headers=bearer(device))
        assert (acting.status_code, acting.json()["code"]) == (401, "SESSION_REVOKED")
    # Signed in again, from the next second on: the sign-in is dated to the second.
    time.sleep(1.1)
    assert api.get(ME, headers=bearer(tokens_of(local_account.email, PASSWORD))).status_code == 200


@pytest.mark.requirement("WF-SEC-0020-A")
def test_a_session_the_closing_missed_signs_in_again_by_giving_its_identifiers(
    api: ContractClient, database: Database, local_account: Account
) -> None:
    # « Un utilisateur qui se déconnecte ne peut plus agir avec ses jetons. » — nor with those of a
    # session Keycloak failed to close, which lives on: the API noted the closing, the realm did
    # nothing. Signed in as usual, the realm gives a token of the same sign-in, refused again; on
    # SESSION_REVOKED the front forces the authentication (prompt=login), and the realm asks for
    # the identifiers, renews the moment of the sign-in in the same session, and the token is
    # admitted (#855).
    row = known(database, local_account)
    browser = FrontBrowser()
    first = exchanged(*browser.sign_in(local_account.email, PASSWORD))
    assert api.get(ME, headers=bearer(first)).status_code == 200
    with database.transaction() as session:
        interface.note_sessions_closed(session, row["id"], utc_now())
    time.sleep(1.1)
    same = exchanged(*browser.signed_in_again())
    forced = exchanged(*browser.sign_in(local_account.email, PASSWORD, prompt="login"))
    before, again, renewed = (claims(each["access_token"]) for each in (first, same, forced))
    assert again["auth_time"] == before["auth_time"] < renewed["auth_time"]
    assert before["sid"] == again["sid"] == renewed["sid"]
    for revoked in (first, same):
        refused = api.get(ME, headers=bearer(revoked))
        assert (refused.status_code, refused.json()["code"]) == (401, "SESSION_REVOKED")
    assert api.get(ME, headers=bearer(forced)).status_code == 200


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
        assert held.email is not None
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
