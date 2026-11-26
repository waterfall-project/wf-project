# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The version of Keycloak, read by the probe of the API on the platform (US-2890, #4641).

The administration API gives the version of Keycloak only to an administrator of the realm
``master``: the extension gives it to the service account of Waterfall, and the API exposes it
beside the others, in ``waterfall_component_version``, which the status screen reads. Run by
``make test-keycloak``, with the variables of ``test_keycloak_platform.py``; the API is served in
the process of the tests, on a database of their own.
"""

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from metrics_reading import samples, value
from pydantic import SecretStr
from support import nowhere
from test_keycloak_platform import image_version, served_settings

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.metrics import COMPONENT_UP, COMPONENT_VERSION

if TYPE_CHECKING:
    from collections.abc import Iterator

    from metrics_reading import Samples

    from waterfall.platform.database import Database
    from waterfall.platform.settings import ServiceSettings

pytestmark = pytest.mark.keycloak

METRICS = "/api/v1/metrics"


@pytest.fixture
def keycloak() -> Iterator[Keycloak]:
    """Give the client of the realm the API reaches."""
    client = Keycloak(served_settings())
    yield client
    client.close()


def collected(database: Database, keycloak: Keycloak, settings: ServiceSettings) -> Samples:
    """Collect the metrics of an API on the Keycloak of the platform, as Prometheus does."""
    administration = KeycloakAdmin(keycloak, settings)
    app = create_app(Services(database, keycloak, administration, *nowhere()))
    response = TestClient(app, raise_server_exceptions=False).get(METRICS)
    assert response.status_code == 200, response.text
    return samples(response.text)


def keycloak_versions(read: Samples) -> list[str]:
    """Give the versions the metrics say of the identity provider."""
    return [
        dict(labelled)["version"]
        for (name, labelled), _ in read.items()
        if name == COMPONENT_VERSION and dict(labelled)["component"] == "identity_provider"
    ]


@pytest.mark.requirement("WF-CMP-0020-A")
@pytest.mark.story("US-2890")
def test_the_api_announces_the_version_of_keycloak_its_service_account_reads(
    database: Database, keycloak: Keycloak
) -> None:
    # « L'écran d'état présente la version de chaque composant. » : that of the identity provider,
    # read from the extension by the service account, is the version of the image (#4641).
    read = collected(database, keycloak, served_settings())
    assert value(read, COMPONENT_UP, component="identity_provider") == 1
    assert keycloak_versions(read) == [image_version()]


@pytest.mark.story("US-2890")
def test_a_service_account_refused_leaves_keycloak_available_without_a_version(
    database: Database, keycloak: Keycloak
) -> None:
    # Proper to US-2890: a secret the realm refuses reads no version; Keycloak, which serves its
    # keys, is available all the same, and no version is said rather than a wrong one.
    wrong = served_settings().model_copy(
        update={"service_client_secret": SecretStr("not-the-secret")}
    )
    read = collected(database, keycloak, wrong)
    assert value(read, COMPONENT_UP, component="identity_provider") == 1
    assert keycloak_versions(read) == []
