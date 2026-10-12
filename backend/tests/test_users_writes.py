# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An account created and changed through the API, and what Waterfall refuses of them (US-0360).

The caller, Camille Martin, holds a role that lets her consult and change the accounts. Keycloak is
the realm of test, which serves keys and nothing of the administration API: a creation Waterfall
accepts reaches it and fails there (503), what it refuses is refused before Keycloak is asked. A
local account created in Keycloak is tried against the platform
(``test_keycloak_authentication.py``); the writing of the account once Keycloak has created it is
tried here, by the function the route calls, under the correlation of a request.
"""

import threading
from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import ContractClient, Logs, Watching, bearer, nowhere, wait_for_a_lock

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.users import withdraw, write_new_account
from waterfall.core.access_roles.administrators import lock_administrators
from waterfall.core.access_roles.interface import Actor
from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.users.interface import Identity, is_address
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import Act, AuditActor, AuditEntry
from waterfall.platform.correlation import HEADER
from waterfall.platform.database import Database, utc_now
from waterfall.platform.errors import ConflictError, UnprocessableError
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ServiceSettings

USERS = "/api/v1/users"
SUBJECT = "6c2d4e1f-3a5b-4c7d-8e9f-0a1b2c3d4e5f"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
CHANGE = ("users.read", "users.write")
CORRELATION = "creation-of-an-account"
# A body of creation Waterfall accepts.
JEANNE = {"last_name": "Montgolfier", "first_name": "Jeanne", "email": "Jeanne@Mairie.LOCAL"}


@pytest.fixture
def caller_permissions() -> tuple[str, ...]:
    """Give the permissions the role of the caller grants: to consult and change the accounts."""
    return CHANGE


@pytest.fixture
def headers(
    database: Database, realm: TestRealm, caller_permissions: tuple[str, ...]
) -> dict[str, str]:
    """Write the account of the caller, Camille Martin, and her role; give her token's header."""
    held = role(database, "Gestion des comptes", permissions=caller_permissions)
    account(
        database,
        "Martin",
        "Camille",
        roles=(held,),
        id=CALLER,
        idp_subject=SUBJECT,
        email="camille.martin@example.org",
    )
    return bearer(realm.token(SUBJECT, KEY))


@pytest.fixture
def watching(keycloak: Keycloak, realm_settings: ServiceSettings, database: Database) -> Watching:
    """Give the administration client of the API, which notes the connections held at each call."""
    return Watching(keycloak, realm_settings, database)


@pytest.fixture
def client(
    contract: OpenAPI, database: Database, keycloak: Keycloak, watching: Watching
) -> ContractClient:
    """Give a client of the API whose administration client is watched."""
    app = create_app(Services(database, keycloak, watching, *nowhere()))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


def accounts(database: Database) -> list[str | None]:
    """Give the addresses of the accounts, in the order of their creation."""
    with database.transaction() as session:
        return list(session.scalars(select(UserAccount.email).order_by(UserAccount.created_at)))


def journal(database: Database) -> list[AuditEntry]:
    """Read the inscriptions of the journal, in the order they were made."""
    with database.transaction() as session:
        return list(session.scalars(select(AuditEntry).order_by(AuditEntry.id)))


def fields(response: Any) -> list[tuple[str, str]]:
    """Give the status, the code, then each field of a refusal by its pointer and its code."""
    body = response.json()
    return [
        (str(response.status_code), body["code"]),
        *((each["pointer"], each["code"]) for each in body.get("fields", [])),
    ]


