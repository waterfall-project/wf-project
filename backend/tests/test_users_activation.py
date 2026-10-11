# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""An account deactivated, reactivated, and given its roles through the API (US-0360).

The caller, Camille Martin, holds a role that lets her consult and change the accounts, and is no
administrator: the account she changes, Jeanne Montgolfier, is. Keycloak is the realm of test,
which serves keys and nothing of the administration API: the closing of the sessions of an account
reaches it and fails there, which the API says in its log and answers all the same. The closing
itself is tried against the platform (``test_keycloak_authentication.py``).
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import ADMINISTRATION, account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from support import ContractClient, Logs, Watching, bearer, wait_for_a_lock

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.administrators import lock_administrators
from waterfall.core.access_roles.tables import AccessRole
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database, utc_now
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.settings import ServiceSettings

USERS = "/api/v1/users"
ME = "/api/v1/me"
CAMILLE = "6c2d4e1f-3a5b-4c7d-8e9f-0a1b2c3d4e5f"
JEANNE = "kc-jeanne"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
# The administration, and the consultation of the accounts the table of the accounts needs.
DIRECTION = (*ADMINISTRATION, "users.read")


@pytest.fixture
def headers(database: Database, realm: TestRealm) -> dict[str, str]:
    """Write the account of the caller, Camille Martin, and her role; give her token's header."""
    held = role(database, "Gestion des comptes", permissions=("users.read", "users.write"))
    account(database, "Martin", "Camille", roles=(held,), id=CALLER, idp_subject=CAMILLE)
    return bearer(realm.token(CAMILLE, KEY))


@pytest.fixture
def managing(database: Database, realm: TestRealm) -> dict[str, str]:
    """Write Camille Martin, who may also change the roles, and so give them (#834)."""
    held = role(database, "Gestion des comptes et des rôles", permissions=DIRECTION)
    account(database, "Martin", "Camille", roles=(held,), id=CALLER, idp_subject=CAMILLE)
    return bearer(realm.token(CAMILLE, KEY))


@pytest.fixture
def watching(keycloak: Keycloak, realm_settings: ServiceSettings, database: Database) -> Watching:
    """Give the administration client of the API, which notes the connections held at each call."""
    return Watching(keycloak, realm_settings, database)


@pytest.fixture
def client(
    contract: OpenAPI, database: Database, keycloak: Keycloak, watching: Watching
) -> ContractClient:
    """Give a client of the API whose administration client is watched."""
    app = create_app(Services(database, keycloak, watching))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def jeanne(database: Database) -> tuple[UUID, UUID]:
    """Write Jeanne Montgolfier's account, the last administrator; give it and her role."""
    direction = role(database, "Direction", permissions=DIRECTION)
    user_id = account(database, "Montgolfier", "Jeanne", roles=(direction,), idp_subject=JEANNE)
    return user_id, direction


def activate(client: ContractClient, headers: dict[str, str], user_id: UUID, **sent: Any) -> Any:
    """Activate or deactivate an account by the API, at version 0 unless ``sent`` says another."""
    body = {"lock_version": 0, **sent}
    return client.request("PUT", f"{USERS}/{user_id}/activation", headers=headers, json=body)


def give(client: ContractClient, headers: dict[str, str], user_id: UUID, *roles: UUID) -> Any:
    """Set the roles of an account by the API, at the version it is read at."""
    version = client.get(f"{USERS}/{user_id}", headers=headers).json()["lock_version"]
    body = {"access_role_ids": [str(each) for each in roles], "lock_version": version}
    return client.request("PUT", f"{USERS}/{user_id}/access-roles", headers=headers, json=body)


