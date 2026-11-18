# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The copy of a revision: its differentials and the own estimates of its risks (US-2550/L3).

A revision created from a marked one takes up every structure of it — the differentials not merged
and the own estimates of the risks identified or dismissed included, with their tasks, their lines
and their lineages — but the differentials already merged, which it does not take up
(WF-REV-0100, E-04, #1758); every table that bears the revision holds as many rows in it as in the
revision marked, the structures not taken up left out (WF-DAT-0010). That a merge and an
occurrence consume a structure for real is proved with US-2560 and US-2620: here a structure is
marked merged around the service.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import on, opened_amendment, structures_path
from estimate_support import Costing, Lines, costing
from nodes_support import Tree, mark, opened
from projects_support import PROJECTS, Scene
from projects_support import scene as make_scene
from risks_support import Costed, costed, declared, material
from sqlalchemy import func, select, update

from waterfall.core.estimate.tables import (
    EstimateLine,
    RevisionRate,
)
from waterfall.core.planning.tables import Node, Task, TaskLink
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.risks.tables import RiskEvaluation

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from sqlalchemy.orm import Session
    from support import ContractClient

    from waterfall.platform.database import Database


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


def structures_of(session: Session, revision_id: UUID) -> list[CostStructure]:
    """Read the structures of a revision, in the order of their lineage."""
    return list(
        session.scalars(
            select(CostStructure)
            .where(CostStructure.revision_id == revision_id)
            .order_by(CostStructure.lineage_id)
        )
    )


def counts(session: Session, revision_id: UUID, excluded: list[UUID]) -> dict[str, int]:
    """Count the rows each table that bears a revision holds for it, the structures left out."""
    kept = [each.id for each in structures_of(session, revision_id) if each.id not in excluded]

    def count(table: Any, *criteria: Any) -> int:
        return session.scalar(select(func.count()).select_from(table).where(*criteria)) or 0

    nodes = select(Node.id).where(Node.revision_id == revision_id, Node.structure_id.in_(kept))
    return {
        "cost_structure": len(kept),
        "node": count(Node, Node.revision_id == revision_id, Node.structure_id.in_(kept)),
        "task": count(Task, Task.structure_id.in_(kept)),
        "task_link": count(
            TaskLink, TaskLink.revision_id == revision_id, TaskLink.structure_id.in_(kept)
        ),
        "estimate_line": count(EstimateLine, EstimateLine.node_id.in_(nodes)),
        "risk_evaluation": count(RiskEvaluation, RiskEvaluation.revision_id == revision_id),
        # The images of the calendars, the categories and the roles are kept by the marking of a
        # revision, not copied: only the rates are.
        "revision_rate": count(RevisionRate, RevisionRate.revision_id == revision_id),
    }


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_revision_created_from_a_marked_one_takes_up_its_differentials_and_risks_own_estimates(
    api: ContractClient, project: Costed
) -> None:
    # « une révision créée à partir d'une révision marquée en reprend toutes les structures,
    # différentielles et propres des risques comprises, hors les structures différentielles déjà
    # fusionnées »: the main structure, the differentials not merged, with their tasks, lines and
    # lineages, and the own estimates of the risks, one identified, one dismissed.
    stage = project.stage
    first = on(project.tree, opened_amendment(api, project, "Avenant 1"))
    second_id = opened_amendment(api, project, "Avenant 2")
    merged_id = opened_amendment(api, project, "Avenant fusionné")
    Lines(first).made(first.made("Essais"), **material(project.costs, "Banc d'essai", "50.00"))
    identified = declared(project)
    dismissed = declared(project, "Fournisseur défaillant")
    with stage.owner.begin() as connection:
        connection.execute(
            update(CostStructure).where(CostStructure.id == UUID(merged_id)).values(is_merged=True)
        )
        connection.execute(
            update(RiskEvaluation)
            .where(RiskEvaluation.risk_id == dismissed.risk_id)
            .values(state="dismissed", provision_node_id=None)
        )
    mark(stage, project.tree.revision)

    created = opened(api, stage)
    new_id = UUID(created["revision_id"])
    with stage.database.transaction() as session:
        marked = structures_of(session, project.revision_id)
        taken = structures_of(session, new_id)
        by_lineage = {each.lineage_id: each for each in taken}
        merged = next(each for each in marked if each.id == UUID(merged_id))
        # Every structure of the revision marked but the one merged is in the new one, under an
        # identifier of its own and its lineage, its label, its kind and its risk.
        assert len(marked) == 6
        assert len(taken) == 5
        assert merged.lineage_id not in by_lineage
        for source in marked:
            if source is merged:
                continue
            copy = by_lineage[source.lineage_id]
            assert copy.id != source.id
            assert (copy.kind, copy.label, copy.risk_id) == (
                source.kind,
                source.label,
                source.risk_id,
            )
            assert (copy.planning_start_on, copy.is_merged) == (source.planning_start_on, False)
        assert {each.kind for each in taken} == {"main", "amendment", "risk"}
        assert {each.risk_id for each in taken if each.kind == "risk"} == {
            identified.risk_id,
            dismissed.risk_id,
        }
        # The nodes of each structure taken up: the lineages of its source, in the same shape.
        for source in marked:
            if source is merged:
                continue
            copy = by_lineage[source.lineage_id]
            shapes = [
                sorted(
                    (each.lineage_id, each.kind, each.rank)
                    for each in session.scalars(select(Node).where(Node.structure_id == id_))
                )
                for id_ in (source.id, copy.id)
            ]
            assert shapes[0] == shapes[1]
        # Every table that bears the revision: as many rows as in the revision marked, but those
        # of the structure merged (WF-DAT-0010).
        assert counts(session, new_id, []) == counts(session, project.revision_id, [merged.id])
    listed_in_new = [
        (each["kind"], each["label"])
        for each in api.get(
            f"{PROJECTS}/{project.project_id}/revisions/{new_id}/structures",
            headers=stage.manager.headers,
        ).json()
    ]
    assert ("amendment", "Avenant fusionné") not in listed_in_new
    assert listed_in_new.count(("amendment", "Avenant 1")) == 1
    assert listed_in_new.count(("amendment", "Avenant 2")) == 1
    assert second_id != merged_id


@pytest.mark.requirement("WF-REV-0100-A")
def test_a_differential_taken_up_is_read_against_the_main_structure_as_it_was(
    api: ContractClient, project: Costed
) -> None:
    # The lineages are kept: the differential of the revision created is still the diff with the
    # main structure it was, its additions added and the rest unchanged.
    stage = project.stage
    amendment = on(project.tree, opened_amendment(api, project, "Avenant 1"))
    Lines(amendment).made(amendment.made("Essais"), **material(project.costs, "Banc", "50.00"))
    mark(stage, project.tree.revision)
    created = opened(api, stage)
    copied = Tree(api, stage, created)
    path = structures_path(project).replace(str(project.revision_id), created["revision_id"])
    structures = api.get(path, headers=stage.manager.headers).json()
    (found,) = [each for each in structures if each["kind"] == "amendment"]
    assert found["label"] == "Avenant 1"
    read = on(copied, found["structure_id"]).read().json()
    marks = {
        (each["task"] or each["estimate_line"])["label"]: each["difference"]
        for each in read["items"]
    }
    assert marks == {
        "Étude": "unchanged",
        "Plans": "unchanged",
        "Réalisation": "unchanged",
        "Fabrication": "unchanged",
        "Essais": "added",
        "Banc": "added",
    }
