# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Every error of the API leaves in the envelope of the contract: one place, one shape.

The typed exceptions of the core, the errors of validation, the errors of the framework and
the exceptions nobody expected all end in ``Problem`` (WF-ARC-0110): a code and its
parameters, never a sentence, and the correlation identifier that finds the error in the logs.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from waterfall.api.contract.models import ErrorCode, FieldProblem, Params, Problem
from waterfall.platform.correlation import HEADER, SCOPE_KEY
from waterfall.platform.errors import FieldError, ServiceError
from waterfall.platform.logs import get_logger

MEDIA_TYPE = "application/problem+json"

logger = get_logger(__name__)

# What Pydantic calls a fault, said as the code of the contract that a field gets.
_NUMBER_FAULTS = {
    "int_parsing",
    "int_type",
    "int_from_float",
    "float_parsing",
    "float_type",
    "decimal_parsing",
    "decimal_type",
}
_INCLUSIVE_BOUNDS = {"greater_than_equal": "minimum", "less_than_equal": "maximum"}
_UNREADABLE_BODY = {"missing", "model_attributes_type", "dict_type"}
_UUID_FAULTS = {"uuid_parsing", "uuid_type"}


def problem_response(
    request: Request,
    status: int,
    code: str,
    params: Mapping[str, Any] | None = None,
    fields: tuple[FieldError, ...] = (),
) -> JSONResponse:
    """Build the envelope of an error. A code the contract does not know is a defect."""
    correlation_id: str = request.scope[SCOPE_KEY]
    problem = Problem(
        code=ErrorCode(code),
        status=status,
        params=Params.model_validate(dict(params)) if params else None,
        fields=[
            FieldProblem(
                pointer=field.pointer,
                code=ErrorCode(field.code),
                params=dict(field.params) or None,
            )
            for field in fields
        ]
        or None,
        correlation_id=correlation_id,
    )
    return JSONResponse(
        problem.model_dump(mode="json", exclude_none=True),
        status_code=status,
        media_type=MEDIA_TYPE,
        headers={HEADER: correlation_id},
    )


def _on_service_error(request: Request, error: Exception) -> JSONResponse:
    refusal = cast("ServiceError", error)
    logger.info("request.refused", code=refusal.code, status=refusal.status)
    return problem_response(request, refusal.status, refusal.code, refusal.params, refusal.fields)


def _on_http_error(request: Request, error: Exception) -> JSONResponse:
    status = cast("HTTPException", error).status_code
    if status in {HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED}:
        return problem_response(request, 404, ErrorCode.NOT_FOUND)
    if status < HTTPStatus.INTERNAL_SERVER_ERROR:
        return problem_response(request, status, ErrorCode.MALFORMED_REQUEST)
    logger.error("request.failed", exc_info=error)
    return internal_error_response(request)


def _is_empty(value: object) -> bool:
    return isinstance(value, str | list | tuple | dict) and not value


def _field_of(fault: Mapping[str, Any]) -> FieldError:
    """Say a fault of Pydantic as the refusal of one field."""
    kind: str = fault["type"]
    place, *path = fault["loc"]
    if place in {"query", "path"}:
        pointer = f"/{place}/{path[0]}"
    else:
        pointer = "".join(f"/{part}" for part in path)
    params: dict[str, Any] = {}
    if kind == "missing":
        code = ErrorCode.VALUE_REQUIRED
    elif kind in {"string_too_long", "too_long"}:
        code = ErrorCode.VALUE_TOO_LONG
    elif kind in {"string_too_short", "too_short"}:
        # Only an empty value, where one value at least is asked, is a value that is lacking.
        lacking = fault.get("ctx", {}).get("min_length") == 1 and _is_empty(fault.get("input"))
        code = ErrorCode.VALUE_REQUIRED if lacking else ErrorCode.VALIDATION_FAILED
    elif kind in _INCLUSIVE_BOUNDS:
        code = ErrorCode.VALUE_OUT_OF_RANGE
        params[_INCLUSIVE_BOUNDS[kind]] = next(iter(fault["ctx"].values()))
    elif kind in _NUMBER_FAULTS:
        code = ErrorCode.NUMBER_INVALID
    elif kind.startswith("date"):
        code = ErrorCode.DATE_INVALID
    else:
        # Including an exclusive bound: the contract has no parameter to say one.
        code = ErrorCode.VALIDATION_FAILED
    return FieldError(pointer=pointer, code=code, params=params)


def _is_unreadable(fault: Mapping[str, Any]) -> bool:
    """Tell a body that is not JSON, or is absent or not an object: it cannot be read at all."""
    if fault["type"] == "json_invalid":
        return True
    return fault["loc"] == ("body",) and fault["type"] in _UNREADABLE_BODY


def _names_no_object(fault: Mapping[str, Any]) -> bool:
    """Tell an identifier of the path that is not an UUID: it cannot name an object."""
    return fault["loc"][0] == "path" and fault["type"] in _UUID_FAULTS


def _on_validation_error(request: Request, error: Exception) -> JSONResponse:
    """400 for a request the server cannot read, 404 for no object, 422 field by field.

    A body that is not JSON, absent or not an object, and a header or a cookie that does not
    parse, make the request unreadable. A malformed identifier in the path names no object:
    it is a 404, like an object that does not exist. Every other fault, a rule on a readable
    body included, is a value the entity refuses.
    """
    faults: list[Mapping[str, Any]] = list(cast("RequestValidationError", error).errors())
    places = {fault["loc"][0] for fault in faults}
    if any(_is_unreadable(fault) for fault in faults) or places & {"header", "cookie"}:
        return problem_response(request, 400, ErrorCode.MALFORMED_REQUEST)
    if any(_names_no_object(fault) for fault in faults):
        return problem_response(request, 404, ErrorCode.NOT_FOUND)
    return problem_response(
        request, 422, ErrorCode.VALIDATION_FAILED, fields=tuple(_field_of(f) for f in faults)
    )


def internal_error_response(request: Request) -> JSONResponse:
    """Answer an error nobody expected with a 500 that says nothing of it."""
    return problem_response(request, 500, ErrorCode.INTERNAL_ERROR)


def install_problem_handlers(app: FastAPI) -> None:
    """Route every kind of error of the application to the envelope."""
    app.add_exception_handler(ServiceError, _on_service_error)
    app.add_exception_handler(HTTPException, _on_http_error)
    app.add_exception_handler(RequestValidationError, _on_validation_error)
