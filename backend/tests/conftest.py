# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The fixtures of the tests of the service."""

import io
import logging
import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
import structlog
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from sqlalchemy import text
from sqlalchemy.orm import Session
from support import CONTRACT, PLATFORM_SECRETS, ContractClient, Logs

from waterfall.api.app import create_app
from waterfall.migrations.runner import upgrade
from waterfall.platform.database import Database, create_database_engine, engine_url
from waterfall.platform.logs import configure_logging
from waterfall.platform.settings import Settings, load_settings


@pytest.fixture
def platform_environment(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Give the process the secrets a service of the test platform is started with."""
    for name, value in PLATFORM_SECRETS.items():
        monkeypatch.setenv(name, value)
    return PLATFORM_SECRETS


@pytest.fixture
def platform_settings(platform_environment: dict[str, str]) -> Settings:
    """Read the settings of the test platform, secrets included."""
    settings = load_settings()
    assert (
        settings.database_url.get_secret_value() == platform_environment["WATERFALL_DATABASE_URL"]
    )
    return settings


@pytest.fixture
def logs(platform_settings: Settings) -> Iterator[Logs]:
    """Capture the logs in memory, as a service of the test platform writes them, then restore."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    stream = io.StringIO()
    configure_logging("DEBUG", stream, platform_settings.secret_values())
    yield Logs(stream)
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.reset_defaults()


@pytest.fixture(scope="session")
def contract() -> OpenAPI:
    """Read the interface contract, once."""
    return OpenAPI.from_file_path(str(CONTRACT))


@pytest.fixture
def client(contract: OpenAPI) -> ContractClient:
    """Build a client on the application."""
    return ContractClient(TestClient(create_app(), raise_server_exceptions=False), contract)


TEST_DATABASE_VARIABLE = "WATERFALL_TEST_DATABASE_URL"


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Create, for this run, a database of the PostgreSQL server the tests are given, migrated.

    ``WATERFALL_TEST_DATABASE_URL`` designates a server and a role that may create databases.
    Without it the tests that need a database fail and say so: PostgreSQL is the database of the
    platform, and no other stands in for it.
    """
    address = os.environ.get(TEST_DATABASE_VARIABLE)
    if not address:
        pytest.fail(
            f"{TEST_DATABASE_VARIABLE} is not set: give it the URL of a PostgreSQL server "
            "whose role may create databases (the guide, 'Tests', says how)",
            pytrace=False,
        )
    name = f"waterfall_test_{uuid4().hex}"
    server = create_database_engine(address).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    url = engine_url(address).set(database=name).render_as_string(hide_password=False)
    engine = create_database_engine(url)
    upgrade(engine)
    engine.dispose()
    yield url
    with server.connect() as connection:
        connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
    server.dispose()


@pytest.fixture
def database(database_url: str) -> Iterator[Database]:
    """Give the migrated database, emptied of its accounts after the test."""
    db = Database(create_database_engine(database_url))
    yield db
    with db.engine.begin() as connection:
        connection.execute(text("TRUNCATE user_account, installation"))
    db.dispose()


@pytest.fixture
def session(database: Database) -> Iterator[Session]:
    """Give a session whose work is rolled back at the end of the test."""
    with Session(database.engine) as opened:
        yield opened
        opened.rollback()
