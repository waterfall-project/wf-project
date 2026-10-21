# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the points of the matrix of the risks: a project's, and the portfolio's (#1053).

They try the simplifications of the fake back against the register and the cells it counts, not
the Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune
exigence »).
"""

import dataclasses
import json
from collections.abc import Iterator
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockdata, mockhistory, mockportfolio, mockstructure, mockwitness
from wftools.mockids import universe

type Node = dict[str, Any]

WITNESS = universe(1)

PROJECT_FIELDS = {"project_id", "project_label", "can_open"}
"""The fields of a point that name its project, in the matrix of the portfolio only."""


@pytest.fixture(scope="module")
def history() -> dict[str, Any]:
    """Read the named examples of the history back from the text the generator writes."""
    return {
        name.removesuffix(".json"): json.loads(mockdata.render(example))["value"]
        for name, example in mockhistory.examples().items()
    }


@pytest.fixture(scope="module")
def rows() -> list[Node]:
    return cast("list[Node]", mockportfolio.portfolio()["items"])


def _bounds(matrix: Node) -> list[str]:
    """Return the bounds of severity of a matrix, each the lower of the level above it."""
    return [level["lower"] for level in matrix["severity_levels"][1:]]


def test_each_risk_the_matrix_counts_is_a_point_at_the_values_of_the_risk(
    history: dict[str, Any],
) -> None:
    # One point per risk the cells count, in the order of the register, at the values the
    # register reads — whatever its state, the screen filtering the points as the grid —, its
    # severity as a share of the budget the cells class, and the zone of its cell.
    budget = Decimal("65430697.64")
    items = history["risks"]["items"]
    matrix = history["risk_matrix"]
    points = matrix["points"]
    assert len(points) == sum(cell["count"] for cell in matrix["cells"])
    assert [point["risk_id"] for point in points] == [item["risk_id"] for item in items]
    for point, item in zip(points, items, strict=True):
        assert point == {
            "risk_id": item["risk_id"],
            "label": item["label"],
            "probability": item["probability"],
            "severity_amount": item["severity"],
            "severity_ratio": point["severity_ratio"],
            "provision_amount": item["provision_amount"],
            "state": item["state"],
            "zone": item["matrix_cell"]["zone"],
        }
        ratio = Decimal(point["severity_ratio"])
        assert ratio == mockstructure.share(Decimal(item["severity"]) / budget)
        assert mockhistory.level(ratio, _bounds(matrix)) == item["matrix_cell"]["severity_level"]
    # 1.91 %, under a hundredth of a percent given to its first digit, 18.34 % (README, « Une
    # part… »).
    assert [point["severity_ratio"] for point in points] == ["0.0191", "0.000003", "0.1834"]


def test_each_risk_the_matrix_of_the_portfolio_counts_is_a_point_with_its_project(
    rows: list[Node],
) -> None:
    # One point per identified risk the cells count, at its values, in the zone of its cell, with
    # its project and whether the reader may open it, as the heaviest name it.
    risks = mockportfolio.identified_risks(rows)
    matrix = cast("Node", mockportfolio.portfolio_risks(rows)["matrix"])
    points = cast("list[Node]", matrix["points"])
    assert len(points) == len(risks) == sum(cell["count"] for cell in matrix["cells"])
    zones = {
        (cell["probability_level"], cell["severity_level"]): cell["zone"]
        for cell in matrix["cells"]
    }
    for point, risk in zip(points, risks, strict=True):
        assert point == {
            "risk_id": risk.risk_id,
            "label": risk.label,
            "probability": str(risk.probability),
            "severity_amount": mockstructure.money(risk.severity),
            "severity_ratio": str(risk.severity_ratio),
            "provision_amount": mockstructure.money(risk.provision),
            "state": "identified",
            "zone": zones[risk.cell],
            "project_id": risk.row["project_id"],
            "project_label": risk.row["label"],
            "can_open": risk.row["can_open"],
        }
        # A share of the budget of its project, in the level of severity its cell gives.
        assert mockhistory.level(risk.severity_ratio, _bounds(matrix)) == risk.cell[1]
    # The witness brings the points of its own matrix, its identified risks only.
    own = {point["risk_id"]: point for point in mockwitness.fixture("risk_matrix")["points"]}
    witness = [point for point in points if point["project_id"] == WITNESS]
    assert [point["risk_id"] for point in witness] == [universe(751)]
    for point in witness:
        assert {key: point[key] for key in own[point["risk_id"]]} == own[point["risk_id"]]
    assert {point["can_open"] for point in points} == {True, False}


def test_the_volume_of_the_portfolio_holds_the_points_it_counts() -> None:
    matrix = mockwitness.fixture("volume/portfolio_risks")["matrix"]
    assert len(matrix["points"]) == sum(cell["count"] for cell in matrix["cells"]) == 429


def test_a_share_just_under_a_bound_is_rounded_onto_it_its_cell_that_of_the_exact_share() -> None:
    # 9.9999 % of the budget, a ten-thousandth of a percent under the bound of 10 %, is given
    # 0.1000, on the bound; its cell is that of the exact share, the third level of severity,
    # not the fourth the rounded share would give: at a probability of 40 %, a watch, not an
    # alert.
    budget = Decimal("1000000.00")
    review = mockwitness.Review(mockwitness.REWORK.last.at, Decimal("0.4"), Decimal("99999.00"))
    risk = dataclasses.replace(mockwitness.REWORK, reviews=(review,))
    bounds = mockwitness.fixture("reference_settings")["risk_matrix"]["severity_bounds"]
    point = mockhistory.matrix_point(risk, budget)
    assert point["severity_ratio"] == "0.1000"
    assert mockhistory.level(Decimal("0.1000"), bounds) == 4
    cell = mockhistory.matrix_cell(risk, budget)
    assert (cell["probability_level"], cell["severity_level"]) == (3, 3)
    assert point["zone"] == cell["zone"] == "watch"


def _matrices(value: object, path: str) -> Iterator[tuple[str, Node]]:
    """Yield each matrix of the risks under a value, with where it lies in the example."""
    if isinstance(value, dict):
        node = cast("Node", value)
        if {"probability_levels", "severity_levels", "cells", "points"} <= node.keys():
            yield path, node
        for key, item in node.items():
            yield from _matrices(item, f"{path}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(cast("list[object]", value)):
            yield from _matrices(item, f"{path}/{index}")


def test_the_points_name_their_project_by_three_fields_in_the_portfolio_and_none_in_a_project() -> (
    None
):
    # Over every example: a project's matrix is the whole answer of its reading, whose points name
    # no project; the portfolio's is the matrix of its risks, whose points name theirs by the
    # three fields together.
    found: set[str] = set()
    for file in sorted(mockwitness.FIXTURES.rglob("*.json")):
        value = json.loads(file.read_text(encoding="utf-8")).get("value")
        for path, matrix in _matrices(value, file.stem):
            portfolio = path == f"{file.stem}/matrix"
            assert portfolio or path == file.stem, path
            found.add("portfolio" if portfolio else "project")
            expected: set[str] = PROJECT_FIELDS if portfolio else set()
            for point in matrix["points"]:
                assert PROJECT_FIELDS & point.keys() == expected, path
    assert found == {"portfolio", "project"}
