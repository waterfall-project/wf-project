# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The review of a risk and the history of its reviews, through the service (US-2590/L1).

``reviewRisk`` confirms or changes the probability and the state of a risk in the current revision,
created when the project has none (WF-RIS-0010, WF-RIS-0020): the transitions between identified
and dismissed in both ways, the provision line removed and recreated — the category and the task
the risk designated, or the ones asked for and the first —, the confirmation without change that
produces a dated review, the refusals in the order of ``review`` (H-09). ``listRiskReviews`` gives
the history; the periodic review filters the register by the day of the last review; a probability
that crosses a bound changes the cell of the risk (WF-RIS-0040). Every answer is checked against
the contract (``ContractClient``).
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from estimate_support import Costing, costing
from nodes_support import faults, mark, refusal
from projects_support import Scene, contribute, person, put_in_state
from projects_support import scene as make_scene
from risks_support import (
    MAKING,
    STUDY,
    Costed,
    Risks,
    another_provision,
    concurrently,
    costed,
    deactivate_category,
    lock_held,
    occur,
    waiting_for_a_lock,
)
from sqlalchemy import func, select, update

from waterfall.core.access_roles.predefined import PROJECT_MANAGER
from waterfall.core.projects.interface import current_day
from waterfall.core.revisions.tables import Revision
from waterfall.core.risks.tables import Risk, RiskReview
from waterfall.platform.database import utc_now

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


def today() -> str:
    """Give the day a review made now is dated of."""
    return current_day(utc_now()).isoformat()


def refused_by(answer: Any, condition: str) -> None:
    """Assert a refusal by 409, the condition named, and nothing else."""
    assert refusal(answer) == (409, CONDITION, {"missing_condition": condition})


def estimate_total(risks: Risks) -> Decimal:
    """Read the total of the estimate of the current revision, the provision lines included."""
    natures = risks.indicators()["by_cost_type"]
    return sum((Decimal(each["amount"]["value"]) for each in natures), Decimal(0))


def reviews_held(project: Costed, risk: dict[str, Any]) -> int:
    """Count the reviews the base holds of a risk."""
    with project.stage.database.transaction() as session:
        count = session.scalar(
            select(func.count()).where(RiskReview.risk_id == UUID(risk["risk_id"]))
        )
    return count or 0


