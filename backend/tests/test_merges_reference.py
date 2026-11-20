# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What a merge leaves: the reference, the other differentials, what the main structure received.

US-2560/L2. The revision a merge marks is the reference without a designation, the former one
still read, and what follows a designation told of the reference it replaces (#4175); the merge
applies only what an up to date differential designates (#4034), keeps what the main structure
received since its opening, leaves another differential intact for the next revision, and the
trace of a risk occurred; a provision whose task leaves goes to another task; the loader of the
witness updates a differential before it merges it. Every answer is checked against the contract
(``ContractClient``).
"""

from dataclasses import replace
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

import pytest
from amendments_support import (
    MAIN_ADDED,
    MAIN_REESTIMATED,
    MAIN_RENAMED,
    OWN_ADDED,
    OWN_RENAMED,
    OutOfDate,
    commands_of,
    node_labelled,
    on,
    opened_amendment,
    out_of_date,
)
from estimate_support import Lines
from history_support import delete
from merges_support import (
    REFUSED,
    client,
    copy_of,
    costed_project,
    lines_of,
    main_of,
    merged,
    merging_worker,
    project_of,
    revision_of,
    structure_row,
    tasks_of,
)
from nodes_support import Tree, mark, opened, put_risk, refusal
from projects_support import PROJECTS, designate
from rebases_support import rebased
from risks_support import MAKING, STUDY, Costed, Risks, declared
from sqlalchemy import select, update

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.interface import Place, load_merge
from waterfall.core.planning.tables import Node
from waterfall.core.revisions.interface import differential_base
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.risks.tables import RiskReferenceShare
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.logs import logging_context

if TYPE_CHECKING:
    from openapi_core import OpenAPI
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database
    from waterfall.platform.keycloak import Keycloak
    from waterfall.platform.queue import TaskQueue
    from waterfall.platform.settings import ServiceSettings
    from waterfall.worker.runner import Worker


@pytest.fixture
def api(
    contract: OpenAPI,
    database: Database,
    keycloak: Keycloak,
    realm_settings: ServiceSettings,
    queue: TaskQueue,
) -> ContractClient:
    """Give a client of the application that deposits its tasks in the queue of the test."""
    return client(contract, database, keycloak, realm_settings, queue)


@pytest.fixture
def worker(database: Database, queue: TaskQueue) -> Worker:
    """Give a worker on the queue of the test that runs the merges."""
    return merging_worker(database, queue)


@pytest.fixture
def project(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    return costed_project(api, owner, database, realm)


def following(api: ContractClient, project: Costed) -> Costed:
    """Open the next revision of the project; give the project costed as it stands in it."""
    revision = opened(api, project.stage)
    tree = Tree(api, project.stage, revision)
    tasks = {label: node for label, (node, _, _) in tasks_of(project, tree.structure_id).items()}
    return replace(
        project,
        tree=tree,
        lines=Lines(tree),
        revision_id=UUID(revision["revision_id"]),
        structure_id=UUID(tree.structure_id),
        tasks=tasks,
    )


def amendment_in(api: ContractClient, project: Costed, label: str = "Avenant 1") -> str:
    """Open a differential in the revision of a project costed, as the manager does; give it."""
    path = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/structures"
    body = {"kind": "amendment", "label": label}
    answer = api.post(path, headers=project.stage.manager.headers, json=body)
    assert answer.status_code == 201, answer.text
    return answer.json()["structure_id"]


def designation(api: ContractClient, project: Costed, revision_id: object) -> Any:
    """Designate a marked revision the reference, as the manager does; give the answer."""
    path = f"{PROJECTS}/{project.project_id}"
    held = project_of(api, project)["lock_version"]
    sent = {"revision_id": str(revision_id), "confirmed": True, "lock_version": held}
    return api.put(f"{path}/reference-revision", headers=project.stage.manager.headers, json=sent)


# --- The reference -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0040-A")
def test_the_revision_a_merge_marks_is_the_reference_and_the_former_one_is_still_read(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « Après contractualisation d'un avenant, la révision produite est la référence sans
    # intervention de l'utilisateur, et l'ancienne reste consultable. »; « La désignation manuelle
    # est proposée tant que le projet n'a ni coût réel ni révision marquée depuis la dernière
    # désignation, et refusée au-delà. »: after a merge, refused by 409 (reference_correctable).
    mark(project.stage, {"revision_id": str(project.revision_id)})
    designate(api, project.stage, {"revision_id": str(project.revision_id)})
    second = following(api, project)
    amendment = amendment_in(api, second)
    on(second.tree, amendment).made("Essais")
    assert merged(api, second, worker, amendment, second.revision_id)["status"] == "succeeded"
    read = project_of(api, project)
    assert read["reference_revision_id"] == str(second.revision_id)
    assert revision_of(api, project, second.revision_id)["is_reference"] is True
    former = revision_of(api, project, project.revision_id)
    assert (former["status"], former["is_reference"]) == ("marked", False)
    assert set(tasks_of(project, project.structure_id)) == {STUDY, MAKING}
    assert commands_of(former)["designate_reference"] == (False, ["reference_correctable"])
    refused = designation(api, project, project.revision_id)
    assert refusal(refused) == (409, REFUSED, {"missing_condition": "reference_correctable"})


def share_rows(project: Costed, revision_id: object) -> dict[UUID, Decimal]:
    """Give the shares a reference revision holds, by risk."""
    with project.stage.owner.begin() as connection:
        rows = connection.execute(
            select(RiskReferenceShare.risk_id, RiskReferenceShare.provision_amount).where(
                RiskReferenceShare.revision_id == revision_id
            )
        )
        return dict(rows.all())


@pytest.mark.requirement("WF-RIS-0050-A")
def test_a_merge_tells_the_designation_the_reference_it_replaces(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « ce qui suit une désignation (register_designation) est prévenu de la nouvelle » (#4175): a
    # risk of 60 in the reference, dismissed in the next revision, keeps its share in the
    # reference the merge produces — the reference replaced named, the merge correcting nothing.
    risks = Risks(api, project)
    risk = risks.declared("0.3")
    risks.costed_at(risk, project.revision_id, "200.00")
    mark(project.stage, {"revision_id": str(project.revision_id)})
    designate(api, project.stage, {"revision_id": str(project.revision_id)})
    assert share_rows(project, project.revision_id) == {UUID(risk["risk_id"]): Decimal("60.00")}
    second = following(api, project)
    risks.reviewed(risks.risk(risk), state="dismissed")
    amendment = amendment_in(api, second)
    merged(api, second, worker, amendment, second.revision_id)
    assert share_rows(project, second.revision_id) == {UUID(risk["risk_id"]): Decimal("60.00")}


# --- What the merge applies ----------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_merge_applies_only_what_the_differential_designates(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « la fusion n'applique que ce que le différentiel désigne » (#4034): a task the main
    # structure received since the opening, a label it changed, a line it re-estimated stay in it
    # after the merge of the differential, updated first; what the differential designates is
    # applied — a task added, a label changed, a task removed.
    late = out_of_date(api, project)
    assert rebased(api, late).status_code == 200
    merged(api, project, worker, late.structure_id)
    labels = set(tasks_of(project, project.structure_id))
    assert {MAIN_ADDED, MAIN_RENAMED[1], OWN_ADDED, OWN_RENAMED[1]} <= labels
    assert {MAIN_RENAMED[0], OWN_RENAMED[0], "Montage", "Documentation"}.isdisjoint(labels)
    making = lines_of(project, project.structure_id)[MAIN_REESTIMATED[0]]
    assert making.unit_disbursement == Decimal(MAIN_REESTIMATED[1])


@pytest.mark.requirement("WF-REV-0050-A")
def test_a_line_the_differential_brings_to_120_and_the_main_one_reestimated_to_140(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « une ligne que le différentiel porte à 120 et que la principale a réestimée à 140 depuis
    # porte 120 de budgété et 140 de réestimé »: the update keeps the 120 of the differential
    # (rule 1), the merge gives it the line as its reference, the 140 re-estimated stays.
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    Lines(tree).changed(node_labelled(tree, "Fabrication"), unit_disbursement="120.00")
    project.lines.changed(node_labelled(project.tree, "Fabrication"), unit_disbursement="140.00")
    # Marked as a re-estimate is, around the service: the entry of the remaining asks a project in
    # progress, which the mark alone stands for here.
    held = lines_of(project, project.structure_id)["Fabrication"]
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(EstimateLine)
            .where(EstimateLine.node_id == held.node_id)
            .values(reestimated_at=utc_now())
        )
    assert rebased(api, OutOfDate(project, amendment, tree)).status_code == 200
    merged(api, project, worker, amendment)
    making = lines_of(project, project.structure_id)["Fabrication"]
    assert (making.budgeted_amount, making.reestimated_amount) == (
        Decimal("120.00"),
        Decimal("140.00"),
    )
    assert making.reference_unit_disbursement == Decimal("120.00")


@pytest.mark.requirement("WF-REV-0100-A")
def test_of_two_differentials_the_second_merged_once_updated_keeps_what_the_first_brought(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « de deux différentiels ouverts le même jour, la fusion du second, mis à jour dans la
    # révision suivante, laisse dans la structure principale tout ce que la fusion du premier y a
    # apporté »; « le différentiel fusionné se lit is_merged dans la révision marquée et n'est pas
    # repris par la suivante ; un autre différentiel de la même révision est intact, repris par la
    # révision suivante, et reste fusionnable » (WF-REV-0100).
    first = amendment_in(api, project, "Avenant 1")
    second = amendment_in(api, project, "Avenant 2")
    on(project.tree, first).made("Essais")
    on(project.tree, second).made("Recette")
    merged(api, project, worker, first, name="Avenant 1")
    assert structure_row(project, first).is_merged is True
    with project.stage.database.transaction() as session:
        assert differential_base(session, project.project_id, UUID(first)) is not None
    assert set(tasks_of(project, second)) == {STUDY, MAKING, "Recette"}
    later = following(api, project)
    held = copy_of(project, second, later.revision_id)
    lineage = structure_row(project, first).lineage_id
    with project.stage.database.transaction() as session:
        carried = session.scalars(
            select(CostStructure.id).where(
                CostStructure.revision_id == later.revision_id,
                CostStructure.lineage_id == lineage,
            )
        ).all()
    assert carried == []
    assert structure_row(project, held).is_merged is False
    assert rebased(api, OutOfDate(later, str(held), on(later.tree, str(held)))).status_code == 200
    merged(api, later, worker, held, later.revision_id, name="Avenant 2")
    main = main_of(project, later.revision_id)
    assert {"Essais", "Recette"} <= set(tasks_of(project, main))


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_trace_of_a_risk_occurred_crosses_the_merge(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « la trace d'un risque survenu (origin_risk_id) traverse la fusion (US-2620) »: a node of
    # the main structure the occurrence of a risk merged keeps it.
    risk_id = uuid4()
    put_risk(project.stage, str(project.tasks[MAKING]), risk_id)
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    tree.changed(node_labelled(tree, MAKING), label="Réalisation reprise")
    merged(api, project, worker, amendment)
    with project.stage.database.transaction() as session:
        origin = session.scalar(select(Node.origin_risk_id).where(Node.id == project.tasks[MAKING]))
    assert origin == risk_id
    assert "Réalisation reprise" in tasks_of(project, project.structure_id)


@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_provision_line_whose_task_the_merge_removes_goes_to_another_task(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « une ligne de provision dont la fusion retire la tâche passe sur la tâche parente »: from
    # the first level, to the first task the merge leaves at the first level (#789).
    risk = declared(project)
    amendment = opened_amendment(api, project)
    tree = on(project.tree, amendment)
    assert delete(tree, node_labelled(tree, STUDY), project.stage.manager).status_code == 200
    merged(api, project, worker, amendment)
    with project.stage.database.transaction() as session:
        parent = session.scalar(select(Node.parent_id).where(Node.id == risk.provision_node_id))
    assert parent == project.tasks[MAKING]
    assert set(tasks_of(project, project.structure_id)) == {MAKING}


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_loader_of_the_witness_updates_a_differential_before_it_merges_it(
    api: ContractClient, project: Costed
) -> None:
    # « load_merge met l'avenant à jour avant de le fusionner quand la marche des événements a
    # écrit la structure principale depuis son ouverture, par la fonction de la mise à jour, sans
    # compte rendu » (conception, « Le chargeur du témoin »): what the main structure received
    # stays, what the differential designates is applied, the revision marked and the reference.
    late = out_of_date(api, project)
    place = Place(project.project_id, project.revision_id, UUID(late.structure_id))
    with logging_context(correlation_id="witness"), project.stage.database.transaction() as held:
        load_merge(held, place, ("Avenant 1", "Extension"), Act(None, utc_now()))
    labels = set(tasks_of(project, project.structure_id))
    assert {MAIN_ADDED, OWN_ADDED, OWN_RENAMED[1]} <= labels
    assert "Montage" not in labels
    marked = revision_of(api, project, project.revision_id)
    assert (marked["status"], marked["version_name"], marked["is_reference"]) == (
        "marked",
        "Avenant 1",
        True,
    )
