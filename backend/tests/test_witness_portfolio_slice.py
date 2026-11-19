# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The slice of the portfolio of the witness, in the form of the contract (US-2770/L1).

``make mock-data`` writes under ``fixtures/witness/portfolio/`` the description of the ten projects
the witness loads beside PRJ-001 and PRJ-002 (``wftools.mockslice``), and the readings of the eight
views of the portfolio the service must answer on them (``wftools.mocksliceviews``). Each write of
the description and each reading is validated here by the model of the contract that reads it —
the description is « dans la forme des schémas du contrat, que ses modèles valident » (EP-11,
« Le témoin ») —, and no key of a file is one its model ignores. Loading them and comparing the
answers of the service is US-2770/L2.
"""

import json
from datetime import date
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import AwareDatetime, BaseModel, RootModel
from support import WITNESS

from waterfall.api.contract.models import (
    ActualCostLine,
    CurrentRevisionMark,
    NodeCreate,
    PaginationMeta,
    PilotHealth,
    PortfolioCostCurve,
    PortfolioCostStructure,
    PortfolioPerformance,
    PortfolioProjectRow,
    PortfolioRisks,
    PortfolioScope,
    PortfolioValue,
    PortfolioWorkload,
    ProjectCreate,
    ProjectRatio,
    RevisionCreate,
    RiskReviewWrite,
    RiskWrite,
    StateTransition,
)
from waterfall.witness.filling import Strict

SLICE = WITNESS.parent / "witness" / "portfolio"


class _Node(Strict):
    node_id: UUID
    node: NodeCreate


class _Task(_Node):
    started_on: date | None
    completed_on: date | None


class _Revision(Strict):
    revision_id: UUID
    opened_at: AwareDatetime
    create: RevisionCreate
    marked_at: AwareDatetime | None
    mark: CurrentRevisionMark | None
    abandoned_at: AwareDatetime | None


class _Review(Strict):
    at: AwareDatetime
    review: RiskReviewWrite


class _Risk(Strict):
    risk_id: UUID
    declared_at: AwareDatetime
    risk: RiskWrite
    own_estimate: list[_Node]
    reviews: list[_Review]


class _Import(Strict):
    cost_import_id: UUID
    imported_at: AwareDatetime
    lines: list[ActualCostLine]


class _Project(Strict):
    project_id: UUID
    created_at: AwareDatetime
    project: ProjectCreate
    inflation_rate: ProjectRatio
    win_probability: ProjectRatio
    reference_revision_id: UUID | None
    transitions: list[StateTransition]
    revisions: list[_Revision]
    tasks: list[_Task]
    lines: list[_Node]
    risks: list[_Risk]
    imports: list[_Import]


class _ProjectList(Strict):
    scope: PortfolioScope
    items: list[PortfolioProjectRow]
    meta: PaginationMeta


READINGS: dict[str, type[BaseModel]] = {
    "getPortfolioProjects": _ProjectList,
    "getPortfolioValue": PortfolioValue,
    "getPortfolioWorkload": PortfolioWorkload,
    "getPortfolioPerformance": PortfolioPerformance,
    "getPortfolioCostStructure": PortfolioCostStructure,
    "getPortfolioRisks": PortfolioRisks,
    "getPortfolioCostCurve": PortfolioCostCurve,
    "getPortfolioPilotHealth": PilotHealth,
}


def _ignored(model: object, data: object, path: str = "") -> list[str]:
    """Name each key of the data the model it was validated into does not hold."""
    if isinstance(model, RootModel):
        return _ignored(cast("RootModel[Any]", model).root, data, path)
    if isinstance(model, BaseModel) and isinstance(data, dict):
        # A field is read under its alias: `from`, a keyword of Python, is held by `from_`.
        fields = {info.alias or name: name for name, info in type(model).model_fields.items()}
        found: list[str] = []
        for key, value in cast("dict[str, Any]", data).items():
            if key not in fields:
                found.append(f"{path}/{key}")
            else:
                found.extend(_ignored(getattr(model, fields[key]), value, f"{path}/{key}"))
        return found
    if isinstance(model, list) and isinstance(data, list):
        items = zip(cast("list[Any]", model), cast("list[Any]", data), strict=True)
        return [
            each
            for rank, (item, value) in enumerate(items)
            for each in _ignored(item, value, f"{path}/{rank}")
        ]
    return []


def _documents(directory: str) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((SLICE / directory).glob("*.json"))
    ]


@pytest.mark.requirement("WF-QUA-0040-A")
def test_each_project_of_the_slice_is_described_by_the_models_of_the_contract() -> None:
    described = _documents("projects")
    assert len(described) == 10
    for document in described:
        project = _Project.model_validate(document["value"])
        assert _ignored(project, document["value"]) == [], project.project.code
        assert project.tasks
        assert project.lines
        assert project.transitions[0].to_state.value == "created"


@pytest.mark.requirement("WF-QUA-0040-A")
def test_each_expected_reading_is_an_answer_of_its_operation() -> None:
    readings = _documents("readings")
    assert sorted(document["operation"] for document in readings) == sorted(READINGS)
    for document in readings:
        model = READINGS[document["operation"]]
        answer = model.model_validate(document["value"])
        assert _ignored(answer, document["value"]) == [], document["operation"]
        assert document["query"]["as_of"] == "2026-06-03"


@pytest.mark.requirement("WF-QUA-0040-A")
def test_a_key_that_no_model_of_the_contract_holds_is_named() -> None:
    document = _documents("projects")[0]["value"]
    document["tasks"][0]["node"]["task"]["colour"] = "rouge"
    project = _Project.model_validate(document)
    assert _ignored(project, document) == ["/tasks/0/node/task/colour"]
