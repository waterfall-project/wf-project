# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Check the catalogues of the front against each other and against the contract (US-0190).

Usage: ``python -m wftools.catalogs BUNDLE REFERENCE TWIN...``, where BUNDLE is the contract
bundled as JSON, REFERENCE the catalogue of texts of the front the others follow, and each
TWIN another catalogue: a single catalogue would have no twin to be checked against.

The catalogues are twins (WF-QUA-0070): each holds every key another holds, each value is a
non-empty text, and a text uses the same ICU arguments as the reference's. A key is the path
of a leaf, its levels joined by dots, which next-intl reserves for the path: a level that
holds a dot could not be read, and a key written twice in a file would keep only its last
text.

What the contract codes has its key in every catalogue, under a root the contract owns:

- ``errors.<CODE>`` for each value of ``ErrorCode``;
- ``permissions.<code>`` for each value of ``PermissionCode``;
- ``enums.<Schema>.<property>...<value>`` for each value of any other enumeration of
  ``components.schemas``: the name of the schema, then the names of the properties down to
  the enumeration. ``items`` and ``additionalProperties`` add no level, nor does a branch of
  ``allOf``, ``anyOf`` or ``oneOf``;
- ``enums.<Parameter>.<value>`` for each value of an enumeration of
  ``components.parameters``, which shares the level of the schemas: a parameter that codes
  values may not bear the name of a schema.

A value that holds a dot is read as levels (``permissions.users.read``). A ``const`` has no
key: the contract uses it for the flag a request sets to confirm (``confirmed: true``), which
nobody reads as a label. Nor has a value that is not a string, such as the ``null`` of an
enumeration that may be empty.

An enumeration written in line, with no name to key its values by, fails: in a parameter of
an operation, which becomes a shared parameter; in a body of a request or of a response, or in
a header, whether under ``paths`` or under ``components.responses``, ``requestBodies`` and
``headers``, whose schema is then named in ``components.schemas``. Two exceptions: ``sort_by``,
whose values are columns, which the headers of the grid already label; and the bodies of the
probes, ``/health`` and the paths under it, which no screen displays.

