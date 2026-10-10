# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What the tests of the service share: the secrets of a test platform, the logs, the contract."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx2 import Response
from openapi_core import OpenAPI
from openapi_core.testing import MockRequest, MockResponse

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
PLATFORM_SECRETS = {
    "WATERFALL_DATABASE_URL": f"postgresql://waterfall:{DB_CREDENTIAL}@db:5432/waterfall",
    "WATERFALL_REDIS_URL": f"redis://:{REDIS_CREDENTIAL}@redis:6379/0",
    "WATERFALL_SERVICE_CLIENT_SECRET": SERVICE_CREDENTIAL,
}
# Where a service of the test platform reaches Keycloak: an address that answers nothing.
PLATFORM_ADDRESSES = {"WATERFALL_KEYCLOAK_ADDRESS": "http://127.0.0.1:9/auth"}
SECRETS = [
    DB_CREDENTIAL,
    REDIS_CREDENTIAL,
    BEARER_JWT,
    SESSION_COOKIE,
    DECODED_CREDENTIAL,
    *PLATFORM_SECRETS.values(),
]


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

    def delete(self, path: str, **kwargs: Any) -> Response:
        """Send a DELETE and check the answer."""
        return self.request("DELETE", path, **kwargs)


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
