# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The sums of the tracked lines of a project, which the indicators read (EP-09, EP-10).

The socle of EP-09 fixes how they name a scope: the whole project and the project alone by a word,
as the contract does, never by ``None``, whose sense would change from one function to the other.
US-1600 and US-1610/L2 write their tests where they fill them: ``actual_costs_until`` on lines
loaded through the interface of the actual costs (``costs_support``).
"""

from annotationlib import Format, call_evaluate_function, get_annotations
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from costs_support import cost, load_import
from projects_support import PROJECTS, Scene, create
from projects_support import scene as make_scene
from sqlalchemy import update

from waterfall.core.costs.interface import (
    PROJECT,
    UNASSIGNED,
    CostKey,
    CostLineLoad,
    CostScope,
    actual_cost_by_subproject,
    actual_costs_until,
)
from waterfall.core.costs.tables import CostLine

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


def test_the_sums_name_the_project_alone_alike_and_the_whole_project_by_a_word() -> None:
    assert (PROJECT, UNASSIGNED) == ("project", "unassigned")
    assert get_annotations(actual_costs_until, format=Format.FORWARDREF)["scope"] is CostScope
    assert (
        call_evaluate_function(CostScope.evaluate_value, Format.STRING)
        == "UUID | Literal['project', 'unassigned']"
    )
    # The key of the project alone in a sum by subproject is the scope that sums it alone.
    assert (
        get_annotations(actual_cost_by_subproject, format=Format.STRING)["return"]
        == "Mapping[CostKey, Decimal]"
    )
    assert (
        call_evaluate_function(CostKey.evaluate_value, Format.STRING)
        == "UUID | Literal['unassigned']"
    )


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def until(stage: Scene, day: date, scope: CostScope, project_id: UUID | None = None) -> Decimal:
    """Sum the tracked lines of a scope of a project, the stage's by default, until a day."""
    with stage.database.transaction() as session:
        return actual_costs_until(
            session, project_id or UUID(stage.project["project_id"]), day, scope
        )


def dated(number: str, code: str | None, amount: str, day: date) -> CostLineLoad:
    """Give a line an import loads, of a document dated ``day``."""
    return replace(cost(number, code, amount), document_date=day)


@pytest.mark.requirement("WF-CRE-0010-A")
def test_the_actual_costs_until_a_day_sum_the_tracked_lines_of_a_scope_dated_by_then(
    api: ContractClient, stage: Scene
) -> None:
    # The lines of the whole project, of the project alone — no subproject part, or a code no
    # subproject bears —, or of a subproject, dated on or before the day; a credit diminishes the
    # sum (« Une ligne de montant négatif est acceptée et diminue le coût réel. »), an excluded
    # line enters it not, nor a line of another project.
    project = UUID(stage.project["project_id"])
    response = api.post(
        f"{PROJECTS}/{project}/subprojects",
        headers=stage.manager.headers,
        json={"code": "SP-1", "label": "Câblage"},
    )
    assert response.status_code == 201, response.text
    cabling = UUID(response.json()["subproject_id"])
    elsewhere = UUID(create(api, stage.manager, label="Autre projet")["project_id"])
    load_import(
        stage,
        project,
        [
            dated("A", "SP-1", "1000.00", date(2026, 3, 31)),
            dated("B", "SP-1", "-200.00", date(2026, 4, 15)),
            dated("C", None, "300.00", date(2026, 4, 1)),
            dated("D", "SP-9", "50.00", date(2026, 4, 30)),
            dated("E", "SP-1", "700.00", date(2026, 4, 2)),
        ],
    )
    load_import(stage, elsewhere, [dated("A", "SP-1", "9999.00", date(2026, 3, 1))])
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostLine)
            .where(CostLine.project_id == project, CostLine.document_number == "E")
            .values(is_in_tracked_scope=False, excluded_reason="Hors contrat")
        )

    april = date(2026, 4, 30)
    assert until(stage, april, PROJECT) == Decimal("1150.00")
    assert until(stage, april, UNASSIGNED) == Decimal("350.00")
    assert until(stage, april, cabling) == Decimal("800.00")
    assert until(stage, date(2026, 4, 14), PROJECT) == Decimal("1300.00")
    assert until(stage, date(2026, 3, 30), PROJECT) == Decimal(0)
    assert until(stage, april, PROJECT, elsewhere) == Decimal("9999.00")
