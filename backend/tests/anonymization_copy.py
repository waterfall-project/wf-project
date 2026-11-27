# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy the tests of the anonymisation run the command on, ``waterfall-restore anonymize``.

(US-2960.) On a copy of the witness, the accounts the witness holds and a few more — active,
deactivated with an avatar, anonymised already, named in the journal as authors and as objects,
administrators kept named there too, left by a reading of the accounts —, and beside it a database
that stands for the identity provider's, the realm of the installation and ``master``: the tables of
Keycloak the command changes, and a few of those it deletes from, the others passed over, absent.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from access_rows import role
from migrations_support import scratch_database
from sqlalchemy import insert, select, text
from sqlalchemy.orm import Session
from support import raw_account

from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.users.interface import (
    Skipped,
    SkippedAccount,
    SkippedPerson,
    SyncReport,
    record_report,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import (
    AuditActor,
    AuditObject,
    AuditProject,
    Inscription,
    record,
)
from waterfall.platform.installation import THE_ROW, Installation
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import BackgroundTask
from waterfall.restore import anonymization
from waterfall.restore import main as restore_main

if TYPE_CHECKING:
    from collections.abc import Generator

    import pytest
    from sqlalchemy import Connection, Engine, TextClause

    from waterfall.platform.database import Database

REALM = "waterfall"
AT = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)
CORRELATION = "anonymization-test"
# Who the copy names besides the witness: names no other row of the witness holds.
PERSONS = (
    ("Quillardet", "Zéphyrine", "zephyrine.quillardet@entreprise.example"),
    ("Vandermeersch", "Aurèle", "aurele.vandermeersch@entreprise.example"),
    ("Kerguélen", "Brunehilde", "brunehilde.kerguelen@entreprise.example"),
)
# The administrators of the copy: the one its bootstrap created, and one of the directory.
ADMINISTRATORS = (
    ("Delacourt", "Isaure", "isaure.delacourt@entreprise.example"),
    ("Montgolfier", "Anselme", "anselme.montgolfier@entreprise.example"),
)
ADMINISTRATION = ("users.write", "access_roles.write")
# A person of the provider a reading left without an account, and a local account it removed.
LEFT = ("Ostrogradsky", "Philomène", "philomene.ostrogradsky@entreprise.example")
REMOVED = "orphelin.desmarais@entreprise.example"
# An account of Waterfall the reading left, named by its identifier alone.
ACCOUNT_LEFT = SkippedAccount(UUID("0b4c2a3e-7d51-4f0e-9c6a-2f8e1d3b5a70"), "LAST_ADMINISTRATOR")
# A person of another realm, for which the command refuses the copy (#5088).
ELSEWHERE = ("Ailleurs", "Personne", "personne.ailleurs@autre.example")
# The tables of the identity provider the stand-in holds, with the columns of Keycloak's.
PROVIDER_TABLES = (
    "CREATE TABLE realm (id text PRIMARY KEY, name text NOT NULL)",
    (
        "CREATE TABLE user_entity (id text PRIMARY KEY, realm_id text NOT NULL,"
        " username text NOT NULL, email text, email_constraint text,"
        " email_verified boolean NOT NULL, first_name text,"
        " last_name text, enabled boolean NOT NULL, federation_link text,"
        " service_account_client_link text)"
    ),
    "CREATE TABLE user_attribute (id text PRIMARY KEY, name text, value text, user_id text)",
    "CREATE TABLE credential (id text PRIMARY KEY, user_id text, user_label text)",
    "CREATE TABLE federated_identity (user_id text NOT NULL, federated_username text)",
    (
        "CREATE TABLE offline_user_session (user_session_id text PRIMARY KEY, user_id text,"
        " realm_id text, data text)"
    ),
    "CREATE TABLE event_entity (id text PRIMARY KEY, realm_id text, details_json text)",
    "CREATE TABLE admin_event_entity (id text PRIMARY KEY, realm_id text, representation text)",
    (
        "CREATE TABLE component (id text PRIMARY KEY, name text, parent_id text,"
        " provider_id text, provider_type text, realm_id text)"
    ),
    (
        "CREATE TABLE component_config (id text PRIMARY KEY,"
        " component_id text NOT NULL REFERENCES component (id), name text, value text)"
    ),
    (
        "CREATE TABLE identity_provider (internal_id text PRIMARY KEY, provider_alias text,"
        " realm_id text)"
    ),
    (
        "CREATE TABLE identity_provider_config (identity_provider_id text NOT NULL"
        " REFERENCES identity_provider (internal_id), name text, value text)"
    ),
    ("CREATE TABLE identity_provider_mapper (id text PRIMARY KEY, idp_alias text, realm_id text)"),
    (
        "CREATE TABLE idp_mapper_config (idp_mapper_id text NOT NULL"
        " REFERENCES identity_provider_mapper (id), name text, value text)"
    ),
    "CREATE TABLE realm_smtp_config (realm_id text NOT NULL, value text, name text NOT NULL)",
    "CREATE TABLE realm_events_listeners (realm_id text NOT NULL, value text NOT NULL)",
)
THE_REALM, OTHER_REALM, MASTER = "r-1", "r-2", "r-master"
OTHER = "autre-royaume"
# The administrators of Keycloak, in ``master``: one named by a name, one by her address.
ADMINISTERING = (
    ("Tisserand", "Héloïse", "heloise.tisserand@entreprise.example", "admin"),
    (
        "Baudricourt",
        "Ysaline",
        "ysaline.baudricourt@entreprise.example",
        "ysaline.baudricourt@entreprise.example",
    ),
)
# The mail server of a realm, as Keycloak keeps it: the relay of the production and its account.
RELAY = "smtp.entreprise.example"
MAIL_SERVER = (("host", RELAY), ("from", "waterfall@entreprise.example"), ("password", "relais"))
SILENCED = (
    text("SELECT realm_id, name, value FROM realm_smtp_config ORDER BY 1, 2"),
    text("SELECT realm_id, value FROM realm_events_listeners ORDER BY 1, 2"),
)
# A directory of the production, and the account a federation binds to it as.
DIRECTORY = "ldaps://annuaire.entreprise.example"
BINDING = "cn=lecteur,dc=entreprise,dc=example"
# What ties a realm to the outside, and the components it holds besides: the provider of its keys.
OUTSIDE = (
    text(
        "SELECT component.realm_id, component.name, component.provider_type, config.name,"
        " config.value FROM component"
        " LEFT JOIN component_config AS config ON config.component_id = component.id"
        " WHERE component.realm_id = :realm ORDER BY 2, 4"
    ),
    text(
        "SELECT provider.provider_alias, config.name, config.value FROM identity_provider"
        " AS provider JOIN identity_provider_config AS config"
        " ON config.identity_provider_id = provider.internal_id"
        " WHERE provider.realm_id = :realm ORDER BY 1, 2"
    ),
    text(
        "SELECT mapper.idp_alias, config.name, config.value FROM identity_provider_mapper"
        " AS mapper JOIN idp_mapper_config AS config ON config.idp_mapper_id = mapper.id"
        " WHERE mapper.realm_id = :realm ORDER BY 1, 2"
    ),
)
FEDERATION = "org.keycloak.storage.UserStorageProvider"
KEYS = "org.keycloak.keys.KeyProvider"
PERSONS_OF_THE_REALM = text(
    "SELECT id, username, email, email_constraint, email_verified, first_name, last_name,"
    " enabled, federation_link FROM user_entity"
    " WHERE realm_id = 'r-1' AND service_account_client_link IS NULL ORDER BY id"
)
OTHERS = text("SELECT * FROM user_entity WHERE service_account_client_link IS NOT NULL ORDER BY id")
# What the stand-in holds of a person besides her account, in either realm — the credentials of the
# realm of the administration apart, which stay.
HELD = (
    text("SELECT user_id, value FROM user_attribute ORDER BY 1"),
    text(
        "SELECT user_id, user_label FROM credential JOIN user_entity ON user_entity.id = user_id"
        " WHERE user_entity.realm_id <> 'r-master' ORDER BY 1"
    ),
    text("SELECT user_id, federated_username FROM federated_identity ORDER BY 1"),
    text("SELECT realm_id, data FROM offline_user_session ORDER BY 1"),
    text("SELECT realm_id, details_json FROM event_entity ORDER BY 1"),
    text("SELECT realm_id, representation FROM admin_event_entity ORDER BY 1"),
)
# What the anonymisation changes in Waterfall; the rest stays as it was.
CHANGED = ("public.user_account", "public.audit_entry", "public.identity_sync_report")

