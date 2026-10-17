# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Each action of EP-03 that WF-SEC-0030 names, done through the API, read back in the journal.

The actions are those of the platform: an account created by an administrator and by the reading
of the identity provider, changed, given and withdrawn its roles, deactivated and reactivated, its
password link made; a role created, changed and deleted. They are done against the Keycloak of the
platform — the provider creates the local account and the extension makes its link —, by an
administrator who signs in to it, then read through ``listAuditEvents``. Run by
``make test-keycloak``, with the variables of ``test_keycloak_authentication.py``.
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx2
import pytest
from access_rows import role
from openapi_core import OpenAPI
from support import ContractClient
from test_keycloak_authentication import (
    DIRECTORY_CREDENTIAL,
    ME,
    USERS,
    bearer,
    collected,
    jeanne,
    known,
    new_address,
    served_api,
    served_settings,
    service_admin,
    tokens_of,
    with_password,
)
from test_keycloak_platform import DIRECTORY_EMAIL, PASSWORD, Account

from waterfall.platform.database import Database
from waterfall.platform.keycloak import Keycloak

pytestmark = pytest.mark.keycloak

ROLES = "/api/v1/access-roles"
EVENTS = "/api/v1/audit-events"
# What the administrator may do: everything this journal inscribes, and read it.
ADMINISTRATION = (
    "users.read",
    "users.write",
    "access_roles.read",
    "access_roles.write",
    "audit_log.read",
)


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
    made = with_password(admin, "Claire", "Martin")
    yield made
    admin.delete(f"/users/{made.id}")


@pytest.fixture
def administrator(database: Database, local_account: Account) -> tuple[str, dict[str, str]]:
    """Make an account of the realm Waterfall's administrator; give its identifier and token."""
    row = known(database, local_account, first_name="Claire", last_name="Martin")
    role(database, "Administration", permissions=ADMINISTRATION, holders=(row["id"],))
    return str(row["id"]), bearer(tokens_of(local_account.email, PASSWORD))


@pytest.fixture
def in_realm(admin: httpx2.Client, database: Database) -> Iterator[list[str]]:
    """Collect the accounts a test creates in the realm, and remove them after."""
    with collected(admin, database) as subjects:
        yield subjects


def done(response: Any, status: int = 200) -> dict[str, Any]:
    """Give the body of an answer that did what was asked; fail otherwise."""
    assert response.status_code == status, response.text
    return response.json() if response.content else {}


def act(api: ContractClient, headers: dict[str, str]) -> dict[str, str]:
    """Do each action of the platform once through the API; give the objects by their name.

    A person of the directory signs in first, created by the platform at her first request.
    """
    directory = done(api.get(ME, headers=bearer(tokens_of(DIRECTORY_EMAIL, DIRECTORY_CREDENTIAL))))
    pilot = done(
        api.post(ROLES, headers=headers, json={"label": "Pilotage", "permissions": []}), 201
    )
    pilot_id = pilot["access_role_id"]
    done(
        api.patch(
            f"{ROLES}/{pilot_id}",
            headers=headers,
            json={
                "label": "Pilotage de projet",
                "permissions": ["planning.read"],
                "lock_version": 0,
            },
        )
    )
    body = jeanne(new_address(), access_role_ids=[pilot_id])
    account = done(api.post(USERS, headers=headers, json=body), 201)
    user_id = account["user_id"]
    version = done(
        api.patch(
            f"{USERS}/{user_id}",
            headers=headers,
            json={"first_name": "Jeanne-Marie", "lock_version": account["lock_version"]},
        )
    )["lock_version"]
    version = done(
        api.request(
            "PUT",
            f"{USERS}/{user_id}/access-roles",
            headers=headers,
            json={"access_role_ids": [], "lock_version": version},
        )
    )["lock_version"]
    done(api.post(f"{USERS}/{user_id}/password-link", headers=headers), 201)
    for is_active in (False, True):
        version = done(
            api.request(
                "PUT",
                f"{USERS}/{user_id}/activation",
                headers=headers,
                json={"is_active": is_active, "lock_version": version},
            )
        )["lock_version"]
    done(api.delete(f"{ROLES}/{pilot_id}", headers=headers), 204)
    return {"directory": directory["user_id"], "jeanne": user_id, "pilot": pilot_id}