# --- The two states, in both ways -----------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_risk_identified_is_dismissed_and_its_provision_leaves_the_estimate(
    risks: Risks, project: Costed
) -> None:
    # « Les trois états sont atteignables, et un risque écarté ne pèse plus sur le devis. » 200 at
    # 30 % is 60: the total is 1 060, then 1 000 once the risk is dismissed, its line gone.
    risk = risks.declared_costed()
    assert estimate_total(risks) == Decimal("1060.00")
    dismissed = risks.reviewed(risk, state="dismissed", probability="0.1")
    assert (dismissed["state"], dismissed["probability"]) == ("dismissed", "0.1")
    assert (dismissed["provision_node_id"], dismissed["provision_task"]) == (None, None)
    assert dismissed["lock_version"] == risk["lock_version"] + 1
    assert dismissed["last_review_on"] == today()
    assert estimate_total(risks) == Decimal("1000.00")
    assert {each["node_id"] for each in project.tree.items()} & {risk["provision_node_id"]} == set()
    commands = {each["command"]: each for each in dismissed["available_commands"]}
    assert commands["update_provision"]["missing_conditions"] == ["risk_identified"]
    assert commands["review"]["is_available"] is True
    # The severity is the own estimate's still, which a dismissal leaves in place.
    assert dismissed["severity"] == risk["severity"]


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_risk_dismissed_is_identified_again_on_its_task_and_category_at_the_new_probability(
    risks: Risks, project: Costed
) -> None:
    # « Un risque écarté qui redevient identifié porte sa provision sur la tâche qu'il désignait. »
    # The line is recreated at the probability sent, 200 at 50 % is 100, under the task designated.
    risk = risks.declared_costed(provision_task_id=str(project.tasks[MAKING]))
    dismissed = risks.reviewed(risk, state="dismissed")
    again = risks.reviewed(dismissed, state="identified", probability="0.5")
    assert (again["state"], again["provision_amount"]) == ("identified", "100.00")
    assert again["provision_task"] == {"node_id": str(project.tasks[MAKING]), "label": MAKING}
    assert again["provision_cost_category_id"] == risk["provision_cost_category_id"]
    assert again["provision_node_id"] not in (None, risk["provision_node_id"])
    line = project.tree.node(again["provision_node_id"])
    assert (line["parent_id"], line["estimate_line"]["reestimated_amount"]) == (
        str(project.tasks[MAKING]),
        "100.00",
    )
    assert estimate_total(risks) == Decimal("1100.00")
    assert again["lock_version"] == dismissed["lock_version"] + 1


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_risk_dismissed_whose_task_was_deleted_is_identified_again_on_the_first_task(
    risks: Risks, project: Costed
) -> None:
    # « …si cette tâche a été supprimée entre-temps, sur la première tâche de premier niveau. »
    risk = risks.declared_costed(provision_task_id=str(project.tasks[MAKING]))
    dismissed = risks.reviewed(risk, state="dismissed")
    gone = risks.delete(project.tree.node(str(project.tasks[MAKING])))
    assert gone.status_code == 200, gone.text
    again = risks.reviewed(dismissed, state="identified")
    assert again["provision_task"] == {"node_id": str(project.tasks[STUDY]), "label": STUDY}


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_risk_dismissed_whose_category_was_deactivated_is_identified_again_on_the_one_chosen(
    risks: Risks, project: Costed
) -> None:
    # « Un risque écarté dont la catégorie a été désactivée redevient identifié avec la catégorie
    # active choisie. » Two others are active: the return asks which, refusing the omission.
    stage = project.stage
    another_provision(stage, "AL1")
    second = another_provision(stage, "AL2")
    risk = risks.declared_costed(provision_cost_category_id=str(project.costs.provision))
    dismissed = risks.reviewed(risk, state="dismissed")
    deactivate_category(stage, project.costs.provision)
    read = risks.risk(dismissed)
    assert read["provision_cost_category_is_active"] is False
    omitted = risks.review(read, state="identified")
    assert [(each[0], each[1]) for each in faults(omitted)] == [
        ("/provision_cost_category_id", "VALUE_REQUIRED")
    ]
    labour = str(project.costs.labour)
    wrong = risks.review(read, state="identified", provision_cost_category_id=labour)
    assert [(each[0], each[1]) for each in faults(wrong)] == [
        ("/provision_cost_category_id", "PROVISION_CATEGORY_REQUIRED")
    ]
    assert reviews_held(project, risk) == 2
    chosen = risks.reviewed(read, state="identified", provision_cost_category_id=str(second))
    assert chosen["provision_cost_category_id"] == str(second)
    assert chosen["provision_cost_category_is_active"] is True
    line = project.tree.node(chosen["provision_node_id"])
    assert line["estimate_line"]["cost_category_id"] == str(second)


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_category_designated_still_active_is_kept_whatever_the_review_sends(
    risks: Risks, project: Costed
) -> None:
    # « Ignored when the designated category is still active and of the provision-for-risks type. »
    other = another_provision(project.stage)
    risk = risks.declared_costed(provision_cost_category_id=str(project.costs.provision))
    dismissed = risks.reviewed(risk, state="dismissed")
    again = risks.reviewed(dismissed, state="identified", provision_cost_category_id=str(other))
    assert again["provision_cost_category_id"] == str(project.costs.provision)


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_return_without_any_active_category_of_provision_is_refused_the_rest_is_not(
    risks: Risks, project: Costed
) -> None:
    # « Sans catégorie active de ce type, son retour à l'état identifié est refusé et nomme la
    # condition manquante. » A confirmation and a dismissal need none.
    risk = risks.declared_costed()
    dismissed = risks.reviewed(risk, state="dismissed")
    kept = risks.reviewed(dismissed, state="dismissed", probability="0.2")
    deactivate_category(project.stage, project.costs.provision)
    refused_by(risks.review(kept, state="identified"), "active_provision_category")
    assert risks.risk(kept)["lock_version"] == kept["lock_version"]
    assert reviews_held(project, risk) == 3
    assert risks.reviewed(kept, probability="0.4")["probability"] == "0.4"


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_return_on_a_main_structure_without_a_task_is_refused_until_one_exists(
    risks: Risks, project: Costed
) -> None:
    # « Sur une révision sans tâche, … le retour d'un risque écarté à l'état identifié [est
    # refusé] ; l'un et l'autre aboutissent dès qu'une tâche existe. » The task designated is gone:
    # the line is under the first task of the first level, the only one left.
    risk = risks.declared_costed()
    dismissed = risks.reviewed(risk, state="dismissed")
    for label in (STUDY, MAKING):
        assert risks.delete(project.tree.node(str(project.tasks[label]))).status_code == 200
    refused_by(risks.review(dismissed, state="identified"), "at_least_one_task")
    made = project.tree.made("Reprise")
    again = risks.reviewed(dismissed, state="identified")
    assert again["provision_task"] == {"node_id": made["node_id"], "label": "Reprise"}


