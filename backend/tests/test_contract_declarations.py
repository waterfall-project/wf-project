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
"""

from pathlib import Path
from typing import Any, cast

import yaml
from support import CONTRACT

METHODS = ("get", "put", "post", "patch", "delete")


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
