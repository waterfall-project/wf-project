# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Write which fixtures of ``fixtures/api/`` the contract cites, by operation and status.

Usage: ``python -m wftools.exampleroutes BUNDLE OUTPUT``, where BUNDLE is the contract bundled
as JSON; OUTPUT, a declaration file of TypeScript, is written by ``make generate-client`` next
to the generated client, and checked up to date with it (``make client-up-to-date``).

The fake client of the tests of the front answers a call with a fixture, by the name of its
file (``src/test/fixtures.ts``). Typed by this table, it answers an operation only with an
example the contract gives that operation, for that status (#133): a list of projects cannot
receive a project alone, which the service will never send.

The bundle names each example it takes from a file after the file, and suffixes a name taken
twice: an example is told to be a fixture by its value, the ``value`` of the file, and among
fixtures of the same value — two empty lists — by the name the bundle gave it.
"""

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from wftools import REPOSITORY

FIXTURES = REPOSITORY / "fixtures" / "api"

METHODS = ("get", "put", "post", "delete", "patch")
"""The methods of the generated client, the only ones the fake client answers."""

JSON = "application/json"

HEADER = """\
// Written by `make generate-client` from the examples of the contract: never edited by hand.

/**
 * The fixtures of `fixtures/api/` the contract cites as examples, by operation and status: what
 * the fake client of the tests may answer to each (`src/test/fixtures.ts`).
 */
export interface Examples {
"""

type Json = dict[str, object]


def fixtures(directory: Path = FIXTURES) -> dict[str, list[str]]:
    """Return the names of the fixtures, by their value written as canonical JSON."""
    names: dict[str, list[str]] = {}
    for path in sorted(directory.rglob("*.json")):
        example = cast("object", json.loads(path.read_text(encoding="utf-8")))
        if isinstance(example, dict) and "value" in example:
            name = path.relative_to(directory).with_suffix("").as_posix()
            names.setdefault(_canonical(cast("Json", example)["value"]), []).append(name)
    return names


def routes(contract: Json, known: dict[str, list[str]]) -> dict[str, dict[int, list[str]]]:
    """Return the fixtures each operation answers, by status, as the contract cites them."""
    table: dict[str, dict[int, list[str]]] = {}
    for route, status, example in _examples(contract):
        value = _canonical(_resolve(contract, example).get("value"))
        for name in _named(example, known.get(value, [])):
            cited = table.setdefault(route, {}).setdefault(status, [])
            if name not in cited:
                cited.append(name)
    return table


def render(table: dict[str, dict[int, list[str]]]) -> str:
    """Write the table as the declaration the fake client reads."""
    lines = [HEADER]
    for route in sorted(table):
        lines.append(f'  "{route}": {{\n')
        for status in sorted(table[route]):
            names = " | ".join(f'"{name}"' for name in sorted(table[route][status]))
            lines.append(f"    {status}: {names};\n")
        lines.append("  };\n")
    lines.append("}\n")
    return "".join(lines)


def _examples(contract: Json) -> Iterator[tuple[str, int, Json]]:
    """Yield each example of a JSON answer: its operation, as the client names it, its status."""
    for path, item in cast("dict[str, Json]", contract["paths"]).items():
        for method in METHODS:
            operation = cast("Json | None", item.get(method))
            if operation is None:
                continue
            responses = cast("dict[str, Json]", operation.get("responses", {}))
            for status, response in responses.items():
                content = cast("dict[str, Json]", _resolve(contract, response).get("content", {}))
                examples = cast("dict[str, Json]", content.get(JSON, {}).get("examples", {}))
                for example in examples.values():
                    yield f"{method.upper()} {path}", int(status), example


def _named(example: Json, candidates: list[str]) -> list[str]:
    """Return the fixtures an example is: of its value, and of its name when one bears it."""
    reference = example.get("$ref")
    component = reference.rsplit("/", 1)[-1] if isinstance(reference, str) else None
    named = [name for name in candidates if name.rsplit("/", 1)[-1] == component]
    return named or candidates


def _resolve(contract: Json, node: Json) -> Json:
    """Follow the references of a node within the bundle, down to what they designate."""
    while isinstance(reference := node.get("$ref"), str):
        target = contract
        for key in reference.removeprefix("#/").split("/"):
            target = cast("Json", target[key])
        node = target
    return node


def _canonical(value: object) -> str:
    """Write a value so that two equal values are written alike."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def main(arguments: list[str], directory: Path = FIXTURES) -> int:
    """Write the fixtures the contract cites, by operation and status."""
    parser = argparse.ArgumentParser(
        prog="wftools.exampleroutes",
        description="Write the fixtures the contract cites, by operation and status.",
    )
    parser.add_argument("bundle", type=Path, help="the contract, bundled as JSON")
    parser.add_argument("output", type=Path, help="the declaration file to write")
    options = parser.parse_args(arguments)
    bundle = cast("Path", options.bundle)
    output = cast("Path", options.output)
    contract = cast("Json", json.loads(bundle.read_text(encoding="utf-8")))
    output.write_text(render(routes(contract, fixtures(directory))), encoding="utf-8", newline="\n")
    print(f"  -> {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