# --- The confirmation, the probability ------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0010-A")
@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_confirmation_without_change_produces_a_dated_review(
    risks: Risks, project: Costed
) -> None:
    # « La confirmation d'un risque sans modification produit un réexamen daté. »
    risk = risks.declared_costed()
    confirmed = risks.reviewed(risk)
    assert (confirmed["probability"], confirmed["state"]) == (risk["probability"], "identified")
    assert confirmed["provision_amount"] == risk["provision_amount"]
    assert confirmed["provision_node_id"] == risk["provision_node_id"]
    assert confirmed["lock_version"] == risk["lock_version"] + 1
    assert confirmed["last_review_on"] == today()
    assert reviews_held(project, risk) == 2
    assert estimate_total(risks) == Decimal("1060.00")
    commands = {each["command"] for each in confirmed["available_commands"]}
    assert {"review", "update_provision", "delete"} <= commands


@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_probability_is_written_by_the_review_and_the_provision_follows_it(
    risks: Risks, project: Costed
) -> None:
    # « …suivent toute modification de la structure propre ou de la probabilité. » 200 at 50 % is
    # 100, in the same write: the line, the total, the provision the risk presents.
    risk = risks.declared_costed()
    reviewed = risks.reviewed(risk, probability="0.5")
    assert (reviewed["probability"], reviewed["provision_amount"]) == ("0.5", "100.00")
    line = project.tree.node(risk["provision_node_id"])
    assert line["estimate_line"]["reestimated_amount"] == "100.00"
    assert estimate_total(risks) == Decimal("1100.00")
    assert risks.risk(risk)["provision_amount"] == "100.00"


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_review_of_a_marked_revision_creates_the_current_one_and_the_marked_one_stays_as_it_was(
    risks: Risks, project: Costed
) -> None:
    # An entry of the current revision, created by copy of the last marked one when none exists.
    risk = risks.declared_costed()
    mark(project.stage, {"revision_id": str(project.revision_id)})
    read = risks.risk(risk)
    risks.reviewed(read, probability="0.6", state="dismissed")
    frozen = risks.risk(risk, project.revision_id)
    assert (frozen["probability"], frozen["state"]) == ("0.3", "identified")
    assert frozen["provision_amount"] == "60.00"
    current = risks.risk(risk)
    assert (current["probability"], current["state"]) == ("0.6", "dismissed")
    assert current["provision_amount"] == "0.00"
    with project.stage.database.transaction() as session:
        drafts = session.scalar(
            select(func.count()).where(
                Revision.project_id == project.project_id, Revision.status == "draft"
            )
        )
    assert drafts == 1


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_review_that_would_create_the_revision_is_refused_to_who_may_not_create_one(
    risks: Risks, project: Costed, database: Database, realm: TestRealm
) -> None:
    stage = project.stage
    risk = risks.declared_costed()
    mark(stage, {"revision_id": str(project.revision_id)})
    entering = person(
        database,
        realm,
        *(each for each in PROJECT_MANAGER if each != "revisions.write"),
        name="Léa",
    )
    contribute(database, stage.project["project_id"], entering, "contributor")
    read = risks.risk(risk)
    refused_by(risks.review(read, entering, state="dismissed"), "may_create_revision")
    with stage.database.transaction() as session:
        drafts = session.scalar(
            select(func.count()).where(
                Revision.project_id == project.project_id, Revision.status == "draft"
            )
        )
    assert drafts == 0
    assert risks.risk(risk)["lock_version"] == read["lock_version"]


# --- The refusals, in the order of the command ----------------------------------------------------


