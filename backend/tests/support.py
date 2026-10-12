# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the service share: the secrets of a test platform, the logs, the contract."""

import io
import json
import logging
import time
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
import structlog
from fastapi.testclient import TestClient
from httpx2 import Response
from openapi_core import OpenAPI
from openapi_core.testing import MockRequest, MockResponse
from sqlalchemy import URL, QueuePool, text

from waterfall.platform.database import Database
from waterfall.platform.keycloak import Keycloak
from waterfall.platform.keycloak_admin import (
    InvitationFailure,
    KeycloakAdmin,
    LocalIdentity,
    PasswordLink,
    ProviderAccount,
)
from waterfall.platform.logs import configure_logging
from waterfall.platform.queue import DEPOSIT_TIMEOUT, TaskQueue
from waterfall.platform.settings import ServiceSettings
from waterfall.platform.storage import Bucket

CONTRACT = Path(__file__).resolve().parents[2] / "docs" / "api" / "openapi.yaml"

# The secrets of the test platform: the values a search of the logs looks for (WF-OBS-0020).
DB_CREDENTIAL = "db-pass-4f8a1c"
REDIS_CREDENTIAL = "redis-pass-9d2e7b"
BEARER_JWT = "eyJhbGciOiJSUzI1NiJ9.test-access-token-3b6f"
SESSION_COOKIE = "wf_session=cookie-value-5c0d"
# A password a driver decodes from its URL: the logs must hide the decoded text, not only the URL.
ENCODED_CREDENTIAL = "p%40ss%2Fw%3Ard%231%5Cx"
DECODED_CREDENTIAL = "p@ss/w:rd#1\\x"
# The two decodings differ on this one: ``unquote`` keeps the plus, ``unquote_plus`` makes a space.
PLUS_CREDENTIAL = "a+b%40"
SERVICE_CREDENTIAL = "service-client-pass-6e1b0a"
STORAGE_CREDENTIAL = "storage-secret-key-8c3d5f"
OWNER_CREDENTIAL = "owner-pass-2a7e9b"
KEYCLOAK_DATABASE_CREDENTIAL = "keycloak-db-pass-0d4c6a"
PLATFORM_SECRETS = {
    "WATERFALL_DATABASE_URL": f"postgresql://waterfall:{DB_CREDENTIAL}@db:5432/waterfall",
    "WATERFALL_REDIS_URL": f"redis://:{REDIS_CREDENTIAL}@redis:6379/0",
    "WATERFALL_SERVICE_CLIENT_SECRET": SERVICE_CREDENTIAL,
    "WATERFALL_STORAGE_SECRET": STORAGE_CREDENTIAL,
    "WATERFALL_OWNER_DATABASE_URL": f"postgresql://waterfall:{OWNER_CREDENTIAL}@db:5432/waterfall",
    "WATERFALL_KEYCLOAK_DATABASE_URL": (
        f"postgresql://keycloak:{KEYCLOAK_DATABASE_CREDENTIAL}@db:5432/keycloak"
    ),
}
# Where a service of the test platform reaches Keycloak and the object storage: addresses that
# answer nothing.
PLATFORM_ADDRESSES = {
    "WATERFALL_KEYCLOAK_ADDRESS": "http://127.0.0.1:9/auth",
    "WATERFALL_STORAGE_ADDRESS": "http://127.0.0.1:9",
    "WATERFALL_STORAGE_ACCESS_KEY": "GK000000000000000000000000",
}
SECRETS = [
    DB_CREDENTIAL,
    REDIS_CREDENTIAL,
    STORAGE_CREDENTIAL,
    OWNER_CREDENTIAL,
    KEYCLOAK_DATABASE_CREDENTIAL,
    BEARER_JWT,
    SESSION_COOKIE,
    DECODED_CREDENTIAL,
    *PLATFORM_SECRETS.values(),
]


def nowhere() -> tuple[TaskQueue, Bucket]:
    """Give a queue and a bucket of the backups that a test which deposits nothing never reaches."""
    queue = TaskQueue.connect(PLATFORM_SECRETS["WATERFALL_REDIS_URL"], timeout=DEPOSIT_TIMEOUT)
    bucket = Bucket.connect(
        "backups",
        PLATFORM_ADDRESSES["WATERFALL_STORAGE_ADDRESS"],
        "us-east-1",
        PLATFORM_ADDRESSES["WATERFALL_STORAGE_ACCESS_KEY"],
        STORAGE_CREDENTIAL,
    )
    return queue, bucket


def service_role(database: URL) -> str:
    """Name the role the API and the worker connect as, which the migrations create (0002).

    It is named after the database the address designates: two databases of one server share
    no role of the service.
    """
    return f"{database.database}_service"


HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def operations(contract: OpenAPI) -> dict[str, tuple[str, str]]:
    """List the operations of the contract: identifier to method and full path."""
    prefix = (contract.spec / "servers" / 0 / "url").read_value()
    found: dict[str, tuple[str, str]] = {}
    for path, item in (contract.spec / "paths").items():
        for method, operation in item.items():
            if method in HTTP_METHODS:
                found[(operation / "operationId").read_value()] = (method.upper(), prefix + path)
    return found


def found_in(text: str) -> list[str]:
    """List the secrets and tokens of the test platform that the text contains."""
    return [secret for secret in SECRETS if secret in text]


