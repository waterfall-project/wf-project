# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A deactivated account anonymised through the API (US-0360, #702, #832).

The caller, Camille Martin, may consult and change the accounts. The account she anonymises, Paul
Durand, an account of the directory, acted and was acted upon before: the journal names him, and
the account of Léa Petit, which he wrote, names him as its author. Keycloak is the realm of test,
which serves keys and nothing of the administration API: it does not answer the removal of a
local account, which the API asks before writing anything — the account of the directory is the
provider's, and is not asked for. A local account removed indeed is tried against the platform
(``test_keycloak_authentication``).
"""

from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import ADMINISTRATION, account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import text
from support import ContractClient, Logs, Watching, bearer

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.audit import AuditActor, AuditObject, Inscription, record
from waterfall.platform.database import Database, utc_now
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ServiceSettings

USERS = "/api/v1/users"
CAMILLE = "6c2d4e1f-3a5b-4c7d-8e9f-0a1b2c3d4e5f"
CALLER = UUID("0192a1b2-0000-7000-8000-00000000ca11")
# What names Paul Durand, and must be found nowhere once he is anonymised.
PAUL = ("Paul", "Durand", "paul.durand@example.org")


@pytest.fixture
def headers(database: Database, realm: TestRealm) -> dict[str, str]:
    """Write the account of the caller, Camille Martin, and her role; give her token's header."""
    held = role(database, "Gestion des comptes", permissions=("users.read", "users.write"))
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
def paul(database: Database) -> UUID:
    """Write Paul Durand's account of the directory, deactivated, with a role and an avatar."""
    pilot = role(database, "Pilote", permissions=("planning.read",))
    return account(
        database,
        "Durand",
        "Paul",
        roles=(pilot,),
        state="deactivated",
        origin="directory",
        idp_subject="kc-paul",
        avatar=b"\x89PNG",
        avatar_media_type="image/png",
    )


def anonymize(client: ContractClient, headers: dict[str, str], user_id: UUID, version: int) -> Any:
    """Anonymise an account by the API, at the version given."""
    body = {"lock_version": version}
    return client.request("POST", f"{USERS}/{user_id}/anonymization", headers=headers, json=body)


def problem(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


def journal(database: Database) -> list[dict[str, Any]]:
    """Read every inscription of the journal whole, in its order."""
    with database.engine.connect() as connection:
        query = text("SELECT to_jsonb(audit_entry) FROM audit_entry ORDER BY id")
        return list(connection.execute(query).scalars())


def row(database: Database, user_id: UUID) -> dict[str, Any]:
    """Read the row of an account whole, its avatar included."""
    with database.engine.connect() as connection:
        query = text("SELECT to_jsonb(user_account) FROM user_account WHERE id = :id")
        return connection.execute(query, {"id": user_id}).scalar_one()


def names_paul(value: object) -> bool:
    """Tell whether a text of a body, a row or an inscription names Paul Durand."""
    return any(part in str(value) for part in PAUL)


def inscribe_as(database: Database, actor: AuditActor) -> None:
    """Inscribe the creation of a role by ``actor``, under the correlation of a request."""
    created = AuditObject("access_role", uuid4(), "Contrôle de gestion")
    with logging_context(correlation_id="req-paul"), database.transaction() as session:
        record(session, Inscription("access_role_create", actor, created, utc_now()))


@pytest.mark.requirement("WF-ADM-0060-A")
def test_an_anonymized_account_is_named_on_no_screen_of_the_accounts_and_is_not_reactivated(
    client: ContractClient, database: Database, headers: dict[str, str], paul: UUID
) -> None:
    # « Après anonymisation d'un compte désactivé, aucun écran — journal d'audit compris — ne
    # présente plus son nom ni son adresse ; […] sa réactivation est refusée. » For the screens of
    # the accounts: the table, the author of their columns of audit, the refusal.
    lea = account(database, "Petit", "Léa", created_by=paul, updated_by=paul)
    response = anonymize(client, headers, paul, 0)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["last_name"], body["first_name"], body["email"], body["has_avatar"]) == (
        None,
        None,
        None,
        False,
    )
    assert (body["anonymized_at"] is not None, body["is_active"], body["lock_version"]) == (
        True,
        False,
        1,
    )
    # Its acts stay attributed to it, by its identifier; its roles stay.
    assert body["access_role_labels"] == ["Pilote"]
    # Its reactivation and its anonymisation stay listed, unavailable (WF-IHM-0090).
    assert body["available_commands"] == [
        {"command": command, "is_available": False, "missing_conditions": ["is_not_anonymized"]}
        for command in ("reactivate", "anonymize")
    ]
    table = client.get(f"{USERS}?include_inactive=true", headers=headers)
    assert table.status_code == 200
    assert not names_paul(table.json())
    (written,) = [each for each in table.json()["items"] if each["user_id"] == str(lea)]
    assert written["audit"]["created_by"] == {
        "kind": "user",
        "user_id": str(paul),
        "display_name": None,
    }
    searched = client.get(f"{USERS}?include_inactive=true&search=durand", headers=headers)
    assert searched.json()["meta"]["total"] == 0
    # « sa réactivation est refusée », as its command says in advance; and nothing gives it back
    # a name.
    refusal = (409, "STATE_FORBIDS_OPERATION", {"missing_condition": "is_not_anonymized"})
    reactivation = {"is_active": True, "lock_version": 1}
    path = f"{USERS}/{paul}"
    reactivated = client.request("PUT", f"{path}/activation", headers=headers, json=reactivation)
    assert problem(reactivated) == refusal
    renamed = {"last_name": "Durand", "lock_version": 1}
    assert problem(client.request("PATCH", path, headers=headers, json=renamed)) == refusal
    stored = row(database, paul)
    assert (stored["state"], stored["lock_version"], stored["avatar"]) == ("deactivated", 1, None)
    assert not names_paul(stored)