type Person = tuple[str, str, str]


@contextmanager
def stand_in(database_url: str) -> Generator[Engine]:
    """Give a database that stands for the identity provider's, the realm and ``master``."""
    with scratch_database(database_url, "waterfall_test_provider") as engine:
        with engine.begin() as connection:
            for statement in PROVIDER_TABLES:
                connection.execute(text(statement))
            connection.execute(
                text("INSERT INTO realm VALUES (:one, :name), (:master, 'master')"),
                {"one": THE_REALM, "master": MASTER, "name": REALM},
            )
        yield engine


def name_copy(witness: Database, owner: Engine, provider: Engine) -> list[Person]:
    """Name the persons of the copy in both databases; give every name and address it holds.

    Two of them administer the installation: the administrator its bootstrap created, and a
    person of the directory, with an avatar; the journal names them as it names the others.
    """
    administration = role(witness, "Administration", permissions=ADMINISTRATION)
    with owner.begin() as connection:
        accounts = _persons(connection)
        administering = _administrators(connection, administration)
        _journal(connection, accounts, administering)
        _report(connection)
        named = connection.execute(
            select(
                UserAccount.last_name,
                UserAccount.first_name,
                UserAccount.email,
                UserAccount.idp_subject,
            ).where(UserAccount.anonymized_at.is_(None))
        ).all()
    copied = [(str(last), str(first), str(email)) for last, first, email, _ in named]
    with provider.begin() as connection:
        # Each person of the realm is the account of Waterfall that bears her subject.
        for person, (*_, subject) in zip(copied, named, strict=True):
            provider_person(connection, THE_REALM, person, subject)
        provider_person(connection, THE_REALM, LEFT)
        for last, first, email, username in ADMINISTERING:
            provider_person(connection, MASTER, (last, first, email), username=username)
        for realm in (THE_REALM, MASTER):
            mail_server(connection, realm)
        connection.execute(
            text(
                "INSERT INTO user_entity VALUES ('service', :realm, 'service-account-api', NULL,"
                " 'service', false, NULL, NULL, true, NULL, 'client-api')"
            ),
            {"realm": THE_REALM},
        )
        _outside(connection, THE_REALM)
    return copied


