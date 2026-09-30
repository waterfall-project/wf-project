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
twice (``estimate_indicators-2``): an example is the fixture whose name it bears, suffix
removed, and whose ``value`` it has — two fixtures may have the same value, two empty lists.
An example named after a fixture without its value is a defect of the tool, or of the bundle:
the tool fails on it rather than let a fixture answer what it does not say. A number is read
alike on both sides: the bundle writes ``1`` where a fixture says ``1.0``. An inline example is
no fixture, and a status that is not a number — ``default``, ``4XX`` — is one the fake client
cannot answer: both are left out.
"""

import argparse
import json
import re
import sys
from collections.abc import Iterator
from decimal import Decimal
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

SUFFIX = re.compile(r"-\d+$")
"""What the bundle adds to the name of an example taken twice."""

type Json = dict[str, object]


class ExampleError(ValueError):
    """An example of the contract is named after a fixture whose value it does not have."""


def fixtures(directory: Path = FIXTURES) -> dict[str, list[str]]:
    """Return the names of the fixtures, by their value written as canonical JSON."""
    names: dict[str, list[str]] = {}
    for path in sorted(directory.rglob("*.json")):
        example = _load(path.read_text(encoding="utf-8"))
        if isinstance(example, dict) and "value" in example:
            name = path.relative_to(directory).with_suffix("").as_posix()
            names.setdefault(_canonical(cast("Json", example)["value"]), []).append(name)
    return names


def routes(contract: Json, known: dict[str, list[str]]) -> dict[str, dict[int, list[str]]]:
    """Return the fixtures each operation answers, by status, as the contract cites them."""
    table: dict[str, dict[int, list[str]]] = {}
    names = {name.rsplit("/", 1)[-1] for listed in known.values() for name in listed}
    for route, status, example in _examples(contract):
        value = _canonical(_resolve(contract, example).get("value"))
        for name in _named(example, known.get(value, []), names):
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
                if not status.isdigit():
                    continue
                content = cast("dict[str, Json]", _resolve(contract, response).get("content", {}))
                examples = cast("dict[str, Json]", content.get(JSON, {}).get("examples", {}))
                for example in examples.values():
                    yield f"{method.upper()} {path}", int(status), example


def _named(example: Json, candidates: list[str], names: set[str]) -> list[str]:
    """Return the fixtures an example is: of its value, and bearing its name, suffix removed."""
    reference = example.get("$ref")
    if not isinstance(reference, str):
        return []
    component = SUFFIX.sub("", reference.rsplit("/", 1)[-1])
    named = [name for name in candidates if name.rsplit("/", 1)[-1] == component]
    if not named and component in names:
        message = f"{reference} is named after the fixture {component}, without its value"
        raise ExampleError(message)
    return named


def _resolve(contract: Json, node: Json) -> Json:
    """Follow the references of a node within the bundle, down to what they designate."""
    while isinstance(reference := node.get("$ref"), str):
        target = contract
        for key in reference.removeprefix("#/").split("/"):
            target = cast("Json", target[key])
        node = target
    return node


def _load(text: str) -> object:
    """Read JSON, a number with a fraction of nothing — ``1.0`` — as the whole number it is."""
    return cast("object", json.loads(text, parse_float=_number))


def _number(text: str) -> int | float:
    """Read a number written with a fraction or an exponent: whole, as an integer."""
    exact = Decimal(text)
    return int(exact) if exact == exact.to_integral_value() else float(text)


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
    contract = cast("Json", _load(bundle.read_text(encoding="utf-8")))
    try:
        table = routes(contract, fixtures(directory))
    except ExampleError as error:
        print(f"  {error}", file=sys.stderr)
        return 1
    output.write_text(render(table), encoding="utf-8", newline="\n")
    print(f"  -> {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