@pytest.mark.requirement("WF-SEC-0030-A")
def test_after_an_anonymization_no_inscription_names_the_account_and_none_else_changes(
    client: ContractClient, database: Database, headers: dict[str, str], paul: UUID
) -> None:
    # « Après anonymisation d'un compte, aucune inscription ne porte plus son nom ; leur nombre,
    # leurs dates et leurs actions sont inchangés. » Paul acted, then was deactivated again; the
    # anonymisation is inscribed itself, last.
    inscribe_as(database, AuditActor(paul, "Paul Durand"))
    deactivation = {"is_active": False, "lock_version": 0}
    path = f"{USERS}/{paul}/activation"
    # Reactivated, then deactivated: two inscriptions name him as their object.
    client.request("PUT", path, headers=headers, json={"is_active": True, "lock_version": 0})
    client.request("PUT", path, headers=headers, json={**deactivation, "lock_version": 1})
    before = journal(database)
    assert sum(names_paul(entry) for entry in before) == 3
    assert anonymize(client, headers, paul, 2).status_code == 200
    after = journal(database)
    assert not [entry for entry in after if names_paul(entry)]
    kept = ("id", "occurred_at", "action", "actor_user_id", "object_id", "params")
    assert [{name: entry[name] for name in kept} for entry in after[:-1]] == [
        {name: entry[name] for name in kept} for entry in before
    ]
    last = after[-1]
    assert (last["action"], last["object_kind"], last["object_id"], last["object_label"]) == (
        "user_anonymize",
        "user",
        str(paul),
        None,
    )
    assert (last["actor_user_id"], last["actor_display_name"]) == (str(CALLER), "Camille Martin")


def test_an_active_account_is_not_anonymized_and_nothing_is_written(
    client: ContractClient, database: Database, headers: dict[str, str], watching: Watching
) -> None:
    # Only a deactivated account is anonymised (WF-ADM-0060): the condition an active one lacks
    # is named (#856), and the provider is not asked.
    active = account(database, "Roux", "Inès", idp_subject="kc-ines")
    assert problem(anonymize(client, headers, active, 0)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "is_deactivated_account"},
    )
    stored = row(database, active)
    assert (stored["last_name"], stored["anonymized_at"], stored["lock_version"]) == (
        "Roux",
        None,
        0,
    )
    assert (journal(database), watching.held) == ([], [])


