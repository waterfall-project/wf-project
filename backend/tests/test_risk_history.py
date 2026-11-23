# SPDX-FileCopyrightText: 2026 waterfall-project
# SPDX-License-Identifier: AGPL-3.0-only
"""The entries of the risks in the undoable history, through the service (US-2590/L2).

The declaration, the change of the provision, the review and the deletion of a risk are entries of
the history of their writer, which ``undoLastChange`` undoes and ``redoLastUndo`` redoes
(WF-IHM-0110, WF-RIS-0020): the answer names the risk (``risk_ids``, #2538), no node and nothing
written; the change of the identity does not enter it. An undoing brings back the probability, the
state, the line and the reviews of the risk; the declaration undone takes away the risk, its own
estimate and its line (#3982); the deletion undone brings back the risk and its own estimate with
their identifiers, the entries of the own estimate having gone with the deletion (#4154). The rules
of the entry refuse what they no longer admit, in the order of ``CommandCondition`` (#795, #732).
The undoing of a deletion of a task that carried a provision line advances the counter of its risk
(#4010); the undoing of a paste of the execution of a task asks for ``remaining.write`` (#2905).
Every answer is checked against the contract (``ContractClient``).
"""

from datetime import date
from typing import TYPE_CHECKING, Any
from uuid import UUID

import pytest
from amendments_support import listed
from estimate_support import Costing, costing
from history_support import delete
from nodes_support import SESSION, entries, refusal, signed_in
from project_rows import risk_row
from projects_support import Scene
from projects_support import scene as make_scene
from risks_support import (
    MAKING,
    STUDY,
    Costed,
    Risks,
    another_provision,
    costed,
    deactivate_category,
    material,
)
from sqlalchemy import delete as delete_rows
from sqlalchemy import insert, select, update

from waterfall.core.access_roles.tables import AccessRolePermission, Permission, UserAccessRole
from waterfall.core.history.interface import RecordedChange, UndoStack, recording
from waterfall.core.planning import writing
from waterfall.core.planning.interface import snapshot, undo_last_change
from waterfall.core.planning.tables import Task
from waterfall.core.revisions.tables import CostStructure
from waterfall.core.risks.tables import Risk
from waterfall.platform.audit import Act
from waterfall.platform.database import utc_now
from waterfall.platform.errors import ForbiddenError

if TYPE_CHECKING:
    from projects_support import Person
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


@pytest.fixture
def who(stage: Scene, realm: TestRealm) -> Person:
    """Give a contributor of the project whose token carries a session of sign-in."""
    return signed_in(stage, realm)


def holding(stage: Scene, realm: TestRealm, *permissions: str) -> Person:
    """Give a contributor whose custom role holds these permissions, and a session of sign-in."""
    return signed_in(stage, realm, permissions)


def deprived(stage: Scene, who: Person, permission: str) -> None:
    """Take a permission from the roles of a contributor, as a manager of the roles does."""
    with stage.database.transaction() as session:
        roles = select(UserAccessRole.access_role_id).where(
            UserAccessRole.user_account_id == who.user_id
        )
        code = select(Permission.id).where(Permission.code == permission)
        session.execute(
            delete_rows(AccessRolePermission).where(
                AccessRolePermission.access_role_id.in_(roles),
                AccessRolePermission.permission_id.in_(code),
            )
        )


def turned(risks: Risks, who: Person, way: str) -> Any:
    """Undo, or redo, the last change of a contributor in the current revision; give the answer."""
    path = f"{risks.base}/revisions/{risks.project.revision_id}/{way}"
    return risks.api.post(path, headers=who.headers)


def undone(risks: Risks, who: Person, way: str = "undo") -> dict[str, Any]:
    """Undo, or redo, a change that must be; give what is answered."""
    answer = turned(risks, who, way)
    assert answer.status_code == 200, answer.text
    return answer.json()


def declared_by(risks: Risks, who: Person, **body: Any) -> dict[str, Any]:
    """Declare a risk at 30 % as a contributor; give it."""
    sent = {"label": "Grue indisponible", "probability": "0.3", **body}
    answer = risks.api.post(f"{risks.base}/risks", headers=who.headers, json=sent)
    assert answer.status_code == 201, answer.text
    return answer.json()


def entered(answer: Any) -> dict[str, Any]:
    """Give the risk a write of a risk answered, which must have succeeded."""
    assert answer.status_code in {200, 201}, answer.text
    return answer.json()