def problem(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def journal(database: Database) -> list[tuple[str, UUID, dict[str, Any]]]:
    """Read the inscriptions of the journal: action, object and data, in their order."""
    with database.transaction() as session:
        entries = session.scalars(select(AuditEntry).order_by(AuditEntry.id))
        return [(entry.action, entry.object_id, entry.params) for entry in entries]


def row(database: Database, user_id: UUID) -> tuple[str, int, UUID | None]:
    """Read the state, the version and the last author of an account."""
    with database.transaction() as session:
        written = session.get_one(UserAccount, user_id)
        return written.state, written.lock_version, written.updated_by


@pytest.mark.requirement("WF-ADM-0060-A")
def test_a_deactivated_account_is_refused_and_reactivated_signs_in_with_its_roles_of_before(
    client: ContractClient,
    database: Database,
    realm: TestRealm,
    headers: dict[str, str],
    jeanne: tuple[UUID, UUID],
) -> None:
    # « La connexion d'un compte désactivé est refusée. » and « Un compte réactivé se connecte de
    # nouveau avec ses rôles d'avant. » A second administrator lets Jeanne be deactivated.
    jeanne_id, direction = jeanne
    account(database, "Durand", "Paul", roles=(direction,))
    signed_in = bearer(realm.token(JEANNE, KEY))
    before = client.get(ME, headers=signed_in).json()
    deactivated = activate(client, headers, jeanne_id, is_active=False)
    assert deactivated.status_code == 200, deactivated.text
    body = deactivated.json()
    assert (body["is_active"], body["lock_version"], body["access_role_labels"]) == (
        False,
        1,
        ["Direction"],
    )
    assert body["available_commands"][0]["command"] == "reactivate"
    assert problem(client.get(ME, headers=bearer(realm.token(JEANNE, KEY))))[:2] == (
        401,
        "ACCOUNT_DEACTIVATED",
    )
    assert activate(client, headers, jeanne_id, is_active=True, lock_version=1).status_code == 200
    after = client.get(ME, headers=bearer(realm.token(JEANNE, KEY))).json()
    assert (after["access_role_ids"], after["permissions"]) == (
        before["access_role_ids"],
        before["permissions"],
    )
    assert row(database, jeanne_id) == ("active", 2, CALLER)
    assert journal(database) == [
        ("user_deactivate", jeanne_id, {}),
        ("user_reactivate", jeanne_id, {}),
    ]


@pytest.mark.requirement("WF-SEC-0020-A")
def test_the_deactivation_of_an_account_signed_in_twice_interrupts_both_at_their_next_request(
    client: ContractClient,
    database: Database,
    realm: TestRealm,
    headers: dict[str, str],
    watching: Watching,
) -> None:
    # « La désactivation d'un compte connecté sur deux postes interrompt les deux à leur requête
    # suivante. » The API reads the account at each request: both tokens are refused, whatever the
    # provider does of the sessions it is asked to close — here, nothing: it fails, and the
    # deactivation stands all the same. Each device holds its own token, of its own session.
    paul = account(database, "Durand", "Paul", idp_subject="kc-paul")
    office, home = (
        bearer(realm.token("kc-paul", KEY, claims={"sid": device})) for device in ("office", "home")
    )
    assert office != home
    assert [client.get(ME, headers=device).status_code for device in (office, home)] == [200, 200]
    assert activate(client, headers, paul, is_active=False).status_code == 200
    for device in (office, home):
        assert problem(client.get(ME, headers=device))[:2] == (401, "ACCOUNT_DEACTIVATED")
    # Asked once the deactivation is committed, with no connection held (#669).
    assert watching.held == [("close_sessions", 0)]


@pytest.mark.requirement("WF-ADM-0120-A")
def test_the_deactivation_of_the_last_administrator_is_refused_until_a_second_one_is_active(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    jeanne: tuple[UUID, UUID],
    watching: Watching,
) -> None:
    # « La désactivation du dernier compte administrateur est refusée » — a deactivated holder of
    # the role is no administrator —, « Elle est acceptée dès qu'un second compte actif porte la
    # permission. »
    jeanne_id, direction = jeanne
    account(database, "Durand", "Paul", roles=(direction,), state="deactivated")
    (announced,) = client.get(f"{USERS}/{jeanne_id}", headers=headers).json()["available_commands"]
    assert announced == {
        "command": "deactivate",
        "is_available": False,
        "missing_conditions": ["last_administrator"],
    }
    # The refusal names the condition the command announced.
    refused = activate(client, headers, jeanne_id, is_active=False)
    assert problem(refused) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": announced["missing_conditions"][0]},
    )
    assert (row(database, jeanne_id), journal(database), watching.held) == (
        ("active", 0, None),
        [],
        [],
    )
    account(database, "Lefèvre", "Anne", roles=(direction,))
    assert activate(client, headers, jeanne_id, is_active=False).status_code == 200
    assert row(database, jeanne_id) == ("deactivated", 1, CALLER)