def test_an_account_anonymized_already_is_refused_as_its_command_says_and_nothing_is_written(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    paul: UUID,
    watching: Watching,
) -> None:
    # The anonymisation is irreversible, and its command says it unavailable once done (#856).
    assert anonymize(client, headers, paul, 0).status_code == 200
    assert problem(anonymize(client, headers, paul, 1)) == (
        409,
        "STATE_FORBIDS_OPERATION",
        {"missing_condition": "is_not_anonymized"},
    )
    assert [entry["action"] for entry in journal(database)] == ["user_anonymize"]
    assert (row(database, paul)["lock_version"], watching.held) == (1, [])


def test_a_local_account_the_provider_does_not_remove_is_not_anonymized_and_nothing_is_written(
    client: ContractClient, database: Database, headers: dict[str, str], watching: Watching
) -> None:
    # WF-ADM-0060: « un compte local anonymisé est en outre retiré du fournisseur d'identité ». It
    # is removed before the write, with no connection held (#669); the realm of test does not
    # answer: 503, nothing is written, and the anonymisation is asked again (#856).
    local = account(database, "Roux", "Inès", state="deactivated", idp_subject="kc-ines")
    assert problem(anonymize(client, headers, local, 0)) == (
        503,
        "COMPONENT_UNAVAILABLE",
        {"component": "identity_provider"},
    )
    assert watching.held == [("remove_account", 0)]
    stored = row(database, local)
    assert (stored["last_name"], stored["email"], stored["anonymized_at"]) == (
        "Roux",
        "inès.roux@example.org",
        None,
    )
    assert (stored["lock_version"], journal(database)) == (0, [])


def test_an_account_of_an_external_provider_anonymized_stays_in_the_provider(
    client: ContractClient, database: Database, headers: dict[str, str], watching: Watching
) -> None:
    # An external provider's account is the provider's, as one of the directory is (Paul's):
    # Waterfall removes no account of it, and the reading of the accounts recognizes it by the
    # subject the anonymisation keeps (WF-ADM-0070).
    relayed = "identity_provider"
    read = account(database, "Bernard", "Dominique", origin=relayed, state="deactivated")
    assert anonymize(client, headers, read, 0).status_code == 200
    assert row(database, read)["idp_subject"].startswith("subject-")
    assert watching.held == []


def test_an_anonymization_at_another_version_or_of_no_account_is_refused(
    client: ContractClient, database: Database, headers: dict[str, str], paul: UUID
) -> None:
    assert problem(anonymize(client, headers, paul, 3)) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": 0},
    )
    assert problem(anonymize(client, headers, uuid4(), 0)) == (404, "NOT_FOUND", {})
    assert (row(database, paul)["anonymized_at"], journal(database)) == (None, [])


def test_the_roles_of_an_anonymized_account_are_inscribed_without_its_name(
    client: ContractClient, database: Database, realm: TestRealm, paul: UUID
) -> None:
    # Its roles may still be withdrawn: the attribution names the account by no label.
    administration = role(database, "Direction", permissions=(*ADMINISTRATION, "users.read"))
    account(database, "Martin", "Camille", roles=(administration,), id=CALLER, idp_subject=CAMILLE)
    managing = bearer(realm.token(CAMILLE, KEY))
    assert anonymize(client, managing, paul, 0).status_code == 200
    body: dict[str, object] = {"access_role_ids": [], "lock_version": 1}
    withdrawn = client.request("PUT", f"{USERS}/{paul}/access-roles", headers=managing, json=body)
    assert (withdrawn.status_code, withdrawn.json()["access_role_ids"]) == (200, [])
    last = journal(database)[-1]
    assert (last["action"], last["object_label"]) == ("user_access_roles_set", None)


class Slipping(Watching):
    """The administration client, whose removal of an account succeeds, a reactivation slipped in.

    The realm of test does not serve the administration API: the removal is noted and succeeds
    here, and the first one lets the account be reactivated meanwhile, as an administrator
    would between the check of the anonymisation and its write.
    """

    def __init__(
        self, keycloak: Keycloak, settings: ServiceSettings, database: Database, user_id: UUID
    ) -> None:
        """Watch the pool of ``database``; reactivate ``user_id`` at the first removal."""
        super().__init__(keycloak, settings, database)
        self.database = database
        self.user_id = user_id
        self.removed: list[str] = []

    def remove_account(self, subject: str) -> None:
        """Note the removal; at the first one, reactivate the account around the service."""
        self._note("remove_account")
        self.removed.append(subject)
        if len(self.removed) == 1:
            with self.database.engine.begin() as connection:
                connection.execute(
                    text(
                        "UPDATE user_account SET state = 'active', "
                        "lock_version = lock_version + 1 WHERE id = :id"
                    ),
                    {"id": self.user_id},
                )


