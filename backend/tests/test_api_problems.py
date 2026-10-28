# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Every error leaves in the envelope of the contract, by one handler (WF-ARC-0110)."""

import threading
import time
from datetime import date
from enum import IntEnum, StrEnum
from typing import Annotated, Any
from uuid import UUID

import httpx2
import pytest
import uvicorn
from fastapi import FastAPI, Header, Path, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field, model_validator
from support import PLATFORM_SECRETS, Logs, found_in

from waterfall.api.app import create_app
from waterfall.api.authentication import Services
from waterfall.api.contract.models import DisplayPreferences, FieldProblem, Problem
from waterfall.platform.errors import (
    BadRequestError,
    ConflictError,
    FieldError,
    ForbiddenError,
    NotFoundError,
    PreconditionFailedError,
    ServiceError,
    UnauthenticatedError,
    UnavailableError,
    UnprocessableError,
)

PREFIX = "/api/v1"


class Entry(BaseModel):
    label: str = Field(max_length=5, min_length=1)
    amount: int = Field(ge=0)
    on: date


class Count(IntEnum):
    """An enumeration of integers, as the generator writes one: ``GridPreferences.page_size``."""

    ten = 10
    twenty_five = 25


class Digits(StrEnum):
    """An enumeration of words that are digits: strings, whatever they read as."""

    ten = "10"
    twenty_five = "25"


class Counted(BaseModel):
    count: Count | None = None
    digits: Digits | None = None


class Span(BaseModel):
    first: int
    last: int

    @model_validator(mode="after")
    def ordered(self) -> "Span":
        if self.last < self.first:
            message = "last before first"
            raise ValueError(message)
        return self


ERRORS: dict[str, Exception] = {
    "bad": BadRequestError("MALFORMED_REQUEST"),
    "unauthenticated": UnauthenticatedError("SESSION_EXPIRED"),
    "forbidden": ForbiddenError("PERMISSION_MISSING", {"missing_permission": "users.write"}),
    "missing": NotFoundError("NOT_FOUND"),
    "conflict": ConflictError(
        "STATE_FORBIDS_OPERATION", {"state": "terminated", "state_enum": "ProjectState"}
    ),
    "stale": PreconditionFailedError("STALE_LOCK_VERSION", {"expected_lock_version": 4}),
    "refused": UnprocessableError(
        "VALIDATION_FAILED",
        fields=(
            FieldError("/label", "VALUE_REQUIRED"),
            FieldError("/amount", "VALUE_OUT_OF_RANGE", {"minimum": 0}),
        ),
    ),
    "down": UnavailableError("COMPONENT_UNAVAILABLE", {"component": "database"}),
    "uncoded": UnprocessableError(
        "TASK_WITHOUT_WORKING_HOURS",
        {
            "resource_role_ids": [str(UUID(int=454))],
            "projects": [{"project_label": "Rénovation", "project_code": None}],
        },
    ),
    "unknown_code": ServiceError("NO_SUCH_CODE"),
    "unexpected": RuntimeError(f"cannot connect to {PLATFORM_SECRETS['WATERFALL_DATABASE_URL']}"),
}