@pytest.mark.requirement("WF-ADM-0050-A")
@pytest.mark.parametrize("lacking", ["last_name", "first_name", "email"])
def test_an_account_without_a_name_a_first_name_or_an_address_is_not_created(
    client: ContractClient, database: Database, headers: dict[str, str], lacking: str
) -> None:
    absent = {name: value for name, value in JEANNE.items() if name != lacking}
    assert fields(client.post(USERS, headers=headers, json=absent)) == [
        ("422", "VALIDATION_FAILED"),
        (f"/{lacking}", "VALUE_REQUIRED"),
    ]
    empty = {**JEANNE, lacking: ""}
    assert fields(client.post(USERS, headers=headers, json=empty)) == [
        ("422", "VALIDATION_FAILED"),
        (f"/{lacking}", "VALUE_REQUIRED"),
    ]
    assert accounts(database) == ["camille.martin@example.org"]


@pytest.mark.requirement("WF-ADM-0050-A")
def test_an_account_whose_address_another_holds_whatever_its_case_is_not_created(
    client: ContractClient, database: Database, headers: dict[str, str], watching: Watching
) -> None:
    holder = account(database, "Montgolfier", "Jeanne", email="jeanne@mairie.local")
    response = client.post(USERS, headers=headers, json=JEANNE)
    assert fields(response) == [("409", "ALREADY_EXISTS"), ("/email", "ALREADY_EXISTS")]
    assert response.json()["fields"][0]["params"] == {"conflicting_object_id": str(holder)}
    # Refused before the identity provider is asked: no account is created there either.
    assert watching.held == []
    assert accounts(database) == ["camille.martin@example.org", "jeanne@mairie.local"]


@pytest.mark.parametrize(
    "address",
    [
        "jeanne.mairie.local",
        "@mairie.local",
        "jeanne@",
        "jeanne@mairie@local",
        "jeanne montgolfier@mairie.local",
        "jeanne@mairie.local\n",
        "jeanne@mairie local",
    ],
    ids=["no at", "no local part", "no domain", "two at", "space", "line feed", "no-break space"],
)
def test_an_address_the_service_does_not_receive_is_refused_on_its_field(
    client: ContractClient, database: Database, headers: dict[str, str], address: str
) -> None:
    response = client.post(USERS, headers=headers, json={**JEANNE, "email": address})
    assert fields(response) == [("422", "VALIDATION_FAILED"), ("/email", "VALIDATION_FAILED")]
    assert accounts(database) == ["camille.martin@example.org"]


@pytest.mark.parametrize(
    "address",
    ["jeanne@intranet", "Jeanne@Mairie.LOCAL", "j@x.test", f"{'j' * 64}@{'m' * 181}.invalid"],
    ids=["no dot", "capitals", "special use", "254 characters"],
)
def test_an_address_is_received_as_written_special_use_domains_included(address: str) -> None:
    # One at, a local part and a domain, no space, 254 characters at most (#665).
    assert len(address) <= 254
    assert is_address(address)
    assert not is_address(f"{'j' * 64}@{'m' * 182}.invalid")


def test_the_roles_the_installation_lacks_and_any_node_are_each_named_on_its_field(
    client: ContractClient, database: Database, headers: dict[str, str], watching: Watching
) -> None:
    known = role(database, "Chiffreur")
    deleted = role(database, "Ancien rôle", deleted=True)
    sent = {
        **JEANNE,
        "access_role_ids": [str(known), str(uuid4()), str(deleted)],
        "org_node_id": str(uuid4()),
    }
    response = client.post(USERS, headers=headers, json=sent)
    # A node is unknown to every installation before EP-05 creates the tree.
    assert fields(response) == [
        ("422", "VALIDATION_FAILED"),
        ("/org_node_id", "UNKNOWN_ORG_NODE"),
        ("/access_role_ids/1", "UNKNOWN_ACCESS_ROLE"),
        ("/access_role_ids/2", "UNKNOWN_ACCESS_ROLE"),
    ]
    assert watching.held == []
    assert accounts(database) == ["camille.martin@example.org"]


