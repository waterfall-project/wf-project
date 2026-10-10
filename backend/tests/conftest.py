# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The fixtures of the tests of the service."""

import io
import json
import logging
import os
from collections.abc import Iterator
from uuid import uuid4

import pytest
import structlog
from fastapi.testclient import TestClient
from openapi_core import Config, OpenAPI
from realm import KEY, TestRealm
from sqlalchemy import Engine, delete, text
from sqlalchemy.orm import Session
from support import (
    CONTRACT,
    PLATFORM_ADDRESSES,
    PLATFORM_SECRETS,
    ContractClient,
    Logs,
    service_role,
)

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.core.access_roles.tables import WRITTEN_BY_MIGRATION
from waterfall.migrations.runner import upgrade
from waterfall.platform.database import Base, Database, create_database_engine, engine_url
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.logs import configure_logging
from waterfall.platform.settings import ServiceSettings, load_service_settings


@pytest.fixture
def platform_environment(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Give the process the secrets a service of the test platform is started with."""
    for name, value in {**PLATFORM_SECRETS, **PLATFORM_ADDRESSES}.items():
        monkeypatch.setenv(name, value)
    return PLATFORM_SECRETS


@pytest.fixture
def platform_settings(platform_environment: dict[str, str]) -> ServiceSettings:
    """Read the settings of the API of the test platform, secrets included."""
    settings = load_service_settings()
    assert (
        settings.database_url.get_secret_value() == platform_environment["WATERFALL_DATABASE_URL"]
    )
    return settings


@pytest.fixture
def services(platform_settings: ServiceSettings) -> Iterator[Services]:
    """Give the services of the API of the test platform, which reach nothing until asked to."""
    database = Database(create_database_engine(platform_settings.database_url.get_secret_value()))
    keycloak = Keycloak(platform_settings)
    yield Services(database, keycloak, KeycloakAdmin(keycloak, platform_settings))
    keycloak.close()
    database.dispose()


@pytest.fixture
def realm() -> Iterator[TestRealm]:
    """Serve one key of the realm of test, then stop."""
    served = TestRealm()
    served.add_key(KEY)
    yield served
    served.stop()


@pytest.fixture
def realm_settings(platform_settings: ServiceSettings, realm: TestRealm) -> ServiceSettings:
    """Give the settings of the API, Keycloak being the realm of test."""
    return platform_settings.model_copy(update={"keycloak_address": realm.address})


@pytest.fixture
def keycloak(realm_settings: ServiceSettings) -> Iterator[Keycloak]:
    """Give the client of the realm of test."""
    client = Keycloak(realm_settings)
    yield client
    client.close()


@pytest.fixture
def api(
    contract: OpenAPI, database: Database, keycloak: Keycloak, realm_settings: ServiceSettings
) -> ContractClient:
    """Give a client of the application on the database of test and the realm of test."""
    app = create_app(Services(database, keycloak, KeycloakAdmin(keycloak, realm_settings)))
    return ContractClient(TestClient(app, raise_server_exceptions=False), contract)


@pytest.fixture
def logs(platform_settings: ServiceSettings) -> Iterator[Logs]:
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
    """Read the interface contract, once.

    A refusal answers in ``application/problem+json``, JSON that openapi-core does not read by
    itself: without this, no refusal could be checked against its schema.
    """
    config = Config(extra_media_type_deserializers={"application/problem+json": json.loads})
    return OpenAPI.from_file_path(str(CONTRACT), config=config)


@pytest.fixture
def client(contract: OpenAPI, services: Services) -> ContractClient:
    """Build a client on the application."""
    return ContractClient(TestClient(create_app(services), raise_server_exceptions=False), contract)


TEST_DATABASE_VARIABLE = "WATERFALL_TEST_DATABASE_URL"


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """Create, for this run, a database of the PostgreSQL server the tests are given, migrated.

    ``WATERFALL_TEST_DATABASE_URL`` designates a server and a superuser, who may create databases
    and roles. Without it the tests that need a database fail and say so: PostgreSQL is the
    database of the platform, and no other stands in for it.
    """
    address = os.environ.get(TEST_DATABASE_VARIABLE)
    if not address:
        pytest.fail(
            f"{TEST_DATABASE_VARIABLE} is not set: give it the URL of a PostgreSQL server "
            "whose role is a superuser (the guide, 'Tests', says how)",
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
        connection.execute(text(f'DROP ROLE IF EXISTS "{service_role(engine_url(url))}"'))
    server.dispose()


@pytest.fixture(scope="session")
def service_database_url(database_url: str) -> Iterator[str]:
    """Give the address of the test database as the service reaches it, by a role of the service.

    A role made for this run, that may sign in, member of the role of the service of the test
    database and holding nothing else: what the tables do not grant the service, the tests cannot
    do either.
    """
    name, password = f"waterfall_test_{uuid4().hex}", uuid4().hex
    service = service_role(engine_url(database_url))
    server = create_database_engine(database_url).execution_options(isolation_level="AUTOCOMMIT")
    with server.connect() as connection:
        connection.execute(
            text(f'CREATE ROLE "{name}" LOGIN PASSWORD \'{password}\' IN ROLE "{service}"')
        )
    url = engine_url(database_url).set(username=name, password=password)
    yield url.render_as_string(hide_password=False)
    with server.connect() as connection:
        connection.execute(
            text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = :name"),
            {"name": name},
        )
        connection.execute(text(f'DROP ROLE "{name}"'))
    server.dispose()


@pytest.fixture
def database(database_url: str, service_database_url: str) -> Iterator[Database]:
    """Give the migrated database as the service sees it, emptied afterwards of every row.

    The rows of every table the code declares are deleted by the owner, the journal of audit
    included: its triggers, which refuse any deletion, are off for that transaction alone — what
    only a superuser may do, and the service never. A table the migrations fill — the catalogue
    of permissions — keeps its rows, as an installation does.
    """
    db = Database(create_database_engine(service_database_url))
    yield db
    db.dispose()
    owner = create_database_engine(database_url)
    with owner.begin() as connection:
        connection.execute(text("SET LOCAL session_replication_role = replica"))
        for table in reversed(Base.metadata.sorted_tables):
            if not table.info.get(WRITTEN_BY_MIGRATION):
                connection.execute(delete(table))
    owner.dispose()


@pytest.fixture
def owner(database_url: str) -> Iterator[Engine]:
    """Give an engine of the owner of the tables, on the database the service sees.

    What the service may not do — delete an account, change the journal — a test does around it,
    through the owner.
    """
    engine = create_database_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(database: Database) -> Iterator[Session]:
    """Give a session whose work is rolled back at the end of the test."""
    with Session(database.engine) as opened:
        yield opened
        opened.rollback()