def build_app(services: Services) -> FastAPI:
    """Build the application with routes of its own that fail in every way a route can."""
    app = create_app(services)

    @app.get("/fail/{kind}")
    def fail(kind: str) -> None:
        raise ERRORS[kind]

    @app.post("/refusals")
    def refuse(params: dict[str, Any]) -> None:
        code = "TASK_WITHOUT_WORKING_HOURS"
        raise UnprocessableError(code, params)

    @app.post("/entries")
    def enter(entry: Entry) -> Entry:
        return entry

    @app.post("/spans")
    def span(span: Span) -> Span:
        return span

    @app.post("/counted")
    def counted(counted: Counted) -> None:
        del counted

    @app.post("/preferences")
    def prefer(preferences: DisplayPreferences) -> None:
        del preferences

    @app.get("/things/{thing_id}")
    def read_thing(thing_id: UUID) -> str:
        return str(thing_id)

    @app.get("/years/{year}")
    def read_year(year: Annotated[int, Path(ge=2000, le=2100)]) -> int:
        return year

    @app.get("/stock")
    def stock(
        above: Annotated[int, Query(gt=0)] = 1,
        below: Annotated[int, Query(lt=10)] = 1,
        tags: Annotated[list[str] | None, Query(min_length=2)] = None,
        name: Annotated[str, Query(min_length=3)] = "abc",
    ) -> int:
        return above + below + len(tags or []) + len(name)

    @app.get("/nonempty")
    def nonempty(name: Annotated[str, Query(min_length=1)]) -> int:
        return len(name)

    @app.get("/search")
    def search(page: Annotated[int, Query(ge=1, le=9)] = 1) -> int:
        return page

    @app.get("/pattern")
    def pattern(code: Annotated[str, Query(pattern="^a$")]) -> str:
        return code

    @app.get("/headed")
    def headed(x: Annotated[int, Header()]) -> int:
        return x

    return app


@pytest.fixture
def app(services: Services) -> FastAPI:
    """Give a fresh application with those routes."""
    return build_app(services)


def problem_of(response: Any) -> Problem:
    """Read the body of an answer as the generated model of the envelope."""
    assert response.headers["content-type"] == "application/problem+json"
    return Problem.model_validate_json(response.content)


def params_of(field: FieldProblem) -> dict[str, Any] | None:
    """Read the parameters of a field refused as they travel, typed by the contract or not."""
    return None if field.params is None else field.params.model_dump(exclude_unset=True)


@pytest.mark.parametrize(
    ("kind", "status", "code"),
    [
        ("bad", 400, "MALFORMED_REQUEST"),
        ("unauthenticated", 401, "SESSION_EXPIRED"),
        ("forbidden", 403, "PERMISSION_MISSING"),
        ("missing", 404, "NOT_FOUND"),
        ("conflict", 409, "STATE_FORBIDS_OPERATION"),
        ("stale", 412, "STALE_LOCK_VERSION"),
        ("refused", 422, "VALIDATION_FAILED"),
        ("down", 503, "COMPONENT_UNAVAILABLE"),
    ],
)
def test_an_exception_of_the_core_is_rendered_with_its_status_and_its_code(
    app: FastAPI, kind: str, status: int, code: str
) -> None:
    response = TestClient(app).get(f"/fail/{kind}")
    problem = problem_of(response)
    assert (response.status_code, problem.status, problem.code.value) == (status, status, code)


def test_the_parameters_and_the_fields_of_an_exception_travel_in_the_envelope(
    app: FastAPI,
) -> None:
    client = TestClient(app)
    assert problem_of(client.get("/fail/stale")).model_dump(exclude_none=True)["params"] == {
        "expected_lock_version": 4
    }
    fields = problem_of(client.get("/fail/refused")).fields
    assert fields is not None
    assert [(f.pointer, f.code.value, params_of(f)) for f in fields] == [
        ("/label", "VALUE_REQUIRED", None),
        ("/amount", "VALUE_OUT_OF_RANGE", {"minimum": 0}),
    ]


@pytest.mark.requirement("WF-ARC-0110-A")
def test_a_null_the_typed_parameters_carry_travels_and_nothing_absent_is_sent(
    app: FastAPI,
) -> None:
    # The parameters several refusals share are typed by the contract (`ProblemParams`, #768):
    # the code of a project without one is null, and stays so in the envelope; what the error
    # does not give — its fields, here — is absent, never null.
    response = TestClient(app).get("/fail/uncoded")
    body = response.json()
    assert body["params"] == {
        "resource_role_ids": [str(UUID(int=454))],
        "projects": [{"project_label": "Rénovation", "project_code": None}],
    }
    assert "fields" not in body
    problem = problem_of(response)
    assert problem.params is not None
    assert problem.params.projects is not None
    assert problem.params.projects[0].project_code is None


