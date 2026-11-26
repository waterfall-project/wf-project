# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The anonymisation of a copy, on the tables of the real Keycloak (US-2960).

A realm of its own is made on the Keycloak of the platform, which keeps the events of its sign-ins
and of its administration, relays to an external provider and locks out on failures; its persons
have a password labelled with their name, an attribute that names them, a link to the external
provider, a session, and events that copy their names and their addresses. The command's
anonymisation of the provider is then run on the database of Keycloak for that realm alone, and a
search of every column of text or of JSON of every table finds none of their names nor of their
addresses. The realm is removed after, whatever happens. Run by ``make test-keycloak``, with the
variables of ``test_keycloak_platform.py``; the database of Keycloak is reached on the server of
``WATERFALL_TEST_DATABASE_URL``, as its superuser.
"""

import time
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import httpx2
import pytest
from anonymization_support import found
from sqlalchemy import text
from test_keycloak_platform import ADDRESS_VARIABLE, PASSWORD, master_admin_token, required
from witness_template import TEST_DATABASE_VARIABLE

from waterfall.platform.database import create_database_engine, engine_url
from waterfall.restore.anonymization import anonymize_realm

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

pytestmark = pytest.mark.keycloak

CLIENT = "anonymization-direct"
PROVIDER = "elsewhere"
# How long the realm may take to keep a session it opened, in seconds.
PATIENCE = 10
SESSIONS = text(
    "SELECT count(*) FROM offline_user_session"
    " JOIN realm ON realm.id = offline_user_session.realm_id WHERE realm.name = :realm"
)


def _realm_of(name: str) -> dict[str, Any]:
    """Describe a realm that keeps every event, relays to a provider and locks out on failures."""
    return {
        "realm": name,
        "enabled": True,
        "eventsEnabled": True,
        "adminEventsEnabled": True,
        "adminEventsDetailsEnabled": True,
        "bruteForceProtected": True,
        "clients": [{"clientId": CLIENT, "publicClient": True, "directAccessGrantsEnabled": True}],
        "identityProviders": [
            {
                "alias": PROVIDER,
                "providerId": "oidc",
                "enabled": True,
                "config": {
                    "authorizationUrl": "https://provider.waterfall.test/auth",
                    "tokenUrl": "https://provider.waterfall.test/token",
                    "clientId": "waterfall",
                    "clientSecret": "not-a-secret",
                    "clientAuthMethod": "client_secret_post",
                },
            }
        ],
    }


def _administering(path: str) -> httpx2.Client:
    """Reach the administration API under ``path``, as the administrator of ``master``."""
    address = required(ADDRESS_VARIABLE).rstrip("/")
    headers = {"Authorization": f"Bearer {master_admin_token()}"}
    return httpx2.Client(base_url=f"{address}/admin/realms{path}", headers=headers, timeout=30)


@pytest.fixture
def realm() -> Iterator[str]:
    """Make a realm of its own, its attributes unmanaged allowed; remove it after."""
    name = f"anonymization-{uuid4().hex[:12]}"
    with _administering("") as admin:
        assert admin.post("", json=_realm_of(name)).status_code == 201
    try:
        with _administering(f"/{name}") as admin:
            profile = admin.get("/users/profile").json()
            profile["unmanagedAttributePolicy"] = "ENABLED"
            assert admin.put("/users/profile", json=profile).status_code == 200
            events = {
                "eventsEnabled": True,
                "eventsListeners": ["jboss-logging"],
                "adminEventsEnabled": True,
                "adminEventsDetailsEnabled": True,
            }
            assert admin.put("/events/config", json=events).status_code == 204
        yield name
    finally:
        with _administering("") as admin:
            admin.delete(f"/{name}")


@pytest.fixture
def provider() -> Iterator[Engine]:
    """Reach the database of Keycloak, on the server of the platform, as its superuser."""
    url = engine_url(required(TEST_DATABASE_VARIABLE)).set(database="keycloak")
    engine = create_database_engine(url.render_as_string(hide_password=False))
    yield engine
    engine.dispose()


def _person(admin: httpx2.Client, realm: str, last_name: str, first_name: str) -> str:
    """Make a person who signs in, fails once, is linked to the provider; give her address."""
    email = f"{first_name}.{last_name}@entreprise.example".lower()
    made = admin.post(
        "/users",
        json={
            "username": email,
            "email": email,
            "emailVerified": True,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "attributes": {"department": [f"Service de {first_name} {last_name}"]},
            "credentials": [{"type": "password", "value": PASSWORD, "temporary": False}],
        },
    )
    assert made.status_code == 201, made.text
    subject = made.headers["Location"].rsplit("/", 1)[-1]
    credential = admin.get(f"/users/{subject}/credentials").json()[0]["id"]
    labelled = admin.put(
        f"/users/{subject}/credentials/{credential}/userLabel",
        content=f"Mot de passe de {last_name}",
        headers={"Content-Type": "text/plain"},
    )
    assert labelled.status_code == 204, labelled.text
    linked = admin.post(
        f"/users/{subject}/federated-identity/{PROVIDER}",
        json={"identityProvider": PROVIDER, "userId": f"ext-{last_name}", "userName": email},
    )
    assert linked.status_code == 204, linked.text
    address = required(ADDRESS_VARIABLE).rstrip("/")
    token = f"{address}/realms/{realm}/protocol/openid-connect/token"
    for password, status in ((f"{PASSWORD}-wrong", 400), (PASSWORD, 200)):
        signed = httpx2.post(
            token,
            data={
                "grant_type": "password",
                "client_id": CLIENT,
                "username": email,
                "password": password,
            },
            timeout=30,
        )
        assert signed.status_code == status, signed.text
    return email


def _kept_sessions(provider: Engine, realm: str, count: int) -> None:
    """Wait until the realm keeps its sessions in its database, which it may write a while after."""
    deadline = time.monotonic() + PATIENCE
    while time.monotonic() < deadline:
        with provider.connect() as connection:
            if connection.execute(SESSIONS, {"realm": realm}).scalar_one() >= count:
                return
        time.sleep(0.2)


@pytest.mark.story("US-2960")
def test_no_name_and_no_address_of_a_person_of_the_realm_is_left_in_the_database_of_keycloak(
    realm: str, provider: Engine
) -> None:
    # Proper to US-2960: « une commande anonymise une sauvegarde restaurée […] dans [la base] du
    # fournisseur d'identité » ; « après l'anonymisation, une recherche des adresses et des noms de
    # la source dans les deux bases ne trouve rien » — here, the base of Keycloak as Keycloak keeps
    # it: its accounts, attributes, credentials, links, sessions, and events of sign-in and of
    # administration.
    suffix = uuid4().hex[:8]
    named = [
        (f"Quillardet{suffix}", f"Zephyrine{suffix}"),
        (f"Kerguelen{suffix}", f"Aurele{suffix}"),
    ]
    with _administering(f"/{realm}") as admin:
        addresses = [
            _person(admin, realm, last_name, first_name) for last_name, first_name in named
        ]
    _kept_sessions(provider, realm, len(named))
    needles = {*addresses, *(name for person in named for name in person)}
    before = found(provider, needles)
    assert {
        "public.user_entity.email",
        "public.user_entity.first_name",
        "public.user_attribute.value",
        "public.credential.user_label",
        "public.federated_identity.federated_username",
        "public.admin_event_entity.representation",
    } <= set(before), sorted(before)
    # The events of sign-in name the user, in one column or the other as Keycloak's version keeps
    # long details.
    assert any(column.startswith("public.event_entity.") for column in before), sorted(before)
    with provider.begin() as connection:
        assert anonymize_realm(connection, realm) == len(named)
    assert found(provider, needles) == {}
