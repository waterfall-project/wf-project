# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""What guards the merge of a differential, and what a merge leaves unwritten (US-2560/L3).

The permission of the merge, held apart from that of the marking (WF-ADM-0100); the designation by
hand refused once a merge has marked a revision (WF-REV-0040); the skeleton of the planning, which
the revision engenders on its main structure alone, and which no structure of a risk's own quote
nor any differential proposes nor receives (WF-PLA-0170); the state a revision is judged on,
read for the commands of its structures. Every answer is checked against the contract
(``ContractClient``).
"""

from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

import pytest
from amendments_support import commands_of, listed, on, opened_amendment
from merges_support import (
    REFUSED,
    client,
    confirmation,
    costed_project,
    merge_path,
    merged,
    merging_worker,
    project_of,
    read_report,
    revision_of,
)
from nodes_support import mark, opened, refusal
from projects_support import PROJECTS, contribute, designate, person
from risks_support import Costed, declared
from sqlalchemy import delete, func, select
from test_skeleton import lotted

from waterfall.core.estimate.tables import EstimateLine
from waterfall.core.planning.tables import Node
from waterfall.core.revisions.states import revision_state
from waterfall.core.risks.tables import RiskEvaluation
from waterfall.platform.errors import NotFoundError

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

MARKING = ("revisions.read", "revision_mark")


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


# --- The permission ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-ADM-0100-A")
def test_a_manager_who_marks_without_the_merge_permission_is_not_offered_the_merge_and_is_refused(
    api: ContractClient, project: Costed, realm: TestRealm, worker: Worker
) -> None:
    # « un rôle disposant du marquage mais non de la fusion refuse de fusionner un différentiel »:
    # a project manager whose role marks the revision (revision_mark) without structure_merge reads
    # the merge unavailable on the revision and is refused by a 403 of mergeCostStructure; the same
    # manager granted structure_merge is offered it and merges.
    stage = project.stage
    amendment = opened_amendment(api, project)
    on(project.tree, amendment).made("Essais")
    marker = person(stage.database, realm, *MARKING, name="Max")
    contribute(stage.database, stage.project["project_id"], marker, "project_manager")
    path = f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}"
    read = api.get(path, headers=marker.headers)
    assert read.status_code == 200, read.text
    commands = commands_of(read.json())
    assert commands["mark"][0] is True
    assert commands.get("merge_structure", (False, []))[0] is False
    sent = confirmation(read_report(api, project, amendment))
    refused = api.post(merge_path(project, amendment), headers=marker.headers, json=sent)
    assert refused.status_code == 403, refused.text
    assert revision_of(api, project, project.revision_id)["status"] == "draft"
    allowed = person(stage.database, realm, *MARKING, "structure_merge", name="Sam")
    contribute(stage.database, stage.project["project_id"], allowed, "project_manager")
    read = api.get(path, headers=allowed.headers)
    assert commands_of(read.json())["merge_structure"] == (True, [])
    answer = api.post(merge_path(project, amendment), headers=allowed.headers, json=sent)
    assert answer.status_code == 202, answer.text
    assert worker.step()


# --- The designation by hand ---------------------------------------------------------------------


@pytest.mark.requirement("WF-REV-0040-A")
def test_after_a_merge_the_designation_by_hand_is_refused_whichever_revision_it_names(
    api: ContractClient, project: Costed, worker: Worker
) -> None:
    # « La désignation manuelle est proposée tant que le projet n'a ni coût réel ni révision marquée
    # depuis la dernière désignation, et refusée au-delà. »: a first revision marked and designated,
    # a merge marks the next one, the reference without a designation; the designation of either
    # is refused by 409 reference_correctable, and the revisions do not offer it.
    mark(project.stage, {"revision_id": str(project.revision_id)})
    designate(api, project.stage, {"revision_id": str(project.revision_id)})
    second = opened(api, project.stage)
    second_id = UUID(second["revision_id"])
    following = replace(project, revision_id=second_id)
    amendment = opened_amendment(api, following)
    merged(api, following, worker, amendment, second_id)
    assert project_of(api, project)["reference_revision_id"] == str(second_id)
    held = project_of(api, project)["lock_version"]
    for named in (project.revision_id, second_id):
        sent = {"revision_id": str(named), "confirmed": True, "lock_version": held}
        answer = api.put(
            f"{PROJECTS}/{project.project_id}/reference-revision",
            headers=project.stage.manager.headers,
            json=sent,
        )
        assert refusal(answer) == (409, REFUSED, {"missing_condition": "reference_correctable"})
        offered = commands_of(revision_of(api, project, named))["designate_reference"]
        assert offered == (False, ["reference_correctable"])


# --- The skeleton --------------------------------------------------------------------------------


def counted(project: Costed, structures: tuple[UUID, ...]) -> dict[UUID, int]:
    """Count the nodes of each of the structures."""
    with project.stage.database.transaction() as session:
        rows = session.execute(
            select(Node.structure_id, func.count())
            .where(Node.structure_id.in_(structures))
            .group_by(Node.structure_id)
        )
        found = dict(rows.all())
    return {each: found.get(each, 0) for each in structures}


@pytest.mark.requirement("WF-PLA-0170-A")
def test_the_skeleton_is_written_in_the_main_structure_alone_never_in_a_quote_or_a_differential(
    api: ContractClient, project: Costed
) -> None:
    # « La génération du squelette n'est pas proposée sur le devis propre d'un risque. »: a revision
    # whose main structure holds no task but bears a risk's own quote and a differential — the
    # main structure emptied around the service —, the skeleton of its work breakdown engendered:
    # every node written is of the main structure; the own quote and the differential keep their
    # nodes, and none of their commands offers it.
    lotted(project.tree, ("Lot A", [("Poste 1", ["Livrable 1"])]))
    amendment = UUID(opened_amendment(api, project))
    own = declared(project).structure_id
    with project.stage.owner.begin() as connection:
        connection.execute(delete(RiskEvaluation))
        in_main = select(Node.id).where(Node.structure_id == project.structure_id)
        connection.execute(delete(EstimateLine).where(EstimateLine.node_id.in_(in_main)))
        connection.execute(delete(Node).where(Node.structure_id == project.structure_id))
    before = counted(project, (amendment, own, project.structure_id))
    assert before[project.structure_id] == 0
    assert before[amendment] > 0
    assert before[own] > 0
    offered = commands_of(revision_of(api, project, project.revision_id))["generate_skeleton"]
    assert offered == (True, [])
    answer = api.post(
        f"{PROJECTS}/{project.project_id}/revisions/{project.revision_id}/skeleton",
        headers=project.stage.manager.headers,
    )
    assert answer.status_code == 201, answer.text
    after = counted(project, (amendment, own, project.structure_id))
    assert after[project.structure_id] > 0
    assert (after[amendment], after[own]) == (before[amendment], before[own])
    structures = listed(api, project)
    assert {each["structure_id"] for each in structures} >= {str(amendment), str(own)}
    for each in structures:
        assert "generate_skeleton" not in commands_of(each)


# --- The state a revision is judged on -----------------------------------------------------------


@pytest.mark.requirement("WF-REV-0050-A")
def test_the_state_of_a_revision_is_judged_on_the_opening_of_its_project(
    api: ContractClient, project: Costed
) -> None:
    # « sur la dernière révision marquée d'un projet sans révision en cours la fusion est offerte »
    # (#790): a revision is the ``source`` of the state when it is the last marked one of a project
    # without a current revision, as a read of a revision judges its commands; not when another
    # revision is current, nor when it is not the last one marked; an unknown revision is a 404.
    stage = project.stage
    mark(stage, {"revision_id": str(project.revision_id)})
    with stage.database.transaction() as session:
        assert revision_state(session, project.project_id, project.revision_id).source is True
        with pytest.raises(NotFoundError):
            revision_state(session, project.project_id, UUID(int=1))
    second = opened(api, stage)
    with stage.database.transaction() as session:
        assert revision_state(session, project.project_id, project.revision_id).source is False
    mark(stage, second, label="v2.0")
    with stage.database.transaction() as session:
        assert revision_state(session, project.project_id, project.revision_id).source is False
        assert revision_state(session, project.project_id, UUID(second["revision_id"])).source