def test_roles_sent_null_are_refused_on_their_field(
    client: ContractClient, database: Database, headers: dict[str, str], watching: Watching
) -> None:
    # Not sent, the account has no role; sent, they are a list, empty or not.
    response = client.post(USERS, headers=headers, json={**JEANNE, "access_role_ids": None})
    assert fields(response) == [
        ("422", "VALIDATION_FAILED"),
        ("/access_role_ids", "VALIDATION_FAILED"),
    ]
    assert watching.held == []
    assert accounts(database) == ["camille.martin@example.org"]


def test_no_connection_is_held_while_the_provider_creates_the_account(
    client: ContractClient, database: Database, headers: dict[str, str], watching: Watching
) -> None:
    # The realm of test serves no administration API: Keycloak fails, and nothing is written.
    response = client.post(USERS, headers=headers, json=JEANNE)
    assert fields(response) == [("503", "COMPONENT_UNAVAILABLE")]
    assert watching.held == [("create_account", 0)]
    assert accounts(database) == ["camille.martin@example.org"]


def test_a_caller_who_may_only_consult_the_accounts_creates_none(
    client: ContractClient, database: Database, realm: TestRealm
) -> None:
    held = role(database, "Lecture des comptes", permissions=("users.read",))
    account(database, "Martin", "Camille", roles=(held,), idp_subject=SUBJECT)
    response = client.post(USERS, headers=bearer(realm.token(SUBJECT, KEY)), json=JEANNE)
    assert fields(response) == [("403", "PERMISSION_MISSING")]
    assert response.json()["params"] == {"missing_permission": "users.write"}


def test_an_account_the_provider_fails_to_withdraw_is_said_in_the_log(
    keycloak: Keycloak, realm_settings: ServiceSettings, logs: Logs
) -> None:
    # The realm of test serves no administration API: the removal fails, and is said in the log.
    withdraw(KeycloakAdmin(keycloak, realm_settings), "kc-jeanne")
    (record,) = logs.named("account.withdrawal_failed")
    assert (record["subject"], record["level"]) == ("kc-jeanne", "error")


@pytest.fixture
def act() -> Iterator[Act]:
    """Act as Camille Martin, under the correlation of a request."""
    with logging_context(correlation_id=CORRELATION):
        yield Act(AuditActor(CALLER, "Camille Martin"), utc_now())


@pytest.mark.requirement("WF-SEC-0030-A")
def test_a_local_account_is_written_with_its_first_roles_and_both_are_inscribed(
    database: Database, headers: dict[str, str], act: Act
) -> None:
    del headers
    estimator, pilot = role(database, "Chiffreur"), role(database, "Pilote")
    identity = Identity("Montgolfier", "Jeanne", "Jeanne@Mairie.LOCAL")
    with database.transaction() as session:
        user = write_new_account(
            session, (identity, "kc-jeanne"), [pilot, estimator, pilot], Actor(CALLER, CHANGE), act
        )
    # The address as written; the roles by label, the one sent twice held once.
    written = user.model_dump(mode="json")
    assert (written["last_name"], written["first_name"], written["email"], written["origin"]) == (
        "Montgolfier",
        "Jeanne",
        "Jeanne@Mairie.LOCAL",
        "local",
    )
    assert user.access_role_labels == ["Chiffreur", "Pilote"]
    assert (user.is_active, user.lock_version.root, user.audit.created_by.kind.value) == (
        True,
        0,
        "user",
    )
    with database.transaction() as session:
        written = session.get_one(UserAccount, user.user_id.root)
        assert (written.idp_subject, written.created_by) == ("kc-jeanne", CALLER)
    created, given = journal(database)
    assert (created.action, created.object_id, created.object_label, created.params) == (
        "user_create",
        user.user_id.root,
        "Jeanne Montgolfier",
        {"origin": "local"},
    )
    assert (given.action, given.object_id, given.params) == (
        "user_access_roles_set",
        user.user_id.root,
        {
            "access_roles_granted": [
                {"access_role_id": str(estimator), "label": "Chiffreur"},
                {"access_role_id": str(pilot), "label": "Pilote"},
            ],
            "access_roles_withdrawn": [],
        },
    )
    for entry in (created, given):
        assert (entry.actor_user_id, entry.actor_display_name, entry.correlation_id) == (
            CALLER,
            "Camille Martin",
            CORRELATION,
        )
        assert entry.occurred_at == act.at