def own_path(risks: Risks, risk: dict[str, Any]) -> str:
    """Give the path of the nodes of the own estimate of a risk in the current revision."""
    return risks.own(risk, risks.project.revision_id)


def made_by(risks: Risks, who: Person, path: str, body: dict[str, Any]) -> dict[str, Any]:
    """Create a node as a contributor; give the node created."""
    answer = risks.api.post(path, headers=who.headers, json=body)
    assert answer.status_code == 201, answer.text
    return answer.json()["nodes"][0]


def costed_by(risks: Risks, who: Person, risk: dict[str, Any], amount: str) -> list[str]:
    """Write a task bearing a line at an amount in the own estimate of a risk; give both nodes."""
    path = own_path(risks, risk)
    task = made_by(risks, who, path, {"kind": "task", "parent_id": None, "task": {"label": "Grue"}})
    line = material(risks.project.costs, "Location", amount)
    sent = {"kind": "estimate_line", "parent_id": task["node_id"], "estimate_line": line}
    return [task["node_id"], made_by(risks, who, path, sent)["node_id"]]


def own_nodes(risks: Risks, structure_id: str) -> list[tuple[str, str]]:
    """Read the nodes of an own estimate, each with its kind, in the order of its plan."""
    base = f"{risks.base}/revisions/{risks.project.revision_id}/structures/{structure_id}/nodes"
    answer = risks.api.get(base, headers=risks.headers)
    assert answer.status_code == 200, answer.text
    return [(each["node_id"], each["kind"]) for each in answer.json()["items"]]


def structure_held(stage: Scene, structure_id: str) -> bool:
    """Tell whether the base holds a structure."""
    with stage.database.transaction() as session:
        found = session.scalar(
            select(CostStructure.id).where(CostStructure.id == UUID(structure_id))
        )
    return found is not None


def risk_undone(answer: dict[str, Any], kind: str, risk: dict[str, Any]) -> None:
    """Assert an undoing or a redoing of an entry of a risk: the risk named, no node, no write."""
    assert answer["undone"] == {"kind": kind, "node_ids": [], "risk_ids": [risk["risk_id"]]}
    assert answer["written"] is None


def figures(read: dict[str, Any]) -> tuple[Any, ...]:
    """Give what an entry of a risk changes of it: its probability, its state and its provision."""
    task = read["provision_task"]
    return (
        read["probability"],
        read["state"],
        read["provision_node_id"],
        read["provision_amount"],
        None if task is None else task["node_id"],
        read["provision_cost_category_id"],
        read["provision_subproject_id"],
    )


# --- The review undone and redone ----------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_review_undone_gives_the_risk_back_its_probability_state_and_line_and_redone_again(
    risks: Risks, who: Person
) -> None:
    # « Le réexamen d'un risque puis son annulation lui rendent sa probabilité et son état
    # précédents. » 200 at 30 % is 60, at 50 % 100: the undoing gives back 30 %, the line of 60 and
    # the reviews before; the redoing writes 50 % and the review again.
    risk = risks.declared_costed()
    before = risks.risk(risk)
    reviews = risks.reviews(before)
    reviewed = entered(risks.review(before, who, probability="0.5"))
    assert (reviewed["probability"], reviewed["provision_amount"]) == ("0.5", "100.00")
    answer = undone(risks, who)
    risk_undone(answer, "risk_review", risk)
    assert answer["remaining_depth"] == 0
    back = risks.risk(risk)
    assert figures(back) == figures(before)
    assert risks.reviews(back) == reviews
    assert back["lock_version"] > reviewed["lock_version"]
    again = undone(risks, who, "redo")
    risk_undone(again, "risk_review", risk)
    redone = risks.risk(risk)
    assert figures(redone) == figures(reviewed)
    assert len(risks.reviews(redone)) == len(reviews) + 1
    assert redone["lock_version"] > back["lock_version"]


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_dismissal_undone_brings_the_line_back_under_its_identifier_and_redone_takes_it(
    risks: Risks, project: Costed, who: Person
) -> None:
    # The dismissal removed the line: its undoing creates it again, the same node under the same
    # task, at 60; its redoing removes it again. The estimate follows: 1 060, then 1 000.
    risk = risks.declared_costed()
    before = risks.risk(risk)
    dismissed = entered(risks.review(before, who, state="dismissed"))
    assert dismissed["provision_node_id"] is None
    risk_undone(undone(risks, who), "risk_review", risk)
    back = risks.risk(risk)
    assert figures(back) == figures(before)
    line = project.tree.node(before["provision_node_id"])
    assert (line["parent_id"], line["estimate_line"]["reestimated_amount"]) == (
        str(project.tasks[STUDY]),
        "60.00",
    )
    undone(risks, who, "redo")
    assert risks.risk(risk)["state"] == "dismissed"
    gone = {each["node_id"] for each in project.tree.items()}
    assert before["provision_node_id"] not in gone