@pytest.mark.requirement("WF-SEC-0030-A")
@pytest.mark.usefixtures("in_realm")
def test_each_action_of_the_platform_produces_an_inscription_dated_and_attributed(
    api: ContractClient, administrator: tuple[str, dict[str, str]]
) -> None:
    # « Chacune des actions énumérées produit une inscription datée et attribuée » — those of this
    # EPIC: the creation and the change of the accounts, of the roles and of their attributions,
    # and the request of a password link. « La suppression d'un rôle produit une inscription qui
    # nomme l'action et l'objet » : the role by its identifier and its label.
    author, headers = administrator
    start = datetime.now(UTC)
    named = act(api, headers)
    end = datetime.now(UTC)
    page = done(api.get(f"{EVENTS}?{urlencode({'limit': 500})}", headers=headers))
    events = page["items"][::-1]
    claire = {"kind": "user", "user_id": author, "display_name": "Claire Martin"}
    assert [
        (event["action"], event["actor"], event["object"]["object_id"]) for event in events
    ] == [
        ("user_create", {"kind": "platform"}, named["directory"]),
        ("access_role_create", claire, named["pilot"]),
        ("access_role_update", claire, named["pilot"]),
        ("user_create", claire, named["jeanne"]),
        ("user_access_roles_set", claire, named["jeanne"]),
        ("user_update", claire, named["jeanne"]),
        ("user_access_roles_set", claire, named["jeanne"]),
        ("password_link_create", claire, named["jeanne"]),
        ("user_deactivate", claire, named["jeanne"]),
        ("user_reactivate", claire, named["jeanne"]),
        ("access_role_delete", claire, named["pilot"]),
    ]
    for event in events:
        assert start <= datetime.fromisoformat(event["occurred_at"]) <= end, event
    pilot = {"access_role_id": named["pilot"], "label": "Pilotage de projet"}
    assert events[0]["params"] == {"origin": "directory"}
    assert [(event["object"]["label"], event["params"]) for event in events[1:]] == [
        ("Pilotage", {"permissions": []}),
        (
            "Pilotage de projet",
            {
                "permissions_granted": ["planning.read"],
                "permissions_withdrawn": [],
                "previous_label": "Pilotage",
            },
        ),
        ("Jeanne Montgolfier", {"origin": "local"}),
        ("Jeanne Montgolfier", {"access_roles_granted": [pilot], "access_roles_withdrawn": []}),
        ("Jeanne-Marie Montgolfier", {"fields": ["first_name"]}),
        (
            "Jeanne-Marie Montgolfier",
            {"access_roles_granted": [], "access_roles_withdrawn": [pilot]},
        ),
        ("Jeanne-Marie Montgolfier", {}),
        ("Jeanne-Marie Montgolfier", {}),
        ("Jeanne-Marie Montgolfier", {}),
        ("Pilotage de projet", {}),
    ]


@pytest.mark.requirement("WF-ADM-0190-A")
@pytest.mark.usefixtures("in_realm")
def test_the_journal_filtered_on_an_author_and_the_attribution_presents_it_dated_of_the_day(
    api: ContractClient, administrator: tuple[str, dict[str, str]]
) -> None:
    # « Après le marquage d'une révision par un utilisateur, le journal filtré sur cet utilisateur
    # et sur l'action de marquage présente une inscription datée du jour » : the marking arrives in
    # EP-04; here the attribution of a role, which names the account and the role given.
    author, headers = administrator
    named = act(api, headers)
    query = urlencode({"user_id": author, "actions": "user_access_roles_set"})
    events = done(api.get(f"{EVENTS}?{query}", headers=headers))["items"]
    today = datetime.now(UTC).date()
    assert [
        (
            datetime.fromisoformat(event["occurred_at"]).date(),
            event["object"]["object_id"],
            event["params"]["access_roles_granted"],
        )
        for event in events
    ] == [
        (today, named["jeanne"], []),
        (
            today,
            named["jeanne"],
            [{"access_role_id": named["pilot"], "label": "Pilotage de projet"}],
        ),
    ]
