# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The anonymisation of a copy, on the tables of the real Keycloak (US-2960).

A realm of its own is made on the Keycloak of the platform, which keeps the events of its sign-ins
and of its administration, relays to an external provider and locks out on failures; its persons
have a password labelled with their name, an attribute that names them, a link to the external
provider, a session, and events that copy their names and their addresses. It reads a directory
too, by a federation of users. The command's anonymisation of the provider is then run on the
database of Keycloak for that realm alone: a search of every column of text or of JSON of every
table finds none of their names nor of their addresses, each person is disabled and named by her
identifier, and the realm holds neither its federation nor its external provider. The realm is
removed after, whatever happens. Run by ``make test-keycloak``, with the
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

from waterfall.core.users.interface import KeptAdministrator
from waterfall.platform.database import create_database_engine, engine_url
from waterfall.restore.anonymization import (
    RealmAnonymized,
    anonymize_administration,
    anonymize_realm,
    silence,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

pytestmark = pytest.mark.keycloak

CLIENT = "anonymization-direct"
PROVIDER = "elsewhere"
FEDERATION = "org.keycloak.storage.UserStorageProvider"
# The account a federation binds to the directory as.
BINDING = "cn=lecteur,dc=entreprise,dc=example"
# How long the realm may take to keep a session it opened, in seconds.
PATIENCE = 10
SESSIONS = text(
    "SELECT count(*) FROM offline_user_session"
    " JOIN realm ON realm.id = offline_user_session.realm_id WHERE realm.name = :realm"
)
PERSONS = text(
    "SELECT user_entity.id, user_entity.username, user_entity.enabled FROM user_entity"
    " JOIN realm ON realm.id = user_entity.realm_id"
    " WHERE realm.name = :realm AND user_entity.service_account_client_link IS NULL"
)
# The credentials of the persons of a realm, counted.
CREDENTIALS = text(
    "SELECT count(*) FROM credential JOIN user_entity ON user_entity.id = credential.user_id"
    " JOIN realm ON realm.id = user_entity.realm_id WHERE realm.name = :realm"
)
# The credentials of the persons of a realm that bear a label.
LABELLED = text(
    "SELECT count(*) FROM credential JOIN user_entity ON user_entity.id = credential.user_id"
    " JOIN realm ON realm.id = user_entity.realm_id"
    " WHERE realm.name = :realm AND credential.user_label IS NOT NULL"
)
REALM_ID = text("SELECT id FROM realm WHERE name = :realm")
# What would send a mail from a realm, counted: its mail server, and its listeners of events.
MAILING = text(
    "SELECT (SELECT count(*) FROM realm_smtp_config WHERE realm_id = :id),"
    " (SELECT count(*) FROM realm_events_listeners WHERE realm_id = :id)"
)
# The relay of the production a realm sends its mails by.
RELAY = "smtp.entreprise.example"
# What ties the realm to the outside, counted: its federations of users and what lies under them,
# with their settings, and its external providers and their mappers, with theirs.
OUTSIDE = text(
    "WITH RECURSIVE "
    "the_realm AS (SELECT id FROM realm WHERE name = :realm), "
    "federation(id) AS (SELECT id FROM component WHERE realm_id = (SELECT id FROM the_realm)"
    " AND provider_type = :federation"
    " UNION SELECT component.id FROM component"
    " JOIN federation ON component.parent_id = federation.id), "
    "provider AS (SELECT internal_id FROM identity_provider"
    " WHERE realm_id = (SELECT id FROM the_realm)), "
    "mapper AS (SELECT id FROM identity_provider_mapper"
    " WHERE realm_id = (SELECT id FROM the_realm)) "
    "SELECT (SELECT count(*) FROM federation),"
    " (SELECT count(*) FROM component_config WHERE component_id IN (SELECT id FROM federation)),"
    " (SELECT count(*) FROM provider),"
    " (SELECT count(*) FROM identity_provider_config"
    " WHERE identity_provider_id IN (SELECT internal_id FROM provider)),"
    " (SELECT count(*) FROM mapper),"
    " (SELECT count(*) FROM idp_mapper_config WHERE idp_mapper_id IN (SELECT id FROM mapper))"
)


def _provider_host(realm: str) -> str:
    """Give the host of the external provider of a realm, its own."""
    return f"{realm}.provider.waterfall.test"


def _directory_host(realm: str) -> str:
    """Give the host of the directory a realm reads, its own."""
    return f"{realm}.annuaire.entreprise.example"


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
                    "authorizationUrl": f"https://{_provider_host(name)}/auth",
                    "tokenUrl": f"https://{_provider_host(name)}/token",
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


def _person(
    admin: httpx2.Client, realm: str, last_name: str, first_name: str, username: str | None = None
) -> str:
    """Make a person who signs in, fails once, is linked to the provider; give her address.

    Her user name is ``username``, her address if none.
    """
    email = f"{first_name}.{last_name}@entreprise.example".lower()
    username = username or email
    made = admin.post(
        "/users",
        json={
            "username": username,
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
                "username": username,
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


@pytest.mark.requirement("WF-EXP-0010-A")
@pytest.mark.story("US-2960")
def test_no_name_and_no_address_of_a_person_of_the_realm_is_left_in_the_database_of_keycloak(
    realm: str, provider: Engine
) -> None:
    # « Aucun environnement hors production ne contient une adresse électronique réelle, hors
    # l'environnement isolé du test de restauration. » : for a copy of the production, by its
    # anonymisation, on the base of Keycloak as Keycloak keeps it. Proper to US-2960: « une
    # commande anonymise une sauvegarde restaurée […] dans [la base] du fournisseur d'identité » ;
    # « après l'anonymisation, une recherche des adresses et des noms de la source dans les deux
    # bases ne trouve rien » — its accounts, attributes, credentials, links, sessions, and events
    # of sign-in and of administration; each person disabled, her user name her identifier, but
    # the administrator Waterfall keeps (#4068), enabled under the identity Waterfall gave it, its
    # address its user name, without a password.
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
    with provider.connect() as connection:
        subject = connection.execute(
            text("SELECT id FROM user_entity WHERE email = :email"), {"email": addresses[0]}
        ).scalar_one()
    kept = KeptAdministrator(
        uuid4(), subject, "1", "Administrator", f"administrator-{suffix}@waterfall.test"
    )
    with provider.begin() as connection:
        assert anonymize_realm(connection, realm, [kept]) == RealmAnonymized(len(named), ())
    assert found(provider, needles) == {}
    with provider.connect() as connection:
        persons = connection.execute(PERSONS, {"realm": realm}).all()
        assert connection.execute(CREDENTIALS, {"realm": realm}).scalar_one() == 0
    assert len(persons) == len(named)
    assert sorted(persons) == sorted(
        (each, kept.email, True) if each == subject else (each, each, False)
        for each, _, _ in persons
    )


def _outside(admin: httpx2.Client, realm: str) -> None:
    """Tie ``realm`` to a directory, by a federation of users, and map a claim of its provider.

    The federation is enabled and imports the persons it reads; Keycloak makes its mappers.
    """
    federation = {
        "name": "annuaire",
        "providerId": "ldap",
        "providerType": FEDERATION,
        "config": {
            "enabled": ["true"],
            "vendor": ["other"],
            "editMode": ["READ_ONLY"],
            "importEnabled": ["true"],
            "connectionUrl": [f"ldap://{_directory_host(realm)}"],
            "authType": ["simple"],
            "bindDn": [BINDING],
            "bindCredential": ["not-a-secret"],
            "usersDn": ["ou=people,dc=entreprise,dc=example"],
            "usernameLDAPAttribute": ["uid"],
            "rdnLDAPAttribute": ["uid"],
            "uuidLDAPAttribute": ["entryUUID"],
            "userObjectClasses": ["inetOrgPerson"],
        },
    }
    made = admin.post("/components", json=federation)
    assert made.status_code == 201, made.text
    mapper = {
        "name": "courriel",
        "identityProviderAlias": PROVIDER,
        "identityProviderMapper": "oidc-user-attribute-idp-mapper",
        "config": {"claim": "email", "user.attribute": "email", "syncMode": "INHERIT"},
    }
    mapped = admin.post(f"/identity-provider/instances/{PROVIDER}/mappers", json=mapper)
    assert mapped.status_code == 201, mapped.text


@pytest.mark.story("US-2960")
def test_the_realm_is_left_tied_to_neither_its_directory_nor_its_external_provider(
    realm: str, provider: Engine
) -> None:
    # Proper to US-2960: opened, the copy would read the directory of the production again — its
    # persons imported anew, names and addresses, by the account it binds as — or let them sign in
    # through the provider of the production. The realm loses its federation of users, the mappers
    # Keycloak made under it and their settings, and its external provider, its mapper and their
    # settings: the address of the directory, the account it binds as and the address of the
    # provider are found nowhere after.
    with _administering(f"/{realm}") as admin:
        _outside(admin, realm)
    outside = {_directory_host(realm), BINDING, _provider_host(realm)}
    counted = {"realm": realm, "federation": FEDERATION}
    with provider.connect() as connection:
        federations, settings, *providers = connection.execute(OUTSIDE, counted).one()
    # The federation, and the mappers Keycloak made under it.
    assert federations > 1
    assert settings > 0
    assert all(providers), providers
    assert {"public.component_config.value", "public.identity_provider_config.value"} <= set(
        found(provider, outside)
    )
    with provider.begin() as connection:
        anonymize_realm(connection, realm)
    with provider.connect() as connection:
        assert tuple(connection.execute(OUTSIDE, counted).one()) == (0,) * 6
    assert found(provider, outside) == {}


@pytest.mark.requirement("WF-EXP-0010-A")
@pytest.mark.story("US-2960")
def test_the_administrators_of_keycloak_keep_no_address_and_the_realm_sends_no_mail(
    realm: str, provider: Engine
) -> None:
    # « Aucun environnement hors production ne contient une adresse électronique réelle, hors
    # l'environnement isolé du test de restauration. » : the realm of the administration, ``master``
    # — a realm of its own stands for it here, the platform's being shared —, holds the addresses
    # of its administrators, which its events of administration copy (#5048), and their
    # attributes, their links to an external provider, the labels of their passwords and their
    # sessions (#5087). They lose them all, their names and their addresses, a user name that is an
    # address too, and keep their passwords and a user name that is none: a search of every column
    # of text of every table of the base of Keycloak finds none of their names nor of their
    # addresses after. Proper to US-2960: the realm loses its mail server — the relay of the
    # production, and its account — and its listeners of events.
    suffix = uuid4().hex[:8]
    named = (f"Tisserand{suffix}", f"Heloise{suffix}")
    addressed = (f"Baudricourt{suffix}", f"Ysaline{suffix}")
    with _administering(f"/{realm}") as admin:
        addresses = [
            _person(admin, realm, *named, username=f"admin-{suffix}"),
            _person(admin, realm, *addressed),
        ]
        mail = {"host": RELAY, "port": "25", "from": f"waterfall-{suffix}@entreprise.example"}
        assert admin.put("", json={"smtpServer": mail}).status_code == 204
        listeners = {
            "eventsEnabled": True,
            "eventsListeners": ["jboss-logging", "email"],
            "adminEventsEnabled": True,
            "adminEventsDetailsEnabled": True,
        }
        assert admin.put("/events/config", json=listeners).status_code == 204
    _kept_sessions(provider, realm, len(addresses))
    needles = {*addresses, *named, *addressed}
    before_found = found(provider, needles)
    assert {
        "public.user_entity.email",
        "public.user_entity.first_name",
        "public.user_attribute.value",
        "public.credential.user_label",
        "public.federated_identity.federated_username",
        "public.admin_event_entity.representation",
    } <= set(before_found), sorted(before_found)
    with provider.connect() as connection:
        realm_id = connection.execute(REALM_ID, {"realm": realm}).scalar_one()
        assert all(connection.execute(MAILING, {"id": realm_id}).one())
        credentials = connection.execute(CREDENTIALS, {"realm": realm}).scalar_one()
        assert connection.execute(SESSIONS, {"realm": realm}).scalar_one() >= len(addresses)
        before = connection.execute(PERSONS, {"realm": realm}).all()
    assert credentials == len(addresses)
    with provider.begin() as connection:
        assert anonymize_administration(connection, realm) == len(addresses)
        silence(connection, [realm_id])
    assert found(provider, needles) == {}
    assert found(provider, {RELAY}) == {}
    with provider.connect() as connection:
        assert tuple(connection.execute(MAILING, {"id": realm_id}).one()) == (0, 0)
        assert connection.execute(CREDENTIALS, {"realm": realm}).scalar_one() == credentials
        assert connection.execute(LABELLED, {"realm": realm}).scalar_one() == 0
        assert connection.execute(SESSIONS, {"realm": realm}).scalar_one() == 0
        after = connection.execute(PERSONS, {"realm": realm}).all()
    # The user name that is no address stays, the other becomes the identifier; both enabled.
    assert sorted(after) == sorted(
        (subject, subject if "@" in username else username, True) for subject, username, _ in before
    )