# --- The declaration and the deletion ------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_declaration_undone_takes_the_risk_its_own_estimate_and_line_and_redone_brings_them(
    risks: Risks, project: Costed, stage: Scene, who: Person
) -> None:
    # #3982: the declaration enters the history; its undoing deletes the risk, its evaluation, its
    # own estimate and its provision line; its redoing creates them again under their identifiers.
    risk = declared_by(risks, who)
    answer = undone(risks, who)
    risk_undone(answer, "risk_create", risk)
    assert risks.read(risk).status_code == 404
    assert not structure_held(stage, risk["structure_id"])
    assert risk["provision_node_id"] not in {each["node_id"] for each in project.tree.items()}
    risk_undone(undone(risks, who, "redo"), "risk_create", risk)
    again = risks.risk(risk)
    assert figures(again) == figures(risk)
    assert again["structure_id"] == risk["structure_id"]
    assert again["label"] == risk["label"]


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_declaration_is_undone_after_the_entries_of_its_own_estimate_undone_before_it(
    risks: Risks, stage: Scene, who: Person
) -> None:
    # The entries of the own estimate advance the counter of the risk, and so do their undoings: the
    # history carries those counters to the declaration under them, which its own stack took back.
    risk = declared_by(risks, who)
    costed_by(risks, who, risk, "200.00")
    assert entered(risks.read(risk))["provision_amount"] == "60.00"
    for _ in range(2):
        assert undone(risks, who)["undone"]["kind"] == "node_create"
    risk_undone(undone(risks, who), "risk_create", risk)
    assert not structure_held(stage, risk["structure_id"])


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0020-A")
def test_a_deletion_undone_brings_back_the_risk_and_its_own_estimate_and_redone_takes_them_again(
    risks: Risks, project: Costed, stage: Scene, who: Person
) -> None:
    # The deletion undone creates the risk again, its own estimate with its nodes and its line under
    # their identifiers, at 60; the entries of the own estimate went with the deletion (#4154), so
    # the undoing that follows is not theirs. Redone, the deletion takes them all again.
    risk = declared_by(risks, who)
    costed_by(risks, who, risk, "200.00")
    held = risks.risk(risk)
    nodes = [each for each, _ in own_nodes(risks, held["structure_id"])]
    removed = risks.remove(held, who)
    assert removed.status_code == 204, removed.text
    risk_undone(undone(risks, who), "risk_delete", risk)
    back = risks.risk(risk)
    assert figures(back) == figures(held)
    assert back["structure_id"] == held["structure_id"]
    assert [each for each, _ in own_nodes(risks, held["structure_id"])] == nodes
    assert len(risks.reviews(back)) == len(risks.reviews(held))
    line = project.tree.node(held["provision_node_id"])
    assert line["estimate_line"]["reestimated_amount"] == "60.00"
    risk_undone(undone(risks, who, "redo"), "risk_delete", risk)
    assert risks.read(risk).status_code == 404
    assert not structure_held(stage, held["structure_id"])


def up_to_date(risks: Risks, structure_id: str) -> object:
    """Read whether the own estimate of a structure is up to date, as the structure list says."""
    held = listed(risks.api, risks.project)
    return next(each for each in held if each["structure_id"] == structure_id)["is_up_to_date"]


