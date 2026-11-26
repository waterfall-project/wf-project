# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The anonymisation of a copy of the production, ``waterfall-restore anonymize`` (US-2960).

On a copy of the witness, the accounts the witness holds and a few more — active, deactivated with
an avatar, anonymised already, named in the journal as authors and as objects, left by a reading of
the accounts —, and beside it a database that stands for the identity provider's: the tables of
Keycloak the command changes, and a few of those it deletes from, the others passed over, absent.
The tables of the real Keycloak are those of ``test_keycloak_anonymization.py``.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import pytest
from access_rows import role
from anonymization_support import found, held_by_table
from migrations_support import scratch_database
from sqlalchemy import delete, insert, or_, select, text, update
from sqlalchemy.orm import Session
from support import raw_account

from waterfall.core.access_roles.interface import administrators
from waterfall.core.access_roles.tables import UserAccessRole
from waterfall.core.users.interface import (
    Skipped,
    SkippedAccount,
    SkippedPerson,
    SyncReport,
    latest_report,
    read_installation_administrator,
    record_report,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditActor, AuditEntry, AuditObject, Inscription, record
from waterfall.platform.installation import THE_ROW, Installation
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import BackgroundTask
from waterfall.restore import anonymization
from waterfall.restore import main as restore_main

if TYPE_CHECKING:
    from collections.abc import Iterator

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
# A person of another realm, which the anonymisation does not touch.
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
OTHERS = text(
    "SELECT * FROM user_entity WHERE realm_id = 'r-2' OR service_account_client_link IS NOT NULL"
    " ORDER BY id"
)
# What the stand-in holds of a person besides her account — of the realm of the administration
# apart, whose attributes and credentials stay —, then the same of the other realm alone.
HELD = (
    (
        text(
            "SELECT user_id, value FROM user_attribute JOIN user_entity ON user_entity.id = user_id"
            " WHERE user_entity.realm_id <> 'r-master' ORDER BY 1"
        ),
        text(
            "SELECT user_id, value FROM user_attribute JOIN user_entity ON user_entity.id = user_id"
            " WHERE user_entity.realm_id = 'r-2' ORDER BY 1"
        ),
    ),
    (
        text(
            "SELECT user_id, user_label FROM credential"
            " JOIN user_entity ON user_entity.id = user_id"
            " WHERE user_entity.realm_id <> 'r-master' ORDER BY 1"
        ),
        text(
            "SELECT user_id, user_label FROM credential"
            " JOIN user_entity ON user_entity.id = user_id"
            " WHERE user_entity.realm_id = 'r-2' ORDER BY 1"
        ),
    ),
    (
        text("SELECT realm_id, details_json FROM event_entity ORDER BY 1"),
        text("SELECT realm_id, details_json FROM event_entity WHERE realm_id = 'r-2' ORDER BY 1"),
    ),
    (
        text("SELECT realm_id, representation FROM admin_event_entity ORDER BY 1"),
        text(
            "SELECT realm_id, representation FROM admin_event_entity WHERE realm_id = 'r-2'"
            " ORDER BY 1"
        ),
    ),
)
# What the anonymisation changes in Waterfall; the rest stays as it was.
CHANGED = ("public.user_account", "public.audit_entry", "public.identity_sync_report")

type Person = tuple[str, str, str]


@pytest.fixture
def provider(database_url: str) -> Iterator[Engine]:
    """Give a database that stands for the identity provider's, the realm and another one."""
    with scratch_database(database_url, "waterfall_test_provider") as engine:
        with engine.begin() as connection:
            for statement in PROVIDER_TABLES:
                connection.execute(text(statement))
            connection.execute(
                text(
                    "INSERT INTO realm VALUES (:one, :name), (:other, 'other'), (:master, 'master')"
                ),
                {"one": THE_REALM, "other": OTHER_REALM, "master": MASTER, "name": REALM},
            )
        yield engine


@pytest.fixture
def copy(witness: Database, owner: Engine, provider: Engine) -> list[Person]:
    """Name the persons of the copy in both databases; give every name and address it holds.

    Two of them administer the installation: the administrator its bootstrap created, and a
    person of the directory, with an avatar.
    """
    administration = role(witness, "Administration", permissions=ADMINISTRATION)
    with owner.begin() as connection:
        accounts = _persons(connection)
        _administrators(connection, administration)
        _journal(connection, accounts)
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
            _provider_person(connection, THE_REALM, person, subject)
        _provider_person(connection, THE_REALM, LEFT)
        _provider_person(connection, OTHER_REALM, ELSEWHERE)
        for last, first, email, username in ADMINISTERING:
            _provider_person(connection, MASTER, (last, first, email), username=username)
        for realm in (THE_REALM, OTHER_REALM, MASTER):
            _mail_server(connection, realm)
        connection.execute(
            text(
                "INSERT INTO user_entity VALUES ('service', :realm, 'service-account-api', NULL,"
                " 'service', false, NULL, NULL, true, NULL, 'client-api')"
            ),
            {"realm": THE_REALM},
        )
        for realm in (THE_REALM, OTHER_REALM):
            _outside(connection, realm)
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


def _administrators(connection: Connection, administration: UUID) -> None:
    """Add the administrators of the copy, holding ``administration``: the bootstrap's first."""
    installed_at = connection.execute(
        select(Installation.installed_at).where(Installation.id == THE_ROW)
    ).scalar_one()
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


def _journal(connection: Connection, accounts: list[UUID]) -> None:
    """Inscribe the first person as the author of a change of each person, herself included."""
    with _session(connection) as session, logging_context(correlation_id=CORRELATION):
        author = AuditActor(accounts[0], f"{PERSONS[0][1]} {PERSONS[0][0]}")
        for audited, (last_name, first_name, _) in zip(accounts, PERSONS, strict=True):
            changed = AuditObject("user", audited, f"{first_name} {last_name}")
            record(session, Inscription("user_update", author, changed, AT))
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
    with _session(connection) as session:
        person = SkippedPerson("kc-left", LEFT[0], LEFT[1], LEFT[2], "EMAIL_MISSING")
        skipped: list[Skipped] = [person, ACCOUNT_LEFT]
        record_report(session, SyncReport(task_id, AT, 1, 2, 3, 4, skipped, [REMOVED]))
        session.commit()


def _session(connection: Connection) -> Session:
    """Give a session that writes in the transaction of ``connection``, as the owner."""
    return Session(bind=connection, join_transaction_mode="create_savepoint")


def _mail_server(connection: Connection, realm: str) -> None:
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


def _provider_person(
    connection: Connection,
    realm: str,
    person: Person,
    subject: str | None = None,
    username: str | None = None,
) -> None:
    """Add a person to a realm, an attribute, a credential, and the events that name her.

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


def _anonymize(
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


def _needles(copy: list[Person]) -> set[str]:
    """Every name, first name and address of the source, and the names the journal shows."""
    named = [*copy, LEFT]
    return {
        *(part for person in named for part in person),
        *(f"{first} {last}" for last, first, _ in named),
        REMOVED,
    }


def _rows(connection: Connection, query: TextClause) -> list[tuple[object, ...]]:
    """Give the rows of a query of the stand-in, as tuples."""
    return [tuple(row) for row in connection.execute(query)]


@pytest.mark.requirement("WF-EXP-0010-A")
@pytest.mark.story("US-2960")
def test_after_the_anonymisation_no_address_and_no_name_of_the_source_is_found_in_either_base(
    copy: list[Person],
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Aucun environnement hors production ne contient une adresse électronique réelle, hors
    # l'environnement isolé du test de restauration. » : for a copy of the production, by its
    # anonymisation. Proper to US-2960: « après l'anonymisation, une recherche des adresses et des
    # noms de la source dans les deux bases ne trouve rien ». The search reads every column of text
    # or of JSON of every table of each base, and finds them before, wherever they were copied.
    # The administrators stay active, lest nobody enter the copy (WF-ADM-0120, #4068): they are
    # found nowhere either, by their names nor by their addresses.
    with Session(owner) as session:
        held = administrators(session)
    assert held
    needles = _needles(copy)
    assert {
        "public.user_account.last_name",
        "public.user_account.first_name",
        "public.user_account.email",
        "public.audit_entry.actor_display_name",
        "public.audit_entry.object_label",
        "public.identity_sync_report.skipped",
        "public.identity_sync_report.removed",
    } <= set(found(owner, needles))
    assert set(found(provider, needles)) == {
        "public.user_entity.username",
        "public.user_entity.email",
        "public.user_entity.email_constraint",
        "public.user_entity.first_name",
        "public.user_entity.last_name",
        "public.user_attribute.value",
        "public.credential.user_label",
        "public.event_entity.details_json",
        "public.admin_event_entity.representation",
    }
    assert _anonymize(monkeypatch, database_url, provider) == 0
    assert found(owner, needles) == {}
    assert found(provider, needles) == {}
    with Session(owner) as session:
        assert administrators(session) == held


@pytest.mark.story("US-2960")
def test_every_account_is_anonymised_and_the_journal_forgets_them_the_rest_kept(
    copy: list[Person],
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960: « les noms, les prénoms, les adresses électroniques et les avatars des
    # comptes sont remplacés, dans la base de Waterfall, journal d'audit compris […] ; les montants,
    # les projets et les dates restent ». Every other table holds what it held, row for row, and
    # the journal its inscriptions, their labels of accounts but made null. The administrators
    # stay active, under an identity in the reserved domain, local, their sessions closed
    # (WF-ADM-0120, #4068); every other account is anonymised and deactivated.
    kept = held_by_table(owner, but=CHANGED)
    with owner.connect() as connection:
        journal = _journal_but_labels(connection)
        anonymised_before = set(
            connection.execute(
                select(UserAccount.id, UserAccount.anonymized_at).where(
                    UserAccount.anonymized_at.is_not(None)
                )
            ).all()
        )
    with Session(owner) as session:
        held = administrators(session)
    assert len(copy) > len(PERSONS)
    assert _anonymize(monkeypatch, database_url, provider) == 0
    assert held_by_table(owner, but=CHANGED) == kept
    with Session(owner) as session:
        accounts = session.scalars(select(UserAccount)).all()
        assert len(accounts) == len(copy) + len(anonymised_before)
        others = [account for account in accounts if account.id not in held]
        assert {
            (account.last_name, account.first_name, account.email, account.avatar)
            for account in others
        } == {(None, None, None, None)}
        assert {(account.state, account.avatar_media_type) for account in others} == {
            ("deactivated", None)
        }
        administering = sorted(
            (account for account in accounts if account.id in held), key=lambda each: each.id
        )
        assert [
            (each.first_name, each.last_name, each.email, each.avatar, each.state, each.origin)
            for each in administering
        ] == [
            (
                "Administrator",
                str(rank),
                f"administrator-{each.id}@waterfall.test",
                None,
                "active",
                "local",
            )
            for rank, each in enumerate(administering, start=1)
        ]
        assert all(each.anonymized_at is None for each in administering)
        # An account anonymised before keeps its date; the others are closed as of the run.
        assert anonymised_before <= {(each.id, each.anonymized_at) for each in accounts}
        before = {user_id for user_id, _ in anonymised_before}
        now = [account for account in others if account.id not in before]
        assert len(now) + len(administering) == len(copy)
        assert all(account.sessions_closed_at == account.anonymized_at for account in now)
        closed = {account.sessions_closed_at for account in now}
        assert {each.sessions_closed_at for each in administering} == closed
        named = session.scalars(
            select(AuditEntry.id).where(
                or_(
                    AuditEntry.actor_display_name.is_not(None),
                    (AuditEntry.object_kind == "user") & AuditEntry.object_label.is_not(None),
                )
            )
        ).all()
        assert named == []
        # The report keeps its counts and what names no person; the person left and the address
        # removed go.
        report = latest_report(session)
        assert report is not None
        assert (report.created, report.updated, report.deactivated, report.restored) == (1, 2, 3, 4)
        assert (report.skipped, report.removed) == ([ACCOUNT_LEFT], [])
    with owner.connect() as connection:
        assert _journal_but_labels(connection) == journal


def _journal_but_labels(connection: Connection) -> list[tuple[object, ...]]:
    """Give the inscriptions of the journal, but the labels the anonymisation forgets."""
    columns = [
        column
        for column in AuditEntry.__table__.columns
        if column.name not in {"actor_display_name", "object_label"}
    ]
    return [tuple(row) for row in connection.execute(select(*columns).order_by(AuditEntry.id))]


@pytest.mark.story("US-2960")
def test_the_provider_keeps_its_persons_by_their_subject_and_nothing_else_names_them(
    copy: list[Person],
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960: in the base of the identity provider, a person keeps her identifier — the
    # subject Waterfall knows her by —, which becomes her user name; she is disabled, tied to no
    # directory, and nothing else of the realm names her. An administrator Waterfall keeps is given
    # the identity Waterfall gave it, its address as its user name, and stays enabled, without a
    # password (#4068). The account of service of a client, and the persons of another realm, are
    # left as they were.
    with provider.connect() as connection:
        others = _rows(connection, OTHERS)
        subjects = [row[0] for row in _rows(connection, PERSONS_OF_THE_REALM)]
        elsewhere = [_rows(connection, of_the_other) for _, of_the_other in HELD]
    assert len(subjects) == len(copy) + 1
    assert all(elsewhere)
    assert _anonymize(monkeypatch, database_url, provider) == 0
    with Session(owner) as session:
        held = administrators(session)
        kept = {
            account.idp_subject: (
                account.idp_subject,
                account.email,
                account.email,
                account.email,
                True,
                account.first_name,
                account.last_name,
                True,
                None,
            )
            for account in session.scalars(select(UserAccount).where(UserAccount.id.in_(held)))
        }
    assert kept
    anonymised = {
        subject: (subject, subject, None, subject, False, None, None, False, None)
        for subject in subjects
    }
    with provider.connect() as connection:
        assert _rows(connection, OTHERS) == others
        assert _rows(connection, PERSONS_OF_THE_REALM) == [
            (anonymised | kept)[subject] for subject in subjects
        ]
        assert [_rows(connection, every) for every, _ in HELD] == elsewhere


@pytest.mark.story("US-2960")
def test_run_again_it_changes_nothing_more_and_succeeds(
    copy: list[Person],
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960: a run that failed halfway is run again; one that succeeded changes
    # nothing more, the dates of the anonymisation included.
    assert copy
    assert _anonymize(monkeypatch, database_url, provider) == 0
    first = (held_by_table(owner), held_by_table(provider))
    assert _anonymize(monkeypatch, database_url, provider) == 0
    assert (held_by_table(owner), held_by_table(provider)) == first


@pytest.mark.story("US-2960")
def test_a_realm_the_provider_does_not_hold_stops_it_before_anything_changes(
    copy: list[Person],
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960: a realm misnamed in the settings would leave the persons of the provider
    # named: the command stops, and changes nothing in either base.
    assert copy
    before = (held_by_table(owner), held_by_table(provider))
    assert _anonymize(monkeypatch, database_url, provider, realm="misnamed") == 1
    assert (held_by_table(owner), held_by_table(provider)) == before


@pytest.mark.story("US-2960")
def test_the_realm_is_cut_off_from_its_directory_and_its_external_providers(
    copy: list[Person],
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960: opened, the copy would read the directory of the production again — its
    # persons imported anew, by the account it binds as — or sign in through its provider. The
    # federation of the realm goes, its mapper and its settings with it, and its external provider
    # with its own; the provider of its keys stays, and another realm is left as it was.
    assert copy
    with provider.connect() as connection:
        of_the_realm = [_rows_of(connection, query, THE_REALM) for query in OUTSIDE]
        elsewhere = [_rows_of(connection, query, OTHER_REALM) for query in OUTSIDE]
    assert {DIRECTORY, BINDING} <= {row[-1] for row in of_the_realm[0]}
    assert all(of_the_realm[1:])
    assert _anonymize(monkeypatch, database_url, provider) == 0
    with provider.connect() as connection:
        assert [_rows_of(connection, query, THE_REALM) for query in OUTSIDE] == [
            [(THE_REALM, "rsa", KEYS, "priority", "100")],
            [],
            [],
        ]
        assert [_rows_of(connection, query, OTHER_REALM) for query in OUTSIDE] == elsewhere


def _rows_of(connection: Connection, query: TextClause, realm: str) -> list[tuple[object, ...]]:
    """Give the rows of a query of the stand-in about one realm, as tuples."""
    return [tuple(row) for row in connection.execute(query, {"realm": realm})]


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("copy")
@pytest.mark.parametrize("arguments", [(), ("--yes",), (anonymization.CONFIRMATION, "--again")])
def test_unless_told_the_databases_are_a_copy_it_changes_nothing(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
) -> None:
    # Proper to US-2960: the service of the restoration holds the databases of the production too;
    # run there by mistake, the command would anonymise the production for good. It changes
    # nothing unless told, in so many words, that they are a copy's (2).
    before = (held_by_table(owner), held_by_table(provider))
    assert _anonymize(monkeypatch, database_url, provider, arguments=arguments) == 2
    assert (held_by_table(owner), held_by_table(provider)) == before


@pytest.mark.story("US-2960")
def test_unless_told_the_databases_are_a_copy_it_says_how_to_tell_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960: refused, the command says the argument that tells it, before it reads
    # any setting.
    assert restore_main.main([anonymization.COMMAND]) == 2
    assert anonymization.CONFIRMATION in capsys.readouterr().err


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("copy")
def test_the_realm_of_the_administration_of_keycloak_is_refused(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960: ``master`` holds the administrators of Keycloak, no installation's
    # persons; disabling them would leave Keycloak without a way to be administered. Named in the
    # settings, it stops the command at start, nothing changed (2).
    before = (held_by_table(owner), held_by_table(provider))
    assert _anonymize(monkeypatch, database_url, provider, realm="master") == 2
    assert "WATERFALL_KEYCLOAK_REALM: " in capsys.readouterr().err
    assert (held_by_table(owner), held_by_table(provider)) == before


MASTER_PERSONS = text(
    "SELECT username, email, email_constraint, first_name, last_name, enabled FROM user_entity"
    " WHERE realm_id = 'r-master' ORDER BY id"
)
MASTER_NAMES = text("SELECT id, username FROM user_entity WHERE realm_id = 'r-master' ORDER BY id")
MASTER_CREDENTIALS = text(
    "SELECT credential.* FROM credential JOIN user_entity ON user_entity.id = user_id"
    " WHERE user_entity.realm_id = 'r-master' ORDER BY credential.id"
)
MASTER_EVENTS = text(
    "SELECT (SELECT count(*) FROM event_entity WHERE realm_id = 'r-master'),"
    " (SELECT count(*) FROM admin_event_entity WHERE realm_id = 'r-master')"
)


@pytest.mark.requirement("WF-EXP-0010-A")
@pytest.mark.story("US-2960")
def test_the_administrators_of_keycloak_keep_no_address_and_no_name_of_the_source(
    copy: list[Person],
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # « Aucun environnement hors production ne contient une adresse électronique réelle, hors
    # l'environnement isolé du test de restauration. » : the realm ``master`` of the copy, which
    # administers Keycloak, holds the addresses of its administrators, and its events copy them
    # (#5048). They lose their names and their addresses — the user name that is an address too —,
    # and their events go; their credentials stay, and a user name that is no address, which
    # ``keycloak-realm`` gives the password of the environment back by.
    assert copy
    addresses = {email for _, _, email, _ in ADMINISTERING}
    assert {
        "public.user_entity.username",
        "public.user_entity.email",
        "public.user_entity.email_constraint",
        "public.event_entity.details_json",
    } <= set(found(provider, addresses))
    with provider.connect() as connection:
        named = [
            (str(subject), str(username)) for subject, username in connection.execute(MASTER_NAMES)
        ]
        credentials = _rows(connection, MASTER_CREDENTIALS)
    assert sorted(username for _, username in named) == sorted(
        username for *_, username in ADMINISTERING
    )
    assert len(credentials) == len(ADMINISTERING)
    assert _anonymize(monkeypatch, database_url, provider) == 0
    assert found(provider, addresses) == {}
    with provider.connect() as connection:
        assert _rows(connection, MASTER_PERSONS) == [
            (subject if "@" in username else username, None, subject, None, None, True)
            for subject, username in named
        ]
        assert connection.execute(MASTER_EVENTS).one() == (0, 0)
        assert _rows(connection, MASTER_CREDENTIALS) == credentials


@pytest.mark.story("US-2960")
def test_no_realm_keeps_its_mail_server_nor_its_listeners_of_events(
    copy: list[Person],
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960 (#5048): opened, a copy that kept the mail server of the production would
    # send real mails by its relay, with its account. Every realm loses its mail server and its
    # listeners of events, the one that mails among them; the relay is found nowhere after.
    assert copy
    with provider.connect() as connection:
        assert all(_rows(connection, query) for query in SILENCED)
    assert set(found(provider, {RELAY})) == {"public.realm_smtp_config.value"}
    assert _anonymize(monkeypatch, database_url, provider) == 0
    with provider.connect() as connection:
        assert [_rows(connection, query) for query in SILENCED] == [[], []]
    assert found(provider, {RELAY}) == {}


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("copy")
def test_the_command_writes_the_administrators_it_keeps_and_where_their_link_is_had(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960 (#4068): nothing is mailed to the administrators kept, whose addresses
    # reach nobody; the command writes their addresses for the operator, the installation
    # administrator's with the command that writes its link, the bootstrap's (WF-EXP-0020).
    capsys.readouterr()
    assert _anonymize(monkeypatch, database_url, provider) == 0
    lines = capsys.readouterr().out.splitlines()
    with Session(owner) as session:
        held = administrators(session)
        addresses = dict(
            session.execute(
                select(UserAccount.id, UserAccount.email).where(UserAccount.id.in_(held))
            ).all()
        )
        installation = session.get(Installation, THE_ROW)
        assert installation is not None
        installer = read_installation_administrator(session, installation.installed_at)
    assert installer is not None
    assert installer.user_id in held
    assert lines[0].startswith(f"waterfall-restore {anonymization.COMMAND}: ")
    assert sorted(lines[1:]) == sorted(
        f"{email}{anonymization.INSTALLATION_NOTE if user_id == installer.user_id else ''}"
        for user_id, email in addresses.items()
    )


@pytest.fixture(params=["deactivated", "without_role"])
def installer_not_kept(request: pytest.FixtureRequest, copy: list[Person], owner: Engine) -> None:
    """Take from the installation administrator of the copy its activity, or its roles."""
    assert copy
    with owner.begin() as connection:
        installed_at = connection.execute(
            select(Installation.installed_at).where(Installation.id == THE_ROW)
        ).scalar_one()
        with _session(connection) as session:
            installer = read_installation_administrator(session, installed_at)
        assert installer is not None
        if request.param == "deactivated":
            connection.execute(
                update(UserAccount)
                .where(UserAccount.id == installer.user_id)
                .values(state="deactivated")
            )
        else:
            connection.execute(
                delete(UserAccessRole).where(UserAccessRole.user_account_id == installer.user_id)
            )
    with Session(owner) as session:
        held = administrators(session)
    assert held
    assert installer.user_id not in held


@pytest.mark.story("US-2960")
@pytest.mark.usefixtures("installer_not_kept")
def test_an_installation_administrator_the_copy_would_not_keep_stops_it_before_anything_changes(
    owner: Engine,
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Proper to US-2960 (#4068): an installation administrator deactivated, or without its roles,
    # in the backup would be anonymised, which the bootstrap refuses; the others kept would have
    # no link, and nobody would enter the copy. Another administrator active, the command stops
    # before it writes anything in either base, and says why and what to do.
    before = (held_by_table(owner), held_by_table(provider))
    capsys.readouterr()
    assert _anonymize(monkeypatch, database_url, provider) == 1
    error = capsys.readouterr().err
    assert "installation administrator" in error
    assert "restore a backup where it holds them" in error
    assert (held_by_table(owner), held_by_table(provider)) == before


@pytest.mark.story("US-2960")
def test_without_its_databases_the_command_stops_naming_them(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proper to US-2960: a setting that lacks stops it at start, named, rather than anonymise one
    # base and not the other.
    monkeypatch.delenv("WATERFALL_DATABASE_URL", raising=False)
    monkeypatch.delenv("WATERFALL_KEYCLOAK_DATABASE_URL", raising=False)
    assert restore_main.main([anonymization.COMMAND, anonymization.CONFIRMATION]) == 2
    error = capsys.readouterr().err
    assert "WATERFALL_DATABASE_URL: is missing" in error
    assert "WATERFALL_KEYCLOAK_DATABASE_URL: is missing" in error
