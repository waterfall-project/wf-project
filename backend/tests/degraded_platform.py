# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The platform of the tests of the degraded mode: each component behind a gate that closes.

The API reaches PostgreSQL, Redis, the object storage and the identity provider through a ``Gate``
each (``degraded_support``); the worker, the checks and the arrangement of a test reach them
directly, as the one that stops them from outside does not. The components are the services of the
tests of the slot, shared by the run: a test closes a gate, never a server (WF-EXP-0040-A).
"""

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from degraded_support import Gate
from fastapi.testclient import TestClient
from redis import ConnectionPool, Redis
from sqlalchemy import func, select
from support import ContractClient

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.platform.database import (
    SHIPPED_ROW,
    Base,
    Database,
    create_database_engine,
)
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import KeycloakAdmin
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.storage import Bucket

if TYPE_CHECKING:
    from collections.abc import Callable

    from openapi_core import OpenAPI
    from sqlalchemy import Engine
    from sqlalchemy.engine import URL

    from waterfall.platform.settings import ServiceSettings


@dataclass(frozen=True)
class Servers:
    """The components of the tests as a test reaches them directly, and what names them."""

    settings: ServiceSettings
    database: Database
    owner: Engine
    queue: TaskQueue
    bucket: Bucket


@dataclass
class Gates:
    """The gates of the four components the API reaches, each open until a test closes it."""

    database: Gate
    cache: Gate
    object_storage: Gate
    identity_provider: Gate

    def named(self, component: str) -> Gate:
        """Give the gate of a component of the contract (``PlatformComponent``)."""
        return {
            "database": self.database,
            "cache": self.cache,
            "object_storage": self.object_storage,
            "identity_provider": self.identity_provider,
        }[component]

    def close(self) -> None:
        """Close every gate, for good."""
        for each in (self.database, self.cache, self.object_storage, self.identity_provider):
            each.close()


def gate_to(address: str) -> Gate:
    """Open a gate to the server an address designates."""
    parts = urlsplit(address)
    assert parts.hostname
    return Gate(parts.hostname, parts.port or 0)


def through_database(url: URL, gate: Gate) -> str:
    """Give the address of a database as it is reached through a gate."""
    return url.set(host=gate.host, port=gate.port).render_as_string(hide_password=False)


def queue_through(queue: TaskQueue, gate: Gate, *, timeout: float) -> TaskQueue:
    """Open the queue of the tests as it is reached through a gate, waiting for it ``timeout``."""
    kept = queue.client.connection_pool.connection_kwargs
    options: dict[str, Any] = {
        **kept,
        "host": gate.host,
        "port": gate.port,
        "socket_timeout": timeout,
        "socket_connect_timeout": timeout,
    }
    return TaskQueue(Redis(connection_pool=ConnectionPool(**options)), queue.stream)


def storage_through(gate: Gate, bucket: Bucket) -> Bucket:
    """Open the bucket of the tests as it is reached through a gate, by the key of the tests."""
    parts = urlsplit(os.environ["WATERFALL_TEST_STORAGE_URL"])
    return Bucket.connect(
        bucket.name,
        f"http://{gate.address}",
        "us-east-1",
        parts.username or "",
        parts.password or "",
    )


@dataclass
class Degradable:
    """The API of a platform whose components stop, and the means to look at it from outside."""

    api: ContractClient
    gates: Gates
    services: Services
    gated_database: Database
    servers: Servers

    def stop(self, component: str) -> None:
        """Stop a component: what it had open is cut, and it refuses what comes."""
        self.gates.named(component).close()

    def restore(self, component: str) -> None:
        """Bring a component back, as it was."""
        self.gates.named(component).open()


def build(
    servers: Servers,
    contract: OpenAPI,
    administration: Callable[[Keycloak, ServiceSettings], KeycloakAdmin] = KeycloakAdmin,
) -> tuple[Degradable, Callable[[], None]]:
    """Make the API of the platform on four gates; give it with the means to close it all."""
    kept = servers.queue.client.connection_pool.connection_kwargs
    url = servers.database.engine.url
    gates = Gates(
        database=Gate(url.host or "127.0.0.1", url.port or 5432),
        cache=Gate(kept["host"], kept["port"]),
        object_storage=gate_to(servers.bucket.client.meta.endpoint_url),
        identity_provider=gate_to(servers.settings.keycloak_address),
    )
    database = Database(create_database_engine(through_database(url, gates.database)))
    settings = servers.settings.model_copy(
        update={"keycloak_backchannel": f"http://{gates.identity_provider.address}/auth"}
    )
    keycloak = Keycloak(settings)
    queue = queue_through(servers.queue, gates.cache, timeout=DEPOSIT_TIMEOUT)
    services = Services(
        database,
        keycloak,
        administration(keycloak, settings),
        queue,
        storage_through(gates.object_storage, servers.bucket),
    )
    app = create_app(services)
    api = ContractClient(TestClient(app, raise_server_exceptions=False), contract)

    def close() -> None:
        gates.close()
        keycloak.close()
        queue.close()
        database.dispose()

    return Degradable(api, gates, services, database, servers), close


def row_counts(owner: Engine) -> dict[str, int]:
    """Count the rows of every table the code declares, as the owner reads them.

    A write that left something half done changes a count that the whole of it would have changed
    with the others, or not at all: two counts taken around a refused request must be equal.
    """
    counts: dict[str, int] = {}
    with owner.connect() as connection:
        for table in Base.metadata.sorted_tables:
            if table.info.get(SHIPPED_ROW) is not None:
                continue
            counts[table.fullname] = connection.scalar(select(func.count()).select_from(table)) or 0
    return counts
