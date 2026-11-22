# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The columns of a line the constraints tie, in the update of a differential (US-3050/L4).

A labour line has its role and its hours and no disbursement, any other the reverse
(``hours_of_a_role``, ``unit_disbursement_without_role``): the role, the hours and the unit
disbursement go together. When the differential designates one of them and the main structure
changes another, the update keeps the three as the differential has them and the report names them
all (``kept``); the line is never written half taken. Every answer is checked against the contract
(``ContractClient``).
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from amendments_support import OutOfDate, node_labelled, out_of_date
from estimate_support import Costing, Lines, add_role, costing
from projects_support import Scene
from projects_support import scene as make_scene
from rebases_support import read_report, rebased
from risks_support import STUDY, Costed, costed, material
from sqlalchemy import update

from waterfall.core.estimate.tables import EstimateLine

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

TASK = STUDY
LINE = "Ligne liée"
COUPLED = ["resource_role", "hours", "unit_disbursement"]
WEEK = (8, 8, 8, 8, 8, 0, 0)


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a fresh platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def costs(stage: Scene) -> Costing:
    """Give the categories the lines name."""
    return costing(stage.database)


@pytest.fixture
def project(api: ContractClient, stage: Scene, costs: Costing) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed(api, stage, costs)


def labour(role: object, hours: str = "4") -> dict[str, Any]:
    """Give a labour line of the role and the hours, as the service receives it."""
    return {
        "label": LINE,
        "quantity": "1",
        "resource_role_id": str(role),
        "hours": hours,
    }


def turned(project: Costed, **columns: object) -> None:
    """Write the columns of the line of the main structure, as no operation of the service does.

    The service never changes the kind of a line (``entries``): the role stays or the line is
    another; the rows are written as they would be by a repair of the data.
    """
    node = node_labelled(project.tree, LINE)["node_id"]
    with project.stage.database.transaction() as session:
        session.execute(
            update(EstimateLine)
            .where(EstimateLine.project_id == project.project_id, EstimateLine.node_id == node)
            .values(**columns)
        )


def material_now(project: Costed, amount: str = "100.00") -> None:
    """Make the line of the main structure a line of material, at an amount."""
    turned(
        project,
        cost_category_id=project.costs.material,
        resource_role_id=None,
        hours=None,
        unit_disbursement=Decimal(amount),
    )


def late_with(api: ContractClient, project: Costed, line: dict[str, Any]) -> OutOfDate:
    """Give a differential out of date whose structures both bear a line under a task."""
    Lines(project.tree).made(node_labelled(project.tree, TASK), **line)
    return out_of_date(api, project)


def rebase(api: ContractClient, late: OutOfDate) -> list[dict[str, Any]]:
    """Update the differential, which must be done; give the differences its report presented."""
    found = read_report(api, late)
    answer = rebased(api, late)
    assert answer.status_code == 200, answer.text
    return found["differences"]


def kept_fields(differences: list[dict[str, Any]], label: str = LINE) -> list[list[str]]:
    """Give the fields named kept of a line."""
    return [
        each["fields"]
        for each in differences
        if each["change"] == "kept" and each["label"] == label
    ]


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_hours_the_differential_designates_keep_the_role_and_the_disbursement_together(
    api: ContractClient, project: Costed
) -> None:
    # [US-3050] A value the differential designates and the main structure changed keeps the
    # differential's, and the report names it (kept): the differential changes the hours of a
    # labour line, the main structure makes it a line of material; the three coupled columns stay
    # the differential's, named all, and the update is done — the line is not written half taken.
    role = add_role(project.stage.database, "SOUD", WEEK)
    late = late_with(api, project, labour(role))
    Lines(late.amendment).changed(node_labelled(late.amendment, LINE), hours="6")
    material_now(project)
    assert kept_fields(rebase(api, late)) == [COUPLED]
    line = node_labelled(late.amendment, LINE)["estimate_line"]
    assert line["resource_role_id"] == str(role)
    assert float(line["hours"]) == 6
    assert line["unit_disbursement"] is None


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_role_the_differential_designates_keeps_the_hours_and_the_disbursement_together(
    api: ContractClient, project: Costed
) -> None:
    # [US-3050] The differential changes the role of a labour line from one to another, the main
    # structure makes it a line of material: the three stay the differential's, named all.
    first = add_role(project.stage.database, "SOUD", WEEK)
    second = add_role(project.stage.database, "MONT", WEEK)
    late = late_with(api, project, labour(first))
    Lines(late.amendment).changed(node_labelled(late.amendment, LINE), resource_role_id=str(second))
    material_now(project)
    assert kept_fields(rebase(api, late)) == [COUPLED]
    line = node_labelled(late.amendment, LINE)["estimate_line"]
    assert line["resource_role_id"] == str(second)
    assert float(line["hours"]) == 4
    assert line["unit_disbursement"] is None


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_disbursement_the_differential_designates_keeps_the_role_and_the_hours_together(
    api: ContractClient, project: Costed
) -> None:
    # [US-3050] The reverse: the differential changes the unit disbursement of a line of
    # material, the main structure makes it a labour line; the three stay the differential's.
    role = add_role(project.stage.database, "SOUD", WEEK)
    late = late_with(api, project, material(project.costs, LINE, "100.00"))
    Lines(late.amendment).changed(node_labelled(late.amendment, LINE), unit_disbursement="120.00")
    turned(
        project,
        cost_category_id=project.costs.labour,
        resource_role_id=role,
        hours=Decimal(4),
        unit_disbursement=None,
    )
    assert kept_fields(rebase(api, late)) == [COUPLED]
    line = node_labelled(late.amendment, LINE)["estimate_line"]
    assert line["resource_role_id"] is None
    assert line["hours"] is None
    assert float(line["unit_disbursement"]) == 120


@pytest.mark.requirement("WF-REV-0100-A")
def test_the_coupled_columns_the_differential_does_not_designate_are_carried_together(
    api: ContractClient, project: Costed
) -> None:
    # [US-3050] What the differential does not designate is carried: the main structure makes a
    # labour line a line of material, the differential changing only the label; the three columns
    # follow together, nothing is kept, the label stays the differential's.
    role = add_role(project.stage.database, "SOUD", WEEK)
    late = late_with(api, project, labour(role))
    Lines(late.amendment).changed(node_labelled(late.amendment, LINE), label="Ligne renommée")
    material_now(project)
    found = rebase(api, late)
    assert kept_fields(found, "Ligne renommée") == []
    line = node_labelled(late.amendment, "Ligne renommée")["estimate_line"]
    assert line["resource_role_id"] is None
    assert line["hours"] is None
    assert float(line["unit_disbursement"]) == 100