@pytest.mark.requirement("WF-RIS-0020-A")
def test_an_own_estimate_created_again_is_up_to_date_only_if_the_main_structure_kept_its_counter(
    risks: Risks, project: Costed, who: Person
) -> None:
    # The deletion of the risk deletes its provision line, which advances the counter of the main
    # structure by one exactly: the undoing, with no write between, gives the own estimate back up
    # to date (EP-30). A write of the main structure between the two leaves it out of date.
    risk = declared_by(risks, who)
    removed = risks.remove(risks.risk(risk), who)
    assert removed.status_code == 204, removed.text
    risk_undone(undone(risks, who), "risk_delete", risk)
    assert up_to_date(risks, risks.risk(risk)["structure_id"]) is True
    second = declared_by(risks, who, label="Pluie")
    removed = risks.remove(risks.risk(second), who)
    assert removed.status_code == 204, removed.text
    project.tree.made("Recette")
    risk_undone(undone(risks, who), "risk_delete", second)
    assert up_to_date(risks, risks.risk(second)["structure_id"]) is False


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0020-A")
def test_the_deletion_of_a_risk_takes_from_the_stacks_the_entries_that_name_its_own_estimate(
    risks: Risks, stage: Scene, who: Person
) -> None:
    # The task and the line entered in the own estimate are two entries of the stack of the writer;
    # ``deleteRisk`` forgets them, as the abandonment of a differential does (#4154), so that no
    # undoing aims at nodes of a structure that is gone. What stays is the declaration of the risk
    # and the deletion itself.
    risk = declared_by(risks, who)
    nodes = {UUID(each) for each in costed_by(risks, who, risk, "200.00")}
    before = entries(stage)
    assert [each.kind for each in before if nodes & set(each.node_ids)] == [
        "node_create",
        "node_create",
    ]
    removed = risks.remove(risks.risk(risk), who)
    assert removed.status_code == 204, removed.text
    left = entries(stage)
    assert not [each for each in left if nodes & set(each.node_ids)]
    assert [each.kind for each in left] == ["risk_create", "risk_delete"]


# --- The provision -------------------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_a_change_of_the_provision_undone_gives_back_its_task_and_subproject_and_redone_again(
    risks: Risks, project: Costed, who: Person
) -> None:
    risk = risks.declared_costed()
    before = risks.risk(risk)
    sub = risks.subproject("LOT-A")
    sent = {"provision_task_id": str(project.tasks[MAKING]), "provision_subproject_id": sub}
    changed = entered(risks.provision(before, who, **sent))
    risk_undone(undone(risks, who), "risk_update", risk)
    back = risks.risk(risk)
    assert figures(back) == figures(before)
    assert project.tree.node(before["provision_node_id"])["parent_id"] == str(project.tasks[STUDY])
    undone(risks, who, "redo")
    assert figures(risks.risk(risk)) == figures(changed)


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_change_of_the_identity_does_not_enter_the_history(risks: Risks, who: Person) -> None:
    # « La modification de l'identité n'y entre pas » (H-02, #1782): nothing to undo after it.
    risk = risks.declared_costed()
    assert risks.update(risks.risk(risk), who, label="Grue en panne").status_code == 200
    assert refusal(turned(risks, who, "undo")) == (
        409,
        CONDITION,
        {"missing_condition": "undo_history_not_empty"},
    )


# --- The rules of the entry ----------------------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_an_undoing_that_would_recreate_a_line_on_a_structure_without_task_is_refused(
    risks: Risks, project: Costed, who: Person
) -> None:
    # The dismissal undone would create the line again; the main structure has no task left since:
    # 409 ``at_least_one_task``, nothing undone.
    risk = risks.declared_costed()
    entered(risks.review(risks.risk(risk), who, state="dismissed"))
    for label in (MAKING, STUDY):
        gone = risks.delete(project.tree.node(str(project.tasks[label])))
        assert gone.status_code == 200, gone.text
    assert refusal(turned(risks, who, "undo")) == (
        409,
        CONDITION,
        {"missing_condition": "at_least_one_task"},
    )
    assert risks.risk(risk)["state"] == "dismissed"


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_an_undoing_that_would_give_back_a_subproject_deleted_since_is_refused(
    risks: Risks, who: Person
) -> None:
    # #732: the provision moved from one subproject to another; the first deleted since, the undoing
    # is refused by 409 ``restored_subproject_exists`` and leaves the second.
    first, second = risks.subproject("LOT-A"), risks.subproject("LOT-B")
    risk = risks.declared_costed(provision_subproject_id=first)
    entered(risks.provision(risks.risk(risk), who, provision_subproject_id=second))
    path = f"{risks.base}/subprojects/{first}?lock_version=0"
    assert risks.api.delete(path, headers=risks.headers).status_code == 204
    assert refusal(turned(risks, who, "undo")) == (
        409,
        CONDITION,
        {"missing_condition": "restored_subproject_exists"},
    )
    assert risks.risk(risk)["provision_subproject_id"] == second


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_an_undoing_that_would_give_back_a_category_deactivated_since_is_refused(
    risks: Risks, project: Costed, who: Person
) -> None:
    # The category of the provision changed, the first one deactivated since: 409
    # ``active_provision_category``; the risk keeps the second.
    other = another_provision(project.stage)
    risk = risks.declared_costed(provision_cost_category_id=str(project.costs.provision))
    entered(risks.provision(risks.risk(risk), who, provision_cost_category_id=str(other)))
    deactivate_category(project.stage, project.costs.provision)
    assert refusal(turned(risks, who, "undo")) == (
        409,
        CONDITION,
        {"missing_condition": "active_provision_category"},
    )
    assert risks.risk(risk)["provision_cost_category_id"] == str(other)