def _outside(connection: Connection, realm: str) -> None:
    """Tie a realm to a directory, by a federation and its mapper, and to an external provider.

    Beside them, the provider of its keys, a component of its own.
    """
    federation, mapper, keys, provider, provider_mapper = (f"{realm}-{n}" for n in range(5))
    components = (
        (federation, "annuaire", realm, "ldap", FEDERATION),
        (mapper, "email", federation, "user-attribute-ldap-mapper", f"{FEDERATION}.mapper"),
        (keys, "rsa", realm, "rsa-generated", KEYS),
    )
    for values in components:
        connection.execute(
            text("INSERT INTO component VALUES (:id, :name, :parent, :provider, :kind, :realm)"),
            dict(zip(("id", "name", "parent", "provider", "kind"), values, strict=True))
            | {"realm": realm},
        )
    configs = (
        (federation, "connectionUrl", DIRECTORY),
        (federation, "bindDn", BINDING),
        (federation, "bindCredential", "secret-de-liaison"),
        (mapper, "ldap.attribute", "mail"),
        (keys, "priority", "100"),
    )
    for component, name, value in configs:
        connection.execute(
            text("INSERT INTO component_config VALUES (:id, :component, :name, :value)"),
            {"id": str(uuid4()), "component": component, "name": name, "value": value},
        )
    connection.execute(
        text("INSERT INTO identity_provider VALUES (:id, 'entreprise', :realm)"),
        {"id": provider, "realm": realm},
    )
    connection.execute(
        text("INSERT INTO identity_provider_config VALUES (:id, 'clientSecret', 'secret-sso')"),
        {"id": provider},
    )
    connection.execute(
        text("INSERT INTO identity_provider_mapper VALUES (:id, 'entreprise', :realm)"),
        {"id": provider_mapper, "realm": realm},
    )
    connection.execute(
        text("INSERT INTO idp_mapper_config VALUES (:id, 'claim', 'email')"),
        {"id": provider_mapper},
    )


