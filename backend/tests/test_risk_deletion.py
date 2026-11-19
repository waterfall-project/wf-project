# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""A risk deleted, and what the abandonment of a revision brings back of the risks (US-2590/L1).

``deleteRisk`` deletes a risk no marked revision cites, with its own estimate and its provision
line, and refuses one a marked revision cites or one that occurred, in the order of ``delete``
(H-09; WF-RIS-0020). The abandonment of a revision brings the evaluation of the risks back to the
last marked revision (M-04): a risk it declared is gone, with its own estimate, one it reviewed is
read again as the marked revision froze it, its history without the reviews of the abandoned
revision, and the counter of a risk never goes back (WF-RIS-0030). Every answer is checked against
the contract (``ContractClient``).
"""

from dataclasses import replace
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from nodes_support import faults, mark, refusal
from projects_support import Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from risks_support import (
    STUDY,
    Costed,
    Risks,
    concurrently,
    costed,
    differential,
    lock_held,
    occur,
    waiting_for_a_lock,
)
from sqlalchemy import func, select

from waterfall.core.access_roles.predefined import PROJECT_MANAGER
from waterfall.core.planning.tables import Node
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.risks.tables import Risk, RiskEvaluation, RiskReview

if TYPE_CHECKING:
    from realm import TestRealm
    from sqlalchemy import Engine
    from support import ContractClient

    from waterfall.platform.database import Database

CONDITION = "STATE_FORBIDS_OPERATION"


@pytest.fixture
def stage(api: ContractClient, owner: Engine, database: Database, realm: TestRealm) -> Scene:
    """Give a platform, its sessions, and the project its manager made."""
    return make_scene(api, owner, database, realm)


@pytest.fixture
def project(api: ContractClient, stage: Scene) -> Costed:
    """Give the project costed at 1 000 in its current revision."""
    costs: Costing = costing(stage.database)
    return costed(api, stage, costs)


@pytest.fixture
def risks(api: ContractClient, project: Costed) -> Risks:
    """Give the risks of the project costed."""
    return Risks(api, project)


def refused_by(answer: Any, condition: str) -> None:
    """Assert a refusal by 409, the condition named, and nothing else."""
    assert refusal(answer) == (409, CONDITION, {"missing_condition": condition})


def held(project: Costed, risk: dict[str, Any]) -> dict[str, int]:
    """Count the rows the base holds of a risk, and of what only it names."""
    risk_id = UUID(risk["risk_id"])
    line = risk["provision_node_id"]
    named = risk_id if line is None else UUID(line)
    with project.stage.database.transaction() as session:
        counts = {
            "risk": select(func.count()).where(Risk.id == risk_id),
            "evaluations": select(func.count()).where(RiskEvaluation.risk_id == risk_id),
            "reviews": select(func.count()).where(RiskReview.risk_id == risk_id),
            "structures": select(func.count()).where(CostStructure.risk_id == risk_id),
            "own_nodes": select(func.count()).where(
                Node.structure_id == UUID(risk["structure_id"])
            ),
            "line": select(func.count()).where(Node.id == named),
        }
        return {name: session.scalar(query) or 0 for name, query in counts.items()}


def total(risks: Risks) -> str:
    """Read the total of the estimate of the current revision, the provision lines included."""
    natures = risks.indicators()["by_cost_type"]
    return f"{sum(float(each['amount']['value']) for each in natures):.2f}"


# --- The deletion ---------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_no_marked_revision_cites_is_deleted_with_its_own_estimate_and_its_provision(
    risks: Risks, project: Costed
) -> None:
    # « …un risque qu'aucune révision marquée ne cite est supprimé avec son devis propre et sa
    # ligne de provision. » 200 at 30 % is a line of 60: the total is 1 120 with two risks, then
    # 1 060 without the one deleted, the other kept as it was.
    kept = risks.declared_costed(label="Conservé")
    risk = risks.declared_costed()
    assert total(risks) == "1120.00"
    before = held(project, risk)
    assert before == {
        "risk": 1,
        "evaluations": 1,
        "reviews": 1,
        "structures": 1,
        "own_nodes": 2,
        "line": 1,
    }
    answer = risks.remove(risk)
    assert answer.status_code == 204, answer.text
    assert not answer.content
    assert held(project, risk) == dict.fromkeys(before, 0)
    assert risks.read(risk).status_code == 404
    assert total(risks) == "1060.00"
    listed = risks.api.get(f"{risks.base}/risks", headers=risks.headers).json()
    assert [each["label"] for each in listed["items"]] == ["Conservé"]
    structures = risks.api.get(
        f"{risks.base}/revisions/{project.revision_id}/structures", headers=risks.headers
    ).json()
    assert [each["risk_id"] for each in structures if each["kind"] == "risk"] == [kept["risk_id"]]
    assert risks.risk(kept)["provision_amount"] == "60.00"


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_a_marked_revision_cites_is_not_deleted_it_is_dismissed(
    risks: Risks, project: Costed
) -> None:
    # « La suppression d'un risque cité par une révision marquée est refusée. » The command says so
    # beforehand, the review dismisses it instead (``deleteRisk``).
    risk = risks.declared_costed()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    read = risks.risk(risk)
    commands = {each["command"]: each["missing_conditions"] for each in read["available_commands"]}
    assert commands["delete"] == ["risk_not_cited"]
    refused_by(risks.remove(read), "risk_not_cited")
    assert held(project, risk)["risk"] == 1
    assert risks.risk(risk)["lock_version"] == read["lock_version"]
    dismissed = risks.reviewed(read, state="dismissed")
    assert dismissed["state"] == "dismissed"
    refused_by(risks.remove(dismissed), "risk_not_cited")


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_occurred_is_not_deleted_whether_or_not_a_marked_revision_cites_it(
    risks: Risks, project: Costed
) -> None:
    # « Toute transition depuis l'état survenu est refusée » : 409, risk_not_occurred, which
    # prevails over risk_not_cited when both are missing, as the command lists them.
    uncited = risks.declared_costed(label="Non cité")
    occur(project.stage, uncited["risk_id"], project.revision_id)
    refused_by(risks.remove(risks.risk(uncited)), "risk_not_occurred")
    cited = risks.declared_costed(label="Cité")
    mark(project.stage, {"revision_id": str(project.revision_id)})
    opened = risks.revision()
    occur(project.stage, cited["risk_id"], opened["revision_id"])
    read = risks.risk(cited)
    commands = {each["command"]: each["missing_conditions"] for each in read["available_commands"]}
    assert commands["delete"] == ["risk_not_occurred", "risk_not_cited"]
    refused_by(risks.remove(read), "risk_not_occurred")
    assert held(project, cited)["risk"] == 1


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_deletion_is_refused_at_a_stale_counter_unknown_or_without_a_counter(
    risks: Risks, project: Costed
) -> None:
    risk = risks.declared_costed()
    stale = risks.remove({**risk, "lock_version": 99})
    assert stale.status_code == 412, stale.text
    assert stale.json()["params"] == {"expected_lock_version": risk["lock_version"]}
    assert held(project, risk)["risk"] == 1
    negative = risks.remove(risk, lock_version=-1)
    assert [(each[0], each[1]) for each in faults(negative)] == [
        ("/query/lock_version", "VALUE_OUT_OF_RANGE")
    ]
    unknown = {**risk, "risk_id": str(UUID(int=1))}
    assert risks.remove(unknown).status_code == 404
    assert held(project, risk)["risk"] == 1


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_state_of_the_project_is_judged_before_the_risk_in_the_order_of_the_contract(
    risks: Risks, project: Costed
) -> None:
    # H-09: no_background_task_running comes before the counter (412) and before the risk is
    # judged, occurred here; project_not_terminal before both, the marking still pending.
    risk = risks.declared_costed()
    occur(project.stage, risk["risk_id"], project.revision_id)
    read = risks.risk(risk)
    risks.started_marking()
    stale = {**read, "lock_version": 99}
    refused_by(risks.remove(stale), "no_background_task_running")
    put_in_state(project.stage.owner, str(project.project_id), "abandoned")
    refused_by(risks.remove(stale), "project_not_terminal")
    assert held(project, risk)["risk"] == 1


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_cited_is_refused_for_that_reason_to_who_may_not_create_a_revision(
    risks: Risks, project: Costed, database: Database, realm: TestRealm
) -> None:
    # Without a current revision every risk is cited: risk_not_cited is named, never
    # may_create_revision, which no deletion needs.
    risk = risks.declared_costed()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    entering = person(
        database,
        realm,
        *(each for each in PROJECT_MANAGER if each != "revisions.write"),
        name="Léa",
    )
    contribute(database, project.stage.project["project_id"], entering, "contributor")
    refused_by(risks.remove(risks.risk(risk), entering), "risk_not_cited")


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_deletion_takes_the_own_estimate_then_the_main_structure_before_the_risk(
    risks: Risks, project: Costed
) -> None:
    # The order of every write that touches a risk and its line: the own estimate, which a write of
    # it holds first, then the main structure that bears the line, then the risk. The risk held by
    # another, the deletion waits for it holding both structures already.
    risk = risks.declared_costed()
    stage = project.stage
    with stage.owner.connect() as holder:
        holder.execute(select(Risk.id).where(Risk.id == UUID(risk["risk_id"])).with_for_update())
        asking = concurrently(lambda: risks.remove(risk))
        waiting_for_a_lock(stage)
        assert lock_held(stage, UUID(risk["structure_id"]))
        assert lock_held(stage, project.structure_id)
        holder.rollback()
    assert asking.result(timeout=30).status_code == 204
    assert held(project, risk)["risk"] == 0


# --- The abandonment ------------------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0020-A")
def test_after_the_abandonment_the_risk_created_is_gone_the_one_reviewed_is_as_marked(
    risks: Risks, project: Costed
) -> None:
    # « Après abandon d'une révision en cours où un risque a été créé, un autre réexaminé et un
    # troisième déclaré survenu, le premier n'existe plus, le second présente la probabilité et
    # l'état de la dernière révision marquée, et le troisième est identifié, avec sa provision et
    # sans coût à la survenance. » The occurrence is US-2620's, not served yet: the third is made
    # occurred around the service in the revision abandoned (``occur``), its evaluation as the
    # occurrence will leave it; what the abandonment brings back of it does not depend on the rest.
    reexamined = risks.declared_costed(label="Réexaminé")
    occurring = risks.declared_costed(label="Survenu")
    marked = project.revision_id
    mark(project.stage, {"revision_id": str(marked)})
    frozen = {each["risk_id"]: risks.risk(each, marked) for each in (reexamined, occurring)}
    opened = risks.revision()
    created = risks.declared(label="Créé")
    risks.costed_at(created, opened["revision_id"], "50.00")
    reviewed = risks.reviewed(risks.risk(reexamined), probability="0.8", state="dismissed")
    occur(project.stage, occurring["risk_id"], opened["revision_id"])
    assert risks.risk(occurring)["state"] == "occurred"
    assert held(project, created)["risk"] == 1
    risks.abandon(opened)
    # The first no longer exists, nor its identity, its own estimate, its line or its reviews.
    assert risks.read(created).status_code == 404
    assert set(held(project, created).values()) == {0}
    # The second presents what the last marked revision froze, and its history keeps none of the
    # reviews of the revision abandoned.
    after = risks.risk(reexamined)
    before = frozen[reexamined["risk_id"]]
    for field in ("probability", "state", "provision_amount", "provision_node_id", "structure_id"):
        assert after[field] == before[field]
    assert (after["probability"], after["state"]) == ("0.3", "identified")
    assert [(each["probability"], each["state"]) for each in risks.reviews(after)] == [
        ("0.3", "identified")
    ]
    assert after["lock_version"] > reviewed["lock_version"]
    # The third is identified again, with its provision line, its own estimate and no cost.
    third = risks.risk(occurring)
    assert (third["state"], third["occurrence_cost"]) == ("identified", None)
    assert third["provision_amount"] == "60.00"
    assert third["provision_task"] == {"node_id": str(project.tasks[STUDY]), "label": STUDY}
    for field in ("provision_node_id", "structure_id", "severity"):
        assert third[field] == frozen[occurring["risk_id"]][field]
    assert held(project, third)["line"] == 1
    listed = risks.api.get(f"{risks.base}/risks", headers=risks.headers).json()
    assert sorted(each["label"] for each in listed["items"]) == ["Réexaminé", "Survenu"]


@pytest.mark.requirement("WF-RIS-0030-A")
@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_counter_of_a_risk_never_goes_back_the_abandonment_of_a_revision_included(
    risks: Risks, project: Costed
) -> None:
    # « …ne revient jamais en arrière, abandon et annulation compris » (EP-08, « Tables et
    # migrations », #3949): every step advances it — the opening of a revision, a review, the
    # abandonment of the revision that holds a review and a differential. Undoing is US-2590/L2's.
    risk = risks.declared_costed()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    seen = [risks.risk(risk)["lock_version"]]
    opened = risks.revision()
    seen.append(risks.risk(risk)["lock_version"])
    risks.reviewed(risks.risk(risk), probability="0.6")
    seen.append(risks.risk(risk)["lock_version"])
    differential(replace(project, revision_id=UUID(opened["revision_id"])))
    seen.append(risks.risk(risk)["lock_version"])
    risks.abandon(opened)
    seen.append(risks.risk(risk)["lock_version"])
    steps = ("the opening", "the review", "the differential", "the abandonment")
    # Strictly: the opening, the review and the abandonment advance the counter; the differential
    # may leave it where it stood, never lower.
    for step, before, after in zip(steps, seen[:-1], seen[1:], strict=True):
        if step == "the differential":
            assert after >= before, f"{step} brought the counter back: {before} to {after}"
        else:
            assert after > before, f"{step} did not advance the counter: {before} to {after}"


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_abandonment_against_a_change_of_the_risk_it_created_answers_cleanly(
    risks: Risks, project: Costed
) -> None:
    # The change of identity waits for the abandonment, at the lock of the project, and answers 404.
    mark(project.stage, {"revision_id": str(project.revision_id)})
    opened = risks.revision()
    created = risks.declared(label="Créé")
    risks.costed_at(created, opened["revision_id"], "50.00")
    stage = project.stage
    with stage.owner.connect() as holder:
        holder.execute(
            select(CostStructure.id)
            .where(CostStructure.id == UUID(risks.risk(created)["structure_id"]))
            .with_for_update()
        )
        abandoning = concurrently(lambda: risks.abandon(opened))
        waiting_for_a_lock(stage)
        changing = concurrently(lambda: risks.update(created, label="Changé"))
        waiting_for_a_lock(stage, count=2)
        holder.rollback()
    abandoning.result(timeout=30)
    assert changing.result(timeout=30).status_code == 404
    assert risks.read(created).status_code == 404
