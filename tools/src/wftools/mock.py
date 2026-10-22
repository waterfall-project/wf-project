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
  Prism prefers a path with no parameter to a templated one;
- the comparison of the volume is read at the address of a project of the volume: Prism serves
  the first example of ``compareRevisions`` and cannot route on its query (``from_revision_id``,
  ``to_revision_id``), so the path of the comparison is repeated for the project of the volume
  with its identifier written in, leading with its example ``volume`` (US-0500/L4, #1201).

No response is written here: responses are the examples of the contract.

The same variant serves Prism as a proxy in front of the real service (``make e2e-service``),
which holds every answer to the contract: there the service authenticates, and its refusal
passes as it answers it, where Prism, asking for a token, would answer one of its own.
"""

import json
import sys
from pathlib import Path
from typing import Any, cast

from wftools.mockids import PROJECTS, identifier


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
    derived["paths"] = _with_literal_paths(contract, cast("Json", derived_paths), prefix)
    return derived


STRUCTURES_PATH = "/projects/{project_id}/revisions/{revision_id}/structures"
NODES_PATH = STRUCTURES_PATH + "/{structure_id}/nodes"
AMENDMENT_EXAMPLE = "amendment"
HTTP_METHODS = frozenset({"get", "put", "post", "delete", "options", "head", "patch", "trace"})
STRUCTURE_PARAMETER = "#/components/parameters/StructureId"
COMPARISON_PATH = "/projects/{project_id}/revisions/comparison"
PROJECT_PARAMETER = "#/components/parameters/ProjectId"
VOLUME_EXAMPLE = "volume"
VOLUME_PROJECT = identifier(PROJECTS, 300)

type Json = dict[str, Any]


def _with_literal_paths(contract: Json, paths: Json, prefix: str) -> Json:
    """Return the paths, plus those the fake back serves at a literal address (#1219, #1201)."""
    return _with_volume_comparison(_with_amendment_nodes(contract, paths, prefix), prefix)


def _with_volume_comparison(paths: Json, prefix: str) -> Json:
    """Return the paths, plus the comparison at the address of the project of the volume.

    A comparison path whose operation lists no example ``volume`` is an error: the fake back
    would be asked for the volume and silently answer the witness.
    """
    comparison = paths.get(prefix + COMPARISON_PATH)
    if comparison is None:
        return paths
    served = _at_a_literal(comparison, PROJECT_PARAMETER, VOLUME_EXAMPLE)
    if VOLUME_EXAMPLE not in _examples(served.get("get", {})):
        message = f"{COMPARISON_PATH} has no example {VOLUME_EXAMPLE!r}: no volume to serve"
        raise ValueError(message)
    address = COMPARISON_PATH.replace("{project_id}", VOLUME_PROJECT)
    return {**paths, prefix + address: served}


def _with_amendment_nodes(contract: Json, paths: Json, prefix: str) -> Json:
    """Return the paths, plus the nodes of each differential structure at its own address."""
    nodes = paths.get(prefix + NODES_PATH)
    if nodes is None:
        return paths
    served = dict(paths)
    for structure in _amendment_structures(contract, paths.get(prefix + STRUCTURES_PATH)):
        address = NODES_PATH.replace("{structure_id}", structure)
        served[prefix + address] = _at_a_literal(nodes, STRUCTURE_PARAMETER, AMENDMENT_EXAMPLE)
    return served


def _resolved(contract: Json, value: Json) -> Json:
    """Return what a reference to the examples of the components points at; others unchanged."""
    if "$ref" not in value:
        return value
    name = str(value["$ref"]).rsplit("/", 1)[-1]
    components: Json = contract.get("components", {})
    examples: Json = components.get("examples", {})
    if name not in examples:
        message = f"the reference {value['$ref']} points at no example of the components"
        raise ValueError(message)
    return cast("Json", examples[name])


def _examples(operation: Json) -> Json:
    """Return the examples of the JSON answer 200 of an operation."""
    content = operation.get("responses", {}).get("200", {}).get("content", {})
    return cast("Json", content.get("application/json", {}).get("examples", {}))


def _amendment_structures(contract: Json, path: Json | None) -> list[str]:
    """Return the identifiers of the differential structures the first listing example names.

    A listing that is missing, or that names none, is an error: the fake back would serve the
    nodes of an amendment its guide promises, and silently serve the wrong ones.
    """
    if path is None:
        message = f"{NODES_PATH} is served but {STRUCTURES_PATH} is not: no amendment to route"
        raise ValueError(message)
    examples = list(_examples(path.get("get", {})).values())
    first = _resolved(contract, cast("Json", examples[0])) if examples else {}
    listed = first.get("value")
    structures = cast("list[Json]", listed) if isinstance(listed, list) else []
    found = [str(item["structure_id"]) for item in structures if item.get("kind") == "amendment"]
    if not found:
        message = (
            f"the first example of {STRUCTURES_PATH} lists no structure of kind "
            f"{AMENDMENT_EXAMPLE!r}: the fake back has no amendment to serve (#1219)"
        )
        raise ValueError(message)
    return found


def _at_a_literal(path: Json, parameter: str, example: str) -> Json:
    """Return a path without one of its parameters, the example named first.

    Only the HTTP methods are rewritten; the parameters declared on the path itself lose it too.
    A path with no ``get`` has no example to lead with.
    """
    served: Json = {}
    for key, value in path.items():
        if key in HTTP_METHODS:
            parameters = value.get("parameters", [])
            served[key] = {
                **value,
                "parameters": [item for item in parameters if item.get("$ref") != parameter],
            }
        elif key == "parameters":
            served[key] = [item for item in value if item.get("$ref") != parameter]
        else:
            served[key] = value
    read = served.get("get")
    if read is None:
        return served
    examples = _examples(read)
    if example in examples:
        reordered = {example: examples[example]} | examples
        response = read["responses"]["200"]
        media = response["content"]["application/json"]
        read["responses"] = {
            **read["responses"],
            "200": {
                **response,
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