@pytest.mark.requirement("WF-ADM-0120-A")
def test_roles_that_take_the_administration_from_the_last_administrator_are_refused(
    client: ContractClient, database: Database, realm: TestRealm, jeanne: tuple[UUID, UUID]
) -> None:
    # « … de même que le retrait de son rôle. » Giving her more stays possible; « Elle est acceptée
    # dès qu'un second compte actif porte la permission. » Only an administrator gives roles (#834):
    # the last one is the only one who may withdraw hers.
    jeanne_id, direction = jeanne
    herself = bearer(realm.token(JEANNE, KEY))
    pilot = role(database, "Pilote", permissions=("planning.read",))
    assert problem(give(client, herself, jeanne_id, pilot)) == (409, "LAST_ADMINISTRATOR", {})
    assert (row(database, jeanne_id), journal(database)) == (("active", 0, None), [])
    more = give(client, herself, jeanne_id, direction, pilot)
    assert more.json()["access_role_labels"] == ["Direction", "Pilote"]
    account(database, "Durand", "Paul", roles=(direction,))
    assert give(client, herself, jeanne_id, pilot).json()["access_role_labels"] == ["Pilote"]


def test_who_may_change_the_accounts_but_not_the_roles_does_not_give_himself_the_administration(
    client: ContractClient, database: Database, headers: dict[str, str], jeanne: tuple[UUID, UUID]
) -> None:
    # The identifier of the role of the administration is read in the table of the accounts; giving
    # it is managing the roles (FBS-1.2, WF-ADM-0090), refused without that permission (#834).
    jeanne_id, direction = jeanne
    read = client.get(f"{USERS}/{jeanne_id}", headers=headers).json()
    assert read["access_role_ids"] == [str(direction)]
    refused = give(client, headers, CALLER, direction)
    assert problem(refused) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "access_roles.write"},
    )
    assert (row(database, CALLER), journal(database)) == (("active", 0, None), [])
    me = client.get(ME, headers=headers).json()
    assert "access_roles.write" not in me["permissions"]


def test_the_roles_of_an_account_are_replaced_and_the_attribution_inscribed(
    client: ContractClient, database: Database, managing: dict[str, str], watching: Watching
) -> None:
    pilot, estimator, auditor = (
        role(database, label) for label in ("Pilote", "Chiffreur", "Audit")
    )
    paul = account(database, "Durand", "Paul", roles=(pilot, estimator))
    response = give(client, managing, paul, auditor, estimator, auditor)
    assert response.status_code == 200, response.text
    # A role sent twice is held once; the one kept is not given again.
    assert (response.json()["access_role_labels"], response.json()["lock_version"]) == (
        ["Audit", "Chiffreur"],
        1,
    )
    assert row(database, paul) == ("active", 1, CALLER)
    assert journal(database) == [
        (
            "user_access_roles_set",
            paul,
            {
                "access_roles_granted": [{"access_role_id": str(auditor), "label": "Audit"}],
                "access_roles_withdrawn": [{"access_role_id": str(pilot), "label": "Pilote"}],
            },
        )
    ]
    # Roles remain: the sessions of the account are not closed.
    assert watching.held == []
    # The same roles again change nothing, and write nothing.
    assert give(client, managing, paul, estimator, auditor).json()["lock_version"] == 1
    assert len(journal(database)) == 1


def test_an_account_withdrawn_all_its_roles_has_its_sessions_closed(
    client: ContractClient, database: Database, managing: dict[str, str], watching: Watching
) -> None:
    pilot = role(database, "Pilote", permissions=("planning.read",))
    paul = account(database, "Durand", "Paul", roles=(pilot,))
    response = give(client, managing, paul)
    assert (response.status_code, response.json()["access_role_ids"]) == (200, [])
    assert watching.held == [("close_sessions", 0)]
    # An account that held none and still holds none loses nothing: its sessions stay.
    assert give(client, managing, paul).status_code == 200
    assert watching.held == [("close_sessions", 0)]


def test_a_role_the_installation_lacks_or_deleted_is_refused_at_its_rank(
    client: ContractClient, database: Database, managing: dict[str, str]
) -> None:
    pilot = role(database, "Pilote")
    deleted = role(database, "Ancien", deleted=True)
    paul = account(database, "Durand", "Paul")
    response = give(client, managing, paul, pilot, deleted, uuid4())
    assert problem(response)[:2] == (422, "VALIDATION_FAILED")
    assert response.json()["fields"] == [
        {"pointer": "/access_role_ids/1", "code": "UNKNOWN_ACCESS_ROLE"},
        {"pointer": "/access_role_ids/2", "code": "UNKNOWN_ACCESS_ROLE"},
    ]
    assert (row(database, paul), journal(database)) == (("active", 0, None), [])


