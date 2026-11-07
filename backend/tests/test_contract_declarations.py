# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The contract declares the refusals the service gives every operation of a kind (#799, #827).

The service refuses a query parameter out of its schema by 422 ``VALIDATION_FAILED``, on any
operation that has one, and a stale ``lock_version`` by 412 ``STALE_LOCK_VERSION``, on any
writing that carries one (``waterfall.api.problems``). An operation that does not declare them
gives an answer the contract does not hold, which ``ContractClient`` would refuse. And the other
way round, a 412 is declared only by a writing that sends a counter, in its body or among its
parameters, that may go stale: one that sends none declares a refusal it can never give (#1210).
The rules of ``redocly.yaml`` cannot read a parameter's place or a body's properties through
their references: the contract is read here, its references followed.

The parameters of the service are declared by hand, not by the models the contract engenders: the
bounds of each one, as the description of the application gives them, are held to those of the
contract (#1873). A bound that drifts, or is copied wrong, is found here and not by a user.
"""

import re
from dataclasses import dataclass, fields, replace
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated, Any, Literal, cast

import pytest
import yaml
from fastapi import Depends, FastAPI, Query
from support import CONTRACT

from waterfall.api.app import create_app

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from waterfall.api.authentication import Services

METHODS = ("get", "put", "post", "patch", "delete")


@dataclass(frozen=True, slots=True)
class Bounds:
    """What a schema bounds: a number from below and above, a text by its length and pattern.

    A list is bounded by its item count (``minItems``, ``maxItems``), and a value may be one of a
    set (``enum``) — an order of the contract's list that does not matter.

    A limit of a number is a value and whether it is excluded. OpenAPI 3.0 writes the exclusion
    as a boolean beside ``minimum``, 3.1 as the limit itself: both read the same here.
    """

    low: tuple[Decimal, bool] | None = None
    high: tuple[Decimal, bool] | None = None
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    enum: frozenset[Any] | None = None
    min_items: int | None = None
    max_items: int | None = None
    # The branches of an ``anyOf`` or ``oneOf`` that bound differently: a value follows one of them.
    either: tuple[Bounds, ...] = ()

    def _written(self, name: str) -> str:
        """Write a bound; a set in sorted order, which a hash would otherwise change per process."""
        value: object = getattr(self, name)
        if name == "enum" and self.enum is not None:
            return "{" + ", ".join(sorted(repr(item) for item in self.enum)) + "}"
        return repr(value)

    def shown(self) -> str:
        """Write the bounds that are set, and only them."""
        return (
            ", ".join(
                f"{field.name}={self._written(field.name)}"
                for field in fields(self)
                if getattr(self, field.name) not in (None, ())
            )
            or "nothing"
        )

    def over(self, other: Bounds) -> Bounds:
        """Complete these bounds by those of another schema the same value follows."""
        return Bounds(
            self.low or other.low,
            self.high or other.high,
            self.min_length if self.min_length is not None else other.min_length,
            self.max_length if self.max_length is not None else other.max_length,
            self.pattern if self.pattern is not None else other.pattern,
            self.enum if self.enum is not None else other.enum,
            self.min_items if self.min_items is not None else other.min_items,
            self.max_items if self.max_items is not None else other.max_items,
            self.either or other.either,
        )


def limit(schema: dict[str, Any], bound: str, exclusive: str) -> tuple[Decimal, bool] | None:
    """Read a limit of a number and whether it is excluded, in the form of either version."""
    excluded = schema.get(exclusive)
    if isinstance(excluded, bool):
        return (Decimal(str(schema[bound])), excluded) if bound in schema else None
    if excluded is not None:
        return Decimal(str(excluded)), True
    return (Decimal(str(schema[bound])), False) if bound in schema else None


def bounds_of(schema: Any, at: Any, follow: Callable[[Any, Any], tuple[Any, Any]]) -> Bounds:
    """Read the bounds of a schema, the schemas it is all of or one of included."""
    schema, at = follow(schema, at)
    if not isinstance(schema, dict):
        return Bounds()
    named = cast("dict[str, Any]", schema)
    found = Bounds(
        limit(named, "minimum", "exclusiveMinimum"),
        limit(named, "maximum", "exclusiveMaximum"),
        named.get("minLength"),
        named.get("maxLength"),
        named.get("pattern"),
        frozenset(named["enum"]) if "enum" in named else None,
        named.get("minItems"),
        named.get("maxItems"),
    )
    for each in cast("list[Any]", named.get("allOf") or []):
        found = found.over(bounds_of(each, at, follow))
    for part in ("anyOf", "oneOf"):
        # The branches are alternatives, not a conjunction; a ``null`` one (an optional parameter)
        # bounds nothing, and a single branch left is the schema itself.
        branches = [
            bounds_of(each, at, follow)
            for each in cast("list[Any]", named.get(part) or [])
            if follow(each, at)[0] != {"type": "null"}
        ]
        if len(branches) == 1:
            found = found.over(branches[0])
        elif branches:
            found = replace(found, either=tuple(branches))
    return found


def agrees(have: Bounds, want: Bounds) -> bool:
    """Tell the bounds a service declares as the contract's, its alternatives included.

    The contract may write a value as one of several schemas (an ``enum`` or a ``pattern``) where
    the service writes one pattern of both: that pattern must accept each value of each ``enum``
    and hold the pattern of each other branch.
    """
    if not want.either or have.either:
        return have == want
    if have.pattern is None or have.enum is not None:
        return False
    if replace(have, pattern=None) != replace(want, either=()):
        return False
    for branch in want.either:
        if branch.enum is not None and not all(
            re.fullmatch(have.pattern, str(value)) for value in branch.enum
        ):
            return False
        if branch.pattern is not None and branch.pattern.strip("^$") not in have.pattern:
            return False
    return True


class Contract:
    """The contract as its files are written, read with their references followed."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.files: dict[Path, Any] = {}

    def load(self, path: Path) -> Any:
        """Read a file of the contract once."""
        path = path.resolve()
        if path not in self.files:
            self.files[path] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return self.files[path]

    def follow(self, node: Any, base: Path) -> tuple[Any, Path]:
        """Follow the references of a node to what they name, and the file that holds it."""
        found: Any = node
        while isinstance(found, dict) and "$ref" in found:
            reference = cast("str", cast("dict[str, Any]", found)["$ref"])
            name, _, pointer = reference.partition("#")
            base = (base.parent / name).resolve() if name else base
            found = self.load(base)
            for part in filter(None, pointer.split("/")):
                found = found[part.replace("~1", "/").replace("~0", "~")]
        return cast("Any", found), base

    def properties(self, schema: Any, base: Path) -> set[str]:
        """Name the properties of a schema, those of the schemas it is all of included."""
        schema, base = self.follow(schema, base)
        if not isinstance(schema, dict):
            return set()
        named = cast("dict[str, Any]", schema)
        found = set(cast("dict[str, Any]", named.get("properties") or {}))
        for part in cast("list[Any]", named.get("allOf") or []):
            found |= self.properties(part, base)
        return found

    def operations(self) -> list[tuple[str, dict[str, Any], list[dict[str, Any]], Path]]:
        """List each operation: its identifier, itself, its parameters followed, its file."""
        listed: list[tuple[str, dict[str, Any], list[dict[str, Any]], Path]] = []
        for item in cast("dict[str, Any]", self.load(self.root)["paths"]).values():
            path_item, base = self.follow(item, self.root)
            shared = cast("list[Any]", path_item.get("parameters") or [])
            for method in METHODS:
                operation = cast("dict[str, Any] | None", path_item.get(method))
                if operation is None:
                    continue
                own = cast("list[Any]", operation.get("parameters") or [])
                parameters = [self.follow(each, base)[0] for each in shared + own]
                listed.append((operation["operationId"], operation, parameters, base))
        return listed

    def parameter_bounds(self) -> dict[str, dict[tuple[str, str], Bounds]]:
        """Give the bounds of each query or path parameter of each operation, by place and name."""
        found: dict[str, dict[tuple[str, str], Bounds]] = {}
        for item in cast("dict[str, Any]", self.load(self.root)["paths"]).values():
            path_item, base = self.follow(item, self.root)
            shared = cast("list[Any]", path_item.get("parameters") or [])
            for method in METHODS:
                operation = cast("dict[str, Any] | None", path_item.get(method))
                if operation is None:
                    continue
                own = cast("list[Any]", operation.get("parameters") or [])
                bounds: dict[tuple[str, str], Bounds] = {}
                for declared in shared + own:
                    parameter, where = self.follow(declared, base)
                    if parameter["in"] in {"query", "path"}:
                        # The references of a schema are read from the file of its parameter.
                        bounds[parameter["in"], parameter["name"]] = bounds_of(
                            parameter.get("schema"), where, self.follow
                        )
                found[operation["operationId"]] = bounds
        return found

    def statuses(self, operation: dict[str, Any]) -> set[str]:
        """Name the statuses an operation declares."""
        return {str(status) for status in cast("dict[Any, Any]", operation["responses"])}

    def carries_lock_version(
        self, operation: dict[str, Any], parameters: list[dict[str, Any]], base: Path
    ) -> bool:
        """Tell an operation that carries ``lock_version``: in its query, or in its body as JSON.

        A deletion sends the counter of its node in its query (#1210), as a writing with a body
        sends it in its body.
        """
        if any(
            each.get("in") == "query" and each.get("name") == "lock_version" for each in parameters
        ):
            return True
        body = operation.get("requestBody")
        if body is None:
            return False
        body, base = self.follow(body, base)
        content = cast("dict[str, Any]", body.get("content") or {})
        schema = cast("dict[str, Any]", content.get("application/json") or {}).get("schema")
        return schema is not None and "lock_version" in self.properties(schema, base)

    def sends_counter(
        self, operation: dict[str, Any], parameters: list[dict[str, Any]], base: Path
    ) -> bool:
        """Tell an operation that sends a counter: ``lock_version``, or ``…_lock_version``.

        In its body, read as JSON, or among its parameters: a merge sends the counters of its two
        structures, a deletion the counter of its node in its query (#1210).
        """
        names = {str(each.get("name")) for each in parameters}
        body = operation.get("requestBody")
        if body is not None:
            body, found = self.follow(body, base)
            content = cast("dict[str, Any]", body.get("content") or {})
            schema = cast("dict[str, Any]", content.get("application/json") or {}).get("schema")
            if schema is not None:
                names |= self.properties(schema, found)
        return any(name == "lock_version" or name.endswith("_lock_version") for name in names)


def without_422(contract: Contract) -> list[str]:
    """Name the operations with a query parameter that do not declare 422."""
    return [
        name
        for name, operation, parameters, _ in contract.operations()
        if any(each.get("in") == "query" for each in parameters)
        and "422" not in contract.statuses(operation)
    ]


def without_412(contract: Contract) -> list[str]:
    """Name the operations that carry ``lock_version`` and do not declare 412."""
    return [
        name
        for name, operation, parameters, base in contract.operations()
        if contract.carries_lock_version(operation, parameters, base)
        and "412" not in contract.statuses(operation)
    ]


def without_counter(contract: Contract) -> list[str]:
    """Name the operations that declare 412 and send no counter that could go stale."""
    return [
        name
        for name, operation, parameters, base in contract.operations()
        if "412" in contract.statuses(operation)
        and not contract.sends_counter(operation, parameters, base)
    ]


def served_bounds(served: dict[str, Any]) -> dict[str, dict[tuple[str, str], Bounds]]:
    """Give the bounds of each query or path parameter the application describes, by operation."""

    def resolve(node: Any, at: Any) -> tuple[Any, Any]:
        found: Any = node
        while isinstance(found, dict) and "$ref" in found:
            target: Any = served
            for part in cast("str", cast("dict[str, Any]", found)["$ref"]).split("/")[1:]:
                target = target[part]
            found = target
        return cast("tuple[Any, Any]", (found, at))

    return {
        operation["operationId"]: {
            (each["in"], each["name"]): bounds_of(each.get("schema"), None, resolve)
            for each in operation.get("parameters", [])
            if each["in"] in {"query", "path"}
        }
        for item in served["paths"].values()
        for operation in item.values()
    }


def drifting(contract: Contract, served: dict[str, Any]) -> dict[tuple[str, str, str], str]:
    """Name each parameter of a served operation whose declared bounds are not the contract's.

    A parameter the service declares and the contract does not is named too (#2185).
    """
    declared = contract.parameter_bounds()
    found: dict[tuple[str, str, str], str] = {}
    for operation, parameters in served_bounds(served).items():
        in_contract = declared.get(operation, {})
        for (place, name), have in parameters.items():
            if (place, name) not in in_contract:
                found[operation, place, name] = "not in the contract"
            elif not agrees(have, in_contract[place, name]):
                found[operation, place, name] = (
                    f"declared {have.shown()}, contract {in_contract[place, name].shown()}"
                )
    return found


def test_every_operation_with_a_query_parameter_declares_its_422() -> None:
    assert without_422(Contract(CONTRACT)) == []


def test_every_writing_that_carries_a_lock_version_declares_its_412() -> None:
    assert without_412(Contract(CONTRACT)) == []


def test_every_writing_that_declares_a_412_sends_a_counter() -> None:
    # #1210: a 412 nothing sent can make stale is a refusal the service never gives.
    assert without_counter(Contract(CONTRACT)) == []


def test_an_operation_that_lacks_either_is_found(tmp_path: Path) -> None:
    (tmp_path / "parameters.yaml").write_text(
        "Limit: { name: limit, in: query, schema: { type: integer } }\n", encoding="utf-8"
    )
    (tmp_path / "schemas.yaml").write_text(
        "Versioned: { properties: { lock_version: { type: integer } } }\n"
        "Change: { allOf: [{ $ref: '#/Versioned' },"
        " { properties: { label: { type: string } } }] }\n",
        encoding="utf-8",
    )
    (tmp_path / "openapi.yaml").write_text(
        "paths:\n"
        "  /things:\n"
        "    get:\n"
        "      operationId: listThings\n"
        "      parameters: [{ $ref: 'parameters.yaml#/Limit' }]\n"
        "      responses: { '200': {} }\n"
        "    patch:\n"
        "      operationId: changeThings\n"
        "      requestBody:\n"
        "        content: { application/json: { schema: { $ref: 'schemas.yaml#/Change' } } }\n"
        "      responses: { '200': {}, '400': {}, '422': {} }\n"
        "    delete:\n"
        "      operationId: deleteThings\n"
        "      responses: { '204': {}, '412': {} }\n"
        "  /others:\n"
        "    get:\n"
        "      operationId: listOthers\n"
        "      parameters: [{ $ref: 'parameters.yaml#/Limit' }]\n"
        "      responses: { '200': {}, '422': {} }\n"
        "    delete:\n"
        "      operationId: deleteOthers\n"
        "      parameters: [{ name: lock_version, in: query, schema: { type: integer } }]\n"
        "      responses: { '204': {}, '412': {}, '422': {} }\n"
        "  /stale:\n"
        "    delete:\n"
        "      operationId: deleteStale\n"
        "      parameters: [{ name: lock_version, in: query, schema: { type: integer } }]\n"
        "      responses: { '204': {}, '422': {} }\n",
        encoding="utf-8",
    )
    contract = Contract(tmp_path / "openapi.yaml")
    assert (without_422(contract), without_412(contract), without_counter(contract)) == (
        ["listThings"],
        ["changeThings", "deleteStale"],
        ["deleteThings"],
    )


# The drifts of the parameters a route checks itself, each pinned with its exact words: a change of
# one of them, or a new drift on the same parameter, fails the test. Every entry is a drift this
# test finds: one that no longer is fails it.
#
# The bounds of the table of the roles of access are read as integers with the other parameters
# and judged after them: a negative one ``NUMBER_INVALID``, named with the faults of the audit
# columns in one refusal (``role_filters``, ``listAccessRoles``). The contract names
# ``NUMBER_INVALID`` at the parameter, in 422; declared on the parameter, ``ge=0`` would give a
# validation 422 of another code.
#
# The same holds of the parameters read as text by a model of the query or by a route, whose
# refusal the contract names (#2185): the decimal bounds of the grid of the hourly rates and of the
# roles of resource (``pattern``), the actions of the journal (``minItems``). The correlation of
# the journal is declared by its model (``Field(pattern=CORRELATION)``, ``api/audit.py``), which
# FastAPI does not describe: a blind spot of this comparison, which reads the application
# description. The decision on these drifts is still to take (#2303).
#
# The sort column of the contributors of a project (EP-04, US-0930, ``listContributors``) is
# declared by a ``pattern`` where the contract names an ``enum``: the same three columns, read as
# text and judged by the route. The author of #2303 decided to keep this tolerance pinned.
CHECKED_BY_THE_ROUTE: dict[tuple[str, str, str], str] = {
    ("listAccessRoles", "query", "holder_count_min"): (
        "declared nothing, contract low=(Decimal('0'), False)"
    ),
    ("listAccessRoles", "query", "holder_count_max"): (
        "declared nothing, contract low=(Decimal('0'), False)"
    ),
    ("listAuditEvents", "query", "actions"): ("declared nothing, contract min_items=1"),
    ("listAuditEvents", "query", "correlation_id"): (
        "declared nothing, contract pattern='^[A-Za-z0-9._-]{1,64}$'"
    ),
    ("getHourlyRateGrid", "query", "rate_min"): (
        r"declared nothing, contract pattern='^-?\\d+(\\.\\d{1,2})?$'"
    ),
    ("getHourlyRateGrid", "query", "rate_max"): (
        r"declared nothing, contract pattern='^-?\\d+(\\.\\d{1,2})?$'"
    ),
    ("listResourceRoles", "query", "monthly_hours_min"): (
        r"declared nothing, contract pattern='^-?\\d+(\\.\\d+)?$'"
    ),
    ("listResourceRoles", "query", "monthly_hours_max"): (
        r"declared nothing, contract pattern='^-?\\d+(\\.\\d+)?$'"
    ),
    ("listResourceRoles", "query", "headcount_min"): (
        r"declared nothing, contract pattern='^-?\\d+(\\.\\d+)?$'"
    ),
    ("listResourceRoles", "query", "headcount_max"): (
        r"declared nothing, contract pattern='^-?\\d+(\\.\\d+)?$'"
    ),
    ("listContributors", "query", "sort_by"): (
        "declared pattern='^(display_name|kind|is_active)$', "
        "contract enum={'display_name', 'is_active', 'kind'}"
    ),
}


@pytest.mark.requirement("WF-ARC-0060-A")
def test_the_bounds_of_every_parameter_the_service_declares_are_those_of_the_contract(
    services: Services,
) -> None:
    # #1873: ``ge``, ``le``, ``gt``, ``lt``, ``min_length`` and ``max_length`` of the declaration
    # against ``minimum``, ``maximum``, their exclusion, ``minLength`` and ``maxLength``; and, since
    # #2185, ``pattern``, ``enum``, ``minItems`` and ``maxItems``, and a parameter the contract
    # lacks.
    found = drifting(Contract(CONTRACT), create_app(services).openapi())
    assert found == CHECKED_BY_THE_ROUTE, found


def list_things(
    limit: int = Query(50, ge=1, le=100),
    page: int = Query(1, gt=0),
    code: str | None = Query(None, min_length=1, max_length=20),
    kept: int = Query(1, ge=1),
) -> None:
    """Serve nothing: the declaration of its parameters is all the test reads."""
    del limit, page, code, kept


def list_more(
    *,
    reference: str = Query("a", pattern="^a$"),
    kind: Literal["a", "b"] = Query("a"),
    tags: Annotated[list[str] | None, Query(min_length=1, max_length=3)] = None,
    unknown: int = Query(1),
) -> None:
    """Declare the parameters of the other keywords, a dependency of the route."""
    del reference, kind, tags, unknown


def list_sorted(
    sort: str = Query("a", pattern=r"^(a|c\.[0-9]+)$"),
    sort_kept: str = Query("a", pattern=r"^(a|b|c\.[0-9]+)$"),
) -> None:
    """Declare a sort the contract writes as an enum or a pattern."""
    del sort, sort_kept


@pytest.mark.requirement("WF-ARC-0060-A")
def test_a_bound_that_drifts_from_the_contract_is_found(tmp_path: Path) -> None:
    (tmp_path / "parameters.yaml").write_text(
        "Limit: { name: limit, in: query, schema: { type: integer, minimum: 1, maximum: 500 } }\n"
        "Page: { name: page, in: query,"
        " schema: { type: integer, minimum: 0, exclusiveMinimum: true } }\n"
        "Code: { name: code, in: query, schema: { type: string, minLength: 1, maxLength: 20 } }\n"
        "Kept: { name: kept, in: query, schema: { type: integer, minimum: 1 } }\n"
        "Reference: { name: reference, in: query, schema: { type: string, pattern: '^b$' } }\n"
        "Kind: { name: kind, in: query, schema: { type: string, enum: [b, a, c] } }\n"
        "Sort: { name: sort, in: query, schema: { anyOf: ["
        "{ type: string, enum: [a, b] }, { type: string, pattern: '^c\\.[0-9]+$' }] } }\n"
        "SortKept: { name: sort_kept, in: query, schema: { anyOf: ["
        "{ type: string, enum: [a, b] }, { type: string, pattern: '^c\\.[0-9]+$' }] } }\n"
        "Tags: { name: tags, in: query,"
        " schema: { type: array, items: { type: string }, minItems: 1, maxItems: 4 } }\n",
        encoding="utf-8",
    )
    (tmp_path / "openapi.yaml").write_text(
        "paths:\n"
        "  /things:\n"
        "    get:\n"
        "      operationId: listThings\n"
        "      parameters:\n"
        "        - $ref: 'parameters.yaml#/Limit'\n"
        "        - $ref: 'parameters.yaml#/Page'\n"
        "        - $ref: 'parameters.yaml#/Code'\n"
        "        - $ref: 'parameters.yaml#/Kept'\n"
        "        - $ref: 'parameters.yaml#/Reference'\n"
        "        - $ref: 'parameters.yaml#/Kind'\n"
        "        - $ref: 'parameters.yaml#/Tags'\n"
        "        - $ref: 'parameters.yaml#/Sort'\n"
        "        - $ref: 'parameters.yaml#/SortKept'\n"
        "      responses: { '200': {}, '422': {} }\n",
        encoding="utf-8",
    )
    app = FastAPI()
    app.add_api_route(
        "/things",
        list_things,
        operation_id="listThings",
        dependencies=[Depends(list_more), Depends(list_sorted)],
    )
    found = drifting(Contract(tmp_path / "openapi.yaml"), app.openapi())
    # The limit is wrong above; the page excludes zero as the contract does, though 3.0 writes it
    # with a boolean and 3.1 with the limit itself; the code and the kept parameter agree. The
    # pattern, the set of the enum and the count of the items each drift, and a parameter the
    # contract lacks is named (#2185).
    assert found.keys() == {
        ("listThings", "query", "limit"),
        ("listThings", "query", "reference"),
        ("listThings", "query", "kind"),
        ("listThings", "query", "tags"),
        ("listThings", "query", "unknown"),
        ("listThings", "query", "sort"),
    }
    assert found["listThings", "query", "unknown"] == "not in the contract"
    limit_text = found["listThings", "query", "limit"]
    assert "high=(Decimal('100'), False)" in limit_text
    assert "high=(Decimal('500'), False)" in limit_text
    assert "pattern='^a$'" in found["listThings", "query", "reference"]
    assert "pattern='^b$'" in found["listThings", "query", "reference"]
    kind_text = found["listThings", "query", "kind"]
    assert "enum={'a', 'b'}" in kind_text
    assert "'c'" in kind_text
    tags_text = found["listThings", "query", "tags"]
    assert "min_items=1" in tags_text
    assert "max_items=3" in tags_text
    assert "max_items=4" in tags_text
    # The contract writes the sort as an enum or a pattern: the pattern served omits ``b``, which
    # the enum accepts, and is found; the one that holds both agrees.
    assert "pattern=" in found["listThings", "query", "sort"]
    assert "either=" in found["listThings", "query", "sort"]
