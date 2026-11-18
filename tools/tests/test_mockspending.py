# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the projection of spending of the witness, the examples of `getProjectSpending`.

They try the examples against the rules the contract states of them (US-2040/L1, #3511): every
amount a sum of parts already rounded, the provisions under no nature, on the remaining to commit
no month before the calculation and the total of the remaining without its provisions.
"""

import json
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockdata, mockhistory, mockindicators, mockspending, mocktoday
from wftools.mockids import universe
from wftools.mockwitness import CORE, SUBPROJECT_CONTROL

type Node = dict[str, Any]

NAMES = (
    "spending",
    "spending_reference_budget",
    "spending_marked_remaining",
    "spending_payment_delays",
    "spending_subproject",
)


@pytest.fixture(scope="module")
def projections() -> dict[str, Node]:
    """Return the examples of the projection, read back from the text the generator writes."""
    found = mocktoday.examples()
    return {name: json.loads(mockdata.render(found[f"{name}.json"]))["value"] for name in NAMES}


def _amounts(months: list[Node]) -> dict[str, Decimal]:
    return {month["month"]: Decimal(month["amount"]) for month in months}


def _summed(each: list[dict[str, Decimal]]) -> dict[str, Decimal]:
    found: dict[str, Decimal] = {}
    for months in each:
        for month, amount in months.items():
            found[month] = found.get(month, Decimal(0)) + amount
    return found


@pytest.mark.parametrize("name", NAMES)
def test_every_amount_is_the_sum_of_what_it_holds(projections: dict[str, Node], name: str) -> None:
    projection = projections[name]
    natures: list[dict[str, Decimal]] = []
    for nature in projection["cost_types"]:
        categories = [_amounts(category["months"]) for category in nature["categories"]]
        for category, months in zip(nature["categories"], categories, strict=True):
            assert Decimal(category["total"]) == sum(months.values(), Decimal(0))
            assert all(months.values())
        months = _amounts(nature["months"])
        assert months == _summed(categories)
        assert Decimal(nature["total"]) == sum(months.values(), Decimal(0))
        natures.append(months)
    by_month = _summed(natures)
    totals = _amounts(projection["monthly_totals"])
    assert totals == {month: by_month.get(month, Decimal(0)) for month in totals}
    assert set(by_month) <= set(totals)
    assert Decimal(projection["total"]) == sum(totals.values(), Decimal(0))


@pytest.mark.parametrize("name", NAMES)
def test_the_natures_come_in_the_order_of_their_code_without_the_provisions(
    projections: dict[str, Node], name: str
) -> None:
    natures = [nature["cost_type_id"] for nature in projections[name]["cost_types"]]
    # « DEB » before « MO »; « PRV » never (WF-DEV-0100).
    assert natures == [universe(462), universe(461)]
    for nature in projections[name]["cost_types"]:
        codes = [category["cost_category_id"] for category in nature["categories"]]
        assert codes in ([universe(401), universe(403)], [universe(402), universe(405)])


def test_the_categories_come_in_the_order_of_their_code_not_of_their_identifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    witness = mockindicators.today()
    read = mockspending.spending(witness, "current_remaining")
    held = [
        category["cost_category_id"]
        for nature in cast("list[Node]", read["cost_types"])
        for category in nature["categories"]
    ]
    assert len(held) > 2
    # Codes that run against the identifiers: the last identifier has the first code.
    ranks = {category: -rank for rank, category in enumerate(sorted(held))}
    monkeypatch.setattr(mockspending, "_ranks", lambda: ranks)
    again = mockspending.spending(witness, "current_remaining")
    for nature in cast("list[Node]", again["cost_types"]):
        found = [category["cost_category_id"] for category in nature["categories"]]
        assert found == sorted(found, reverse=True)


def test_on_the_remaining_the_total_is_the_remaining_without_provisions_from_today(
    projections: dict[str, Node],
) -> None:
    witness = mockindicators.today()
    remaining = sum(
        (
            mockindicators.remaining_of(witness, line)
            for line in witness.lines
            if not mockhistory.is_provision(line)
        ),
        Decimal(0),
    )
    for name in ("spending", "spending_payment_delays"):
        projection = projections[name]
        assert Decimal(projection["total"]) == remaining
        assert projection["monthly_totals"][0]["month"] >= "2026-06"
        assert projection["context"]["is_stored"] is False
    assert projections["spending_payment_delays"]["payment_delays"] is True


def test_the_disbursements_come_later_than_the_spending(projections: dict[str, Node]) -> None:
    spent = _amounts(projections["spending"]["monthly_totals"])
    paid = _amounts(projections["spending_payment_delays"]["monthly_totals"])
    assert paid != spent
    running_spent = running_paid = Decimal(0)
    for month in sorted(set(spent) | set(paid)):
        running_spent += spent.get(month, Decimal(0))
        running_paid += paid.get(month, Decimal(0))
        assert running_paid <= running_spent


def test_the_reference_shows_the_months_before_the_calculation(
    projections: dict[str, Node],
) -> None:
    projection = projections["spending_reference_budget"]
    assert projection["monthly_totals"][0]["month"] < "2026-06"
    assert Decimal(projection["total"]) == mockindicators.budget(mockindicators.reference())


def test_a_subproject_keeps_its_own_lines(projections: dict[str, Node]) -> None:
    witness = mockindicators.today()
    projection = projections["spending_subproject"]
    assert projection["context"]["scope"] == SUBPROJECT_CONTROL
    assert Decimal(projection["total"]) == sum(
        (
            mockindicators.remaining_of(witness, line)
            for line in witness.lines
            if witness.in_scope(line, SUBPROJECT_CONTROL) and not mockhistory.is_provision(line)
        ),
        Decimal(0),
    )
    assert Decimal(projection["total"]) < Decimal(projections["spending"]["total"])


def test_a_scope_without_a_line_spends_nothing() -> None:
    nothing = mockspending.spending(
        mockindicators.today(CORE), "current_remaining", scope=universe(802)
    )
    assert (nothing["total"], nothing["monthly_totals"], nothing["cost_types"]) == ("0.00", [], [])
