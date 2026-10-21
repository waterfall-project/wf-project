# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""Tests of the points of the matrix of the risks: a project's, and the portfolio's (#1053).

They try the simplifications of the fake back against the register and the cells it counts, not
the Vérif of a requirement: none cites one (WF-QUA-0010, « un test qui ne couvre aucune
exigence »).
"""

import json
from decimal import Decimal
from typing import Any, cast

import pytest

from wftools import mockdata, mockhistory, mockportfolio, mockstructure, mockwitness
from wftools.mockids import universe

type Node = dict[str, Any]

WITNESS = universe(1)


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