ROLE = {"resource_role_id": str(UUID(int=454)), "code": "MONT-CAB", "label": "Monteur"}
TASK = {"project_id": str(UUID(int=1)), "node_id": str(UUID(int=2)), "label": "Câblage"}
IMPORTED = {"lineage_id": str(UUID(int=3)), "label": "Câblage"}
LINE = {
    "structure_id": str(UUID(int=4)),
    "structure_label": "Principale",
    "node_id": str(UUID(int=5)),
    "row_number": 2,
    "label": "Essais",
}
SHAPES: list[tuple[str, Any]] = [
    ("columns", ["wbs_element", "document_number"]),
    ("estimate_lines", [LINE]),
    ("missing_columns", [{"column": "amount", "labels": ["Montant", "Amount"]}]),
    ("resource_roles", [ROLE]),
    ("subproject", {"subproject_id": str(UUID(int=6)), "label": "Poste"}),
    ("tasks", [TASK]),
    ("tasks", [IMPORTED]),
]
"""Each typed parameter by its name and a value of a shape the contract gives: `tasks` twice, a task
named by its node and a task imported, named by its lineage (`ProblemImportedTask`)."""


@pytest.mark.requirement("WF-ARC-0110-A")
@pytest.mark.parametrize(("name", "value"), SHAPES)
def test_a_valid_typed_parameter_leaves_the_envelope_as_it_was_given(
    app: FastAPI, name: str, value: Any
) -> None:
    response = TestClient(app).post("/refusals", json={name: value})
    assert (response.status_code, response.json()["params"]) == (422, {name: value})


INVALID_SHAPES: list[dict[str, Any]] = [
    {"resource_roles": [{"code": "MONT-CAB"}]},
    {"tasks": [{"label": "Câblage"}]},
    {"subproject": "SP-1"},
    {"missing_columns": [{"column": "unknown", "labels": []}]},
    {"columns": ["unknown"]},
]


@pytest.mark.requirement("WF-ARC-0110-A")
@pytest.mark.parametrize("params", INVALID_SHAPES)
def test_a_typed_parameter_of_a_shape_the_contract_does_not_give_is_an_internal_error(
    app: FastAPI, params: dict[str, Any]
) -> None:
    response = TestClient(app, raise_server_exceptions=False).post(
        "/refusals", json=params, headers={"X-Correlation-ID": "trace-shape"}
    )
    problem = problem_of(response)
    assert (response.status_code, problem.code.value) == (500, "INTERNAL_ERROR")
    assert problem.correlation_id == "trace-shape"
    assert problem.params is None


@pytest.mark.requirement("WF-ARC-0110-A")
def test_a_typed_parameter_given_as_none_is_left_out_but_an_open_one_travels(
    app: FastAPI,
) -> None:
    response = TestClient(app).post(
        "/refusals", json={"subproject": None, "tasks": None, "other": None, "columns": []}
    )
    assert response.json()["params"] == {"other": None, "columns": []}


@pytest.mark.requirement("WF-OBS-0020-A")
def test_the_correlation_identifier_of_the_request_is_in_the_envelope_and_the_header(
    app: FastAPI,
) -> None:
    response = TestClient(app).get("/fail/missing", headers={"X-Correlation-ID": "trace-42"})
    assert problem_of(response).correlation_id == "trace-42"
    assert response.headers["X-Correlation-ID"] == "trace-42"


def test_an_unexpected_exception_is_a_500_with_a_correlation_and_no_detail(
    app: FastAPI, logs: Logs
) -> None:
    response = TestClient(app, raise_server_exceptions=False).get(
        "/fail/unexpected", headers={"X-Correlation-ID": "trace-500"}
    )
    problem = problem_of(response)
    assert (response.status_code, problem.code.value) == (500, "INTERNAL_ERROR")
    assert problem.correlation_id == "trace-500"
    assert response.headers["X-Correlation-ID"] == "trace-500"
    assert found_in(response.text) == []
    (failure,) = logs.named("request.failed")
    assert failure["correlation_id"] == "trace-500"
    assert failure["actor"] == "anonymous"
    assert "RuntimeError" in failure["exception"]
    ours = [record["event"] for record in logs.records if record["event"].startswith("request.")]
    assert ours == ["request.failed", "request.completed"]
    assert logs.named("request.completed")[0]["status"] == 500