@pytest.mark.parametrize("operation", ["activation", "access-roles"])
def test_a_write_at_another_version_or_on_no_account_is_refused(
    client: ContractClient, database: Database, managing: dict[str, str], operation: str
) -> None:
    paul = account(database, "Durand", "Paul", lock_version=3)
    sent: dict[str, object] = (
        {"is_active": False} if operation == "activation" else {"access_role_ids": []}
    )
    refusals: list[tuple[UUID, int, tuple[int, str, dict[str, object]]]] = [
        (paul, 2, (412, "STALE_LOCK_VERSION", {"expected_lock_version": 3})),
        (uuid4(), 0, (404, "NOT_FOUND", {})),
    ]
    for user_id, version, expected in refusals:
        path = f"{USERS}/{user_id}/{operation}"
        body = {**sent, "lock_version": version}
        assert problem(client.request("PUT", path, headers=managing, json=body)) == expected
    assert (row(database, paul), journal(database)) == (("active", 3, None), [])


def test_an_account_deactivated_again_keeps_its_version_and_has_its_sessions_closed_again(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    watching: Watching,
    logs: Logs,
) -> None:
    # Asking again closes the sessions a failure of the provider left open; nothing is written.
    # The realm of test closes none: the failure is said in the log, and the answer given.
    paul = account(database, "Durand", "Paul", state="deactivated")
    assert activate(client, headers, paul, is_active=False).json()["lock_version"] == 0
    assert (row(database, paul), journal(database)) == (("deactivated", 0, None), [])
    assert watching.held == [("close_sessions", 0)]
    (record,) = logs.named("account.sessions_not_closed")
    assert (record["user_id"], record["level"]) == (str(paul), "error")


def test_a_role_deleted_while_the_attribution_waits_for_the_guard_is_refused(
    client: ContractClient, database: Database, managing: dict[str, str]
) -> None:
    # The attribution takes the lock of the guard before it reads the roles sent: the deletion,
    # which holds it while it counts the holders, has marked the role deleted when they are read.
    # Read before the lock, the role would be given while deleted, held by an account.
    leaving = role(database, "Rôle supprimé")
    paul = account(database, "Durand", "Paul")
    with ThreadPoolExecutor(1) as other, Session(database.engine) as deleting:
        lock_administrators(deleting)
        attributing = other.submit(give, client, managing, paul, leaving)
        wait_for_a_lock(database)
        deleting.execute(
            update(AccessRole).where(AccessRole.id == leaving).values(deleted_at=utc_now())
        )
        deleting.commit()
        # What the thread raised is raised here, with its cause.
        answer = attributing.result(timeout=10)
    assert problem(answer)[:2] == (422, "VALIDATION_FAILED")
    assert answer.json()["fields"] == [
        {"pointer": "/access_role_ids/0", "code": "UNKNOWN_ACCESS_ROLE"}
    ]
    assert (row(database, paul), journal(database)) == (("active", 0, None), [])


@pytest.mark.parametrize("operation", ["activation", "access-roles"])
def test_a_write_that_waits_for_the_guard_holds_no_lock_on_the_account(
    client: ContractClient, database: Database, managing: dict[str, str], operation: str
) -> None:
    # The lock of the guard is taken before the account is locked, by every write that takes it:
    # a write waiting for it holds nothing another one would wait for in turn. Locked first, the
    # account would be held while the write waits, and could not be locked here.
    paul = account(database, "Durand", "Paul")
    with ThreadPoolExecutor(1) as other, Session(database.engine) as guarding:
        lock_administrators(guarding)
        writing = (
            other.submit(activate, client, managing, paul, is_active=False)
            if operation == "activation"
            else other.submit(give, client, managing, paul)
        )
        wait_for_a_lock(database)
        locked = guarding.scalar(
            select(UserAccount.id).where(UserAccount.id == paul).with_for_update(nowait=True)
        )
        guarding.commit()
        # What the thread raised is raised here, with its cause.
        answer = writing.result(timeout=10)
    assert (locked, answer.status_code) == (paul, 200)