@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_entry_another_contributor_took_up_since_is_refused_naming_the_risk(
    risks: Risks, who: Person
) -> None:
    # « L'annulation d'une modification qu'un autre contributeur a depuis reprise est refusée en
    # nommant l'objet en conflit » : the risk reviewed again by its manager since.
    risk = risks.declared_costed()
    reviewed = entered(risks.review(risks.risk(risk), who, probability="0.5"))
    risks.reviewed(reviewed, probability="0.6")
    assert refusal(turned(risks, who, "undo")) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": risk["risk_id"], "conflicting_object_label": risk["label"]},
    )
    assert risks.risk(risk)["probability"] == "0.6"


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.requirement("WF-IHM-0110-A")
def test_an_entry_of_a_risk_is_undone_under_the_permission_of_the_risks(
    risks: Risks, stage: Scene, who: Person
) -> None:
    # The entry of a risk asked for ``risks.write``: an undoing without it is refused by 403,
    # naming it, and nothing is undone.
    risk = risks.declared_costed()
    entered(risks.review(risks.risk(risk), who, probability="0.5"))
    act = Act(who.user_id, utc_now())
    revision = risks.project.revision_id
    with stage.database.transaction() as session, pytest.raises(ForbiddenError) as refused:
        undo_last_change(
            session,
            risks.project.project_id,
            revision,
            writing.Writer(act, "office"),
            ("planning.write", "estimate.write", "remaining.write"),
        )
    assert (refused.value.code, dict(refused.value.params)) == (
        "PERMISSION_MISSING",
        {"missing_permission": "risks.write"},
    )
    assert risks.risk(risk)["probability"] == "0.5"


# --- What the grids undo of a provision ----------------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_deletion_of_the_task_of_a_provision_undone_brings_the_line_back_and_tells_its_risk(
    risks: Risks, project: Costed, who: Person
) -> None:
    # #4010: the deletion of ``Étude`` carried the line to ``Réalisation`` and advanced the counter
    # of the risk; its undoing brings the line back under ``Étude`` and advances it again, as its
    # redoing does.
    risk = risks.declared_costed()
    held = risks.risk(risk)
    task = project.tree.node(str(project.tasks[STUDY]))
    assert delete(project.tree, task, who).status_code == 200
    carried = risks.risk(risk)
    assert carried["provision_task"]["node_id"] == str(project.tasks[MAKING])
    assert carried["lock_version"] > held["lock_version"]
    assert undone(risks, who)["undone"]["kind"] == "node_delete"
    back = risks.risk(risk)
    assert back["provision_task"]["node_id"] == str(project.tasks[STUDY])
    assert back["lock_version"] > carried["lock_version"]
    undone(risks, who, "redo")
    again = risks.risk(risk)
    assert again["provision_task"]["node_id"] == str(project.tasks[MAKING])
    assert again["lock_version"] > back["lock_version"]


# --- The permission of the undoing of a paste (#2905) ---------------------------------------------


