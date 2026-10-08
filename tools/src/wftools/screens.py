# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Confront the screens of the front with the functional breakdown of the specification.

Usage: ``python -m wftools.screens``.

Every leaf function of the FBS (§3.4.1) is addressable from the navigation — a page, a route or
a section of a screen, the ergonomics deciding how they are gathered (EP-02, definition of done).
The table of the functions of the front, ``frontend/src/navigation/functions.json``, says where
each one is: a function of the second level by its route, which the navigation offers; a leaf
with a screen of its own (``leaves``) by its route, which the screen of its function leads to;
a leaf that the screen of its function shows itself (``sections``) by the route of its function.

The check fails, naming the leaf or the route:

- on a leaf of the FBS the table does not address, unless it is declared below, with its
  reason, as having no screen yet; and on a declaration that no longer holds;
- on a code of the table that is not a function of the FBS, or a leaf or a section that is not a
  leaf under its function;
- on a route of the table that no page of ``frontend/src/app`` answers — the page that catches
  every other address, ``[...path]``, says « not found », and answers none;
- on a leaf with a screen of its own that the page of its function does not name by
  ``leafOf("FBS-…")``, the one way the front finds a leaf it links to, and so cannot lead to.

The navigation is drawn from the table, and offers each of its functions; that every route is
indeed reached by a link is proven in a browser, by ``frontend/e2e/screens.spec.ts``.
"""

import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from wftools import REPOSITORY, projection
from wftools.projection import Function

TABLE = REPOSITORY / "frontend" / "src" / "navigation" / "functions.json"
"""The table of the functions of the front, which the navigation is drawn from."""
APP = REPOSITORY / "frontend" / "src" / "app"
"""The routes of the front, one directory each, its page in ``page.tsx``."""

WITHOUT_SCREEN: dict[str, str] = {}
"""The leaves of the FBS that no screen addresses yet, each with its reason and the issue that
follows it; none today."""

_PAGE = "page.tsx"
# A segment in brackets names a group of routes, which adds nothing to the address.
_GROUP = re.compile(r"^\(.+\)$")
# The page that answers every address no other page does: it says « not found ».
_CATCH_ALL = re.compile(r"^\[\.\.\..+\]$")


@dataclass(frozen=True, slots=True)
class Address:
    """Where the table puts a function of the FBS."""

    code: str
    route: str
    kind: str
    """``function``, ``leaf`` — a screen of its own —, or ``section`` of its function's screen."""
    function: str | None
    """The code of the function a leaf or a section belongs to; ``None`` for a function."""


def _objects(value: object) -> list[dict[str, object]]:
    """Return the objects of a JSON array, anything else as an empty list."""
    items = cast("list[object]", value) if isinstance(value, list) else []
    return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]


def addresses(table: dict[str, object]) -> Iterator[Address]:
    """Yield every function, leaf and section of the table, in its order."""
    for group in _objects(table.get("groups")):
        for fn in _objects(group.get("functions")):
            code, route = str(fn.get("code")), str(fn.get("route"))
            yield Address(code, route, "function", None)
            for section in _objects(fn.get("sections")):
                yield Address(str(section.get("code")), route, "section", code)
            for leaf in _objects(fn.get("leaves")):
                yield Address(str(leaf.get("code")), str(leaf.get("route")), "leaf", code)


def routes(table: dict[str, object]) -> list[str]:
    """Return every route of the table: of a group, a function, a leaf with a screen of its own."""
    found = [str(group["route"]) for group in _objects(table.get("groups")) if "route" in group]
    for address in addresses(table):
        if address.kind != "section" and address.route not in found:
            found.append(address.route)
    return found


def pages(app: Path) -> dict[str, str]:
    """Return the source of the page of each route of the application, by its route."""
    found: dict[str, str] = {}
    for page in sorted(app.rglob(_PAGE)):
        segments = page.parent.relative_to(app).parts
        if any(_CATCH_ALL.match(segment) for segment in segments):
            continue
        route = "/" + "/".join(segment for segment in segments if not _GROUP.match(segment))
        found[route] = page.read_text(encoding="utf-8")
    return found


def confront(
    tree: tuple[Function, ...],
    table: dict[str, object],
    app: dict[str, str],
    without_screen: dict[str, str],
) -> list[str]:
    """Return what the table and the pages of the application miss of the FBS, one line each."""
    findings: list[str] = []
    named = {fn.code: fn for fn in tree}
    leaves = {fn.code: fn for fn in projection.leaves(tree)}
    seen: set[str] = set()
    for address in addresses(table):
        findings.extend(_address(address, named, leaves, seen))
        seen.add(address.code)
    for code, fn in leaves.items():
        if code not in seen and code not in without_screen:
            findings.append(f"{code} {fn.label}: a leaf of the FBS without a route in the table")
    for code in without_screen:
        if code not in leaves:
            findings.append(f"{code}: declared without a screen, but not a leaf of the FBS")
        elif code in seen:
            findings.append(f"{code}: declared without a screen, but the table addresses it")
    findings.extend(
        f"{route}: a route of the table that no page of the application answers"
        for route in routes(table)
        if route not in app
    )
    for address in addresses(table):
        if address.kind == "leaf" and address.function is not None:
            findings.extend(_led_to(address, table, app))
    return findings


def _address(
    address: Address, named: dict[str, Function], leaves: dict[str, Function], seen: set[str]
) -> Iterator[str]:
    """Yield what is wrong with one entry of the table, against the FBS."""
    if address.code in seen:
        yield f"{address.code}: twice in the table"
    if address.code not in named:
        yield f"{address.code}: in the table, but not a function of the FBS"
        return
    if address.function is None:
        return
    function = named.get(address.function)
    if address.code not in leaves or function is None or not named[address.code].is_under(function):
        yield (
            f"{address.code}: a {address.kind} of {address.function} in the table,"
            " but not a leaf under it in the FBS"
        )


def _led_to(address: Address, table: dict[str, object], app: dict[str, str]) -> Iterator[str]:
    """Yield the route of a leaf with a screen of its own that the page of its function omits."""
    function = next(
        (other for other in addresses(table) if other.code == address.function),
        None,
    )
    source = app.get(function.route) if function is not None else None
    if source is not None and f'leafOf("{address.code}")' not in source:
        yield (
            f"{address.route}: the screen of {address.code}, which the page of {address.function}"
            " does not name by leafOf, and so does not lead to"
        )


def main() -> int:
    """Confront the table of the front with the FBS of the projection and the pages of the app."""
    tree = projection.read_functions()
    table = cast("dict[str, object]", json.loads(TABLE.read_text(encoding="utf-8")))
    app = pages(APP)
    findings = confront(tree, table, app, WITHOUT_SCREEN)
    for finding in findings:
        print(finding, file=sys.stderr)
    leaves = projection.leaves(tree)
    print(
        f"{len(leaves)} leaves of the FBS, {len(WITHOUT_SCREEN)} declared without a screen; "
        f"{len(routes(table))} routes; {len(findings)} finding(s)"
    )
    for code, reason in WITHOUT_SCREEN.items():
        print(f"  without a screen: {code}, {reason}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