Under those three roots, a key that matches nothing the contract codes fails too: it is the
leftover of a value the contract has withdrawn. Other keys — the texts of the interface —
are the front's own, and only their twin presence is checked.
"""

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

type Key = tuple[str, ...]
"""A key of a catalogue: the names of its levels, from the root to the leaf."""

NAMED: dict[str, Key] = {"ErrorCode": ("errors",), "PermissionCode": ("permissions",)}
"""The enumerations of the contract that have their own root, instead of ``enums``."""
CODED = frozenset({"enums", "errors", "permissions"})
"""The roots of the keys the contract owns."""
IN_LINE = frozenset({"sort_by"})
"""The parameters of operations whose values may be enumerated in line: columns, labelled."""
PROBES = ("/health",)
"""The paths, and the paths under them, whose bodies may enumerate in line: nobody reads them."""
_TRANSPARENT = ("items", "additionalProperties")
_BRANCHES = ("allOf", "anyOf", "oneOf")
_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
_CHOICES = frozenset({"plural", "select", "selectordinal"})


def dotted(key: Key) -> str:
    """Return a key as next-intl reads it, its levels joined by dots."""
    return ".".join(key)


def _object(value: object) -> dict[str, object]:
    """Return a JSON object as such, anything else as an empty one."""
    return cast("dict[str, object]", value) if isinstance(value, dict) else {}


def _list(value: object) -> list[object]:
    """Return a JSON array as such, anything else as an empty one."""
    return cast("list[object]", value) if isinstance(value, list) else []


def coded_keys(contract: dict[str, object]) -> set[Key]:
    """Return the key of each value the contract codes in its schemas and shared parameters."""
    components = _object(contract.get("components"))
    keys = {
        key
        for name, schema in _object(components.get("schemas")).items()
        for key in _enum_keys(schema, NAMED.get(name, ("enums", name)))
    }
    keys.update(
        key
        for name, parameter in _object(components.get("parameters")).items()
        for key in _enum_keys(_object(parameter).get("schema"), ("enums", name))
    )
    return keys


def _enum_keys(schema: object, prefix: Key) -> Iterator[Key]:
    """Yield the key of each value of the enumerations a schema declares, at any depth."""
    if not isinstance(schema, dict):
        return
    node = cast("dict[str, object]", schema)
    for value in _list(node.get("enum")):
        if isinstance(value, str):
            yield (*prefix, *value.split("."))
    for name, member in _object(node.get("properties")).items():
        yield from _enum_keys(member, (*prefix, name))
    for keyword in _TRANSPARENT:
        yield from _enum_keys(node.get(keyword), prefix)
    for keyword in _BRANCHES:
        for branch in _list(node.get(keyword)):
            yield from _enum_keys(branch, prefix)


def contract_faults(contract: dict[str, object]) -> list[str]:
    """Return the coded values of the contract that could not have a key of their own."""
    components = _object(contract.get("components"))
    schemas = _object(components.get("schemas"))
    faults = [
        f"components.parameters.{name}: also the name of a schema, whose keys it would share"
        for name, parameter in _object(components.get("parameters")).items()
        if name in schemas and any(_enum_keys(_object(parameter).get("schema"), ()))
    ]
    faults.extend(
        f"{operation}: the parameter {parameter.get('name')} enumerates its values in line; "
        "make it a shared parameter of docs/api/components/parameters.yaml, whose name keys "
        "its values"
        for _, operation, fields, shared in _operations(contract)
        for parameter in map(_object, (*shared, *_list(fields.get("parameters"))))
        if parameter.get("name") not in IN_LINE and any(_enum_keys(parameter.get("schema"), ()))
    )
    faults.extend(
        f"{where}: enumerates values in line; name the schema in components.schemas, whose "
        "name keys its values"
        for where, schema in _bodies(contract)
        if any(_enum_keys(schema, ()))
    )
    return faults


def _operations(
    contract: dict[str, object],
) -> Iterator[tuple[str, str, dict[str, object], list[object]]]:
    """Yield each operation: its path, its method and path, its fields, the path's parameters."""
    for path, item in _object(contract.get("paths")).items():
        fields = _object(item)
        shared = _list(fields.get("parameters"))
        for method in _METHODS:
            if method in fields:
                yield path, f"{method.upper()} {path}", _object(fields[method]), shared


def _bodies(contract: dict[str, object]) -> Iterator[tuple[str, object]]:
    """Yield each schema of a body or a header of the contract, with where it is written."""
    components = _object(contract.get("components"))
    for kind in ("responses", "requestBodies"):
        for name, body in _object(components.get(kind)).items():
            yield from _body_schemas(f"components.{kind}.{name}", body)
    for name, header in _object(components.get("headers")).items():
        yield f"components.headers.{name}", _object(header).get("schema")
    for path, operation, fields, _ in _operations(contract):
        if path in PROBES or path.startswith(tuple(f"{probe}/" for probe in PROBES)):
            continue
        yield from _body_schemas(f"{operation} request", fields.get("requestBody"))
        for status, response in _object(fields.get("responses")).items():
            yield from _body_schemas(f"{operation} {status}", response)


def _body_schemas(where: str, body: object) -> Iterator[tuple[str, object]]:
    """Yield the schema of each medium and each header of a body, with where it is written."""
    fields = _object(body)
    for medium, content in _object(fields.get("content")).items():
        yield f"{where} {medium}", _object(content).get("schema")
    for name, header in _object(fields.get("headers")).items():
        yield f"{where} header {name}", _object(header).get("schema")