def pasted(project: Costed, who: Person, task_id: UUID, **columns: object) -> None:
    """Keep in the history of a contributor the paste that writes these columns of a task.

    The paste still refuses the columns of the execution, cell by cell (#2805): the entry is kept
    around the service as the paste would keep it, its write made by the owner of the tables.
    """
    project_id, revision_id = project.project_id, project.revision_id
    change = RecordedChange(
        project_id, UndoStack(revision_id, who.user_id, SESSION), "paste", (task_id,), utc_now()
    )
    with project.stage.database.transaction() as session, recording(session, change) as frame:
        frame.keep_before(snapshot(session, project_id, (task_id,)))
        session.execute(update(Task).where(Task.node_id == task_id).values(**columns))
        frame.keep_after(snapshot(session, project_id, (task_id,)))


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_paste_of_the_execution_of_a_task_asks_for_the_remaining_to_commit(
    project: Costed, who: Person
) -> None:
    # The paste writes the days a task started and completed on under ``remaining.write`` (#2805):
    # its undoing asks for it, and not for the planning (#2905); a paste of the label besides asks
    # for both, the planning's named first. Refused by 403, nothing is undone.
    task_id = project.tasks[STUDY]
    started = {"progress": "started", "started_on": date(2026, 11, 3)}

    def attempt(*permissions: str) -> Any:
        act = Act(who.user_id, utc_now())
        with project.stage.database.transaction() as session:
            return undo_last_change(
                session,
                project.project_id,
                project.revision_id,
                writing.Writer(act, SESSION),
                permissions,
            )

    def refused(*permissions: str) -> str:
        with pytest.raises(ForbiddenError) as raised:
            attempt(*permissions)
        assert raised.value.code == "PERMISSION_MISSING"
        return str(raised.value.params["missing_permission"])

    pasted(project, who, task_id, **started)
    assert refused("planning.write", "estimate.write") == "remaining.write"
    assert attempt("remaining.write").kind == "paste"
    assert project.tree.node(str(task_id))["task"]["progress"] == "not_started"
    pasted(project, who, task_id, label="Étude détaillée", **started)
    assert refused("estimate.write") == "planning.write"
    assert refused("planning.write") == "remaining.write"
    assert attempt("planning.write", "remaining.write").kind == "paste"
    assert project.tree.node(str(task_id))["task"]["label"] == STUDY


# --- The undoing through the route, under the permissions of the risks (#2905) --------------------


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_role_that_holds_only_the_risks_write_undoes_and_redoes_a_review_by_the_route(
    risks: Risks, stage: Scene, realm: TestRealm
) -> None:
    # A custom role that reads the project and writes its risks, nothing of the three grids: the
    # review it wrote is undone (200) and redone by the routes, which ask no more for the planning.
    owner = holding(stage, realm, "planning.read", "risks.read", "risks.write")
    risk = risks.declared_costed()
    entered(risks.review(risks.risk(risk), owner, probability="0.5"))
    risk_undone(undone(risks, owner), "risk_review", risk)
    assert risks.risk(risk)["probability"] == "0.3"
    risk_undone(undone(risks, owner, "redo"), "risk_review", risk)
    assert risks.risk(risk)["probability"] == "0.5"


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_review_by_the_route_is_refused_naming_the_risks_write_once_taken_away(
    risks: Risks, stage: Scene, realm: TestRealm
) -> None:
    # The same role that keeps a grid but is no longer granted ``risks.write``: the dependency of
    # the route passes, the service judges the entry and names ``risks.write`` (403): no undoing.
    owner = holding(stage, realm, "planning.read", "risks.read", "risks.write", "remaining.write")
    risk = risks.declared_costed()
    entered(risks.review(risks.risk(risk), owner, probability="0.5"))
    deprived(stage, owner, "risks.write")
    assert refusal(turned(risks, owner, "undo")) == (
        403,
        "PERMISSION_MISSING",
        {"missing_permission": "risks.write"},
    )
    assert risks.risk(risk)["probability"] == "0.5"


@pytest.mark.requirement("WF-ADM-0100-A")
@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_undoing_of_a_paste_of_the_execution_passes_the_route_under_the_remaining_write_alone(
    project: Costed, risks: Risks, stage: Scene, realm: TestRealm
) -> None:
    # #2905 through the route: a role that reads the project and commits the remaining, no grid
    # else, undoes the paste of the execution of a task (200); the entry is kept around the service.
    owner = holding(stage, realm, "planning.read", "remaining.write")
    task_id = project.tasks[STUDY]
    pasted(project, owner, task_id, progress="started", started_on=date(2026, 11, 3))
    assert undone(risks, owner)["undone"]["kind"] == "paste"
    assert project.tree.node(str(task_id))["task"]["progress"] == "not_started"