def test_an_address_taken_meanwhile_is_refused_by_the_unique_index(
    database: Database, headers: dict[str, str], act: Act
) -> None:
    del headers
    holder = account(database, "Montgolfier", "Jeanne", email="JEANNE@mairie.local")
    identity = Identity("Montgolfier", "Jeanne", "jeanne@MAIRIE.local")
    with pytest.raises(ConflictError) as refused, database.transaction() as session:
        write_new_account(session, (identity, "kc-jeanne"), [], Actor(CALLER, CHANGE), act)
    assert refused.value.code == "ALREADY_EXISTS"
    assert [(each.pointer, dict(each.params)) for each in refused.value.fields] == [
        ("/email", {"conflicting_object_id": str(holder)})
    ]
    assert journal(database) == []


def test_a_role_deleted_while_the_account_waits_for_the_guard_is_refused(
    database: Database, headers: dict[str, str], act: Act
) -> None:
    # The creation reads the roles sent under the lock that the deletion of a role holds while
    # it counts the holders: the role deleted meanwhile is unknown, and nothing is written.
    del headers
    leaving = role(database, "Rôle supprimé")
    identity = Identity("Montgolfier", "Jeanne", "jeanne@mairie.local")
    failures: list[UnprocessableError] = []

    def create() -> None:
        with logging_context(correlation_id=CORRELATION):
            try:
                with database.transaction() as session:
                    write_new_account(
                        session, (identity, "kc-jeanne"), [leaving], Actor(CALLER, CHANGE), act
                    )
            except UnprocessableError as error:
                failures.append(error)

    with Session(database.engine) as deleting:
        lock_administrators(deleting)
        creating = threading.Thread(target=create)
        creating.start()
        wait_for_a_lock(database)
        deleting.execute(
            update(AccessRole).where(AccessRole.id == leaving).values(deleted_at=act.at)
        )
        deleting.commit()
    creating.join(timeout=10)
    assert [[(each.pointer, each.code) for each in failure.fields] for failure in failures] == [
        [("/access_role_ids/0", "UNKNOWN_ACCESS_ROLE")]
    ]
    assert accounts(database) == ["camille.martin@example.org"]
    assert journal(database) == []


def change(client: ContractClient, headers: dict[str, str], user_id: UUID, **sent: object) -> Any:
    """Change an account by the API, at the version it is read at unless ``sent`` says another."""
    if "lock_version" not in sent:
        sent["lock_version"] = client.get(f"{USERS}/{user_id}", headers=headers).json()[
            "lock_version"
        ]
    return client.patch(f"{USERS}/{user_id}", headers=headers, json=sent)


