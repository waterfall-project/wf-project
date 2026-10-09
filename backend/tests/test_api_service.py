# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The service answers as the contract says, and exposes nothing the contract does not."""

from typing import TYPE_CHECKING, cast

import pytest
from fastapi import FastAPI, Request
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from openapi_core import OpenAPI
from openapi_core.exceptions import OpenAPIError
from support import (
    BEARER_JWT,
    PLATFORM_SECRETS,
    SESSION_COOKIE,
    ContractClient,
    Logs,
    found_in,
)

from waterfall.api.app import create_app
from waterfall.platform.correlation import FORM

if TYPE_CHECKING:
    from starlette.routing import BaseRoute

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


def test_the_liveness_probe_answers_ok_as_the_contract_says(client: ContractClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_every_route_of_the_application_is_an_operation_of_the_contract(
    contract: OpenAPI,
) -> None:
    declared = operations(contract)
    # The application describes what it serves; it just does not serve the description.
    served = create_app().openapi()["paths"]
    routes = {
        operation["operationId"]: (method.upper(), path)
        for path, item in served.items()
        for method, operation in item.items()
    }
    assert routes
    # A route left out of its own description would escape the comparison above.
    for route in create_app().routes:
        router = getattr(route, "original_router", None)
        for served_route in cast("list[BaseRoute]", router.routes) if router else [route]:
            assert isinstance(served_route, APIRoute)
            assert served_route.include_in_schema
    for operation_id, served in routes.items():
        assert declared[operation_id] == served


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/api/v1/openapi.json"])
def test_no_page_of_documentation_and_no_openapi_document_is_served(
    path: str, client: ContractClient
) -> None:
    response = client.client.get(path)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_a_request_without_a_correlation_identifier_gets_one(client: ContractClient) -> None:
    response = client.get("/api/v1/health")
    assert FORM.fullmatch(response.headers["X-Correlation-ID"])


def test_the_correlation_identifier_of_the_caller_is_kept_and_bound_to_the_logs(
    client: ContractClient, logs: Logs
) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "front-7f3a"})
    assert response.headers["X-Correlation-ID"] == "front-7f3a"
    (record,) = logs.named("request.completed")
    assert record["correlation_id"] == "front-7f3a"
    assert (record["method"], record["path"], record["status"]) == ("GET", "/api/v1/health", 200)
    assert record["actor"] == "anonymous"


def test_a_correlation_identifier_of_the_wrong_form_is_replaced(client: ContractClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "not valid!"})
    assert response.headers["X-Correlation-ID"] != "not valid!"


@pytest.mark.requirement("WF-OBS-0020-A")
def test_what_a_request_carries_is_not_written_to_the_logs(logs: Logs) -> None:
    # A route that fails writes the refusal and its trace: where what a request carries — and
    # a secret of the platform that the failure quotes — could leak.
    app = create_app()

    @app.get("/fail")
    def fail(request: Request) -> None:
        redis = PLATFORM_SECRETS["WATERFALL_REDIS_URL"]
        message = f"refused {len(request.cookies)} cookie, {redis}"
        raise RuntimeError(message)

    response = TestClient(app, raise_server_exceptions=False).get(
        "/fail", headers={"Authorization": f"Bearer {BEARER_JWT}", "Cookie": SESSION_COOKIE}
    )
    assert response.status_code == 500
    assert BEARER_JWT not in response.text
    assert logs.named("request.failed")
    assert "refused" in logs.text
    assert found_in(logs.text) == []


def test_a_response_that_the_contract_does_not_describe_is_rejected(contract: OpenAPI) -> None:
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> dict[str, int]:
        return {"status": 3}

    with pytest.raises(OpenAPIError):
        ContractClient(TestClient(app), contract).get("/api/v1/health")


def test_a_path_with_a_query_string_is_validated_as_the_application_serves_it(
    client: ContractClient,
) -> None:
    response = client.get("/api/v1/health?x=1&x=2")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})