@pytest.mark.requirement("WF-OBS-0020-A")
def test_a_secret_in_an_unexpected_exception_is_in_no_line_of_the_logs(
    app: FastAPI, logs: Logs
) -> None:
    TestClient(app, raise_server_exceptions=False).get("/fail/unexpected")
    assert "cannot connect to" in logs.text
    assert found_in(logs.text) == []


@pytest.mark.requirement("WF-OBS-0020-A")
def test_an_unexpected_exception_under_a_real_server_is_logged_once_with_its_correlation(
    app: FastAPI, logs: Logs
) -> None:
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_config=None, access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        while not server.started:
            time.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]
        response = httpx2.get(
            f"http://127.0.0.1:{port}/fail/unexpected", headers={"X-Correlation-ID": "live-1"}
        )
    finally:
        server.should_exit = True
        thread.join(timeout=30)
    assert (response.status_code, problem_of(response).correlation_id) == (500, "live-1")
    traces = [record for record in logs.records if "exception" in record]
    assert [record["event"] for record in traces] == ["request.failed"]
    assert traces[0]["correlation_id"] == "live-1"
    assert found_in(logs.text) == []


def test_a_code_the_contract_does_not_know_is_an_internal_error(app: FastAPI) -> None:
    response = TestClient(app, raise_server_exceptions=False).get("/fail/unknown_code")
    assert (response.status_code, problem_of(response).code.value) == (500, "INTERNAL_ERROR")


def test_a_route_that_does_not_exist_is_a_not_found_in_the_envelope(app: FastAPI) -> None:
    response = TestClient(app).get("/nowhere")
    assert (response.status_code, problem_of(response).code.value) == (404, "NOT_FOUND")


def test_a_method_the_route_does_not_serve_is_a_not_found(app: FastAPI) -> None:
    response = TestClient(app).post(f"{PREFIX}/health")
    assert (response.status_code, problem_of(response).code.value) == (404, "NOT_FOUND")


def test_a_path_with_a_slash_the_contract_does_not_write_is_not_redirected(app: FastAPI) -> None:
    response = TestClient(app, follow_redirects=False).get(f"{PREFIX}/health/")
    assert (response.status_code, problem_of(response).code.value) == (404, "NOT_FOUND")
    assert "location" not in response.headers


def test_a_body_that_is_not_json_is_a_malformed_request(app: FastAPI) -> None:
    response = TestClient(app).post(
        "/entries", content="{nope", headers={"content-type": "application/json"}
    )
    assert (response.status_code, problem_of(response).code.value) == (400, "MALFORMED_REQUEST")


def test_a_missing_body_is_a_malformed_request(app: FastAPI) -> None:
    response = TestClient(app).post("/entries")
    assert (response.status_code, problem_of(response).code.value) == (400, "MALFORMED_REQUEST")


def test_a_header_that_cannot_be_read_is_a_malformed_request(app: FastAPI) -> None:
    response = TestClient(app).get("/headed")
    assert (response.status_code, problem_of(response).code.value) == (400, "MALFORMED_REQUEST")


def test_the_values_of_a_body_that_are_refused_are_a_422_with_one_field_each(
    app: FastAPI,
) -> None:
    response = TestClient(app).post("/entries", json={"label": "too long", "amount": -1, "on": "x"})
    problem = problem_of(response)
    assert (response.status_code, problem.code.value) == (422, "VALIDATION_FAILED")
    assert problem.fields is not None
    assert {(f.pointer, f.code.value): params_of(f) for f in problem.fields} == {
        ("/label", "VALUE_TOO_LONG"): None,
        ("/amount", "VALUE_OUT_OF_RANGE"): {"minimum": 0},
        ("/on", "DATE_INVALID"): None,
    }