def _persons(connection: Connection) -> list[UUID]:
    """Add the persons of the copy, one deactivated with an avatar, and one anonymised already."""
    accounts: list[UUID] = []
    for number, (last_name, first_name, email) in enumerate(PERSONS):
        values = raw_account(last_name=last_name, first_name=first_name, email=email)
        if number == 1:
            values |= {
                "state": "deactivated",
                "avatar": b"\x89PNG",
                "avatar_media_type": "image/png",
            }
        connection.execute(insert(UserAccount).values(values))
        accounts.append(UUID(str(values["id"])))
    anonymised = raw_account(
        last_name=None,
        first_name=None,
        email=None,
        state="deactivated",
        anonymized_at=datetime(2026, 1, 5, tzinfo=UTC),
    )
    connection.execute(insert(UserAccount).values(anonymised))
    return accounts


def _administrators(connection: Connection, administration: UUID) -> list[UUID]:
    """Add the administrators of the copy, holding ``administration``: the bootstrap's first."""
    installed_at = connection.execute(
        select(Installation.installed_at).where(Installation.id == THE_ROW)
    ).scalar_one()
    accounts: list[UUID] = []
    for number, (last_name, first_name, email) in enumerate(ADMINISTRATORS):
        values = raw_account(last_name=last_name, first_name=first_name, email=email)
        if number == 0:
            values |= {"created_at": installed_at, "created_by": None}
        else:
            values |= {
                "origin": "directory",
                "avatar": b"\x89PNG",
                "avatar_media_type": "image/png",
            }
        connection.execute(insert(UserAccount).values(values))
        connection.execute(
            insert(UserAccessRole).values(
                user_account_id=values["id"], access_role_id=administration
            )
        )
        accounts.append(UUID(str(values["id"])))
    return accounts


def _journal(connection: Connection, accounts: list[UUID], administering: list[UUID]) -> None:
    """Inscribe the first person as the author of a change of each person, herself included.

    And of each person made project manager of a project, the contributor named by her account
    (WF-SEC-0030, #4127): the journal names her as its object there too. Each administrator is the
    author of a change of the other, of its making project manager, and of a change of the first
    person: the journal names the administrators as authors and as objects, as any copy does.
    """
    project = AuditProject(uuid4(), "PRJ-001", "Projet copié")
    with session_in(connection) as session, logging_context(correlation_id=CORRELATION):
        author = AuditActor(accounts[0], f"{PERSONS[0][1]} {PERSONS[0][0]}")
        for audited, (last_name, first_name, _) in zip(accounts, PERSONS, strict=True):
            name = f"{first_name} {last_name}"
            changed = AuditObject("user", audited, name)
            record(session, Inscription("user_update", author, changed, AT))
            manager = AuditObject("contributor", audited, name)
            record(session, Inscription("project_manager_add", author, manager, AT, project))
        named = [
            (user_id, f"{first_name} {last_name}")
            for user_id, (last_name, first_name, _) in zip(
                administering, ADMINISTRATORS, strict=True
            )
        ]
        person = AuditObject("user", accounts[0], author.display_name)
        for (actor, actor_name), (audited, name) in zip(named, reversed(named), strict=True):
            administrator = AuditActor(actor, actor_name)
            changed = AuditObject("user", audited, name)
            record(session, Inscription("user_update", administrator, changed, AT))
            manager = AuditObject("contributor", audited, name)
            record(session, Inscription("project_manager_add", administrator, manager, AT, project))
            record(session, Inscription("user_update", administrator, person, AT))
        session.commit()


