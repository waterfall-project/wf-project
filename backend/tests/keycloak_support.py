# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the accounts on the Keycloak of the platform share: their fixtures (#979).

The client of the realm, the administration client of the API that notes the connections lent at
each call, the API served on them, the service account, the logs, the maker of local accounts and
the administrator of a test, which ``test_keycloak_identity_sync`` and
``test_keycloak_identity_change`` read alike, declared once so that the two files do not drift. A
test file takes a fixture by naming it at its top (``api = keycloak_support.api``): pytest reads it
from there.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from support import ContractClient, Logs, Watching, captured_logs, nowhere
from test_keycloak_authentication import changing_accounts, service_admin, with_password
from test_keycloak_platform import served_settings

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.users.tables import UserAccount
from waterfall.platform.keycloak import Keycloak

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from uuid import UUID

    import httpx2
    from openapi_core import OpenAPI
    from test_keycloak_platform import Account

    from waterfall.platform.database import Database


@pytest.fixture
def keycloak() -> Iterator[Keycloak]:
    """Give the client of the realm the API and the worker reach."""
    client = Keycloak(served_settings())
    yield client
    client.close()


@pytest.fixture
def watching(keycloak: Keycloak, database: Database) -> Watching:
    """Give the administration client of the API, which notes the connections held at each call."""
    return Watching(keycloak, served_settings(), database)


@pytest.fixture
def api(
    contract: OpenAPI, database: Database, keycloak: Keycloak, watching: Watching
) -> ContractClient:
    """Give a client of the API on the database of the test and the Keycloak of the platform."""
    app = create_app(Services(database, keycloak, watching, *nowhere()))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def admin() -> Iterator[httpx2.Client]:
    """Reach the administration API of the realm as the service account, as the API does."""
    with service_admin(served_settings()) as client:
        yield client


@pytest.fixture
def logs() -> Iterator[Logs]:
    """Capture the logs in memory, the secrets of the realm masked, then restore them.

    The fixture of ``conftest.py`` would give the process the secrets of a platform of test, which
    ``served_settings`` reads from then on and the Keycloak of the platform refuses.
    """
    with captured_logs(served_settings().secret_values()) as captured:
        yield captured


@pytest.fixture
def made(admin: httpx2.Client) -> Iterator[Callable[[str, str], Account]]:
    """Give a maker of local accounts of the realm with a password, removed after the test."""
    accounts: list[Account] = []

    def make(first_name: str, last_name: str) -> Account:
        accounts.append(with_password(admin, first_name, last_name))
        return accounts[-1]

    yield make
    for account in accounts:
        admin.delete(f"/users/{account.id}")


@dataclass(frozen=True, slots=True)
class Administrator:
    """The administrator of a test, Claude: her account in Waterfall, and her token's header."""

    user_id: UUID
    headers: dict[str, str]


@pytest.fixture
def administrator(database: Database, made: Callable[[str, str], Account]) -> Administrator:
    """Make Claude a local account Waterfall knows, which may change the accounts."""
    claude = made("Claude", "Locale")
    headers = changing_accounts(database, claude)
    return Administrator(user_of(database, claude.id), headers)


def user_of(database: Database, subject: str) -> UUID:
    """Give the account Waterfall holds for a subject of the realm."""
    with database.transaction() as session:
        return session.scalars(
            select(UserAccount.id).where(UserAccount.idp_subject == subject)
        ).one()
