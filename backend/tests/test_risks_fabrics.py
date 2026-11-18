# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The fabrics every lot of the back of EP-08 starts from (``risks_support``, US-2550/L1).

Tests of the tools of the tests, which cover no requirement: the project costed at 1 000, read
through the service; the risk of severity 200 at 30 %, its own estimate and its provision line of
60, which the estimate tells a provision by its category, in the structure the planning reads; the
differential beside the main structure, which it leaves as it was.
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import Costing, costing
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import (
    ESTIMATE,
    PROVISION,
    SEVERITY,
    STUDY,
    Costed,
    costed,
    declared,
    differential,
)
from sqlalchemy import select

from waterfall.core.planning.tallying import provision_lines
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.risks.tables import Risk, RiskEvaluation

if TYPE_CHECKING:
    from uuid import UUID

    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name, the provision's among them."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000."""
    return costed(api, stage, costs)


def lines_of(project: Costed, structure_id: UUID) -> dict[str, dict[str, Any]]:
    """Read the lines of a structure of the current revision through the service, by node."""
    path = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/structures"
    answer = project.tree.api.get(
        f"{path}/{structure_id}/nodes", headers=project.stage.manager.headers
    )
    assert answer.status_code == 200, answer.text
    return {
        each["node_id"]: each for each in answer.json()["items"] if each["kind"] == "estimate_line"
    }


def total(lines: dict[str, dict[str, Any]]) -> Decimal:
    """Sum the re-estimated amounts of lines read."""
    return sum(
        (Decimal(each["estimate_line"]["reestimated_amount"]) for each in lines.values()),
        Decimal(0),
    )


def test_the_project_costed_bears_1000_in_two_tasks_of_its_main_structure(
    project: Costed,
) -> None:
    lines = lines_of(project, project.structure_id)
    assert total(lines) == ESTIMATE
    assert {each["parent_id"] for each in lines.values()} == {
        str(each) for each in project.tasks.values()
    }


def test_the_risk_declared_bears_its_severity_and_its_provision_line_under_the_study(
    project: Costed,
) -> None:
    # The provision of 60 is in the main structure, under the study, and the estimate tells it a
    # provision by its category: the planning reads it among the provisions of the structure, and
    # no other line. The own estimate of the risk holds the 200 of its severity.
    risk = declared(project)
    main = lines_of(project, project.structure_id)
    provision = main[str(risk.provision_node_id)]
    assert provision["parent_id"] == str(project.tasks[STUDY])
    assert Decimal(provision["estimate_line"]["reestimated_amount"]) == PROVISION
    assert total(main) == ESTIMATE + PROVISION
    assert total(lines_of(project, risk.structure_id)) == SEVERITY
    with project.stage.database.transaction() as session:
        provisions = provision_lines(session, project.project_id, project.structure_id)
        evaluation = session.scalars(
            select(RiskEvaluation).where(RiskEvaluation.risk_id == risk.risk_id)
        ).one()
        held = session.scalar(select(Risk.id).where(Risk.id == risk.risk_id))
    assert provisions == {risk.provision_node_id}
    assert (evaluation.state, evaluation.structure_id) == ("identified", risk.structure_id)
    assert held == risk.risk_id


def test_the_differential_is_a_structure_of_its_own_beside_the_main_one(project: Costed) -> None:
    structure_id = differential(project)
    with project.stage.database.transaction() as session:
        kinds = dict(
            session.execute(
                select(CostStructure.id, CostStructure.kind).where(
                    CostStructure.revision_id == project.revision_id
                )
            ).all()
        )
    assert kinds == {project.structure_id: "main", structure_id: "amendment"}
    assert total(lines_of(project, project.structure_id)) == ESTIMATE