def test_a_local_account_changes_its_names_and_its_address_and_the_change_is_inscribed(
    client: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    jeanne = account(database, "Montgolfier", "Jeanne")
    response = change(
        client,
        headers,
        jeanne,
        last_name="Montgolfier-Durand",
        first_name="Jeanne",
        email="Jeanne.Durand@Mairie.LOCAL",
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["last_name"], body["first_name"], body["email"]) == (
        "Montgolfier-Durand",
        "Jeanne",
        "Jeanne.Durand@Mairie.LOCAL",
    )
    assert (body["lock_version"], body["audit"]["updated_by"]["user_id"]) == (1, str(CALLER))
    [entry] = journal(database)
    # The fields changed, by their names alone: the journal keeps no name nor address.
    assert (entry.action, entry.object_id, entry.object_label, entry.params) == (
        "user_update",
        jeanne,
        "Jeanne Montgolfier-Durand",
        {"fields": ["last_name", "email"]},
    )
    assert entry.correlation_id == response.headers[HEADER]


@pytest.mark.requirement("WF-ADM-0050-A")
@pytest.mark.parametrize("origin", ["directory", "identity_provider"])
def test_the_names_and_the_address_of_an_account_of_the_provider_are_not_changed(
    client: ContractClient, database: Database, headers: dict[str, str], origin: str
) -> None:
    dominique = account(database, "Bernard", "Dominique", origin=origin)
    refused = change(
        client,
        headers,
        dominique,
        last_name="Martin",
        first_name="Dominique",
        email="Dominique.Bernard@example.org",
    )
    # The first name sent unchanged is not refused; the address in another case is a change.
    assert fields(refused) == [
        ("422", "VALIDATION_FAILED"),
        ("/last_name", "FIELD_READ_ONLY"),
        ("/email", "FIELD_READ_ONLY"),
    ]
    # An address it may not change is refused for that alone, malformed or not.
    malformed = change(client, headers, dominique, email="jeanne@")
    assert fields(malformed) == [("422", "VALIDATION_FAILED"), ("/email", "FIELD_READ_ONLY")]
    unchanged = change(
        client,
        headers,
        dominique,
        last_name="Bernard",
        first_name="Dominique",
        email="dominique.bernard@example.org",
        org_node_id=None,
    )
    assert unchanged.status_code == 200, unchanged.text
    assert (unchanged.json()["last_name"], unchanged.json()["lock_version"]) == ("Bernard", 0)
    assert journal(database) == []


def test_a_change_to_an_address_another_holds_is_refused(
    client: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    jeanne = account(database, "Montgolfier", "Jeanne")
    response = change(client, headers, jeanne, email="CAMILLE.martin@example.org")
    assert fields(response) == [("409", "ALREADY_EXISTS"), ("/email", "ALREADY_EXISTS")]
    assert response.json()["fields"][0]["params"] == {"conflicting_object_id": str(CALLER)}
    assert journal(database) == []


@pytest.mark.parametrize(
    ("sent", "refusal"),
    [
        ({"org_node_id": str(uuid4())}, [("/org_node_id", "UNKNOWN_ORG_NODE")]),
        ({"email": "jeanne@"}, [("/email", "VALIDATION_FAILED")]),
        ({"email": ""}, [("/email", "VALUE_REQUIRED")]),
        (
            {"last_name": None, "email": None},
            [("/last_name", "VALIDATION_FAILED"), ("/email", "VALIDATION_FAILED")],
        ),
    ],
    ids=["a node", "an address malformed", "an address empty", "names null"],
)
def test_a_change_with_a_field_in_fault_is_refused_on_it(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    sent: dict[str, object],
    refusal: list[tuple[str, str]],
) -> None:
    jeanne = account(database, "Montgolfier", "Jeanne")
    assert fields(change(client, headers, jeanne, **sent)) == [
        ("422", "VALIDATION_FAILED"),
        *refusal,
    ]
    assert journal(database) == []


def test_a_change_made_on_a_version_that_is_not_the_current_one_is_refused(
    client: ContractClient, database: Database, headers: dict[str, str]
) -> None:
    jeanne = account(database, "Montgolfier", "Jeanne", lock_version=3)
    response = change(client, headers, jeanne, first_name="Jeanne-Marie", lock_version=2)
    assert fields(response) == [("412", "STALE_LOCK_VERSION")]
    assert response.json()["params"] == {"expected_lock_version": 3}
    # A change that changes nothing still checks the version it is made on.
    stale = change(client, headers, jeanne, first_name="Jeanne", lock_version=2)
    assert fields(stale) == [("412", "STALE_LOCK_VERSION")]


def test_a_change_to_an_account_that_does_not_exist_is_a_missing_object(
    client: ContractClient, headers: dict[str, str]
) -> None:
    response = change(client, headers, uuid4(), first_name="Jeanne", lock_version=0)
    assert fields(response) == [("404", "NOT_FOUND")]