@pytest.mark.requirement("WF-RIS-0020-A")
def test_no_transition_leaves_the_state_occurred_and_the_command_says_so_beforehand(
    risks: Risks, project: Costed
) -> None:
    # « Toute transition depuis l'état survenu est refusée. » The occurrence is US-2620's: the risk
    # is made occurred around the service. The review names risk_not_occurred; the change of the
    # provision names risk_identified, as the contract says it of an occurred risk (``RiskCommand``,
    # ``updateRiskProvision``), where the criterion of the story says risk_not_occurred (#3814).
    risk = risks.declared_costed()
    occur(project.stage, risk["risk_id"], project.revision_id)
    read = risks.risk(risk)
    assert read["state"] == "occurred"
    commands = {each["command"]: each["missing_conditions"] for each in read["available_commands"]}
    assert commands["review"] == ["risk_not_occurred"]
    for state in ("identified", "dismissed"):
        refused_by(risks.review(read, state=state), "risk_not_occurred")
    refused_by(risks.provision(read, provision_task_id=None), "risk_identified")
    assert risks.risk(risk)["lock_version"] == read["lock_version"]
    assert reviews_held(project, risk) == 1


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_state_of_the_project_is_judged_before_the_risk_and_the_risk_before_the_fields(
    risks: Risks, project: Costed
) -> None:
    # H-09: project_not_terminal, no_background_task_running, then the counter (412), then the
    # state of the risk, then the fields of the entry (422), as ``createRisk`` judges.
    risk = risks.declared_costed()
    stale = {**risk, "lock_version": 99}
    refused = risks.review(stale, probability="1.5")
    assert refused.status_code == 412, refused.text
    assert refused.json()["params"] == {"expected_lock_version": risk["lock_version"]}
    unlikely = risks.review(risk, probability="1.5")
    assert [(each[0], each[1], each[2]) for each in faults(unlikely)] == [
        ("/probability", "VALUE_OUT_OF_RANGE", {"maximum": "1"})
    ]
    assert reviews_held(project, risk) == 1
    risks.started_marking()
    refused_by(risks.review(stale, probability="1.5"), "no_background_task_running")
    put_in_state(project.stage.owner, str(project.project_id), "abandoned")
    refused_by(risks.review(stale, probability="1.5"), "project_not_terminal")


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_risk_occurred_is_judged_before_the_fields_and_after_the_counter(
    risks: Risks, project: Costed
) -> None:
    risk = risks.declared_costed()
    occur(project.stage, risk["risk_id"], project.revision_id)
    read = risks.risk(risk)
    refused_by(risks.review(read, state="identified", probability="1.5"), "risk_not_occurred")
    assert risks.review({**read, "lock_version": 99}, state="identified").status_code == 412


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_review_or_a_history_of_an_unknown_risk_is_not_found(risks: Risks) -> None:
    risk = risks.declared_costed()
    unknown = {**risk, "risk_id": str(UUID(int=1))}
    assert risks.review(unknown).status_code == 404
    path = f"{risks.base}/risks/{unknown['risk_id']}/reviews"
    assert risks.api.get(path, headers=risks.headers).status_code == 404


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_probability_is_refused_beyond_the_precision_the_column_keeps(risks: Risks) -> None:
    risk = risks.declared_costed()
    answer = risks.review(risk, probability="0.12345")
    pointers = [(each[0], each[1]) for each in faults(answer)]
    assert pointers == [("/probability", "VALIDATION_FAILED")]
    assert risks.risk(risk)["lock_version"] == risk["lock_version"]


# --- The history of the reviews -------------------------------------------------------------------


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_history_of_a_risk_gives_each_review_the_identification_the_first(
    risks: Risks, project: Costed
) -> None:
    # Each review, its day, the probability, the severity and the state retained, the most recent
    # first; the identification is the oldest, at the severity of an own estimate not yet costed.
    risk = risks.declared("0.3")
    risks.costed_in(risk, "200.00")
    first = risks.reviewed(risks.risk(risk), probability="0.5")
    second = risks.reviewed(first, probability="0.2", state="dismissed")
    history = risks.reviews(second)
    assert [(each["probability"], each["severity"], each["state"]) for each in history] == [
        ("0.2", "200.00", "dismissed"),
        ("0.5", "200.00", "identified"),
        ("0.3", "0.00", "identified"),
    ]
    assert {each["reviewed_on"] for each in history} == {today()}
    assert history[-1]["actor"]["kind"] == "user"
    assert {each["actor"]["user_id"] for each in history} == {str(project.stage.manager.user_id)}


