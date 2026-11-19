# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the project list of the portfolio read with column filters (US-2690/L1)."""

import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest

from wftools import REPOSITORY, mockportfolio

if TYPE_CHECKING:
    from wftools.mockstructure import JsonObject

CONTRACT = REPOSITORY / "docs" / "api"

_BOUNDED = (
    "reference_budget",
    "current_estimate",
    "win_probability",
    "project_manager_projection",
    "delta_to_reference",
    "cost_index",
    "schedule_index",
)


@pytest.fixture(scope="module")
def whole() -> dict[str, Any]:
    """Return the list of the three hundred projects, as the generator writes it."""
    return mockportfolio.portfolio()


@pytest.fixture(scope="module")
def filtered(whole: dict[str, Any]) -> dict[str, Any]:
    """Return the example of the list read with column filters."""
    return mockportfolio.portfolio_filtered(whole)


def _operation(name: str) -> str:
    text = (CONTRACT / "paths" / "portfolio.yaml").read_text(encoding="utf-8")
    parts = re.split(r"^    operationId: (\w+)$", text, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))[name]


def test_the_filtered_list_holds_every_project_the_three_filters_retain(
    whole: dict[str, Any], filtered: dict[str, Any]
) -> None:
    # Each filter judged on its own, on the raw values of the row: the example holds exactly the
    # projects that all three retain, and nothing else.
    def retained(row: dict[str, Any]) -> bool:
        index = row["cost_index"]
        if index is None or not index["value"]["is_computable"]:
            return False
        if row["delta_to_reference"] is None or row["last_marked_at"] is None:
            return False
        return (
            Decimal(index["value"]["value"]) <= Decimal("0.9")
            and Decimal(row["delta_to_reference"]) >= 0
            and row["last_marked_at"] < "2026-04-01T00:00:00Z"
        )

    expected = {row["project_id"] for row in whole["items"] if retained(row)}
    items = filtered["value"]["items"]
    assert {row["project_id"] for row in items} == expected
    assert len(items) == len(expected) == 49
    assert filtered["value"]["meta"] == {"limit": 50, "offset": 0, "total": 49}
    assert filtered["value"]["scope"] == whole["scope"]
    assert "les 49 projets en cours" in filtered["summary"]


def test_a_null_column_is_retained_by_no_bound(filtered: dict[str, Any]) -> None:
    # US-2690: an offer has neither index nor variance, and no bound of those columns keeps it.
    assert {row["state"] for row in filtered["value"]["items"]} == {"in_progress"}
    assert mockportfolio.filtered_rows([_row()]) == [_row()]
    absent: list[JsonObject] = [
        {"cost_index": None},
        {"cost_index": {"value": {"value": None}}},
        {"delta_to_reference": None},
        {"last_marked_at": None},
    ]
    for column in absent:
        assert mockportfolio.filtered_rows([_row() | column]) == []


def _row() -> JsonObject:
    return {
        "project_id": "p",
        "label": "l",
        "cost_index": {"value": {"value": "0.5"}},
        "delta_to_reference": "10.00",
        "last_marked_at": "2026-03-01T17:00:00Z",
    }


def test_the_filtered_list_is_sorted_by_the_cost_index_then_the_label(
    filtered: dict[str, Any],
) -> None:
    keys = [
        (Decimal(row["cost_index"]["value"]["value"]), row["label"], row["project_id"])
        for row in filtered["value"]["items"]
    ]
    assert keys == sorted(keys)
    assert keys[0][0] < keys[-1][0]


def test_the_list_declares_a_filter_for_each_of_its_columns() -> None:
    text = _operation("getPortfolioProjects")
    parameters = (CONTRACT / "components" / "parameters.yaml").read_text(encoding="utf-8")
    cited = re.findall(r"parameters\.yaml#/(Portfolio\w+)", text)
    names = {
        found.group(1)
        for name in cited
        if (found := re.search(rf"^{name}:\n  name: (\w+)$", parameters, flags=re.MULTILINE))
    }
    for column in _BOUNDED:
        assert {f"{column}_min", f"{column}_max"} <= names, column
    assert {"code", "last_marked_at_from", "last_marked_at_to"} <= names
    assert "volume/portfolio_projects_filtered.json" in text
    refused = text.split("\n      '422':", 1)[1].split("\n      '500'", 1)[0]
    assert "/query/<column>_max" in refused
    assert "/query/last_marked_at_to" in refused


def test_the_organisation_node_changes_no_amount_of_the_list() -> None:
    parameters = (CONTRACT / "components" / "parameters.yaml").read_text(encoding="utf-8")
    node = parameters.split("\nPortfolioOrgNode:\n", 1)[1].split("\n\n", 1)[0]
    assert "it changes no amount of the project list, of the value nor of" in node
