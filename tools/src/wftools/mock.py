# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Derive, from the bundled contract, the variant the fake back serves (US-0030).

Usage: ``python -m wftools.mock BUNDLE``, where BUNDLE is the contract bundled as JSON; the
file is rewritten in place.

Three differences, and only these, so that the fake back answers what the contract says:

- every path is prefixed with the path of the contract's server, ``/api/v1``: Prism serves
  paths at the root and ignores a relative server, and the front must call the fake back
  exactly as it will call the real service;
- no operation requires a bearer token: the fake back answers whoever calls it, as the account
  the mock-up starts from, and authentication is the real service's (EP-03);
- the nodes of a differential structure are read at the address of that structure: Prism serves
  the first example of an operation whatever the path, so the path of each structure of kind
  ``amendment`` that the first example of ``listCostStructures`` lists is repeated with its
  identifier written in, and ``listNodes`` there leads with its example ``amendment`` (#1219).
  Prism prefers a path with no parameter to a templated one.

No response is written here: responses are the examples of the contract.

The same variant serves Prism as a proxy in front of the real service (``make e2e-service``),
which holds every answer to the contract: there the service authenticates, and its refusal
passes as it answers it, where Prism, asking for a token, would answer one of its own.
"""

import json
import sys
from pathlib import Path
from typing import cast


def derive(contract: dict[str, object]) -> dict[str, object]:
    """Return the variant of a bundled contract the fake back serves."""
    servers = cast("list[dict[str, str]]", contract.get("servers", [{"url": ""}]))
    prefix = servers[0]["url"].rstrip("/")
    paths = cast("dict[str, dict[str, object]]", contract["paths"])
    derived_paths = {
        f"{prefix}{path}": {method: _without_security(field) for method, field in item.items()}
        for path, item in paths.items()
    }
    derived = {key: value for key, value in contract.items() if key != "security"}
    derived["servers"] = [{"url": "/"}]
    derived["paths"] = _with_amendment_nodes(contract, derived_paths, prefix)
    return derived


STRUCTURES_PATH = "/projects/{project_id}/revisions/{revision_id}/structures"
NODES_PATH = STRUCTURES_PATH + "/{structure_id}/nodes"
AMENDMENT_EXAMPLE = "amendment"
STRUCTURE_PARAMETER = "#/components/parameters/StructureId"
Item = dict[str, object]


def _with_amendment_nodes(
    contract: dict[str, object], paths: dict[str, Item], prefix: str
) -> dict[str, Item]:
    """Return the paths, plus the nodes of each differential structure at its own address."""
    nodes = paths.get(prefix + NODES_PATH)
    if nodes is None:
        return paths
    served = dict(paths)
    for structure in _amendment_structures(contract, paths.get(prefix + STRUCTURES_PATH)):
        address = prefix + NODES_PATH.replace("{structure_id}", structure)
        served[address] = _at_a_structure(nodes)
    return served


def _resolved(contract: dict[str, object], value: object) -> object:
    """Return what a reference to the examples of the components points at; others unchanged."""
    if isinstance(value, dict) and "$ref" in value:
        name = str(cast("Item", value)["$ref"]).rsplit("/", 1)[-1]
        components = cast("dict[str, Item]", contract.get("components", {}))
        return cast("Item", components.get("examples", {})).get(name, value)
    return value


def _examples(operation: Item) -> Item:
    """Return the examples of the JSON answer 200 of an operation."""
    responses = cast("dict[str, Item]", operation.get("responses", {}))
    content = cast("dict[str, Item]", responses.get("200", {}).get("content", {}))
    return cast("Item", content.get("application/json", {}).get("examples", {}))


def _amendment_structures(contract: dict[str, object], path: Item | None) -> list[str]:
    """Return the identifiers of the differential structures the first listing example names."""
    operation = cast("Item", (path or {}).get("get", {}))
    examples = _examples(operation)
    first = _resolved(contract, next(iter(examples.values()), {}))
    listed = cast("Item", first).get("value") if isinstance(first, dict) else None
    if not isinstance(listed, list):
        return []
    structures = cast("list[Item]", listed)
    return [str(item["structure_id"]) for item in structures if item.get("kind") == "amendment"]


def _at_a_structure(path: Item) -> Item:
    """Return the path of the nodes without its structure parameter, the amendment example first."""
    served: Item = {}
    for method, field in path.items():
        operation = cast("Item", field)
        parameters = cast("list[Item]", operation.get("parameters", []))
        served[method] = {
            **operation,
            "parameters": [item for item in parameters if item.get("$ref") != STRUCTURE_PARAMETER],
        }
    read = cast("Item", served["get"])
    examples = _examples(read)
    if AMENDMENT_EXAMPLE in examples:
        reordered = {AMENDMENT_EXAMPLE: examples[AMENDMENT_EXAMPLE]} | examples
        responses = cast("dict[str, Item]", read["responses"])
        media = cast("dict[str, Item]", responses["200"]["content"])["application/json"]
        read["responses"] = {
            **responses,
            "200": {
                **responses["200"],
                "content": {"application/json": {**media, "examples": reordered}},
            },
        }
    return served


def _without_security(field: object) -> object:
    """Return an operation without its security requirement; any other field unchanged."""
    if not isinstance(field, dict):
        return field
    operation = cast("dict[str, object]", field)
    return {key: value for key, value in operation.items() if key != "security"}


def main(arguments: list[str]) -> int:
    """Rewrite a bundled contract, in place, as the variant the fake back serves."""
    if len(arguments) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    bundle = Path(arguments[0])
    contract = cast("dict[str, object]", json.loads(bundle.read_text(encoding="utf-8")))
    bundle.write_text(json.dumps(derive(contract), ensure_ascii=False), encoding="utf-8")
    print(f"  -> {bundle} (fake back: paths under the server prefix, no bearer token required)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