@pytest.mark.requirement("WF-RIS-0020-A")
@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_history_of_a_risk_read_in_a_marked_revision_stops_at_its_marking(
    risks: Risks, project: Costed
) -> None:
    # « Pour une révision marquée, les réexamens faits jusqu'à son marquage » (WF-RIS-0030): the
    # reviews of the revision that follows do not belong to what the marked one froze.
    risk = risks.declared_costed()
    first = risks.reviewed(risk, probability="0.4")
    mark(project.stage, {"revision_id": str(project.revision_id)})
    second = risks.reviewed(risks.risk(risk), probability="0.7")
    assert [each["probability"] for each in risks.reviews(second)] == ["0.7", "0.4", "0.3"]
    assert [each["probability"] for each in risks.reviews(first, project.revision_id)] == [
        "0.4",
        "0.3",
    ]
    detail = risks.risk(risk)
    assert (detail["probability"], detail["last_review_on"]) == ("0.7", today())
    assert risks.risk(risk, project.revision_id)["probability"] == "0.4"
    # A revision that holds no evaluation of the risk presents no history of it.
    unknown = risks.api.get(
        f"{risks.base}/risks/{risk['risk_id']}/reviews?revision_id={UUID(int=1)}",
        headers=risks.headers,
    )
    assert unknown.status_code == 404


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_periodic_review_presents_the_risks_not_reviewed_since_a_day(
    risks: Risks, project: Costed
) -> None:
    # « La revue périodique présente les risques dont la probabilité n'a pas été réexaminée. » Two
    # risks, one last reviewed in 2025; the register filtered on the last review up to a day of
    # 2026 lists it alone, and no more once it has been reviewed today.
    old = risks.declared_costed(label="Ancien")
    risks.declared_costed(label="Récent")
    with project.stage.owner.begin() as connection:
        connection.execute(
            update(RiskReview)
            .where(RiskReview.risk_id == UUID(old["risk_id"]))
            .values(reviewed_on=date(2025, 6, 1))
        )

    def not_reviewed() -> list[str]:
        answer = risks.api.get(
            f"{risks.base}/risks?last_review_on_to=2026-01-01", headers=risks.headers
        )
        assert answer.status_code == 200, answer.text
        return [each["label"] for each in answer.json()["items"]]

    assert not_reviewed() == ["Ancien"]
    risks.reviewed(risks.risk(old), probability="0.35")
    assert not_reviewed() == []


@pytest.mark.requirement("WF-RIS-0040-A")
def test_the_detail_gives_the_two_notes_and_the_history_the_reviews_of_the_risk(
    risks: Risks,
) -> None:
    # « …ainsi que l'accès aux deux notes et à l'historique. » ``getRisk`` the description and the
    # actions of mitigation, ``listRiskReviews`` the history — the identification and each review.
    risk = risks.declared_costed(
        description="La grue est louée.", mitigation_notes="Réserver une seconde grue."
    )
    reviewed = risks.reviewed(risk, probability="0.45")
    detail = risks.risk(reviewed)
    assert (detail["description"], detail["mitigation_notes"]) == (
        "La grue est louée.",
        "Réserver une seconde grue.",
    )
    history = risks.reviews(detail)
    assert [(each["reviewed_on"], each["probability"]) for each in history] == [
        (today(), "0.45"),
        (today(), "0.3"),
    ]


# --- The order of the locks, the counter judged under it ------------------------------------------


@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_review_takes_the_main_structure_before_the_risk(risks: Risks, project: Costed) -> None:
    # The order of every entry of a risk: the main structure, then the risk. The risk held by
    # another, the review waits for it holding the main structure already — were it the other way
    # round it would close an interlock (40P01) with a write of the own estimate.
    risk = risks.declared_costed()
    stage = project.stage
    with concurrently() as start, stage.owner.connect() as holder:
        holder.execute(select(Risk.id).where(Risk.id == UUID(risk["risk_id"])).with_for_update())
        asking = start(lambda: risks.review(risk, probability="0.5"))
        waiting_for_a_lock(stage, holder)
        assert lock_held(stage, project.structure_id)
        holder.rollback()
    assert asking.result(timeout=30).status_code == 201
    assert risks.risk(risk)["provision_amount"] == "100.00"


@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_counter_of_a_review_is_judged_under_the_lock_of_the_risk(
    risks: Risks, project: Costed
) -> None:
    # The risk locked by another that advances its counter while the review waits: the counter it
    # carries is stale when it gets the lock — it is refused (412), nothing written, instead of
    # judged on the counter read before the lock.
    risk = risks.declared_costed()
    stage = project.stage
    with concurrently() as start, stage.owner.connect() as holder:
        holder.execute(select(Risk.id).where(Risk.id == UUID(risk["risk_id"])).with_for_update())
        asking = start(lambda: risks.review(risk, state="dismissed"))
        waiting_for_a_lock(stage, holder)
        holder.execute(
            update(Risk)
            .where(Risk.id == UUID(risk["risk_id"]))
            .values(lock_version=Risk.lock_version + 1)
        )
        holder.commit()
    assert refusal(asking.result(timeout=30)) == (
        412,
        "STALE_LOCK_VERSION",
        {"expected_lock_version": risk["lock_version"] + 1},
    )
    assert reviews_held(project, risk) == 1
