# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The statements of the computation of the scopes of a day, counted (#3569, #3802).

The computation of the indicators and the curves of scopes reads the tree of the revision computed
and that of its reference once, the remaining to commit drawn from them, and the actual cost of
every scope by one sum by subproject: a scope more costs one statement only, the tracked lines of
its curves by day of document. The project is a project In progress priced task by task, a
subproject bearing one of its lines (``day_indicators_support``).
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from costs_support import load_import
from day_indicators_support import Planned, completed, dated, priced, subproject
from planning_support import DAY
from projects_support import Scene
from projects_support import scene as make_scene
from sqlalchemy import event

from waterfall.core.costs.interface import PROJECT, UNASSIGNED, CostScope
from waterfall.core.indicators.caching import day_entry
from waterfall.core.indicators.interface import IndicatorsReading, day_reading
from waterfall.platform.database import utc_now

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


def statements(stage: Scene, scopes: list[CostScope]) -> list[str]:
    """Give the statements the computation of the scopes of the day sends, in their order."""
    sent: list[str] = []

    def heard(*arguments: Any) -> None:
        sent.append(str(arguments[2]))

    with stage.database.transaction() as session:
        project_id = UUID(stage.project["project_id"])
        reading = day_reading(session, project_id, IndicatorsReading(PROJECT, utc_now()))
        assert reading is not None
        engine = session.get_bind()
        event.listen(engine, "before_cursor_execute", heard)
        try:
            day_entry(session, reading.basis, reading.context, scopes)
        finally:
            event.remove(engine, "before_cursor_execute", heard)
    return sent


def test_a_scope_more_costs_one_statement_and_the_actual_cost_is_summed_once(
    api: ContractClient, stage: Scene
) -> None:
    # A criterion of the lot's own (#3802), which reprises no Vérif: it cites no requirement.
    lot = UUID(subproject(api, stage, "10001", "Lot 10001"))
    found = priced(api, stage, [Planned("Études", "400"), Planned("Câblage", "600", str(lot))])
    completed(found.tree, "Études", DAY)
    load_import(stage, UUID(stage.project["project_id"]), [dated("FA-1", None, "500.00", DAY)])
    alone = statements(stage, [lot])
    every = statements(stage, [PROJECT, lot, UNASSIGNED])
    assert len(every) == len(alone) + 2, (alone, every)
    # The actual cost is read from its table once for the sum of every scope, and once by scope
    # for the days it falls on.
    for sent, scopes in ((alone, 1), (every, 3)):
        read = [each for each in sent if "FROM cost_line" in each]
        assert len(read) == 1 + scopes, sent
    # The lines of a revision are read once by revision: the remaining does not read them again.
    rows = [each for each in alone if "FROM estimate_line" in each]
    revisions = {found.reference_id, UUID(found.tree.revision["revision_id"])}
    assert len(rows) == len(revisions), alone
