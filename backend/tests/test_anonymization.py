# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The anonymisation of a copy of the production, ``waterfall-restore anonymize`` (US-2960).

What the command replaces and keeps, in both databases, on the copy of ``anonymization_copy``; its
refusals are those of ``test_anonymization_refusals.py``, and the tables of the real Keycloak those
of ``test_keycloak_anonymization.py``.
"""

from typing import TYPE_CHECKING

import pytest
from anonymization_copy import (
    ACCOUNT_LEFT,
    ADMINISTERING,
    ADMINISTRATORS,
    BINDING,
    CHANGED,
    DIRECTORY,
    HELD,
    KEYS,
    OTHERS,
    OUTSIDE,
    PERSONS,
    PERSONS_OF_THE_REALM,
    REALM,
    RELAY,
    SILENCED,
    THE_REALM,
    Person,
    anonymize_copy,
    name_copy,
    rows,
    source_needles,
    stand_in,
)
from anonymization_support import found, held_by_table
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from waterfall.core.access_roles.interface import administrators
from waterfall.core.users.interface import latest_report, read_installation_administrator
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import ACCOUNT_KINDS, AuditEntry
from waterfall.platform.installation import THE_ROW, Installation
from waterfall.restore import anonymization

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Connection, Engine, TextClause

    from waterfall.platform.database import Database


@pytest.fixture
def provider(database_url: str) -> Iterator[Engine]:
    """Give a database that stands for the identity provider's, the realm and ``master``."""
    with stand_in(database_url) as engine:
        yield engine


@pytest.fixture
def copy(witness: Database, owner: Engine, provider: Engine) -> list[Person]:
    """Name the persons of the copy in both databases; give every name and address it holds."""
    return name_copy(witness, owner, provider)


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
    # found nowhere either, by their names nor by their addresses — in the journal, which names
    # them as authors and as objects, neither, though they are not anonymised (#4068, 0057).
    with Session(owner) as session:
        held = administrators(session)
    assert held
    kept = {f"{first} {last}" for last, first, _ in ADMINISTRATORS}
    assert set(found(owner, kept)) >= {
        "public.audit_entry.actor_display_name",
        "public.audit_entry.object_label",
    }
    needles = source_needles(copy)
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
        "public.federated_identity.federated_username",
        "public.offline_user_session.data",
        "public.event_entity.details_json",
        "public.admin_event_entity.representation",
    }
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
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
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
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
                    AuditEntry.object_kind.in_(ACCOUNT_KINDS)
                    & AuditEntry.object_label.is_not(None),
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
    # password (#4068). The account of service of a client is left as it was. In both realms, the
    # attributes, the links to an external provider, the sessions and the events go, and the
    # credentials of the realm of the installation (#5087).
    with provider.connect() as connection:
        others = rows(connection, OTHERS)
        subjects = [row[0] for row in rows(connection, PERSONS_OF_THE_REALM)]
        assert all(rows(connection, every) for every in HELD)
    assert len(subjects) == len(copy) + 1
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
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
        assert rows(connection, OTHERS) == others
        assert rows(connection, PERSONS_OF_THE_REALM) == [
            (anonymised | kept)[subject] for subject in subjects
        ]
        assert [rows(connection, every) for every in HELD] == [[]] * len(HELD)


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
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
    first = (held_by_table(owner), held_by_table(provider))
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
    assert (held_by_table(owner), held_by_table(provider)) == first


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
    # with its own; the provider of its keys stays.
    assert copy
    with provider.connect() as connection:
        of_the_realm = [_rows_of(connection, query, THE_REALM) for query in OUTSIDE]
    assert {DIRECTORY, BINDING} <= {row[-1] for row in of_the_realm[0]}
    assert all(of_the_realm[1:])
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
    with provider.connect() as connection:
        assert [_rows_of(connection, query, THE_REALM) for query in OUTSIDE] == [
            [(THE_REALM, "rsa", KEYS, "priority", "100")],
            [],
            [],
        ]


def _rows_of(connection: Connection, query: TextClause, realm: str) -> list[tuple[object, ...]]:
    """Give the rows of a query of the stand-in about one realm, as tuples."""
    return [tuple(row) for row in connection.execute(query, {"realm": realm})]


MASTER_PERSONS = text(
    "SELECT username, email, email_constraint, first_name, last_name, enabled FROM user_entity"
    " WHERE realm_id = 'r-master' ORDER BY id"
)
MASTER_NAMES = text("SELECT id, username FROM user_entity WHERE realm_id = 'r-master' ORDER BY id")
MASTER_CREDENTIALS = text(
    "SELECT credential.id, credential.user_id, credential.user_label FROM credential"
    " JOIN user_entity ON user_entity.id = user_id"
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
    # their attributes, their links to an external provider, their sessions and the labels of their
    # credentials, and their events go (#5087); their credentials stay, and a user name that is no
    # address, which ``keycloak-realm`` gives the password of the environment back by. Neither
    # their names nor their addresses are found anywhere in the base after.
    assert copy
    needles = {part for *person, _ in ADMINISTERING for part in person}
    assert {
        "public.user_entity.username",
        "public.user_entity.email",
        "public.user_entity.email_constraint",
        "public.user_entity.first_name",
        "public.user_entity.last_name",
        "public.user_attribute.value",
        "public.credential.user_label",
        "public.federated_identity.federated_username",
        "public.offline_user_session.data",
        "public.event_entity.details_json",
        "public.admin_event_entity.representation",
    } <= set(found(provider, needles))
    with provider.connect() as connection:
        named = [
            (str(subject), str(username)) for subject, username in connection.execute(MASTER_NAMES)
        ]
        credentials = rows(connection, MASTER_CREDENTIALS)
    assert sorted(username for _, username in named) == sorted(
        username for *_, username in ADMINISTERING
    )
    assert len(credentials) == len(ADMINISTERING)
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
    assert found(provider, needles) == {}
    with provider.connect() as connection:
        assert rows(connection, MASTER_PERSONS) == [
            (subject if "@" in username else username, None, subject, None, None, True)
            for subject, username in named
        ]
        assert connection.execute(MASTER_EVENTS).one() == (0, 0)
        assert rows(connection, MASTER_CREDENTIALS) == [
            (identifier, user_id, None) for identifier, user_id, _ in credentials
        ]


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
        assert all(rows(connection, query) for query in SILENCED)
    assert set(found(provider, {RELAY})) == {"public.realm_smtp_config.value"}
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
    with provider.connect() as connection:
        assert [rows(connection, query) for query in SILENCED] == [[], []]
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
    assert anonymize_copy(monkeypatch, database_url, provider) == 0
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
    assert sorted(lines[1:-1]) == sorted(
        f"{email}{anonymization.INSTALLATION_NOTE if user_id == installer.user_id else ''}"
        for user_id, email in addresses.items()
    )
    assert lines[-1] == (
        f"waterfall-restore {anonymization.COMMAND}: {len(held)} of {len(held)} administrators "
        f"kept updated in the realm {REALM} of Keycloak"
    )
