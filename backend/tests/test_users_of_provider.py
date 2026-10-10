# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A person the identity provider knows and Waterfall not yet: admitted by her origin, no role."""

import threading
import time
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session
from support import raw_account

from waterfall.core.users.interface import (
    NAME_MAX_LENGTH,
    Account,
    NotAdmitted,
    add_account_of_provider,
    origin_of,
    read_account_of_subject,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.database import Database
from waterfall.platform.keycloak_admin import ProviderAccount

NOON = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
SUBJECT = "0f6a3b2c-1d4e-4f5a-8b9c-7d6e5f4a3b2c"


def person(**overrides: Any) -> ProviderAccount:
    """Describe a person of the directory as the provider does, with the changes asked for."""
    fields: dict[str, Any] = {
        "subject": SUBJECT,
        "last_name": "Annuaire",
        "first_name": "Dominique",
        "email": "dominique.annuaire@waterfall.test",
        "is_federated": True,
        "is_relayed": False,
        **overrides,
    }
    return ProviderAccount(**fields)


@pytest.mark.parametrize(
    ("is_federated", "is_relayed", "origin"),
    [
        (True, False, "directory"),
        # Read from the directory, then linked to a provider: the directory holds its identity.
        (True, True, "directory"),
        (False, True, "identity_provider"),
        (False, False, None),
    ],
)
def test_the_origin_of_an_account_is_where_the_provider_reads_it(
    is_federated: bool, is_relayed: bool, origin: str | None
) -> None:
    assert origin_of(person(is_federated=is_federated, is_relayed=is_relayed)) == origin


def test_a_person_of_the_directory_is_created_active_by_the_platform(session: Session) -> None:
    created = add_account_of_provider(session, person(), NOON)
    assert isinstance(created, Account)
    assert (created.last_name, created.first_name, created.email) == (
        "Annuaire",
        "Dominique",
        "dominique.annuaire@waterfall.test",
    )
    assert (created.origin, created.is_active, created.subject) == ("directory", True, SUBJECT)
    assert (created.created_by, created.updated_by) == (None, None)
    assert created.created_at == created.updated_at == NOON
    assert read_account_of_subject(session, SUBJECT) == created


def test_a_person_relayed_by_an_external_provider_is_created_as_such(session: Session) -> None:
    created = add_account_of_provider(session, person(is_federated=False, is_relayed=True), NOON)
    assert isinstance(created, Account)
    assert created.origin == "identity_provider"


def test_a_local_account_of_the_provider_is_not_admitted(session: Session) -> None:
    refused = add_account_of_provider(session, person(is_federated=False), NOON)
    assert refused == NotAdmitted.LOCAL_ACCOUNT
    assert read_account_of_subject(session, SUBJECT) is None


@pytest.mark.parametrize(
    ("lacking", "reason"),
    [
        ({"email": ""}, NotAdmitted.NO_ADDRESS),
        ({"last_name": ""}, NotAdmitted.NAME_NOT_STORABLE),
        ({"first_name": ""}, NotAdmitted.NAME_NOT_STORABLE),
        ({"last_name": "x" * (NAME_MAX_LENGTH + 1)}, NotAdmitted.NAME_NOT_STORABLE),
        ({"first_name": "x" * (NAME_MAX_LENGTH + 1)}, NotAdmitted.NAME_NOT_STORABLE),
    ],
)
def test_a_person_whose_identity_cannot_be_kept_is_not_admitted(
    lacking: dict[str, str], reason: NotAdmitted, session: Session
) -> None:
    assert add_account_of_provider(session, person(**lacking), NOON) == reason
    assert session.scalar(select(func.count()).select_from(UserAccount)) == 0


def test_an_address_another_account_holds_admits_nobody(session: Session) -> None:
    session.execute(
        insert(UserAccount).values(**raw_account(email="Dominique.Annuaire@waterfall.test"))
    )
    assert add_account_of_provider(session, person(), NOON) == NotAdmitted.ADDRESS_TAKEN
    assert read_account_of_subject(session, SUBJECT) is None


def test_a_person_created_twice_is_one_account(session: Session) -> None:
    first = add_account_of_provider(session, person(), NOON)
    second = add_account_of_provider(session, person(last_name="Autre"), NOON)
    assert isinstance(first, Account)
    assert second == first
    assert session.scalar(select(func.count()).select_from(UserAccount)) == 1


def wait_for_a_lock(database: Database) -> None:
    """Wait until a transaction waits for a lock another one holds, in 10 seconds at most."""
    deadline = time.monotonic() + 10
    with database.engine.connect() as watching:
        while time.monotonic() < deadline:
            if watching.scalar(text("SELECT count(*) FROM pg_locks WHERE NOT granted")):
                return
            watching.rollback()
            time.sleep(0.05)
    pytest.fail("no transaction waits for a lock")


def test_two_first_requests_at_once_give_one_account(database: Database) -> None:
    with Session(database.engine) as first, Session(database.engine) as second:
        inserted = add_account_of_provider(first, person(), NOON)
        assert isinstance(inserted, Account)
        found: list[Account | NotAdmitted] = []
        waiting = threading.Thread(
            target=lambda: found.append(add_account_of_provider(second, person(), NOON))
        )
        waiting.start()
        # The second waits for the first, whose row is not committed yet.
        wait_for_a_lock(database)
        assert found == []
        first.commit()
        waiting.join(timeout=10)
        assert found == [inserted]
        second.commit()
    with Session(database.engine) as session:
        assert session.scalar(select(func.count()).select_from(UserAccount)) == 1
