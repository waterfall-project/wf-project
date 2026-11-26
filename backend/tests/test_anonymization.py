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
from anonymization_support import found, held_by_table
from migrations_support import scratch_database
from sqlalchemy import insert, or_, select, text
from sqlalchemy.orm import Session
from support import raw_account

from waterfall.core.users.interface import (
    Skipped,
    SkippedAccount,
    SkippedPerson,
    SyncReport,
    latest_report,
    record_report,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditActor, AuditEntry, AuditObject, Inscription, record
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
)
THE_REALM, OTHER_REALM = "r-1", "r-2"
PERSONS_OF_THE_REALM = text(
    "SELECT id, username, email, email_constraint, email_verified, first_name, last_name,"
    " enabled, federation_link FROM user_entity"
    " WHERE realm_id = 'r-1' AND service_account_client_link IS NULL ORDER BY id"
)
OTHERS = text(
    "SELECT * FROM user_entity WHERE realm_id = 'r-2' OR service_account_client_link IS NOT NULL"
    " ORDER BY id"
)
# What the stand-in holds of a person besides her account, then the same of the other realm alone.
HELD = (
    (
        text("SELECT user_id, value FROM user_attribute ORDER BY 1"),
        text(
            "SELECT user_id, value FROM user_attribute JOIN user_entity ON user_entity.id = user_id"
            " WHERE user_entity.realm_id = 'r-2' ORDER BY 1"
        ),
    ),
    (
        text("SELECT user_id, user_label FROM credential ORDER BY 1"),
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
                text("INSERT INTO realm VALUES (:one, :name), (:other, 'other')"),
                {"one": THE_REALM, "other": OTHER_REALM, "name": REALM},
            )
        yield engine


@pytest.fixture
def copy(witness: Database, owner: Engine, provider: Engine) -> list[Person]:
    """Name the persons of the copy in both databases; give every name and address it holds."""
    assert witness
    with owner.begin() as connection:
        accounts = _persons(connection)
        _journal(connection, accounts)
        _report(connection)
        named = connection.execute(
            select(UserAccount.last_name, UserAccount.first_name, UserAccount.email).where(
                UserAccount.anonymized_at.is_(None)
            )
        ).all()
    copied = [(str(last), str(first), str(email)) for last, first, email in named]
    with provider.begin() as connection:
        for person in [*copied, LEFT]:
            _provider_person(connection, THE_REALM, person)
        _provider_person(connection, OTHER_REALM, ELSEWHERE)
        connection.execute(
            text(
                "INSERT INTO user_entity VALUES ('service', :realm, 'service-account-api', NULL,"
                " 'service', false, NULL, NULL, true, NULL, 'client-api')"
            ),
            {"realm": THE_REALM},
        )
    return copied


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


def _provider_person(connection: Connection, realm: str, person: Person) -> None:
    """Add a person to a realm, an attribute, a credential, and the events that name her."""
    last_name, first_name, email = person
    subject = str(uuid4())
    connection.execute(
        text(
            "INSERT INTO user_entity VALUES (:id, :realm, :username, :email, :email, true,"
            " :first_name, :last_name, true, 'ldap', NULL)"
        ),
        {
            "id": subject,
            "realm": realm,
            "username": email.partition("@")[0],
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
    monkeypatch: pytest.MonkeyPatch, database_url: str, provider: Engine, realm: str = REALM
) -> int:
    """Run the command on the two databases, as the operator does."""
    monkeypatch.setenv("WATERFALL_DATABASE_URL", database_url)
    url = provider.url.render_as_string(hide_password=False)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_DATABASE_URL", url)
    monkeypatch.setenv("WATERFALL_KEYCLOAK_REALM", realm)
    return restore_main.main([anonymization.COMMAND])


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
    # the journal its inscriptions, their labels of accounts but made null.
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
    assert len(copy) > len(PERSONS)
    assert _anonymize(monkeypatch, database_url, provider) == 0
    assert held_by_table(owner, but=CHANGED) == kept
    with Session(owner) as session:
        accounts = session.scalars(select(UserAccount)).all()
        assert len(accounts) == len(copy) + len(anonymised_before)
        assert {
            (account.last_name, account.first_name, account.email, account.avatar)
            for account in accounts
        } == {(None, None, None, None)}
        assert {(account.state, account.avatar_media_type) for account in accounts} == {
            ("deactivated", None)
        }
        # An account anonymised before keeps its date; the others are closed as of the run.
        assert anonymised_before <= {(each.id, each.anonymized_at) for each in accounts}
        before = {user_id for user_id, _ in anonymised_before}
        now = [account for account in accounts if account.id not in before]
        assert len(now) == len(copy)
        assert all(account.sessions_closed_at == account.anonymized_at for account in now)
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
    database_url: str,
    provider: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Proper to US-2960: in the base of the identity provider, a person keeps her identifier — the
    # subject Waterfall knows her by —, which becomes her user name; she is disabled, tied to no
    # directory, and nothing else of the realm names her. The account of service of a client, and
    # the persons of another realm, are left as they were.
    with provider.connect() as connection:
        others = _rows(connection, OTHERS)
        subjects = [row[0] for row in _rows(connection, PERSONS_OF_THE_REALM)]
        elsewhere = [_rows(connection, of_the_other) for _, of_the_other in HELD]
    assert len(subjects) == len(copy) + 1
    assert all(elsewhere)
    assert _anonymize(monkeypatch, database_url, provider) == 0
    with provider.connect() as connection:
        assert _rows(connection, OTHERS) == others
        assert _rows(connection, PERSONS_OF_THE_REALM) == [
            (subject, subject, None, subject, False, None, None, False, None)
            for subject in subjects
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
def test_without_its_databases_the_command_stops_naming_them(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proper to US-2960: a setting that lacks stops it at start, named, rather than anonymise one
    # base and not the other.
    monkeypatch.delenv("WATERFALL_DATABASE_URL", raising=False)
    monkeypatch.delenv("WATERFALL_KEYCLOAK_DATABASE_URL", raising=False)
    assert restore_main.main([anonymization.COMMAND]) == 2
    error = capsys.readouterr().err
    assert "WATERFALL_DATABASE_URL: is missing" in error
    assert "WATERFALL_KEYCLOAK_DATABASE_URL: is missing" in error