class Logs:
    """The records the service wrote, read back from the stream they were written to."""

    def __init__(self, stream: io.StringIO) -> None:
        self.stream = stream

    @property
    def text(self) -> str:
        """Everything written, as the log would show it."""
        return self.stream.getvalue()

    @property
    def records(self) -> list[dict[str, Any]]:
        """Each line is one JSON record."""
        return [json.loads(line) for line in self.text.splitlines()]

    def named(self, event: str) -> list[dict[str, Any]]:
        """Return the records of one event."""
        return [record for record in self.records if record["event"] == event]


@contextmanager
def captured_logs(secrets: Iterable[str] = ()) -> Generator[Logs]:
    """Capture the logs in memory, ``secrets`` masked as a service masks its own, then restore."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    stream = io.StringIO()
    configure_logging("DEBUG", stream, secrets)
    try:
        yield Logs(stream)
    finally:
        root.handlers[:] = handlers
        root.setLevel(level)
        structlog.reset_defaults()


class ContractClient:
    """A client of the application whose every answer is checked against the contract."""

    def __init__(self, client: TestClient, contract: OpenAPI) -> None:
        self.client = client
        self.contract = contract

    def request(self, method: str, path: str, **kwargs: Any) -> Response:
        """Send the request; fail if the answer is not the one the contract describes."""
        response = self.client.request(method, path, **kwargs)
        target = urlsplit(path)
        request = MockRequest(
            "http://testserver",
            method.lower(),
            target.path,
            args=dict(parse_qs(target.query)),
        )
        conforming = MockResponse(
            response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            # An answer without content, a 204, has no type.
            content_type=response.headers.get("content-type", "").split(";")[0],
        )
        self.contract.validate_response(request, conforming)
        return response

    def get(self, path: str, **kwargs: Any) -> Response:
        """Send a GET and check the answer."""
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        """Send a POST and check the answer."""
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Response:
        """Send a PATCH and check the answer."""
        return self.request("PATCH", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Response:
        """Send a DELETE and check the answer."""
        return self.request("DELETE", path, **kwargs)


def bearer(token: str) -> dict[str, str]:
    """Give the header that carries an access token."""
    return {"Authorization": f"Bearer {token}"}


def raw_account(**overrides: object) -> dict[str, object]:
    """Give the columns of an account written by hand, with the changes a test asks for."""
    return {
        "id": uuid4(),
        "last_name": "Martin",
        "first_name": "Claire",
        "email": "claire.martin@example.org",
        "idp_subject": f"subject-{uuid4()}",
        "origin": "local",
        "created_at": datetime(2026, 10, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 10, 1, tzinfo=UTC),
        **overrides,
    }


# The locks a session of the database of the test waits for, but the watcher's own: a session of
# another database of the same server, another run of the tests, waits for its own (#670). By the
# database of the session, since a lock on a transaction names none.
WAITING = text(
    "SELECT count(*) FROM pg_locks AS held JOIN pg_stat_activity AS backend USING (pid) "
    "WHERE NOT held.granted AND held.pid <> pg_backend_pid() "
    "AND backend.datname = current_database()"
)


def wait_for_a_lock(database: Database) -> None:
    """Wait until a transaction waits for a lock another one holds, in 10 seconds at most."""
    deadline = time.monotonic() + 10
    with database.engine.connect() as watching:
        while time.monotonic() < deadline:
            if watching.scalar(WAITING):
                return
            watching.rollback()
            time.sleep(0.05)
    pytest.fail("no transaction waits for a lock")


class Watching(KeycloakAdmin):
    """The administration client of the service, noting what the database lends at each call.

    Before calling Keycloak, each call notes the connections taken out of the pool of the
    database: none may be while Keycloak is asked (#669). It calls Keycloak itself: no stand-in.
    """

    def __init__(self, keycloak: Keycloak, settings: ServiceSettings, database: Database) -> None:
        """Watch the pool of ``database``; nothing is noted yet."""
        super().__init__(keycloak, settings)
        pool = database.engine.pool
        assert isinstance(pool, QueuePool)
        self.pool = pool
        self.held: list[tuple[str, int]] = []

    def _note(self, call: str) -> None:
        self.held.append((call, self.pool.checkedout()))

    def read_account(self, subject: str) -> ProviderAccount | None:
        """Note, then read an account of the realm."""
        self._note("read_account")
        return super().read_account(subject)

    def create_account(self, identity: LocalIdentity) -> str | None:
        """Note, then create a local account of the realm."""
        self._note("create_account")
        return super().create_account(identity)

    def remove_account(self, subject: str) -> None:
        """Note, then remove an account of the realm."""
        self._note("remove_account")
        super().remove_account(subject)

    def send_invitation(self, subject: str) -> InvitationFailure | None:
        """Note, then have the extension mail an account its invitation."""
        self._note("send_invitation")
        return super().send_invitation(subject)

    def change_identity(self, subject: str, identity: LocalIdentity) -> bool:
        """Note, then give a local account of the realm another identity."""
        self._note("change_identity")
        return super().change_identity(subject, identity)

    def close_sessions(self, subject: str) -> None:
        """Note, then close the sessions of an account."""
        self._note("close_sessions")
        super().close_sessions(subject)

    def make_password_link(self, subject: str) -> PasswordLink | None:
        """Note, then have the extension make the password link of an account."""
        self._note("make_password_link")
        return super().make_password_link(subject)

    def set_locale(self, subject: str, locale: str | None) -> None:
        """Note, then give an account of the realm its language."""
        self._note("set_locale")
        super().set_locale(subject, locale)
