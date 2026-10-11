# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The reading of the accounts of the provider, as the module of the accounts writes it.

What the provider holds of a person is followed, by the platform, on the accounts it holds; one it
no longer holds is deactivated; a local account is left alone (WF-ADM-0070). What the worker asks
of Keycloak is tried against the platform (``test_keycloak_identity_sync.py``); its writes are
tried here, under the correlation of a task.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from support import raw_account

from waterfall.core.users.interface import (
    NotAdmitted,
    SyncReport,
    deactivate_unheld,
    follow,
    known_subjects,
    latest_report,
    record_report,
    unheld_accounts,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.audit import AuditEntry
from waterfall.platform.keycloak_admin import ProviderAccount
from waterfall.platform.logs import logging_context
from waterfall.platform.tasks import BackgroundTask

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


def test_a_local_account_is_never_followed(session: Session) -> None:
    # A local account is Waterfall's (WF-ADM-0070), whatever the realm holds of it.
    row = held(session, origin="local")
    assert follow(session, of_provider(row, last_name="Autre"), NOON) == "unchanged"
    assert session.get_one(UserAccount, row["id"]).last_name == "Martin"


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
    assert follow(session, of_provider(row, **changed), NOON) == reason
    stored = session.get_one(UserAccount, row["id"])
    assert (stored.email, stored.first_name, stored.lock_version) == (row["email"], "Claire", 0)
    assert journal(session) == []


def test_a_person_unknown_to_waterfall_is_created_without_any_role(session: Session) -> None:
    person = of_provider(raw_account(last_name="Annuaire", first_name="Dominique"))
    assert follow(session, person, NOON) == "created"
    assert follow(session, person, NOON) == "unchanged"
    local = of_provider(raw_account(email="l@x.org"), is_federated=False)
    assert follow(session, local, NOON) == NotAdmitted.LOCAL_ACCOUNT


@pytest.mark.requirement("WF-DAT-0070-A")
def test_an_account_the_provider_no_longer_holds_is_deactivated_by_the_platform(
    session: Session,
) -> None:
    gone = held(session)
    kept = held(session, email="kept@example.org")
    local = held(session, email="local@example.org", origin="local")
    held(session, email="off@example.org", state="deactivated")
    assert known_subjects(session) == frozenset(session.scalars(select(UserAccount.idp_subject)))
    unheld = unheld_accounts(session, {kept["idp_subject"], local["idp_subject"]})
    assert [(each.user_id, each.email) for each in unheld] == [(gone["id"], gone["email"])]
    assert deactivate_unheld(session, gone["id"], NOON) is True
    stored = session.get_one(UserAccount, gone["id"])
    assert (stored.state, stored.updated_by, stored.updated_at) == ("deactivated", None, NOON)
    assert journal(session) == [("user_deactivate", None, gone["id"], {})]
    # Deactivated already, or local: left as it is.
    assert deactivate_unheld(session, gone["id"], NOON) is False
    assert deactivate_unheld(session, local["id"], NOON) is False
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
            [("d@x.org", "LAST_ADMINISTRATOR")],
            ["orphan@x.org"],
        )
        record_report(session, report)
        reports.append(report)
    assert latest_report(session) == reports[0]
