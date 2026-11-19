# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the project list of the portfolio read with column filters (US-2690/L1).

They try the example of the fake back against the rules the filters retain by, and the contract
against the convention it follows; none tries the Vérif of a requirement on a case of its own,
which the back tests of the filter will (WF-QUA-0010), so none cites one.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

import pytest
import yaml

from wftools import REPOSITORY, mockportfolio, mocktext

if TYPE_CHECKING:
    from pathlib import Path

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


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _is_reference(node: Any) -> bool:
    return isinstance(node, dict) and "$ref" in cast("dict[str, Any]", node)


def _follow(base: Path, node: Any) -> Any:
    """Resolve the references of a node, the file of each one relative to the file that cites it."""
    while _is_reference(node):
        reference = cast("str", node["$ref"])
        name, _, pointer = reference.partition("#")
        if name:
            base = (base.parent / name).resolve()
        node = _load(base)
        for part in [step for step in pointer.split("/") if step]:
            node = node[part]
    return node


def _operation(name: str) -> dict[str, Any]:
    path = CONTRACT / "paths" / "portfolio.yaml"
    for item in _load(path).values():
        if item.get("get", {}).get("operationId") == name:
            return item["get"]
    raise AssertionError(name)


def _parameters(name: str) -> dict[str, dict[str, Any]]:
    """Return the parameters of an operation, resolved, by the name they carry in the query."""
    path = CONTRACT / "paths" / "portfolio.yaml"
    found = [_follow(path, node) for node in _operation(name)["parameters"]]
    return {parameter["name"]: parameter for parameter in found}


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
            Decimal(index["value"]["value"]) <= mockportfolio.FILTERED_COST_INDEX_MAX
            and Decimal(row["delta_to_reference"]) >= mockportfolio.FILTERED_DELTA_MIN
            and mockportfolio.instant(row["last_marked_at"]) < mockportfolio.FILTERED_MARKED_BEFORE
        )

    expected = {row["project_id"] for row in whole["items"] if retained(row)}
    items = filtered["value"]["items"]
    assert {row["project_id"] for row in items} == expected
    assert 0 < len(items) == len(expected) < len(whole["items"])
    assert filtered["value"]["meta"] == {"limit": 50, "offset": 0, "total": len(expected)}
    assert filtered["value"]["scope"] == whole["scope"]
    assert f"les {mocktext.count(len(expected))} projets en cours" in filtered["summary"]


def test_a_null_column_is_retained_by_no_bound(filtered: dict[str, Any]) -> None:
    # US-2690: an offer has neither index nor variance, and no bound of those columns keeps it.
    assert {row["state"] for row in filtered["value"]["items"]} == {"in_progress"}
    assert mockportfolio.filtered_rows([_row()]) == [_row()]
    absent: list[JsonObject] = [
        {"cost_index": None},
        {"cost_index": {"value": {"value": None}}},
        {"cost_index": _not_computed()},
        {"delta_to_reference": None},
        {"last_marked_at": None},
    ]
    for column in absent:
        assert mockportfolio.filtered_rows([_row() | column]) == []


def _not_computed() -> JsonObject:
    """Return an index not computed as `Computable` defines it: no value, and a reason."""
    value: JsonObject = {"is_computable": False, "value": None, "reason": "no_actual_cost"}
    return {"value": value, "zone": None}


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
    operation = _operation("getPortfolioProjects")
    parameters = _parameters("getPortfolioProjects")
    for column in _BOUNDED:
        assert {f"{column}_min", f"{column}_max"} <= parameters.keys(), column
    assert {"code", "last_marked_at_from", "last_marked_at_to"} <= parameters.keys()
    assert "volume/portfolio_projects_filtered.json" in str(operation["responses"]["200"])
    refused = operation["responses"]["422"]["description"]
    assert "/query/<column>_max" in refused
    assert "/query/last_marked_at_to" in refused


def test_the_sort_says_where_a_project_without_a_value_comes() -> None:
    # US-2690/L2: the service sorts a null column after the others in ascending order.
    sort = next(
        parameter
        for parameter in _operation("getPortfolioProjects")["parameters"]
        if parameter.get("name") == "sort_by"
    )
    description = " ".join(sort["description"].split())
    assert "after the others in ascending order, before them in descending" in description


def test_the_column_filters_are_optional_and_typed_as_their_column() -> None:
    types = {
        "reference_budget": "Money",
        "current_estimate": "Money",
        "win_probability": "Percent",
        "project_manager_projection": "Money",
        "delta_to_reference": "Money",
        "cost_index": "Decimal",
        "schedule_index": "Decimal",
    }
    wanted = {
        f"{column}_{bound}": kind for column, kind in types.items() for bound in ("min", "max")
    }
    wanted |= {"last_marked_at_from": "Timestamp", "last_marked_at_to": "Timestamp"}
    path = CONTRACT / "paths" / "portfolio.yaml"
    found = [_follow(path, node) for node in _operation("getPortfolioProjects")["parameters"]]
    filters = {parameter["name"]: parameter for parameter in found if parameter["name"] in wanted}
    assert len(filters) == len(wanted)
    assert len(wanted) + 1 == 17  # the code, the fourteen bounds and the two ends of the period
    assert not any(parameter.get("required", False) for parameter in found)
    assert {
        name: parameter["schema"]["$ref"].partition("#/")[2] for name, parameter in filters.items()
    } == wanted


def test_the_422_of_the_list_gives_the_rules_and_the_examples_of_the_portfolio_period() -> None:
    refusal = _operation("getPortfolioProjects")["responses"]["422"]
    shared = _load(CONTRACT / "components" / "responses.yaml")["PortfolioPeriodRefused"]
    own = refusal["content"]["application/problem+json"]["examples"]
    common = shared["content"]["application/problem+json"]["examples"]
    # The same two examples, by the same files; the others are the refusals of the columns.
    for name, example in common.items():
        assert own[name]["$ref"] == example["$ref"], name
    rules = (
        "/query/from",
        "/query/to",
        "params.maximum",
        "params.minimum",
        "DATE_INVALID",
        "the refusal designates the bound sent, `params` naming the completed bound",
    )
    for rule in rules:
        assert " ".join(rule.split()) in " ".join(shared["description"].split())
        assert " ".join(rule.split()) in " ".join(refusal["description"].split()), rule
    assert {"bounds_inverted", "marking_period_inverted"} <= own.keys()


def test_the_refusals_of_the_columns_are_written_by_the_generator() -> None:
    refused: dict[str, Any] = mockportfolio.refusals()
    low, high = mockportfolio.REFUSED_BOUNDS
    assert low < high
    bounds, marking = (
        refused["portfolio_projects_bounds_inverted.json"]["value"],
        refused["portfolio_projects_marking_period_inverted.json"]["value"],
    )
    assert bounds["fields"][0]["pointer"] == "/query/reference_budget_max"
    assert bounds["fields"][0]["params"] == {"minimum": f"{high:.2f}"}
    start, end = mockportfolio.REFUSED_MARKING
    assert end < start
    assert marking["fields"][0]["pointer"] == "/query/last_marked_at_to"
    assert mockportfolio.instant(marking["fields"][0]["params"]["minimum"]) == start


def test_the_organisation_node_changes_no_amount_of_the_list() -> None:
    node = _parameters("getPortfolioProjects")["org_node_id"]["description"]
    assert "changes no amount of the project list" in node
    assert "`getPortfolioProjects`" in node
