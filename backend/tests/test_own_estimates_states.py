# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The states of an own estimate prepared as a differential, and its fabrics (EP-30, US-3070/L1).

Tests of the socle, which close no criterion: the fabrics of EP-30 (``own_estimates_support``) read
in the state each says — whole and up to date, out of date, pruned by a marking —; an own estimate
of EP-08 born up to date, kept so by the writes of a provision line and put out of date by any other
write of the main structure; and the copy of a revision, which keeps the state of each own estimate
and what a pruned one abandons, and whose abandonment takes them away. They cover no requirement.
"""

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from nodes_support import mark
from own_estimates_support import (
    ABANDONED,
    ADDED,
    MAIN_ADDED,
    MODIFIED,
    held_lines,
    held_tasks,
    out_of_date_risk,
    pruned_risk,
    risk_differential,
)
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import ESTIMATE, SEVERITY, STUDY, Costed, Risks, costed
from sqlalchemy import select, update

from waterfall.core.planning.tables import Node
from waterfall.core.revisions.interface import (
    Abandonment,
    abandonments_of,
    own_estimate_state,
    own_estimate_states,
)
from waterfall.core.revisions.tables import CostStructure, OwnEstimateAbandonment, Revision
from waterfall.platform.errors import NotFoundError

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.core.revisions.interface import OwnEstimateState
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


def state(project: Costed, structure_id: UUID | str) -> OwnEstimateState:
    """Read the state of an own estimate through the interface of the revisions."""
    with project.stage.database.transaction() as session:
        return own_estimate_state(session, project.project_id, _uuid(structure_id))


def _uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(value)


def test_the_own_estimate_of_the_fabric_is_whole_up_to_date_and_designates_a_severity_of_200(
    project: Costed,
) -> None:
    risk = risk_differential(project)
    found = state(project, risk.structure_id)
    assert (found.whole, found.pruned, found.up_to_date, found.consumed) == (
        True,
        False,
        True,
        False,
    )
    assert risk.base_id is not None
    base, own = held_lines(project, risk.base_id), held_lines(project, risk.structure_id)
    assert sum(base.values(), Decimal(0)) == ESTIMATE
    assert sum(own.values(), Decimal(0)) - sum(base.values(), Decimal(0)) == SEVERITY
    assert own[MODIFIED[0]] == MODIFIED[2]
    assert own[ADDED[0]] == ADDED[1]
    assert held_tasks(project, risk.structure_id) == {STUDY}
    assert held_tasks(project, risk.base_id) == {STUDY, ABANDONED}


def test_the_own_estimate_of_the_fabric_is_out_of_date_once_the_main_structure_moved_on(
    project: Costed,
) -> None:
    risk = out_of_date_risk(project)
    found = state(project, risk.structure_id)
    assert (found.whole, found.up_to_date) == (True, False)
    assert MAIN_ADDED in held_tasks(project, project.structure_id)
    assert STUDY not in held_tasks(project, project.structure_id)
    assert held_tasks(project, risk.structure_id) == {STUDY}


def test_the_own_estimate_of_the_fabric_pruned_by_a_marking_keeps_what_it_designates(
    project: Costed,
) -> None:
    risk = pruned_risk(project)
    found = state(project, risk.structure_id)
    assert (found.pruned, found.pruned_revision_id) == (True, project.revision_id)
    with project.stage.database.transaction() as session:
        status = session.scalar(select(Revision.status).where(Revision.id == project.revision_id))
        bases = session.scalars(
            select(CostStructure.id).where(CostStructure.differential_id == risk.structure_id)
        ).all()
        abandoned = abandonments_of(session, project.project_id, risk.structure_id)
        lineage = session.scalar(select(Node.lineage_id).where(Node.id == project.tasks[ABANDONED]))
    assert status == "marked"
    assert bases == []
    assert abandoned == (Abandonment(lineage),)
    assert set(held_lines(project, risk.structure_id)) == {MODIFIED[0], ADDED[0]}


def test_the_state_of_a_structure_that_is_no_own_estimate_is_not_found(project: Costed) -> None:
    with pytest.raises(NotFoundError):
        state(project, project.structure_id)


def _counter_retained(project: Costed, structure_id: UUID) -> int | None:
    """Read the counter of the main structure an own estimate retained, around the service."""
    with project.stage.owner.connect() as connection:
        return connection.scalar(
            select(CostStructure.main_lock_version).where(CostStructure.id == structure_id)
        )


def _consumed(project: Costed, structure_id: UUID) -> int | None:
    """Consume an own estimate around the service, as an occurrence does; give its counter retained."""
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.id == structure_id).values(is_merged=True)
        )
    return _counter_retained(project, structure_id)


def test_an_own_estimate_stays_up_to_date_across_the_writes_of_a_provision_line(
    api: ContractClient, project: Costed
) -> None:
    # Two risks declared through the service: each own estimate born up to date, the declaration of
    # the second — its provision line created in the main structure — leaves the first so; the
    # severity of the first written, its provision line with it, leaves both so, and does not carry
    # over a consumed own estimate, which keeps its counter. A task of the main structure puts both
    # out of date, and a provision written after does not bring them back.
    risks = Risks(api, project)
    first = risks.declared(label="Grue")
    consumed = UUID(risks.declared(label="Grève")["structure_id"])
    second = risks.declared(label="Météo")
    assert [state(project, each["structure_id"]).up_to_date for each in (first, second)] == [
        True,
        True,
    ]
    held = _consumed(project, consumed)
    risks.costed_in(first, "200.00")
    assert [state(project, each["structure_id"]).up_to_date for each in (first, second)] == [
        True,
        True,
    ]
    assert _counter_retained(project, consumed) == held
    assert (state(project, consumed).consumed, state(project, consumed).up_to_date) == (True, False)
    project.tree.made(MAIN_ADDED)
    risks.costed_in(second, "100.00")
    with project.stage.database.transaction() as session:
        states = own_estimate_states(session, project.project_id, project.revision_id)
    assert [each.up_to_date for each in states] == [False, False, False]


def test_the_copy_of_a_revision_keeps_the_state_of_an_own_estimate_and_what_it_abandons(
    api: ContractClient, project: Costed
) -> None:
    # The own estimate pruned by the marking is taken up pruned, against the same revision, up to
    # date, with what it abandons; the abandonment of the copy takes its abandonments away, those
    # of the marked revision staying.
    risk = pruned_risk(project)
    risks = Risks(api, project)
    opened = risks.revision()
    with project.stage.database.transaction() as session:
        [copied] = own_estimate_states(session, project.project_id, opened["revision_id"])
        abandoned = abandonments_of(session, project.project_id, copied.structure_id)
        kept = abandonments_of(session, project.project_id, risk.structure_id)
    assert (copied.risk_id, copied.pruned_revision_id) == (risk.risk_id, project.revision_id)
    assert copied.up_to_date
    assert abandoned == kept
    assert len(kept) == 1
    risks.abandon(opened)
    with project.stage.database.transaction() as session:
        left = session.scalars(select(OwnEstimateAbandonment.revision_id)).all()
    assert left == [project.revision_id]


def test_the_copy_of_a_revision_keeps_an_own_estimate_whole_and_up_to_date(
    api: ContractClient, project: Costed
) -> None:
    risk = risk_differential(project)
    mark(project.stage, {"revision_id": str(project.revision_id)})
    opened = Risks(api, project).revision()
    with project.stage.database.transaction() as session:
        [copied] = own_estimate_states(session, project.project_id, opened["revision_id"])
    assert (copied.risk_id, copied.whole, copied.up_to_date) == (risk.risk_id, True, True)
