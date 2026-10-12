# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the accounts of the provider, on the platform (US-0370/L2).

The worker runs the task ``identity_sync`` against the Keycloak of the platform and the directory
of test it federates: a person of the directory gets an account before any sign-in; one the
directory no longer retains — by a filter of its federation, or the federation removed — is
deactivated, the last administrator kept and reported (WF-ADM-0070, WF-ADM-0180). A person of the
directory is attached by her address to the account that holds it (#707); the local accounts of the
realm Waterfall does not know and that never had a password are removed (#811); the reading gives
the realm back the identity of a local account it holds otherwise (#919), which a change of the
identity carries to it (#810, ``test_keycloak_identity_change.py``). Run by
``make test-keycloak``, with the variables of ``test_keycloak_authentication.py``, whose helpers it
takes. A test that changes the federation of the realm gives it back, whatever happens.

The realm keeps the accounts of other tests and of its own installation, that the database of the
test does not know: each test of a reading makes Waterfall know them first (``realm_known``), as
the realm holds them, so that the reading neither creates them, nor removes them, nor gives them
another identity.
"""

import time
from collections.abc import Callable, Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import httpx2
import pytest
from access_rows import ADMINISTRATION, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from sqlalchemy import Engine, delete, insert, select
from support import ContractClient, Logs, Watching, captured_logs, nowhere, raw_account
from test_keycloak_authentication import (
    DIRECTORY_CREDENTIAL,
    EXTERNAL_CREDENTIAL,
    EXTERNAL_USERNAME,
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
from test_keycloak_platform import (
    DIRECTORY_EMAIL,
    EXTERNAL_PROVIDER,
    PASSWORD,
    Account,
    administering,
    set_password,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.interface import roles_held_by
from waterfall.core.users.interface import (
    NAME_MAX_LENGTH,
    Skipped,
    SkippedAccount,
    SkippedPerson,
    SyncReport,
    latest_report,
    record_report,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database, utc_now
from waterfall.platform.keycloak import Keycloak, unavailable
from waterfall.platform.keycloak_admin import KeycloakAdmin, LocalIdentity
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import BackgroundTask, submit
from waterfall.worker import identity_sync
from waterfall.worker.identity_sync import IdentitySync
from waterfall.worker.runner import Worker

pytestmark = pytest.mark.keycloak

USER_STORAGE = "org.keycloak.storage.UserStorageProvider"
# The bind credential of the directory of test, a development value
# (deploy/keycloak/development/waterfall.yaml), which the realm masks when it is read.
BIND_CREDENTIAL = "development-only-directory-admin"
# A filter of the federation that retains every person of the directory but Dominique.
WITHOUT_DOMINIQUE = "(!(uid=dominique.annuaire))"
EXTERNAL_EMAIL = "camille.externe@external.test"
SYNCS = "/api/v1/identity-syncs"


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
def reading(keycloak: Keycloak) -> IdentitySync:
    """Give the reading of the accounts as the worker runs it."""
    return IdentitySync(KeycloakAdmin(keycloak, served_settings()))


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


def user_of(database: Database, subject: str) -> UUID:
    """Give the account Waterfall holds for a subject of the realm."""
    with database.transaction() as session:
        return session.scalars(
            select(UserAccount.id).where(UserAccount.idp_subject == subject)
        ).one()


@pytest.fixture
def realm_known(database: Database, reading: IdentitySync) -> None:
    """Make Waterfall know, as local ones, the accounts the realm holds but the directory's.

    Each as the realm holds it: the reading gives the realm back the identity Waterfall holds of a
    local account (#919). One whose names or address Waterfall cannot hold, as an account
    anonymised, which the reading leaves alone.
    """
    with database.transaction() as session:
        held = set(session.scalars(select(UserAccount.idp_subject)))
        for account in reading.admin.list_accounts():
            if account.is_federated or account.subject in held:
                continue
            identity = {
                "last_name": account.last_name,
                "first_name": account.first_name,
                "email": account.email,
            }
            if all(1 <= len(value) <= NAME_MAX_LENGTH for value in identity.values()):
                row = raw_account(idp_subject=account.subject, **identity)
            else:
                gone = {"state": "deactivated", "anonymized_at": utc_now()}
                row = raw_account(idp_subject=account.subject, **dict.fromkeys(identity), **gone)
            session.execute(insert(UserAccount).values(**row))


def read_accounts(
    database: Database, reading: IdentitySync, requested_by: UUID | None = None
) -> SyncReport:
    """Have a worker run a reading of the accounts, asked for or scheduled; give its report."""
    queue, _ = nowhere()
    with (
        logging_context(correlation_id=f"reading-{uuid4().hex}"),
        database.transaction() as session,
    ):
        task_id = submit(session, queue, "identity_sync", requested_by)
    assert Worker(database, queue, {"identity_sync": reading}, "worker").run_task(task_id)
    queue.close()
    with database.transaction() as session:
        report = latest_report(session)
    assert report is not None
    assert report.task_id == task_id
    return report


def counts(report: SyncReport) -> tuple[int, int, int, list[Skipped], list[str]]:
    """Give what a report counts, then what it names."""
    return report.created, report.updated, report.deactivated, report.skipped, report.removed


def of_the_directory(database: Database) -> UserAccount:
    """Read the account of Dominique, the person of the directory of test."""
    with database.transaction() as session:
        account = session.scalars(
            select(UserAccount).where(UserAccount.email == DIRECTORY_EMAIL)
        ).one()
        session.expunge(account)
    return account


def journal(database: Database, user_id: UUID) -> list[tuple[Any, ...]]:
    """Read the inscriptions about an account: action, author, data."""
    with database.transaction() as session:
        rows = session.execute(
            select(AuditEntry.action, AuditEntry.actor_user_id, AuditEntry.params)
            .where(AuditEntry.object_id == user_id)
            .order_by(AuditEntry.id)
        )
        return [tuple(row) for row in rows]


def directory() -> dict[str, Any]:
    """Read the federation of the directory of test, as the realm holds it."""
    with administering() as realm:
        (component,) = realm.get("/components", params={"type": USER_STORAGE}).json()
    return component


@contextmanager
def directory_retaining(search: str) -> Generator[None]:
    """Have the federation retain only the persons of an LDAP filter, then every person again."""
    component = directory()

    def retain(searched: list[str]) -> None:
        config = {**component["config"], "customUserSearchFilter": searched}
        with administering() as realm:
            done = realm.put(f"/components/{component['id']}", json={**component, "config": config})
        assert done.status_code == 204, done.text

    retain([search])
    try:
        yield
    finally:
        retain([])


@contextmanager
def directory_removed() -> Generator[Callable[[], None]]:
    """Remove the federation of the directory; give what federates it again, done at the end.

    It is federated again under the same identifier, with its credential and its mappers.
    """
    component = directory()
    with administering() as realm:
        mappers = realm.get("/components", params={"parent": component["id"]}).json()
        assert realm.delete(f"/components/{component['id']}").status_code == 204
    federated: list[bool] = []

    def federate() -> None:
        config = {**component["config"], "bindCredential": [BIND_CREDENTIAL]}
        with administering() as realm:
            created = realm.post("/components", json={**component, "config": config})
            assert created.status_code == 201, created.text
            defaults = realm.get("/components", params={"parent": component["id"]}).json()
            named = {mapper["name"]: mapper["id"] for mapper in defaults}
            for mapper in mappers:
                put = {**mapper, "id": named[mapper["name"]]}
                assert realm.put(f"/components/{put['id']}", json=put).status_code == 204
        federated.append(True)

    try:
        yield federate
    finally:
        if not federated:
            federate()


# --- WF-ADM-0070: the persons of the directory ---------------------------------------------------


@pytest.mark.requirement("WF-ADM-0070-A")
@pytest.mark.usefixtures("realm_known")
def test_after_a_scheduled_reading_a_person_of_the_directory_has_an_account_before_any_sign_in(
    database: Database, reading: IdentitySync
) -> None:
    # « Après lecture, chaque personne de l'annuaire retenue a un compte actif dans Waterfall, sans
    # rôle si elle n'en avait pas, avant toute connexion. » « Une personne ajoutée à l'annuaire a
    # un compte dans Waterfall au terme de la périodicité choisie, sans intervention. » : the
    # reading the platform schedules, with no one asking (its interval is tried by
    # test_worker_process.py). Her first name is the directory's givenName (#667).
    report = read_accounts(database, reading)
    assert counts(report) == (1, 0, 0, [], [])
    account = of_the_directory(database)
    assert (account.first_name, account.last_name, account.origin, account.state) == (
        "Dominique",
        "Annuaire",
        "directory",
        "active",
    )
    assert (account.created_by, account.updated_by) == (None, None)
    with database.transaction() as session:
        assert roles_held_by(session, [account.id]) == {account.id: []}
    assert journal(database, account.id) == [("user_create", None, {"origin": "directory"})]
    # Read again, nothing changes.
    assert counts(read_accounts(database, reading)) == (0, 0, 0, [], [])


@pytest.mark.requirement("WF-SEC-0010-A")
@pytest.mark.usefixtures("realm_known")
def test_the_reading_finds_the_directory_without_ever_holding_its_secret(
    database: Database, reading: IdentitySync, admin: httpx2.Client, logs: Logs
) -> None:
    # « Une recherche des secrets connus dans le dépôt, les images publiées et les journaux ne les
    # trouve pas. » : for the logs of the reading of the accounts. The service account may view the
    # realm, to find the directories it federates and have them synchronised; the realm masks their
    # bind credential, which neither the logs nor the report carry.
    report = read_accounts(database, reading)
    assert BIND_CREDENTIAL not in logs.text
    assert BIND_CREDENTIAL not in repr(report)
    (component,) = admin.get("/components", params={"type": USER_STORAGE}).json()
    assert component["config"]["bindCredential"] == ["**********"]


@pytest.mark.requirement("WF-ADM-0070-A")
@pytest.mark.usefixtures("realm_known")
def test_a_person_withdrawn_from_the_directory_has_her_account_deactivated_at_the_next_reading(
    database: Database, reading: IdentitySync
) -> None:
    # « Une personne retirée de l'annuaire voit son compte désactivé à la synchronisation
    # suivante » ; her acts are EP-04's. The platform deactivates it (WF-DAT-0070).
    read_accounts(database, reading)
    with directory_retaining(WITHOUT_DOMINIQUE):
        report = read_accounts(database, reading)
    assert counts(report) == (0, 0, 1, [], [])
    account = of_the_directory(database)
    assert (account.state, account.updated_by) == ("deactivated", None)
    assert journal(database, account.id)[-1] == ("user_deactivate", None, {})


@pytest.mark.requirement("WF-ADM-0070-A")
@pytest.mark.usefixtures("realm_known")
def test_the_last_administrator_withdrawn_from_the_directory_stays_active_and_is_reported(
    database: Database, reading: IdentitySync
) -> None:
    # « Le dernier compte administrateur, retiré de l'annuaire, reste actif et la synchronisation
    # le signale. »
    read_accounts(database, reading)
    account = of_the_directory(database)
    role(database, "Administration", permissions=ADMINISTRATION, holders=(account.id,))
    with directory_retaining(WITHOUT_DOMINIQUE):
        report = read_accounts(database, reading)
    # Named by its identifier alone (#920).
    assert counts(report) == (0, 0, 0, [SkippedAccount(account.id, "LAST_ADMINISTRATOR")], [])
    kept = of_the_directory(database)
    assert (kept.state, kept.lock_version) == ("active", account.lock_version)


@pytest.mark.requirement("WF-ADM-0070-A")
@pytest.mark.usefixtures("realm_known")
def test_an_anonymized_account_whose_person_is_still_in_the_directory_stays_anonymized(
    api: ContractClient, database: Database, reading: IdentitySync, administrator: Administrator
) -> None:
    # « Un compte anonymisé dont la personne figure encore dans l'annuaire reste anonymisé après
    # synchronisation, et aucun compte n'est créé à son nom. » : the reading finds her by the
    # subject the anonymisation keeps.
    read_accounts(database, reading)
    dominique = of_the_directory(database)
    path = f"{USERS}/{dominique.id}"
    deactivated = api.request(
        "PUT",
        f"{path}/activation",
        headers=administrator.headers,
        json={"is_active": False, "lock_version": dominique.lock_version},
    )
    assert deactivated.status_code == 200, deactivated.text
    lock_version = deactivated.json()["lock_version"]
    anonymized = api.post(
        f"{path}/anonymization", headers=administrator.headers, json={"lock_version": lock_version}
    )
    assert anonymized.status_code == 200, anonymized.text
    assert counts(read_accounts(database, reading)) == (0, 0, 0, [], [])
    with database.transaction() as session:
        kept = session.get_one(UserAccount, dominique.id)
        assert (kept.idp_subject, kept.state, kept.email, kept.last_name) == (
            dominique.idp_subject,
            "deactivated",
            None,
            None,
        )
        assert kept.anonymized_at is not None
        named = select(UserAccount.id).where(UserAccount.first_name == "Dominique")
        assert session.scalars(named).all() == []


# --- WF-ADM-0180: the directory withdrawn, then federated again (#844) --------------------------


@pytest.mark.requirement("WF-ADM-0180-A")
@pytest.mark.usefixtures("realm_known")
def test_the_accounts_of_a_directory_withdrawn_stay_deactivated_then_sign_in_once_federated_again(
    api: ContractClient,
    database: Database,
    reading: IdentitySync,
    administrator: Administrator,
    made: Callable[[str, str], Account],
) -> None:
    # « Après retrait de l'annuaire et synchronisation, les comptes qui en venaient existent
    # toujours, désactivés, et leurs actes restent attribués. » « Réactivés après une nouvelle
    # fédération qui les reconnaît, ils se connectent. » A new federation gives the persons other
    # subjects: the reading attaches each by her address to her account (#707).
    read_accounts(database, reading)
    dominique = of_the_directory(database)
    role(database, "Comptes", permissions=("users.read", "users.write"), holders=(dominique.id,))
    paul = known(database, made("Paul", "Durand"))
    as_dominique = bearer(tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL))
    renamed = api.patch(
        f"{USERS}/{paul['id']}",
        headers=as_dominique,
        json={"last_name": "Dumas", "lock_version": 0},
    )
    assert renamed.status_code == 200, renamed.text
    with directory_removed() as federate:
        assert counts(read_accounts(database, reading)) == (0, 0, 1, [], [])
        withdrawn = of_the_directory(database)
        assert (withdrawn.id, withdrawn.state) == (dominique.id, "deactivated")
        # Her act stays hers.
        audit = api.get(f"{USERS}/{paul['id']}", headers=administrator.headers).json()["audit"]
        assert audit["updated_by"] == {
            "kind": "user",
            "user_id": str(dominique.id),
            "display_name": "Dominique Annuaire",
        }
        federate()
    assert counts(read_accounts(database, reading)) == (0, 1, 0, [], [])
    attached = of_the_directory(database)
    assert (attached.id, attached.state) == (dominique.id, "deactivated")
    assert attached.idp_subject != dominique.idp_subject
    assert journal(database, dominique.id)[-1] == (
        "user_update",
        None,
        {"fields": [], "attached": True},
    )
    activation = {"is_active": True, "lock_version": attached.lock_version}
    reactivated = api.request(
        "PUT", f"{USERS}/{dominique.id}/activation", headers=administrator.headers, json=activation
    )
    assert reactivated.status_code == 200, reactivated.text
    me = api.get(ME, headers=bearer(tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL)))
    assert (me.status_code, me.json()["user_id"]) == (200, str(dominique.id))


# --- #707: an address an account holds, at the first request -------------------------------------


def test_a_person_of_the_directory_finds_at_her_first_request_the_account_of_her_address(
    api: ContractClient, database: Database
) -> None:
    # Created by hand before the directory was federated: hers, with its roles, once she signs in
    # by the directory; the attachment is inscribed by the platform.
    row = raw_account(email=DIRECTORY_EMAIL.upper(), last_name="Annuaire", first_name="Dominique")
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    planning = role(database, "Planification", permissions=("planning.read",), holders=(row["id"],))
    me = api.get(ME, headers=bearer(tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL)))
    assert me.status_code == 200, me.text
    body = me.json()
    assert (body["user_id"], body["origin"], body["email"]) == (
        str(row["id"]),
        "directory",
        DIRECTORY_EMAIL,
    )
    assert body["access_role_ids"] == [str(planning)]
    assert journal(database, UUID(str(row["id"]))) == [
        ("user_update", None, {"fields": ["email"], "attached": True})
    ]


def test_a_person_relayed_at_the_address_an_account_holds_is_not_admitted_and_it_stays_intact(
    api: ContractClient, database: Database
) -> None:
    # A provider lax about addresses would open the account of another (#707).
    row = raw_account(email=EXTERNAL_EMAIL)
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**row))
    tokens = tokens_of(EXTERNAL_USERNAME, EXTERNAL_CREDENTIAL, provider=EXTERNAL_PROVIDER)
    refused = api.get(ME, headers=bearer(tokens))
    assert (refused.status_code, refused.json()["code"]) == (401, "ACCOUNT_NOT_ADMITTED")
    with database.transaction() as session:
        kept = session.get_one(UserAccount, row["id"])
        assert (kept.idp_subject, kept.origin, kept.lock_version) == (
            row["idp_subject"],
            "local",
            0,
        )
    assert journal(database, UUID(str(row["id"]))) == []


@pytest.mark.usefixtures("realm_known")
def test_a_person_relayed_whose_account_cannot_be_written_is_left_and_reported(
    database: Database, owner: Engine, reading: IdentitySync, admin: httpx2.Client
) -> None:
    # Relayed by the external provider at the address an account of Waterfall holds, a person is
    # not attached (#707): ``ALREADY_EXISTS``. With a name longer than a column holds:
    # ``VALIDATION_FAILED``. Both are left, and the report names them. The account ``realm_known``
    # gave her, which the service may not delete, the owner deletes.
    tokens_of(EXTERNAL_USERNAME, EXTERNAL_CREDENTIAL, provider=EXTERNAL_PROVIDER)
    with owner.begin() as connection:
        connection.execute(delete(UserAccount).where(UserAccount.email == EXTERNAL_EMAIL))
    with database.transaction() as session:
        session.execute(insert(UserAccount).values(**raw_account(email=EXTERNAL_EMAIL)))
    long_address = f"long-{uuid4().hex[:8]}@example.org"
    user = {"username": long_address, "email": long_address, "enabled": True}
    created = admin.post("/users", json={**user, "firstName": "Jeanne", "lastName": "L" * 101})
    assert created.status_code == 201, created.text
    subject = created.headers["Location"].rsplit("/", 1)[-1]
    try:
        link = {"identityProvider": EXTERNAL_PROVIDER, "userId": str(uuid4()), "userName": "long"}
        linked = admin.post(f"/users/{subject}/federated-identity/{EXTERNAL_PROVIDER}", json=link)
        assert linked.status_code == 204, linked.text
        report = read_accounts(database, reading)
        # Each a person of the provider, named as it holds her (#918).
        persons = [each for each in report.skipped if isinstance(each, SkippedPerson)]
        assert len(persons) == len(report.skipped)
        assert sorted((each.email, each.code) for each in persons) == [
            (EXTERNAL_EMAIL, "ALREADY_EXISTS"),
            (long_address, "VALIDATION_FAILED"),
        ]
        (long,) = (each for each in persons if each.email == long_address)
        assert (long.subject, long.last_name, long.first_name) == (subject, "L" * 101, "Jeanne")
        with database.transaction() as session:
            named = select(UserAccount.id).where(UserAccount.email == long_address)
            assert session.scalars(named).all() == []
    finally:
        admin.delete(f"/users/{subject}")


# --- #811: the local accounts of the realm Waterfall does not know -------------------------------


def imported(address: str, *, hours_ago: float) -> str:
    """Make a local account of the realm, without a password, created that long ago; its subject."""
    created = int((time.time() - hours_ago * 3600) * 1000)
    user = {
        "username": address,
        "email": address,
        "firstName": "Jeanne",
        "lastName": "Orpheline",
        "enabled": True,
        "createdTimestamp": created,
    }
    with administering() as realm:
        done = realm.post("/partialImport", json={"ifResourceExists": "FAIL", "users": [user]})
        assert done.status_code == 200, done.text
        return str(done.json()["results"][0]["id"])


@pytest.mark.usefixtures("realm_known")
def test_the_local_accounts_waterfall_does_not_know_and_without_password_are_removed(
    database: Database, reading: IdentitySync, admin: httpx2.Client
) -> None:
    # Left by a creation Waterfall did not complete (#811): removed and named, once older than a
    # creation under way can be; one with a password, young, or Waterfall knows, stays.
    orphan = f"orphan-{uuid4().hex[:8]}@example.org"
    known_address = f"known-{uuid4().hex[:8]}@example.org"
    subjects = {
        "orphan": imported(orphan, hours_ago=2),
        "young": imported(f"young-{uuid4().hex[:8]}@example.org", hours_ago=0),
        "set": imported(f"set-{uuid4().hex[:8]}@example.org", hours_ago=2),
        "known": imported(known_address, hours_ago=2),
    }
    set_password(admin, subjects["set"], PASSWORD)
    known(database, Account(subjects["known"], known_address))
    try:
        assert counts(read_accounts(database, reading))[3:] == ([], [orphan])
        held = {
            name: admin.get(f"/users/{subject}").status_code for name, subject in subjects.items()
        }
        assert held == {"orphan": 404, "young": 200, "set": 200, "known": 200}
    finally:
        for subject in subjects.values():
            admin.delete(f"/users/{subject}")


class Unremoving(Watching):
    """An administration client whose removal of an account Keycloak does not answer."""

    def __init__(self, keycloak: Keycloak, database: Database) -> None:
        """Watch ``database``; no removal is asked yet."""
        super().__init__(keycloak, served_settings(), database)
        self.asked: list[str] = []

    def remove_account(self, subject: str) -> None:
        """Note the account, then fail as a realm that does not answer."""
        self.asked.append(subject)
        raise unavailable()


@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.usefixtures("realm_known")
def test_a_reading_stopped_before_its_end_leaves_the_base_and_the_realm_as_they_were(
    database: Database,
    keycloak: Keycloak,
    admin: httpx2.Client,
    logs: Logs,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « L'arrêt du worker pendant une tâche laisse la base inchangée, et la tâche est reprise après
    # redémarrage. » : for the reading of the accounts, stopped once its persons are followed,
    # before its report. Its orphans are removed from the realm once its transaction is committed
    # only: a reading stopped removes none, and one the realm does not let go is removed by the
    # next reading (#811).
    reading = IdentitySync(KeycloakAdmin(keycloak, served_settings()))
    orphan = f"orphan-{uuid4().hex[:8]}@example.org"
    subject = imported(orphan, hours_ago=2)
    queue, _ = nowhere()
    correlation = f"reading-{uuid4().hex}"
    try:
        with logging_context(correlation_id=correlation), database.transaction() as session:
            task_id = submit(session, queue, "identity_sync", None)

        def stopped(_session: object, _report: SyncReport) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(identity_sync, "record_report", stopped)
        with pytest.raises(KeyboardInterrupt):
            Worker(database, queue, {"identity_sync": reading}, "worker").run_task(task_id)
        monkeypatch.setattr(identity_sync, "record_report", record_report)
        with database.transaction() as session:
            task = session.get_one(BackgroundTask, task_id)
            assert (task.status, task.attempts) == ("running", 1)
            named = select(UserAccount.id).where(UserAccount.email == DIRECTORY_EMAIL)
            assert session.scalars(named).all() == []
            assert session.scalars(select(AuditEntry.id)).all() == []
            assert latest_report(session) is None
        assert admin.get(f"/users/{subject}").status_code == 200
        # Run again, the realm not answering the removal.
        unremoving = Unremoving(keycloak, database)
        refusing = IdentitySync(unremoving)
        assert Worker(database, queue, {"identity_sync": refusing}, "worker").run_task(task_id)
        with database.transaction() as session:
            task = session.get_one(BackgroundTask, task_id)
            assert (task.status, task.attempts) == ("succeeded", 2)
            report = latest_report(session)
        assert report is not None
        assert counts(report) == (1, 0, 0, [], [orphan])
        assert unremoving.asked == [subject]
        assert admin.get(f"/users/{subject}").status_code == 200
        (record,) = logs.named("identity_sync.orphan_not_removed")
        assert (record["subject"], record["correlation_id"]) == (subject, correlation)
        assert counts(read_accounts(database, reading)) == (0, 0, 0, [], [orphan])
        assert admin.get(f"/users/{subject}").status_code == 404
    finally:
        queue.close()
        admin.delete(f"/users/{subject}")


# --- #919: the realm given back the identity of a local account ------------------------------


@pytest.mark.requirement("WF-ADM-0070-A")
@pytest.mark.usefixtures("realm_known")
def test_a_local_account_the_realm_holds_otherwise_is_given_back_its_identity_by_the_reading(
    database: Database, reading: IdentitySync, made: Callable[[str, str], Account]
) -> None:
    # « Un compte local créé depuis Waterfall existe dans le fournisseur d'identité. » : as
    # Waterfall holds it, which is its authority (WF-ADM-0050). A report of updateUser applied by
    # the realm but left unanswered gave it another identity: the reading gives Waterfall's back,
    # once committed, and changes nothing of the account in Waterfall (#919).
    paul = made("Paul", "Durand")
    row = known(database, paul, last_name="Durand", first_name="Paul")
    elsewhere = LocalIdentity("Dumas", "Paul", f"paul.{uuid4().hex[:8]}@mairie.test")
    assert reading.admin.change_identity(paul.id, elsewhere)
    report = read_accounts(database, reading)
    assert (report.updated, report.restored, report.skipped) == (0, 1, [])
    held = reading.admin.read_account(paul.id)
    assert held is not None
    assert (held.last_name, held.first_name, held.email) == ("Durand", "Paul", paul.email)
    with database.transaction() as session:
        stored = session.get_one(UserAccount, row["id"])
        assert (stored.last_name, stored.email, stored.lock_version) == ("Durand", paul.email, 0)
    assert read_accounts(database, reading).restored == 0


# --- WF-ARC-0090: the reading of the accounts asked for -----------------------------------------


@pytest.mark.requirement("WF-ARC-0090-A")
@pytest.mark.usefixtures("realm_known")
def test_a_reading_asked_for_holds_no_request_and_its_requester_sees_it_end(
    api: ContractClient,
    database: Database,
    reading: IdentitySync,
    administrator: Administrator,
) -> None:
    # « … n'immobilise aucune requête au-delà de la création de la tâche, et l'utilisateur en voit
    # l'aboutissement. » : for the reading of the accounts.
    asked = api.post(SYNCS, headers=administrator.headers)
    assert (asked.status_code, asked.json()["status"]) == (202, "queued")
    task_id = UUID(asked.json()["task_id"])
    assert (
        api.get(f"/api/v1/tasks/{task_id}", headers=administrator.headers).json()["status"]
        == "queued"
    )
    assert Worker(database, nowhere()[0], {"identity_sync": reading}, "worker").run_task(task_id)
    ended = api.get(f"/api/v1/tasks/{task_id}", headers=administrator.headers).json()
    assert (ended["status"], ended["result_url"]) == ("succeeded", f"{SYNCS}/latest")
    report = api.get(f"{SYNCS}/latest", headers=administrator.headers).json()
    assert (report["task_id"], report["created"]) == (str(task_id), 1)
