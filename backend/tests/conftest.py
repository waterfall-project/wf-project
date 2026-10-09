# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The fixtures of the tests of the service."""

import io
import logging
from collections.abc import Iterator

import pytest
import structlog
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from support import CONTRACT, PLATFORM_SECRETS, ContractClient, Logs

from waterfall.api.app import create_app
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
