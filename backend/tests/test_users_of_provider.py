# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A person the identity provider knows and Waterfall not yet: admitted by her origin, no role."""

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session
from support import raw_account

from waterfall.core.users.interface import (
    NAME_MAX_LENGTH,
    add_account_of_provider,
    origin_of,
    read_account_of_subject,
)
from waterfall.core.users.tables import UserAccount
from waterfall.platform.keycloak import ProviderAccount

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
    assert created is not None
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
    assert created is not None
    assert created.origin == "identity_provider"


def test_a_local_account_of_the_provider_is_not_admitted(session: Session) -> None:
    assert add_account_of_provider(session, person(is_federated=False), NOON) is None
    assert read_account_of_subject(session, SUBJECT) is None


@pytest.mark.parametrize(
    "lacking",
    [
        {"email": ""},
        {"last_name": ""},
        {"first_name": ""},
        {"last_name": "x" * (NAME_MAX_LENGTH + 1)},
    ],
)
def test_a_person_whose_identity_cannot_be_kept_is_not_admitted(
    lacking: dict[str, str], session: Session
) -> None:
    assert add_account_of_provider(session, person(**lacking), NOON) is None
    assert session.scalar(select(func.count()).select_from(UserAccount)) == 0


def test_an_address_another_account_holds_admits_nobody(session: Session) -> None:
    session.execute(
        insert(UserAccount).values(**raw_account(email="Dominique.Annuaire@waterfall.test"))
    )
    assert add_account_of_provider(session, person(), NOON) is None
    assert read_account_of_subject(session, SUBJECT) is None


def test_a_person_created_twice_is_one_account(session: Session) -> None:
    first = add_account_of_provider(session, person(), NOON)
    second = add_account_of_provider(session, person(last_name="Autre"), NOON)
    assert first is not None
    assert second == first
    assert session.scalar(select(func.count()).select_from(UserAccount)) == 1
