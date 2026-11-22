# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The measure of the merge and of the occurrence: what it counts, and what it leaves (US-2650/L2).

``make measure-core`` merges a differential it opens and has an identified risk occur, each one
rolled back. The tool is no requirement's, and its tests cite none: they hold its promise to leave
nothing written, on the database of the tests, by counting the rows of the tables the two touch.
"""

from typing import TYPE_CHECKING, Any

import pytest
from estimate_support import costing
from occurrence_support import occurring
from projects_support import scene as make_scene
from risks_support import Costed, costed
from sqlalchemy import Engine, func, select

from measure.__main__ import PARTS
from measure.risks import measure_merge, measure_occurrence
from measure.target import MeasureError, Target
from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.history.tables import UndoEntry
from waterfall.core.planning.interface import Place
from waterfall.core.planning.tables import Node, Task
from waterfall.core.revisions.tables import CostStructure, Revision
from waterfall.core.risks.tables import RiskEvaluation, RiskReview
from waterfall.platform.correlation import correlation_id_from
from waterfall.platform.logs import PLATFORM, logging_context

if TYPE_CHECKING:
    from realm import TestRealm
    from support import ContractClient

    from waterfall.platform.database import Database

_COUNTED = (
    Node,
    Task,
    EstimateLine,
    CostStructure,
    Revision,
    RiskEvaluation,
    RiskReview,
    UndoEntry,
)


@pytest.fixture
def project(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Costed:
    """Give the project its manager made, costed at 1 000 in its current revision."""
    stage = make_scene(api, owner, database, realm)
    return costed(api, stage, costing(stage.database))


def _target(project: Costed) -> Target:
    place = Place(project.project_id, project.revision_id, project.structure_id)
    return Target(place, 0, project.stage.manager.user_id)


def _state(database: Database) -> dict[str, Any]:
    with database.transaction() as session:
        counts = {
            table.__tablename__: session.scalar(select(func.count()).select_from(table))
            for table in _COUNTED
        }
        revisions = sorted(session.execute(select(Revision.id, Revision.status)).all())
        evaluations = sorted(
            session.execute(select(RiskEvaluation.risk_id, RiskEvaluation.state)).all()
        )
    return {"counts": counts, "revisions": revisions, "evaluations": evaluations}


def test_the_merge_and_the_occurrence_are_parts_of_the_measure() -> None:
    assert {"merge", "occurrence"} <= set(PARTS)


def test_a_merge_measured_leaves_nothing_written(project: Costed) -> None:
    database = project.stage.database
    before = _state(database)

    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        measure = measure_merge(database, _target(project), 2)

    assert _state(database) == before
    assert measure.name == "merge a differential"
    assert measure.summary is not None
    assert measure.summary.runs == 2


def test_an_occurrence_measured_leaves_the_risk_identified_and_nothing_written(
    api: ContractClient, project: Costed
) -> None:
    occurring(api, project)
    database = project.stage.database
    before = _state(database)

    with logging_context(correlation_id=correlation_id_from(None), actor=PLATFORM):
        measure = measure_occurrence(database, _target(project), 2)

    assert _state(database) == before
    assert measure.summary is not None
    assert measure.summary.runs == 2


def test_an_occurrence_is_not_measured_on_a_project_without_an_identified_risk(
    project: Costed,
) -> None:
    with pytest.raises(MeasureError, match="no identified risk"):
        measure_occurrence(project.stage.database, _target(project), 1)
