# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The eight views of the portfolio, read on the witness, compared with the expected (US-2770/L2).

``make mock-data`` computes under ``fixtures/witness/portfolio/readings`` what each view must answer
on the witness loaded with its slice, read at the date of the witness, 3 June 2026, by ``as_of``: a
past date for a service whose clock runs on, so that each project contributes by what its last
revision marked by then kept (WF-PTF-0010, WF-DAT-0040). The generator imports nothing of the back;
a disagreement is arbitrated by the specification, never by one side. The examples of the contract
at three hundred projects (``volume/portfolio_*``) are not compared here and are not to be: they
stay those of the fake back (EP-11, decision of 18 November 2026).
"""

import json
import re
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode

import pytest
import yaml
from portfolio_listing_support import served
from projects_support import READING, person
from support import CONTRACT, WITNESS

if TYPE_CHECKING:
    from pathlib import Path

    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

READINGS = WITNESS.parent / "witness" / "portfolio" / "readings"
# The route of each operation of the portfolio.
ROUTES = {
    "getPortfolioProjects": "projects",
    "getPortfolioValue": "value",
    "getPortfolioWorkload": "workload",
    "getPortfolioPerformance": "performance",
    "getPortfolioCostStructure": "cost-structure",
    "getPortfolioRisks": "risks",
    "getPortfolioCostCurve": "cost-curve",
    "getPortfolioPilotHealth": "pilot-health",
}


def expected() -> list[dict[str, Any]]:
    """Read the readings expected, one document per view."""
    return [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(READINGS.glob("*.json"))
    ]


# Three lists whose order neither the contract nor the specification fixes (finding #4507): the
# roles of the workload, the points of the matrix, the signals of the pilot health are compared by
# their content, sorted on both sides by a stable key, not by their order.
UNORDERED = ("/roles", "/matrix/points", "/signals")


def _by_content(items: list[object]) -> list[object]:
    """Sort items by their canonical JSON, the same on both sides."""
    return sorted(items, key=lambda each: json.dumps(each, sort_keys=True))


def differences(
    found: object, wanted: object, hours: frozenset[str] = frozenset(), path: str = ""
) -> list[str]:
    """Name each place where an answer differs from the reading expected, with both values.

    ``hours`` holds the places typed ``Hours`` in the contract (see ``hours_places``).
    """
    if isinstance(found, dict) and isinstance(wanted, dict):
        have, want = cast("dict[str, object]", found), cast("dict[str, object]", wanted)
        return [
            each
            for key in sorted(set(have) | set(want))
            for each in differences(
                have.get(key, "<absent>"), want.get(key, "<absent>"), hours, f"{path}/{key}"
            )
        ]
    if isinstance(found, list) and isinstance(wanted, list):
        items, expected_items = cast("list[object]", found), cast("list[object]", wanted)
        if path in UNORDERED:
            items, expected_items = _by_content(items), _by_content(expected_items)
        if len(items) != len(expected_items):
            return [
                f"{path}: {len(items)} items, expected {len(expected_items)}",
                f"  found: {_named(items)}",
                f"  expected: {_named(expected_items)}",
            ]
        return [
            each
            for rank, (one, other) in enumerate(zip(items, expected_items, strict=True))
            for each in differences(one, other, hours, f"{path}/{rank}")
        ]
    if isinstance(found, str) and isinstance(wanted, str):
        if re.sub(r"/\d+(?=/|$)", "/*", path) in hours and _same_decimal(found, wanted):
            return []
        return [] if found == wanted else [f"{path}: {found!r}, expected {wanted!r}"]
    return [] if found == wanted else [f"{path}: {found!r}, expected {wanted!r}"]


def _named(items: list[object]) -> list[str]:
    """Name the items of a list: their code or their label, and their signal when they have one."""
    names: list[str] = []
    for each in items:
        if isinstance(each, dict):
            held = cast("dict[str, object]", each)
            names.append(
                "/".join(
                    str(held[key])
                    for key in ("code", "project_label", "label")
                    if key in held and held[key] is not None
                )
                + f" {held.get('code', '')}"
            )
    return names


# Only ``Hours`` is compared by value. The contract says of it: "exact decimal … rendered at ten
# decimals at most … An entry keeps the decimals it was sent with" (``common.yaml#/Hours``), so
# ``3746.9`` and ``3746.90`` are two spellings it allows. It fixes no such freedom for the other
# decimals (``Money``, ``Percent``, ratios): they are compared string for string.
def _same_decimal(found: str, wanted: str) -> bool:
    """Tell whether two strings are one exact decimal: ``1466.5`` and ``1466.50`` are."""
    try:
        return Decimal(found) == Decimal(wanted)
    except InvalidOperation:
        return False


def _load(file: Path) -> dict[str, Any]:
    return cast("dict[str, Any]", yaml.safe_load(file.read_text(encoding="utf-8")))


def _hours_in(node: object, file: Path, path: str, found: set[str], seen: tuple[str, ...]) -> None:
    """Collect the places of a schema that are typed ``Hours``, following the references."""
    if isinstance(node, list):
        for each in cast("list[object]", node):
            _hours_in(each, file, path, found, seen)
        return
    if not isinstance(node, dict):
        return
    held = cast("dict[str, Any]", node)
    ref = held.get("$ref")
    if isinstance(ref, str):
        name, _, pointer = ref.partition("#")
        target = (file.parent / name).resolve() if name else file
        if target.name == "common.yaml" and pointer == "/Hours":
            found.add(path)
            return
        key = f"{target}#{pointer}:{path}"
        if key in seen:
            return
        target_node: Any = _load(target)
        for part in pointer.strip("/").split("/"):
            target_node = target_node[part] if part else target_node
        _hours_in(target_node, target, path, found, (*seen, key))
        return
    for keyword in ("allOf", "oneOf", "anyOf"):
        _hours_in(held.get(keyword), file, path, found, seen)
    for name, each in cast("dict[str, Any]", held.get("properties", {})).items():
        _hours_in(each, file, f"{path}/{name}", found, seen)
    _hours_in(held.get("items"), file, f"{path}/*", found, seen)


def hours_places(operation: str) -> frozenset[str]:
    """Name the places of the 200 answer of an operation that the contract types ``Hours``."""
    paths = CONTRACT.parent / "paths" / "portfolio.yaml"
    routes = cast("dict[str, dict[str, Any]]", _load(paths))
    for route in routes.values():
        get: dict[str, Any] | None = route.get("get")
        if get and get.get("operationId") == operation:
            schema: Any = get["responses"]["200"]["content"]["application/json"]["schema"]
            found: set[str] = set()
            _hours_in(schema, paths, "", found, ())
            return frozenset(found)
    raise AssertionError(operation)


@pytest.mark.story("US-2770")
def test_the_readings_expected_are_the_eight_views_of_the_portfolio() -> None:
    assert sorted(document["operation"] for document in expected()) == sorted(ROUTES)


@pytest.mark.story("US-2770")
@pytest.mark.parametrize("operation", sorted(ROUTES))
def test_a_view_read_at_the_date_of_the_witness_answers_the_reading_expected(
    api: ContractClient, witness: Database, realm: TestRealm, operation: str
) -> None:
    # [US-2770] « les lectures attendues des huit vues sur le témoin ainsi chargé sont […]
    # comparées aux réponses du service » : the answer of the service, read by the manager with
    # ``as_of`` the 3 June 2026, is the reading ``make mock-data`` computed, key for key.
    [reading] = [each for each in expected() if each["operation"] == operation]
    reader = person(witness, realm, *READING)
    query = urlencode(reading["query"], safe=",")
    answer = served(api, reader, ROUTES[operation], query)
    found = differences(answer, reading["value"], hours_places(operation))
    assert not found, "\n".join(found)
