# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The service answers as the contract says, and exposes nothing the contract does not.

Every answer a test of the API reads passes through ``ContractClient``, which holds it to the
schema the contract declares for its operation and status: an answer that departs from it fails
the test, and the chain with it (WF-ARC-0060). The paths played against the service hold the
answers they traverse to the same contract, by Prism as a proxy (``make e2e-service``).
"""

from typing import TYPE_CHECKING, Any, cast

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from jsonschema_path import default_handlers
from openapi_core import OpenAPI
from openapi_core.templating.paths.exceptions import PathNotFound
from openapi_core.templating.responses.exceptions import ResponseNotFound
from openapi_core.validation.response.exceptions import InvalidData
from support import (
    BEARER_JWT,
    PLATFORM_SECRETS,
    SESSION_COOKIE,
    AmbiguousCompositionError,
    ContractClient,
    Logs,
    UndeclaredPropertyError,
    documents,
    found_in,
    operations,
)

from waterfall.api.app import create_app
from waterfall.platform.correlation import FORM

if TYPE_CHECKING:
    from collections.abc import Iterator

    from starlette.routing import BaseRoute

    from waterfall.api.authentication import Services


def xml_bodies(node: object) -> Iterator[dict[str, Any]]:
    """Give each ``application/xml`` body a document declares, at any depth."""
    if isinstance(node, dict):
        for key, value in cast("dict[str, Any]", node).items():
            if key == "application/xml" and isinstance(value, dict):
                yield cast("dict[str, Any]", value)
            else:
                yield from xml_bodies(value)
    elif isinstance(node, list):
        for each in cast("list[object]", node):
            yield from xml_bodies(each)


def test_the_liveness_probe_answers_ok_as_the_contract_says(client: ContractClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.requirement("WF-ARC-0060-A")
def test_every_route_of_the_application_is_an_operation_of_the_contract(
    contract: OpenAPI, services: Services
) -> None:
    declared = operations(contract)
    # The application describes what it serves; it just does not serve the description.
    served = create_app(services).openapi()["paths"]
    routes = {
        operation["operationId"]: (method.upper(), path)
        for path, item in served.items()
        for method, operation in item.items()
    }
    assert routes
    # A route left out of its own description would escape the comparison above.
    for route in create_app(services).routes:
        router = getattr(route, "original_router", None)
        for served_route in cast("list[BaseRoute]", router.routes) if router else [route]:
            assert isinstance(served_route, APIRoute)
            assert served_route.include_in_schema
    for operation_id, served in routes.items():
        assert declared[operation_id] == served


@pytest.mark.requirement("WF-ARC-0060-A")
@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json", "/api/v1/openapi.json"])
def test_no_page_of_documentation_and_no_openapi_document_is_served(
    path: str, client: ContractClient
) -> None:
    response = client.client.get(path)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.requirement("WF-ARC-0060-A")
def test_an_address_outside_the_contract_is_not_found(client: ContractClient) -> None:
    response = client.client.get("/api/v1/unknown")
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
def test_what_a_request_carries_is_not_written_to_the_logs(logs: Logs, services: Services) -> None:
    # A route that fails writes the refusal and its trace: where what a request carries — and
    # a secret of the platform that the failure quotes — could leak.
    app = create_app(services)

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


@pytest.mark.requirement("WF-ARC-0060-A")
@pytest.mark.parametrize(
    ("status", "body", "rejection"),
    [
        (200, {"status": 3}, InvalidData),
        (200, {}, InvalidData),
        (418, {"status": "ok"}, ResponseNotFound),
    ],
    ids=["a value outside its schema", "a field missing", "a status not declared"],
)
def test_a_response_that_the_contract_does_not_describe_is_rejected(
    contract: OpenAPI, status: int, body: dict[str, object], rejection: type[Exception]
) -> None:
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        return JSONResponse(body, status_code=status)

    with pytest.raises(rejection):
        ContractClient(TestClient(app), contract).get("/api/v1/health")


# A failed background task, as the contract's example ``task_failed`` gives it.
FAILED_TASK = {
    "task_id": "01926f3a-7c00-7000-8000-000000000931",
    "kind": "revision_mark",
    "status": "failed",
    "progress": 40,
    "submitted_at": "2026-06-03T14:05:00Z",
    "finished_at": "2026-06-03T14:07:00Z",
    "result_url": None,
}

# The current account, as the contract's example ``me_grid_settings`` gives it, its
# permissions cut short.
ME = {
    "user_id": "01926f3a-7c00-7000-8000-000000000301",
    "last_name": "Martin",
    "first_name": "Camille",
    "email": "camille.martin@example.com",
    "anonymized_at": None,
    "is_active": True,
    "origin": "local",
    "org_node_id": None,
    "org_node_label": None,
    "access_role_ids": ["01926f3a-7c00-7000-8000-000000000701"],
    "access_role_labels": ["Direction de projet"],
    "has_avatar": False,
    "audit": {
        "created_at": "2025-09-01T09:00:00Z",
        "created_by": {"kind": "platform"},
        "updated_at": "2026-06-03T14:05:00Z",
        "updated_by": {"kind": "platform"},
    },
    "lock_version": 3,
    "permissions": ["users.read"],
}

# A refusal whose field problem carries a sentence the contract does not declare.
REFUSAL_WITH_A_MESSAGE = {
    "code": "COMPONENT_UNAVAILABLE",
    "status": 503,
    "params": {"component": "database"},
    "correlation_id": "front-7f3a",
    "fields": [{"pointer": "/x", "code": "VALUE_REQUIRED", "message": "Champ requis"}],
}


@pytest.mark.requirement("WF-ARC-0110-A")
@pytest.mark.parametrize(
    ("route", "status", "body", "pointer"),
    [
        (
            "/api/v1/health",
            200,
            {"status": "ok", "hint": "Le compte est désactivé"},
            "/hint",
        ),
        ("/api/v1/health", 503, REFUSAL_WITH_A_MESSAGE, "/fields/0/message"),
        (
            "/api/v1/health",
            200,
            {"status": "ok", "a/b~c": "Phrase"},
            "/a~1b~0c",
        ),
        (
            "/api/v1/tasks/{task_id}",
            200,
            {
                **FAILED_TASK,
                "problem": {
                    "code": "HOURLY_RATE_MISSING",
                    "status": 422,
                    "detail": "Taux horaire manquant",
                },
            },
            "/problem/detail",
        ),
        (
            "/api/v1/me",
            200,
            {
                **ME,
                "display_preferences": {
                    "grids": {
                        "g": {
                            "sort": {"column": "label", "order": "asc", "msg": "Trié par nom"},
                        }
                    }
                },
            },
            "/display_preferences/grids/g/sort/msg",
        ),
    ],
    ids=[
        "at the top of the body",
        "in an object of a list",
        "escaped as RFC 6901 says",
        "in a nullable object",
        "in the value of an open object",
    ],
)
def test_an_answer_that_holds_a_property_its_schema_does_not_declare_is_rejected(
    contract: OpenAPI, route: str, status: int, body: dict[str, object], pointer: str
) -> None:
    # « Aucune réponse de l'API ne contient de phrase destinée à l'utilisateur » : a sentence
    # the contract does not declare, which openapi-core lets pass, fails the client of the tests.
    app = FastAPI()
    media = "application/json" if status == 200 else "application/problem+json"

    @app.get(route)
    def answer() -> JSONResponse:
        return JSONResponse(body, status_code=status, media_type=media)

    with pytest.raises(UndeclaredPropertyError) as rejected:
        ContractClient(TestClient(app), contract).get(route.format(task_id=FAILED_TASK["task_id"]))
    assert rejected.value.pointers == [pointer]


@pytest.mark.requirement("WF-ARC-0110-A")
def test_an_answer_that_is_not_json_is_validated_without_being_walked(contract: OpenAPI) -> None:
    # The Prometheus exposition is text: it holds no property, and the client lets it pass.
    app = FastAPI()
    exposition = "# HELP up Whether the service answers.\nup 1\n"

    @app.get("/api/v1/metrics")
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(exposition)

    response = ContractClient(TestClient(app), contract).get("/api/v1/metrics")
    assert (response.status_code, response.text) == (200, exposition)


@pytest.mark.requirement("WF-ARC-0110-A")
def test_an_object_the_contract_leaves_open_may_hold_any_property(contract: OpenAPI) -> None:
    # The parameters of a refusal name its condition by codes and values the contract leaves
    # open (``Problem.params``): the client does not refuse them.
    app = FastAPI()
    body = {
        "code": "COMPONENT_UNAVAILABLE",
        "status": 503,
        "params": {"component": "database", "retry": 3},
        "correlation_id": "front-7f3a",
    }

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        return JSONResponse(body, status_code=503, media_type="application/problem+json")

    response = ContractClient(TestClient(app), contract).get("/api/v1/health")
    assert response.json() == body


def minimal_contract(schema: dict[str, object]) -> OpenAPI:
    """Declare a single operation, ``GET /api/v1/health``, whose answer has the schema."""
    return OpenAPI.from_dict(
        {
            "openapi": "3.1.0",
            "info": {"title": "minimal", "version": "1"},
            "servers": [{"url": "/api/v1"}],
            "paths": {
                "/health": {
                    "get": {
                        "operationId": "health",
                        "responses": {
                            "200": {
                                "description": "the answer",
                                "content": {"application/json": {"schema": schema}},
                            }
                        },
                    }
                }
            },
        }
    )


def two_objects(part: str) -> dict[str, object]:
    """Compose two objects, each requiring the property it declares."""
    return {
        part: [
            {"type": "object", "required": ["a"], "properties": {"a": {"type": "string"}}},
            {"type": "object", "required": ["b"], "properties": {"b": {"type": "string"}}},
        ]
    }


@pytest.mark.requirement("WF-ARC-0110-A")
@pytest.mark.parametrize(
    ("schema", "body"),
    [
        (two_objects("oneOf"), {"a": "x"}),
        (two_objects("anyOf"), {"a": "x"}),
        (
            {
                "type": "object",
                "properties": {
                    "c": {"anyOf": [two_objects("oneOf"), {"type": "null"}]},
                },
            },
            {"c": {"a": "x"}},
        ),
        (
            {
                "oneOf": [
                    {"type": "array", "items": {"type": "string"}},
                    {"type": "array", "items": {"type": "integer"}},
                ]
            },
            ["x"],
        ),
    ],
    ids=["a oneOf of two objects", "an anyOf of two objects", "below a property", "two lists"],
)
def test_a_composition_of_which_more_than_one_branch_describes_an_object_is_refused(
    schema: dict[str, object], body: object
) -> None:
    # Held to both branches at once, an object of the first would be allowed what only the
    # second declares: the client refuses to read the composition rather than open it.
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        return JSONResponse(body)

    with pytest.raises(AmbiguousCompositionError):
        ContractClient(TestClient(app), minimal_contract(schema)).get("/api/v1/health")


@pytest.mark.requirement("WF-ARC-0110-A")
def test_a_nullable_object_stays_closed() -> None:
    # The composition of shapes the contract writes, a schema or null, is read as its schema.
    schema: dict[str, object] = {
        "type": "object",
        "properties": {"c": {"anyOf": [two_objects("allOf"), {"type": "null"}]}},
    }
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        return JSONResponse({"c": {"a": "x", "b": "y", "hint": "Phrase"}})

    with pytest.raises(UndeclaredPropertyError) as rejected:
        ContractClient(TestClient(app), minimal_contract(schema)).get("/api/v1/health")
    assert rejected.value.pointers == ["/c/hint"]


TEXT = {"type": "string"}


def closed_object(required: list[str], **properties: object) -> dict[str, object]:
    """Give an object that declares every property it may hold, requiring some of them."""
    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


@pytest.mark.requirement("WF-ARC-0110-A")
def test_an_object_of_closed_branches_apart_follows_the_one_whose_own_properties_it_carries() -> (
    None
):
    # ``ProblemParams.tasks`` (#2635): a task of an entry requires its node, a task of an import
    # its lineage, and neither declares the other's. Each element is held to its branch alone, so
    # a sentence below it is still found.
    node = {"type": "object", "properties": {"id": {"type": "string"}}}
    schema: dict[str, object] = {
        "type": "array",
        "items": {
            "oneOf": [
                closed_object(["node", "label"], node=node, label=TEXT),
                closed_object(["lineage", "label"], lineage=TEXT, label=TEXT),
            ]
        },
    }
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        return JSONResponse(
            [
                {"lineage": "l", "label": "Essais"},
                {"node": {"id": "n", "hint": "Phrase"}, "label": "Câblage"},
            ]
        )

    with pytest.raises(UndeclaredPropertyError) as rejected:
        ContractClient(TestClient(app), minimal_contract(schema)).get("/api/v1/health")
    assert rejected.value.pointers == ["/1/node/hint"]


@pytest.mark.requirement("WF-ARC-0110-A")
@pytest.mark.parametrize(
    ("objects", "body"),
    [
        (
            [closed_object(["a"], a=TEXT), closed_object(["a"], a=TEXT)],
            {"a": "x"},
        ),
        (
            [
                closed_object(["a"], a=TEXT),
                {"type": "object", "required": ["b"], "properties": {"b": TEXT}},
            ],
            {"b": "y"},
        ),
        (
            [closed_object(["a"], a=TEXT, b=TEXT), closed_object(["b"], b=TEXT)],
            {"a": "x", "b": "y"},
        ),
    ],
    ids=["closed, the same required", "one closed, one open", "a required the other declares"],
)
def test_closed_branches_an_object_may_follow_both_of_are_refused(
    objects: list[dict[str, object]], body: dict[str, str]
) -> None:
    # Closing is not enough: each branch must be closed and require what no other declares, or a
    # value of one would be read as both.
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        return JSONResponse(body)

    with pytest.raises(AmbiguousCompositionError):
        ContractClient(TestClient(app), minimal_contract({"anyOf": objects})).get("/api/v1/health")


@pytest.mark.requirement("WF-ARC-0060-A")
@pytest.mark.parametrize(
    "body",
    [{"a": "x", "b": "y"}, {}],
    ids=["the own properties of both branches", "the own properties of none"],
)
def test_an_object_of_closed_branches_apart_that_fits_not_exactly_one_is_refused_by_the_schema(
    body: dict[str, str],
) -> None:
    # ``apart`` follows the one branch whose own properties a value carries; a value carrying those
    # of both, or of none, is refused before the walk, by the validation of the answer against the
    # schema. Were that validation skipped, the walk would follow both branches.
    schema: dict[str, object] = {
        "oneOf": [closed_object(["a"], a=TEXT), closed_object(["b"], b=TEXT)]
    }
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        return JSONResponse(body)

    with pytest.raises(InvalidData):
        ContractClient(TestClient(app), minimal_contract(schema)).get("/api/v1/health")


@pytest.mark.requirement("WF-ARC-0060-A")
def test_an_answer_to_an_operation_the_contract_does_not_declare_is_rejected(
    contract: OpenAPI,
) -> None:
    app = FastAPI()

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {"version": "1"}

    with pytest.raises(PathNotFound):
        ContractClient(TestClient(app), contract).get("/api/v1/version")


def test_a_path_with_a_query_string_is_validated_as_the_application_serves_it(
    client: ContractClient,
) -> None:
    response = client.get("/api/v1/health?x=1&x=2")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


@pytest.mark.requirement("WF-ARC-0060-A")
def test_an_xml_answer_the_contract_declares_binary_is_validated_as_its_bytes() -> None:
    # The file of MS Project (#2675): openapi-core would parse it into a tree of XML, then refuse
    # the tree as no string; its bytes are the string the contract declares.
    content = "<?xml version='1.0'?><Project><Name>Études</Name></Project>".encode()
    schema: dict[str, object] = {"type": "string", "format": "binary"}
    declared = cast("dict[str, Any]", minimal_contract(schema).spec.read_value())
    answer = declared["paths"]["/health"]["get"]["responses"]["200"]
    answer["content"] = {"application/xml": {"schema": schema}}
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> Response:
        return Response(content, media_type="application/xml")

    response = ContractClient(TestClient(app), OpenAPI.from_dict(declared)).get("/api/v1/health")
    assert (response.status_code, response.content) == (200, content)


def test_the_only_xml_body_of_the_contract_is_a_binary_string(contract: OpenAPI) -> None:
    # ``BINARY_TYPES`` reads every ``application/xml`` body as the text of its bytes: that holds
    # while the contract declares no such body but a binary string (the MS Project export).
    declared = cast("dict[str, Any]", contract.spec.read_value())
    root = contract.spec.base_uri
    found = documents(root, declared)
    binary = {"type": "string", "format": "binary"}
    xml = [
        address
        for address, each in found.items()
        for node in xml_bodies(each)
        if node.get("schema") != binary
    ]
    assert xml == []


def test_an_answer_is_validated_without_reading_a_document_of_the_contract_again(
    contract: OpenAPI, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The documents the schemas of the contract reach are read once, when a client is first given
    # it (#2720): the validation of a refusal, held to ``common.yaml#/Problem`` through
    # ``responses.yaml``, reads none of them again, nor does a second client.
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> JSONResponse:
        refusal = {"code": "COMPONENT_UNAVAILABLE", "status": 503, "correlation_id": "front-7f3a"}
        return JSONResponse(refusal, status_code=503, media_type="application/problem+json")

    first = ContractClient(TestClient(app), contract)
    read: list[str] = []
    reading = default_handlers["file"]

    def counted(address: str) -> object:
        read.append(address)
        return reading(address)

    monkeypatch.setitem(default_handlers, "file", counted)
    second = ContractClient(TestClient(app), contract)
    assert second.get("/api/v1/health").status_code == 503
    assert read == []
    assert second.contract is first.contract
    # The other way round, to prove the listener hears what it should: the contract as it was
    # given, not resolved, reads the documents it reaches when it is asked for them.
    asked = contract.spec / "paths" / "/health" / "get" / "responses" / "503" / "content"
    assert asked.exists()
    assert any(address.endswith("responses.yaml") for address in read)
    read.clear()
    # An example, which no validation resolves, is not held: it is read when it is asked for.
    examples = second.contract.spec / "paths" / "/health" / "get" / "responses" / "200"
    examples = examples / "content" / "application/json" / "examples"
    assert (examples / "ok" / "value").read_value() == {"status": "ok"}
    assert [address.rpartition("/")[2] for address in read] == ["liveness.json"]