def test_a_missing_or_empty_field_is_a_value_required(app: FastAPI) -> None:
    problem = problem_of(TestClient(app).post("/entries", json={"label": "", "on": "2026-06-30"}))
    assert problem.fields is not None
    assert {(f.pointer, f.code.value) for f in problem.fields} == {
        ("/label", "VALUE_REQUIRED"),
        ("/amount", "VALUE_REQUIRED"),
    }


def test_a_number_that_is_not_one_is_a_number_invalid(app: FastAPI) -> None:
    problem = problem_of(
        TestClient(app).post("/entries", json={"label": "a", "amount": "many", "on": "2026-06-30"})
    )
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [("/amount", "NUMBER_INVALID")]


def test_a_query_parameter_that_is_refused_is_named_under_query(app: FastAPI) -> None:
    response = TestClient(app).get("/search", params={"page": 10})
    problem = problem_of(response)
    assert response.status_code == 422
    assert problem.fields is not None
    assert [(f.pointer, f.code.value, params_of(f)) for f in problem.fields] == [
        ("/query/page", "VALUE_OUT_OF_RANGE", {"maximum": 9})
    ]


def test_a_query_parameter_of_the_wrong_type_is_a_422(app: FastAPI) -> None:
    problem = problem_of(TestClient(app).get("/search", params={"page": "x"}))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [
        ("/query/page", "NUMBER_INVALID")
    ]
    assert problem.code.value == "VALIDATION_FAILED"


def test_a_body_that_is_not_an_object_is_a_malformed_request(app: FastAPI) -> None:
    response = TestClient(app).post("/entries", json=["not", "an", "object"])
    assert (response.status_code, problem_of(response).code.value) == (400, "MALFORMED_REQUEST")


def test_any_other_fault_is_a_validation_failed_on_its_field(app: FastAPI) -> None:
    problem = problem_of(TestClient(app).get("/pattern", params={"code": "b"}))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [
        ("/query/code", "VALIDATION_FAILED")
    ]


def test_a_nul_in_an_item_of_a_list_is_pointed_at_the_item(app: FastAPI) -> None:
    sent = {"grids": {"tasks": {"hidden_columns": ["a", "\x00"]}}}
    problem = problem_of(TestClient(app).post("/preferences", json=sent))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [
        ("/grids/tasks/hidden_columns/1", "VALIDATION_FAILED")
    ]


def test_an_integer_out_of_an_enumeration_of_integers_alone_is_a_value_out_of_range(
    app: FastAPI,
) -> None:
    # The number of lines per page is one of four integers: another integer is out of the range
    # the contract admits (#1045). The theme is one of three words: an integer sent there is a
    # value of another kind, refused as any other value, not a value out of range.
    sent = {"theme": 3, "grids": {"users": {"page_size": 30}}}
    problem = problem_of(TestClient(app).post("/preferences", json=sent))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value, params_of(f)) for f in problem.fields] == [
        ("/theme", "VALIDATION_FAILED", None),
        ("/grids/users/page_size", "VALUE_OUT_OF_RANGE", None),
    ]


# What a model of its own sends to an enumeration, and the code its field gets: Pydantic says the
# values an enumeration of integers admits bare (« 10 or 25 »), those of words quoted
# (« '10' or '25' »), whatever they read as. A drift of that wording fails here, on models that
# owe nothing to the contract; a change of the contract fails the tests of its fields.
ENUMERATED: list[tuple[dict[str, Any], str]] = [
    ({"count": 30}, "VALUE_OUT_OF_RANGE"),
    ({"count": -1}, "VALUE_OUT_OF_RANGE"),
    ({"count": "30"}, "VALIDATION_FAILED"),
    ({"count": 30.0}, "VALIDATION_FAILED"),
    ({"count": "ten"}, "VALIDATION_FAILED"),
    ({"count": False}, "VALIDATION_FAILED"),
    ({"digits": 30}, "VALIDATION_FAILED"),
    ({"digits": 25}, "VALIDATION_FAILED"),
    ({"digits": "30"}, "VALIDATION_FAILED"),
]


