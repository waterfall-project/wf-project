# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A change of the identity of a local account, carried to the realm (#810).

Waterfall is the authority on a local account (motif of WF-ADM-0050): ``updateUser`` gives the
realm, which signs it in and mails it by its address, the new name, first name and address, out of
any transaction (#669); a change refused after all gives the realm back the identity Waterfall
holds then. Run by ``make test-keycloak``, against the Keycloak of the platform, with the variables
of ``test_keycloak_authentication.py``. Moved out of ``test_keycloak_identity_sync.py``, whose
reading gives the realm back the identity it holds otherwise (#919).
"""

from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from sqlalchemy import select, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from support import ContractClient, Logs, Watching, captured_logs, nowhere
from test_keycloak_authentication import (
    ME,
    USERS,
    bearer,
    changing_accounts,
    known,
    served_settings,
    service_admin,
    tokens_of,
    with_password,
)
from test_keycloak_identity_sync import journal, user_of
from test_keycloak_platform import (
    PASSWORD,
    Account,
    mailed_link,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.correlation import HEADER
from waterfall.platform.database import Database
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin, LocalIdentity

pytestmark = pytest.mark.keycloak


@pytest.fixture
def keycloak() -> Iterator[Keycloak]:
    """Give the client of the realm the API and the worker reach."""
    client = Keycloak(served_settings())
    yield client
    client.close()


@pytest.fixture
def watching(keycloak: Keycloak, database: Database) -> Watching:
    """Give the administration client of the API, which notes the connections held at each call."""
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
def logs() -> Iterator[Logs]:
    """Capture the logs in memory, the secrets of the realm masked, then restore them.

    The fixture of ``conftest.py`` would give the process the secrets of a platform of test, which
    ``served_settings`` reads from then on and the Keycloak of the platform refuses.
    """
    with captured_logs(served_settings().secret_values()) as captured:
        yield captured


@pytest.fixture
def made(admin: httpx2.Client) -> Iterator[Callable[[str, str], Account]]:
    """Give a maker of local accounts of the realm with a password, removed after the test."""
    accounts: list[Account] = []

    def make(first_name: str, last_name: str) -> Account:
        accounts.append(with_password(admin, first_name, last_name))
        return accounts[-1]

    yield make
    for account in accounts:
        admin.delete(f"/users/{account.id}")


@dataclass(frozen=True, slots=True)
class Administrator:
    """The administrator of a test, Claude: her account in Waterfall, and her token's header."""

    user_id: UUID
    headers: dict[str, str]


@pytest.fixture
def administrator(database: Database, made: Callable[[str, str], Account]) -> Administrator:
    """Make Claude a local account Waterfall knows, which may change the accounts."""
    claude = made("Claude", "Locale")
    headers = changing_accounts(database, claude)
    return Administrator(user_of(database, claude.id), headers)


# --- #810: the identity of a local account reaches the realm -------------------------------------


def test_a_local_account_renamed_signs_in_by_its_new_address_and_is_mailed_there(
    api: ContractClient,
    database: Database,
    administrator: Administrator,
    watching: Watching,
    made: Callable[[str, str], Account],
) -> None:
    # Waterfall is the authority on a local account (motif of WF-ADM-0050): the realm, which
    # signs it in and mails it by its address, takes its new identity, asked out of any
    # transaction (#669, #810).
    paul = made("Paul", "Durand")
    row = known(database, paul, last_name="Durand", first_name="Paul")
    address = f"Paul.{uuid4().hex[:8]}@Mairie.test"
    sent = {"last_name": "Dumas", "email": address, "lock_version": 0}
    changed = api.patch(f"{USERS}/{row['id']}", headers=administrator.headers, json=sent)
    assert changed.status_code == 200, changed.text
    assert (changed.json()["last_name"], changed.json()["email"]) == ("Dumas", address)
    assert ("change_identity", 0) in watching.held
    held = watching.read_account(paul.id)
    assert held is not None
    assert (held.last_name, held.first_name, held.email) == ("Dumas", "Paul", address.lower())
    assert api.get(ME, headers=bearer(tokens_of(address.lower(), PASSWORD))).status_code == 200
    assert watching.send_invitation(paul.id) is None
    assert mailed_link(address.lower())
    assert journal(database, UUID(str(row["id"]))) == [
        ("user_update", administrator.user_id, {"fields": ["last_name", "email"]})
    ]
    # Inscribed under the correlation of the request.
    with database.transaction() as session:
        inscribed = select(AuditEntry.correlation_id).where(AuditEntry.object_id == row["id"])
        assert session.scalars(inscribed).all() == [changed.headers[HEADER]]


class Choosing(Watching):
    """An administration client before whose first write of an account its holder picks English."""

    def __init__(self, keycloak: Keycloak, database: Database) -> None:
        """Watch ``database``; no language is chosen yet."""
        super().__init__(keycloak, served_settings(), database)
        self.chosen: list[str] = []

    def _as_service(self, method: str, path: str, **options: Any) -> httpx2.Response:
        if method == "PUT" and not self.chosen:
            self.chosen.append(path)
            self.set_locale(path.rsplit("/", 1)[-1], "en")
        return super()._as_service(method, path, **options)


def test_a_change_of_identity_keeps_the_language_its_holder_chose_meanwhile(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    administrator: Administrator,
    made: Callable[[str, str], Account],
) -> None:
    # The realm is given the names and the address alone: a language chosen while the change is
    # carried (setMyPreferences, WF-INTF-0160) is not written over by what was read before.
    paul = made("Paul", "Durand")
    row = known(database, paul, last_name="Durand", first_name="Paul")
    KeycloakAdmin(keycloak, served_settings()).set_locale(paul.id, "fr")
    choosing = Choosing(keycloak, database)
    app = create_app(Services(database, keycloak, choosing, *nowhere()))
    client = ContractClient(TestClient(app, raise_server_exceptions=False), contract)
    body = {"last_name": "Dumas", "lock_version": 0}
    changed = client.patch(f"{USERS}/{row['id']}", headers=administrator.headers, json=body)
    assert changed.status_code == 200, changed.text
    assert len(choosing.chosen) == 1
    with service_admin(served_settings()) as admin:
        held = admin.get(f"/users/{paul.id}").json()
    assert (held["lastName"], held["attributes"]["locale"]) == ("Dumas", ["en"])


class Overtaken(Watching):
    """An administration client after whose change of an identity another write passes."""

    def __init__(
        self,
        keycloak: Keycloak,
        database: Database,
        user_id: UUID,
        meanwhile: Callable[[], None] | None = None,
        **values: str,
    ) -> None:
        """Watch ``database``, where ``user_id`` takes ``values`` and its next version meanwhile."""
        super().__init__(keycloak, served_settings(), database)
        self.database = database
        self.user_id = user_id
        self.meanwhile = meanwhile
        self.values = values

    def change_identity(self, subject: str, identity: LocalIdentity) -> bool:
        """Change the identity, then write the account, as another write would; then the rest."""
        done = super().change_identity(subject, identity)
        if done and self.held == [("change_identity", 0)]:
            with self.database.transaction() as session:
                session.execute(
                    update(UserAccount)
                    .where(UserAccount.id == self.user_id)
                    .values(lock_version=UserAccount.lock_version + 1, **self.values)
                )
            if self.meanwhile is not None:
                self.meanwhile()
        return done


@pytest.fixture
def overtaking(
    contract: OpenAPI, database: Database, keycloak: Keycloak
) -> Callable[..., ContractClient]:
    """Give a maker of clients of the API whose change of an account another write overtakes.

    The other write gives the account the values asked for, then what runs ``meanwhile`` runs.
    """

    def client(
        user_id: UUID, meanwhile: Callable[[], None] | None = None, **values: str
    ) -> ContractClient:
        overtaken = Overtaken(keycloak, database, user_id, meanwhile, **values)
        app = create_app(Services(database, keycloak, overtaken, *nowhere()))
        return ContractClient(TestClient(app, raise_server_exceptions=False), contract)

    return client


@pytest.mark.parametrize(
    "case",
    [
        ({"last_name": "Dumas (Paul)"}, (422, "VALIDATION_FAILED")),
        ({"email": "taken"}, (409, "ALREADY_EXISTS")),
        ({"last_name": "Dumas"}, (412, "STALE_LOCK_VERSION")),
    ],
    ids=["a name the realm refuses", "an address it holds", "a write passed meanwhile"],
)
def test_a_change_of_a_local_account_refused_leaves_the_realm_as_it_was(
    overtaking: Callable[..., ContractClient],
    database: Database,
    administrator: Administrator,
    made: Callable[[str, str], Account],
    case: tuple[dict[str, str], tuple[int, str]],
) -> None:
    # Refused by the realm, which holds the address of an account Waterfall does not know, or by
    # Waterfall once the realm took it — the realm then given back what it held (#810).
    sent, refusal = case
    paul = made("Paul", "Durand")
    row = known(database, paul, last_name="Durand", first_name="Paul")
    user_id = UUID(str(row["id"]))
    if sent.get("email") == "taken":
        sent = {"email": made("Jeanne", "Orpheline").email.upper()}
    body = {**sent, "lock_version": 0}
    refused = overtaking(user_id).patch(
        f"{USERS}/{user_id}", headers=administrator.headers, json=body
    )
    assert (refused.status_code, refused.json()["code"]) == refusal
    with database.transaction() as session:
        assert session.get_one(UserAccount, user_id).last_name == "Durand"
    assert journal(database, user_id) == []
    with service_admin(served_settings()) as admin:
        held = admin.get(f"/users/{paul.id}").json()
    assert (held["lastName"], held["email"]) == ("Durand", paul.email)


def test_a_change_refused_after_another_gives_the_realm_the_identity_waterfall_holds_then(
    overtaking: Callable[..., ContractClient],
    database: Database,
    administrator: Administrator,
    made: Callable[[str, str], Account],
) -> None:
    # Another administrator renamed Paul while the realm took the change: the realm is given back
    # the identity Waterfall holds at the refusal, read again, not the one read before (#810).
    paul = made("Paul", "Durand")
    user_id = UUID(str(known(database, paul, last_name="Durand", first_name="Paul")["id"]))
    client = overtaking(user_id, last_name="Durand-Martin")
    body = {"last_name": "Dumas", "lock_version": 0}
    refused = client.patch(f"{USERS}/{user_id}", headers=administrator.headers, json=body)
    assert (refused.status_code, refused.json()["code"]) == (412, "STALE_LOCK_VERSION")
    with service_admin(served_settings()) as admin:
        held = admin.get(f"/users/{paul.id}").json()
    assert (held["lastName"], held["firstName"], held["email"]) == (
        "Durand-Martin",
        "Paul",
        paul.email,
    )


def test_an_identity_the_realm_cannot_take_back_is_logged(
    overtaking: Callable[..., ContractClient],
    database: Database,
    administrator: Administrator,
    made: Callable[[str, str], Account],
    logs: Logs,
) -> None:
    # An account of the realm took Paul's former address meanwhile: the realm cannot be given it
    # back, which the log says; the refusal is what the caller is told (#810).
    paul = made("Paul", "Durand")
    user_id = UUID(str(known(database, paul, last_name="Durand", first_name="Paul")["id"]))
    taken: list[str] = []

    def take_the_former_address() -> None:
        with service_admin(served_settings()) as admin:
            user = {"username": paul.email, "email": paul.email, "enabled": True}
            names = {"firstName": "Jeanne", "lastName": "Orpheline"}
            created = admin.post("/users", json={**user, **names})
        assert created.status_code == 201, created.text
        taken.append(created.headers["Location"].rsplit("/", 1)[-1])

    address = f"paul.{uuid4().hex[:8]}@mairie.test"
    client = overtaking(user_id, take_the_former_address)
    body = {"email": address, "lock_version": 0}
    try:
        refused = client.patch(f"{USERS}/{user_id}", headers=administrator.headers, json=body)
        assert (refused.status_code, refused.json()["code"]) == (412, "STALE_LOCK_VERSION")
        (record,) = logs.named("account.identity_not_restored")
        assert (record["user_id"], record["reason"]) == (str(user_id), "address_taken")
        with service_admin(served_settings()) as admin:
            assert admin.get(f"/users/{paul.id}").json()["email"] == address
    finally:
        with service_admin(served_settings()) as admin:
            for subject in taken:
                admin.delete(f"/users/{subject}")


class Refusing(Database):
    """The database of the test, which refuses one transaction once told, after those let pass."""

    def __init__(self, database: Database) -> None:
        """Share the engine of ``database``; refuse nothing yet."""
        super().__init__(database.engine)
        self.passing: int | None = None

    @contextmanager
    def transaction(self) -> Generator[Session]:
        """Refuse the transaction told, as a database that does not answer; run the others."""
        if self.passing == 0:
            self.passing = None
            statement = "BEGIN"
            raise OperationalError(statement, None, ConnectionError("no answer"))
        if self.passing is not None:
            self.passing -= 1
        with super().transaction() as session:
            yield session


@pytest.fixture
def refusing(
    contract: OpenAPI, database: Database, keycloak: Keycloak
) -> Callable[[UUID], ContractClient]:
    """Give a maker of clients of the API whose change of an account another write overtakes.

    Once the change refused, the database refuses to read the account again.
    """

    def client(user_id: UUID) -> ContractClient:
        refused = Refusing(database)

        def refuse_the_reading_again() -> None:
            refused.passing = 1

        overtaken = Overtaken(keycloak, database, user_id, refuse_the_reading_again)
        app = create_app(Services(refused, keycloak, overtaken, *nowhere()))
        return ContractClient(TestClient(app, raise_server_exceptions=False), contract)

    return client


def test_a_change_refused_whose_account_cannot_be_read_again_gives_the_realm_its_former_identity(
    refusing: Callable[[UUID], ContractClient],
    database: Database,
    administrator: Administrator,
    made: Callable[[str, str], Account],
    logs: Logs,
) -> None:
    # The write of the change is refused, then the database refuses to read the account again: the
    # realm is given back the identity read before the change, and the log says why (#810).
    paul = made("Paul", "Durand")
    user_id = UUID(str(known(database, paul, last_name="Durand", first_name="Paul")["id"]))
    body = {"last_name": "Dumas", "lock_version": 0}
    refused = refusing(user_id).patch(
        f"{USERS}/{user_id}", headers=administrator.headers, json=body
    )
    assert (refused.status_code, refused.json()["code"]) == (412, "STALE_LOCK_VERSION")
    (record,) = logs.named("account.identity_not_reread")
    assert record["user_id"] == str(user_id)
    assert logs.named("account.identity_not_restored") == []
    with service_admin(served_settings()) as admin:
        held = admin.get(f"/users/{paul.id}").json()
    assert (held["lastName"], held["firstName"], held["email"]) == ("Durand", "Paul", paul.email)


def test_a_change_refused_of_an_account_attached_meanwhile_gives_the_realm_its_former_identity(
    overtaking: Callable[..., ContractClient],
    database: Database,
    administrator: Administrator,
    made: Callable[[str, str], Account],
) -> None:
    # The account was attached meanwhile to a person of the directory (#707): what Waterfall holds
    # now is not the local account the realm took the change of, which gets back its identity read
    # before the change (#810).
    paul = made("Paul", "Durand")
    user_id = UUID(str(known(database, paul, last_name="Durand", first_name="Paul")["id"]))
    attached = {"idp_subject": f"directory-{uuid4()}", "origin": "directory"}
    client = overtaking(user_id, last_name="Durand-Martin", **attached)
    body = {"last_name": "Dumas", "lock_version": 0}
    refused = client.patch(f"{USERS}/{user_id}", headers=administrator.headers, json=body)
    assert (refused.status_code, refused.json()["code"]) == (412, "STALE_LOCK_VERSION")
    with service_admin(served_settings()) as admin:
        held = admin.get(f"/users/{paul.id}").json()
    assert (held["lastName"], held["firstName"], held["email"]) == ("Durand", "Paul", paul.email)