def icu_arguments(message: str) -> frozenset[str]:
    """Return the names of the ICU arguments a message uses, at any depth."""
    names: set[str] = set()
    index = 0
    while index < len(message):
        index = _message(message, index, names) + 1
    return frozenset(names)


def _message(text: str, index: int, names: set[str]) -> int:
    """Read a message up to the brace that closes it; return the index of that brace."""
    while index < len(text):
        if text[index] == "}":
            return index
        if text[index] == "'":
            index = _quoted(text, index)
            continue
        if text[index] == "{":
            index = _argument(text, index + 1, names)
        index += 1
    return index


def _quoted(text: str, index: int) -> int:
    """Skip an apostrophe as intl-messageformat reads it; return the index after it.

    Two apostrophes are one, literal; one before a brace or an angle bracket — the tags of
    rich text — opens a literal text up to the next lone apostrophe; any other is literal.
    """
    following = text[index + 1 : index + 2]
    if following == "'":
        return index + 2
    if following not in ("{", "}", "<", ">"):
        return index + 1
    index += 1
    while index < len(text):
        if text[index : index + 2] == "''":
            index += 2
        elif text[index] == "'":
            return index + 1
        else:
            index += 1
    return index


def _upto(text: str, index: int, stops: str) -> int:
    """Return the index of the first of ``stops`` from ``index``, or the end of the text."""
    while index < len(text) and text[index] not in stops:
        index += 1
    return index


def _argument(text: str, index: int, names: set[str]) -> int:
    """Read an argument after its opening brace; return the index of its closing brace."""
    end = _upto(text, index, ",}")
    names.add(text[index:end].strip())
    if end == len(text) or text[end] == "}":
        return end
    kind_end = _upto(text, end + 1, ",}")
    if text[end + 1 : kind_end].strip() not in _CHOICES:
        return _upto(text, kind_end, "}")
    # Each option: a selector, then its message in braces, until the brace of the argument.
    index = kind_end
    while index < len(text) and text[index] != "}":
        opening = _upto(text, index + 1, "{}")
        if opening == len(text) or text[opening] == "}":
            return opening
        index = _message(text, opening + 1, names) + 1
    return index


class _Group(dict[str, object]):
    """An object of a catalogue as read, with the names it holds more than once."""

    def __init__(self, pairs: list[tuple[str, object]]) -> None:
        super().__init__(pairs)
        seen: set[str] = set()
        self.twice: list[str] = []
        for name, _ in pairs:
            if name in seen and name not in self.twice:
                self.twice.append(name)
            seen.add(name)


def parse_catalogue(text: str) -> object:
    """Return a catalogue read from JSON, keeping trace of the keys an object writes twice."""
    return json.loads(text, object_pairs_hook=_Group)


@dataclass(frozen=True, slots=True)
class Reading:
    """What a catalogue holds: every leaf, the texts among them, and the faults of its shape."""

    keys: set[Key] = field(default_factory=set[Key])
    texts: dict[Key, str] = field(default_factory=dict[Key, str])
    faults: list[str] = field(default_factory=list[str])


def read_catalogue(catalogue: object) -> Reading:
    """Return the keys and texts of a catalogue, and what is wrong with its shape."""
    reading = Reading()
    if isinstance(catalogue, dict):
        _collect(cast("dict[str, object]", catalogue), (), reading)
    else:
        reading.faults.append("is not an object of keys")
    return reading


def _collect(group: dict[str, object], prefix: Key, reading: Reading) -> None:
    """Add the leaves of a group of keys to a reading, with their faults."""
    if prefix and not group:
        reading.faults.append(f"{dotted(prefix)} is an empty group")
    if isinstance(group, _Group):
        reading.faults.extend(
            f"{dotted((*prefix, name))} is written more than once" for name in group.twice
        )
    for name, value in group.items():
        # A faulty level still names its key as next-intl would read it: the fault is
        # reported once, and not again as a key the twin lacks.
        key = (*prefix, *name.split("."))
        if not name or "." in name:
            reading.faults.append(
                f"{dotted((*prefix, name))}: a level empty or with a dot, which next-intl misreads"
            )
        if isinstance(value, dict):
            _collect(cast("dict[str, object]", value), key, reading)
            continue
        reading.keys.add(key)
        if isinstance(value, str) and value.strip():
            reading.texts[key] = value
        else:
            reading.faults.append(f"{dotted(key)} is not a non-empty text")


