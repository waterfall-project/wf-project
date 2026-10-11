# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The link that sets the password of an account, asked for through the API (US-0350).

The caller, Camille Martin, may consult and change the accounts. Keycloak is the realm of test,
which serves keys and nothing of the administration API: what the API refuses before asking the
extension for a link is tried here; the link itself, made by the extension, and its inscription in
the journal, against the platform (``test_keycloak_authentication.py``).
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from access_rows import account, role
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from support import ContractClient, Watching, bearer

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.interface import inscribe_password_link
from waterfall.platform.audit import Act, AuditActor, AuditEntry
from waterfall.platform.database import Database
from waterfall.platform.errors import ConflictError
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.logs import logging_context
from waterfall.platform.settings import ServiceSettings

USERS = "/api/v1/users"
CAMILLE = "6c2d4e1f-3a5b-4c7d-8e9f-0a1b2c3d4e5f"
NOON = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


@pytest.fixture
def watching(keycloak: Keycloak, realm_settings: ServiceSettings, database: Database) -> Watching:
    """Give the administration client of the API, which notes each call to Keycloak."""
    return Watching(keycloak, realm_settings, database)


@pytest.fixture
def client(
    contract: OpenAPI, database: Database, keycloak: Keycloak, watching: Watching
) -> ContractClient:
    """Give a client of the API whose administration client is watched."""
    app = create_app(Services(database, keycloak, watching))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


def caller(database: Database, realm: TestRealm, *permissions: str) -> dict[str, str]:
    """Write Camille Martin's account with a role of ``permissions``; give her token's header."""
    held = role(database, "Gestion des comptes", permissions=permissions)
    account(database, "Martin", "Camille", roles=(held,), idp_subject=CAMILLE)
    return bearer(realm.token(CAMILLE, KEY))


@pytest.fixture
def headers(database: Database, realm: TestRealm) -> dict[str, str]:
    """Let the caller consult and change the accounts."""
    return caller(database, realm, "users.read", "users.write")


def link_of(client: ContractClient, headers: dict[str, str], user_id: UUID) -> Any:
    """Ask the API for the password link of an account."""
    return client.post(f"{USERS}/{user_id}/password-link", headers=headers)


def refusal(response: Any) -> tuple[int, str, dict[str, Any]]:
    """Give the status, the code and the parameters of a refusal."""
    body = response.json()
    return response.status_code, body["code"], body.get("params", {})


type Traces = Callable[[], tuple[list[tuple[str, int]], int]]


@pytest.fixture
def traces(watching: Watching, database: Database) -> Traces:
    """Give what a request left: the calls to Keycloak, and the number of inscriptions."""

    def read() -> tuple[list[tuple[str, int]], int]:
        with database.transaction() as session:
            count = session.scalar(select(func.count()).select_from(AuditEntry))
        return watching.held, count or 0

    return read


@pytest.mark.parametrize(
    "case",
    [
        ("directory", "active", "is_local_account"),
        ("identity_provider", "active", "is_local_account"),
        ("local", "deactivated", "is_active_account"),
        # Lacking both, it is refused by the first.
        ("directory", "deactivated", "is_local_account"),
    ],
    ids=["of the directory", "of an external provider", "deactivated", "both"],
)
@pytest.mark.requirement("WF-ADM-0140-A")
def test_an_account_that_is_not_local_or_is_deactivated_has_no_link(
    client: ContractClient,
    database: Database,
    headers: dict[str, str],
    traces: Traces,
    case: tuple[str, str, str],
) -> None:
    # « Un compte importé n'a pas d'écran de mot de passe » : it authenticates with its directory,
    # and Waterfall gives it no link that would set one. The provider is not even asked.
    origin, state, condition = case
    user_id = account(database, "Montgolfier", "Jeanne", origin=origin, state=state)
    response = link_of(client, headers, user_id)
    assert refusal(response) == (409, "STATE_FORBIDS_OPERATION", {"missing_condition": condition})
    assert traces() == ([], 0)


def test_an_account_that_does_not_exist_has_no_link(
    client: ContractClient, headers: dict[str, str], traces: Traces
) -> None:
    response = link_of(client, headers, uuid4())
    assert refusal(response)[:2] == (404, "NOT_FOUND")
    assert traces() == ([], 0)


@pytest.mark.parametrize(
    "case",
    [(("users.read",), 403), (("users.write",), 404)],
    ids=["without changing the accounts", "without consulting them"],
)
def test_a_link_is_given_only_to_who_may_change_the_accounts(
    client: ContractClient,
    database: Database,
    realm: TestRealm,
    traces: Traces,
    case: tuple[tuple[str, ...], int],
) -> None:
    permissions, status = case
    user_id = account(database, "Montgolfier", "Jeanne")
    response = link_of(client, caller(database, realm, *permissions), user_id)
    assert response.status_code == status
    assert traces() == ([], 0)


def test_a_link_keycloak_could_not_make_is_neither_given_nor_inscribed(
    client: ContractClient, database: Database, headers: dict[str, str], traces: Traces
) -> None:
    # The realm of test serves no extension: Keycloak fails, asked with no connection held (#669).
    user_id = account(database, "Montgolfier", "Jeanne")
    response = link_of(client, headers, user_id)
    assert refusal(response) == (
        503,
        "COMPONENT_UNAVAILABLE",
        {"component": "identity_provider"},
    )
    assert traces() == ([("make_password_link", 0)], 0)


def test_a_link_made_is_inscribed_by_its_author_without_anything_of_the_link(
    database: Database, session: Session
) -> None:
    author = AuditActor(uuid4(), "Camille Martin")
    user_id = account(database, "Montgolfier", "Jeanne")
    with logging_context(correlation_id="link"):
        inscribe_password_link(session, user_id, Act(author, NOON))
    entry = session.scalars(select(AuditEntry)).one()
    assert (entry.action, entry.object_id, entry.object_label) == (
        "password_link_create",
        user_id,
        "Jeanne Montgolfier",
    )
    assert (entry.actor_user_id, entry.occurred_at, entry.params) == (author.user_id, NOON, {})


def test_a_link_made_for_an_account_deactivated_meanwhile_is_neither_inscribed_nor_given(
    database: Database, session: Session
) -> None:
    # The account is read again under a lock once the provider made the link (#669).
    user_id = account(database, "Montgolfier", "Jeanne", state="deactivated")
    with logging_context(correlation_id="link"), pytest.raises(ConflictError) as refused:
        inscribe_password_link(session, user_id, Act(None, NOON))
    assert refused.value.params == {"missing_condition": "is_active_account"}
    assert session.scalars(select(AuditEntry)).all() == []
