# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Check the catalogues of the front against each other and against the contract (US-0190).

Usage: ``python -m wftools.catalogs BUNDLE CATALOGUE...``, where BUNDLE is the contract
bundled as JSON and each CATALOGUE a catalogue of texts of the front, the reference first.

The catalogues are twins (WF-QUA-0070): each holds every key another holds, and each value
is a non-empty text. A key is the path of a leaf, its levels joined by dots, which next-intl
reserves for the path: a level that holds a dot could not be read.

What the contract codes has its key in every catalogue, under a root the contract owns:

- ``errors.<CODE>`` for each value of ``ErrorCode``;
- ``permissions.<code>`` for each value of ``PermissionCode``;
- ``enums.<Schema>.<property>...<value>`` for each value of any other enumeration of
  ``components.schemas``: the name of the schema, then the names of the properties down to
  the enumeration. ``items`` and ``additionalProperties`` add no level, nor does a branch of
  ``allOf``, ``anyOf`` or ``oneOf``.

A value that holds a dot is read as levels (``permissions.users.read``). A ``const`` has no
key: the contract uses it for the flag a request sets to confirm (``confirmed: true``), which
nobody reads as a label. Nor has a value that is not a string, such as the ``null`` of an
enumeration that may be empty.

Under those three roots, a key that matches nothing the contract codes fails too: it is the
leftover of a value the contract has withdrawn. Other keys — the texts of the interface —
are the front's own, and only their twin presence is checked.
"""

import argparse
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import cast

type Key = tuple[str, ...]
"""A key of a catalogue: the names of its levels, from the root to the leaf."""

NAMED: dict[str, Key] = {"ErrorCode": ("errors",), "PermissionCode": ("permissions",)}
"""The enumerations of the contract that have their own root, instead of ``enums``."""
CODED = frozenset({"enums", "errors", "permissions"})
"""The roots of the keys the contract owns."""
_TRANSPARENT = ("items", "additionalProperties")
_BRANCHES = ("allOf", "anyOf", "oneOf")


def dotted(key: Key) -> str:
    """Return a key as next-intl reads it, its levels joined by dots."""
    return ".".join(key)


def coded_keys(contract: dict[str, object]) -> set[Key]:
    """Return the key of each value the contract codes in ``components.schemas``."""
    components = cast("dict[str, object]", contract.get("components", {}))
    schemas = cast("dict[str, object]", components.get("schemas", {}))
    return {
        key
        for name, schema in schemas.items()
        for key in _enum_keys(schema, NAMED.get(name, ("enums", name)))
    }


def _enum_keys(schema: object, prefix: Key) -> Iterator[Key]:
    """Yield the key of each value of the enumerations a schema declares, at any depth."""
    if not isinstance(schema, dict):
        return
    node = cast("dict[str, object]", schema)
    for value in cast("list[object]", node.get("enum", [])):
        if isinstance(value, str):
            yield (*prefix, *value.split("."))
    for name, member in cast("dict[str, object]", node.get("properties", {})).items():
        yield from _enum_keys(member, (*prefix, name))
    for keyword in _TRANSPARENT:
        yield from _enum_keys(node.get(keyword), prefix)
    for keyword in _BRANCHES:
        for branch in cast("list[object]", node.get(keyword, [])):
            yield from _enum_keys(branch, prefix)


def read_catalogue(catalogue: object) -> tuple[set[Key], list[str]]:
    """Return the keys of a catalogue, and what is wrong with its shape."""
    keys: set[Key] = set()
    faults: list[str] = []
    if isinstance(catalogue, dict):
        _collect(cast("dict[str, object]", catalogue), (), keys, faults)
    else:
        faults.append("is not an object of keys")
    return keys, faults


def _collect(group: dict[str, object], prefix: Key, keys: set[Key], faults: list[str]) -> None:
    """Add the leaves of a group of keys to ``keys``, and its faults to ``faults``."""
    if prefix and not group:
        faults.append(f"{dotted(prefix)} is an empty group")
    for name, value in group.items():
        key = (*prefix, name)
        if not name or "." in name:
            faults.append(f"{dotted(key)}: a level empty or with a dot, which next-intl misreads")
        elif isinstance(value, dict):
            _collect(cast("dict[str, object]", value), key, keys, faults)
        elif isinstance(value, str) and value.strip():
            keys.add(key)
        else:
            faults.append(f"{dotted(key)} is not a non-empty text")


def problems(contract: dict[str, object], catalogues: dict[str, object]) -> list[str]:
    """Return every key a catalogue lacks or should not have, and every fault of its shape."""
    found: list[str] = []
    read: dict[str, set[Key]] = {}
    for name, catalogue in catalogues.items():
        keys, faults = read_catalogue(catalogue)
        found.extend(f"{name}: {fault}" for fault in faults)
        read[name] = keys
    coded = coded_keys(contract)

    def orphan(key: Key) -> bool:
        return key[0] in CODED and key not in coded

    held = {key for keys in read.values() for key in keys if not orphan(key)}
    for name, keys in read.items():
        found.extend(
            f"{name}: missing {dotted(key)}, a value the contract codes"
            for key in sorted(coded - keys)
        )
        for key in sorted(held - coded - keys):
            holders = ", ".join(other for other, theirs in read.items() if key in theirs)
            found.append(f"{name}: missing {dotted(key)}, which {holders} has")
        found.extend(
            f"{name}: {dotted(key)} matches no value the contract codes"
            for key in sorted(filter(orphan, keys))
        )
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
    loaded: list[object] = []
    for path in (bundle, *paths):
        try:
            loaded.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as error:
            print(f"{path}: not readable as JSON: {error}", file=sys.stderr)
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
