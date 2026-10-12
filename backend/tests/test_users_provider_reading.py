# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the accounts of the provider, as the module of the accounts writes it.

What the provider holds of a person is followed, by the platform, on the accounts it holds; one it
no longer holds is deactivated; a local account is left as Waterfall holds it, the provider given
back its identity if it holds another (WF-ADM-0070, #919). What the reading leaves is reported, an
account of Waterfall by its identifier alone (#918, #920). What the worker asks of Keycloak is tried
against the platform (``test_keycloak_identity_sync.py``); its writes are tried here, under the
correlation of a task, with a change of roles at once.
"""

import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from access_rows import ADMINISTRATION, role
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from support import raw_account, wait_for_a_lock

from waterfall.core.access_roles.interface import Act, roles_held_by, set_access_roles
from waterfall.core.users.interface import (
    HeldAccount,
    NotAdmitted,
    NotFollowed,
    SkippedAccount,
    SkippedAddressHeld,
    SkippedPerson,
    SyncReport,
    deactivate_unheld,
    follow,
    identity_to_restore,
    known_subjects,
    latest_report,
    record_report,
    unheld_accounts,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.database import Database
from waterfall.platform.keycloak_admin import LocalIdentity, ProviderAccount
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import BackgroundTask
from waterfall.worker import identity_sync
from waterfall.worker.identity_sync import Written, write_accounts

NOON = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
CORRELATION = "reading-of-the-accounts"


@pytest.fixture(autouse=True)
def correlation() -> Iterator[None]:
    """Run the test under the correlation of a task, as a reading always is."""
    with logging_context(correlation_id=CORRELATION):
        yield


def held(session: Session, **overrides: Any) -> dict[str, Any]:
    """Write an account of the directory by hand, with the changes asked for."""
    row = raw_account(**{"origin": "directory", **overrides})
    session.execute(insert(UserAccount).values(**row))
    return row


def of_provider(row: dict[str, Any], **overrides: Any) -> ProviderAccount:
    """Describe the person of an account as the provider holds her, with the changes asked for."""
    fields: dict[str, Any] = {
        "subject": row["idp_subject"],
        "last_name": row["last_name"],
        "first_name": row["first_name"],
        "email": row["email"],
        "is_federated": True,
        "is_relayed": False,
        **overrides,
    }
    return ProviderAccount(**fields)


def journal(session: Session) -> list[tuple[Any, ...]]:
    """Read the inscriptions: action, author, object, data."""
    return [
        tuple(each)
        for each in session.execute(
            select(
                AuditEntry.action, AuditEntry.actor_user_id, AuditEntry.object_id, AuditEntry.params
            ).order_by(AuditEntry.id)
        )
    ]


@pytest.mark.requirement("WF-DAT-0070-A")
def test_an_account_the_reading_updates_carries_the_platform_as_its_author(
    session: Session,
) -> None:
    # « Une ligne mise à jour par un traitement automatique porte la plateforme comme auteur. »
    author = held(session, email="administrator@example.org")
    row = held(session, created_by=author["id"], updated_by=author["id"])
    changed = of_provider(row, last_name="Martin-Dupont", email="claire.dupont@example.org")
    assert follow(session, changed, NOON) == "updated"
    stored = session.get_one(UserAccount, row["id"])
    assert (stored.updated_by, stored.updated_at, stored.created_by) == (None, NOON, author["id"])
    assert (stored.last_name, stored.email, stored.lock_version) == (
        "Martin-Dupont",
        "claire.dupont@example.org",
        1,
    )
    assert journal(session) == [
        ("user_update", None, row["id"], {"fields": ["last_name", "email"]})
    ]


def test_an_account_the_provider_holds_as_it_was_is_left_unwritten(session: Session) -> None:
    row = held(session)
    assert follow(session, of_provider(row), NOON) == "unchanged"
    assert session.get_one(UserAccount, row["id"]).lock_version == 0
    assert journal(session) == []


@pytest.mark.parametrize(
    "otherwise",
    [{"last_name": "Autre"}, {"first_name": "Autre"}, {"email": "autre@example.org"}],
    ids=["name", "first name", "address"],
)
def test_a_local_account_the_provider_holds_otherwise_is_left_for_it_to_take_back(
    session: Session, otherwise: dict[str, str]
) -> None:
    # A local account is Waterfall's (WF-ADM-0050), whatever the realm holds of it: the reading
    # changes nothing of it, and tells the provider to take its identity back (#919).
    row = held(session, origin="local")
    assert follow(session, of_provider(row, **otherwise, is_federated=False), NOON) == "restored"
    stored = session.get_one(UserAccount, row["id"])
    assert (stored.last_name, stored.first_name, stored.email, stored.lock_version) == (
        "Martin",
        "Claire",
        "claire.martin@example.org",
        0,
    )
    assert journal(session) == []


def test_a_local_account_the_provider_holds_alike_or_anonymized_is_left_alone(
    session: Session,
) -> None:
    # The provider does not keep the case of an address; an anonymised account is out of it, and
    # never given an identity back (WF-ADM-0060).
    row = held(session, origin="local", email="Claire.Martin@Example.org")
    alike = of_provider(row, email="claire.martin@example.org", is_federated=False)
    assert follow(session, alike, NOON) == "unchanged"
    named = {"last_name": "Roux", "first_name": "Inès", "email": "ines.roux@example.org"}
    gone = held(session, **dict.fromkeys(named), anonymized_at=NOON, state="deactivated")
    assert follow(session, of_provider(gone, **named, is_federated=False), NOON) == "unchanged"


def test_the_identity_given_back_is_the_one_a_local_account_holds_when_it_is_read(
    session: Session,
) -> None:
    local = held(session, origin="local")
    assert identity_to_restore(session, local["idp_subject"]) == LocalIdentity(
        "Martin", "Claire", "claire.martin@example.org"
    )
    # An account anonymised since, one of the directory, or none: the provider is given nothing.
    named = dict.fromkeys(("last_name", "first_name", "email"))
    gone = held(session, origin="local", **named, anonymized_at=NOON, state="deactivated")
    federated = held(session, email="dominique@example.org")
    for subject in (gone["idp_subject"], federated["idp_subject"], "nobody"):
        assert identity_to_restore(session, subject) is None


def test_an_anonymized_account_is_neither_renamed_nor_created_again(session: Session) -> None:
    # Found by the subject its anonymisation keeps (WF-ADM-0070, WF-ADM-0060).
    named = {"last_name": "Annuaire", "first_name": "Dominique", "email": "d@x.org"}
    row = held(session, **dict.fromkeys(named), anonymized_at=NOON, state="deactivated")
    assert follow(session, of_provider(row, **named), NOON) == "unchanged"
    stored = session.get_one(UserAccount, row["id"])
    assert (stored.last_name, stored.email, stored.lock_version) == (None, None, 0)
    assert session.scalars(select(UserAccount.id).where(UserAccount.email == "d@x.org")).all() == []


@pytest.mark.parametrize(
    ("changed", "reason"),
    [
        ({"email": "taken@example.org"}, NotAdmitted.ADDRESS_TAKEN),
        ({"email": ""}, NotAdmitted.NO_ADDRESS),
        ({"first_name": ""}, NotAdmitted.NAME_NOT_STORABLE),
    ],
    ids=["address taken", "no address", "no first name"],
)
def test_an_identity_the_account_cannot_take_leaves_it_as_it_was(
    session: Session, changed: dict[str, str], reason: NotAdmitted
) -> None:
    held(session, email="TAKEN@example.org")
    row = held(session)
    assert follow(session, of_provider(row, **changed), NOON) == NotFollowed(reason, row["id"])
    stored = session.get_one(UserAccount, row["id"])
    assert (stored.email, stored.first_name, stored.lock_version) == (row["email"], "Claire", 0)
    assert journal(session) == []


def test_a_person_unknown_to_waterfall_is_created_without_any_role(session: Session) -> None:
    person = of_provider(raw_account(last_name="Annuaire", first_name="Dominique"))
    assert follow(session, person, NOON) == "created"
    assert follow(session, person, NOON) == "unchanged"
    local = of_provider(raw_account(email="l@x.org"), is_federated=False)
    assert follow(session, local, NOON) == NotFollowed(NotAdmitted.LOCAL_ACCOUNT, None)


def test_what_the_reading_leaves_is_reported_an_account_by_its_identifier_alone(
    database: Database,
) -> None:
    # A person without an address is named, by her subject and her names (#918); an account of
    # Waterfall is named by its identifier alone, none of its personal data copied — the one that
    # bears the address of a person left without an account too, with her subject (#920).
    with database.transaction() as session:
        renamed = held(session)
        gone = held(session, email="dominique.bernard@example.org")
    role(database, "Administration", permissions=ADMINISTRATION, holders=(gone["id"],))
    without_address = of_provider(raw_account(last_name="Garnier", first_name="Hugo"), email="")
    relayed = of_provider(
        raw_account(email="DOMINIQUE.bernard@example.org"), is_federated=False, is_relayed=True
    )
    people = [without_address, relayed, of_provider(renamed, first_name="")]
    with database.transaction() as session:
        written = write_accounts(
            session, people, [HeldAccount(gone["id"], gone["idp_subject"])], NOON
        )
    assert written.skipped == [
        SkippedPerson(without_address.subject, "Garnier", "Hugo", None, "EMAIL_MISSING"),
        SkippedAddressHeld(relayed.subject, gone["id"], "ALREADY_EXISTS"),
        SkippedAccount(renamed["id"], "VALIDATION_FAILED"),
        SkippedAccount(gone["id"], "LAST_ADMINISTRATOR"),
    ]
    with database.transaction() as session:
        assert session.get_one(UserAccount, gone["id"]).state == "active"


@pytest.mark.requirement("WF-DAT-0070-A")
def test_an_account_the_provider_no_longer_holds_is_deactivated_by_the_platform(
    session: Session,
) -> None:
    gone = held(session)
    kept = held(session, email="kept@example.org")
    local = held(session, email="local@example.org", origin="local")
    held(session, email="off@example.org", state="deactivated")
    assert known_subjects(session) == frozenset(session.scalars(select(UserAccount.idp_subject)))
    (unheld,) = unheld_accounts(session, {kept["idp_subject"], local["idp_subject"]})
    assert unheld == HeldAccount(gone["id"], gone["idp_subject"])
    # Attached to another subject meanwhile, it is held after all.
    moved = HeldAccount(gone["id"], "another-subject")
    assert deactivate_unheld(session, moved, NOON) is False
    assert deactivate_unheld(session, unheld, NOON) is True
    stored = session.get_one(UserAccount, gone["id"])
    assert (stored.state, stored.updated_by, stored.updated_at) == ("deactivated", None, NOON)
    assert journal(session) == [("user_deactivate", None, gone["id"], {})]
    # Deactivated already, or local: left as it is.
    assert deactivate_unheld(session, unheld, NOON) is False
    as_local = HeldAccount(local["id"], local["idp_subject"])
    assert deactivate_unheld(session, as_local, NOON) is False
    assert session.get_one(UserAccount, local["id"]).state == "active"


def test_the_report_read_is_that_of_the_latest_reading(session: Session) -> None:
    assert latest_report(session) is None
    reports: list[SyncReport] = []
    for hours in (2, 1):
        task_id = uuid4()
        session.add(
            BackgroundTask(
                id=task_id,
                kind="identity_sync",
                status="succeeded",
                progress=100,
                payload={},
                correlation_id=CORRELATION,
                attempts=1,
                submitted_at=NOON,
                finished_at=NOON,
            )
        )
        session.flush()
        report = SyncReport(
            task_id,
            NOON + timedelta(hours=hours),
            2,
            1,
            1,
            hours,
            [
                SkippedAccount(uuid4(), "LAST_ADMINISTRATOR"),
                SkippedPerson("kc-hugo", "Garnier", "Hugo", None, "EMAIL_MISSING"),
                SkippedAddressHeld("kc-camille", uuid4(), "ALREADY_EXISTS"),
                SkippedAddressHeld("kc-lou", None, "ALREADY_EXISTS"),
            ],
            ["orphan@x.org"],
        )
        record_report(session, report)
        reports.append(report)
    assert latest_report(session) == reports[0]


def test_the_reading_and_a_change_of_roles_queue_without_a_deadlock(
    database: Database, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The reading follows an account, the roles of which an administrator sets meanwhile, then
    # deactivates another under the guard of the last administrator. It takes the lock of the rule
    # before any row, as the change of roles does: the change waits for the reading, then passes —
    # in the other order, each would wait on what the other holds.
    with database.transaction() as session:
        renamed = held(session)
        gone = held(session, email="gone@example.org")
    planning = role(database, "Planification", permissions=("planning.read",))
    outcomes: list[object] = []

    def give_roles() -> None:
        try:
            with logging_context(correlation_id=CORRELATION), database.transaction() as session:
                session.execute(text("SET LOCAL lock_timeout = '10s'"))
                set_access_roles(session, renamed["id"], [planning], 1, Act(None, NOON))
        except DBAPIError as error:
            outcomes.append(error)
        else:
            outcomes.append("given")

    concurrent = threading.Thread(target=give_roles)

    def follow_then_give_roles(session: Session, person: ProviderAccount, at: datetime) -> object:
        followed = follow(session, person, at)
        concurrent.start()
        wait_for_a_lock(database)
        return followed

    monkeypatch.setattr(identity_sync, "follow", follow_then_give_roles)
    with database.transaction() as session:
        session.execute(text("SET LOCAL lock_timeout = '10s'"))
        written = write_accounts(
            session,
            [of_provider(renamed, last_name="Martin-Dupont")],
            [HeldAccount(gone["id"], gone["idp_subject"])],
            NOON,
        )
    concurrent.join(15)
    counts = {"created": 0, "updated": 1, "unchanged": 0, "restored": 0, "deactivated": 1}
    assert written == Written(counts, [], [])
    assert outcomes == ["given"]
    with database.transaction() as session:
        stored = session.get_one(UserAccount, renamed["id"])
        assert (stored.last_name, stored.lock_version) == ("Martin-Dupont", 2)
        held_roles = roles_held_by(session, [renamed["id"]])[renamed["id"]]
        assert [each.access_role_id for each in held_roles] == [planning]
        assert session.get_one(UserAccount, gone["id"]).state == "deactivated"