def _argument_faults(read: dict[str, Reading]) -> list[str]:
    """Return the texts whose ICU arguments differ from those of the reference's."""
    (reference, first), *others = read.items()
    found: list[str] = []
    for name, reading in others:
        for key in sorted(first.texts.keys() & reading.texts.keys()):
            theirs, ours = icu_arguments(first.texts[key]), icu_arguments(reading.texts[key])
            if theirs != ours:
                found.append(
                    f"{name}: {dotted(key)} uses the arguments {{{', '.join(sorted(ours))}}}, "
                    f"{reference} {{{', '.join(sorted(theirs))}}}"
                )
    return found


def problems(contract: dict[str, object], catalogues: dict[str, object]) -> list[str]:
    """Return every key a catalogue lacks or should not have, and every fault of its shape."""
    found = [f"contract: {fault}" for fault in contract_faults(contract)]
    read: dict[str, Reading] = {}
    for name, catalogue in catalogues.items():
        read[name] = read_catalogue(catalogue)
        found.extend(f"{name}: {fault}" for fault in read[name].faults)
    coded = coded_keys(contract)

    def orphan(key: Key) -> bool:
        return key[0] in CODED and key not in coded

    held = {key for reading in read.values() for key in reading.keys if not orphan(key)}
    for name, reading in read.items():
        found.extend(
            f"{name}: missing {dotted(key)}, a value the contract codes"
            for key in sorted(coded - reading.keys)
        )
        for key in sorted(held - coded - reading.keys):
            holders = ", ".join(other for other, theirs in read.items() if key in theirs.keys)
            found.append(f"{name}: missing {dotted(key)}, which {holders} has")
        found.extend(
            f"{name}: {dotted(key)} matches no value the contract codes"
            for key in sorted(filter(orphan, reading.keys))
        )
    if read:
        found.extend(_argument_faults(read))
    return found


def main(arguments: list[str]) -> int:
    """Check the catalogues, and fail on a key one lacks or none should have."""
    parser = argparse.ArgumentParser(
        prog="wftools.catalogs",
        description="Check that the catalogues of the front are twins and cover the contract.",
    )
    parser.add_argument("bundle", type=Path, help="the contract, bundled as JSON")
    parser.add_argument("catalogues", type=Path, nargs="+", help="the catalogues of texts")
    options = parser.parse_args(arguments)
    bundle = cast("Path", options.bundle)
    paths = cast("list[Path]", options.catalogues)
    _, *twins = paths
    if not twins:
        print("at least two catalogues: the reference, then its twins", file=sys.stderr)
        return 1
    loaded: list[object] = []
    for path in (bundle, *paths):
        try:
            loaded.append(parse_catalogue(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as error:
            print(f"{path}: not readable as JSON: {error}", file=sys.stderr)
            return 1
    if not isinstance(loaded[0], dict):
        print(f"{bundle}: not a contract, which is a JSON object", file=sys.stderr)
        return 1
    contract = cast("dict[str, object]", loaded[0])
    catalogues = {str(path): catalogue for path, catalogue in zip(paths, loaded[1:], strict=True)}
    found = problems(contract, catalogues)
    for problem in found:
        print(problem, file=sys.stderr)
    if found:
        print(
            "  each key goes into every catalogue, one per value the contract codes: "
            "docs/dev/README.md, « Clés de traduction »",
            file=sys.stderr,
        )
        return 1
    print(f"{len(paths)} catalogues, twins; {len(coded_keys(contract))} coded values covered")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