def test_a_reactivation_slipped_before_the_write_leaves_the_account_active_until_anonymized_again(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    headers: dict[str, str],
) -> None:
    # The gap #868 is to close: the account is out of the provider, the write refused, and the
    # local account active; deactivated, then anonymised again, it is removed once more, which
    # the provider takes for done, and anonymised.
    local = account(database, "Roux", "Inès", state="deactivated", idp_subject="kc-ines")
    slipping = Slipping(keycloak, realm_settings, database, local)
    app = create_app(Services(database, keycloak, slipping))
    client = ContractClient(TestClient(app, raise_server_exceptions=False), contract)
    assert problem(anonymize(client, headers, local, 0)) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": 1},
    )
    stored = row(database, local)
    assert (stored["state"], stored["last_name"], stored["anonymized_at"]) == (
        "active",
        "Roux",
        None,
    )
    deactivation = {"is_active": False, "lock_version": 1}
    path = f"{USERS}/{local}/activation"
    assert client.request("PUT", path, headers=headers, json=deactivation).status_code == 200
    assert anonymize(client, headers, local, 2).status_code == 200
    assert slipping.removed == ["kc-ines", "kc-ines"]
    assert slipping.held.count(("remove_account", 0)) == 2
    assert row(database, local)["anonymized_at"] is not None


class Removing(Watching):
    """The administration client, whose removal of an account succeeds.

    The realm of test does not serve the administration API: the removal is noted and succeeds
    here; the other calls go to the realm, which answers none.
    """

    def __init__(self, keycloak: Keycloak, settings: ServiceSettings, database: Database) -> None:
        """Watch the pool of ``database``; nothing is removed yet."""
        super().__init__(keycloak, settings, database)
        self.removed: list[str] = []

    def remove_account(self, subject: str) -> None:
        """Note the removal, which succeeds."""
        self._note("remove_account")
        self.removed.append(subject)


@pytest.fixture
def removing(
    contract: OpenAPI, database: Database, keycloak: Keycloak, realm_settings: ServiceSettings
) -> tuple[ContractClient, Removing]:
    """Give a client of the API whose administration client removes the accounts it is asked."""
    administration = Removing(keycloak, realm_settings, database)
    app = create_app(Services(database, keycloak, administration))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract), administration


def test_the_deactivation_of_a_local_account_anonymized_asked_again_closes_no_session(
    removing: tuple[ContractClient, Removing],
    database: Database,
    headers: dict[str, str],
    logs: Logs,
) -> None:
    # A call made by hand: the account is deactivated already, which answers 200; a local account
    # anonymised is no longer in the provider, which is not asked to close its sessions.
    client, administration = removing
    local = account(database, "Roux", "Inès", state="deactivated", idp_subject="kc-ines")
    assert anonymize(client, headers, local, 0).status_code == 200
    before = row(database, local)
    deactivation = {"is_active": False, "lock_version": 1}
    path = f"{USERS}/{local}/activation"
    assert client.request("PUT", path, headers=headers, json=deactivation).status_code == 200
    assert row(database, local) == before
    assert (administration.removed, administration.held) == (
        ["kc-ines"],
        [("remove_account", 0)],
    )
    assert logs.named("account.sessions_not_closed") == []


def test_the_deactivation_of_an_account_of_the_directory_anonymized_asked_again_closes_its_sessions(
    client: ContractClient, headers: dict[str, str], watching: Watching, logs: Logs, paul: UUID
) -> None:
    # An account of the directory anonymised is still the provider's: asking its deactivation
    # again closes the sessions a failure of the provider left open, as for any other. The realm
    # of test closes none: the failure is said in the log.
    assert anonymize(client, headers, paul, 0).status_code == 200
    deactivation = {"is_active": False, "lock_version": 1}
    path = f"{USERS}/{paul}/activation"
    response = client.request("PUT", path, headers=headers, json=deactivation)
    assert (response.status_code, response.json()["lock_version"]) == (200, 1)
    assert watching.held == [("close_sessions", 0)]
    (record,) = logs.named("account.sessions_not_closed")
    assert record["user_id"] == str(paul)