# --- What an entry is judged on: what it restores ------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_change_of_the_identity_by_the_author_is_no_conflict_of_the_undoing_of_a_review(
    risks: Risks, who: Person
) -> None:
    # Only « la modification d'un autre contributeur » is a conflict: the author reviews, corrects
    # the label, and undoes the review (200); the new label stays, the stack below is not blocked.
    risk = risks.declared_costed()
    reviewed = entered(risks.review(risks.risk(risk), who, probability="0.5"))
    assert risks.update(reviewed, who, label="Grue en panne").status_code == 200
    risk_undone(undone(risks, who), "risk_review", risk)
    back = risks.risk(risk)
    assert (back["label"], back["probability"]) == ("Grue en panne", "0.3")
    risk_undone(undone(risks, who, "redo"), "risk_review", risk)
    assert risks.risk(risk)["label"] == "Grue en panne"


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_real_write_of_another_contributor_after_a_change_of_the_identity_is_still_a_conflict(
    risks: Risks, who: Person
) -> None:
    # The identity corrected, then the manager reviews the risk again: that is the modification of
    # another contributor, 409 naming the risk by the label it has now.
    risk = risks.declared_costed()
    reviewed = entered(risks.review(risks.risk(risk), who, probability="0.5"))
    assert risks.update(reviewed, who, label="Grue en panne").status_code == 200
    risks.reviewed(risks.risk(risk), probability="0.6")
    assert refusal(turned(risks, who, "undo")) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": risk["risk_id"], "conflicting_object_label": "Grue en panne"},
    )


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_change_of_the_identity_does_not_erase_a_conflict_already_born(
    risks: Risks, who: Person
) -> None:
    # A reviews, another reviews (the undoing of A is a conflict), then the label is corrected: the
    # counter of the identity is carried only to the entries that held the one before it, so the
    # conflict stays: 409 naming the risk, the review of the other not overwritten.
    risk = risks.declared_costed()
    entered(risks.review(risks.risk(risk), who, probability="0.5"))
    risks.reviewed(risks.risk(risk), probability="0.6")
    assert risks.update(risks.risk(risk), who, label="Grue en panne").status_code == 200
    assert refusal(turned(risks, who, "undo")) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": risk["risk_id"], "conflicting_object_label": "Grue en panne"},
    )
    assert risks.risk(risk)["probability"] == "0.6"


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_change_of_the_identity_after_an_undoing_is_no_conflict_of_the_redoing(
    risks: Risks, who: Person
) -> None:
    # #4219: the same carrying on the entries undone (their ``before``, the path of the redoing): a
    # review undone, the label corrected, then redone (200): the new label stays.
    risk = risks.declared_costed()
    entered(risks.review(risks.risk(risk), who, probability="0.5"))
    risk_undone(undone(risks, who), "risk_review", risk)
    assert risks.update(risks.risk(risk), who, label="Grue en panne").status_code == 200
    risk_undone(undone(risks, who, "redo"), "risk_review", risk)
    back = risks.risk(risk)
    assert (back["label"], back["probability"]) == ("Grue en panne", "0.5")


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_change_of_the_identity_does_not_erase_a_conflict_born_after_an_undoing(
    risks: Risks, who: Person
) -> None:
    # #4219: a review undone, another contributor reviews the risk, then the label is corrected: the
    # carrying leaves the entry undone that did not hold the counter before it, so the redoing stays
    # a conflict (409 naming the risk), the review of the other not overwritten.
    risk = risks.declared_costed()
    entered(risks.review(risks.risk(risk), who, probability="0.5"))
    risk_undone(undone(risks, who), "risk_review", risk)
    risks.reviewed(risks.risk(risk), probability="0.6")
    assert risks.update(risks.risk(risk), who, label="Grue en panne").status_code == 200
    assert refusal(turned(risks, who, "redo")) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": risk["risk_id"], "conflicting_object_label": "Grue en panne"},
    )
    assert risks.risk(risk)["probability"] == "0.6"