def _report(connection: Connection) -> None:
    """Keep the report of a reading that left a person of the provider and removed an address."""
    task_id = uuid4()
    connection.execute(
        insert(BackgroundTask).values(
            id=task_id,
            kind="identity_sync",
            status="succeeded",
            progress=100,
            payload={},
            correlation_id=CORRELATION,
            attempts=1,
            submitted_at=AT,
            finished_at=AT,
        )
    )
    with session_in(connection) as session:
        person = SkippedPerson("kc-left", LEFT[0], LEFT[1], LEFT[2], "EMAIL_MISSING")
        skipped: list[Skipped] = [person, ACCOUNT_LEFT]
        record_report(session, SyncReport(task_id, AT, 1, 2, 3, 4, skipped, [REMOVED]))
        session.commit()


def session_in(connection: Connection) -> Session:
    """Give a session that writes in the transaction of ``connection``, as the owner."""
    return Session(bind=connection, join_transaction_mode="create_savepoint")


def mail_server(connection: Connection, realm: str) -> None:
    """Give a realm the mail server of the production, and the listeners of its events."""
    for name, value in MAIL_SERVER:
        connection.execute(
            text("INSERT INTO realm_smtp_config VALUES (:realm, :value, :name)"),
            {"realm": realm, "name": name, "value": value},
        )
    for listener in ("jboss-logging", "email"):
        connection.execute(
            text("INSERT INTO realm_events_listeners VALUES (:realm, :value)"),
            {"realm": realm, "value": listener},
        )


def provider_person(
    connection: Connection,
    realm: str,
    person: Person,
    subject: str | None = None,
    username: str | None = None,
) -> None:
    """Add a person to a realm, what Keycloak holds of her, and the events that name her.

    An attribute, a credential, a link to an external provider, and a session.

    Her identifier is ``subject``, one of her own if none; her user name ``username``, the first
    part of her address if none.
    """
    last_name, first_name, email = person
    subject = subject or str(uuid4())
    username = username or email.partition("@")[0]
    connection.execute(
        text(
            "INSERT INTO user_entity VALUES (:id, :realm, :username, :email, :email, true,"
            " :first_name, :last_name, true, 'ldap', NULL)"
        ),
        {
            "id": subject,
            "realm": realm,
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
        },
    )
    rows = (
        ("INSERT INTO user_attribute VALUES (:id, 'LDAP_ENTRY_DN', :value, :subject)", last_name),
        ("INSERT INTO federated_identity VALUES (:subject, :value)", email),
        (
            "INSERT INTO offline_user_session VALUES (:id, :subject, :realm, :value)",
            f'{{"notes": {{"KC_LOGIN_HINT": "{email}"}}}}',
        ),
        ("INSERT INTO credential VALUES (:id, :subject, :value)", f"clé de {first_name}"),
        ("INSERT INTO event_entity VALUES (:id, :realm, :value)", f'{{"username": "{email}"}}'),
        (
            "INSERT INTO admin_event_entity VALUES (:id, :realm, :value)",
            f'{{"lastName": "{last_name}"}}',
        ),
    )
    for statement, value in rows:
        values = {"id": str(uuid4()), "realm": realm, "subject": subject, "value": value}
        connection.execute(text(statement), values)


def anonymize_copy(
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
    provider: Engine,
    realm: str = REALM,
    arguments: tuple[str, ...] = (anonymization.CONFIRMATION,),
) -> int:
    """Run the command on the two databases, as the operator does, told they are a copy's."""
    monkeypatch.setenv("WATERFALL_DATABASE_URL", database_url)
    url = provider.url.render_as_string(hide_password=False)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_DATABASE_URL", url)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_REALM", realm)
    return restore_main.main([anonymization.COMMAND, *arguments])


def source_needles(copy: list[Person]) -> set[str]:
    """Every name, first name and address of the source, and the names the journal shows.

    Those of the administrators of Keycloak, in ``master``, among them.
    """
    named = [*copy, LEFT, *((last, first, email) for last, first, email, _ in ADMINISTERING)]
    return {
        *(part for person in named for part in person),
        *(f"{first} {last}" for last, first, _ in named),
        REMOVED,
    }


def rows(connection: Connection, query: TextClause) -> list[tuple[object, ...]]:
    """Give the rows of a query of the stand-in, as tuples."""
    return [tuple(row) for row in connection.execute(query)]
