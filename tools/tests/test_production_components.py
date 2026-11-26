# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The components of the production platform, checked before its migrations (US-2810/L1).

The Compose of production runs ``waterfall-check-components`` before ``waterfall-migrate``, and the
platform goes no further when a component is of a version older than the one required
(WF-CMP-0020-A). The PostgreSQL of every Compose that starts the back is the one the processes of
the back accept: its major version 18, set for 1 024 locks per transaction.
"""

import re
import tomllib
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from wftools import REPOSITORY

if TYPE_CHECKING:
    from pathlib import Path

COMPOSE = REPOSITORY / "deploy" / "compose"
PRODUCTION = COMPOSE / "compose.prod.yaml"
DONE = {"condition": "service_completed_successfully"}
HEALTHY = {"condition": "service_healthy"}


def services() -> dict[str, Any]:
    """Read the services of the production platform."""
    return yaml.safe_load(PRODUCTION.read_text(encoding="utf-8"))["services"]


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_migrations_wait_for_the_check_of_the_components_run_by_the_image() -> None:
    # « Le déploiement échoue en le disant si un composant est d'une version antérieure à celle
    # exigée. » : the check ends before the migrations start, and a failure stops the platform,
    # everything else depending on the migrations.
    found = services()
    assert found["components"]["command"] == ["waterfall-check-components"]
    assert found["components"]["image"] == found["migrate"]["image"]
    assert found["components"]["restart"] == "no"
    assert found["migrate"]["depends_on"]["components"] == DONE
    assert found["install"]["depends_on"]["migrate"] == DONE
    assert found["components"]["depends_on"] == {
        "waterfall-database": DONE,
        "redis": HEALTHY,
        "keycloak-realm": HEALTHY,
    }
    # keycloak-realm waits for keycloak alone: no cycle with the migrations (#4641).
    assert found["keycloak-realm"]["depends_on"] == {"keycloak": HEALTHY}


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_check_reaches_each_component_as_the_platform_does_in_tls_and_holds_what_it_needs() -> (
    None
):
    environment = services()["components"]["environment"]
    owner = services()["migrate"]["environment"]["WATERFALL_DATABASE_URL"]
    assert environment["WATERFALL_DATABASE_URL"] == owner
    assert environment["WATERFALL_REDIS_URL"].startswith("rediss://")
    assert environment["WATERFALL_KEYCLOAK_BACKCHANNEL"] == "https://keycloak:8443/auth"
    assert environment["WATERFALL_TLS_AUTHORITY"] == "/trust/root.crt"
    name = "WATERFALL_SERVICE_CLIENT_SECRET"
    assert environment[name] == f"${{{name}:?set {name} in .env}}"
    assert "WATERFALL_KEYCLOAK_ADMIN_PASSWORD" not in environment
    assert services()["keycloak"]["depends_on"] == {"keycloak-database": DONE}


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_command_is_one_of_the_distribution_the_image_installs() -> None:
    pyproject = tomllib.loads((REPOSITORY / "backend" / "pyproject.toml").read_text("utf-8"))
    scripts = pyproject["project"]["scripts"]
    assert scripts["waterfall-check-components"] == "waterfall.platform.components_check:main"


def locks_of(path: Path) -> list[int]:
    """Read each ``max_locks_per_transaction`` a file sets for a PostgreSQL, in whatever way."""
    text = path.read_text(encoding="utf-8")
    return [int(found) for found in re.findall(r"max_locks_per_transaction=(\d+)", text)]


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.parametrize(
    "name",
    [
        "compose.prod.yaml",
        "compose.service.yaml",
        "compose.test.yaml",
        "compose.restore-test.yaml",
    ],
)
def test_the_postgresql_of_every_compose_that_starts_the_back_is_set_for_1024_locks(
    name: str,
) -> None:
    # The API, the worker and the service of the restoration refuse to start under 1 024 locks per
    # transaction: the server of the production, the service platform, the tests and the test of a
    # restoration are each set for as many.
    assert locks_of(COMPOSE / name) == [1024]


@pytest.mark.requirement("WF-CMP-0020-A")
def test_the_postgresql_of_the_job_of_the_back_is_set_as_the_one_of_the_workstation() -> None:
    assert locks_of(REPOSITORY / ".github" / "workflows" / "back.yml") == [1024]