# --- What enters the history, and what does not --------------------------------------------------


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_change_of_the_provision_that_changes_nothing_keeps_no_entry(
    risks: Risks, who: Person
) -> None:
    # ``updateRiskProvision`` with what the risk already has writes nothing: no entry is kept, and
    # the review before it is the last change to undo.
    risk = risks.declared_costed()
    reviewed = entered(risks.review(risks.risk(risk), who, probability="0.5"))
    same = {"provision_cost_category_id": reviewed["provision_cost_category_id"]}
    assert risks.provision(reviewed, who, **same).status_code == 200
    risk_undone(undone(risks, who), "risk_review", risk)
    assert risks.risk(risk)["probability"] == "0.3"


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_write_of_a_risk_by_a_token_without_session_keeps_no_entry(risks: Risks) -> None:
    # #2472: the token of the manager carries no ``sid``; its review is made, no stack keeps it.
    risk = risks.declared_costed()
    risks.reviewed(risks.risk(risk), probability="0.5")
    assert risks.risk(risk)["probability"] == "0.5"
    answer = risks.api.post(
        f"{risks.base}/revisions/{risks.project.revision_id}/undo", headers=risks.headers
    )
    assert refusal(answer)[:2] == (403, "SESSION_ID_MISSING")


@pytest.mark.requirement("WF-IHM-0110-A")
def test_the_redoing_of_a_declaration_is_refused_when_the_risk_was_taken_up_since(
    risks: Risks, project: Costed, stage: Scene, who: Person
) -> None:
    # The declaration undone, the risk is absent; found again under its identifier since — which
    # the stacks would not let pass here: written around the service —, its redoing would create it
    # twice: 409 ``UNDO_CONFLICT`` naming it.
    risk = declared_by(risks, who)
    risk_undone(undone(risks, who), "risk_create", risk)
    with stage.database.transaction() as session:
        session.execute(
            insert(Risk).values(
                **risk_row(
                    project.project_id, id=UUID(risk["risk_id"]), label="Reprise", lock_version=7
                )
            )
        )
    assert refusal(turned(risks, who, "redo")) == (
        409,
        "UNDO_CONFLICT",
        {"conflicting_object_id": risk["risk_id"], "conflicting_object_label": "Reprise"},
    )


# --- The restoring of a deleted task that carried a provision line (#4010) ------------------------


def study_deleted(
    risks: Risks, project: Costed, who: Person
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Delete the task of the provision line of a risk, which the line leaves for the next task."""
    risk = risks.declared_costed()
    task = project.tree.node(str(project.tasks[STUDY]))
    assert delete(project.tree, task, who).status_code == 200
    return risk, risks.risk(risk)


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_undoing_of_a_deletion_that_carried_a_provision_line_does_not_break_a_foreign_key(
    risks: Risks, project: Costed, who: Person
) -> None:
    # Before US-2590/L2 the line, carried under ``Réalisation``, held the row of the task to bring
    # back: the undoing failed on a foreign key (500). It is 200 and the line is under ``Étude``.
    risk, carried = study_deleted(risks, project, who)
    assert carried["provision_task"]["node_id"] == str(project.tasks[MAKING])
    assert undone(risks, who)["undone"]["kind"] == "node_delete"
    assert risks.risk(risk)["provision_task"]["node_id"] == str(project.tasks[STUDY])


@pytest.mark.requirement("WF-IHM-0110-A")
@pytest.mark.requirement("WF-RIS-0010-A")
def test_the_redoing_of_a_deletion_that_carried_a_provision_line_is_no_conflict_on_the_line(
    risks: Risks, project: Costed, who: Person
) -> None:
    # Before US-2590/L2 the redoing was refused (409): the line, carried back under ``Étude`` by the
    # undoing, was judged at a counter the undoing had not carried to the entry.
    risk, _ = study_deleted(risks, project, who)
    undone(risks, who)
    assert undone(risks, who, "redo")["undone"]["kind"] == "node_delete"
    assert risks.risk(risk)["provision_task"]["node_id"] == str(project.tasks[MAKING])


@pytest.mark.requirement("WF-IHM-0110-A")
def test_a_task_brought_back_is_written_before_the_line_that_goes_under_it(
    risks: Risks, project: Costed, who: Person
) -> None:
    # The nodes created again come before those changed (``bring_back``): the line goes under the
    # task that is only now written again, and the tasks are in their order.
    risk, _ = study_deleted(risks, project, who)
    undone(risks, who)
    line = risks.risk(risk)["provision_node_id"]
    nodes = {each["node_id"]: each for each in project.tree.items()}
    assert nodes[line]["parent_id"] == str(project.tasks[STUDY])
    roots = [each["node_id"] for each in project.tree.items() if each["parent_id"] is None]
    assert roots[:2] == [str(project.tasks[STUDY]), str(project.tasks[MAKING])]
