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
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlencode

import pytest
from portfolio_listing_support import served
from projects_support import READING, person
from support import WITNESS

if TYPE_CHECKING:
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


def differences(found: object, wanted: object, path: str = "") -> list[str]:
    """Name each place where an answer differs from the reading expected, with both values."""
    if isinstance(found, dict) and isinstance(wanted, dict):
        have, want = cast("dict[str, object]", found), cast("dict[str, object]", wanted)
        return [
            each
            for key in sorted(set(have) | set(want))
            for each in differences(
                have.get(key, "<absent>"), want.get(key, "<absent>"), f"{path}/{key}"
            )
        ]
    if isinstance(found, list) and isinstance(wanted, list):
        items, expected_items = cast("list[object]", found), cast("list[object]", wanted)
        if len(items) != len(expected_items):
            return [
                f"{path}: {len(items)} items, expected {len(expected_items)}",
                f"  found: {_named(items)}",
                f"  expected: {_named(expected_items)}",
            ]
        return [
            each
            for rank, (one, other) in enumerate(zip(items, expected_items, strict=True))
            for each in differences(one, other, f"{path}/{rank}")
        ]
    if isinstance(found, str) and isinstance(wanted, str) and _same_decimal(found, wanted):
        return []
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


def _same_decimal(found: str, wanted: str) -> bool:
    """Tell whether two strings are one exact decimal: ``1466.5`` and ``1466.50`` are.

    The contract carries an amount, an hour, a ratio as an exact decimal in a string
    (``Hours``, ``Money``, ``Percent``): the digits after the last significant one are not a
    value, and the generator writes none where the service rounds to the hundredth.
    """
    try:
        return Decimal(found) == Decimal(wanted)
    except InvalidOperation:
        return False


@pytest.mark.story("US-2770")
def test_the_readings_expected_are_the_eight_views_of_the_portfolio() -> None:
    assert sorted(document["operation"] for document in expected()) == sorted(ROUTES)


# The views whose answer differs from the reading expected where neither the specification, nor the
# contract, nor the file of the EPIC decides between the service and the generator: each is a
# question to the author, and the test must fail until it is answered (``strict``), the reading or
# the service then corrected and the entry removed.
OPEN_QUESTIONS = {
    "getPortfolioWorkload": (
        "the roles come by label then identifier from the service, by identifier from the "
        "generator (the example of the contract at three hundred projects is by identifier); the "
        "specification (WF-PTF-0060-A) and the contract give no order"
    ),
    "getPortfolioRisks": (
        "the points of the matrix come by project label then identifier from the service, by "
        "project identifier from the generator; the specification (WF-PTF-0090) and the contract "
        "give no order"
    ),
    "getPortfolioPilotHealth": (
        "the signals come by project identifier from the service, by project label from the "
        "generator; and the service raises risks_not_reviewed for PRJ-001 — its interval starts "
        "at its passage to In progress, 15 January 2026 (DECISIONS.md, 20 November 2026) — where "
        "the generator, following WF-PTF-0110-A to the letter (« entre l'avant-dernière et la "
        "dernière révision marquée »), starts it at the marking of the offer, 15 December 2025"
    ),
}


def cases() -> list[object]:
    """Give each operation to read, those with an open question marked as failing for its reason."""
    return [
        pytest.param(
            operation,
            marks=pytest.mark.xfail(strict=True, reason=OPEN_QUESTIONS[operation]),
        )
        if operation in OPEN_QUESTIONS
        else operation
        for operation in sorted(ROUTES)
    ]


@pytest.mark.story("US-2770")
@pytest.mark.parametrize("operation", cases())
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
    found = differences(answer, reading["value"])
    assert not found, "\n".join(found)