@pytest.mark.parametrize(("sent", "code"), ENUMERATED)
def test_only_an_integer_sent_to_an_enumeration_of_integers_is_out_of_its_range(
    app: FastAPI, sent: dict[str, Any], code: str
) -> None:
    problem = problem_of(TestClient(app).post("/counted", json=sent))
    assert problem.fields is not None
    [(name, _)] = sent.items()
    assert [(f.pointer, f.code.value, params_of(f)) for f in problem.fields] == [
        (f"/{name}", code, None)
    ]


def test_a_value_an_enumeration_admits_is_read_whatever_it_is_sent_as(app: FastAPI) -> None:
    # 25, "25" and 25.0 are 25; "25" is one of the words, 25 is not one.
    for sent in ({"count": 25}, {"count": "25"}, {"count": 25.0}, {"digits": "25"}):
        assert TestClient(app).post("/counted", json=sent).status_code == 200, sent


def test_an_identifier_in_the_path_that_cannot_name_an_object_is_a_not_found(
    app: FastAPI,
) -> None:
    response = TestClient(app).get("/things/not-an-identifier")
    assert (response.status_code, problem_of(response).code.value) == (404, "NOT_FOUND")


def test_a_rule_on_a_whole_body_that_can_be_read_is_a_422_not_a_malformed_request(
    app: FastAPI,
) -> None:
    response = TestClient(app).post("/spans", json={"first": 3, "last": 1})
    problem = problem_of(response)
    assert (response.status_code, problem.code.value) == (422, "VALIDATION_FAILED")
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [("", "VALIDATION_FAILED")]


@pytest.mark.parametrize("body", [None, [1, 2], "text", 3])
def test_a_body_that_is_null_or_not_an_object_is_a_malformed_request(
    app: FastAPI, body: Any
) -> None:
    response = TestClient(app).post("/spans", json=body)
    assert (response.status_code, problem_of(response).code.value) == (400, "MALFORMED_REQUEST")


def test_a_path_parameter_that_is_not_an_identifier_is_a_422_on_its_own_field(
    app: FastAPI,
) -> None:
    response = TestClient(app).get("/years/1999")
    problem = problem_of(response)
    assert (response.status_code, problem.code.value) == (422, "VALIDATION_FAILED")
    assert problem.fields is not None
    assert [(f.pointer, f.code.value, params_of(f)) for f in problem.fields] == [
        ("/path/year", "VALUE_OUT_OF_RANGE", {"minimum": 2000})
    ]


def test_a_path_parameter_of_the_wrong_type_is_a_number_invalid(app: FastAPI) -> None:
    problem = problem_of(TestClient(app).get("/years/next"))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [("/path/year", "NUMBER_INVALID")]


@pytest.mark.parametrize(
    ("parameters", "pointer"),
    [({"above": 0}, "/query/above"), ({"below": 10}, "/query/below")],
)
def test_an_exclusive_bound_is_a_validation_failed_the_contract_has_no_parameter_for(
    app: FastAPI, parameters: dict[str, int], pointer: str
) -> None:
    problem = problem_of(TestClient(app).get("/stock", params=parameters))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value, params_of(f)) for f in problem.fields] == [
        (pointer, "VALIDATION_FAILED", None)
    ]


def test_a_value_too_short_but_not_empty_is_a_validation_failed(app: FastAPI) -> None:
    problem = problem_of(TestClient(app).get("/stock", params={"name": "ab"}))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [
        ("/query/name", "VALIDATION_FAILED")
    ]


def test_a_list_too_short_but_not_empty_is_a_validation_failed(app: FastAPI) -> None:
    problem = problem_of(TestClient(app).get("/stock", params={"tags": ["one"]}))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [
        ("/query/tags", "VALIDATION_FAILED")
    ]


def test_an_empty_value_where_one_is_asked_is_a_value_required(app: FastAPI) -> None:
    problem = problem_of(TestClient(app).get("/nonempty", params={"name": ""}))
    assert problem.fields is not None
    assert [(f.pointer, f.code.value) for f in problem.fields] == [
        ("/query/name", "VALUE_REQUIRED")
    ]
